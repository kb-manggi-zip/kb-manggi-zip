"""환경설정 — .env / 환경변수에서 로드 (pydantic-settings)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 서버 / CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # DB — 기본 SQLite 파일. compose에선 Postgres URL 주입.
    database_url: str = "sqlite:///./kb.db"

    # LLM (Phase B4). 키 없거나 llm_enabled=False면 템플릿 폴백.
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-5"
    llm_enabled: bool = False

    # 외부 데이터 (Phase B2)
    molit_api_key: str = ""
    kakao_api_key: str = ""

    # 캐시
    cache_dir: str = "./cache"
    cache_ttl_hours: int = 24

    # 규칙 YAML 위치
    rules_dir: str = str(BACKEND_ROOT / "rules")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_active(self) -> bool:
        """실제 Claude 호출 가능 여부 (키 존재 + 명시적 활성화)."""
        return self.llm_enabled and bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
