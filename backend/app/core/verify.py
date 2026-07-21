"""LLM 출력 안전장치 — 권유 가드레일 + 숫자 검증.

헌법 0-1.5: "추천합니다/하세요/가입하세요/이득/무조건/확실" 패턴 차단 → 재생성.
헌법 0-1.1: LLM이 낸 숫자는 입력 facts에 있는 값만 허용, 불일치 시 재생성 2회 → 폴백.

Phase B4에서 재생성 루프를 완성한다. 지금은 판정 함수만 제공(seam).
"""
import re

# 권유·단정 표현 (서술만 허용)
SOLICITATION_PATTERNS = [
    "추천합니다", "추천드립니다", "하세요", "하시길", "가입하세요",
    "이득", "무조건", "확실", "반드시 ", "최고의 선택", "강력히",
]

_NUM = re.compile(r"[0-9][0-9,]*")


def contains_solicitation(text: str) -> bool:
    """권유/단정 표현이 있으면 True (있으면 재생성 대상)."""
    return any(p in text for p in SOLICITATION_PATTERNS)


def _numbers(text: str) -> set[int]:
    out = set()
    for m in _NUM.finditer(text or ""):
        try:
            out.add(int(m.group().replace(",", "")))
        except ValueError:
            pass
    return out


def numbers_grounded(text: str, allowed: set[int]) -> bool:
    """출력의 모든 숫자가 허용 집합(입력 facts 파생)에 포함되는지.

    allowed 에는 원값·만원 단위·억 단위 등 표현 파생값을 미리 넣어 호출한다.
    """
    return _numbers(text).issubset(allowed)
