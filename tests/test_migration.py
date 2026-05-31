"""Verify the Alembic migration is idempotent and the JSONB backfill is correct."""
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, text

from app.config import settings


def _alembic(*args):
    result = subprocess.run(
        [sys.executable, "-m", "alembic"] + list(args),
        capture_output=True,
        text=True,
        cwd=".",
    )
    assert result.returncode == 0, f"alembic {' '.join(args)} failed:\n{result.stderr}"
    return result


def test_migration_idempotent_and_backfill():
    """
    1. upgrade head (already at head — should be a no-op)
    2. upgrade head again (truly idempotent)
    3. downgrade -1
    4. upgrade head (re-applies cleanly)
    5. seed data
    6. assert backfill rows == JSONB key count
    """
    try:
        _alembic("upgrade", "head")
        _alembic("upgrade", "head")
        _alembic("downgrade", "-1")
        _alembic("upgrade", "head")

        from seed import main as seed_main
        seed_main()

        sync_url = settings.database_url.replace("+asyncpg", "")
        engine = create_engine(sync_url)
        with engine.connect() as conn:
            section_count = conn.execute(
                text("SELECT count(*) FROM report_sections WHERE report_id = 1")
            ).scalar()
            jsonb_count = conn.execute(
                text(
                    "SELECT count(*) FROM market_research_reports r,"
                    " jsonb_each(r.sections) WHERE r.id = 1"
                )
            ).scalar()
        engine.dispose()

        assert jsonb_count >= 3, "seed should have at least 3 JSONB keys"
        assert section_count == jsonb_count, (
            f"backfill count {section_count} != JSONB key count {jsonb_count}"
        )
    finally:
        # Always restore valid schema + data so subsequent tests work
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=".")
        from seed import main as seed_main
        seed_main()
