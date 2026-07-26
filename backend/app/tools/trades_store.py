"""실거래 저장 계층 (SQLite).

- 서버 런타임은 이 DB에서만 읽는다 (외부 API 미접촉 = 데모 안정성).
- 쓰기는 scripts/refresh/ (refresh_deals·seed_demo) 에서만.
- DB 우선순위: TRADES_DB env > data/trades.db(실데이터) > data/trades.demo.db(커밋 스냅샷).
- 스키마: trades(sigungu_code, umd_name, trade_type, house_type, price, monthly, area_m2, deal_ym, collected_at)
  · trade_type: 'sale'(매매) | 'jeonse'(전세) | 'monthly'(월세)
  · house_type: '아파트' | '연립다세대' (국토부 API property_type 값 그대로) — 기본값 '아파트'(기존 데이터 호환)
  · price/monthly = 원(KRW). 매매·전세는 monthly=0.
  · 멱등: (sigungu, deal_ym, trade_type, house_type) 배치 단위 DELETE 후 INSERT.
"""

import json
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
    collected_at TEXT NOT NULL,
    house_type   TEXT NOT NULL DEFAULT '아파트'
);
CREATE INDEX IF NOT EXISTS ix_trades_type ON trades(trade_type);
CREATE INDEX IF NOT EXISTS ix_trades_batch ON trades(sigungu_code, deal_ym, trade_type, house_type);

CREATE TABLE IF NOT EXISTS region_facts (
    region_id    TEXT NOT NULL,          -- 프론트 Region.id (예: mapo-m)
    field        TEXT NOT NULL,          -- grocery | dining_cafe | leisure ...
    value_json   TEXT NOT NULL,          -- JSON 문자열 리스트 (예: ["음식점·카페 45곳"])
    count        INTEGER NOT NULL DEFAULT 0,
    source       TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    PRIMARY KEY (region_id, field)
);
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
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """CREATE TABLE IF NOT EXISTS는 기존 DB엔 새 컬럼을 안 만들어주므로 수동 보강."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(trades)")}
    if "house_type" not in cols:
        conn.execute("ALTER TABLE trades ADD COLUMN house_type TEXT NOT NULL DEFAULT '아파트'")
        conn.commit()


def replace_batch(
    conn: sqlite3.Connection,
    sigungu_code: str,
    deal_ym: str,
    trade_type: str,
    rows: list[dict],
    house_type: str = "아파트",
) -> int:
    """(sigungu, deal_ym, trade_type, house_type) 배치 교체 — 재실행해도 중복 없음."""
    collected_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "DELETE FROM trades WHERE sigungu_code=? AND deal_ym=? AND trade_type=? AND house_type=?",
        (sigungu_code, deal_ym, trade_type, house_type),
    )
    conn.executemany(
        """INSERT INTO trades
           (sigungu_code, umd_name, trade_type, house_type, price, monthly, area_m2, deal_ym, collected_at)
           VALUES (:sigungu_code, :umd_name, :trade_type, :house_type,
                   :price, :monthly, :area_m2, :deal_ym, :collected_at)""",
        [{**r, "house_type": house_type, "collected_at": collected_at} for r in rows],
    )
    conn.commit()
    return len(rows)


def read_trades(
    trade_type: str,
    *,
    db_path: Optional[str] = None,
    sigungu_code: Optional[str] = None,
    deal_ym: Optional[str] = None,
    house_type: Optional[str] = None,
) -> list[dict]:
    """trade_type 의 정규화 거래 읽기 (aggregate 입력용 TradeRow shape). house_type 미지정 시 전체(아파트+빌라)."""
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
        q = "SELECT umd_name, price, monthly, area_m2, deal_ym, house_type FROM trades WHERE trade_type=?"
        params: list = [trade_type]
        if sigungu_code:
            q += " AND sigungu_code=?"
            params.append(sigungu_code)
        if deal_ym:
            q += " AND deal_ym=?"
            params.append(deal_ym)
        if house_type:
            q += " AND house_type=?"
            params.append(house_type)
        cur = conn.execute(q, params)
        rows = [
            {"umd_name": u, "price": p, "monthly": m, "area_m2": a, "deal_ym": ym, "house_type": ht}
            for (u, p, m, a, ym, ht) in cur.fetchall()
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


# ── 지역 상권 데이터(발품 그라운딩용) ──────────────────────────────────
def write_region_facts(
    region_id: str,
    field: str,
    values: list[str],
    count_n: int,
    source: str,
    *,
    db_path: Optional[str] = None,
) -> None:
    """region_facts 한 행 저장(멱등: PK(region_id, field) INSERT OR REPLACE)."""
    path = db_path or resolve_db_path(write=True)
    conn = connect(path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO region_facts "
            "(region_id, field, value_json, count, source, collected_at) VALUES (?,?,?,?,?,?)",
            (
                region_id,
                field,
                json.dumps(values, ensure_ascii=False),
                count_n,
                source,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def read_region_facts(region_id: str, *, db_path: Optional[str] = None) -> dict:
    """region_id → {field: [값 문자열...]} (DB 없거나 없으면 {})."""
    path = db_path or resolve_db_path(write=False)
    if not path or not Path(path).exists():
        return {}
    conn = connect(path)
    try:
        rows = conn.execute("SELECT field, value_json FROM region_facts WHERE region_id=?", (region_id,)).fetchall()
    finally:
        conn.close()
    return {field: json.loads(vj) for field, vj in rows}


def sample_trade(umd_name: str, trade_type: str, *, db_path: Optional[str] = None) -> Optional[dict]:
    """동+거래유형의 '중위가에 가장 가까운 실거래 1건' (발품 근거용, 국토부 실데이터).

    반환 {price, monthly, area_m2, deal_ym} 또는 None. (아웃라이어 대신 대표 사례)
    """
    path = db_path or resolve_db_path(write=False)
    if not path or not Path(path).exists():
        return None
    conn = connect(path)
    try:
        rows = conn.execute(
            "SELECT price, monthly, area_m2, deal_ym FROM trades WHERE umd_name=? AND trade_type=? AND price>0",
            (umd_name, trade_type),
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        return None
    mid = sorted(r[0] for r in rows)[len(rows) // 2]  # 중위가
    best = min(rows, key=lambda r: abs(r[0] - mid))  # 중위가에 가장 가까운 실사례
    return {"price": best[0], "monthly": best[1], "area_m2": best[2], "deal_ym": best[3]}
