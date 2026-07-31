"""전세→월세 전환(§7-2) compare 연결 — 손계산 대조 + 독립성 + 미입력 불변.

전환율은 rules/renewal.yaml(conversionRate) 단일 출처. cap_pct(인상률)와 독립 규제.
"""

import datetime

from app.core.rules import get_rules
from app.schemas import ContractInfo, FinanceInfo
from app.tools.compare import compute_compare
from app.tools.format import js_round

NOW = datetime.datetime(2026, 7, 19, tzinfo=datetime.timezone.utc)
RATE = get_rules().renewal.conversionRate  # 0.0475
FIN = FinanceInfo(annualIncome=40_000_000, ownCapital=30_000_000, household="1인", firstHome="모름", under35=True)


def _renewal(**kw):
    c = dict(type="전세", deposit=320_000_000, monthlyRent=0, expiryDate="2026-11-30", renewalUsed="미사용")
    c.update(kw)
    r = compute_compare(ContractInfo(**c), FIN, now=NOW)
    return next(b for b in r.branches if b.branch == "갱신")


def test_conversion_hand_calc():
    # 320M ×1.05(기본 합의 인상) = 336M, 전환 1억 → 236M / 월세 = 1억×0.0475/12
    b = _renewal(renewalSituations=["jeonse_to_monthly"], conversionAmount=100_000_000)
    conv_monthly = js_round(100_000_000 * RATE / 12)
    assert b.depositOrPrice == 236_000_000
    assert conv_monthly == 395_833  # 손계산: 100,000,000 × 0.0475 ÷ 12
    assert "+ 월세" in b.headline and "전환" in b.headline


def test_conversion_not_entered_is_guidance_only():
    # 전환 상황만 승인·감액분 미입력 → 전환 미계산(인상 5%만) → 336M, 월세 없음
    b = _renewal(renewalSituations=["jeonse_to_monthly"])
    assert b.depositOrPrice == 336_000_000
    assert "전환" not in b.headline


def test_conversion_independent_of_cap_pct():
    # 통보경과(cap 0) + 전환 동시 → 인상 0 + 전환 1억 → 320M - 1억 = 220M (각각 적용)
    b = _renewal(
        expiryDate="2026-05-30",
        renewalSituations=["notice_deadline_passed", "jeonse_to_monthly"],
        conversionAmount=100_000_000,
    )
    assert b.depositOrPrice == 220_000_000


def test_golden_path_unchanged_without_conversion():
    b = _renewal(deposit=280_000_000)  # 상황·전환 없음
    assert b.depositOrPrice == 294_000_000
