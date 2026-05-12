from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class SkinPartDetection(Base):
    __tablename__ = "skin_part_detections"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False
    )
    image_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("uploaded_images.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    raw_part_name: Mapped[str] = mapped_column(String(50), nullable=False)
    class_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    facepart: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    bbox_x1: Mapped[float] = mapped_column(Float(precision=53), nullable=False)
    bbox_y1: Mapped[float] = mapped_column(Float(precision=53), nullable=False)
    bbox_x2: Mapped[float] = mapped_column(Float(precision=53), nullable=False)
    bbox_y2: Mapped[float] = mapped_column(Float(precision=53), nullable=False)
    bbox_source: Mapped[str] = mapped_column(String(30), nullable=False)
    detection_confidence: Mapped[float | None] = mapped_column(Float(precision=53), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
