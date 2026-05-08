from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE", name="fk_user_profiles_user"),
        unique=True,
        nullable=False,
    )

    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    skin_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sensitive: Mapped[int | None] = mapped_column(Integer, nullable=True)

    main_concerns: Mapped[list | None] = mapped_column(JSON, nullable=True)
    allergy_ingredients: Mapped[list | None] = mapped_column(JSON, nullable=True)
    preferred_product_types: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
