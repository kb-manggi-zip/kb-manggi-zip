"""Vercel Python 서버리스 진입점 — backend/ 의 FastAPI 앱을 그대로 노출(ASGI).

단일 Vercel 배포에서 프론트(정적)와 백엔드(이 함수)가 같은 도메인을 공유한다.
/api/* 요청이 vercel.json rewrite로 이 함수에 도달하고, FastAPI( router prefix '/api' )가 라우팅한다.
데이터·룰 파일은 vercel.json의 includeFiles("backend/**")로 함께 번들된다.
"""

import sys
from pathlib import Path

# backend/ 를 import 경로에 추가 (app.main → FastAPI 인스턴스)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402  # @vercel/python이 ASGI app으로 인식해 서빙

__all__ = ["app"]
