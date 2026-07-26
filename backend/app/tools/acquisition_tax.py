"""취득세 — 지방세법 제11조 1항 8호 구간 조회 (B1.5 리서치 반영, 순수).

주택 유상거래, 85㎡ 이하 가정(농특세 면제). 지방교육세는 지방세법 제151조 1항 1호 단서에
따라 취득세율의 1/2×20%(=10%)로 계산돼, 합산 실효세율 = 취득세율 × (1+edu_tax_ratio).
rules/one_time.yaml의 acquisition 사용.
"""

from ..core.rules import read_yaml
from .format import js_round


def _base_rate(price: float, a: dict) -> float:
    """가·나·다 3단계 — 6억 이하/6~9억 선형/9억 초과."""
    if price <= a["low_threshold"]:
        return a["low_rate"]
    if price > a["high_threshold"]:
        return a["high_rate"]
    raw_percent = price / 300_000_000 * 2 - 3
    rounded_percent = js_round(raw_percent * 10000) / 10000  # 소수점 다섯째자리 반올림, 넷째자리까지
    return rounded_percent / 100


def acquisition_fee(price: float, *, rules: dict | None = None) -> float:
    """취득세 + 지방교육세 합산 실효 부담액."""
    a = rules or read_yaml("one_time.yaml")["acquisition"]
    base = _base_rate(price, a)
    return price * base * (1 + a["edu_tax_ratio"])
