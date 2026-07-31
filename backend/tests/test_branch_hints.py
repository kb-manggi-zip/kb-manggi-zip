"""상황 → 3갈래 힌트 전파(표시 계층) — resolver.branchHints 회귀.

계산 무관. applied(승인·requires 통과) 케이스만, 문구는 yaml 원문 그대로.
"""

from pathlib import Path

import yaml

from app.schemas import ContractInfo
from app.tools.renewal_resolver import resolve

RULES = Path(__file__).resolve().parent.parent / "rules" / "renewal_cases.yaml"
_DOC = yaml.safe_load(RULES.read_text(encoding="utf-8"))
_BY_ID = {c["id"]: c for c in _DOC["cases"]}


def _contract():
    return ContractInfo(type="전세", deposit=280_000_000, monthlyRent=0, expiryDate="2026-11-30", renewalUsed="미사용")


def test_no_situations_no_hints():
    r = resolve([], _contract(), days_left=40)
    assert r.branchHints == {"renewal": [], "move": [], "purchase": []}


def test_rejected_situation_no_hints():
    # noticeDaysLeft>=0 → notice_deadline_passed 기각 → 힌트 미표시(계산과 표시가 같은 판정)
    r = resolve(["notice_deadline_passed"], _contract(), days_left=40)
    assert all(len(v) == 0 for v in r.branchHints.values())


def test_favorable_hint_only_renewal():
    r = resolve(["notice_deadline_passed"], _contract(), days_left=-31)
    assert len(r.branchHints["renewal"]) == 1
    assert r.branchHints["renewal"][0]["tone"] == "favorable"
    assert r.branchHints["move"] == [] and r.branchHints["purchase"] == []


def test_accumulates_across_situations():
    # 실거주거절 + 권소진 동시 승인 → move에 힌트 2건 누적
    r = resolve(["landlord_self_occupancy", "renewal_right_exhausted"], _contract(), days_left=40)
    assert len(r.branchHints["move"]) == 2
    assert len(r.branchHints["purchase"]) == 2
    ids = {h["situationId"] for h in r.branchHints["move"]}
    assert ids == {"landlord_self_occupancy", "renewal_right_exhausted"}


def test_hint_text_matches_yaml_verbatim():
    r = resolve(["landlord_self_occupancy"], _contract(), days_left=40)
    yaml_move = _BY_ID["landlord_self_occupancy"]["branch_hint"]["move"]
    hint = r.branchHints["move"][0]
    assert hint["text"] == yaml_move["text"]  # 재작성 방지
    assert hint["tone"] == yaml_move["tone"]


def test_null_hint_branch_skipped():
    # jeonse_to_monthly: purchase=null → purchase 힌트 없음, renewal/move만
    r = resolve(["jeonse_to_monthly"], _contract(), days_left=40)
    assert len(r.branchHints["renewal"]) == 1
    assert len(r.branchHints["move"]) == 1
    assert r.branchHints["purchase"] == []
