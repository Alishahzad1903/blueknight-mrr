"""collab init

Revision ID: 0001
Revises:
Create Date: 2026-05-31
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- parent tables (idempotent) ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id      BIGSERIAL PRIMARY KEY,
            org_id  BIGINT NOT NULL,
            email   TEXT
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS market_research_reports (
            id          BIGSERIAL PRIMARY KEY,
            user_id     BIGINT NOT NULL REFERENCES users(id),
            title       TEXT NOT NULL DEFAULT '',
            sections    JSONB NOT NULL DEFAULT '{}',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # --- enum types (idempotent) ---
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE edit_source AS ENUM ('human', 'ai_rewrite', 'revert');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE share_permission AS ENUM ('view', 'edit');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)

    # --- report_sections ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS report_sections (
            id                  BIGSERIAL PRIMARY KEY,
            report_id           BIGINT NOT NULL REFERENCES market_research_reports(id),
            section_key         TEXT NOT NULL,
            content             JSONB NOT NULL DEFAULT '{}',
            version             INT NOT NULL DEFAULT 1,
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by_user_id  BIGINT NOT NULL REFERENCES users(id),
            UNIQUE (report_id, section_key)
        )
    """)

    # --- report_section_edits ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS report_section_edits (
            id              BIGSERIAL PRIMARY KEY,
            report_id       BIGINT NOT NULL REFERENCES market_research_reports(id),
            section_key     TEXT NOT NULL,
            version_before  INT NOT NULL,
            version_after   INT NOT NULL,
            content_before  JSONB NOT NULL,
            content_after   JSONB NOT NULL,
            editor_user_id  BIGINT NOT NULL REFERENCES users(id),
            source          edit_source NOT NULL,
            ts              TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # --- report_shares ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS report_shares (
            id                  BIGSERIAL PRIMARY KEY,
            report_id           BIGINT NOT NULL REFERENCES market_research_reports(id),
            target_user_id      BIGINT NOT NULL REFERENCES users(id),
            permission          share_permission NOT NULL,
            granted_by_user_id  BIGINT NOT NULL REFERENCES users(id),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            revoked_at          TIMESTAMPTZ
        )
    """)

    # --- indexes ---
    op.execute("""
        CREATE INDEX IF NOT EXISTS report_section_edits_history_idx
        ON report_section_edits (report_id, section_key, ts DESC)
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS report_shares_active_uniq
        ON report_shares (report_id, target_user_id)
        WHERE revoked_at IS NULL
    """)

    # --- backfill report_sections from existing JSONB ---
    op.execute("""
        INSERT INTO report_sections
            (report_id, section_key, content, version, updated_at, updated_by_user_id)
        SELECT r.id, kv.key, kv.value, 1, r.created_at, r.user_id
        FROM market_research_reports r,
             jsonb_each(r.sections) AS kv(key, value)
        ON CONFLICT (report_id, section_key) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS report_shares, report_section_edits, report_sections CASCADE")
    op.execute("DROP TYPE IF EXISTS share_permission")
    op.execute("DROP TYPE IF EXISTS edit_source")
