"""테스트 공통 설정. app import 전에 환경변수를 세팅한다."""

import os

import pytest

# 격리된 SQLite 테스트 DB / 임시 캐시 (실 API·실 DB 미접촉)
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_kb.db")
os.environ.setdefault("LLM_ENABLED", "false")
os.environ.setdefault("CACHE_DIR", "./cache")


@pytest.fixture(autouse=True)
def _clear_memo_caches():
    """모듈 레벨 인메모리 캐시(clarify/regions/spend)를 테스트마다 비운다 — 크로스 테스트 오염 방지."""
    from app import graph
    from app.agents import clarify, spend_query

    for c in (clarify._CLARIFY_CACHE, spend_query._SPEND_CACHE, graph._REGIONS_CACHE):
        c.clear()
    yield
