"""명확화(판단 노드) + 개인화 조합 레이어 — 순수 함수 검증(LLM 없이 전 경로).

핵심: 자유입력은 정해진 축으로만 매핑(창작 금지), 모순은 되묻기, 조합은 결정론.
"""

from app.agents import clarify
from app.tools import persona


# ── 명확화: 자유입력 → 제약된 신호 ──────────────────────────────────
def test_note_signals_maps_to_fixed_axes_only():
    sig = clarify.note_signals("재택이라 집 근처에서 다 해결해요")
    assert sig["labels"], "재택 신호를 잡아야 함"
    # 통근 민감도↓·생활편의↑ 방향
    assert sig["boost"]["commute"] < 1.0
    assert sig["boost"]["consumption"] > 1.0


def test_note_signals_empty_for_blank():
    assert clarify.note_signals("") == {"labels": [], "boost": {}}


def test_note_weights_reflect_note_and_renormalize():
    base = clarify.note_weights("1인", "")
    remote = clarify.note_weights("1인", "재택이라 집에서 일해요")
    assert abs(sum(remote.values()) - 1.0) < 0.01  # 재정규화(합=1)
    assert remote["commute"] < base["commute"]  # 재택 → 통근 가중치↓
    assert remote["consumption"] > base["consumption"]


# ── 명확화: 모순 감지(되묻기, 닫힌 루프) ────────────────────────────
def test_household_conflict_detected():
    r = clarify.clarify({}, {"household": "1인"}, note="아이 학군 좋은 동네였으면")
    assert r["conflicts"], "1인인데 자녀 언급 → 모순 되묻기"
    assert "자녀" in r["conflicts"][0]


def test_commute_note_asks_workplace():
    r = clarify.clarify({}, {"household": "1인"}, note="회사까지 통근이 중요해요")
    assert any("근무지" in q for q in r["questions"])


def test_clarify_no_note_no_conflict():
    r = clarify.clarify({}, {"household": "신혼"}, note="")
    assert r["conflicts"] == []
    assert r["persona"] == "신혼 가구"
    assert len(r["priorities"]) == 4


# ── 개인화 조합 레이어 ──────────────────────────────────────────────
def test_build_persona_combines_resources():
    prof = persona.build_persona({}, {"household": "신혼"}, budget=320_000_000)
    assert prof["segment"] == "신혼 가구"
    assert prof["workplace"]  # 대표 직장 조합됨
    assert abs(sum(prof["weights"].values()) - 1.0) < 0.01
    assert any("실거래" in r for r in prof["resources"])
    assert "억" in prof["budgetBand"]


def test_persona_reflects_note_in_weights():
    plain = persona.build_persona({"note": ""}, {"household": "1인"})
    remote = persona.build_persona({"note": "재택근무라 통근은 상관없어요"}, {"household": "1인"})
    assert remote["weights"]["commute"] < plain["weights"]["commute"]


def test_scoring_ctx_is_single_source():
    ctx = persona.scoring_ctx({"note": ""}, {"household": "자녀"}, budget=500_000_000, in_preferred=True)
    assert ctx["household"] == "자녀"
    assert ctx["budget"] == 500_000_000
    assert ctx["in_preferred"] is True
    assert "weights" in ctx and abs(sum(ctx["weights"].values()) - 1.0) < 0.01
