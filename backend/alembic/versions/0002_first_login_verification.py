"""first login verification

Revision ID: 0002_first_login_verification
Revises: 0001_initial_schema
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_first_login_verification"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "first_login_verifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=180), nullable=False),
        sa.Column("otp_hash", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_first_login_verifications_email", "first_login_verifications", ["email"], unique=True)
    op.create_index("ix_first_login_verifications_verified", "first_login_verifications", ["verified"], unique=False)
    op.create_index("ix_first_login_email_verified", "first_login_verifications", ["email", "verified"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_first_login_email_verified", table_name="first_login_verifications")
    op.drop_index("ix_first_login_verifications_verified", table_name="first_login_verifications")
    op.drop_index("ix_first_login_verifications_email", table_name="first_login_verifications")
    op.drop_table("first_login_verifications")
