"""규칙 로더 — get_rules가 노출하는 값(갱신·일회성·통보기한)이 프론트 rules.ts와 동일.

대출/보증 규제값(LTV·DSR·전세금리·보증료)은 lending_regulated.yaml·guarantee_hug.yaml에서
직접 로드하므로 여기서 검증하지 않는다(test_compare_equivalence가 출력으로 검증)."""

from app.core.rules import get_rules
from app.tools.broker_fee import broker_fee


def test_rules_match_frontend_values():
    r = get_rules()
    assert r.renewal.increaseCap == 0.05
    assert r.renewal.conversionRate == 0.0475  # 2026.7.16 기준금리 인상 반영
    assert r.oneTime.moveBase == 800_000
    assert r.oneTime.acquisitionRate == 0.011
    assert r.noticeDeadlineMonths == 2


def test_broker_fee_bands_match_frontend():
    """서울시 조례(제8585호) 별표1 구간표 — frontend rules.ts::brokerRateBands 와 동치."""
    assert broker_fee(30_000_000) == 150_000  # 5천만원 미만, 0.5%(한도 20만 이내)
    assert broker_fee(80_000_000) == 300_000  # 5천만~1억, 0.4%→32만이나 한도 30만 캡
    assert broker_fee(300_000_000) == 900_000  # 1억~6억, 0.3%
    assert broker_fee(800_000_000) == 3_200_000  # 6억~12억, 0.4%
    assert broker_fee(2_000_000_000) == 12_000_000  # 15억 이상, 0.6%
