"""Phase 2: application table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_status = sa.Enum(
    "DRAFT",
    "SENT",
    "FOLLOWED_UP",
    "INTERVIEW",
    "REJECTED",
    "OFFER_RECEIVED",
    "NO_ANSWER",
    "WITHDRAWN",
    name="applicationstatus",
)


def upgrade() -> None:
    op.create_table(
        "application",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("offer_id", sa.String(), nullable=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("organization", sa.String(), nullable=False),
        sa.Column("position", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("status", _status, nullable=False),
        sa.Column("lang", sa.String(), nullable=False),
        sa.Column("template", sa.String(), nullable=False),
        sa.Column("engine", sa.String(), nullable=False),
        sa.Column("folder", sa.String(), nullable=False),
        sa.Column("email_subject", sa.String(), nullable=False),
        sa.Column("email_body", sa.String(), nullable=False),
        sa.Column("ats_score", sa.Integer(), nullable=True),
        sa.Column("jury_score_before", sa.Integer(), nullable=True),
        sa.Column("jury_score_after", sa.Integer(), nullable=True),
        sa.Column("compaction_level", sa.Integer(), nullable=True),
        sa.Column("job_id", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_application_offer_id", "application", ["offer_id"])
    op.create_index("ix_application_status", "application", ["status"])
    op.create_index("ix_application_created_at", "application", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_application_created_at", table_name="application")
    op.drop_index("ix_application_status", table_name="application")
    op.drop_index("ix_application_offer_id", table_name="application")
    op.drop_table("application")
