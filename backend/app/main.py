"""FastAPI 진입점.

VITE_API_URL 하나만 프론트에 설정하면 이 백엔드가 프론트를 무수정으로 구동한다.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import BACKEND_ROOT, settings
from .core.db import init_db
from .core.rules import get_rules
from .routers.api import router as api_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="KB만기.zip API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# 하루시뮬 씬 이미지(scripts/generate_scene_images.py가 채움) — 없으면 빈 디렉터리, 404만 남(에러 아님).
_SCENE_IMAGE_DIR = BACKEND_ROOT / "data" / "scene_images"
_SCENE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static/scene_images", StaticFiles(directory=str(_SCENE_IMAGE_DIR)), name="scene_images")


@app.on_event("startup")
def _startup() -> None:
    init_db()  # 테이블 생성 (SQLite/Postgres)
    get_rules()  # 규칙 로드 + 미검증 경고 출력
    # 기동 시 어느 실거래 DB를 읽는지 1줄 로그 — 리허설에서 stale DB 함정을 눈으로 확인.
    from .tools import trades_store

    logging.getLogger("app.main").info("실거래 DB(읽기): %s", trades_store.resolve_db_path())


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "llm_active": settings.llm_active,  # False면 템플릿 폴백 모드
        "db": settings.database_url.split("://", 1)[0],
    }
