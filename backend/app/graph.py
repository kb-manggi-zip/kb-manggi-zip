"""LangGraph 오케스트레이션 — Phase B3 구현·연결 완료.

라우터(routers/api.py)가 아래 컴파일된 그래프를 경유해 호출한다:
  - build_compare_graph()  : compare 노드                                   → /api/compare
  - build_regions_graph()  : regions 노드                                   → /api/regions
  - build_analyze_graph()  : intake → clarify → compare → route → persona → narrate → /api/analyze

노드별 LLM/결정론(정직 표기):
  - clarify : LLM(llm_active 시 자유입력 해석, 축 제약) + 키워드 폴백. 모순 감지는 결정론.
  - compare : 결정론(순수 산술 + rules YAML).
  - route   : 결정론(if문 라우팅. 자율 에이전트 아님).
  - persona : 결정론(세그먼트 프로필 lookup + 가중치 조합).
  - narrate : LLM(통역) + 템플릿 폴백.

전 노드에 Langfuse `@observe` + 부모 span 'journey'로 **한 trace에 nested**,
프론트 `X-Session-Id` → `core/tracing.session_scope`로 **한 여정 = 한 Langfuse Session** 그룹핑.
각 span에 input/output/metadata 기록(무엇을 보고/판단해/넘겼는지).

남은 확장(선택):
  - simulate 노드의 LLM 내레이션(현재 narrator는 결정론 YAML fixture)
  - 계약서 Vision(extractor) 노드
"""

from typing import TypedDict

from langfuse import observe
from langgraph.graph import END, StateGraph

from .core import tracing  # noqa: F401 — Langfuse 클라이언트 초기화(키 있으면 생성, 없으면 None)
from .schemas import ContractInfo, FinanceInfo
from .tools import molit
from .tools.compare import compute_compare


class CompareState(TypedDict):
    contract: dict
    finance: dict
    comparison: dict


def _rules_snapshot() -> dict:
    """이 계산이 '어떤 규정·언제 기준'인지 관측에 남길 스냅샷 (LTV·KB캡·전환율 + checked_at)."""
    from .core.rules import read_yaml

    lend = read_yaml("lending_regulated.yaml")
    renew = read_yaml("renewal.yaml")
    conv = (renew.get("conversion_rate") or {}) if isinstance(renew, dict) else {}
    return {
        "ltv_first_home_regulated": lend["ltv"]["first_home"]["regulated"],
        "ltv_no_house_regulated": lend["ltv"]["no_house"]["regulated"],
        "kb_purchase_cap": lend["mortgage_cap"]["kb_purchase"],
        "dsr_stress_metro": lend["dsr"]["stress_rate"]["metro_regulated"],
        "conversion_rate": conv.get("value"),
        "conversion_rate_checked_at": conv.get("checked_at"),
        "lending_checked_at": "2026-07-20",  # 파일 헤더 주석 기준(값 셀단위 대조 완료)
    }


@observe(name="compare_node")
def compare_node(state: CompareState) -> dict:
    contract = ContractInfo(**state["contract"])
    finance = FinanceInfo(**state["finance"])
    result = compute_compare(contract, finance)
    comparison = result.model_dump()

    # 관측: 무엇을 보고(입력 요약) / 어떤 규정으로(스냅샷) / 무엇을 냈는지(3갈래 요약)
    tracing.span_update(
        input={"contract": state["contract"], "finance": state["finance"]},
        output={
            "branches": [
                {"branch": b["branch"], "depositOrPrice": b["depositOrPrice"], "monthlyBurden": b["monthlyBurden"]}
                for b in comparison["branches"]
            ],
            "dday": comparison["dday"],
        },
        metadata={"rules": _rules_snapshot()},
    )
    return {"comparison": comparison}


def build_compare_graph():
    graph = StateGraph(CompareState)
    graph.add_node("compare", compare_node)
    graph.set_entry_point("compare")
    graph.add_edge("compare", END)
    return graph.compile()


