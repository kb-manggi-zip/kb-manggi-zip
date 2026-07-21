"""B1.5 리서치 반영 프리미티브 검증 — 스펙 PART 4 C-케이스 기반.

이 테스트가 곧 "스펙 산식의 사실확인"이다 (HF 앵커·정책대출 자격·규제 판정).
아직 compare/스키마/프론트에는 연결하지 않은, 순수 함수 단위 검증.
"""
import pytest

from app.tools.guarantee_hug import calc_guarantee_fee
from app.tools.lending_calc import (
    annuity_payment,
    dsr_loan_limit,
    effective_dsr_rate,
    solve_max_price,
)
from app.tools.policy_loans import (
    buttimok_youth_eligibility,
    didimdol_eligibility,
)
from app.tools.regions import classify_region


# ── 지역 판정 ───────────────────────────────────────────────────────
def test_classify_seoul_demo_regions_are_regulated():
    # 데모 동네(구 이름만)도 서울=규제로 잡혀야 함 (스펙 pseudocode 보완 지점)
    for name in ["마포구 합정동", "은평구 녹번동", "도봉구 창동", "노원구 상계동", "중랑구 면목동"]:
        r = classify_region(name)
        assert r["is_regulated"] is True, name
        assert r["is_metro"] is True, name


def test_classify_nonregulated():
    r = classify_region("부산광역시 해운대구")
    assert r["is_regulated"] is False
    assert r["is_metro"] is False


# ── C6: HF 앵커 (산식 검증의 결정타) ─────────────────────────────────
def test_c6_hf_anchor_monthly_payment():
    m = annuity_payment(320_000_000, 0.0285, 30)  # 디딤돌 신혼 최대·최저금리·30년
    assert abs(m - 1_323_383) <= 100


# ── 스트레스 DSR: 금리 분리 + 한도 역산 ──────────────────────────────
def test_stress_rate_lowers_limit():
    base = 0.0410
    sizing = effective_dsr_rate(base, stress_rate=0.030, base_ratio=1.0, loan_type_ratio=1.0)
    assert sizing == pytest.approx(0.0710)
    # 산정금리(7.1%)가 표시금리(4.1%)보다 한도를 낮춘다
    lim_stress = dsr_loan_limit(80_000_000, 0.40, sizing, 30)
    lim_base = dsr_loan_limit(80_000_000, 0.40, base, 30)
    assert lim_stress < lim_base


# ── C1: 서울 매매 — LTV40% + 캡 바인딩 ───────────────────────────────
def test_c1_seoul_buy_caps():
    # 자본 3.8억, 소득 8천, 서울(규제 LTV 40%), 정책 없음, KB캡 3억
    dsr = dsr_loan_limit(80_000_000, 0.40, effective_dsr_rate(0.0410, 0.030, 1.0, 1.0), 30)
    price = solve_max_price(capital=380_000_000, ltv=0.40, dsr_limit=dsr,
                            policy_limit=0, bank_cap=300_000_000)
    loan = price - 380_000_000
    assert loan <= min(300_000_000, dsr) + 1  # 대출 ≤ min(KB캡3억, DSR한도)
    assert price <= 380_000_000 / (1 - 0.40) + 1  # LTV 제약


# ── C2: 신혼·무주택·소득 8천 → 디딤돌 자격 O, 한도 3.2억 ──────────────
def test_c2_didimdol_newlywed_eligible():
    p = didimdol_eligibility(
        annual_income=80_000_000, household="신혼", is_no_house=True,
        net_asset=200_000_000,
    )
    assert p.eligible is True
    assert p.limit == 320_000_000
    assert p.rate == 0.0285


def test_didimdol_over_income_rejected():
    p = didimdol_eligibility(
        annual_income=90_000_000, household="신혼", is_no_house=True, net_asset=200_000_000,
    )
    assert p.eligible is False
    assert p.limit == 0


# ── C4: 보증금 2.5억 아파트·80%이하 → 요율 0.00122 ───────────────────
def test_c4_guarantee_rate():
    g = calc_guarantee_fee(250_000_000)  # 기본 apartment·le80
    assert g["rate"] == 0.00122
    assert g["monthly_equiv"] == int(250_000_000 * 0.00122 / 12)


# ── C5: 만28세·소득 4.5천·보증금 2억 → 버팀목 자격 O, 금리 2.9% ────────
def test_c5_buttimok_eligible():
    p = buttimok_youth_eligibility(
        age=28, annual_income=45_000_000, deposit=200_000_000, net_asset=50_000_000,
    )
    assert p.eligible is True
    assert p.rate == 0.029
    assert p.limit == 150_000_000
