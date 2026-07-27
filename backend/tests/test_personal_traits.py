"""소비 성향 실측 override — 증거 위계 2위(개인 실측). 결정론, compare 미접촉."""

from app.tools import persona
from app.tools import personal_traits as pt


def test_p1_cafe_high_override():
    o = pt.derive_personal_traits("P1")
    assert o["카페"]["level"] == "high"  # 재택 1인 — 카페 실측 높음
    assert o["카페"]["ratio"] >= 1.3
    assert "또래 평균" in o["카페"]["reason"]


def test_uncrossed_category_keeps_segment():
    # 임계(0.7~1.3) 안이면 override 없음 → 세그먼트 값 유지
    o = pt.derive_personal_traits("P1")
    assert "식비" not in o  # P1 식비는 또래 평균 근처 → override 안 됨


def test_hand_calc_ratio():
    # P1 카페 비중 ÷ baseline(0.045) = 배수. 코드값과 손계산 일치.
    ratios = pt.aggregate_category_ratio("P1")
    from app.core.rules import read_yaml

    base = read_yaml("consumption_baseline.yaml")["baseline_ratio"]["카페"]
    expected = round(ratios["카페"] / base, 2)
    assert pt.derive_personal_traits("P1")["카페"]["ratio"] == expected


def test_values_food_override_by_persona():
    assert pt.values_food_override(pt.derive_personal_traits("P1")) is True  # 카페·배달 high
    assert pt.values_food_override(pt.derive_personal_traits("P2")) is False  # 카페·배달 low
    assert pt.values_food_override(pt.derive_personal_traits("P3")) is None  # 식음료 편차 없음 → 세그먼트 유지


def test_no_mydata_returns_empty():
    assert pt.derive_personal_traits("P1", db_path="/nonexistent.db") == {}


def test_persona_signals_have_sources():
    p = persona.build_persona({"note": "재택근무예요"}, {"household": "1인"}, persona_id="P1")
    sources = {s["source"] for s in p["consumptionSignals"]}
    assert "세그먼트" in sources and "실측" in sources  # 3위·2위 다 노출
    measured = [s for s in p["consumptionSignals"] if s["source"] == "실측"]
    assert any("카페" in s["label"] for s in measured)
    assert all(s.get("reason") for s in measured)  # 실측엔 근거 문장 필수


def test_scoring_ctx_reflects_override():
    ctx = persona.scoring_ctx({"note": ""}, {"household": "1인"}, 500_000_000, None, persona_id="P1")
    assert ctx.get("values_food") is True  # 실측이 스코어에 반영
