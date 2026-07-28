"""명확화(판단 노드) + 개인화 조합 레이어 — 순수 함수 검증(LLM 없이 전 경로).

핵심: 자유입력은 정해진 축으로만 매핑(창작 금지), 모순은 되묻기, 조합은 결정론.
"""

import json

from app.agents import clarify
from app.core.config import settings
from app.tools import persona


def _force_llm(monkeypatch, response: str):
    """llm_active=True로 만들고 clarify.generate를 캔드 응답으로 모킹."""
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
    assert settings.llm_active  # 게이트 열림 확인
    monkeypatch.setattr(clarify, "generate", lambda **kw: response)


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


def test_no_household_conflict_before_selection():
    # J1: 가구 유형 미선택(household_selected=False)이면 자녀 힌트가 있어도 상충 오탐하지 않는다.
    r = clarify.clarify({}, {"household": "1인"}, note="아이 학군 좋은 동네였으면", household_selected=False)
    assert r["conflicts"] == [], "가구 미선택 → 대조 불가 → 상충 없음"
    assert r["held"] is False
    # 실제로 '1인'을 선택하면(기본 household_selected=True) 그때부터 상충 감지(현행 유지)
    r2 = clarify.clarify({}, {"household": "1인"}, note="아이 학군 좋은 동네였으면")
    assert r2["conflicts"]


def test_validate_profile_rule_fallback_detects_and_holds():
    # 최종 프로필 종합검증: LLM 비활성(테스트) → 간이 검증(mode=rule). 상충이면 held + weightAdjust 미반영.
    note = {"note": "재택근무해요 · 통근이 제일 중요해요"}
    r = clarify.validate_profile(note, {"household": "1인"}, budget=360_000_000)
    assert r["mode"] == "rule"
    assert r["conflicts"], "재택+통근 → 상충 감지"
    assert r["held"] is True and r["weightAdjust"] == {}, "상충 남으면 확정 전 미반영"
    # 상충 없는 입력은 해석된 boost가 실린다(확정 시 반영될 값)
    r2 = clarify.validate_profile({"note": "카페 자주 가요"}, {"household": "1인"})
    assert r2["mode"] == "rule" and r2["conflicts"] == [] and r2["weightAdjust"]


def test_validate_profile_structured_conflicts_and_accept():
    # K1: 상충이 구조(conflictItems)로 나와 인라인 해소가 가능하고, '둘 다'(accepted)면 해소+반영.
    # (conftest가 LLM_ENABLED=false → 간이검증 경로)
    r = clarify.validate_profile({"note": "재택근무예요 · 매일 통근해요"}, {"household": "1인"})
    axis = [c for c in r["conflictItems"] if c["type"] == "axis"]
    assert axis and {axis[0]["optionA"], axis[0]["optionB"]} == {"재택근무예요", "매일 통근해요"}
    assert axis[0]["allowBoth"] is True and r["held"] is True and r["weightAdjust"] == {}
    # '둘 다 맞아요' → 그 쌍은 상충 제외, 해석 boost 반영(사용자가 확인한 상쇄)
    r2 = clarify.validate_profile(
        {"note": "재택근무예요 · 매일 통근해요"},
        {"household": "1인"},
        accepted_pairs=[["재택근무예요", "매일 통근해요"]],
    )
    assert r2["conflictItems"] == [] and r2["weightAdjust"]


def test_validate_profile_household_conflict_carries_values():
    # K1: 가구 불일치는 optionA/optionB에 '가구 유형 값'을 실어 문진 복귀 없이 바꿀 수 있게 한다.
    r = clarify.validate_profile({"note": "아이 학교가 중요해요"}, {"household": "1인"})
    hh = [c for c in r["conflictItems"] if c["type"] == "household"]
    assert hh and hh[0]["optionA"] == "1인" and hh[0]["optionB"] == "자녀" and hh[0]["allowBoth"] is False


def test_segment_stays_with_selection_under_unresolved_conflict():
    # J2: 미확정 note는 세그먼트를 뒤집지 않는다 — segment는 선택된 가구 유형에서만 나온다.
    from app.tools import persona

    r = clarify.clarify({}, {"household": "1인"}, note="아이 학교 근처였으면")
    assert r["persona"] == "1인 청년 임차 가구", "상충 미해결이어도 segment는 선택값 유지"
    p = persona.build_persona({"note": "아이 학교 근처였으면"}, {"household": "1인"})
    assert p["segment"] == "1인 청년 임차 가구"


def test_intra_note_contradiction():
    # 한 입력에 재택(통근↓)+통근(통근↑) 함께 → 조용한 상쇄 대신 되묻기
    r = clarify.clarify({}, {"household": "1인"}, note="재택근무해요 통근해요")
    assert any("통근" in c and ("상충" in c or "함께" in c) for c in r["conflicts"])
    assert r["held"] is True  # 상충 미해결 → 반영 보류 신호


def test_contradictory_note_held_from_ranking():
    # B1: 미확정 상충 입력은 랭킹에 반영 보류 — 자기상쇄 boost가 조용히 순위를 흔들면 안 됨
    base = clarify.note_weights("1인", "")
    held = clarify.note_weights("1인", "재택근무해요 통근해요")  # 상충, 미확정(adjust 없음)
    assert held == base, "상충 미확정 입력은 base 가중치 그대로(보류)"
    # 사용자가 HITL로 확정(adjust 전달)하면 그때는 반영
    applied = clarify.note_weights("1인", "재택근무해요 통근해요", adjust={"commute": 0.5})
    assert applied != base


