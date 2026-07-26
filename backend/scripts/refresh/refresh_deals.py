"""국토부 실거래 수집 (오프라인) → SQLite(trades.db).

⚠️ 외부 API를 때리는 유일한 곳. 서버 런타임은 이걸 실행하지 않는다.
실행:  python scripts/refresh/refresh_deals.py        (.env 에 MOLIT_API_KEY 필요)
수집:  6구 × 최근 6개월 × {아파트, 연립다세대} × {매매, 전월세}
결과:  cache/raw/ (원응답 캐시) + data/trades.db (정규화 적재, house_type별 멱등)

오피스텔·단독다가구는 이번 확장 범위 밖(POC 스코프: 아파트+연립다세대만).
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # backend/

from app.core.cache import cached  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.rules import read_yaml  # noqa: E402
from app.tools import molit, trades_store  # noqa: E402


# ── 정규화 (순수 — pandas 없이 테스트 가능) ─────────────────────────
def parse_won(v) -> int:
    """'82,500'(만원, 공백/콤마) → 825000000(원). None/빈값 → 0."""
    if v is None:
        return 0
    s = str(v).replace(",", "").replace(" ", "").strip()
    if not s or not s.lstrip("-").isdigit():
        return 0
    return int(s) * 10_000  # 만원 → 원


def _clean_umd(v) -> str:
    return " ".join(str(v or "").split())


def normalize_rows(
    records: list[dict], sigungu_code: str, deal_ym: str, kind: str, house_type: str = "아파트"
) -> list[dict]:
    """API 원레코드 → 정규화 거래 dict[].  kind: 'sale' | 'rent'.

    전월세(rent)는 월세금액>0 이면 'monthly', 아니면 'jeonse'.
    house_type: '아파트' | '연립다세대' (국토부 API property_type 값 그대로).
    """
    out: list[dict] = []
    for rec in records:
        umd = _clean_umd(rec.get("법정동"))
        if not umd:
            continue
        try:
            area = float(rec.get("전용면적") or 0) or None
        except (TypeError, ValueError):
            area = None

        if kind == "sale":
            price, monthly, tt = parse_won(rec.get("거래금액")), 0, "sale"
        else:  # rent
            deposit = parse_won(rec.get("보증금액"))
            mon = parse_won(rec.get("월세금액"))
            price, monthly = deposit, mon
            tt = "monthly" if mon > 0 else "jeonse"

        if price <= 0:
            continue
        out.append(
            {
                "sigungu_code": sigungu_code,
                "umd_name": umd,
                "trade_type": tt,
                "house_type": house_type,
                "price": price,
                "monthly": monthly,
                "area_m2": area,
                "deal_ym": deal_ym,
            }
        )
    return out


# ── 수집 (API — 유일한 외부 호출 지점, @cached) ──────────────────────
@cached(subdir="raw")
def collect_raw(sigungu_code: str, deal_ym: str, kind_api: str, property_type: str = "아파트") -> list[dict]:
    """PublicDataReader 실거래 원응답 → JSON-safe list[dict].

    kind_api: '매매' | '전월세'.  property_type: '아파트' | '연립다세대'.
    ※ 설치된 PublicDataReader 버전에 따라 get_data 인자명 확인 필요(첫 실행 시).
    실패 시 상위에서 조합 스킵.
    """
    import json

    try:
        from PublicDataReader import TransactionPrice
    except ImportError as e:
        raise RuntimeError("PublicDataReader 미설치. pip install -r requirements.txt (PublicDataReader, pandas)") from e

    if not settings.molit_api_key:
        raise RuntimeError(".env 에 MOLIT_API_KEY 가 필요합니다.")

    api = TransactionPrice(settings.molit_api_key)
    df = api.get_data(
        property_type=property_type,
        trade_type=kind_api,
        sigungu_code=sigungu_code,
        start_year_month=deal_ym,
        end_year_month=deal_ym,
    )
    if df is None or len(df) == 0:
        return []
    return json.loads(df.to_json(orient="records", force_ascii=False))


# ── sanity / summary (seed_demo 와 공유) ─────────────────────────────
def sanity_check(conn, valid_months: set[str]) -> None:
    total = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    if total == 0:
        raise RuntimeError("수집 결과 0건 — API 키/파라미터/네트워크 확인 필요")
    weird = conn.execute("SELECT COUNT(*) FROM trades WHERE price < 10000000 OR price > 10000000000").fetchone()[0]
    if weird:
        print(f"  ⚠ 이상 price {weird}건 (1천만 미만/100억 초과)")
    oob = conn.execute(
        "SELECT COUNT(*) FROM trades WHERE deal_ym NOT IN (%s)" % ",".join("?" * len(valid_months)),
        tuple(valid_months),
    ).fetchone()[0]
    if oob:
        print(f"  ⚠ deal_ym 범위 밖 {oob}건")


def summarize(conn, elapsed: float, failures: list) -> None:
    total = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    print("\n── 수집 요약 ──")
    for code, cnt in conn.execute(
        "SELECT sigungu_code, COUNT(*) FROM trades GROUP BY sigungu_code ORDER BY sigungu_code"
    ):
        print(f"  {code}: {cnt}건")
    by_type = dict(conn.execute("SELECT trade_type, COUNT(*) FROM trades GROUP BY trade_type"))
    print(f"  거래유형별: {by_type}")
    by_house = dict(conn.execute("SELECT house_type, COUNT(*) FROM trades GROUP BY house_type"))
    print(f"  주택유형별: {by_house}")
    print(f"  총 {total}건 · {elapsed:.1f}s · 실패 조합 {len(failures)}개")
    for f in failures:
        print(f"    ✗ {f}")


# ── 실행 ─────────────────────────────────────────────────────────────
def run() -> None:
    sigungus = read_yaml("regions.yaml")["sigungu"]
    months = molit.recent_year_months(6)
    house_types = ["아파트", "연립다세대"]
    print(f"수집 대상: {list(sigungus.keys())} × {months} × {house_types} × [매매, 전월세]")

    db_path = trades_store.resolve_db_path(write=True)
    conn = trades_store.connect(db_path)
    failures: list = []
    t0 = time.time()

    for name, meta in sigungus.items():
        code = str(meta["code"])
        for ym in months:
            for house_type in house_types:
                for kind_api, kind in (("매매", "sale"), ("전월세", "rent")):
                    try:
                        raw = collect_raw(code, ym, kind_api, property_type=house_type)
                    except Exception as e:  # 실패 조합은 로그 남기고 계속
                        failures.append((name, ym, house_type, kind_api, str(e)[:80]))
                        print(f"  ✗ {name} {ym} {house_type} {kind_api}: {str(e)[:80]}")
                        continue
                    rows = normalize_rows(raw, code, ym, kind, house_type=house_type)
                    if kind == "sale":
                        trades_store.replace_batch(conn, code, ym, "sale", rows, house_type=house_type)
                    else:
                        trades_store.replace_batch(
                            conn,
                            code,
                            ym,
                            "jeonse",
                            [r for r in rows if r["trade_type"] == "jeonse"],
                            house_type=house_type,
                        )
                        trades_store.replace_batch(
                            conn,
                            code,
                            ym,
                            "monthly",
                            [r for r in rows if r["trade_type"] == "monthly"],
                            house_type=house_type,
                        )
                    time.sleep(0.3)  # 쿼터 보호

    sanity_check(conn, set(months))
    summarize(conn, time.time() - t0, failures)
    conn.close()
    print(f"\n✓ {db_path} 적재 완료. 데모 스냅샷: cp {db_path} data/trades.demo.db")


if __name__ == "__main__":
    run()
