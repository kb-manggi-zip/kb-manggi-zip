"""Langfuse 트레이싱 초기화 (Phase B3). 키 없으면 조용히 비활성화(그래프는 정상 동작).

관측 보강(각 노드 span에 input/output/metadata + HITL 이벤트)은 아래 span_update/trace_event로.
langfuse 미설정/실패 시 전부 no-op — 관측은 부가기능이라 서비스 흐름을 절대 막지 않는다(단, 실패는 로그).
"""

import logging
from contextlib import AbstractContextManager, nullcontext
from typing import Any, Optional

from langfuse import Langfuse, get_client, propagate_attributes

from .config import settings

log = logging.getLogger("kb.tracing")

langfuse_client: Langfuse | None = None

if settings.langfuse_public_key and settings.langfuse_secret_key:
    langfuse_client = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        base_url=settings.langfuse_base_url,
    )


def span_update(
    *,
    input: Optional[Any] = None,
    output: Optional[Any] = None,
    metadata: Optional[dict] = None,
) -> None:
    """현재 span(=@observe 함수)에 입력/출력/메타데이터를 기록한다.

    "각 노드가 무엇을 보고(input) 무엇을 판단해(metadata) 무엇을 넘겼는지(output)"가
    Langfuse 화면에서 그대로 읽히게 하는 것이 목적. langfuse 미설정이면 no-op.
    """
    if langfuse_client is None:
        return
    try:
        get_client().update_current_span(input=input, output=output, metadata=metadata)
    except Exception as e:  # 관측 실패가 요청을 깨선 안 됨 — 삼키지 않고 로그
        log.warning("langfuse span_update 실패(관측만 영향): %s", e)


def trace_event(name: str, *, metadata: Optional[dict] = None, input: Optional[Any] = None) -> None:
    """세션 내 이벤트를 남긴다(예: HITL 사용자 확정 — '제안은 AI, 확정은 사람'을 trace에 박제)."""
    if langfuse_client is None:
        return
    try:
        get_client().create_event(name=name, input=input, metadata=metadata)
    except Exception as e:
        log.warning("langfuse trace_event 실패(관측만 영향): %s", e)


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
