"""세션 트레이싱 plumbing — X-Session-Id 헤더 수용 + langfuse off 시 no-op."""

from contextlib import nullcontext

import pytest
from fastapi.testclient import TestClient

from app.core import tracing
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_session_scope_is_usable():
    """langfuse on/off 무관하게 컨텍스트로 안전하게 진입/종료된다(예외 없음)."""
    with tracing.session_scope("sess-123"):
        pass
    with tracing.session_scope("sess-123", user_id="u-1"):
        pass


def test_session_scope_noop_when_no_session_id():
    """session_id 없으면 항상 nullcontext(트레이싱 미적용) — 동작 불변."""
    assert isinstance(tracing.session_scope(None), type(nullcontext()))
    assert isinstance(tracing.session_scope(""), type(nullcontext()))


def test_endpoints_accept_session_header(client):
    """X-Session-Id 헤더가 있어도 모든 엔드포인트가 정상 200(헤더는 스키마 밖)."""
    h = {"X-Session-Id": "journey-abc"}
    assert client.post("/api/simulate", json={"branch": "매매", "regionId": "mapo"}, headers=h).status_code == 200
    assert client.get("/api/regions", params={"branch": "이사", "budget": 0}, headers=h).status_code == 200


def test_endpoints_work_without_session_header(client):
    """헤더 없이도 동일하게 동작(하위 호환)."""
    assert client.post("/api/simulate", json={"branch": "이사", "regionId": "seongbuk"}).status_code == 200
