"""정책대출 자격·한도·금리 (B1.5 리서치 반영, 순수).

디딤돌(매매)·버팀목 청년전세(이사/갱신). rules/policy_loans.yaml 사용.
자격 판정은 코드(LLM 아님). 숫자는 yaml 원문만.
"""

from dataclasses import dataclass

from ..core.rules import read_yaml


@dataclass
class PolicyResult:
    eligible: bool
    limit: int
    rate: float
    reason: str


def didimdol_eligibility(
    *,
    annual_income: int,
    household: str,  # '1인' | '신혼' | '자녀'
    is_no_house: bool,
    net_asset: int,
    first_home: bool = False,
    is_metro_regulated: bool = False,
    rules: dict | None = None,
) -> PolicyResult:
    d = (rules or read_yaml("policy_loans.yaml"))["didimdol"]

    # 카테고리별 소득상한/한도 (신혼 > 생애최초·2자녀 > 일반)
    if household == "신혼":
        income_cap = d["income_cap"]["newlywed"]
        limit = d["limit"]["newlywed_or_2child"]
        cat = "신혼"
    elif household == "자녀":
        income_cap = d["income_cap"]["first_home_or_2child"]
        limit = d["limit"]["newlywed_or_2child"]
        cat = "다자녀"
    elif first_home:
        income_cap = d["income_cap"]["first_home_or_2child"]
        limit = d["limit"]["first_home"]
        cat = "생애최초"
    else:
        income_cap = d["income_cap"]["general"]
        limit = d["limit"]["general"]
        cat = "일반"

    eligible = (
        (not d["requires_no_house"] or is_no_house) and annual_income <= income_cap and net_asset <= d["net_asset_cap"]
    )
    rate = d["rate_min"]  # 최저금리(우대 기준) — 표시 시 rate_min~rate_max 범위 병기

    if eligible:
        reason = f"{cat} 기준 소득요건 충족(≤{income_cap:,}), 한도 {limit:,}"
    else:
        reason = "디딤돌 자격 미충족(소득·무주택·순자산 확인)"
    return PolicyResult(eligible, limit if eligible else 0, rate, reason)


def buttimok_youth_eligibility(
    *,
    age: int,
    annual_income: int,
    deposit: int,
    net_asset: int,
    is_local: bool = False,
    rules: dict | None = None,
) -> PolicyResult:
    b = (rules or read_yaml("policy_loans.yaml"))["buttimok_youth"]

    in_age = b["age"]["min"] <= age <= b["age"]["max"]
    eligible = (
        in_age and annual_income <= b["income_cap"] and deposit <= b["deposit_cap"] and net_asset <= b["net_asset_cap"]
    )

    # 소득 구간별 금리 (오름차순 upto 매칭)
    rate = b["rate_by_income"][-1]["rate"]
    for tier in b["rate_by_income"]:
        if annual_income <= tier["upto"]:
            rate = tier["rate"]
            break
    if is_local:
        rate = max(b["rate_floor"], rate - b["local_discount"])

    reason = (
        f"청년(만{b['age']['min']}~{b['age']['max']}) 소득 {annual_income:,} 기준 금리 {rate:.2%}"
        if eligible
        else "버팀목 청년전세 자격 미충족(나이·소득·보증금 확인)"
    )
    return PolicyResult(eligible, b["limit"] if eligible else 0, rate, reason)
