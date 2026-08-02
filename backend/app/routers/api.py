"""API 라우터 — 엔드포인트 계약(types.ts 1:1).

| 엔드포인트            | 처리                              | LLM |
|----------------------|-----------------------------------|-----|
| POST /api/compare    | tools.compare (3종+보증료)        | ❌  |
| GET  /api/regions    | tools.molit 필터 → Region[]       | ❌  |
| POST /api/simulate   | agents.narrator → SimulateResponse| ✅* |
| POST /api/products   | agents.matcher → ProductsResponse | ✅* |
| POST /api/briefing   | agents.briefing → 통역 문장       | ✅* |
| POST /api/draft-notice | agents.drafter                  | ✅* |
| POST /api/reservation| DB 저장                           | ❌  |
(*: 현재 LLM 비활성 시 템플릿/fixture 폴백)
"""

import asyncio

from fastapi import APIRouter, Depends, Header, Query
from langfuse import observe
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from ..agents import briefing, drafter, matcher, narrator
from ..core import tracing
from ..core.db import get_db
from ..core.tracing import session_scope
from ..graph import build_analyze_graph, build_compare_graph, build_regions_graph
from ..models.reservation import Reservation
from ..schemas import (
    AnalyzeResponse,
    BriefingRequest,
    BriefingResponse,
    ClarifyRequest,
    ClarifyResult,
    CompareRequest,
    CompareResponse,
    DecisionReport,
    DraftNoticeRequest,
    DraftNoticeResponse,
    HitlRequest,
    HousingType,
    PersonaProfile,
    ProductsRequest,
    ProductsResponse,
    Region,
    ReportRequest,
    ReservationRequest,
    ReservationResponse,
    SimulateRequest,
    SimulateResponse,
    ValidateProfileRequest,
)

router = APIRouter(prefix="/api")


def get_session_id(x_session_id: str | None = Header(default=None)) -> str | None:
    """프론트가 여정마다 보내는 세션ID(헤더 X-Session-Id). 스키마(body) 변경 없음.

    없으면 None → 트레이싱 no-op. 있으면 이 요청의 trace가 해당 세션으로 묶인다.
    """
    return x_session_id


_compare_graph = build_compare_graph()


@router.post("/compare", response_model=CompareResponse)
def compare(req: CompareRequest, session_id: str | None = Depends(get_session_id)) -> CompareResponse:
    with session_scope(session_id):
        result = _compare_graph.invoke(
            {
                "contract": req.contract.model_dump(),
                "finance": req.finance.model_dump(),
            }
        )
    return CompareResponse(**result["comparison"])


_analyze_graph = build_analyze_graph()


@observe(name="journey")
def _run_analyze(contract: dict, finance: dict) -> dict:
    """부모 span(=여정) — 그래프 6노드(intake/clarify/compare/route/persona/narrate)가 이 trace에 nested."""
    return _analyze_graph.invoke({"contract": contract, "finance": finance})


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: CompareRequest, session_id: str | None = Depends(get_session_id)) -> AnalyzeResponse:
    """분석 에이전트 — intake→clarify→compare→route→persona→narrate 6노드 그래프(한 trace에 전 노드 nested).

    계산(결정론)·명확화(판단)·조합(결정론)·통역(LLM)을 한 번의 에이전트 실행으로. 숫자는 compare 노드만 생성.
    """
    with session_scope(session_id):
        result = _run_analyze(req.contract.model_dump(), req.finance.model_dump())
    return AnalyzeResponse(
        comparison=CompareResponse(**result["comparison"]),
        briefing=result["briefing"],
        clarify=ClarifyResult(**result["clarify"]) if result.get("clarify") else None,
        persona=PersonaProfile(**result["persona"]) if result.get("persona") else None,
    )


@router.post("/clarify", response_model=ClarifyResult)
def clarify_endpoint(req: ClarifyRequest, session_id: str | None = Depends(get_session_id)) -> ClarifyResult:
    """명확화(판단) — 폼값+자유입력 → 제약 해석 + 모순 되묻기(가구불일치·이전 반영 충돌). 계산 전에 페르소나 확정."""
    from ..agents import clarify as clarify_agent

    with session_scope(session_id):
        result = clarify_agent.clarify(
            req.contract.model_dump(),
            req.finance.model_dump(),
            note=req.contract.note,
            prior_notes=req.priorNotes,
            household_selected=req.householdSelected,
        )
    return ClarifyResult(**result)