class RegionsState(TypedDict):
    branch: str
    budget: int
    houseType: str | None
    sigungu: str | None
    household: str | None
    note: str | None
    personaId: str | None
    regions: list


@observe(name="regions_node")
def regions_node(state: RegionsState) -> dict:
    # 후보 풀(top=8) → 개인화 스코어(통계근거 가중합)로 재정렬 → 상위 3 + 근거
    pool = molit.regions_by_branch(
        state["branch"], state["budget"], house_type=state.get("houseType"), sigungu=state.get("sigungu"), top=8
    )
    from .tools import persona, scoring

    # 스코어 입력은 조합 레이어(persona.scoring_ctx) 단일 소스로 — 자유입력·실측 override 포함.
    ctx = persona.scoring_ctx(
        {"note": state.get("note") or ""},
        {"household": state.get("household")},
        state["budget"],
        True if state.get("sigungu") else None,
        persona_id=state.get("personaId"),
    )
    pool_dicts = [r.model_dump() for r in pool]
    ranked = scoring.rank(pool_dicts, ctx, top=3)

    # 관측: 후보별 점수 breakdown + 적용 예산필터 + 가중치(자유입력 반영본)
    breakdown = {r["name"]: scoring.score_region(r, ctx)["breakdown"] for r in pool_dicts}
    tracing.span_update(
        input={
            "branch": state["branch"],
            "budget": state["budget"],
            "sigungu": state.get("sigungu"),
            "weights": ctx["weights"],
        },
        output={"top": [{"name": r["name"], "score": r["score"], "reasons": r["scoreReasons"]} for r in ranked]},
        metadata={
            "budget_filter": state["budget"],
            "candidates_evaluated": len(pool_dicts),
            "score_breakdown": breakdown,
        },
    )
    return {"regions": ranked}


def build_regions_graph():
    graph = StateGraph(RegionsState)
    graph.add_node("regions", regions_node)
    graph.set_entry_point("regions")
    graph.add_edge("regions", END)
    return graph.compile()


# ── 분석 에이전트: intake(상황파악) → compare(계산 tool) → narrate(개인화 LLM) ──
# 단일 함수가 아니라 다단계 흐름 → Langfuse에 '에이전트 경로'로 찍힌다(발표 시연).
class AnalyzeState(TypedDict):
    contract: dict
    finance: dict
    situation: str
    clarify: dict
    comparison: dict
    routing: dict
    persona: dict
    briefing: str


@observe(name="intake_node")
def intake_node(state: AnalyzeState) -> dict:
    """이해 단계 — 입력 검증 + 상황(페르소나) 서술. LLM이 잘하는 '이해'의 자리."""
    ContractInfo(**state["contract"])  # 검증
    FinanceInfo(**state["finance"])
    from .agents import briefing as briefing_agent

    situation = briefing_agent.situation_of(state)
    tracing.span_update(
        input={"contract": state["contract"], "finance": state["finance"]},
        output={"situation": situation},
    )
    return {"situation": situation}


@observe(name="clarify_node")
def clarify_node(state: AnalyzeState) -> dict:
    """명확화(판단) — 폼값+자유입력을 제약된 축으로 해석 + 모순 감지(되묻기). 창작 금지·닫힌 루프."""
    from .agents import clarify as clarify_agent
    from .core.config import settings

    note = state["contract"].get("note", "")
    result = clarify_agent.clarify(state["contract"], state["finance"], note=note)
    tracing.span_update(
        input={"note": note, "household": state["finance"].get("household")},
        output=result,  # persona·priorities·conflicts·questions·noteSignals(제약된 축 스키마)
        metadata={
            "conflict_detected": bool(result["conflicts"]),
            "signals": result["noteSignals"],
            "llm_used": settings.llm_active,  # False면 키워드 축 매핑(결정론 폴백)
        },
    )
    return {"clarify": result}


