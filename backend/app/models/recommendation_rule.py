from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class RecommendationRule(Base):
    __tablename__ = "recommendation_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    display_part_name: Mapped[str] = mapped_column(String(50), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(100), nullable=False)
    issue_display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)

    reason_template: Mapped[str] = mapped_column(Text, nullable=False)
    recommend_categories: Mapped[Any] = mapped_column(JSON, nullable=False)
    recommend_ingredients: Mapped[Any] = mapped_column(JSON, nullable=False)
    care_tips: Mapped[Any] = mapped_column(JSON, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
