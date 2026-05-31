"""Seed the database with fixture data for development and testing."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://mrr:mrr@localhost:5432/mrr")
SYNC_URL = DATABASE_URL.replace("+asyncpg", "")

# psycopg2 wants a plain postgres:// URL, not postgresql://
CONN_STR = SYNC_URL.replace("postgresql://", "postgresql://", 1)


def main() -> None:
    conn = psycopg2.connect(CONN_STR)
    conn.autocommit = False
    cur = conn.cursor()

    # users: org 1 (ids 1-3), org 2 (ids 4-6)
    cur.execute("""
        INSERT INTO users (id, org_id, email) VALUES
            (1, 1, 'alice@org1.com'),
            (2, 1, 'bob@org1.com'),
            (3, 1, 'carol@org1.com'),
            (4, 2, 'dave@org2.com'),
            (5, 2, 'eve@org2.com'),
            (6, 2, 'frank@org2.com')
        ON CONFLICT (id) DO NOTHING
    """)

    # sync the sequence so future inserts don't collide
    cur.execute("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))")

    # report owned by user 1 with 3 JSONB sections
    cur.execute("""
        INSERT INTO market_research_reports (id, user_id, title, sections)
        VALUES (
            1,
            1,
            'ACME Market Analysis 2026',
            '{
                "executive_summary": {"text": "ACME shows strong momentum in Q1 2026."},
                "market_size":        {"text": "The total addressable market is $12B."},
                "key_trends":         {"text": "AI adoption is the dominant growth driver."}
            }'::jsonb
        )
        ON CONFLICT (id) DO NOTHING
    """)

    cur.execute("SELECT setval('market_research_reports_id_seq', (SELECT MAX(id) FROM market_research_reports))")

    # backfill report_sections from the seeded JSONB (mirrors the migration backfill)
    cur.execute("""
        INSERT INTO report_sections
            (report_id, section_key, content, version, updated_at, updated_by_user_id)
        SELECT r.id, kv.key, kv.value, 1, r.created_at, r.user_id
        FROM market_research_reports r,
             jsonb_each(r.sections) AS kv(key, value)
        ON CONFLICT (report_id, section_key) DO NOTHING
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Seed complete.")


if __name__ == "__main__":
    main()
