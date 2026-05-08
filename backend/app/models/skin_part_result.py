from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class SkinPartResult(Base):
    __tablename__ = "skin_part_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    image_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("uploaded_images.id", ondelete="SET NULL"), nullable=True
    )
    json_record_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("skin_json_records.id", ondelete="SET NULL"), nullable=True
    )

    raw_part_name: Mapped[str] = mapped_column(String(50), nullable=False)
    display_part_name: Mapped[str] = mapped_column(String(50), nullable=False)

    metric_name: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_display_name: Mapped[str] = mapped_column(String(50), nullable=False)

    grade_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    measured_value: Mapped[float | None] = mapped_column(Float(precision=53), nullable=True)
    predicted_value: Mapped[float | None] = mapped_column(Float(precision=53), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float(precision=53), nullable=True)

    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(100), nullable=False)
    reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
