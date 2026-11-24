"""Store site content, the résumé PDF, and shared request limits."""

from alembic import op
import sqlalchemy as sa


revision = "6f4dca2a70b9"
down_revision = "8b63ee91fd42"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "site_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
    )
    op.create_table(
        "resume_document",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payload", sa.LargeBinary(), nullable=False),
    )
    op.create_table(
        "request_limit",
        sa.Column("scope", sa.String(16), primary_key=True),
        sa.Column("client_key", sa.String(64), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=False),
    )
    op.create_index("ix_request_limit_expires_at", "request_limit", ["expires_at"])


def downgrade():
    op.drop_table("request_limit")
    op.drop_table("resume_document")
    op.drop_table("site_profile")
