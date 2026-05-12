from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Double, ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class SkinMetricValue(Base):
    __tablename__ = "skin_metric_values"

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
    part_result_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("skin_part_results.id", ondelete="SET NULL"), nullable=True
    )
    raw_part_name: Mapped[str] = mapped_column(String(50), nullable=False)
    display_part_name: Mapped[str] = mapped_column(String(50), nullable=False)
    facepart: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    metric_group: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(Double, nullable=False)
    value_type: Mapped[str] = mapped_column(String(20), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_dummy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dummy_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
