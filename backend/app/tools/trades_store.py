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
import logging
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

CREATE TABLE IF NOT EXISTS region_transit (
    region_id    TEXT NOT NULL,          -- 프론트 Region.id
    workplace    TEXT NOT NULL,          -- 직장 라벨 (예: '여의도(금융권)')
    minutes      INTEGER NOT NULL,
    transfers    INTEGER,                -- 환승 횟수 (예상치는 NULL)
    estimated    INTEGER NOT NULL DEFAULT 0,  -- 1=직선거리 예상, 0=ODsay 실측
    collected_at TEXT NOT NULL,
    PRIMARY KEY (region_id, workplace)
);
"""


_log = logging.getLogger("trades_store")
_READ_DB_CHOICE: Optional[str] = None  # 읽기 DB 결정 메모이즈(매 read마다 COUNT 방지)


def _real_db_has_region_data() -> bool:
    """실DB(trades.db)가 통근/상권 데이터를 실제로 갖고 있나. 없으면 개인화가 조용히 죽으므로 체크."""
    try:
        con = sqlite3.connect(str(REAL_DB))
        n = con.execute("SELECT COUNT(*) FROM region_transit").fetchone()[0]
        con.close()
        return n > 0
    except Exception:
        return False


def _resolve_read_db() -> Optional[str]:
    """읽기 DB 선택 + 함정 가드. 결과를 1회 메모이즈하고 어느 DB를 읽는지 로그로 남긴다."""
    global _READ_DB_CHOICE
    if _READ_DB_CHOICE is not None:
        return _READ_DB_CHOICE or None
    if REAL_DB.exists():
        if _real_db_has_region_data():
            choice = str(REAL_DB)
        elif DEMO_DB.exists():
            # 가드: 실DB에 통근/상권이 비어 있으면 완전한 데모 DB로 폴백(조용히 넘어가지 않고 경고).
            _log.warning(
                "trades.db에 region_transit이 비어 있어 데모 DB로 폴백합니다 (개인화 통근/상권 보존). "
                "stale trades.db를 삭제하거나 refresh_regions로 채우세요. fallback=%s",
                DEMO_DB,
            )
            choice = str(DEMO_DB)
        else:
            choice = str(REAL_DB)
    elif DEMO_DB.exists():
        choice = str(DEMO_DB)
    else:
        choice = ""
    _log.info("실거래 DB 사용: %s", choice or "(없음)")
    _READ_DB_CHOICE = choice
    return choice or None


def _reset_read_db_cache() -> None:
    """테스트 전용 — 읽기 DB 결정 메모이즈 초기화."""
    global _READ_DB_CHOICE
    _READ_DB_CHOICE = None


def resolve_db_path(write: bool = False) -> Optional[str]:
    """읽기: env > 실DB(통근데이터 有) > 데모DB. 쓰기: env > 실DB(기본).

    읽기 시 실DB에 region_transit이 비어 있으면(=stale) 데모 DB로 폴백한다(경고 로그).
    """
    env = os.environ.get("TRADES_DB")
    if env:
        return env
    if write:
        return str(REAL_DB)
    return _resolve_read_db()


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
    """trade_type 의 정규화 거래 읽기 (aggregate 입력용 TradeRow shape).

    house_type 미지정 시 전체(아파트+연립다세대).
    """
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
        q = "SELECT umd_name, price, monthly, area_m2, deal_ym, house_type, sigungu_code FROM trades WHERE trade_type=?"
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
            {"umd_name": u, "price": p, "monthly": m, "area_m2": a, "deal_ym": ym, "house_type": ht, "sigungu_code": sg}
            for (u, p, m, a, ym, ht, sg) in cur.fetchall()
        ]
    finally:
        conn.close()
    if not rows:
        raise RuntimeError(
            f"실거래 DB에 '{trade_type}' 데이터가 없습니다 (path={path}). "
            "refresh_deals.py 또는 seed_demo.py 를 먼저 실행하세요."
        )
    return rows


def sale_prices(
    umd_name: str,
    *,
    area_lo: Optional[float] = None,
    area_hi: Optional[float] = None,
    since_ym: Optional[str] = None,
    db_path: Optional[str] = None,
) -> list[int]:
    """동의 매매 실거래 가격 목록 (전세가율 계산용). area(±범위)·최근개월(since_ym) 필터 옵션.

    DB 없거나 해당 조건 표본 없으면 [] (호출부가 표본 부족을 판단 → 지표 미표시). 지어내지 않는다.
    """
    path = db_path or resolve_db_path(write=False)
    if not path or not Path(path).exists():
        return []
    conn = connect(path)
    try:
        rows = conn.execute(
            "SELECT price, area_m2, deal_ym FROM trades WHERE umd_name=? AND trade_type='sale' AND price>0",
            (umd_name,),
        ).fetchall()
    finally:
        conn.close()
    out: list[int] = []
    for price, area, ym in rows:
        if area_lo is not None and area is not None and not (area_lo <= area <= area_hi):
            continue
        if since_ym and ym and ym < since_ym:  # 'YYYYMM' 문자열 비교
            continue
        out.append(int(price))
    return out


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


def read_region_fact_counts(region_id: str, *, db_path: Optional[str] = None) -> dict:
    """region_id → {field: count(정수)} (DB 없거나 없으면 {}).

    value_json은 사람이 읽는 문장(예: "반경 500m 내 마트·편의점 186곳")이라 문장 안 숫자를
    정규식으로 다시 뽑으면 500(반경) 같은 무관한 숫자를 잘못 집을 수 있음 — 저장 시 이미 확보한
    정수 count 컬럼을 직접 읽는다(2026-07-31, scoring.py의 정규식 오독 버그 수정 계기로 추가).
    """
    path = db_path or resolve_db_path(write=False)
    if not path or not Path(path).exists():
        return {}
    conn = connect(path)
    try:
        rows = conn.execute("SELECT field, count FROM region_facts WHERE region_id=?", (region_id,)).fetchall()
    finally:
        conn.close()
    return {field: n for field, n in rows}


def write_region_transit(
    region_id: str, workplace: str, minutes: int, transfers, estimated: bool, *, db_path: Optional[str] = None
) -> None:
    """통근시간 1건 저장(멱등 PK(region_id, workplace)). refresh에서만 호출(실 API)."""
    path = db_path or resolve_db_path(write=True)
    conn = connect(path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO region_transit "
            "(region_id, workplace, minutes, transfers, estimated, collected_at) VALUES (?,?,?,?,?,?)",
            (region_id, workplace, int(minutes), transfers, int(estimated), datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def read_region_transit(region_id: str, workplace: str, *, db_path: Optional[str] = None) -> Optional[dict]:
    """(region_id, workplace) → {minutes, transfers, estimated} 또는 None(런타임은 이것만 읽음)."""
    path = db_path or resolve_db_path(write=False)
    if not path or not Path(path).exists():
        return None
    conn = connect(path)
    try:
        row = conn.execute(
            "SELECT minutes, transfers, estimated FROM region_transit WHERE region_id=? AND workplace=?",
            (region_id, workplace),
        ).fetchone()
    finally:
        conn.close()
    return {"minutes": row[0], "transfers": row[1], "estimated": bool(row[2])} if row else None


def sample_trade(
    umd_name: str, trade_type: str, *, max_price: Optional[int] = None, db_path: Optional[str] = None
) -> Optional[dict]:
    """동+거래유형의 '중위가에 가장 가까운 실거래 1건' (발품 근거용, 국토부 실데이터).

    max_price(예산 상한)를 주면 그 이하 거래에서 우선 선정(발품이 예산 초과 매물을 앞세우지 않게).
    상한 이하 표본이 없으면 전체에서 대표 사례를 뽑되 overBudget=True로 표기(문장에서 '예산 상위 평형' 명시).
    반환 {price, monthly, area_m2, deal_ym, overBudget} 또는 None. (아웃라이어 대신 대표 사례)
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

    def _nearest_median(candidates: list) -> tuple:
        mid = sorted(r[0] for r in candidates)[len(candidates) // 2]  # 중위가
        return min(candidates, key=lambda r: abs(r[0] - mid))  # 중위가에 가장 가까운 실사례

    over_budget = False
    pool = rows
    if max_price and max_price > 0:
        within = [r for r in rows if r[0] <= max_price]
        if within:
            pool = within  # 예산 이하에서만 대표 사례 선정
        else:
            over_budget = True  # 예산 이하 표본 없음 → 전체에서 뽑되 표기(폴백)
    best = _nearest_median(pool)
    return {
        "price": best[0],
        "monthly": best[1],
        "area_m2": best[2],
        "deal_ym": best[3],
        "overBudget": over_budget,
    }
