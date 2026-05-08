from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class PartRecommendation(Base):
    __tablename__ = "part_recommendations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    rule_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("recommendation_rules.id", ondelete="SET NULL"), nullable=True
    )

    display_part_name: Mapped[str] = mapped_column(String(50), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(100), nullable=False)
    issue_display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)

    reason: Mapped[str] = mapped_column(Text, nullable=False)
    recommend_categories: Mapped[Any] = mapped_column(JSON, nullable=False)
    recommend_ingredients: Mapped[Any] = mapped_column(JSON, nullable=False)
    excluded_ingredients: Mapped[Any] = mapped_column(JSON, nullable=True)
    exclusion_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    care_tips: Mapped[Any] = mapped_column(JSON, nullable=True)

    recommendation_source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="rule_based"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