@observe(name="persona_node")
def persona_node(state: AnalyzeState) -> dict:
    """개인화 조합 — 확정 페르소나에 맞춰 리소스를 한 산출물(PersonaProfile)로 조합."""
    from .tools import persona as persona_tool

    # budgetBand용 예산 = 라우팅이 가리키는 갈래의 금액(없으면 0)
    budget = 0
    rec = (state.get("routing") or {}).get("branch")
    for b in (state.get("comparison") or {}).get("branches", []):
        if b.get("branch") == rec:
            budget = b.get("depositOrPrice", 0)
            break
    from .agents.report import persona_id_for

    pid = persona_id_for(state["finance"], state["contract"])
    prof = persona_tool.build_persona(state["contract"], state["finance"], budget, state.get("clarify"), persona_id=pid)

    # 관측: 가중치 조정 전→후 + 소비성향 신호별 출처(세그먼트/실측/진술) — 증거 위계
    from .tools import scoring

    base_weights = scoring.weights_for(state["finance"].get("household"))
    tracing.span_update(
        input={"household": state["finance"].get("household"), "note": state["contract"].get("note", "")},
        output=prof,  # PersonaProfile 전체
        metadata={
            "weights_before": base_weights,
            "weights_after": prof["weights"],
            "weight_basis": prof["weightBasis"],
            "consumption_sources": [s["source"] for s in prof.get("consumptionSignals", [])],
        },
    )
    return {"persona": prof}


@observe(name="route_node")
def route_node(state: AnalyzeState) -> dict:
    """슈퍼바이저 — '어떤 규칙 세트/어떤 갈래가 현실적인지' **결정론 라우팅**(if문, 자율 아님·LLM 없음).

    계산은 규칙, 여기선 '적용 선택'만. 흩어진 if문을 한 곳에 모아 유지보수·확장을 쉽게 하는 그릇.
    """
    from .agents import supervisor

    routing = supervisor.route(state["contract"], state["finance"], state["comparison"])
    tracing.span_update(
        input={"contract_type": state["contract"].get("type"), "housingType": state["contract"].get("housingType")},
        output=routing,
        metadata={"recommended_branch": routing.get("branch")},
    )
    return {"routing": routing}


@observe(name="narrate_node")
def narrate_node(state: AnalyzeState) -> dict:
    """개인화 통역 단계 — 계산된 숫자 + 라우팅(갈래 현실성)을 상황에 맞게 설명(LLM). 숫자는 comparison만 인용.

    페르소나는 여기서 하드코딩하지 않는다. briefing.build_system()이 persona_frames.yaml에서
    사용자 상황(계약유형·가구·청년·생애최초)에 매칭되는 관점 frame을 골라 시스템 프롬프트에 주입하고,
    호칭도 briefing이 가구 라벨에서 파생한다.
    """
    from .agents import briefing as briefing_agent
    from .schemas import BriefingRequest

    req = BriefingRequest(
        kind="compare",
        context={
            "comparison": state["comparison"],
            "contract": state["contract"],
            "finance": state["finance"],
            "routing": state.get("routing"),
        },
    )
    text = briefing_agent.run(req)
    # 통역 span: 무엇을 인용했는지(숫자 facts) + 생성문. verify/LLM 사용여부는 core.llm.generate가 같은 span에 기록.
    tracing.span_update(
        input={
            "facts": {
                "branches": [
                    {"branch": b["branch"], "monthlyBurden": b["monthlyBurden"]}
                    for b in state["comparison"]["branches"]
                ],
                "recommended": (state.get("routing") or {}).get("branch"),
            }
        },
        output={"briefing": text},
    )
    return {"briefing": text}


def build_analyze_graph():
    graph = StateGraph(AnalyzeState)
    graph.add_node("intake", intake_node)
    graph.add_node("clarify", clarify_node)
    graph.add_node("compare", compare_node)
    graph.add_node("route", route_node)
    graph.add_node("persona", persona_node)
    graph.add_node("narrate", narrate_node)
    graph.set_entry_point("intake")
    graph.add_edge("intake", "clarify")
    graph.add_edge("clarify", "compare")
    graph.add_edge("compare", "route")
    graph.add_edge("route", "persona")
    graph.add_edge("persona", "narrate")
    graph.add_edge("narrate", END)
    return graph.compile()
