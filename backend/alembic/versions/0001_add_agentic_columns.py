"""add agentic verification columns

Revision ID: 0001_add_agentic_columns
Revises:
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_add_agentic_columns"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "verification_reports",
        sa.Column("verification_mode", sa.String(length=20), nullable=True, server_default="rule_based"),
    )
    op.add_column(
        "verification_reports",
        sa.Column("agent_summary", sa.String(length=2000), nullable=True),
    )
    op.add_column(
        "verification_reports",
        sa.Column("agent_trace", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column("verification_reports", "agent_trace")
    op.drop_column("verification_reports", "agent_summary")
    op.drop_column("verification_reports", "verification_mode")
