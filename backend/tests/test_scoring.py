"""개인화 스코어 — 통계근거 가중치(임의 아님) + 축별 점수 + 재정렬."""

from app.tools import scoring, trades_store


def test_weights_derived_from_survey():
    w = scoring.derive_weights()
    assert abs(sum(w.values()) - 1.0) < 0.01
    assert w["commute"] == 0.405  # 0.306 / 0.755 (W1: 4축 전부 <표10> 원문 30.6/25.5/8.3/11.1 정규화)
    # 통계에서 '계산'됨(하드코딩 아님) 증명
    assert scoring.derive_weights({"a": 1, "b": 3}) == {"a": 0.25, "b": 0.75}


def test_persona_weights_differ_with_evidence():
    y = scoring.weights_for("1인")  # 청년의삶: 통근 39.2% 1위 → commute↑
    n = scoring.weights_for("신혼")  # 주거실태 표36(주택구입자금) → budget↑ / 표10·11 실측 → commute↑
    assert y["commute"] > n["commute"]
    assert n["budget"] > y["budget"]


def test_axis_scores():
    assert scoring.score_commute(30) == 1.0
    assert scoring.score_commute(60) == 0.0
    assert scoring.score_commute(None) == 0.5
    assert scoring.score_preference(True) == 1.0
    assert scoring.score_preference(False) == 0.3
    assert 0 <= scoring.score_consumption(300, None, None, True, False, False) <= 1
    assert 0 <= scoring.score_consumption(300, 150, 20, True, True, True) <= 1
    assert scoring.score_consumption(None, None, None, True, True, True) == 0.5


def test_rank_reorders_by_commute_and_exposes_reason(tmp_path, monkeypatch):
    db = str(tmp_path / "t.db")
    trades_store.write_region_transit("A", "여의도(금융권)", 25, 0, False, db_path=db)
    trades_store.write_region_transit("B", "여의도(금융권)", 70, 2, False, db_path=db)
    monkeypatch.setenv("TRADES_DB", db)
    regions = [
        {"id": "A", "midPrice": 500_000_000, "surplus": 50_000_000},
        {"id": "B", "midPrice": 500_000_000, "surplus": 50_000_000},
    ]
    ctx = {
        "household": "신혼",
        "budget": 550_000_000,
        "workplace": "여의도(금융권)",
        "traits": [],
        "in_preferred": None,
    }
    ranked = scoring.rank(regions, ctx, top=2)
    assert ranked[0]["id"] == "A"  # 통근 25분 < 70분 → A 1위
    assert ranked[0]["score"] > ranked[1]["score"]
    assert any("통근" in r for r in ranked[0]["scoreReasons"])
