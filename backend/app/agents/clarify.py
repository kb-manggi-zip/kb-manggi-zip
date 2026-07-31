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
import logging
import re
from functools import lru_cache
from typing import Optional

from ..core.config import settings
from ..core.llm import generate
from ..schemas import RenewalSituation
from ..tools import scoring

log = logging.getLogger("clarify")
_SITUATION_VALUES = {e.value for e in RenewalSituation}  # 닫힌 enum — LLM 출력 검증용

# 스코어 축 → 사람 라벨 (화면·우선순위 표기용)
AXIS_LABEL = {
    "commute": "통근",
    "consumption": "생활·소비",
    "budget": "예산 여유",
    "preference": "선호지역",
}
_AXES = set(AXIS_LABEL)


# ── 방향(닫힌 enum) → 배수: 크기는 rules/axis_adjust.yaml 고정(LLM 생성 금지, 재현성) ──
@lru_cache(maxsize=1)
def _axis_adjust_cfg() -> dict:
    from ..core.rules import read_yaml

    doc = read_yaml("axis_adjust.yaml")
    if doc.get("checked_at") in (None, "", "null"):
        log.warning("axis_adjust.yaml 미검증(checked_at 없음)")
    return doc


def dir_mult(direction: str) -> float:
    """방향 → 배수(yaml). 알 수 없는 값이면 1.0(변화 없음)."""
    entry = (_axis_adjust_cfg().get("directions") or {}).get(str(direction))
    return float(entry["multiplier"]) if entry else 1.0


def dir_sign(direction: str) -> int:
    """방향 부호: up류=+1, down류=-1, 그 외 0."""
    d = str(direction)
    return 1 if d in ("up", "strong_up") else (-1 if d in ("down", "strong_down") else 0)


_DIRECTIONS = {"strong_up", "up", "down", "strong_down"}  # LLM 출력 검증용(닫힌 집합)

# 가구 세그먼트 → 표시 라벨
SEGMENT_LABEL = {
    "1인": "1인 청년 임차 가구",
    "신혼": "신혼 가구",
    "자녀": "자녀 양육 가구",
}

# 카페·외식 소비 성향 키워드 — _NOTE_MAP(가중치 보정)과 note_values_food(실제 성향 판정)가 공유.
# 하나의 목록만 유지해 "중요도만 올라가고 실제 판정은 안 바뀌는" 드리프트를 구조적으로 막는다.
_CAFE_KEYWORDS = ("카페", "외식", "맛집", "배달", "먹")
# "번화가/상권 선호"도 개념상 같은 축(consumption=외식·카페 밀집도)을 가리키는 표현이라 동일 취급.
# 별도 그룹인 이유: _NOTE_MAP의 반영 라벨 문구("번화가·상권 선호")를 카페 라벨과 다르게 유지하기 위함.
_COMMERCIAL_KEYWORDS = ("번화가", "시내", "상권 좋", "핫플")
# 장보기·여가 성향 키워드 — note_values_grocery/note_values_leisure과 _NOTE_MAP이 공유.
_GROCERY_KEYWORDS = ("장보기", "마트", "시장")
_LEISURE_KEYWORDS = ("여가", "취미", "운동", "산책", "나들이")

