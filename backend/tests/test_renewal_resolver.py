"""갱신 상황 resolver — 결정론 조합 회귀 테스트.

핵심: requires 교차검증(자유입력만으로 계산 안 바뀜)·priority 승자독식·enum 밖 폐기·
guidance 원문 일치. compare 연동 골든패스 불변은 test_compare_equivalence 가 담보.
"""

from pathlib import Path

import yaml

from app.schemas import ContractInfo
from app.tools.renewal_resolver import resolve

RULES = Path(__file__).resolve().parent.parent / "rules" / "renewal_cases.yaml"


def _contract():
    return ContractInfo(
        type="전세",
        deposit=280_000_000,
        monthlyRent=0,
        expiryDate="2026-11-30",
        renewalUsed="미사용",
    )


def test_notice_deadline_passed_applies_cap_zero():
    r = resolve(["notice_deadline_passed"], _contract(), days_left=-31)
    assert r.cap_pct == 0
    assert r.applied == ["notice_deadline_passed"]


def test_notice_deadline_rejected_when_days_left_positive():
    # 자유입력에 '통보 없었어요'가 있어도 noticeDaysLeft>=0 이면 기각 → cap 기본 5 (핵심)
    r = resolve(["notice_deadline_passed"], _contract(), days_left=40)
    assert r.cap_pct == 5
    assert r.applied == []
    assert r.rejected and r.rejected[0]["id"] == "notice_deadline_passed"


def test_priority_winner_take_all():
    # notice(prio 100, cap 0) vs right_exhausted(prio 90, cap None) 동시 → cap 0
    r = resolve(["renewal_right_exhausted", "notice_deadline_passed"], _contract(), days_left=-31)
    assert r.cap_pct == 0
    assert r.applied[0] == "notice_deadline_passed"


def test_out_of_enum_value_discarded_only():
    r = resolve(["bogus", "landlord_self_occupancy"], _contract(), days_left=40)
    assert r.applied == ["landlord_self_occupancy"]  # 정상 값은 살아남음
    assert any(x["id"] == "bogus" for x in r.rejected)  # 밖 값만 폐기


def test_empty_defaults_to_simple_increase():
    r = resolve([], _contract(), days_left=40)
    assert r.cap_pct == 5  # 현행 동작(골든패스와 동일)
    assert r.applied == []


def test_unknown_not_in_table_no_calc_effect():
    r = resolve(["unknown"], _contract(), days_left=40)
    assert r.cap_pct == 5  # 계산 미반영(기본 유지)
    assert r.applied == []
    assert any(x["id"] == "unknown" for x in r.rejected)


def test_guidance_matches_yaml_verbatim():
    doc = yaml.safe_load(RULES.read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in doc["cases"]}
    r = resolve(["landlord_self_occupancy"], _contract(), days_left=40)
    assert r.guidances == [by_id["landlord_self_occupancy"]["guidance"]]  # 재작성 방지
    assert r.citations == [by_id["landlord_self_occupancy"]["citation"]]
