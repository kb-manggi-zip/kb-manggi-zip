"""중개보수 — 서울시 조례 구간표 조회 (B1.5 리서치 반영, 순수).

[거래금액 구간] → 상한요율×한도액. rules/one_time.yaml의 broker_rate_bands 사용.
"""

from ..core.rules import read_yaml


def _band(amount: float, bands: list[dict]) -> dict:
    for b in bands:
        if b["upto"] is None or amount < b["upto"]:
            return b
    return bands[-1]


def broker_fee(amount: float, *, bands: list[dict] | None = None) -> float:
    """구간별 상한요율 × 거래금액, 한도액 있으면 상한 적용."""
    t = bands or read_yaml("one_time.yaml")["broker_rate_bands"]["bands"]
    band = _band(amount, t)
    fee = amount * band["rate"]
    return min(fee, band["cap"]) if band.get("cap") is not None else fee
