from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Double, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class MetricThresholdRule(Base):
    __tablename__ = "metric_threshold_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 빈 문자열("")은 "전체 부위 적용"을 의미한다.
    raw_part_name: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_group: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # "low_is_bad" | "high_is_bad" | "metric_specific"
    direction: Mapped[str] = mapped_column(String(30), nullable=False)

    mild_threshold: Mapped[float | None] = mapped_column(Double, nullable=True)
    moderate_threshold: Mapped[float | None] = mapped_column(Double, nullable=True)
    severe_threshold: Mapped[float | None] = mapped_column(Double, nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
