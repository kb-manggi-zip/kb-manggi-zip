"""문진 명확화 — 판단 노드(종합명세 §4-2).

역할: 폼값 + 자유입력(자연어)을 **정해진 세그먼트·우선순위 축으로 제약**해 해석하고,
값끼리의 모순(예: 가구유형 ↔ 자유입력 언급)을 감지해 **되묻는다**(닫힌 루프).

두 경로 (llm_active 여부로 분기):
- **LLM 경로**(llm_active): 자유입력 해석을 Claude가 한다. 단 출력은 정해진 축(commute/consumption/
  budget/preference)으로만 제약 — 새 축·항목·숫자 창작 금지. 스키마/제약 위반이면 즉시 키워드 폴백.
- **키워드 폴백**(llm 비활성 or 실패): `_NOTE_MAP` 규칙 매핑. 오프라인/테스트에서 동일 플로우 완주.

안전장치(§4-5 감사 가능성):
- 판단 노드지만 **창작 금지** — LLM이든 키워드든 출력은 위 4축으로 제약.
- **모순 감지 자체는 항상 결정론**(`_household_conflict`). LLM은 감지된 모순의 '되묻기 문구'만 자연스럽게 다듬는다.
- 닫힌 루프: 명확화 → (프론트) 사용자 확정(HITL) → 결정론 계산. 재현·감사 가능(자율계획과 다름).

⚠️ 랭킹/persona는 이 모듈과 별개로 **결정론 keyword 가중치**를 쓴다(persona 결정론 원칙).
   LLM은 여기서 '해석·되묻기·제안 가중치'를 만들어 사용자에게 보여주는 데까지. 둘 다 같은 note에서 출발.
"""

import json
import re
from typing import Optional

from ..core.config import settings
from ..core.llm import generate
from ..tools import scoring

# 스코어 축 → 사람 라벨 (화면·우선순위 표기용)
AXIS_LABEL = {
    "commute": "통근",
    "consumption": "생활·소비",
    "budget": "예산 여유",
    "preference": "선호지역",
}
_AXES = set(AXIS_LABEL)

# 가구 세그먼트 → 표시 라벨
SEGMENT_LABEL = {
    "1인": "1인 청년 임차 가구",
    "신혼": "신혼 가구",
    "자녀": "자녀 양육 가구",
}

# 자유입력 키워드 → (반영 라벨, 축별 가중치 배수). **정해진 항목만** — 폴백 경로 규칙.
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
    (
        ("반려동물", "강아지", "고양이", "반려견", "반려묘"),
        "반려동물 — 산책·생활공간 중시 → 선호지역↑·생활편의↑",
        {"preference": 1.2, "consumption": 1.2},
    ),
    (("학교", "학군", "등하교", "등하원"), "자녀 학군 근접 중시 → 선호지역↑", {"preference": 1.3}),
    (("부모님", "부모님 근처", "가족 근처"), "가족 근접 선호 → 선호지역↑", {"preference": 1.3}),
    # LLM-off 폴백 품질용 확장(방향 명확한 것만)
    (("지하철", "전철", "역 가까", "역세권"), "대중교통 접근 중시 → 통근 편의↑", {"commute": 1.2}),
    (("번화가", "시내", "상권 좋", "핫플"), "번화가·상권 선호 → 상권 매치↑", {"consumption": 1.3}),
    (("한적한 동네", "공원", "산책로", "자연"), "쾌적·정주 환경 선호 → 선호지역↑", {"preference": 1.2}),
]

# 자유입력이 특정 가구를 시사하는데 폼 선택과 다르면 모순(되묻기). 창작 아닌 사실 대조.
_HOUSEHOLD_HINTS = {
    "자녀": ("아이", "자녀", "학군", "육아", "등원", "등하교", "학교", "어린이집"),
    "신혼": ("결혼", "신혼", "배우자", "부부", "둘이"),
    "1인": ("혼자", "자취", "1인"),
}

_COMMUTE_KEYS = ("통근", "출퇴근", "회사", "직장")


def _axis_dir(boost: dict, axis: str) -> int:
    """축 보정 방향: 1=높임, -1=낮춤, 0=변화없음."""
    v = boost.get(axis, 1.0)
    return 1 if v > 1.05 else (-1 if v < 0.95 else 0)


def _intra_note_contradiction(note: str) -> list[str]:
    """한 입력 안에 같은 축을 '높이는+낮추는' 표현이 함께 있으면 되묻기(조용한 상쇄 금지).

    예: '재택근무해요 통근해요' → 통근을 낮추는 재택 + 높이는 통근 → 충돌.
    """
    dirs: dict[str, set] = {}
    for keys, _label, b in _NOTE_MAP:
        if any(k in note for k in keys):
            for axis, mult in b.items():
                d = 1 if mult > 1.05 else (-1 if mult < 0.95 else 0)
                if d:
                    dirs.setdefault(axis, set()).add(d)
    out = []
    for axis, ds in dirs.items():
        if 1 in ds and -1 in ds:
            label = AXIS_LABEL[axis]
            out.append(f"'{label}'을(를) 높이는 표현과 낮추는 표현이 함께 있어요. 어느 쪽으로 반영할지 정해 주세요.")
    return out


