"""실거래 저장 계층 (SQLite).

- 서버 런타임은 이 DB에서만 읽는다 (외부 API 미접촉 = 데모 안정성).
- 쓰기는 scripts/refresh/ (refresh_deals·seed_demo) 에서만.
- DB 우선순위: TRADES_DB env > data/trades.db(실데이터) > data/trades.demo.db(커밋 스냅샷).
- 스키마: trades(sigungu_code, umd_name, trade_type, price, monthly, area_m2, deal_ym, collected_at)
  · trade_type: 'sale'(매매) | 'jeonse'(전세) | 'monthly'(월세)
  · price/monthly = 원(KRW). 매매·전세는 monthly=0.
  · 멱등: (sigungu, deal_ym, trade_type) 배치 단위 DELETE 후 INSERT.
"""
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..core.config import BACKEND_ROOT

DATA_DIR = BACKEND_ROOT / "data"
REAL_DB = DATA_DIR / "trades.db"
DEMO_DB = DATA_DIR / "trades.demo.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sigungu_code TEXT NOT NULL,
    umd_name     TEXT NOT NULL,
    trade_type   TEXT NOT NULL,
    price        INTEGER NOT NULL,
    monthly      INTEGER NOT NULL DEFAULT 0,
    area_m2      REAL,
    deal_ym      TEXT NOT NULL,
    collected_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_trades_type ON trades(trade_type);
CREATE INDEX IF NOT EXISTS ix_trades_batch ON trades(sigungu_code, deal_ym, trade_type);
"""


def resolve_db_path(write: bool = False) -> Optional[str]:
    """읽기: env > 실DB > 데모DB. 쓰기: env > 실DB(기본)."""
    env = os.environ.get("TRADES_DB")
    if env:
        return env
    if write:
        return str(REAL_DB)
    if REAL_DB.exists():
        return str(REAL_DB)
    if DEMO_DB.exists():
        return str(DEMO_DB)
    return None


def connect(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def replace_batch(
    conn: sqlite3.Connection,
    sigungu_code: str,
    deal_ym: str,
    trade_type: str,
    rows: list[dict],
) -> int:
    """(sigungu, deal_ym, trade_type) 배치 교체 — 재실행해도 중복 없음."""
    collected_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "DELETE FROM trades WHERE sigungu_code=? AND deal_ym=? AND trade_type=?",
        (sigungu_code, deal_ym, trade_type),
    )
    conn.executemany(
        """INSERT INTO trades
           (sigungu_code, umd_name, trade_type, price, monthly, area_m2, deal_ym, collected_at)
           VALUES (:sigungu_code, :umd_name, :trade_type, :price, :monthly, :area_m2, :deal_ym, :collected_at)""",
        [{**r, "collected_at": collected_at} for r in rows],
    )
    conn.commit()
    return len(rows)


def read_trades(
    trade_type: str,
    *,
    db_path: Optional[str] = None,
    sigungu_code: Optional[str] = None,
    deal_ym: Optional[str] = None,
) -> list[dict]:
    """trade_type 의 정규화 거래 읽기 (aggregate 입력용 TradeRow shape)."""
    path = db_path or resolve_db_path(write=False)
    if not path or not Path(path).exists():
        raise RuntimeError(
            "실거래 DB가 없습니다. 먼저 실거래를 수집하세요:\n"
            "  python scripts/refresh/refresh_deals.py   (실 API 키 필요)\n"
            "또는 데모 스냅샷 생성:\n"
            "  python scripts/refresh/seed_demo.py"
        )
    conn = connect(path)
    try:
        q = "SELECT umd_name, price, monthly, area_m2, deal_ym FROM trades WHERE trade_type=?"
        params: list = [trade_type]
        if sigungu_code:
            q += " AND sigungu_code=?"
            params.append(sigungu_code)
        if deal_ym:
            q += " AND deal_ym=?"
            params.append(deal_ym)
        cur = conn.execute(q, params)
        rows = [
            {"umd_name": u, "price": p, "monthly": m, "area_m2": a, "deal_ym": ym}
            for (u, p, m, a, ym) in cur.fetchall()
        ]
    finally:
        conn.close()
    if not rows:
        raise RuntimeError(
            f"실거래 DB에 '{trade_type}' 데이터가 없습니다 (path={path}). "
            "refresh_deals.py 또는 seed_demo.py 를 먼저 실행하세요."
        )
    return rows


def count(db_path: Optional[str] = None) -> int:
    path = db_path or resolve_db_path(write=False)
    if not path or not Path(path).exists():
        return 0
    conn = connect(path)
    try:
        return conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    finally:
        conn.close()
