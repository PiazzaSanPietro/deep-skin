"""create skin result tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── skin_json_records ─────────────────────────────────
    op.create_table(
        "skin_json_records",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=True),
        sa.Column("raw_subject_id", sa.String(100), nullable=True),
        sa.Column("device", sa.Integer(), nullable=True),
        sa.Column("angle", sa.Integer(), nullable=True),
        sa.Column("facepart", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("bbox_x", sa.Integer(), nullable=True),
        sa.Column("bbox_y", sa.Integer(), nullable=True),
        sa.Column("bbox_w", sa.Integer(), nullable=True),
        sa.Column("bbox_h", sa.Integer(), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["analysis_sessions.id"],
            name="fk_skin_json_records_session",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_skin_json_records_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_skin_json_records_session_id", "skin_json_records", ["session_id"])
    op.create_index("idx_skin_json_records_user_id", "skin_json_records", ["user_id"])
    op.create_index("idx_skin_json_records_raw_subject_id", "skin_json_records", ["raw_subject_id"])

    # ── skin_part_results ─────────────────────────────────
    op.create_table(
        "skin_part_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("image_id", sa.BigInteger(), nullable=True),
        sa.Column("json_record_id", sa.BigInteger(), nullable=True),
        sa.Column("raw_part_name", sa.String(50), nullable=False),
        sa.Column("display_part_name", sa.String(50), nullable=False),
        sa.Column("metric_name", sa.String(50), nullable=False),
        sa.Column("metric_display_name", sa.String(50), nullable=False),
        sa.Column("grade_value", sa.Integer(), nullable=True),
        sa.Column("measured_value", sa.Float(precision=53), nullable=True),
        sa.Column("predicted_value", sa.Float(precision=53), nullable=True),
        sa.Column("confidence_score", sa.Float(precision=53), nullable=True),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("issue_type", sa.String(100), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=True),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("model_version", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["analysis_sessions.id"],
            name="fk_skin_part_results_session",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_skin_part_results_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["image_id"], ["uploaded_images.id"],
            name="fk_skin_part_results_image",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["json_record_id"], ["skin_json_records.id"],
            name="fk_skin_part_results_json_record",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_skin_part_results_session_id", "skin_part_results", ["session_id"])
    op.create_index("idx_skin_part_results_user_id", "skin_part_results", ["user_id"])
    op.create_index("idx_skin_part_results_part", "skin_part_results", ["display_part_name"])
    op.create_index("idx_skin_part_results_metric", "skin_part_results", ["metric_name"])
    op.create_index("idx_skin_part_results_issue", "skin_part_results", ["issue_type"])
    op.create_index("idx_skin_part_results_severity", "skin_part_results", ["severity"])


def downgrade() -> None:
    op.drop_index("idx_skin_part_results_severity", table_name="skin_part_results")
    op.drop_index("idx_skin_part_results_issue", table_name="skin_part_results")
    op.drop_index("idx_skin_part_results_metric", table_name="skin_part_results")
    op.drop_index("idx_skin_part_results_part", table_name="skin_part_results")
    op.drop_index("idx_skin_part_results_user_id", table_name="skin_part_results")
    op.drop_index("idx_skin_part_results_session_id", table_name="skin_part_results")
    op.drop_table("skin_part_results")
    op.drop_index("idx_skin_json_records_raw_subject_id", table_name="skin_json_records")
    op.drop_index("idx_skin_json_records_user_id", table_name="skin_json_records")
    op.drop_index("idx_skin_json_records_session_id", table_name="skin_json_records")
    op.drop_table("skin_json_records")