def _contradictions(prior_notes: list, note: str) -> list[str]:
    """이전에 반영·확정한 조정과 이번 입력이 축 방향에서 충돌하면 되묻기(조용한 덮어쓰기 금지)."""
    if not prior_notes:
        return []
    prior = note_signals(" ".join(prior_notes))["boost"]
    new = note_signals(note)["boost"]
    out = []
    for axis in _AXES:
        pd, nd = _axis_dir(prior, axis), _axis_dir(new, axis)
        if pd and nd and pd != nd:
            label = AXIS_LABEL[axis]
            was = "낮추기로" if pd < 0 else "높이기로"
            verb = "다시 높일까요" if pd < 0 else "다시 낮출까요"
            out.append(f"이전엔 '{label}'을 {was} 하셨는데 이번엔 반대네요. {label} 비중을 {verb}?")
    return out


# ── 키워드 폴백 경로 ──────────────────────────────────────────────────
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


def _apply_boost(w: dict, boost: dict) -> dict:
    """가중치 × 축별 배수 → 재정규화(합=1)."""
    w = {k: v * boost.get(k, 1.0) for k, v in w.items()}
    total = sum(w.values()) or 1.0
    return {k: round(v / total, 3) for k, v in w.items()}


def note_weights(household: Optional[str], note: str, adjust: Optional[dict] = None) -> dict:
    """가구 가중치 × 보정 → 재정규화. **persona/랭킹이 쓰는 결정론 경로.**

    adjust(=HITL로 확정된 축별 배수)가 있으면 그걸 쓰고(자연어→LLM 해석 확정분까지 반영),
    없으면 note 키워드로 보정(LLM-off 폴백). 둘 다 결정론.

    단, **미확정 입력에 축 내부 상충(예: 재택+통근)이 있으면 반영 보류**(B1) — 자기상쇄된
    boost가 조용히 랭킹을 흔드는 걸 막는다. 사용자가 HITL로 확정(adjust 전달)하면 그때 반영.
    """
    if adjust:
        boost = adjust
    elif note and (_intra_note_contradiction(note) or _household_conflict(household, note)):
        boost = {}  # 미해결 상충 → 반영 보류(조용한 상쇄 금지). base 가중치 그대로.
    else:
        boost = note_signals(note)["boost"]
    return _apply_boost(scoring.weights_for(household), boost)


# ── LLM 경로 (제약된 해석) ────────────────────────────────────────────
_CLARIFY_SYSTEM = (
    "너는 주거상담 문진 보조다. 사용자의 자유입력 한 문장을 읽고 '주거 선택 가중치 축'에 대한 "
    "영향만 판단해 JSON으로 답한다. 규칙(반드시 준수):\n"
    "- 축은 정확히 이 넷만: commute(통근), consumption(생활·소비), budget(예산), preference(선호지역).\n"
    "- weight_adjustments는 {축: 배수}, 배수는 0.3~2.0 실수(1.0=변화없음, <1 낮춤, >1 높임). 해당 없으면 빈 객체.\n"
    "- 새 축·새 항목·구체 숫자(금액/개수)를 창작하지 마라.\n"
    "- interpretation은 반영 이유를 한국어 짧은 구절 배열로(없으면 빈 배열).\n"
    "- question은 '감지된 모순'이 주어졌을 때만 그 사실에 근거한 자연스러운 되묻기 한 문장, 없으면 빈 문자열.\n"
    '출력은 오직 JSON 하나: {"interpretation": [..], "weight_adjustments": {..}, "question": ".."}'
)


def _extract_json(text: str) -> Optional[dict]:
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _llm_interpret(note: str, household: Optional[str], conflict_facts: list[str]) -> Optional[dict]:
    """llm_active일 때만. 스키마/제약 위반 시 None → 키워드 폴백. 반환 {labels, boost, question}."""
    user = (
        f"자유입력: {note}\n"
        f"가구유형(폼 선택): {household}\n"
        f"코드가 감지한 모순(있으면 이 사실에만 근거해 question 작성): {conflict_facts or '없음'}\n"
    )
    raw = generate(system=_CLARIFY_SYSTEM, user=user, fallback=lambda: "")  # 비활성이면 ""
    data = _extract_json(raw)
    if data is None:
        return None
    wa = data.get("weight_adjustments") or {}
    interp = data.get("interpretation") or []
    if not isinstance(wa, dict) or not isinstance(interp, list):
        return None
    # 제약 검증: 축 밖 키 또는 범위 밖 배수 → 위반 → 폴백(창작 차단)
    for k, v in wa.items():
        if k not in _AXES or not isinstance(v, (int, float)) or isinstance(v, bool) or not (0.3 <= float(v) <= 2.0):
            return None
    return {
        "labels": [str(x) for x in interp],
        "boost": {k: float(v) for k, v in wa.items()},
        "question": str(data.get("question") or "").strip(),
    }


