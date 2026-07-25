"""분석 에이전트 그래프 — intake→compare→narrate 다단계. (LLM 없이 폴백으로 검증)"""

import pytest
from fastapi.testclient import TestClient

from app.graph import build_analyze_graph
from app.main import app

P2 = {
    "contract": {
        "type": "전세",
        "deposit": 320000000,
        "monthlyRent": 0,
        "expiryDate": "2026-10-30",
        "renewalUsed": "미사용",
    },
    "finance": {
        "annualIncome": 80000000,
        "ownCapital": 60000000,
        "household": "신혼",
        "firstHome": "예",
        "under35": True,
    },
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_analyze_graph_has_three_nodes():
    g = build_analyze_graph()
    nodes = set(g.get_graph().nodes)
    assert {"intake", "compare", "narrate"} <= nodes  # 단일노드가 아니라 다단계 흐름


def test_analyze_endpoint_returns_comparison_and_briefing(client):
    r = client.post("/api/analyze", json=P2)
    assert r.status_code == 200
    d = r.json()
    assert len(d["comparison"]["branches"]) == 3  # 계산 노드 산출
    assert [b["branch"] for b in d["comparison"]["branches"]] == ["갱신", "이사", "매매"]
    assert d["briefing"]  # 통역 노드 산출(폴백 템플릿)


def test_analyze_numbers_from_compute(client):
    # /api/analyze의 숫자 == /api/compare(동일 계산) — LLM이 숫자를 만들지 않음을 확인
    a = client.post("/api/analyze", json=P2).json()["comparison"]
    c = client.post("/api/compare", json=P2).json()
    assert a["branches"][2]["monthlyBurden"] == c["branches"][2]["monthlyBurden"]
