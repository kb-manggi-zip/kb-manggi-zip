"""Langfuse 트레이싱 초기화 (Phase B3). 키 없으면 조용히 비활성화(그래프는 정상 동작)."""

from contextlib import AbstractContextManager, nullcontext

from langfuse import Langfuse, propagate_attributes

from .config import settings

langfuse_client: Langfuse | None = None

if settings.langfuse_public_key and settings.langfuse_secret_key:
    langfuse_client = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        base_url=settings.langfuse_base_url,
    )


def session_scope(
    session_id: str | None = None,
    user_id: str | None = None,
) -> AbstractContextManager:
    """세션ID를 현재 trace와 그 안에서 생성되는 하위 span 전체에 전파한다.

    같은 session_id를 가진 여러 API 호출(analyze→regions→simulate→products…)은
    Langfuse의 **Sessions** 화면에서 '한 사용자 여정'으로 묶여 보인다.
    반드시 root span(=@observe/graph.invoke) '생성 직전'에 진입해야 소급 적용된다.

    langfuse 미설정이거나 session_id가 없으면 no-op 컨텍스트를 돌려준다(동작 불변).
    """
    if langfuse_client is None or not session_id:
        return nullcontext()
    return propagate_attributes(session_id=session_id, user_id=user_id)
