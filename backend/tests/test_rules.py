"""규칙 로더 — get_rules가 노출하는 값(갱신·일회성·통보기한)이 프론트 rules.ts와 동일.

대출/보증 규제값(LTV·DSR·전세금리·보증료)은 lending_regulated.yaml·guarantee_hug.yaml에서
직접 로드하므로 여기서 검증하지 않는다(test_compare_equivalence가 출력으로 검증)."""

from app.core.rules import get_rules


def test_rules_match_frontend_values():
    r = get_rules()
    assert r.renewal.increaseCap == 0.05
    assert r.renewal.conversionRate == 0.0475  # 2026.7.16 기준금리 인상 반영
    assert r.oneTime.moveBase == 1_500_000
    assert r.oneTime.brokerRate == 0.004
    assert r.oneTime.acquisitionRate == 0.011
    assert r.noticeDeadlineMonths == 2
