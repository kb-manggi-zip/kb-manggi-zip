"""Langfuse 트레이싱 초기화 (Phase B3). 키 없으면 조용히 비활성화(그래프는 정상 동작)."""

from langfuse import Langfuse

from .config import settings

langfuse_client: Langfuse | None = None

if settings.langfuse_public_key and settings.langfuse_secret_key:
    langfuse_client = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        base_url=settings.langfuse_base_url,
    )
