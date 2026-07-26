"""실거래 집계 파이프라인 — 동별 중위가·거래건수·예산필터·상위3.

fetch_trades(실 API)는 STUB이지만, 그 뒤 aggregate_to_regions는 완성이라 여기서 검증한다.
(실 API 붙으면 fetch_trades가 아래 TradeRow[]를 채워주기만 하면 됨)
"""

from app.tools.molit import TradeRow, aggregate_to_regions


def _rows() -> list[TradeRow]:
    return [
        {"umd_name": "합정동", "price": 500_000_000, "monthly": 0},
        {"umd_name": "합정동", "price": 520_000_000, "monthly": 0},
        {"umd_name": "합정동", "price": 900_000_000, "monthly": 0},  # 예산 초과 후보(중위는 이내)
        {"umd_name": "망원동", "price": 300_000_000, "monthly": 0},
        {"umd_name": "망원동", "price": 320_000_000, "monthly": 0},
        {"umd_name": "성산동", "price": 800_000_000, "monthly": 0},  # 예산 초과 → 제외
    ]


def test_aggregate_median_and_count():
    regions = aggregate_to_regions(_rows(), "매매", budget=0)  # 필터 없음
    by = {r.name: r for r in regions}
    assert by["합정동"].midPrice == 520_000_000  # median(500,520,900)
    assert by["합정동"].tradeCount == 3
    assert by["망원동"].midPrice == 310_000_000  # median(300,320)


def test_budget_filter_and_top_and_surplus():
    budget = 600_000_000
    regions = aggregate_to_regions(_rows(), "매매", budget=budget)
    names = [r.name for r in regions]
    assert "성산동" not in names  # midPrice 800M > 예산 → 제외
    assert names[0] == "합정동"  # 예산 근접(surplus 80M < 망원동 290M) → 첫번째
    top = regions[0]
    assert top.surplus == budget - top.midPrice
    assert len(regions) <= 3


def test_monthly_mid_price():
    rows: list[TradeRow] = [
        {"umd_name": "망원동", "price": 70_000_000, "monthly": 1_900_000},
        {"umd_name": "망원동", "price": 74_000_000, "monthly": 2_000_000},
    ]
    regions = aggregate_to_regions(rows, "이사", budget=0, monthly=True)
    assert regions[0].monthlyMidPrice == 1_950_000
    assert regions[0].branch == "이사"


def test_enrichment_join():
    enrich = {"합정동": {"id": "mapo", "lat": 37.5498, "lng": 126.9137, "tags": ["역세권"]}}
    regions = aggregate_to_regions(
        [{"umd_name": "합정동", "price": 500_000_000, "monthly": 0}],
        "매매",
        budget=0,
        enrich=enrich,
    )
    assert regions[0].id == "mapo"
    assert regions[0].lat == 37.5498
    assert regions[0].tags == ["역세권"]
