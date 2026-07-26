"""refresh 정규화 로직 — 실 API 호출 없이 수집분 샘플로 검증."""

from scripts.refresh.refresh_deals import normalize_rows, parse_won


def test_parse_won():
    assert parse_won("82,500") == 825_000_000  # 만원 → 원
    assert parse_won(" 1,000 ") == 10_000_000
    assert parse_won("80") == 800_000
    assert parse_won(None) == 0
    assert parse_won("") == 0
    assert parse_won("N/A") == 0


def test_normalize_sale():
    recs = [{"법정동": " 합정동 ", "거래금액": "82,500", "전용면적": 84.9}]
    rows = normalize_rows(recs, "11440", "202605", "sale")
    assert rows == [
        {
            "sigungu_code": "11440",
            "umd_name": "합정동",
            "trade_type": "sale",
            "house_type": "아파트",
            "price": 825_000_000,
            "monthly": 0,
            "area_m2": 84.9,
            "deal_ym": "202605",
        }
    ]


def test_normalize_house_type_passthrough():
    recs = [{"법정동": "길음동", "거래금액": "50,000", "전용면적": 39.6}]
    rows = normalize_rows(recs, "11290", "202605", "sale", house_type="연립다세대")
    assert rows[0]["house_type"] == "연립다세대"


def test_normalize_rent_splits_jeonse_monthly():
    recs = [
        {"법정동": "망원동", "보증금액": "50,000", "월세금액": "80", "전용면적": 59.9},  # 월세
        {"법정동": "망원동", "보증금액": "220,000", "월세금액": "0", "전용면적": 84.9},  # 전세
    ]
    rows = normalize_rows(recs, "11440", "202605", "rent")
    monthly = next(r for r in rows if r["trade_type"] == "monthly")
    jeonse = next(r for r in rows if r["trade_type"] == "jeonse")
    assert monthly["price"] == 500_000_000 and monthly["monthly"] == 800_000
    assert jeonse["price"] == 2_200_000_000 and jeonse["monthly"] == 0


def test_normalize_skips_bad_rows():
    recs = [{"법정동": "", "거래금액": "50,000"}, {"법정동": "합정동", "거래금액": "0"}]
    assert normalize_rows(recs, "11440", "202605", "sale") == []
