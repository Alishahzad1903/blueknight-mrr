"""Concurrent PATCHes: exactly one wins (200), the other loses (412), one edit row."""
import asyncio
from sqlalchemy import text


async def test_concurrent_patches_one_wins(client, auth_header, db_session):
    h = auth_header(1)
    # Both fire with If-Match: "1" at the same time
    r1, r2 = await asyncio.gather(
        client.patch(
            "/reports/1/sections/executive_summary",
            json={"content": {"text": "writer_A"}},
            headers={**h, "If-Match": '"1"'},
        ),
        client.patch(
            "/reports/1/sections/executive_summary",
            json={"content": {"text": "writer_B"}},
            headers={**h, "If-Match": '"1"'},
        ),
    )
    statuses = sorted([r1.status_code, r2.status_code])
    assert statuses == [200, 412], f"expected [200, 412], got {statuses}"

    # Exactly one edit row written
    count = (await db_session.execute(
        text(
            "SELECT count(*) FROM report_section_edits "
            "WHERE report_id=1 AND section_key='executive_summary'"
        )
    )).scalar()
    assert count == 1, f"expected 1 edit row, got {count}"

    # Winning version is exactly 2
    version = (await db_session.execute(
        text("SELECT version FROM report_sections WHERE report_id=1 AND section_key='executive_summary'")
    )).scalar()
    assert version == 2
