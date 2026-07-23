"""LLM seam — Claude 호출 자리 + 템플릿 폴백.

원칙(헌법 0-1): 숫자는 도구가 계산, LLM은 통역/라우팅만. 출력은 가드레일·검증 통과.

동작:
- settings.llm_active == False (키 없음 또는 LLM_ENABLED=false, 기본값)
      → 항상 fallback() 반환. API 키 없이 전 엔드포인트가 200으로 동작.
- settings.llm_active == True
      → 실제 Claude 호출 후 가드레일 검사. 부적합하면 fallback().
        ※ STUB: 숫자 검증(verify.numbers_grounded) 기반 재생성 2회 루프는 Phase B4.
          그전까지 LLM_ENABLED=true는 권장하지 않는다(검증 미완).
"""

import logging
from typing import Callable

from .config import settings
from .verify import contains_solicitation, numbers_grounded

log = logging.getLogger("kb.llm")

# 모든 LLM 노드 공통 시스템 규칙 (헌법 0-1.5 / 기획서 Trust Layer)
SYSTEM_RULES = (
    "너는 전월세 만기 의사결정을 돕는 비교 서비스의 내레이터다. "
    "숫자와 고유명사는 입력으로 주어진 facts에 있는 것만 사용한다. "
    "없는 정보는 지어내지 말고 '확인 불가'로 둔다. "
    "추천·권유·단정('추천합니다/하세요/가입하세요/무조건/확실/이득') 표현을 쓰지 않는다. "
    "세 갈래를 나란히 서술만 하고 결론(무엇을 고르라)은 내리지 않는다."
)


def generate(
    *,
    system: str,
    user: str,
    fallback: Callable[[], str],
    allowed_numbers: set[int] | None = None,
) -> str:
    """LLM 통역 텍스트 생성. 비활성/부적합 시 템플릿 폴백.

    Args:
        system: 노드별 추가 지시 (SYSTEM_RULES 뒤에 결합)
        user:   facts를 담은 프롬프트
        fallback: 폴백 텍스트 생성기 (프론트 briefings.ts 이식 템플릿)
        allowed_numbers: 출력에 허용되는 숫자 집합. None이면 숫자 검증 생략(하위호환).
    """
    if not settings.llm_active:
        return fallback()

    for attempt in range(3):
        try:
            text = _call_claude(system, user)
        except Exception as e:
            log.warning("LLM 호출 실패 → 폴백: %s", e)
            return fallback()

        if contains_solicitation(text):
            log.info("권유 표현 감지 (시도 %d) → 재생성", attempt + 1)
            continue

        if allowed_numbers is not None and not numbers_grounded(text, allowed_numbers):
            log.info("숫자 불일치 감지 (시도 %d) → 재생성", attempt + 1)
            continue

        return text

    log.warning("재생성 2회 모두 실패 → 폴백")
    return fallback()

def _call_claude(system: str, user: str) -> str:
    """실제 Claude 호출. settings.llm_active 일 때만 도달."""
    from anthropic import Anthropic  # 지연 import (키 없을 때 의존성 회피)

    client = Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model=settings.llm_model,
        max_tokens=1024,
        system=f"{SYSTEM_RULES}\n\n{system}",
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in msg.content if block.type == "text")