@observe(name="profile_validation")
def _run_validate_profile(req: ValidateProfileRequest) -> ClarifyResult:
    """SC-14 최종 프로필 종합검증 — '무엇을 봤고 어떻게 검증했나'가 이 span에 남는다(관측·발표 물증)."""
    from ..agents import clarify as clarify_agent

    result = clarify_agent.validate_profile(
        req.contract.model_dump(),
        req.finance.model_dump(),
        budget=req.budget,
        household_selected=req.householdSelected,
        accepted_pairs=req.acceptedPairs,
    )
    tracing.span_update(
        input={"notes": req.contract.note, "household": req.finance.household, "budget": req.budget},
        output=result,
        metadata={"mode": result["mode"], "conflict_count": len(result["conflicts"])},
    )
    return ClarifyResult(**result)


@router.post("/validate-profile", response_model=ClarifyResult)
def validate_profile_endpoint(
    req: ValidateProfileRequest, session_id: str | None = Depends(get_session_id)
) -> ClarifyResult:
    """최종 프로필 종합검증 — 누적 자유입력+가구+예산을 한 번에 의미 검증(LLM) / 간이 검증(키워드 폴백)."""
    with session_scope(session_id):
        return _run_validate_profile(req)


@observe(name="decision_report")
def _run_report(req: ReportRequest) -> DecisionReport:
    from ..agents import report as report_agent

    return report_agent.build_report(
        req.contract.model_dump(),
        req.finance.model_dump(),
        req.branch,
        persona_id=req.personaId,
        region_id=req.regionId,
    )


@router.post("/report", response_model=DecisionReport)
def report(req: ReportRequest, session_id: str | None = Depends(get_session_id)) -> DecisionReport:
    """만기 결정 리포트 — 최종 산출물. ⑤ 지출은 합성 마이데이터 집계(가드레일 T2SQL), compare와 단방향."""
    with session_scope(session_id):
        return _run_report(req)


@router.post("/hitl")
def hitl(req: HitlRequest, session_id: str | None = Depends(get_session_id)) -> dict:
    """HITL 확정 이벤트 기록(관측 전용) — 같은 세션 trace에 '제안→사용자 확정'을 박제. 계산 부작용 없음."""
    with session_scope(session_id):
        tracing.trace_event(
            "hitl_persona_confirm",
            metadata={"choice": req.choice, "signals": req.signals, "note": req.note},
        )
    return {"ok": True}


@router.post("/persona", response_model=PersonaProfile)
def persona_endpoint(
    req: CompareRequest,
    budget: int = Query(default=0),  # 프론트가 고른 갈래 예산 → budgetBand 표기용
    personaId: str = Query(default=""),  # 합성 마이데이터 페르소나 → 실측 소비 override
    session_id: str | None = Depends(get_session_id),
) -> PersonaProfile:
    """개인화 조합 레이어 — 확정 페르소나 → 리소스 조합 산출물(화면 프로필 카드)."""
    from ..agents import clarify as clarify_agent
    from ..agents.report import persona_id_for
    from ..tools import persona as persona_tool

    with session_scope(session_id):
        c = req.contract.model_dump()
        f = req.finance.model_dump()
        cl = clarify_agent.clarify(c, f, note=req.contract.note)
        pid = personaId or persona_id_for(f, c)
        prof = persona_tool.build_persona(c, f, budget=budget, clarify_result=cl, persona_id=pid)
    return PersonaProfile(**prof)


_regions_graph = build_regions_graph()


def _sigungu_code(area: str) -> str | None:
    """선호지역 구명(예 '마포구') → 시군구코드('11440'). 빈값/미매칭 → None(6구 전체)."""
    if not area:
        return None
    from ..core.rules import read_yaml

    entry = (read_yaml("regions.yaml").get("sigungu") or {}).get(area)
    return entry.get("code") if entry else None


