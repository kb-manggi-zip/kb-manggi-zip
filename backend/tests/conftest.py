"""테스트 공통 설정. app import 전에 환경변수를 세팅한다."""

import os

# 격리된 SQLite 테스트 DB / 임시 캐시 (실 API·실 DB 미접촉)
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_kb.db")
os.environ.setdefault("LLM_ENABLED", "false")
os.environ.setdefault("CACHE_DIR", "./cache")
