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
    NextAction,
    Region,
    SpendAnalysis,
)


def _man(won: int) -> str:
    """원 → '만원' 반올림 표기."""
    return f"{round(won / 10_000):,}만원"


def _next_action(branch: Branch, contract: dict, finance: dict, selected) -> NextAction:
    """⑥ 자격 기반 차액 — compute_compare와 같은 정책대출 자격 판정으로 이자 절감액을 계산.

    전세(갱신/이사): 버팀목 청년 vs KB 전세대출 금리 차 × 대출액.
    매매: 디딤돌 vs KB 주담대 금리 차 × 정책대출 인정액(혼합분).
    자격 미해당이면 annualSaving=0 + 요건 확인 안내. (모두 rules 값, 창작 없음)
    """
    from ..core.rules import read_yaml
    from ..tools.policy_loans import buttimok_youth_eligibility, didimdol_eligibility

    lend = read_yaml("lending_regulated.yaml")
    loan = selected.loanAmount or 0

    if branch in ("갱신", "이사"):
        kb_rate = lend["rates"]["jeonse_kb"]
        bt = buttimok_youth_eligibility(
            age=30 if finance.get("under35") else 99,
            annual_income=finance.get("annualIncome", 0),
            deposit=contract.get("deposit", 0),
            net_asset=finance.get("ownCapital", 0),
        )
        if bt.eligible and loan > 0 and bt.rate < kb_rate:
            saving = round(loan * (kb_rate - bt.rate))
            return NextAction(
                headline="버팀목 청년 전세대출 자격이면 이자를 아껴요",
                detail=(
                    f"KB 전세대출 {kb_rate:.2%} 대신 버팀목 {bt.rate:.2%} 적용 시 "
                    f"대출 {_man(loan)} 기준 연 약 {_man(saving)} 절감"
                ),
                annualSaving=saving,
                eligible=True,
            )
        return NextAction(
            headline="버팀목 청년 전세대출 자격을 먼저 확인해요",
            detail="만34세 이하·소득·보증금 요건을 충족하면 KB 대비 낮은 금리가 적용될 수 있어요. 상담에서 확인해요.",
            annualSaving=0,
            eligible=False,
        )

    # 매매 — 디딤돌 혼합분 이자 경감
    kb_base = lend["rates"]["kb_mortgage_default"]
    policy = didimdol_eligibility(
        annual_income=finance.get("annualIncome", 0),
        household=finance.get("household"),
        is_no_house=True,
        net_asset=finance.get("ownCapital", 0),
        first_home=(finance.get("firstHome") == "예"),
        is_metro_regulated=True,
    )
    gov_cap = lend["mortgage_cap"]["gov_metro"]
    policy_amt = min(policy.limit, gov_cap, loan) if policy.eligible else 0
    if policy.eligible and policy_amt > 0 and policy.rate < kb_base:
        saving = round(policy_amt * (kb_base - policy.rate))
        return NextAction(
            headline="디딤돌 정책대출을 섞으면 이자를 아껴요",
            detail=(
                f"KB 주담대 {kb_base:.2%} 대신 디딤돌 {policy.rate:.2%}(최저) 혼합 시 "
                f"{_man(policy_amt)} 기준 연 약 {_man(saving)} 경감"
            ),
            annualSaving=saving,
            eligible=True,
        )
    return NextAction(
        headline="디딤돌 정책대출 자격을 먼저 확인해요",
        detail="무주택·소득·자산 요건을 충족하면 낮은 고정금리를 섞을 수 있어요. 상담에서 확인해요.",
        annualSaving=0,
        eligible=False,
    )


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

    pid = persona_id or persona_id_for(finance, contract)

    # ① 상황 — 명확화(HITL 반영) + 페르소나 조합(persona_id로 실측 소비 override 반영)
    cl = clarify_agent.clarify(contract, finance, note=contract.get("note", ""))
    prof = persona_tool.build_persona(contract, finance, budget, cl, persona_id=pid)

    # ③④ 동네·발품 — 이사/매매만(갱신은 현 동네 유지). regions_node와 동일하게 스코어링 태워 근거 확보.
    top_region = None
    day_brief = ""
    if branch in ("이사", "매매"):
        from ..tools import scoring

        pool = molit.regions_by_branch(branch, budget, house_type=contract.get("housingType"), top=8)
        if pool:
            ctx = persona_tool.scoring_ctx(contract, finance, budget, None, persona_id=pid)
            ranked = scoring.rank([r.model_dump() for r in pool], ctx, top=len(pool))
            # L5: 사용자가 실제로 본 '선택한 동네'(region_id)를 우선 채택, 없으면 추천 1위. (일관성)
            chosen = next((r for r in ranked if r.get("id") == region_id), None) or (ranked[0] if ranked else None)
            if chosen:
                top_region = Region(**chosen)
                # L5.2: 발품 소비 문구를 프로필 칩과 같은 신호(실측>진술>세그먼트)로 — 불일치 해소.
                sigs = prof.get("consumptionSignals", [])
                lead = (
                    next((s for s in sigs if s.get("source") == "실측"), None)
                    or next((s for s in sigs if s.get("source") == "진술"), None)
                    or next((s for s in sigs if s.get("source") == "세그먼트"), None)
                )
                day_brief = narrator.lifestyle_fallback(
                    {
                        "region": chosen,
                        "branch": branch,
                        "finance": finance,
                        "trait": lead.get("label") if lead else None,
                    }
                )
    else:
        # 갱신: 새 발품 대신 '현재 동네 유지' 연속성 요약 — 여정에 빈 구간이 안 생기게(B7).
        area = contract.get("preferredArea") or "지금 사는 동네"
        move_cost = next((b.oneTimeCost for b in comparison.branches if b.branch == "이사"), 0)
        day_brief = (
            f"{area}에서의 익숙한 동선을 그대로 이어가요. 새로 적응할 동네도, 발품도 필요 없어요. "
            f"이사였다면 들었을 일회성 비용 약 {_man(move_cost)}을(를) 아끼는 셈이에요."
        )

    # ⑤ 지출 실현가능성 — 합성 마이데이터 집계(가드레일 T2SQL/표준). compare와 단방향.
    from . import spend_query

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
        nextAction=_next_action(branch, contract, finance, selected),
        dday=comparison.dday,
        noticeDeadline=comparison.noticeDeadline,
    )
