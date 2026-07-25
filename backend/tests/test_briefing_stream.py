"""SSE 브리핑 스트림 — 폴백(LLM 비활성) 경로 검증. 실 API 호출 없음."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _collect_data(sse_text: str) -> str:
    """SSE 응답 텍스트에서 data: 청크를 이어붙여 원문 복원 ([DONE] 제외)."""
    parts = []
    for line in sse_text.splitlines():
        if line.startswith("data:"):
            payload = line[len("data:") :].lstrip()
            if payload != "[DONE]":
                parts.append(payload)
    return "".join(parts)


def test_briefing_stream_savedmoney(client):
    r = client.post("/api/briefing/stream", json={"kind": "savedMoney", "context": {}})
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    assert "[DONE]" in r.text  # 종료 이벤트
    assert _collect_data(r.text) == "눌러앉으면 아끼는 돈의 쓰임을 정리했어요."


def test_briefing_stream_compare(client):
    payload = {
        "kind": "compare",
        "context": {
            "name": "신혼 가구",
            "comparison": {
                "branches": [
                    {
                        "branch": "갱신",
                        "headline": "",
                        "depositOrPrice": 0,
                        "loanAmount": 0,
                        "oneTimeCost": 0,
                        "guaranteeMonthly": 0,
                        "monthlyBurden": 900000,
                        "risks": [],
                        "cares": [],
                        "basis": [],
                        "feature": "",
                    },
                    {
                        "branch": "이사",
                        "headline": "",
                        "depositOrPrice": 0,
                        "loanAmount": 0,
                        "oneTimeCost": 0,
                        "guaranteeMonthly": 0,
                        "monthlyBurden": 800000,
                        "risks": [],
                        "cares": [],
                        "basis": [],
                        "feature": "",
                    },
                    {
                        "branch": "매매",
                        "headline": "",
                        "depositOrPrice": 0,
                        "loanAmount": 0,
                        "oneTimeCost": 0,
                        "guaranteeMonthly": 0,
                        "monthlyBurden": 1690000,
                        "risks": [],
                        "cares": [],
                        "basis": [],
                        "feature": "",
                    },
                ],
                "dday": 100,
                "noticeDaysLeft": 40,
                "noticeDeadline": "2026-08-30",
                "monthlyToDeposit": 0,
                "savings": 0,
                "assumptions": [],
            },
        },
    }
    r = client.post("/api/briefing/stream", json=payload)
    assert r.status_code == 200
    assert "[DONE]" in r.text
    text = _collect_data(r.text)  # 청크 재조립
    assert "신혼 가구" in text  # 폴백 템플릿에 이름 포함
    assert "옮기기" in text  # lightest = 이사(월80만) → "옮기기"
