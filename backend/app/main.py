"""FastAPI 진입점.

VITE_API_URL 하나만 프론트에 설정하면 이 백엔드가 프론트를 무수정으로 구동한다.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.db import init_db
from .core.rules import get_rules
from .routers.api import router as api_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="KB 만기상담소 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
def _startup() -> None:
    init_db()  # 테이블 생성 (SQLite/Postgres)
    get_rules()  # 규칙 로드 + 미검증 경고 출력


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "llm_active": settings.llm_active,  # False면 템플릿 폴백 모드
        "db": settings.database_url.split("://", 1)[0],
    }
