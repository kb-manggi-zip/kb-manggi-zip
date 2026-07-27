"""문진 명확화 — 판단 노드(종합명세 §4-2 ★1순위).

역할: 폼값 + 자유입력(자연어)을 **정해진 세그먼트·우선순위 축으로 제약**해 해석하고,
값끼리의 모순(예: 가구유형 ↔ 자유입력 언급)을 감지해 **되묻는다**(닫힌 루프).

안전장치(§4-5 감사 가능성):
- 판단 노드지만 **창작 금지** — 자유입력은 아래 정해진 키워드 축으로만 매핑된다.
  LLM을 켜면 자연어 해석 폭이 넓어지는 seam이지만, 출력은 여전히 이 축들로 제약(창작 아님).
- 모순은 "명확화 질문 → 사용자 확정 → 결정론 계산"의 닫힌 루프 → 재현·감사 가능(자율계획과 다름).
- 실제 재질의(UI)는 프론트가 처리. 여기선 질문 텍스트만 만든다.

이 모듈은 순수(외부 I/O 없음) — 테스트가 LLM 없이 전 경로를 검증한다.
"""

from typing import Optional

from ..tools import scoring

# 스코어 축 → 사람 라벨 (화면·우선순위 표기용)
AXIS_LABEL = {
    "commute": "통근",
    "consumption": "생활·소비",
    "budget": "예산 여유",
    "preference": "선호지역",
}

# 가구 세그먼트 → 표시 라벨
SEGMENT_LABEL = {
    "1인": "1인 청년 임차 가구",
    "신혼": "신혼 가구",
    "자녀": "자녀 양육 가구",
}

# 자유입력 키워드 → (반영 라벨, 축별 가중치 배수). **정해진 항목만** — LLM 켜도 이 축들로 제약.
# 배수는 '감'이 아니라 방향만(↑/↓) 부여하는 보정 — 재정규화되므로 절대크기 아닌 상대조정.
_NOTE_MAP: list[tuple[tuple[str, ...], str, dict]] = [
    (
        ("재택", "집에서", "집 주변", "동네에서", "근처에서"),
        "재택·동네생활 중시 → 통근 가중치 절반·생활편의↑",
        {"commute": 0.5, "consumption": 1.3},
    ),
    (("자차", "차로", "운전", "차 있"), "자차 이동 → 통근시간 민감도↓", {"commute": 0.7}),
    (("도보", "걸어", "걸어서"), "도보 생활권 선호 → 선호지역 근접↑", {"preference": 1.2}),
    (("카페", "외식", "맛집", "배달", "먹"), "외식·카페 소비 성향 → 상권 매치↑", {"consumption": 1.3}),
    (("조용", "한적", "정주", "오래 살"), "정주·생활환경 중시 → 선호지역↑", {"preference": 1.2}),
    (("통근", "출퇴근", "회사", "직장", "가까운 데"), "통근 최소화 우선 → 통근↑", {"commute": 1.3}),
]

# 자유입력이 특정 가구를 시사하는데 폼 선택과 다르면 모순(되묻기). 창작 아닌 사실 대조.
_HOUSEHOLD_HINTS = {
    "자녀": ("아이", "자녀", "학군", "육아", "등원", "등하교", "학교", "어린이집"),
    "신혼": ("결혼", "신혼", "배우자", "부부", "둘이"),
    "1인": ("혼자", "자취", "1인"),
}

_COMMUTE_KEYS = ("통근", "출퇴근", "회사", "직장")


def note_signals(note: str) -> dict:
    """자유입력 → {labels: 반영한 신호, boost: 축별 배수}. 정해진 축만(창작 금지)."""
    note = note or ""
    labels: list[str] = []
    boost: dict[str, float] = {}
    for keys, label, b in _NOTE_MAP:
        if any(k in note for k in keys):
            labels.append(label)
            for axis, mult in b.items():
                boost[axis] = boost.get(axis, 1.0) * mult
    return {"labels": labels, "boost": boost}


def note_weights(household: Optional[str], note: str) -> dict:
    """가구 가중치(scoring.weights_for) × 자유입력 보정 → 재정규화. 스코어가 이걸 쓰면 명확화가 순위에 반영."""
    w = scoring.weights_for(household)
    boost = note_signals(note)["boost"]
    w = {k: v * boost.get(k, 1.0) for k, v in w.items()}
    total = sum(w.values()) or 1.0
    return {k: round(v / total, 3) for k, v in w.items()}


def segment_label(household: Optional[str]) -> str:
    return SEGMENT_LABEL.get(household or "", "임차 가구")


def _household_conflict(household: Optional[str], note: str) -> list[str]:
    """자유입력이 다른 가구유형을 시사하면 되묻기(실사용자 오선택 방지)."""
    out = []
    for seg, keys in _HOUSEHOLD_HINTS.items():
        if seg != household and any(k in note for k in keys):
            out.append(f"'{seg}' 관련 언급이 있는데 가구 유형은 '{household}'로 선택하셨어요. 맞는지 확인해 주세요.")
    return out


def clarify(contract: dict, finance: dict, note: str = "") -> dict:
    """폼값+자유입력 → ClarifyResult(dict). 순수·결정론(LLM seam은 note 해석 확장용).

    반환: {persona, priorities, conflicts, questions, noteSignals}
    """
    household = finance.get("household") or "1인"
    note = note or contract.get("note") or ""

    sig = note_signals(note)
    w = note_weights(household, note)
    priorities = [AXIS_LABEL[k] for k, _ in sorted(w.items(), key=lambda kv: -kv[1])]

    conflicts = _household_conflict(household, note)
    questions = list(conflicts)
    if any(k in note for k in _COMMUTE_KEYS):
        questions.append(
            "통근 발품 정확도를 높이려면 주 근무지를 알려주세요 (지금은 가구 유형 기준 대표 직장으로 가정)."
        )

    return {
        "persona": segment_label(household),
        "priorities": priorities,
        "conflicts": conflicts,
        "questions": questions,
        "noteSignals": sig["labels"],
    }
