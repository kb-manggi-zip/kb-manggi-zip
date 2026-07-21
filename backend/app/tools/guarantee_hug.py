"""HUG 반환보증 보증료 — 3중 테이블 조회 (B1.5 리서치 반영, 순수).

[보증금 구간][주택유형][부채비율] → 요율. rules/guarantee_hug.yaml 사용.
월환산 = 보증금 × 요율 / 12 (계약일수와 무관하게 동일).
"""
from ..core.rules import read_yaml


def _band(deposit: int) -> str:
    if deposit <= 90_000_000:
        return "under_90m"
    if deposit <= 200_000_000:
        return "m90_to_200m"
    return "over_200m"


def guarantee_rate(
    deposit: int,
    *,
    house_type: str | None = None,
    debt_ratio: str | None = None,
    rules: dict | None = None,
) -> float:
    """[보증금 구간][주택유형][부채비율] → 연 보증료율."""
    g = rules or read_yaml("guarantee_hug.yaml")
    ht = house_type or g["default_house_type"]
    dr = debt_ratio or g["default_debt_ratio"]
    return g["hug_fee_rate"][_band(deposit)][ht][dr]


def calc_guarantee_fee(
    deposit: int,
    *,
    house_type: str | None = None,
    debt_ratio: str | None = None,
    rules: dict | None = None,
) -> dict:
    g = rules or read_yaml("guarantee_hug.yaml")
    ht = house_type or g["default_house_type"]
    dr = debt_ratio or g["default_debt_ratio"]
    rate = guarantee_rate(deposit, house_type=ht, debt_ratio=dr, rules=g)

    annual_fee = int(deposit * rate)
    return {
        "rate": rate,
        "annual_fee": annual_fee,
        "monthly_equiv": int(deposit * rate / 12),
        "basis": "HUG 공시 요율 (보증금액×보증료율×계약일수/365)",
        "assumption": f"{ht} · 부채비율 {dr} 가정",
    }
