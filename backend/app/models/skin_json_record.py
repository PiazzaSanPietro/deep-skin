from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class SkinJsonRecord(Base):
    __tablename__ = "skin_json_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_subject_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    device: Mapped[int | None] = mapped_column(Integer, nullable=True)
    angle: Mapped[int | None] = mapped_column(Integer, nullable=True)
    facepart: Mapped[int | None] = mapped_column(Integer, nullable=True)

    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    bbox_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox_w: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox_h: Mapped[int | None] = mapped_column(Integer, nullable=True)

    raw_json: Mapped[Any] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