def test_prior_contradiction_reask():
    # 재택(통근↓) 반영 후 '통근 중요'(통근↑) → 되묻기(조용한 덮어쓰기 금지)
    r = clarify.clarify({}, {"household": "1인"}, note="통근이 제일 중요해요", prior_notes=["재택근무예요"])
    assert any("통근" in c and ("다시" in c or "반대" in c) for c in r["conflicts"])


def test_prior_no_contradiction_when_aligned():
    r = clarify.clarify({}, {"household": "1인"}, note="카페 자주 가요", prior_notes=["재택근무예요"])
    assert r["conflicts"] == []  # 다른 축이면 충돌 아님


def test_commute_note_asks_workplace():
    r = clarify.clarify({}, {"household": "1인"}, note="회사까지 통근이 중요해요")
    assert any("근무지" in q for q in r["questions"])


def test_clarify_no_note_no_conflict():
    r = clarify.clarify({}, {"household": "신혼"}, note="")
    assert r["conflicts"] == []
    assert r["persona"] == "신혼 가구"
    assert len(r["priorities"]) == 4


# ── LLM 경로 (제약된 해석) ──────────────────────────────────────────
def test_llm_path_used_when_active_and_valid(monkeypatch):
    resp = json.dumps(
        {
            "interpretation": ["재택 언급 → 통근 비중 낮춤"],
            "weight_adjustments": {"commute": 0.5, "consumption": 1.3},
            "question": "",
        }
    )
    _force_llm(monkeypatch, resp)
    r = clarify.clarify({}, {"household": "1인"}, note="집에서 대부분 시간을 보내요")
    # noteSignals가 LLM interpretation에서 옴(키워드 라벨 아님)
    assert r["noteSignals"] == ["재택 언급 → 통근 비중 낮춤"]


def test_llm_out_of_axis_falls_back_to_keyword(monkeypatch):
    # 축 밖 키(foo) → 제약 위반 → 키워드 폴백
    _force_llm(monkeypatch, json.dumps({"interpretation": ["x"], "weight_adjustments": {"foo": 1.5}, "question": ""}))
    r = clarify.clarify({}, {"household": "1인"}, note="카페 자주 가요")
    kw = clarify.note_signals("카페 자주 가요")["labels"]
    assert r["noteSignals"] == kw  # 폴백 경로 라벨과 동일


def test_llm_bad_multiplier_falls_back(monkeypatch):
    # 배수 범위(0.3~2.0) 위반 → 폴백
    _force_llm(
        monkeypatch, json.dumps({"interpretation": ["x"], "weight_adjustments": {"commute": 9.0}, "question": ""})
    )
    r = clarify.clarify({}, {"household": "1인"}, note="카페 자주 가요")
    assert r["noteSignals"] == clarify.note_signals("카페 자주 가요")["labels"]


def test_llm_garbage_output_falls_back(monkeypatch):
    _force_llm(monkeypatch, "여기 JSON 없음 그냥 텍스트")
    r = clarify.clarify({}, {"household": "1인"}, note="재택근무예요")
    assert r["noteSignals"] == clarify.note_signals("재택근무예요")["labels"]


def test_llm_phrases_conflict_question_when_detected(monkeypatch):
    # 모순 감지는 결정론, LLM은 되묻기 문구만 자연스럽게
    resp = json.dumps(
        {"interpretation": [], "weight_adjustments": {}, "question": "혹시 아이와 함께 지내실 계획인가요?"}
    )
    _force_llm(monkeypatch, resp)
    r = clarify.clarify({}, {"household": "1인"}, note="아이 학군이 좋았으면 해요")
    assert r["conflicts"]  # 감지는 그대로(결정론)
    assert r["questions"][0] == "혹시 아이와 함께 지내실 계획인가요?"  # 문구는 LLM


# ── 개인화 조합 레이어 ──────────────────────────────────────────────
def test_build_persona_combines_resources():
    prof = persona.build_persona({}, {"household": "신혼"}, budget=320_000_000)
    assert prof["segment"] == "신혼 가구"
    assert prof["workplace"]  # 대표 직장 조합됨
    assert abs(sum(prof["weights"].values()) - 1.0) < 0.01
    assert any("실거래" in r for r in prof["resources"])
    assert "억" in prof["budgetBand"]


def test_persona_reflects_note_in_weights():
    # 상충 없는 단일 방향 입력(재택→통근↓)은 그대로 반영. ('통근' 키워드를 넣으면 B1 보류 대상이 됨)
    plain = persona.build_persona({"note": ""}, {"household": "1인"})
    remote = persona.build_persona({"note": "재택근무라 집에서 일해요"}, {"household": "1인"})
    assert remote["weights"]["commute"] < plain["weights"]["commute"]


def test_scoring_ctx_is_single_source():
    ctx = persona.scoring_ctx({"note": ""}, {"household": "자녀"}, budget=500_000_000, in_preferred=True)
    assert ctx["household"] == "자녀"
    assert ctx["budget"] == 500_000_000
    assert ctx["in_preferred"] is True
    assert "weights" in ctx and abs(sum(ctx["weights"].values()) - 1.0) < 0.01
