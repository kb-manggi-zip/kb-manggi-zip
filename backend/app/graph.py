"""LangGraph 오케스트레이션 — Phase B3 구현·연결 완료.

라우터(routers/api.py)가 아래 컴파일된 그래프를 경유해 호출한다:
  - build_compare_graph()  : compare 노드            → /api/compare
  - build_regions_graph()  : regions 노드            → /api/regions
  - build_analyze_graph()  : intake → compare → narrate (다단계 분석 에이전트) → /api/analyze

전 노드에 Langfuse `@observe` 부착 + `analyze_agent` 부모 span으로 **한 trace에 nested**,
프론트 `X-Session-Id` → `core/tracing.session_scope`로 **한 여정 = 한 Langfuse Session** 그룹핑.
(검증: tests/, in-memory OTel exporter로 session.id 전파 확인)

남은 확장(선택):
  - Supervisor 분기: renewal 선택 시 regions/simulate 스킵 → finance 직행 (현재는 화면 흐름이 담당)
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


@observe(name="compare_node")
def compare_node(state: CompareState) -> dict:
    contract = ContractInfo(**state["contract"])
    finance = FinanceInfo(**state["finance"])
    result = compute_compare(contract, finance)
    return {"comparison": result.model_dump()}


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
    regions: list


@observe(name="regions_node")
def regions_node(state: RegionsState) -> dict:
    # 후보 풀(top=8) → 개인화 스코어(통계근거 가중합)로 재정렬 → 상위 3 + 근거
    pool = molit.regions_by_branch(
        state["branch"], state["budget"], house_type=state.get("houseType"), sigungu=state.get("sigungu"), top=8
    )
    from .tools import persona, scoring

    # 스코어 입력은 조합 레이어(persona.scoring_ctx) 단일 소스로 — 자유입력(note) 보정 가중치 포함.
    ctx = persona.scoring_ctx(
        {"note": state.get("note") or ""},
        {"household": state.get("household")},
        state["budget"],
        True if state.get("sigungu") else None,
    )
    ranked = scoring.rank([r.model_dump() for r in pool], ctx, top=3)
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

    return {"situation": briefing_agent.situation_of(state)}


@observe(name="clarify_node")
def clarify_node(state: AnalyzeState) -> dict:
    """명확화(판단) — 폼값+자유입력을 제약된 축으로 해석 + 모순 감지(되묻기). 창작 금지·닫힌 루프."""
    from .agents import clarify as clarify_agent

    result = clarify_agent.clarify(state["contract"], state["finance"], note=state["contract"].get("note", ""))
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
    prof = persona_tool.build_persona(state["contract"], state["finance"], budget, state.get("clarify"))
    return {"persona": prof}


@observe(name="route_node")
def route_node(state: AnalyzeState) -> dict:
    """슈퍼바이저 — '어떤 규칙 세트/어떤 갈래가 현실적인지' 라우팅(결정론).

    계산은 규칙, 여기선 '적용 선택'만. 경우의 수(주택유형×상황)가 늘수록 확장 우위 → '왜 에이전트'의 실체.
    """
    from .agents import supervisor

    routing = supervisor.route(state["contract"], state["finance"], state["comparison"])
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
    return {"briefing": briefing_agent.run(req)}


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
