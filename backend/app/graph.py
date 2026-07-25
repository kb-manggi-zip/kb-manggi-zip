"""LangGraph 오케스트레이션 — Phase B3 SEAM (미구현·미연결).

현재 라우터(routers/api.py)는 tools·agents 를 **직접** 호출한다 (단순·안정).
Phase B3에서 이 파일에 Supervisor 그래프를 구성하고, 라우터가 그래프를 경유하도록 바꾼다.
그래프로 바꿔도 각 노드의 결과(계산·집계·통역)는 지금과 동일해야 한다(회귀 기준).

의도한 그래프 (기획서 7절):
    Supervisor
      ├─ intake        (문진 정리)
      ├─ compare       → tools/compare.py           (LLM 없음)
      ├─ regions       → tools/molit.py             (LLM 없음)
      ├─ simulate      → agents/narrator.py         (LLM)
      ├─ content       → agents/briefing.py         (LLM, SSE)
      └─ finance       → agents/matcher.py (RAG)    (LLM)
    renewal 선택 시 regions/simulate 스킵 → finance 직행.

구현 시:
  - requirements.txt 의 langgraph·langfuse 주석 해제
  - 상태 스키마 = app/schemas.py 재사용 (AppState 확장)
  - Langfuse 트레이싱을 전 노드에 부착 (발표용 노드 경로 캡처)
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
    regions: list


@observe(name="regions_node")
def regions_node(state: RegionsState) -> dict:
    result = molit.regions_by_branch(state["branch"], state["budget"])
    return {"regions": [r.model_dump() for r in result]}


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
    comparison: dict
    briefing: str


@observe(name="intake_node")
def intake_node(state: AnalyzeState) -> dict:
    """이해 단계 — 입력 검증 + 상황(페르소나) 서술. LLM이 잘하는 '이해'의 자리."""
    ContractInfo(**state["contract"])  # 검증
    FinanceInfo(**state["finance"])
    from .agents import briefing as briefing_agent

    return {"situation": briefing_agent.situation_of(state)}


@observe(name="narrate_node")
def narrate_node(state: AnalyzeState) -> dict:
    """개인화 통역 단계 — 계산된 숫자를 상황에 맞게 설명(LLM). 숫자는 comparison만 인용."""
    from .agents import briefing as briefing_agent
    from .schemas import BriefingRequest

    f = state["finance"]
    name = "신혼 가구" if f.get("household") == "신혼" else "고객"
    req = BriefingRequest(
        kind="compare",
        context={
            "comparison": state["comparison"],
            "contract": state["contract"],
            "finance": state["finance"],
            "name": name,
        },
    )
    return {"briefing": briefing_agent.run(req)}


def build_analyze_graph():
    graph = StateGraph(AnalyzeState)
    graph.add_node("intake", intake_node)
    graph.add_node("compare", compare_node)
    graph.add_node("narrate", narrate_node)
    graph.set_entry_point("intake")
    graph.add_edge("intake", "compare")
    graph.add_edge("compare", "narrate")
    graph.add_edge("narrate", END)
    return graph.compile()
