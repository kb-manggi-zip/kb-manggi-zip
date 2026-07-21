"""데이터베이스 — SQLAlchemy.

- 기본: SQLite 파일 (설정 없이 로컬 데모 동작)
- compose: DATABASE_URL=postgresql+psycopg://... 주입 시 Postgres
동일한 ORM/세션 인터페이스로 뒤의 실체(SQLite/Postgres)만 교체된다.
"""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

_connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """스타트업 시 테이블 생성 (마이그레이션 도구는 규모 커지면 Alembic으로)."""
    from ..models import reservation  # noqa: F401  (모델 등록)

    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
