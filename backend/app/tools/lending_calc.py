"""대출 한도·상환 계산 프리미티브 (B1.5 리서치 반영, 순수).

핵심 원칙(스펙 2-2):
- **금리 용도 분리**: 한도 산정 = base + 스트레스, 월 상환 표시 = base 만.
  지금 working compare는 stressRate 하나로 둘 다 써서 월 부담이 과대 → 여기서 분리한다.
- C6 앵커: annuity_payment(3.2억, 2.85%, 30) ≈ 1,323,383원 (HF 계산기 일치).
"""


def annuity_payment(principal: float, annual_rate: float, years: int) -> float:
    """원리금균등 월 상환액."""
    if principal <= 0:
        return 0.0
    r = annual_rate / 12
    n = years * 12
    if r == 0:
        return principal / n
    return principal * r / (1 - (1 + r) ** -n)


def pv_annuity(monthly_pmt: float, annual_rate: float, years: int) -> float:
    """월 상환액 → 감당 가능한 원금(연금현가). DSR 한도 역산용."""
    if monthly_pmt <= 0:
        return 0.0
    r = annual_rate / 12
    n = years * 12
    if r == 0:
        return monthly_pmt * n
    return monthly_pmt * (1 - (1 + r) ** -n) / r


def effective_dsr_rate(
    base_rate: float, stress_rate: float, base_ratio: float, loan_type_ratio: float
) -> float:
    """DSR '산정용' 금리 = base + 스트레스×기본비율×유형비율. (월상환 표시엔 쓰지 말 것)"""
    return base_rate + stress_rate * base_ratio * loan_type_ratio


def dsr_loan_limit(
    annual_income: float,
    dsr_cap: float,
    sizing_rate: float,
    years: int,
    existing_debt_monthly: float = 0.0,
) -> float:
    """DSR 한도액. (연소득×DSR상한/12 - 기존부채월상환)을 산정금리로 연금현가."""
    monthly_capacity = annual_income * dsr_cap / 12 - existing_debt_monthly
    return pv_annuity(monthly_capacity, sizing_rate, years)


def solve_max_price(
    capital: float,
    ltv: float,
    dsr_limit: float,
    policy_limit: float,
    bank_cap: float,
) -> int:
    """최대 집값. loan_needed(=price-capital) ≤ loan_allowed(=min(price×ltv, 절대상한)).

    절대상한 = min(dsr_limit, policy_limit + bank_cap).
    - LTV 제약:  price ≤ capital / (1 - ltv)
    - 절대 제약: price ≤ capital + 절대상한
    """
    abs_cap = min(dsr_limit, policy_limit + bank_cap)
    price_abs = capital + abs_cap
    price_ltv = float("inf") if ltv >= 1 else capital / (1 - ltv)
    return int(min(price_ltv, price_abs))
