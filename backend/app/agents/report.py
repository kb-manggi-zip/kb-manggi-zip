"""만기 결정 리포트 조립 — 최종 산출물(①상황 ②채점 ③동네 ④하루 ⑤지출 실현가능성 ⑥액션).

⚠️ 단방향 원칙: compute_compare(예산)는 **읽기 전용 맥락**으로 인용만 한다.
   지출 분석(spend)은 comparison을 입력으로 받지 않고, comparison도 spend를 절대 참조하지 않는다.
   → 예산은 금융 사실만으로. 지출은 리포트 ⑤의 맥락 정보로만. (코드 리뷰 확인 지점)
"""

from typing import Optional

from ..schemas import (
    Branch,
    ContractInfo,
    DecisionReport,
    FinanceInfo,
    Region,
    SpendAnalysis,
)


def _man(won: int) -> str:
    """원 → '만원' 반올림 표기."""
    return f"{round(won / 10_000):,}만원"


def persona_id_for(finance: dict, contract: dict) -> str:
    """데모 매핑: 가구/계약 → 합성 마이데이터 페르소나(P1/P2/P3). (실서비스는 마이데이터 본인 계정)"""
    if finance.get("household") == "신혼":
        return "P2"
    if contract.get("type") == "월세":
        return "P3"
    return "P1"


def _feasibility_sentence(selected, spend: Optional[dict]) -> str:
    """⑤ 정보형 문장 — compare의 월 부담(맥락) vs 지출 변동 여력(집계). 권유 금지."""
    if not spend:
        return "지출로 본 실현 가능성은 마이데이터 동의 후 실제 내역으로 분석됩니다."
    burden = selected.monthlyBurden  # compare 출력(맥락). 여기서 재계산하지 않는다.
    variable = spend["variableMonthly"]
    if burden <= variable:
        return (
            f"선택하신 '{selected.branch}'의 월 부담 {_man(burden)}은 현재 변동지출 여력 {_man(variable)} 안에 있어요."
        )
    gap = burden - variable
    adjustables = [t for t in spend["topCategories"] if t["category"] not in ("주거", "보험")][:2]
    hint = ", ".join(f"{t['category']} {_man(t['monthly'])}" for t in adjustables) or "변동지출"
    return f"월 {_man(gap)}이 현재 변동지출 여력({_man(variable)})을 넘어요. 조정 가능 지출: {hint}."


def build_report(
    contract: dict,
    finance: dict,
    branch: Branch,
    *,
    persona_id: Optional[str] = None,
    region_id: Optional[str] = None,
) -> DecisionReport:
    from ..tools import molit
    from ..tools import persona as persona_tool
    from ..tools.compare import compute_compare
    from . import clarify as clarify_agent
    from . import narrator

    # ② 채점 — compare 출력을 '맥락'으로 인용(읽기 전용)
    comparison = compute_compare(ContractInfo(**contract), FinanceInfo(**finance))
    selected = next((b for b in comparison.branches if b.branch == branch), comparison.branches[0])
    budget = selected.depositOrPrice

    # ① 상황 — 명확화(HITL 반영 내역) + 페르소나 조합
    cl = clarify_agent.clarify(contract, finance, note=contract.get("note", ""))
    prof = persona_tool.build_persona(contract, finance, budget, cl)

    # ③④ 동네·발품 — 이사/매매만(갱신은 현 동네 유지). regions_node와 동일하게 스코어링 태워 근거 확보.
    top_region = None
    day_brief = ""
    if branch in ("이사", "매매"):
        from ..tools import scoring

        pool = molit.regions_by_branch(branch, budget, house_type=contract.get("housingType"), top=8)
        if pool:
            ctx = persona_tool.scoring_ctx(contract, finance, budget, None)
            ranked = scoring.rank([r.model_dump() for r in pool], ctx, top=1)
            if ranked:
                top_region = Region(**ranked[0])
                day_brief = narrator.lifestyle_fallback({"region": ranked[0], "branch": branch, "finance": finance})

    # ⑤ 지출 실현가능성 — 합성 마이데이터 집계(가드레일 T2SQL/표준). compare와 단방향.
    from . import spend_query

    pid = persona_id or persona_id_for(finance, contract)
    persona_ctx = f"{finance.get('household')} 가구 · {contract.get('type')} 계약 · note={contract.get('note', '')}"
    spend = spend_query.analyze_spending(pid, persona_ctx=persona_ctx, branch=branch)
    feasibility = _feasibility_sentence(selected, spend)

    return DecisionReport(
        persona=prof,  # PersonaProfile dict → pydantic 변환
        clarify=cl,
        comparison=comparison,
        selectedBranch=branch,
        topRegion=top_region,
        dayBrief=day_brief,
        spend=SpendAnalysis(**spend) if spend else None,
        feasibility=feasibility,
        dday=comparison.dday,
        noticeDeadline=comparison.noticeDeadline,
    )