# ── 공통 ──────────────────────────────────────────────────────────────
def segment_label(household: Optional[str]) -> str:
    return SEGMENT_LABEL.get(household or "", "임차 가구")


def _household_conflict(household: Optional[str], note: str) -> list[str]:
    """자유입력이 다른 가구유형을 시사하면 되묻기(실사용자 오선택 방지). **항상 결정론.**

    household가 None/빈값(=가구 유형 미선택)이면 대조 불가 → [] (J1: 미선택 필드는 상충 대상 제외).
    """
    if not household:
        return []
    out = []
    for seg, keys in _HOUSEHOLD_HINTS.items():
        if seg != household and any(k in note for k in keys):
            out.append(f"'{seg}' 관련 언급이 있는데 가구 유형은 '{household}'로 선택하셨어요. 맞는지 확인해 주세요.")
    return out


# 같은 입력 재계산(특히 LLM 재호출) 방지 — /api/persona가 화면마다 clarify를 부르므로 캐시 효과 큼.
_CLARIFY_CACHE: dict = {}
_CLARIFY_CACHE_MAX = 512


def clarify(contract: dict, finance: dict, note: str = "", prior_notes: Optional[list] = None) -> dict:
    """폼값+자유입력 → ClarifyResult(dict).

    prior_notes: 이미 반영·확정한 자유입력들. 이번 입력이 이와 축 방향에서 충돌하면 되묻는다.
    반환: {persona, priorities, conflicts, questions, noteSignals}
    """
    household_sel = finance.get("household")  # None/빈값 = 사용자가 아직 미선택(J1)
    household = household_sel or "1인"  # 가중치·세그먼트 기본값(표시용). 상충 감지엔 household_sel만 쓴다.
    note = note or contract.get("note") or ""

    # 캐시 조회 (같은 입력 → 같은 결과. LLM 호출도 여기서 스킵)
    # household_sel(미선택 None vs 선택 '1인')을 키에 포함 — 상충 결과가 달라 캐시 충돌 방지.
    ckey = (note, household_sel, tuple(prior_notes or ()), settings.llm_active)
    hit = _CLARIFY_CACHE.get(ckey)
    if hit is not None:
        return dict(hit)

    # 1) 모순 감지 = 항상 결정론. 가구 불일치는 **선택된 값끼리만**(미선택이면 household_sel=None → 스킵, J1).
    conflicts = (
        _household_conflict(household_sel, note)
        + _intra_note_contradiction(note)
        + _contradictions(prior_notes or [], note)
    )

    # 2) 신호 라벨 + 적용 boost = LLM(축 제약) 우선, 실패/비활성 시 키워드.
    llm = _llm_interpret(note, household, conflicts) if (note and settings.llm_active) else None
    if llm is not None:
        labels, boost, llm_question = llm["labels"], llm["boost"], llm["question"]
    else:
        sig = note_signals(note)
        labels, boost, llm_question = sig["labels"], sig["boost"], ""

    # weightAdjust = 이 입력의 '적용 boost'(축 제약). 사용자가 HITL로 확정하면 이게 랭킹에 실린다(결정론·재현가능).
    # priorities도 같은 boost로 → 화면 우선순위 = 실제 동네 랭킹.
    w = _apply_boost(scoring.weights_for(household), boost)
    priorities = [AXIS_LABEL[k] for k, _ in sorted(w.items(), key=lambda kv: -kv[1])]

    # 3) 되묻기: 감지는 결정론, 문구만 LLM(감지된 모순이 있을 때만 자연 문장으로 대체)
    questions = [llm_question] if (llm_question and conflicts) else list(conflicts)
    if any(k in note for k in _COMMUTE_KEYS):
        questions.append(
            "통근 발품 정확도를 높이려면 주 근무지를 알려주세요 (지금은 가구 유형 기준 대표 직장으로 가정)."
        )

    result = {
        "persona": segment_label(household),
        "weightAdjust": boost,  # 확정 시 랭킹에 실릴 축별 배수(HITL 확정분만 반영)
        "held": bool(conflicts),  # 상충 미해결 → 자동 반영 보류(UI '확인 대기'). 확정 전엔 랭킹 미반영.
        "priorities": priorities,
        "conflicts": conflicts,
        "questions": questions,
        "noteSignals": labels,
    }
    if len(_CLARIFY_CACHE) >= _CLARIFY_CACHE_MAX:
        _CLARIFY_CACHE.clear()
    _CLARIFY_CACHE[ckey] = result
    return dict(result)
