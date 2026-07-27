"""국토부 실거래 → 동네 후보 Region[].

파이프라인:  (오프라인) refresh_deals.py → SQLite(trades.db)
             (런타임)   fetch_trades(=DB 읽기) → aggregate_to_regions → Region[]

⚠️ 서버 런타임은 외부 API를 호출하지 않는다. DB(실데이터 or 데모 스냅샷)만 읽는다.
   실 API 호출은 scripts/refresh/refresh_deals.py 에서만.
"""

from datetime import date
from statistics import median
from typing import Optional, TypedDict

import yaml

from ..core.config import BACKEND_ROOT
from ..schemas import Branch, Region
from . import trades_store

# branch(문자열) → DB trade_type
_TRADE_TYPE = {"매매": "sale", "이사": "jeonse", "이사-월세": "monthly"}


class TradeRow(TypedDict):
    """정규화된 실거래 1건.

    price:   매매가 또는 전세보증금 (원)
    monthly: 월세 (원). 전세/매매는 0.
    """

    umd_name: str  # 법정동 이름 (예: '합정동')
    price: int
    monthly: int
    area_m2: float
    deal_ym: str  # 'YYYYMM'


class Enrichment(TypedDict, total=False):
    id: str
    lat: float
    lng: float
    tags: list[str]


def recent_year_months(n: int = 6, offset: int = 1, today: Optional[date] = None) -> list[str]:
    """실행 시점 기준 최근 n개월 'YYYYMM' (offset=1: 직전 월부터 — 당월은 데이터 부족)."""
    today = today or date.today()
    out = []
    y, m = today.year, today.month
    # offset 만큼 뒤로
    for _ in range(offset):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    for _ in range(n):
        out.append(f"{y}{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return out


def load_enrich() -> dict[str, Enrichment]:
    path = BACKEND_ROOT / "data" / "region_enrich.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def aggregate_to_regions(
    rows: list[TradeRow],
    branch: Branch,
    budget: int,
    *,
    monthly: bool = False,
    enrich: Optional[dict[str, Enrichment]] = None,
    top: int = 3,
) -> list[Region]:
    """실거래 → 동별 집계 → 예산 필터 → 예산 적합 순 상위 N.

    - midPrice = 동별 중위 price / monthlyMidPrice = 동별 중위 monthly(monthly=True)
    - surplus = budget - midPrice (budget>0 시 예산 이내만)
    - 정렬:
        · budget>0 → **surplus 오름차순**(예산에 가장 잘 맞는=예산으로 갈 수 있는 상위 동네).
          거래건수(유동성)로 tie-break. → 갈래(매매 sale / 전세 jeonse)마다 가격대가 달라
          후보 동네가 달라진다(거래건수만으로 정렬하면 대단지가 모든 갈래에 똑같이 뜨는 문제 해결).
        · budget=0 → 정보 없으니 tradeCount 내림차순(구 동작).
    """
    enrich = enrich or {}
    groups: dict[str, list[TradeRow]] = {}
    for r in rows:
        groups.setdefault(r["umd_name"], []).append(r)

    regions: list[Region] = []
    for umd, items in groups.items():
        mid = int(median(sorted(x["price"] for x in items)))
        monthly_mid = int(median(sorted(x["monthly"] for x in items))) if monthly else None
        e = enrich.get(umd, {})
        regions.append(
            Region(
                id=e.get("id", umd),
                name=umd,
                midPrice=mid,
                monthlyMidPrice=monthly_mid,
                surplus=budget - mid,
                tradeCount=len(items),
                tags=e.get("tags", []),
                lat=e.get("lat", 0.0),
                lng=e.get("lng", 0.0),
                branch=branch,
            )
        )

    if budget > 0:
        regions = [r for r in regions if r.midPrice <= budget]
        # 예산 근접(surplus 오름차순) → 예산으로 갈 수 있는 상위 동네. 유동성(tradeCount)로 tie-break.
        regions.sort(key=lambda r: (r.surplus, -r.tradeCount))
    else:
        regions.sort(key=lambda r: r.tradeCount, reverse=True)
    return regions[:top]


def fetch_trades(
    trade_type: str,
    *,
    sigungu_code: Optional[str] = None,
    deal_ym: Optional[str] = None,
    house_type: Optional[str] = None,
) -> list[TradeRow]:
    """정규화 실거래 읽기 — **DB에서만** (외부 API 미접촉).

    trade_type: 'sale' | 'jeonse' | 'monthly'
    house_type: '아파트' | '연립다세대' | None(전체 — 아파트+연립다세대 블렌드)
    DB 없거나 비면 명확한 에러(refresh 안내).
    """
    return trades_store.read_trades(  # type: ignore[return-value]
        trade_type, sigungu_code=sigungu_code, deal_ym=deal_ym, house_type=house_type
    )


def regions_by_branch(
    branch: str, budget: int, house_type: Optional[str] = None, sigungu: Optional[str] = None, top: int = 3
) -> list[Region]:
    """예산 필터된 동네 후보 상위 top. branch: '매매'|'이사'|'이사-월세'.

    house_type: '아파트' | '연립다세대' | None(전체 블렌드, 기본값).
    sigungu: 선호지역 시군구코드(예 '11440'=마포). None이면 6구 전체에서 추천.
    top: 후보 수 (개인화 스코어 재정렬 시 풀을 넓히려면 크게).
    """
    monthly = branch == "이사-월세"
    region_branch: Branch = "매매" if branch == "매매" else "이사"
    trade_type = _TRADE_TYPE.get(branch, "sale")

    rows = fetch_trades(trade_type, sigungu_code=sigungu, house_type=house_type)  # DB (없으면 RuntimeError)
    return aggregate_to_regions(rows, region_branch, budget, monthly=monthly, enrich=load_enrich(), top=top)
