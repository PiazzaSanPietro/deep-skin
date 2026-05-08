"""create recommendation tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ingredient_rules ──────────────────────────────────
    op.create_table(
        "ingredient_rules",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ingredient_name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("caution_for_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ingredient_name", name="uq_ingredient_rules_name"),
    )
    op.create_index("idx_ingredient_rules_sensitive", "ingredient_rules", ["caution_for_sensitive"])

    # ── recommendation_rules ──────────────────────────────
    op.create_table(
        "recommendation_rules",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("display_part_name", sa.String(50), nullable=False),
        sa.Column("issue_type", sa.String(100), nullable=False),
        sa.Column("issue_display_name", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("reason_template", sa.Text(), nullable=False),
        sa.Column("recommend_categories", sa.JSON(), nullable=False),
        sa.Column("recommend_ingredients", sa.JSON(), nullable=False),
        sa.Column("care_tips", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "display_part_name", "issue_type", "severity",
            name="uq_recommendation_rules_part_issue_severity",
        ),
    )
    op.create_index("idx_recommendation_rules_part_issue", "recommendation_rules", ["display_part_name", "issue_type"])
    op.create_index("idx_recommendation_rules_severity", "recommendation_rules", ["severity"])
    op.create_index("idx_recommendation_rules_active", "recommendation_rules", ["is_active"])

    # ── part_recommendations ──────────────────────────────
    op.create_table(
        "part_recommendations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("rule_id", sa.BigInteger(), nullable=True),
        sa.Column("display_part_name", sa.String(50), nullable=False),
        sa.Column("issue_type", sa.String(100), nullable=False),
        sa.Column("issue_display_name", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("recommend_categories", sa.JSON(), nullable=False),
        sa.Column("recommend_ingredients", sa.JSON(), nullable=False),
        sa.Column("excluded_ingredients", sa.JSON(), nullable=True),
        sa.Column("exclusion_reason", sa.Text(), nullable=True),
        sa.Column("care_tips", sa.JSON(), nullable=True),
        sa.Column("recommendation_source", sa.String(50), nullable=False, server_default="rule_based"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["analysis_sessions.id"],
            name="fk_part_recommendations_session",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_part_recommendations_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"], ["recommendation_rules.id"],
            name="fk_part_recommendations_rule",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_part_recommendations_session_id", "part_recommendations", ["session_id"])
    op.create_index("idx_part_recommendations_user_id", "part_recommendations", ["user_id"])
    op.create_index("idx_part_recommendations_part", "part_recommendations", ["display_part_name"])
    op.create_index("idx_part_recommendations_issue", "part_recommendations", ["issue_type"])
    op.create_index("idx_part_recommendations_severity", "part_recommendations", ["severity"])

    # ── products ──────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("brand_name", sa.String(255), nullable=True),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("target_issue", sa.String(100), nullable=False),
        sa.Column("target_part", sa.String(50), nullable=True),
        sa.Column("ingredients", sa.JSON(), nullable=True),
        sa.Column("excluded_for_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("product_url", sa.String(500), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_products_target_issue", "products", ["target_issue"])
    op.create_index("idx_products_target_part", "products", ["target_part"])
    op.create_index("idx_products_category", "products", ["category"])
    op.create_index("idx_products_is_active", "products", ["is_active"])


def downgrade() -> None:
    op.drop_index("idx_products_is_active", table_name="products")
    op.drop_index("idx_products_category", table_name="products")
    op.drop_index("idx_products_target_part", table_name="products")
    op.drop_index("idx_products_target_issue", table_name="products")
    op.drop_table("products")
    op.drop_index("idx_part_recommendations_severity", table_name="part_recommendations")
    op.drop_index("idx_part_recommendations_issue", table_name="part_recommendations")
    op.drop_index("idx_part_recommendations_part", table_name="part_recommendations")
    op.drop_index("idx_part_recommendations_user_id", table_name="part_recommendations")
    op.drop_index("idx_part_recommendations_session_id", table_name="part_recommendations")
    op.drop_table("part_recommendations")
    op.drop_index("idx_recommendation_rules_active", table_name="recommendation_rules")
    op.drop_index("idx_recommendation_rules_severity", table_name="recommendation_rules")
    op.drop_index("idx_recommendation_rules_part_issue", table_name="recommendation_rules")
    op.drop_table("recommendation_rules")
    op.drop_index("idx_ingredient_rules_sensitive", table_name="ingredient_rules")
    op.drop_table("ingredient_rules")
