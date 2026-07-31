"""4축 조정 = 방향 분류 + yaml 고정 배수 — 재현성 회귀(이 작업의 핵심).

LLM은 방향만, 크기는 rules/axis_adjust.yaml. 같은 입력 → 항상 같은 배수.
"""

import json

from app.agents import clarify as C


def test_strong_down_maps_to_yaml_multiplier():
    assert C.dir_mult("strong_down") == 0.3
    assert C.dir_mult("up") == 1.4
    assert C.dir_mult("strong_up") == 1.8
    assert C.dir_mult("down") == 0.6
    # 방향 적용 시 통근 배수 0.3 → 통근 가중치 하락
    base = C.note_weights("1인", "")
    low = C.note_weights("1인", "", {"commute": "strong_down"})
    assert low["commute"] < base["commute"]


def test_unknown_direction_discarded_per_axis(monkeypatch):
    # LLM이 enum 밖 값을 뱉으면 그 축만 폐기(전체 폴백 아님). commute만 살아남아야.
    fake = json.dumps(
        {
            "interpretation": [],
            "weight_adjustments": {"commute": "strong_down", "budget": "very_down", "consumption": "0.3"},
            "question": "",
            "renewal_ask_pct": None,
            "consult_note": "",
            "renewal_situations": [],
            "situation_evidence": {},
            "conversion_amount": None,
        }
    )
    monkeypatch.setattr(C, "generate", lambda **kw: fake)
    out = C._llm_interpret("재택근무예요", "1인", [])
    assert out is not None
    assert out["boost"] == {"commute": "strong_down"}  # budget('very_down')·consumption('0.3') 폐기


def test_reproducibility_same_input_same_multiplier():
    # validate_profile(ProfileConfirm 실제 경로) 3회 → weightAdjust·가중치 완전 동일
    P = dict(
        type="전세",
        deposit=280_000_000,
        monthlyRent=0,
        expiryDate="2026-11-30",
        renewalUsed="미사용",
        preferredArea="성북구",
        note="재택근무예요",
    )
    F = dict(annualIncome=40_000_000, ownCapital=30_000_000, household="1인", firstHome="모름", under35=True)
    runs = [C.validate_profile(P, F, 0, True, []) for _ in range(3)]
    was = [r["weightAdjust"] for r in runs]
    assert was[0] == was[1] == was[2]
    ws = [C.note_weights("1인", "재택근무예요", r["weightAdjust"]) for r in runs]
    assert ws[0] == ws[1] == ws[2]


def test_fallback_and_llm_use_same_multiplier_table():
    # 폴백(note_directions) 방향 == LLM 방향이면 배수도 동일(같은 yaml 테이블)
    fb = C.note_directions("재택근무예요")
    assert fb["commute"] == "strong_down"
    assert C.dir_mult(fb["commute"]) == C.dir_mult("strong_down") == 0.3


def test_clamp_range_kept():
    cfg = C._axis_adjust_cfg()
    assert cfg["clamp"] == {"min": 0.3, "max": 2.0}
    # 모든 방향 배수가 클램프 범위 안
    for d in ("strong_up", "up", "down", "strong_down"):
        assert 0.3 <= C.dir_mult(d) <= 2.0


def test_note_directions_deterministic_and_closed():
    for note in ("재택근무예요", "매일 통근해요", "아이 학교가 중요해요"):
        d = C.note_directions(note)
        assert all(v in {"strong_up", "up", "down", "strong_down"} for v in d.values())
