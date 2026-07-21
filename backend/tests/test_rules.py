"""규칙 로더 — YAML 값이 프론트 rules.ts 와 동일(시작 예시값)."""
from app.core.rules import get_rules


def test_rules_match_frontend_values():
    r = get_rules()
    assert r.renewal.increaseCap == 0.05
    assert r.renewal.conversionRate == 0.055
    assert r.loan.ltv == 0.70
    assert r.loan.dsrCap == 0.40
    assert r.loan.stressRate == 0.045
    assert r.loan.years == 30
    assert r.loan.jeonseRate == 0.038
    assert r.guarantee.feeRate == 0.0015
    assert r.oneTime.moveBase == 1_500_000
    assert r.oneTime.brokerRate == 0.004
    assert r.oneTime.acquisitionRate == 0.011
    assert r.noticeDeadlineMonths == 2
