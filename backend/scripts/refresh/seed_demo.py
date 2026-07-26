"""데모 스냅샷 생성 → data/trades.demo.db.

⚠️ 합성(SYNTHETIC) 데이터. 실 API 키가 없을 때/네트워크 없이 데모·테스트를 돌리기 위한 seed.
실데이터 확보 시:  python scripts/refresh/refresh_deals.py  →  cp data/trades.db data/trades.demo.db
로 교체할 것. (숫자는 region_enrich 데모 동의 대략적 시세 중심의 난수)

실행:  python scripts/refresh/seed_demo.py
"""

import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # backend/

from app.tools import molit, trades_store  # noqa: E402
from scripts.refresh.refresh_deals import sanity_check, summarize  # noqa: E402

# (sigungu_code, 동명, 매매가 중심) — 아파트 매매
SALE = [
    ("11440", "합정동", 530_000_000),
    ("11380", "녹번동", 490_000_000),
    ("11320", "창동", 430_000_000),
]
# 전세보증금 중심
JEONSE = [
    ("11290", "길음동", 290_000_000),
    ("11350", "상계동", 260_000_000),
    ("11260", "면목동", 230_000_000),
]
# (보증금 중심, 월세 중심) — 월세
MONTHLY = [
    ("11440", "망원동", 72_000_000, 1_950_000),
    ("11290", "보문동", 55_000_000, 1_700_000),
    ("11260", "면목동", 60_000_000, 1_800_000),
]

AREAS = [59.9, 74.9, 84.9]
VILLA_AREAS = [29.9, 39.6, 49.5]  # 연립다세대는 아파트보다 소형 위주(원룸~투룸)
VILLA_PRICE_RATIO = 0.65  # 같은 동네 기준 연립다세대는 아파트 대비 대략 낮은 가격대(합성 근사)
PER_DONG = 40  # 동별 합성 거래 수


def _rows(rng, sigungu, umd, tt, price_c, deal_ym, monthly_c=0, house_type="아파트"):
    areas = VILLA_AREAS if house_type == "연립다세대" else AREAS
    out = []
    for _ in range(PER_DONG):
        price = int(price_c * (1 + rng.gauss(0, 0.06)))
        mon = int(monthly_c * (1 + rng.gauss(0, 0.08))) if monthly_c else 0
        out.append(
            {
                "sigungu_code": sigungu,
                "umd_name": umd,
                "trade_type": tt,
                "house_type": house_type,
                "price": price,
                "monthly": mon,
                "area_m2": rng.choice(areas),
                "deal_ym": deal_ym,
            }
        )
    return out


def run() -> None:
    rng = random.Random(42)
    months = molit.recent_year_months(6)
    db_path = str(trades_store.DEMO_DB)
    conn = trades_store.connect(db_path)
    conn.execute("DELETE FROM trades")  # seed 는 권위적: 통째로 재생성
    conn.commit()
    t0 = time.time()

    # 매매 (아파트 + 연립다세대)
    for sig, umd, pc in SALE:
        for ym in months:
            trades_store.replace_batch(conn, sig, ym, "sale", _rows(rng, sig, umd, "sale", pc, ym))
            villa_rows = _rows(rng, sig, umd, "sale", int(pc * VILLA_PRICE_RATIO), ym, house_type="연립다세대")
            trades_store.replace_batch(conn, sig, ym, "sale", villa_rows, house_type="연립다세대")
    # 전세 (아파트 + 연립다세대)
    for sig, umd, pc in JEONSE:
        for ym in months:
            trades_store.replace_batch(conn, sig, ym, "jeonse", _rows(rng, sig, umd, "jeonse", pc, ym))
            villa_rows = _rows(rng, sig, umd, "jeonse", int(pc * VILLA_PRICE_RATIO), ym, house_type="연립다세대")
            trades_store.replace_batch(conn, sig, ym, "jeonse", villa_rows, house_type="연립다세대")
    # 월세 (아파트 + 연립다세대)
    for sig, umd, dc, mc in MONTHLY:
        for ym in months:
            trades_store.replace_batch(conn, sig, ym, "monthly", _rows(rng, sig, umd, "monthly", dc, ym, monthly_c=mc))
            villa_rows = _rows(
                rng, sig, umd, "monthly", int(dc * VILLA_PRICE_RATIO), ym, monthly_c=mc, house_type="연립다세대"
            )
            trades_store.replace_batch(conn, sig, ym, "monthly", villa_rows, house_type="연립다세대")

    print("── 데모 스냅샷 (SYNTHETIC) ──")
    sanity_check(conn, set(months))
    summarize(conn, time.time() - t0, failures=[])
    conn.close()
    print(f"\n✓ {db_path} 생성 (합성 데이터 — 실데이터로 교체 권장)")


if __name__ == "__main__":
    run()
