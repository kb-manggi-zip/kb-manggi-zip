"""소비 성향 '실측 override' — 개인 실측(mydata)이 세그먼트 통계를 덮어쓰는 2위 증거. 결정론(LLM 아님).

증거 위계: 1위 본인 진술+HITL(구현: agents/clarify.py::note_values_food, 배선: tools/persona.py::scoring_ctx)
         / 2위 개인 실측(여기) / 3위 세그먼트 통계(spending_profiles).
개인 카테고리 비중 ÷ 또래 평균(rules/consumption_baseline.yaml)이 임계(±30%)를 넘으면 성향 override + 근거 문장.
mydata 없으면 {} (세그먼트 값 유지). compare 미접촉.
"""

from typing import Optional

from ..agents import spend_query
from ..core.rules import read_yaml

_BASELINE_FILE = "consumption_baseline.yaml"


def aggregate_category_ratio(persona_id: str, *, db_path: Optional[str] = None) -> dict:
    """mydata 3개월 카테고리 비중(총지출 대비). 가드레일 쿼리로 조회."""
    total = spend_query._std_scalar("SELECT SUM(amount) FROM transactions WHERE persona_id=:pid", persona_id, db_path)
    if total <= 0:
        return {}
    rows = spend_query.guarded_execute(
        "SELECT category, SUM(amount) FROM transactions WHERE persona_id=:pid GROUP BY category",
        persona_id,
        db_path=db_path,
    )
    return {c: (a or 0) / total for c, a in rows}


def derive_personal_traits(persona_id: str, *, db_path: Optional[str] = None) -> dict:
    """{category: {level, reason, ratio}} — 또래 대비 편차 큰 카테고리만. 없으면 {}(세그먼트 유지)."""
    b = read_yaml(_BASELINE_FILE)
    hi, lo, base = b["threshold_high"], b["threshold_low"], b["baseline_ratio"]
    try:
        personal = aggregate_category_ratio(persona_id, db_path=db_path)
    except spend_query.GuardrailError:
        return {}  # mydata 없음 → override 없음
    if not personal:
        return {}
    overrides: dict = {}
    for cat, bratio in base.items():
        if bratio <= 0:
            continue
        ratio = personal.get(cat, 0.0) / bratio
        if ratio >= hi:
            overrides[cat] = {
                "level": "high",
                "ratio": round(ratio, 2),
                "reason": f"최근 3개월 {cat} 지출이 또래 평균의 {ratio:.1f}배",
            }
        elif ratio <= lo:
            overrides[cat] = {
                "level": "low",
                "ratio": round(ratio, 2),
                "reason": f"{cat} 지출이 또래 평균의 {ratio:.1f}배 수준",
            }
        # 0.7~1.3 은 세그먼트 값 유지(노이즈 미반영)
    return overrides


# 소비 성향 → 상권 매치(values_food)에 영향 주는 카테고리
_FOOD_CATS = ("카페", "배달", "식비")


def values_food_override(overrides: dict) -> Optional[bool]:
    """실측 override가 식음료 소비 성향을 뒤집으면 True/False, 아니면 None(세그먼트 유지)."""
    if any(overrides.get(c, {}).get("level") == "high" for c in _FOOD_CATS):
        return True
    if (
        overrides
        and all(overrides.get(c, {}).get("level") == "low" for c in _FOOD_CATS if c in overrides)
        and any(c in overrides for c in _FOOD_CATS)
    ):
        return False
    return None


def values_leisure_override(overrides: dict) -> Optional[bool]:
    """실측 override의 '여가' 카테고리로 여가 성향 판정. values_food_override와 동일 패턴(단일 카테고리)."""
    level = overrides.get("여가", {}).get("level")
    if level == "high":
        return True
    if level == "low":
        return False
    return None
