"""예약 저장 ORM. SQLite/Postgres 공통 (DATABASE_URL로 실체만 교체)."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    branch: Mapped[str] = mapped_column(String(8))
    date: Mapped[str] = mapped_column(String(32))
    product_name: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
