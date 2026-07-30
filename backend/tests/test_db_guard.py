"""DB 함정 가드 — stale trades.db(통근 데이터 비어있음)가 완전한 데모 DB를 가리지 않게."""

import sqlite3

import pytest

from app.tools import trades_store


@pytest.fixture(autouse=True)
def _reset_db_cache():
    """이 파일의 monkeypatch가 memoize한 tmp 경로가 다른 테스트로 새지 않게 리셋."""
    trades_store._reset_read_db_cache()
    yield
    trades_store._reset_read_db_cache()


def _seed_transit(path):
    con = sqlite3.connect(str(path))
    con.execute(
        "INSERT INTO region_transit (region_id, workplace, minutes, transfers, estimated, collected_at) "
        "VALUES ('성산동','판교(IT)',21,1,0,'2026-07')"
    )
    con.commit()
    con.close()


def test_stale_trades_db_falls_back_to_demo(tmp_path, monkeypatch):
    real = tmp_path / "trades.db"
    demo = tmp_path / "trades.demo.db"
    trades_store.connect(str(real)).close()  # SCHEMA만 — region_transit 빈 stale DB
    trades_store.connect(str(demo)).close()
    _seed_transit(demo)  # 데모 DB엔 통근 데이터 있음

    monkeypatch.setattr(trades_store, "REAL_DB", real)
    monkeypatch.setattr(trades_store, "DEMO_DB", demo)
    monkeypatch.delenv("TRADES_DB", raising=False)
    trades_store._reset_read_db_cache()

    # stale 실DB가 있어도 통근이 비었으면 데모 DB로 폴백
    assert trades_store.resolve_db_path() == str(demo)

    # 실DB에 통근 데이터가 차면 실DB를 선택
    _seed_transit(real)
    trades_store._reset_read_db_cache()
    assert trades_store.resolve_db_path() == str(real)


def test_env_override_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADES_DB", "/custom/path.db")
    assert trades_store.resolve_db_path() == "/custom/path.db"
