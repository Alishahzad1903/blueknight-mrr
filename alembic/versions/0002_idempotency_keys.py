"""idempotency keys table

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-31
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS idempotency_keys (
            key          TEXT NOT NULL,
            user_id      BIGINT NOT NULL REFERENCES users(id),
            request_hash TEXT NOT NULL,
            status_code  INT NOT NULL,
            response_body JSONB NOT NULL,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (key, user_id)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS idempotency_keys")
