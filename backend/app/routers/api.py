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
from ..core.db import get_db
from ..core.tracing import session_scope
from ..graph import build_analyze_graph, build_compare_graph, build_regions_graph
from ..models.reservation import Reservation
from ..schemas import (
    AnalyzeResponse,
    BriefingRequest,
    BriefingResponse,
    CompareRequest,
    CompareResponse,
    DraftNoticeRequest,
    DraftNoticeResponse,
    HousingType,
    ProductsRequest,
    ProductsResponse,
    Region,
    ReservationRequest,
    ReservationResponse,
    SimulateRequest,
    SimulateResponse,
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


@observe(name="analyze_agent")
def _run_analyze(contract: dict, finance: dict) -> dict:
    """부모 span — 이 안에서 그래프가 돌면 intake/compare/narrate 노드가 이 trace에 nested로 묶인다."""
    return _analyze_graph.invoke({"contract": contract, "finance": finance})


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: CompareRequest, session_id: str | None = Depends(get_session_id)) -> AnalyzeResponse:
    """분석 에이전트 — intake→compare→narrate 다단계 그래프(한 trace에 전 노드 nested).

    계산(결정론)과 개인화 통역(LLM)을 한 번의 에이전트 실행으로. 숫자는 compare 노드만 생성.
    """
    with session_scope(session_id):
        result = _run_analyze(req.contract.model_dump(), req.finance.model_dump())
    return AnalyzeResponse(comparison=CompareResponse(**result["comparison"]), briefing=result["briefing"])


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
    session_id: str | None = Depends(get_session_id),
) -> list[Region]:
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
            }
        )
    return result["regions"]


@observe(name="simulate")
def _run_simulate(branch: str, region_id: str) -> SimulateResponse:
    return narrator.run(branch, region_id)


@router.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest, session_id: str | None = Depends(get_session_id)) -> SimulateResponse:
    with session_scope(session_id):
        return _run_simulate(req.branch, req.regionId)


@observe(name="products")
def _run_products(branch: str, comparison) -> ProductsResponse:
    return matcher.run(branch, comparison)


@router.post("/products", response_model=ProductsResponse)
def products(req: ProductsRequest, session_id: str | None = Depends(get_session_id)) -> ProductsResponse:
    with session_scope(session_id):
        return _run_products(req.branch, req.comparison)


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
