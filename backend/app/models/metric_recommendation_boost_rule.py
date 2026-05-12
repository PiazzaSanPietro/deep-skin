from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Double, JSON, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class MetricRecommendationBoostRule(Base):
    __tablename__ = "metric_recommendation_boost_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    metric_group: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # NULL이면 모든 부위에 적용
    raw_part_name: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # "low_is_bad" | "high_is_bad" | "metric_specific"
    direction: Mapped[str] = mapped_column(String(30), nullable=False)

    threshold_min: Mapped[float | None] = mapped_column(Double, nullable=True)
    threshold_max: Mapped[float | None] = mapped_column(Double, nullable=True)

    # 기존 추천 성분 중 우선순위를 올릴 성분 목록 (예: ["BHA", "zinc_pca"])
    boost_ingredients: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    # 기존 결과에 보조로 추가할 성분 후보 목록
    add_ingredients: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    # 보조 카테고리 추가 목록
    add_categories: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    # 관리 팁 문구 추가
    add_care_tips: Mapped[str | None] = mapped_column(Text, nullable=True)

    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
