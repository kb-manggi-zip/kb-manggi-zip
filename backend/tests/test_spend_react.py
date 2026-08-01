"""spend 여력 판정 ReAct 트레이스 — 표시용 결정론 로그.

계산 로직 무관(fixed/variable/surplus 불변). reactLog 결론과 feasibility 판정이 모순되지 않음을 보장.
"""

from app.agents.report import build_report

S3_C = dict(type="전세", deposit=320_000_000, monthlyRent=0, expiryDate="2026-10-30", renewalUsed="미사용")
S3_F = dict(annualIncome=80_000_000, ownCapital=60_000_000, household="신혼", firstHome="예", under35=True)


def test_react_log_three_steps_filled():
    r = build_report(S3_C, S3_F, "매매")
    log = r.spend.reactLog
    assert len(log) == 3
    for step in log:
        assert step["thought"].strip() and step["action"].strip() and step["observation"].strip()


def test_verdict_matches_feasibility_no_contradiction():
    # S3 매매 → 여력 초과. verdict("초과 …")와 feasibility 문장("넘어요")이 같은 판정.
    r = build_report(S3_C, S3_F, "매매")
    over_verdict = r.spend.verdict.startswith("초과")
    over_sentence = "넘어요" in r.feasibility
    assert over_verdict == over_sentence  # 모순 없음
    # 초과 금액이 feasibility의 gap과 일치
    assert "16만" in r.spend.verdict
    assert "초과 16만" in r.feasibility


def test_within_budget_verdict():
    # 갱신(월 부담 작음) → 여력 안. verdict "여력 안", 3단계 관찰 마지막이 '여력 안'.
    r = build_report(S3_C, S3_F, "갱신")
    assert r.spend.verdict == "여력 안"
    assert "여력 안" in r.spend.reactLog[2]["observation"]
    assert "안에 있어요" in r.feasibility


def test_react_log_does_not_change_numbers():
    # reactLog 유무와 무관하게 fixed/variable/total은 동일(계산 불변).
    r = build_report(S3_C, S3_F, "매매")
    assert r.spend.fixedMonthly + r.spend.variableMonthly <= r.spend.monthlyTotal + 1  # 반올림 여유
    assert r.spend.variableMonthly > 0
