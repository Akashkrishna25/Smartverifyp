"""add applicant persistent fields to applications table

Revision ID: 0002_add_applicant_fields
Revises: 0001_add_agentic_columns
Create Date: 2026-08-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_add_applicant_fields"
down_revision = "0001_add_agentic_columns"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("applications", sa.Column("aadhaar_number", sa.String(length=20), nullable=True))
    op.add_column("applications", sa.Column("pan_number", sa.String(length=20), nullable=True))
    op.add_column("applications", sa.Column("dob", sa.String(length=50), nullable=True))
    op.add_column("applications", sa.Column("gender", sa.String(length=50), nullable=True))
    op.add_column("applications", sa.Column("address", sa.String(length=500), nullable=True))
    op.add_column("applications", sa.Column("father_name", sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column("applications", "father_name")
    op.drop_column("applications", "address")
    op.drop_column("applications", "gender")
    op.drop_column("applications", "dob")
    op.drop_column("applications", "pan_number")
    op.drop_column("applications", "aadhaar_number")