# 자유입력 키워드 → (반영 라벨, 축별 가중치 배수). **정해진 항목만** — 폴백 경로 규칙.
# 배수는 '감'이 아니라 방향만(↑/↓) 부여하는 보정 — 재정규화되므로 절대크기 아닌 상대조정.
# 폴백 키워드 → 축 '방향'(닫힌 enum). 크기는 axis_adjust.yaml에서 dir_mult로 변환(LLM 경로와 동일 배수 테이블).
_NOTE_MAP: list[tuple[tuple[str, ...], str, dict]] = [
    (
        ("재택", "집에서", "집 주변", "동네에서", "근처에서"),
        "재택·동네생활 중시 → 통근 거의 고려 안 함·생활편의↑",
        {"commute": "strong_down", "consumption": "up"},
    ),
    (("자차", "차로", "운전", "차 있"), "자차 이동 → 통근시간 민감도↓", {"commute": "down"}),
    (("도보", "걸어", "걸어서"), "도보 생활권 선호 → 선호지역 근접↑", {"preference": "up"}),
    (_CAFE_KEYWORDS, "외식·카페 소비 성향 → 상권 매치↑", {"consumption": "up"}),
    (("조용", "한적", "정주", "오래 살"), "정주·생활환경 중시 → 선호지역↑", {"preference": "up"}),
    (("통근", "출퇴근", "회사", "직장", "가까운 데"), "통근 최소화 우선 → 통근↑", {"commute": "up"}),
    (
        ("반려동물", "강아지", "고양이", "반려견", "반려묘"),
        "반려동물 — 산책·생활공간 중시 → 선호지역↑·생활편의↑",
        {"preference": "up", "consumption": "up"},
    ),
    (("학교", "학군", "등하교", "등하원"), "자녀 학군 근접 중시 → 선호지역↑", {"preference": "up"}),
    (("부모님", "부모님 근처", "가족 근처"), "가족 근접 선호 → 선호지역↑", {"preference": "up"}),
    # LLM-off 폴백 품질용 확장(방향 명확한 것만)
    (("지하철", "전철", "역 가까", "역세권"), "대중교통 접근 중시 → 통근 편의↑", {"commute": "up"}),
    (("번화가", "시내", "상권 좋", "핫플"), "번화가·상권 선호 → 상권 매치↑", {"consumption": "up"}),
    (("한적한 동네", "공원", "산책로", "자연"), "쾌적·정주 환경 선호 → 선호지역↑", {"preference": "up"}),
    (_GROCERY_KEYWORDS, "장보기 성향 → 생활상권 매치↑", {"consumption": "up"}),
    (_LEISURE_KEYWORDS, "여가 활동 선호 → 생활상권 매치↑", {"consumption": "up"}),
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
            for axis, direction in b.items():
                d = dir_sign(direction)
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
            for axis, direction in b.items():
                boost[axis] = boost.get(axis, 1.0) * dir_mult(direction)  # 방향→yaml 배수(LLM 경로와 동일 테이블)
    return {"labels": labels, "boost": boost}


def note_directions(note: str) -> dict:
    """폴백 경로의 축별 '방향'(weightAdjust 형태). 같은 축 여러 신호면 더 강한 방향 유지.
    LLM 경로와 동일하게 '방향'을 산출 → 확정 시 note_weights가 같은 yaml 배수로 변환."""
    note = note or ""
    out: dict[str, str] = {}
    for keys, _label, b in _NOTE_MAP:
        if any(k in note for k in keys):
            for axis, direction in b.items():
                if axis not in out or abs(dir_mult(direction) - 1) > abs(dir_mult(out[axis]) - 1):
                    out[axis] = direction
    return out


# ── 갱신 인상률 파싱 + 상담 사정 보존 (작업 A·B) ──────────────────────────────
def extract_renewal_pct(note: str) -> Optional[int]:
    """자유입력에서 '집주인이 요구한 인상률'을 추출. '7% 올려달래요' → 7. 없으면 None.
    ★ 숫자는 '제안'으로만 반환한다 — 계산엔 HITL 확정 후 compare가 min(X,5%)로 재사용(직행 금지)."""
    if not note:
        return None
    # '올리다' 계열(올려/올리고/올린대/올릴/올렸/올랐) 또는 '인상' 맥락일 때만(단순 % 언급·전세가율 등은 무시)
    if not any(k in note for k in ("올려", "올리", "올랐", "올렸", "올릴", "인상")):
        return None
    m = re.search(r"(\d{1,2}(?:\.\d)?)\s*(?:%|퍼센트|프로)", note)
    if not m:
        return None
    try:
        v = float(m.group(1))
    except ValueError:
        return None
    return int(round(v)) if 0 < v <= 100 else None


# 상담 전달 사정 키워드 — 계산 불가한 법률·협의 영역(보수적: 이 '구체' 키워드가 든 문장만 전달).
# ※ '집주인/임대인'처럼 포괄적인 말은 제외 — 모든 인상률 요청에 붙어 순수 인상률까지 상담메모로 새는 걸 막음.
_CONSULT_KEYS = (
    "갱신요구권",
    "갱신권",
    "실거주",
    "실입주",
    "직접 살",
    "수리",
    "보수",
    "누수",
    "곰팡이",
    "특약",
    "보증금 반환",
    "돌려주",
    "재계약",
    "명도",
    "퇴거",
    "갱신 거절",
    "거절당",
    "소송",
    "내용증명",
    "연락이 안",
    "안 해줘",
    "안해줘",
)


def extract_consult_note(note: str) -> str:
    """4축·인상률로 해석 못한 '갱신·주거 사정' 문장만 원문 그대로 보존(상담 전달용).
    판단 기준(보수적): 상담 키워드가 든 문장만. 잡담('날씨 좋네요')은 키워드 없어 제외. LLM 요약·재작성 없음."""
    if not note:
        return ""
    keep = [s.strip() for s in _split_notes(note) if any(k in s for k in _CONSULT_KEYS)]
    return " · ".join(keep)


# 갱신 상황 키워드 폴백(LLM 비활성/실패 시). 문장 단위로 닫힌 enum에 매핑. 매칭 없는 갱신 사정 → unknown.
_SITUATION_KEYWORDS = (
    (RenewalSituation.notice_deadline_passed, ("통보 없었", "통보가 없", "통보 안 ", "통보를 안", "묵시적")),
    (
        RenewalSituation.renewal_right_exhausted,
        ("이미 갱신", "한 번 썼", "갱신권 썼", "갱신요구권 사용", "갱신권 사용", "이미 사용"),
    ),
    (RenewalSituation.jeonse_to_monthly, ("월세로 돌리", "전세를 월세", "월세로 바꾸", "월세로 전환", "반전세")),
    (RenewalSituation.landlord_self_occupancy, ("실거주", "실입주", "직접 살", "본인이 들어", "직계")),
    (RenewalSituation.term_change, ("계약기간", "기간을 바꾸", "기간 변경", "1년만", "2년으로")),
)


def extract_situations(note: str) -> tuple[list, dict]:
    """자유입력 → (상황 enum 목록, {상황 id: 원문 구절}). 원문 그대로 보존(요약 금지).
    특정 상황 키워드 매칭 우선, 매칭 없지만 갱신·주거 사정(_CONSULT_KEYS)이면 unknown(계산 미반영)."""
    situations: list = []
    evidence: dict = {}
    if not note:
        return situations, evidence
    for sent in _split_notes(note):
        s = sent.strip()
        matched = None
        for sit, keys in _SITUATION_KEYWORDS:
            if any(k in s for k in keys):
                matched = sit
                break
        if matched is None and any(k in s for k in _CONSULT_KEYS):
            matched = RenewalSituation.unknown  # 갱신 사정이나 분류 불가 → consultNote 창구
        if matched is not None and matched.value not in evidence:
            situations.append(matched)
            evidence[matched.value] = s
    return situations, evidence


_CONVERSION_CTX = ("월세로 돌리", "전세를 월세", "월세로 바꾸", "월세로 전환", "전환")


def extract_conversion_amount(note: str) -> Optional[int]:
    """자유입력에서 '보증금을 월세로 돌리려는 감액분'을 원 단위로 추출(전환 맥락일 때만).
    '1억'=1e8, '1억5천'=1.5e8, '5천만'=5e7, '3000만'=3e7. 없으면 None. LLM 프리필의 오프라인 폴백."""
    if not note or not any(k in note for k in _CONVERSION_CTX):
        return None
    won = 0
    m = re.search(r"(\d+(?:\.\d+)?)\s*억", note)
    if m:
        won += int(round(float(m.group(1)) * 100_000_000))
    if "천" in note:
        m = re.search(r"(\d+)\s*천\s*만?", note)  # '5천만'·'억 5천' → 천만 단위
        if m:
            won += int(m.group(1)) * 10_000_000
    else:
        m = re.search(r"(\d+)\s*만", note)
        if m:
            won += int(m.group(1)) * 10_000
    return won if won > 0 else None


def note_values_food(note: str) -> Optional[bool]:
    """자유입력에서 카페·외식 소비 성향 직접 감지 → score_consumption의 values_food 판정.

    기존엔 자유입력이 consumption '가중치'(중요도)만 올리고, 그 가중치가 곱해지는 '판정'
    (values_food)은 세그먼트 평균(spending_profiles traits)에만 의존해 — "카페 좋아한다"고
    말해도 세그먼트 평균이 아니라고 하면 판정이 안 바뀌는 불일치가 있었다.

    personal_traits.py 문서화된 증거 위계("1위 본인 진술+HITL / 2위 개인 실측 / 3위 세그먼트")의
    1위가 실제로는 구현된 적이 없었음 — 이 함수가 그 빈 자리를 채운다(tools/persona.py에서 실측보다도
    우선 적용). 부정 표현(카페 싫어함)은 아직 감지하지 않음 — 침묵/반대를 False로 단정하지 않고
    True 아니면 None(판단 보류, 하위 tier에 위임)만 반환한다.

    "번화가/상권 선호"(_COMMERCIAL_KEYWORDS)도 개념상 같은 축(외식·카페 밀집도)을 가리키므로
    함께 감지한다. 단 "재택"·"반려동물"은 같은 consumption 가중치를 올리지만 사유가 다르므로
    (생활편의·산책공간이지 외식·카페가 아님) 여기 포함하지 않는다.
    """
    note = note or ""
    return True if any(k in note for k in _CAFE_KEYWORDS + _COMMERCIAL_KEYWORDS) else None


def note_values_grocery(note: str) -> Optional[bool]:
    """자유입력에서 장보기 성향 직접 감지 → score_consumption의 그로서리 게이트. note_values_food와 동일 패턴."""
    note = note or ""
    return True if any(k in note for k in _GROCERY_KEYWORDS) else None


def note_values_leisure(note: str) -> Optional[bool]:
    """자유입력에서 여가 성향 직접 감지 → score_consumption의 여가 게이트. note_values_food와 동일 패턴."""
    note = note or ""
    return True if any(k in note for k in _LEISURE_KEYWORDS) else None


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
        # 확정된 '방향'(AxisDirection) → yaml 고정 배수 + 클램프. 곱셈·정규화는 _apply_boost 그대로.
        cfg = _axis_adjust_cfg()
        clamp = cfg.get("clamp") or {"min": 0.3, "max": 2.0}
        lo, hi = float(clamp["min"]), float(clamp["max"])
        boost = {ax: max(lo, min(hi, dir_mult(d))) for ax, d in adjust.items()}
    elif note and (_intra_note_contradiction(note) or _household_conflict(household, note)):
        boost = {}  # 미해결 상충 → 반영 보류(조용한 상쇄 금지). base 가중치 그대로.
    else:
        boost = note_signals(note)["boost"]  # 폴백도 dir_mult로 변환된 배수(LLM 경로와 동일)
    return _apply_boost(scoring.weights_for(household), boost)


# ── LLM 경로 (제약된 해석) ────────────────────────────────────────────
_CLARIFY_SYSTEM = (
    "너는 주거상담 문진 보조다. 사용자의 자유입력 한 문장을 읽고 '주거 선택 가중치 축'에 대한 "
    "영향만 판단해 JSON으로 답한다. 규칙(반드시 준수):\n"
    "- 축은 정확히 이 넷만: commute(통근), consumption(생활·소비), budget(예산), preference(선호지역).\n"
    "- weight_adjustments는 {축: 방향}. 방향은 정확히 이 넷 중 하나(★배수 숫자 금지): "
    "strong_up(매우 중요), up(더 중요), down(덜 중요), strong_down(거의 고려 안 함). 해당 없으면 빈 객체.\n"
    '  예: \'재택근무예요\'→{"commute":"strong_down"}, \'아이 학교가 중요해요\'→{"preference":"up"}, '
    '\'매일 통근해요\'→{"commute":"up"}.\n'
    "- 새 축·새 항목·구체 숫자(금액/개수/배수)를 창작하지 마라. 방향은 위 4종 목록 밖 값 금지.\n"
    "- interpretation은 반영 이유를 한국어 짧은 구절 배열로(없으면 빈 배열).\n"
    "- question은 '감지된 모순'이 주어졌을 때만 그 사실에 근거한 자연스러운 되묻기 한 문장, 없으면 빈 문자열.\n"
    "- renewal_ask_pct: 집주인이 요구한 갱신 인상률을 **입력에서 읽어** 정수 %로(예 '두 배로'=100, '7% 올려'=7). "
    "없으면 null. ★입력에 근거해 읽는 것만 허용 — 없는 숫자를 지어내지 마라.\n"
    "- consult_note: 가중치·인상률로 계산 불가한 갱신·주거 사정(실거주 거절·수리·보증금 반환·갱신권 등)이 있으면 "
    "**입력 문장을 그대로 인용**(요약·재작성·번역 금지). 없으면 빈 문자열. 잡담은 넣지 마라.\n"
    "- renewal_situations: 갱신 관련 사정이 있으면 아래 '닫힌 목록'의 id만 배열로. "
    "★목록 밖 값·새 id 창작 금지. 없으면 빈 배열.\n"
    "  목록: notice_deadline_passed(임대인이 갱신 통보를 기한 내 안 함/묵시적), "
    "renewal_right_exhausted(갱신요구권 이미 사용·소진), "
    "jeonse_to_monthly(전세를 월세로 전환 요구), "
    "landlord_self_occupancy(임대인 본인·직계 실거주 이유로 갱신 거절), "
    "term_change(계약기간 변경 요구), simple_increase(단순 % 인상 합의), unknown(갱신 사정이나 위로 분류 불가).\n"
    "- situation_evidence: {상황 id: 그 분류의 근거가 된 사용자 원문 구절}. "
    "**그대로 인용**(요약 금지). 분류한 상황만.\n"
    "- conversion_amount: 보증금을 월세로 돌리려는 금액이 있으면 원 단위 정수로"
    "(예 '1억'=100000000, '5천만'=50000000). 없으면 null. ★입력에 근거해서만.\n"
    '출력은 오직 JSON 하나: {"interpretation": [..], "weight_adjustments": {..}, "question": "..", '
    '"renewal_ask_pct": null, "consult_note": "", "renewal_situations": [], "situation_evidence": {}, '
    '"conversion_amount": null}'
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
    # 방향 검증: 축이 4개 안 + 방향이 닫힌 enum인 것만 채택.
    # 밖 값은 '그 축만' 폐기(전체 폴백 아님, 갱신 상황 규약과 동일).
    directions = {k: v for k, v in wa.items() if k in _AXES and isinstance(v, str) and v in _DIRECTIONS}
    # 인상률: LLM이 읽은 정수만 채택(0~100). 범위 밖·타입 이상 → None(계산 미반영, HITL 제안 없음).
    ask = data.get("renewal_ask_pct")
    ask_pct = int(ask) if isinstance(ask, (int, float)) and not isinstance(ask, bool) and 0 < ask <= 100 else None
    # 갱신 상황: 닫힌 enum만 채택. enum 밖 값은 '그 값만' 폐기(전체 폴백 아님).
    raw_sit = data.get("renewal_situations") or []
    situations = (
        [s for s in raw_sit if isinstance(s, str) and s in _SITUATION_VALUES] if isinstance(raw_sit, list) else []
    )
    raw_ev = data.get("situation_evidence") or {}
    evidence = (
        {k: str(v) for k, v in raw_ev.items() if k in _SITUATION_VALUES and isinstance(v, str) and v.strip()}
        if isinstance(raw_ev, dict)
        else {}
    )
    conv = data.get("conversion_amount")
    conv_amt = int(conv) if isinstance(conv, (int, float)) and not isinstance(conv, bool) and conv > 0 else None
    return {
        "labels": [str(x) for x in interp],
        "boost": directions,  # {축: 방향}(닫힌 enum). 크기는 note_weights가 yaml에서 변환
        "question": str(data.get("question") or "").strip(),
        "renewalAskPct": ask_pct,
        "consultNote": str(data.get("consult_note") or "").strip(),  # 원문 인용(요약 금지 프롬프트로 강제)
        "renewalSituations": situations,  # 닫힌 enum 분류(밖 값 폐기)
        "situationEvidence": evidence,  # 상황 id → 원문 구절
        "conversionAmount": conv_amt,  # 보증금→월세 전환 감액분(원) 제안
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


def clarify(
    contract: dict,
    finance: dict,
    note: str = "",
    prior_notes: Optional[list] = None,
    household_selected: bool = True,
) -> dict:
    """폼값+자유입력 → ClarifyResult(dict).

    prior_notes: 이미 반영·확정한 자유입력들. 이번 입력이 이와 축 방향에서 충돌하면 되묻는다.
    household_selected: 사용자가 가구 유형을 **실제 선택**했는지. False(문진 초반 미선택)면 가구 상충 감지 스킵(J1).
      (household는 스키마상 항상 유효값이 오므로, 선택 여부는 이 플래그로만 판별한다.)
    반환: {persona, priorities, conflicts, questions, noteSignals}
    """
    household = finance.get("household") or "1인"  # 가중치·세그먼트 기본값(표시용)
    household_for_conflict = household if household_selected else None  # 미선택이면 대조 제외(J1)
    note = note or contract.get("note") or ""

    # 캐시 조회 (같은 입력 → 같은 결과. LLM 호출도 여기서 스킵)
    # household_selected를 키에 포함 — 선택 여부에 따라 상충 결과가 달라 캐시 충돌 방지.
    ckey = (note, household, household_selected, tuple(prior_notes or ()), settings.llm_active)
    hit = _CLARIFY_CACHE.get(ckey)
    if hit is not None:
        return dict(hit)

    # 1) 모순 감지 = 항상 결정론. 가구 불일치는 **선택된 값일 때만**(미선택이면 household_for_conflict=None → 스킵, J1).
    conflicts = (
        _household_conflict(household_for_conflict, note)
        + _intra_note_contradiction(note)
        + _contradictions(prior_notes or [], note)
    )

    # 2) 신호 라벨 + 적용 boost = LLM(축 제약) 우선, 실패/비활성 시 키워드.
    llm = _llm_interpret(note, household, conflicts) if (note and settings.llm_active) else None
    if llm is not None:
        # LLM primary: 자연어를 읽어 4축 '방향'·인상률·상담 사정을 뽑는다(크기는 yaml 고정).
        labels, boost, llm_question = llm["labels"], llm["boost"], llm["question"]  # boost = {축: 방향}
        ask_pct, consult = llm["renewalAskPct"], llm["consultNote"]
        situations, evidence = llm["renewalSituations"], llm["situationEvidence"]
        conv_amt = llm["conversionAmount"]
    else:
        # 폴백(LLM 비활성/실패): 키워드로 오프라인 완주. 방향도 동일 산출(LLM 경로와 같은 배수 테이블).
        sig = note_signals(note)
        labels, llm_question = sig["labels"], ""
        boost = note_directions(note)  # {축: 방향} — LLM 경로와 형식·테이블 동일
        ask_pct, consult = extract_renewal_pct(note), extract_consult_note(note)
        sit_list, evidence = extract_situations(note)
        situations = [s.value for s in sit_list]  # enum → str(계약 일관)
        conv_amt = extract_conversion_amount(note)

    # weightAdjust = 이 입력의 '방향'(닫힌 enum). HITL 확정 시 랭킹에 실린다(결정론·재현가능).
    # priorities는 방향→yaml 배수로 변환해 산출 → 화면 우선순위 = 실제 동네 랭킹.
    boost_mult = {ax: dir_mult(d) for ax, d in boost.items()}
    w = _apply_boost(scoring.weights_for(household), boost_mult)
    priorities = [AXIS_LABEL[k] for k, _ in sorted(w.items(), key=lambda kv: -kv[1])]

    # 3) 되묻기: 감지는 결정론, 문구만 LLM(감지된 모순이 있을 때만 자연 문장으로 대체)
    questions = [llm_question] if (llm_question and conflicts) else list(conflicts)
    if any(k in note for k in _COMMUTE_KEYS):
        questions.append(
            "통근 발품 정확도를 높이려면 주 근무지를 알려주세요 (지금은 가구 유형 기준 대표 직장으로 가정)."
        )

    result = {
        "persona": segment_label(household),
        "weightAdjust": boost,  # 확정 시 랭킹에 실릴 축별 '방향'(HITL 확정분만 반영, 크기는 yaml)
        "held": bool(conflicts),  # 상충 미해결 → 자동 반영 보류(UI '확인 대기'). 확정 전엔 랭킹 미반영.
        "priorities": priorities,
        "conflicts": conflicts,
        "questions": questions,
        "noteSignals": labels,
        "renewalAskPct": ask_pct,  # LLM이 읽은 '제안'(폴백은 정규식) — 확정 후 compare가 씀
        "consultNote": consult,  # LLM이 고른 원문 사정(폴백은 키워드) — 상담 전달
        "renewalSituations": situations,  # 닫힌 enum 분류 '제안'(확정 전 계산 미반영)
        "situationEvidence": evidence,  # 상황 id → 원문 구절(그대로)
        "conversionAmount": conv_amt,  # 보증금→월세 전환 감액분(원) '제안'(프리필용)
    }
    if len(_CLARIFY_CACHE) >= _CLARIFY_CACHE_MAX:
        _CLARIFY_CACHE.clear()
    _CLARIFY_CACHE[ckey] = result
    return dict(result)


# ── 최종 프로필 종합검증 (SC-14) — 누적 자유입력 전체를 한 번에 의미 검증 ─────────────
# 반환 conflictItems = 인라인 해소용 구조(K1/K4). 각 항목: 상충하는 두 신호 + 되묻는 질문.
_VALIDATE_SYSTEM = (
    "너는 주거상담 '최종 프로필' 검증기다. 사용자가 문진에서 담아둔 문장들과 폼값(가구 유형·예산)을 "
    "함께 보고, **서로 모순되는 문장 쌍만** 찾아 JSON으로 답한다. 규칙(반드시 준수):\n"
    "- 새 사실·새 축·구체 숫자를 창작하지 마라. 주어진 문장과 폼값만 대조한다.\n"
    "- **가구 유형(1인/신혼/자녀) 불일치는 다루지 마라(별도 처리). 담아둔 '문장끼리'의 축 상충만 찾아라.**\n"
    "- 축은 정확히 이 넷만: commute(통근), consumption(생활·소비), budget(예산), preference(선호지역).\n"
    "- conflicts: 상충 있으면 [{optionA:'문장 그대로', optionB:'상충하는 문장 그대로', axis:'축', "
    "question:'무엇과 무엇이 부딪히는지 짧게'}] — optionA/optionB는 반드시 입력 문장을 그대로 인용. 없으면 [].\n"
    "- weight_adjustments: 진술로 조정할 축 {축: 배수(0.3~2.0)} — 없으면 빈 객체.\n"
    "- interpretation: 반영 이유를 한국어 짧은 구절 배열로(없으면 빈 배열).\n"
    '출력은 오직 JSON: {"conflicts":[{"optionA":"..","optionB":"..","axis":"..","question":".."}], '
    '"weight_adjustments":{}, "interpretation":[]}'
)


def _split_notes(note: str) -> list[str]:
    """누적 자유입력(문진에서 ' · '로 합침) → 개별 문장 리스트."""
    return [n.strip() for n in (note or "").replace(" · ", "\x00").split("\x00") if n.strip()]


def _household_conflict_items(notes: list[str], household: Optional[str], accepted: set) -> list[dict]:
    """가구 불일치 = **사실 대조(결정론)**. 선택된 가구 ↔ 자유입력이 시사하는 가구가 다르면 되묻기.

    optionA/optionB에 가구 유형 '값'을 실어 프론트가 문진 복귀 없이 finance.household를 바꿀 수 있게 한다.
    """
    if not household:
        return []
    items: list[dict] = []
    seen: set = set()
    for n in notes:
        for seg, keys in _HOUSEHOLD_HINTS.items():
            if seg != household and seg not in seen and any(k in n for k in keys):
                if frozenset((household, seg)) in accepted:
                    continue
                seen.add(seg)
                items.append(
                    {
                        "type": "household",
                        "axis": "",
                        "optionA": household,  # 값(프론트가 라벨 변환)
                        "optionB": seg,
                        "question": f"'{n}' — 가구 유형이 '{SEGMENT_LABEL.get(household, household)}'가 맞나요?",
                        "allowBoth": False,
                    }
                )
    return items


def _axis_conflict_items_kw(notes: list[str], accepted: set) -> list[dict]:
    """축 상충(간이 검증, 키워드) — 두 문장이 같은 축을 반대 방향으로 밀면 되묻기. optionA/optionB=문장 원문."""
    items: list[dict] = []
    sigs = [(n, note_signals(n)["boost"]) for n in notes]
    for i in range(len(sigs)):
        for j in range(i + 1, len(sigs)):
            na, ba = sigs[i]
            nb, bb = sigs[j]
            if frozenset((na, nb)) in accepted:
                continue
            for axis in _AXES:
                da, db = _axis_dir(ba, axis), _axis_dir(bb, axis)
                if da and db and da != db:
                    items.append(
                        {
                            "type": "axis",
                            "axis": axis,
                            "optionA": na,
                            "optionB": nb,
                            "question": f"'{na}' ↔ '{nb}' — '{AXIS_LABEL[axis]}'에서 서로 반대예요.",
                            "allowBoth": True,
                        }
                    )
                    break
    for n in notes:  # 한 문장 안에 반대 방향(예: '재택인데 통근') → 인라인은 '둘 다'/정정
        if _intra_note_contradiction(n) and frozenset((n,)) not in accepted:
            items.append(
                {
                    "type": "intra",
                    "axis": "",
                    "optionA": n,
                    "optionB": "",
                    "question": f"'{n}' 안에 서로 반대되는 내용이 있어요.",
                    "allowBoth": True,
                }
            )
    return items


def _match_note(opt: str, notes: list[str]) -> Optional[str]:
    """LLM이 인용한 문자열 → 실제 담아둔 문장으로 매핑(정확 → 포함 순). 매칭 없으면 None."""
    opt = (opt or "").strip()
    if not opt:
        return None
    for n in notes:  # 정확 일치 우선
        if n == opt:
            return n
    for n in notes:  # 포함(부분 인용) 허용
        if opt in n or n in opt:
            return n
    return None


def _llm_axis_conflicts(notes: list[str], household: Optional[str], budget: int) -> Optional[dict]:
    """llm_active일 때만. 축 상충(의미) + 해석 boost. 스키마/제약 위반 시 None → 키워드 폴백.

    가구 유형 불일치는 여기서 다루지 않는다(별도 결정론 경로). 여기선 '문장 ↔ 문장' 축 상충만.
    """
    budget_line = f"예산(참고, 만원): {budget // 10000}" if budget else "예산: 미상"
    user = f"가구 유형: {household or '미선택'}\n{budget_line}\n담아둔 문장들: {notes or '(없음)'}"
    data = _extract_json(generate(system=_VALIDATE_SYSTEM, user=user, fallback=lambda: ""))
    if data is None:
        return None
    wa, conflicts, interp = (
        data.get("weight_adjustments") or {},
        data.get("conflicts") or [],
        data.get("interpretation") or [],
    )
    if not (isinstance(wa, dict) and isinstance(conflicts, list) and isinstance(interp, list)):
        return None
    for k, v in wa.items():
        if k not in _AXES or not isinstance(v, (int, float)) or isinstance(v, bool) or not (0.3 <= float(v) <= 2.0):
            return None
    items: list[dict] = []
    for c in conflicts:
        if not isinstance(c, dict):
            return None
        # optionA/optionB는 반드시 '실제 담아둔 문장'으로 매핑(인라인 A/B 제거가 정확히 되도록).
        # 매칭 안 되면(폼값 인용 등 LLM 잡음) 버린다 — 가구 불일치는 별도 결정론 경로가 잡는다.
        a, b = _match_note(str(c.get("optionA") or ""), notes), _match_note(str(c.get("optionB") or ""), notes)
        ax = str(c.get("axis") or "")
        if a and b and a != b:
            items.append(
                {
                    "type": "axis",
                    "axis": ax if ax in _AXES else "",
                    "optionA": a,
                    "optionB": b,
                    "question": str(c.get("question") or f"'{a}' ↔ '{b}'").strip(),
                    "allowBoth": True,
                }
            )
    return {"items": items, "boost": {k: float(v) for k, v in wa.items()}, "labels": [str(x) for x in interp]}


def validate_profile(
    contract: dict,
    finance: dict,
    budget: int = 0,
    household_selected: bool = True,
    accepted_pairs: Optional[list] = None,
) -> dict:
    """SC-14 최종 프로필 종합검증 — 누적 자유입력 전체 + 가구 + 예산을 한 번에 보고 상충을 잡는다.

    가구 불일치는 **사실 대조(결정론)**, 축/의미 상충은 **LLM(의미검증)** 우선·키워드('간이검증') 폴백.
    accepted_pairs: 사용자가 '둘 다 맞아요'로 확인한 쌍(frozenset). 그 쌍은 다시 상충으로 잡지 않는다(K1).
    반환 ClarifyResult 형태 + conflictItems(인라인 해소용) + mode('ai'|'rule').
    """
    household = finance.get("household") or "1인"
    household_for_conflict = household if household_selected else None
    notes = _split_notes(contract.get("note") or "")
    accepted = {frozenset(p) for p in (accepted_pairs or [])}

    # 축/의미 상충: LLM 우선, 폴백 키워드
    llm = _llm_axis_conflicts(notes, household, budget) if (notes and settings.llm_active) else None
    if llm is not None:
        axis_items = [c for c in llm["items"] if frozenset((c["optionA"], c["optionB"])) not in accepted]
        labels, mode = llm["labels"], "ai"
    else:
        axis_items = _axis_conflict_items_kw(notes, accepted)
        labels, mode = note_signals(" ".join(notes))["labels"], "rule"

    # 가구 불일치: 항상 결정론(사실 대조)
    conflict_items = _household_conflict_items(notes, household_for_conflict, accepted) + axis_items
    held = bool(conflict_items)

    # 확정(상충 없음) 시에만 해석 반영 — '둘 다'로 확인된 상쇄는 사용자가 확인한 것이라 그대로 둔다.
    # weightAdjust = 결정론 '방향'(키워드). 크기는 note_weights가 yaml에서 변환 → 재현 가능.
    boost = {} if held else note_directions(" ".join(notes))
    boost_mult = {ax: dir_mult(d) for ax, d in boost.items()}
    w = _apply_boost(scoring.weights_for(household), boost_mult)
    return {
        "persona": segment_label(household),
        "weightAdjust": boost,
        "held": held,
        "priorities": [AXIS_LABEL[k] for k, _ in sorted(w.items(), key=lambda kv: -kv[1])],
        "conflicts": [c["question"] for c in conflict_items],  # 하위호환(문자열)
        "conflictItems": conflict_items,  # 인라인 해소용 구조(K1/K4)
        "questions": [c["question"] for c in conflict_items],
        "noteSignals": labels,
        "mode": mode,
    }
