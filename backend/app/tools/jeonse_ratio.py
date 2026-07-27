"""전세가율 리스크 지표 — 실거래 나눗셈(예측·ML 아님).

전세가율 = 보증금 ÷ 같은 동 유사평형 매매 중위가 (trades.db 실거래).
구간(rules/jeonse_ratio.yaml)으로 판정 — HUG 담보인정비율 90% 제도 사실 기반 **안내**(위험 예측 아님).
표본 <5건이면 None → 지표 미표시(근사·추정 금지).
"""

from datetime import date
from statistics import median
from typing import Optional

from ..core.rules import read_yaml
from . import trades_store

_MIN_SAMPLE = 5
_RULES_FILE = "jeonse_ratio.yaml"


def _since_ym(months: int, today: Optional[date] = None) -> str:
    """최근 months개월의 시작 'YYYYMM' (today 포함 months개월 창)."""
    today = today or date.today()
    y, m = today.year, today.month
    for _ in range(months - 1):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return f"{y}{m:02d}"


def classify_band(ratio: float, rules: Optional[dict] = None) -> dict:
    """ratio → {level, label}. rules 미지정 시 yaml 로드."""
    bands = (rules or read_yaml(_RULES_FILE))["bands"]
    for b in bands:
        if ratio <= b["max"]:
            return {"level": b["level"], "label": b["label"]}
    last = bands[-1]
    return {"level": last["level"], "label": last["label"]}


def jeonse_ratio(
    deposit: int,
    umd_name: str,
    area_m2: Optional[float] = None,
    *,
    months: int = 6,
    today: Optional[date] = None,
    rules: Optional[dict] = None,
    db_path: Optional[str] = None,
) -> Optional[dict]:
    """전세가율 = deposit ÷ (같은 동 유사평형 매매 중위가). 표본<5 → None.

    area_m2 주면 ±20% 유사평형으로 필터, 없으면 동 전체 평형. 최근 months개월.
    반환: {ratio, saleMedian, sampleCount, band, label, basis} 또는 None.
    """
    if deposit <= 0:
        return None
    area_lo = area_hi = None
    if area_m2:
        area_lo, area_hi = area_m2 * 0.8, area_m2 * 1.2
    prices = trades_store.sale_prices(
        umd_name, area_lo=area_lo, area_hi=area_hi, since_ym=_since_ym(months, today), db_path=db_path
    )
    if len(prices) < _MIN_SAMPLE:
        return None
    sale_median = int(median(sorted(prices)))
    if sale_median <= 0:
        return None
    ratio = deposit / sale_median
    band = classify_band(ratio, rules)
    area_note = "유사평형(±20%) " if area_m2 else ""
    return {
        "ratio": round(ratio, 3),
        "saleMedian": sale_median,
        "sampleCount": len(prices),
        "band": band["level"],
        "label": band["label"],
        "basis": f"최근 {months}개월 {umd_name} {area_note}매매 {len(prices)}건 중위가 기준",
    }
