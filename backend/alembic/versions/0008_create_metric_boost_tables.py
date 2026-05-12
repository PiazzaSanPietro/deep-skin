"""create metric boost tables for recommendation correction

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── metric_threshold_rules ────────────────────────────
    op.create_table(
        "metric_threshold_rules",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        # 빈 문자열("")은 "전체 부위 적용"을 의미한다.
        sa.Column("raw_part_name", sa.String(50), nullable=False),
        sa.Column("metric_group", sa.String(50), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        # "low_is_bad" | "high_is_bad" | "metric_specific"
        sa.Column("direction", sa.String(30), nullable=False),
        sa.Column("mild_threshold", sa.Double(), nullable=True),
        sa.Column("moderate_threshold", sa.Double(), nullable=True),
        sa.Column("severe_threshold", sa.Double(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_metric_threshold_rules_part_group",
        "metric_threshold_rules",
        ["raw_part_name", "metric_group"],
    )
    op.create_index(
        "idx_metric_threshold_rules_group_name",
        "metric_threshold_rules",
        ["metric_group", "metric_name"],
    )
    op.create_index(
        "idx_metric_threshold_rules_active",
        "metric_threshold_rules",
        ["is_active"],
    )

    # ── metric_recommendation_boost_rules ─────────────────
    op.create_table(
        "metric_recommendation_boost_rules",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("metric_group", sa.String(50), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        # NULL이면 모든 부위에 적용
        sa.Column("raw_part_name", sa.String(50), nullable=True),
        # "low_is_bad" | "high_is_bad" | "metric_specific"
        sa.Column("direction", sa.String(30), nullable=False),
        sa.Column("threshold_min", sa.Double(), nullable=True),
        sa.Column("threshold_max", sa.Double(), nullable=True),
        # 기존 추천 성분 중 우선순위를 올릴 성분 목록
        sa.Column("boost_ingredients", sa.JSON(), nullable=True),
        # 기존 결과에 보조로 추가할 성분 후보
        sa.Column("add_ingredients", sa.JSON(), nullable=True),
        # 보조 카테고리 추가
        sa.Column("add_categories", sa.JSON(), nullable=True),
        # 관리 팁 문구 추가
        sa.Column("add_care_tips", sa.Text(), nullable=True),
        sa.Column("priority", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_metric_boost_rules_group_name",
        "metric_recommendation_boost_rules",
        ["metric_group", "metric_name"],
    )
    op.create_index(
        "idx_metric_boost_rules_part",
        "metric_recommendation_boost_rules",
        ["raw_part_name"],
    )
    op.create_index(
        "idx_metric_boost_rules_active",
        "metric_recommendation_boost_rules",
        ["is_active"],
    )
    op.create_index(
        "idx_metric_boost_rules_priority",
        "metric_recommendation_boost_rules",
        ["priority"],
    )


def downgrade() -> None:
    # FK/인덱스 의존성 없음. boost_rules → threshold_rules 순서로 drop.
    op.drop_table("metric_recommendation_boost_rules")
    op.drop_table("metric_threshold_rules")
