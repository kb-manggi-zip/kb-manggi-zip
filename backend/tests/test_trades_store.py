"""실거래 SQLite 저장 계층 — 쓰기·읽기·멱등·빈DB 에러. (외부 API 미접촉)"""

import pytest

from app.tools import trades_store


def _rows(n, umd="합정동"):
    return [
        {
            "sigungu_code": "11440",
            "umd_name": umd,
            "trade_type": "sale",
            "price": 500_000_000 + i,
            "monthly": 0,
            "area_m2": 84.9,
            "deal_ym": "202605",
        }
        for i in range(n)
    ]


def test_write_read_and_idempotent(tmp_path):
    db = str(tmp_path / "t.db")
    conn = trades_store.connect(db)
    trades_store.replace_batch(conn, "11440", "202605", "sale", _rows(3))
    trades_store.replace_batch(conn, "11440", "202605", "sale", _rows(3))  # 재실행
    conn.close()

    assert trades_store.count(db) == 3  # 중복 없음 (배치 교체)
    got = trades_store.read_trades("sale", db_path=db)
    assert len(got) == 3
    assert got[0]["umd_name"] == "합정동"
    assert got[0]["house_type"] == "아파트"  # 기본값
    assert set(got[0]) == {"umd_name", "price", "monthly", "area_m2", "deal_ym", "house_type", "sigungu_code"}


def test_house_type_batches_dont_clobber_each_other(tmp_path):
    db = str(tmp_path / "t.db")
    conn = trades_store.connect(db)
    trades_store.replace_batch(conn, "11440", "202605", "sale", _rows(3), house_type="아파트")
    trades_store.replace_batch(conn, "11440", "202605", "sale", _rows(2), house_type="연립다세대")
    conn.close()

    assert trades_store.count(db) == 5  # 유형 다르면 같은 (sigungu,deal_ym,trade_type)여도 안 지워짐
    apt = trades_store.read_trades("sale", db_path=db, house_type="아파트")
    villa = trades_store.read_trades("sale", db_path=db, house_type="연립다세대")
    assert len(apt) == 3 and len(villa) == 2


def test_empty_db_raises_with_guidance(tmp_path):
    db = str(tmp_path / "empty.db")
    trades_store.connect(db).close()
    with pytest.raises(RuntimeError, match="refresh"):
        trades_store.read_trades("sale", db_path=db)


def test_missing_db_raises(tmp_path):
    with pytest.raises(RuntimeError):
        trades_store.read_trades("sale", db_path=str(tmp_path / "nope.db"))
