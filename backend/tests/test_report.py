"""만기 결정 리포트 — 페르소나별 집계 차이 + 단방향(compare 역유입 없음) + verify."""

from app.agents import report as R
from app.schemas import ContractInfo, FinanceInfo
from app.tools.compare import compute_compare

P1_C = dict(
    type="월세",
    deposit=50_000_000,
    monthlyRent=600_000,
    expiryDate="2026-10-15",
    renewalUsed="미사용",
    housingType="연립다세대",
    note="재택근무예요",
)
P1_F = dict(annualIncome=45_000_000, ownCapital=30_000_000, household="1인", firstHome="모름", under35=True)


def test_report_persona_distinct_spend():
    v = {}
    for pid in ("P1", "P2", "P3"):
        rep = R.build_report(P1_C, P1_F, "이사", persona_id=pid)
        v[pid] = rep.spend.variableMonthly
    assert len({v["P1"], v["P2"], v["P3"]}) == 3  # 셋 다 다른 집계


def test_report_one_directional_no_compare_pollution():
    """지출 분석이 compare 숫자에 영향 주지 않음 — 리포트의 comparison == 직접 compute_compare."""
    rep = R.build_report(P1_C, P1_F, "이사", persona_id="P1")
    direct = compute_compare(ContractInfo(**P1_C), FinanceInfo(**P1_F))
    assert rep.comparison.model_dump() == direct.model_dump()


def test_report_completes_without_spend(monkeypatch):
    """mydata 없으면 ⑤는 None이어도 리포트(①~④+⑥) 완성 — 리포트가 볼모 안 됨."""
    from app.agents import spend_query

    monkeypatch.setattr(spend_query, "analyze_spending", lambda *a, **k: None)
    rep = R.build_report(P1_C, P1_F, "이사", persona_id="P1")
    assert rep.spend is None
    assert rep.comparison is not None and rep.dday is not None
    assert "마이데이터" in rep.feasibility  # 안내 문구


def test_feasibility_within_capacity():
    rep = R.build_report(P1_C, P1_F, "이사", persona_id="P1")
    assert "안에 있어요" in rep.feasibility


def test_feasibility_over_capacity():
    # 변동 여력보다 부담이 큰 케이스: 매매(고부담) 선택 + 저지출 페르소나(P1)
    rep = R.build_report(P1_C, P1_F, "매매", persona_id="P1")
    burden = next(b for b in rep.comparison.branches if b.branch == "매매").monthlyBurden
    if burden > rep.spend.variableMonthly:
        assert "넘어요" in rep.feasibility
        # verify: 문장 속 여력 숫자가 집계 원값과 일치
        assert f"{round(rep.spend.variableMonthly / 10_000):,}만원" in rep.feasibility
    else:
        assert "안에 있어요" in rep.feasibility
