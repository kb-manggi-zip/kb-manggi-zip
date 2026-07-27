"""전세가율 리스크 지표 — 실거래 나눗셈(예측 아님). 구간 경계·표본부족·손계산 대조."""

from datetime import date

from app.tools import jeonse_ratio as jr


# ── 구간 판정 (경계) ──────────────────────────────────────────────
def test_classify_band_boundaries():
    assert jr.classify_band(0.70)["level"] == "safe"  # ≤0.70
    assert jr.classify_band(0.7001)["level"] == "caution"  # 0.70 초과
    assert jr.classify_band(0.90)["level"] == "caution"  # ≤0.90
    assert jr.classify_band(0.9001)["level"] == "alert"  # 0.90 초과
    assert jr.classify_band(1.20)["level"] == "alert"


# ── 표본 부족 → None (지어내지 않음) ──────────────────────────────
def test_sample_shortage_returns_none(monkeypatch):
    monkeypatch.setattr(jr.trades_store, "sale_prices", lambda *a, **k: [500_000_000] * 4)  # 4건<5
    assert jr.jeonse_ratio(400_000_000, "테스트동") is None


def test_deposit_zero_returns_none():
    assert jr.jeonse_ratio(0, "테스트동") is None


# ── 손계산 대조 ───────────────────────────────────────────────────
def test_ratio_hand_calc(monkeypatch):
    # 매매 5건 중위 5억, 보증금 4.35억 → 0.87 = caution
    monkeypatch.setattr(
        jr.trades_store,
        "sale_prices",
        lambda *a, **k: [460_000_000, 480_000_000, 500_000_000, 520_000_000, 540_000_000],
    )
    r = jr.jeonse_ratio(435_000_000, "합정동")
    assert r["saleMedian"] == 500_000_000
    assert r["sampleCount"] == 5
    assert r["ratio"] == 0.87
    assert r["band"] == "caution"
    assert "합정동" in r["basis"] and "5건" in r["basis"]


def test_safe_band(monkeypatch):
    monkeypatch.setattr(jr.trades_store, "sale_prices", lambda *a, **k: [1_000_000_000] * 6)
    r = jr.jeonse_ratio(600_000_000, "성수동")  # 0.60
    assert r["band"] == "safe" and r["ratio"] == 0.6


def test_since_ym_window():
    # 2026-07 기준 최근 6개월 창 시작 = 202602
    assert jr._since_ym(6, today=date(2026, 7, 15)) == "202602"
    assert jr._since_ym(1, today=date(2026, 7, 15)) == "202607"
