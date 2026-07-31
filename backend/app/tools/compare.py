"""세 갈래 비교 계산기 ★ 서비스의 심장 (B1.5 리서치 반영).

프론트 src/engine/compare.ts 와 1:1 동치 (오차 0). 양쪽을 함께 고치고
`TZ=UTC npx tsx scripts/gen_fixtures.mjs && pytest` 로 검증한다.

B1.5 반영:
- 매매: 규제지역(수도권) 가정 · LTV(생애최초 70% / 무주택 40%) · KB 자체 한도 3억 ·
        스트레스 DSR(한도 산정에만) · 디딤돌 정책대출 혼합.
- 갱신/이사: 전세대출 금리 = 버팀목(under35 자격) 또는 KB 3.89% · HUG 3중 테이블 보증료.
- 금리 용도 분리: 한도 산정 = base+스트레스, 월 상환 표시 = base 만.

⚠️ 반올림은 js_round(=JS Math.round)로 통일. 매매 지역은 PoC상 수도권 규제지역 가정.
"""

from datetime import datetime, timezone

from ..core.rules import Rules, get_rules, read_yaml
from ..schemas import BranchResult, CompareResponse, ContractInfo, FinanceInfo
from .acquisition_tax import acquisition_fee
from .broker_fee import broker_fee
from .dates import d_day, notice_days_left, notice_deadline
from .format import format_amt, js_round
from .guarantee_hug import guarantee_rate
from .lending_calc import annuity_payment, dsr_loan_limit, effective_dsr_rate, solve_max_price
from .policy_loans import buttimok_youth_eligibility, didimdol_eligibility


