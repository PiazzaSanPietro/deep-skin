"""create analysis image tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── analysis_sessions ─────────────────────────────────
    op.create_table(
        "analysis_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("session_name", sa.String(255), nullable=False),
        sa.Column("input_type", sa.String(30), nullable=False, server_default="image"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("overall_status", sa.String(30), nullable=True),
        sa.Column("summary_message", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_analysis_sessions_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_analysis_sessions_user_id", "analysis_sessions", ["user_id"])
    op.create_index("idx_analysis_sessions_status", "analysis_sessions", ["status"])
    op.create_index("idx_analysis_sessions_created_at", "analysis_sessions", ["created_at"])

    # ── uploaded_images ───────────────────────────────────
    op.create_table(
        "uploaded_images",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("angle", sa.Integer(), nullable=True),
        sa.Column("facepart", sa.Integer(), nullable=True),
        sa.Column("upload_status", sa.String(30), nullable=False, server_default="uploaded"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["analysis_sessions.id"],
            name="fk_uploaded_images_session",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_uploaded_images_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_uploaded_images_session_id", "uploaded_images", ["session_id"])
    op.create_index("idx_uploaded_images_user_id", "uploaded_images", ["user_id"])
    op.create_index("idx_uploaded_images_status", "uploaded_images", ["upload_status"])


def downgrade() -> None:
    op.drop_index("idx_uploaded_images_status", table_name="uploaded_images")
    op.drop_index("idx_uploaded_images_user_id", table_name="uploaded_images")
    op.drop_index("idx_uploaded_images_session_id", table_name="uploaded_images")
    op.drop_table("uploaded_images")
    op.drop_index("idx_analysis_sessions_created_at", table_name="analysis_sessions")
    op.drop_index("idx_analysis_sessions_status", table_name="analysis_sessions")
    op.drop_index("idx_analysis_sessions_user_id", table_name="analysis_sessions")
    op.drop_table("analysis_sessions")