@router.get("/regions", response_model=list[Region])
def regions(
    branch: str = Query(...),
    budget: int = 0,
    housingType: HousingType | None = Query(default=None),
    preferredArea: str = Query(default=""),  # 선호지역 구명 → 그 구에서 우선 추천(없으면 6구 전체)
    household: str = Query(default=""),  # 개인화 스코어 가중치·통근 직장 결정용
    note: str = Query(default=""),  # 자유입력 → (adjust 없을 때) 키워드 보정
    adjust: str = Query(default=""),  # HITL 확정된 축별 배수(JSON) → 랭킹에 직접 반영(자연어 확정분)
    personaId: str = Query(default=""),  # 실측 소비 override(values_food)를 순위에 반영
    session_id: str | None = Depends(get_session_id),
) -> list[Region]:
    import json

    try:
        note_adjust = json.loads(adjust) if adjust else {}
        if not isinstance(note_adjust, dict):
            note_adjust = {}
    except json.JSONDecodeError:
        note_adjust = {}
    # housingType이 국토부 API property_type과 동일 값('아파트'|'연립다세대')이라 변환 없이 그대로 씀
    house_type = housingType
    with session_scope(session_id):
        result = _regions_graph.invoke(
            {
                "branch": branch,
                "budget": budget,
                "houseType": house_type,
                "sigungu": _sigungu_code(preferredArea),
                "household": household or None,
                "note": note or None,
                "noteAdjust": note_adjust,
                "personaId": personaId or None,
            }
        )
    return result["regions"]


@observe(name="simulate")
def _run_simulate(branch: str, region_id: str, household: str | None, lead_signal: str | None) -> SimulateResponse:
    return narrator.run(branch, region_id, household=household, lead_signal=lead_signal)


@router.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest, session_id: str | None = Depends(get_session_id)) -> SimulateResponse:
    with session_scope(session_id):
        return _run_simulate(req.branch, req.regionId, req.household, req.leadSignal)


@observe(name="products")
def _run_products(branch: str, comparison, contract_type: str | None = None) -> ProductsResponse:
    return matcher.run(branch, comparison, contract_type)


@router.post("/products", response_model=ProductsResponse)
def products(req: ProductsRequest, session_id: str | None = Depends(get_session_id)) -> ProductsResponse:
    with session_scope(session_id):
        contract_type = req.contract.type if req.contract else None
        return _run_products(req.branch, req.comparison, contract_type)


@observe(name="briefing")
def _run_briefing(req: BriefingRequest) -> str:
    return briefing.run(req)


@router.post("/briefing", response_model=BriefingResponse)
def briefing_endpoint(req: BriefingRequest, session_id: str | None = Depends(get_session_id)) -> BriefingResponse:
    # 한 번에 반환(비스트리밍). 타이핑 UX는 /briefing/stream 사용.
    with session_scope(session_id):
        return BriefingResponse(text=_run_briefing(req))


@router.post("/briefing/stream")
async def briefing_stream(
    req: BriefingRequest, session_id: str | None = Depends(get_session_id)
) -> EventSourceResponse:
    """통역 문장을 토큰 단위로 SSE 스트리밍 (프론트 타이핑 효과와 연결).

    이벤트: data:<청크> 반복 → 마지막에 event:done. LLM 비활성 시 폴백 템플릿을 어절로 흘림.
    """

    async def event_gen():
        with session_scope(session_id):
            for chunk in briefing.stream(req):
                yield {"data": chunk}
                await asyncio.sleep(0.03)  # 청크 페이싱 — 폴백도 '타이핑'처럼 보이게 (실 Claude는 자연 페이스)
        yield {"event": "done", "data": "[DONE]"}

    return EventSourceResponse(event_gen())


@router.post("/draft-notice", response_model=DraftNoticeResponse)
def draft_notice(req: DraftNoticeRequest, session_id: str | None = Depends(get_session_id)) -> DraftNoticeResponse:
    with session_scope(session_id):
        return drafter.run(req)


@router.post("/reservation", response_model=ReservationResponse)
def reservation(req: ReservationRequest, db: Session = Depends(get_db)) -> ReservationResponse:
    row = Reservation(branch=req.branch, date=req.date, product_name=req.productName)
    db.add(row)
    db.commit()
    db.refresh(row)
    return ReservationResponse(ok=True, id=row.id)