def compute_compare(
    contract: ContractInfo,
    finance: FinanceInfo,
    rules: Rules | None = None,
    now: datetime | None = None,
) -> CompareResponse:
    rules = rules or get_rules()
    now = now or datetime.now(timezone.utc)
    lend = read_yaml("lending_regulated.yaml")

    deposit = contract.deposit
    monthly_rent = contract.monthlyRent
    ctype = contract.type
    renewal_used = contract.renewalUsed
    # 주택유형 → HUG 요율 유형. 아파트/연립다세대 둘 다 '주택'이라 세금·대출은 동일.
    hug_type = "apartment" if contract.housingType == "아파트" else "other"
    hug_label = "아파트" if contract.housingType == "아파트" else "연립·다세대"
    own_capital = finance.ownCapital
    annual_income = finance.annualIncome
    first_home = finance.firstHome
    under35 = finance.under35

    renewal = rules.renewal
    one_time = rules.oneTime
    notice_months = rules.noticeDeadlineMonths

    # ── 규제값 (수도권 규제지역 가정) ──
    jeonse_kb = lend["rates"]["jeonse_kb"]
    kb_base = lend["rates"]["kb_mortgage_default"]
    ltv_first = lend["ltv"]["first_home"]["regulated"]
    ltv_nohouse = lend["ltv"]["no_house"]["regulated"]
    kb_cap = lend["mortgage_cap"]["kb_purchase"]
    gov_cap = lend["mortgage_cap"]["gov_metro"]
    dsr_cap = lend["dsr"]["cap"]
    stress = lend["dsr"]["stress_rate"]["metro_regulated"]
    base_ratio = lend["dsr"]["base_ratio"]
    ltr = lend["dsr"]["loan_type_ratio"][lend["dsr"]["default_loan_type"]]
    term = lend["loan_term_years"]
    jeonse_cap = lend["jeonse_limit"]["base"]
    acq_reduction = lend["first_home_acq_reduction"]

    # ── 날짜 ──
    dday = d_day(contract.expiryDate, now)
    deadline = notice_deadline(contract.expiryDate, notice_months)
    days_left = notice_days_left(contract.expiryDate, notice_months, now)

    # ── 전세대출 유효 금리 (버팀목 청년 or KB 3.89%) ──
    bt = buttimok_youth_eligibility(
        age=30 if under35 else 99,
        annual_income=annual_income,
        deposit=deposit,
        net_asset=own_capital,
    )
    jeonse_rate = bt.rate if bt.eligible else jeonse_kb

    # === 갱신 ===
    # 집주인 요구 인상률(확정분)이 있으면 min(요구%, 법정상한 5%)로 계산 — 기존 상한 로직 재사용, 새 수식 없음.
    # 미입력(None)이면 renewal.increaseCap(5%) 그대로 → 기존 동작·골든패스 숫자 100% 불변.
    ask_pct = contract.renewalAskPct
    effective_cap = min(ask_pct / 100, renewal.increaseCap) if ask_pct is not None else renewal.increaseCap
    new_deposit = js_round(deposit * (1 + effective_cap)) if ctype == "전세" else deposit
    new_monthly = js_round(monthly_rent * (1 + effective_cap)) if ctype == "월세" else 0
    deposit_gap = max(0, new_deposit - deposit)
    renewal_loan_interest = js_round(deposit_gap * jeonse_rate / 12)
    renewal_guar_monthly = js_round(deposit * guarantee_rate(deposit, house_type=hug_type) / 12)
    renewal_monthly_burden = (
        renewal_loan_interest + renewal_guar_monthly if ctype == "전세" else new_monthly + renewal_guar_monthly
    )
    monthly_to_deposit = js_round(monthly_rent * 12 / renewal.conversionRate) if ctype == "월세" else 0

    # 통보기한 경과(days_left<0) → 임대인 미통보 시 '동일 조건 묵시적 갱신'(인상 0%)이 원칙(주임법 §6).
    notice_passed = days_left < 0
    cap_pct = int(round(renewal.increaseCap * 100))  # 법정 상한 % (=5)
    if notice_passed:
        # 묵시적 갱신 상태에선 '동일 조건 원칙'이 인상률 판정보다 우선.
        uncertainty = (
            "통보기한이 지나 임대인이 통보하지 않았다면 동일 조건 묵시적 갱신(인상 0%)이 원칙이에요. "
            f"아래 금액은 합의 인상 시 {cap_pct}% 상한 기준입니다."
        )
    elif ask_pct is not None:
        uncertainty = (
            f"요구하신 {ask_pct}%는 법정 상한({cap_pct}%) 이내예요."
            if ask_pct <= cap_pct
            else f"요구 {ask_pct}%는 법정 상한을 넘어요 — 상한({cap_pct}%) 기준으로 계산했어요."
        )
    elif renewal_used == "모름":
        uncertainty = "갱신권 미사용 시 5% 상한 적용 / 이미 사용 시 협의 필요"
    elif renewal_used == "사용":
        uncertainty = "이미 사용해 법정 갱신은 어려울 수 있어요"
    else:
        uncertainty = None

    # 헤드라인: 인상 반영 시 금액이 오르는데 '그대로'라고 하지 않도록 분기(B5).
    if ctype == "전세":
        renewal_headline = (
            f"보증금 {format_amt(deposit)} → {format_amt(new_deposit)} (합의 인상 시)"
            if new_deposit != deposit
            else f"보증금 {format_amt(deposit)} 그대로"
        )
    else:
        renewal_headline = f"월세 {js_round(new_monthly / 10000)}만으로 연장"

    renewal_basis = ["법정 상한 5%", "HUG 공시 요율"]
    if notice_passed:
        renewal_basis = ["통보기한 경과 → 동일 조건 갱신 원칙(주임법 §6)"] + renewal_basis

    renewal_branch = BranchResult(
        branch="갱신",
        headline=renewal_headline,
        depositOrPrice=new_deposit,
        loanAmount=deposit_gap,
        oneTimeCost=0,
        guaranteeMonthly=renewal_guar_monthly,
        monthlyBurden=renewal_monthly_burden,
        risks=[
            "보증금 반환 위험 지속",
            "법정 갱신권 이미 사용" if renewal_used == "사용" else "임대인 사정에 따라 거절 가능",
        ],
        cares=[f"반환보증 점검 (+{format_amt(renewal_guar_monthly)}/월)", "계약서 특약 확인"],
        basis=renewal_basis,
        uncertainty=uncertainty,
        feature="가장 가볍고 익숙함",
    )

    # === 이사 (전세대출 한도 = 보증금 80%, 최고 2.22억) ===
    extra = min(js_round(deposit * 0.80), jeonse_cap)
    move_budget = deposit + extra
    move_interest = js_round(extra * jeonse_rate / 12)
    move_guar_monthly = js_round(move_budget * guarantee_rate(move_budget, house_type=hug_type) / 12)
    move_one_time = js_round(one_time.moveBase + broker_fee(deposit))

    move_branch = BranchResult(
        branch="이사",
        headline=f"새 전세 최대 {format_amt(move_budget)}",
        depositOrPrice=move_budget,
        loanAmount=extra,
        oneTimeCost=move_one_time,
        guaranteeMonthly=move_guar_monthly,
        monthlyBurden=move_interest + move_guar_monthly,
        risks=["새 보증금 잠김", "이사 과정 일회성 비용"],
        cares=[
            "새 계약 시 전세보증금 반환보증 확인",
            f"일회성 비용 약 {format_amt(move_one_time)}",
        ],
        basis=["전세대출 한도 80%", "실거래 기준"],
        feature="환경을 바꿀 기회",
    )

    # === 매매 (수도권 규제지역 가정) ===
    capital = own_capital + deposit
    ltv = ltv_first if first_home == "예" else ltv_nohouse

    sizing_rate = effective_dsr_rate(kb_base, stress, base_ratio, ltr)  # 한도 산정용(스트레스)
    dsr_limit = dsr_loan_limit(annual_income, dsr_cap, sizing_rate, term)  # 기존부채 0

    policy = didimdol_eligibility(
        annual_income=annual_income,
        household=finance.household,
        is_no_house=True,
        net_asset=own_capital,
        first_home=(first_home == "예"),
        is_metro_regulated=True,
    )
    policy_limit = policy.limit if policy.eligible else 0
    bank_cap = min(kb_cap, gov_cap)  # KB 3억 < 정부 6억 → 3억

    max_price = solve_max_price(capital, ltv, dsr_limit, policy_limit, bank_cap)
    needed = max_price - capital

    policy_amt = min(policy_limit, needed) if policy.eligible else 0
    bank_amt = needed - policy_amt
    buy_monthly = js_round(
        annuity_payment(policy_amt, policy.rate, term)
        + annuity_payment(bank_amt, kb_base, term)  # 표시용은 base(스트레스 아님)
    )
    buy_move_broker = broker_fee(max_price, table="broker_rate_bands_purchase")
    buy_one_time = js_round(one_time.moveBaseBuy + buy_move_broker + acquisition_fee(max_price))
    if first_home == "예":
        buy_one_time = max(0, buy_one_time - acq_reduction)

    buy_basis = [f"규제지역 LTV {js_round(ltv * 100)}%", "KB 한도 3억", "스트레스 DSR 가산 3.0%"]
    if policy.eligible:
        buy_basis.append("디딤돌 혼합")

    buy_branch = BranchResult(
        branch="매매",
        headline=f"최대 {format_amt(max_price)} 내 집",
        depositOrPrice=max_price,
        loanAmount=needed,
        oneTimeCost=buy_one_time,
        guaranteeMonthly=0,
        monthlyBurden=buy_monthly,
        risks=["자산가치 변동", "원금 장기 상환 부담"],
        cares=["화재보험 가입", "청약통장 납입 유지"],
        basis=buy_basis,
        feature="일부는 원금으로 적립",
    )

    savings = move_one_time

    assumptions = [
        "이 금액은 사전 가늠이며, 실제 대출 심사 결과와 다를 수 있어요",
        "전세대출 금리 HF 공시 평균 3.89%",
        "규제지역 LTV 40% (생애최초 70%)",
        "KB 주택구입 대출 한도 3억 (2026.7~)",
        "스트레스 DSR 수도권 3.0% (한도 산정에만 적용)",
        f"보증료 HUG 공시 요율 ({hug_label}·부채비율 80% 이하 가정)",
        "기존 대출이 없다고 가정했어요. 대출이 있으면 한도가 줄어들 수 있어요",
    ]
    if first_home == "모름":
        assumptions.append("생애최초 주택구입이라면 LTV 70%까지 가능해 한도가 더 늘어날 수 있어요")
    assumptions.append("법정 상한 5%")

    return CompareResponse(
        branches=[renewal_branch, move_branch, buy_branch],
        dday=dday,
        noticeDaysLeft=days_left,
        noticeDeadline=deadline,
        monthlyToDeposit=monthly_to_deposit,
        savings=savings,
        assumptions=assumptions,
    )
