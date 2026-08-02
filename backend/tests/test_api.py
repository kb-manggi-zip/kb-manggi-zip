"""엔드포인트 스모크 — 스키마 준수 + LLM 0회 경로 + 예약 저장."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    # with 컨텍스트가 startup 이벤트(init_db)를 실행 → 테이블 생성
    with TestClient(app) as c:
        yield c


P2 = {
    "contract": {
        "type": "전세",
        "deposit": 320000000,
        "monthlyRent": 0,
        "expiryDate": "2026-10-30",
        "renewalUsed": "미사용",
    },
    "finance": {"annualIncome": 80000000, "ownCapital": 60000000, "household": "신혼"},
}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["llm_active"] is False  # 키 없음 → 폴백 모드


def test_compare_schema(client):
    r = client.post("/api/compare", json=P2)
    assert r.status_code == 200
    body = r.json()
    assert len(body["branches"]) == 3
    assert [b["branch"] for b in body["branches"]] == ["갱신", "이사", "매매"]
    assert body["dday"] > 0
    for b in body["branches"]:
        assert isinstance(b["monthlyBurden"], int)


def test_regions_branches(client):
    for branch, expect in [("매매", "매매"), ("이사", "이사"), ("이사-월세", "이사")]:
        r = client.get("/api/regions", params={"branch": branch, "budget": 0})
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 3
        assert all(row["branch"] == expect for row in rows)


def test_regions_housing_type_filter(client):
    apt = client.get("/api/regions", params={"branch": "이사", "budget": 0, "housingType": "아파트"})
    villa = client.get("/api/regions", params={"branch": "이사", "budget": 0, "housingType": "연립다세대"})
    assert apt.status_code == 200 and villa.status_code == 200
    assert len(apt.json()) == 3 and len(villa.json()) == 3
    # housingType 미지정 시(기존 동작) 여전히 동작 — 하위호환
    blended = client.get("/api/regions", params={"branch": "이사", "budget": 0})
    assert blended.status_code == 200 and len(blended.json()) == 3


def test_products_and_simulate(client):
    r = client.post("/api/products", json={"branch": "매매"})
    assert r.status_code == 200
    assert r.json()["mainLoan"]["name"]

    r = client.post("/api/simulate", json={"branch": "매매", "regionId": "mapo"})
    assert r.status_code == 200
    assert len(r.json()["scenes"]) == 3  # region_id 있으면 고정 3씬 동적 조립(2026-08-02)


def test_briefing_fallback(client):
    r = client.post("/api/briefing", json={"kind": "savedMoney", "context": {}})
    assert r.status_code == 200
    assert r.json()["text"]


def test_draft_notice_placeholder(client):
    r = client.post("/api/draft-notice", json={"expiryDate": "2026-10-30"})
    assert r.status_code == 200
    draft = r.json()["draft"]
    assert "2026년 10월 30일" in draft
    assert "[동·호수]" in draft


def test_reservation_persists(client):
    r = client.post(
        "/api/reservation",
        json={"branch": "매매", "date": "2026-08-01", "productName": "KB 주담대"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert isinstance(r.json()["id"], int)
