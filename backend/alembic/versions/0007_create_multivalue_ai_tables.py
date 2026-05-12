"""create multivalue AI storage tables

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ai_raw_responses ──────────────────────────────────
    op.create_table(
        "ai_raw_responses",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("image_id", sa.BigInteger(), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("server_type", sa.String(50), nullable=False),
        sa.Column("raw_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["analysis_sessions.id"],
            name="fk_ai_raw_responses_session",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["image_id"], ["uploaded_images.id"],
            name="fk_ai_raw_responses_image",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_ai_raw_responses_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ai_raw_responses_session", "ai_raw_responses", ["session_id"])
    op.create_index("idx_ai_raw_responses_user", "ai_raw_responses", ["user_id"])

    # ── skin_part_detections ──────────────────────────────
    op.create_table(
        "skin_part_detections",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("image_id", sa.BigInteger(), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_part_name", sa.String(50), nullable=False),
        sa.Column("class_name", sa.String(50), nullable=True),
        sa.Column("facepart", sa.SmallInteger(), nullable=False),
        sa.Column("bbox_x1", sa.Float(precision=53), nullable=False),
        sa.Column("bbox_y1", sa.Float(precision=53), nullable=False),
        sa.Column("bbox_x2", sa.Float(precision=53), nullable=False),
        sa.Column("bbox_y2", sa.Float(precision=53), nullable=False),
        sa.Column("bbox_source", sa.String(30), nullable=False),
        sa.Column("detection_confidence", sa.Float(precision=53), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["analysis_sessions.id"],
            name="fk_skin_part_detections_session",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["image_id"], ["uploaded_images.id"],
            name="fk_skin_part_detections_image",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_skin_part_detections_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_skin_part_detections_session", "skin_part_detections", ["session_id"])
    op.create_index("idx_skin_part_detections_part", "skin_part_detections", ["raw_part_name"])

    # ── skin_metric_values ────────────────────────────────
    op.create_table(
        "skin_metric_values",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("image_id", sa.BigInteger(), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("part_result_id", sa.BigInteger(), nullable=True),
        sa.Column("raw_part_name", sa.String(50), nullable=False),
        sa.Column("display_part_name", sa.String(50), nullable=False),
        sa.Column("facepart", sa.SmallInteger(), nullable=False),
        sa.Column("metric_group", sa.String(50), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("metric_key", sa.String(100), nullable=False),
        sa.Column("value", sa.Double(), nullable=False),
        sa.Column("value_type", sa.String(20), nullable=False),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("is_dummy", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("dummy_reason", sa.String(100), nullable=True),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["analysis_sessions.id"],
            name="fk_skin_metric_values_session",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["image_id"], ["uploaded_images.id"],
            name="fk_skin_metric_values_image",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_skin_metric_values_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["part_result_id"], ["skin_part_results.id"],
            name="fk_skin_metric_values_part_result",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_skin_metric_values_session", "skin_metric_values", ["session_id"])
    op.create_index("idx_skin_metric_values_part", "skin_metric_values", ["raw_part_name"])
    op.create_index("idx_skin_metric_values_metric_group", "skin_metric_values", ["metric_group"])
    op.create_index("idx_skin_metric_values_is_dummy", "skin_metric_values", ["is_dummy"])


def downgrade() -> None:
    # MySQL에서는 테이블 drop 시 인덱스/FK 제약이 함께 삭제된다.
    # FK가 걸린 인덱스를 별도로 drop하면 1553 에러가 발생하므로 테이블을 직접 drop한다.
    # skin_metric_values → skin_part_results FK가 있으므로 먼저 drop.
    op.drop_table("skin_metric_values")
    op.drop_table("skin_part_detections")
    op.drop_table("ai_raw_responses")
