import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# 프로젝트 루트(backend/)를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.database import Base

# ── 모델 import ──────────────────────────────────────────
from app.models.user import User  # noqa: F401
from app.models.user_profile import UserProfile  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.analysis_session import AnalysisSession  # noqa: F401
from app.models.uploaded_image import UploadedImage  # noqa: F401
from app.models.skin_json_record import SkinJsonRecord  # noqa: F401
from app.models.skin_part_result import SkinPartResult  # noqa: F401
from app.models.ingredient_rule import IngredientRule  # noqa: F401
from app.models.recommendation_rule import RecommendationRule  # noqa: F401
from app.models.part_recommendation import PartRecommendation  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.ai_raw_response import AiRawResponse  # noqa: F401
from app.models.skin_part_detection import SkinPartDetection  # noqa: F401
from app.models.skin_metric_value import SkinMetricValue  # noqa: F401
from app.models.metric_threshold_rule import MetricThresholdRule  # noqa: F401
from app.models.metric_recommendation_boost_rule import MetricRecommendationBoostRule  # noqa: F401
# ─────────────────────────────────────────────────────────

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
