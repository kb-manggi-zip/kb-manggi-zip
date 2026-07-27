"""가드레일 Text-to-SQL — 7종 가드레일 차단 + 표준 집계 + LLM 경로 폴백."""

import pytest

from app.agents import spend_query as sq


# ── 가드레일 차단 (7종) ───────────────────────────────────────────
@pytest.mark.parametrize(
    "name,sql",
    [
        ("DDL", "DROP TABLE transactions"),
        ("쓰기", "UPDATE transactions SET amount=0 WHERE persona_id=:pid"),
        ("삭제", "DELETE FROM transactions WHERE persona_id=:pid"),
        ("다중문", "SELECT 1 FROM transactions WHERE persona_id=:pid; DROP TABLE transactions"),
        ("persona_id 누락", "SELECT SUM(amount) FROM transactions"),
        ("시스템테이블", "SELECT name FROM sqlite_master WHERE persona_id=:pid"),
        ("금지함수", "SELECT sqlite_version() FROM transactions WHERE persona_id=:pid"),
        ("PRAGMA", "PRAGMA table_info(transactions)"),
        ("ATTACH", "ATTACH DATABASE 'x.db' AS y WHERE persona_id=:pid"),
    ],
)
def test_guardrail_blocks(name, sql):
    with pytest.raises(sq.GuardrailError):
        sq.guarded_execute(sql, "P1")


def test_valid_select_passes():
    rows = sq.guarded_execute(
        "SELECT SUM(amount) FROM transactions WHERE persona_id=:pid AND category=:c".replace(":c", "'카페'"),
        "P1",
    )
    assert rows and rows[0][0] > 0


# ── persona 격리 (타 페르소나 데이터 차단) ────────────────────────
def test_persona_isolation():
    p1 = sq.standard_aggregates("P1")["monthlyTotal"]
    p2 = sq.standard_aggregates("P2")["monthlyTotal"]
    assert p1 != p2  # :pid 바인딩으로 각자 다른 데이터


# ── 표준 집계 ─────────────────────────────────────────────────────
def test_standard_aggregates_shape():
    a = sq.standard_aggregates("P1")
    assert a["monthlyTotal"] > 0
    assert abs(a["fixedMonthly"] + a["variableMonthly"] - a["monthlyTotal"]) <= 2  # /3 반올림 오차
    assert len(a["topCategories"]) == 3
    assert len(a["trend"]) == 3


def test_analyze_llm_off_no_dynamic():
    r = sq.analyze_spending("P1")  # conftest LLM off
    assert r["synthetic"] is True
    assert r["dynamicQueries"] == []


# ── LLM 경로: 악성 SQL → 가드레일 차단 → 폴백 ─────────────────────
def test_llm_malicious_sql_falls_back(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "anthropic_api_key", "test")
    # 질문은 하나, SQL은 타테이블 시도 → 차단 → 폴백(변동지출)
    monkeypatch.setattr(sq, "_llm_questions", lambda *a, **k: ["조정 가능 지출은?"])
    monkeypatch.setattr(sq, "_llm_sql", lambda q: "SELECT * FROM sqlite_master WHERE persona_id=:pid")
    r = sq.analyze_spending("P1", persona_ctx="1인 재택", branch="이사")
    assert len(r["dynamicQueries"]) == 1
    dq = r["dynamicQueries"][0]
    assert dq["fellBack"] is True
    assert dq["result"] == r["variableMonthly"]  # 표준 집계로 대체


def test_llm_valid_sql_executes(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "anthropic_api_key", "test")
    monkeypatch.setattr(sq, "_llm_questions", lambda *a, **k: ["배달 지출은?"])
    monkeypatch.setattr(
        sq, "_llm_sql", lambda q: "SELECT SUM(amount)/3 FROM transactions WHERE persona_id=:pid AND category='배달'"
    )
    r = sq.analyze_spending("P1", persona_ctx="1인 재택", branch="이사")
    dq = r["dynamicQueries"][0]
    assert dq["fellBack"] is False
    assert dq["result"] > 0
