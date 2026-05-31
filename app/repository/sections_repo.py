import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

WRITE_SECTION_SQL = text("""
WITH before AS (
    SELECT version, content
    FROM report_sections
    WHERE report_id = :rid AND section_key = :key
),
updated AS (
    UPDATE report_sections
       SET content            = CAST(:new_content AS jsonb),
           version            = version + 1,
           updated_at         = now(),
           updated_by_user_id = :uid
     WHERE report_id   = :rid
       AND section_key = :key
       AND version     = :expected_version
    RETURNING version
),
edit AS (
    INSERT INTO report_section_edits
        (report_id, section_key, version_before, version_after,
         content_before, content_after, editor_user_id, source)
    SELECT :rid, :key, b.version, u.version,
           b.content, CAST(:new_content AS jsonb), :uid, CAST(:source AS edit_source)
    FROM before b, updated u
    RETURNING id, version_after, content_after
)
SELECT e.id AS edit_id, e.version_after AS new_version, e.content_after AS content FROM edit e
""")


async def get_section(session: AsyncSession, report_id: int, section_key: str) -> dict | None:
    sql = text("""
        SELECT section_key, content, version, updated_at, updated_by_user_id
        FROM report_sections
        WHERE report_id = :rid AND section_key = :key
    """)
    row = (await session.execute(sql, {"rid": report_id, "key": section_key})).mappings().first()
    if row is None:
        return None
    return dict(row)


async def write_section(
    session: AsyncSession,
    *,
    report_id: int,
    section_key: str,
    new_content: dict,
    expected_version: int,
    user_id: int,
    source: str,
) -> dict | None:
    row = (
        await session.execute(
            WRITE_SECTION_SQL,
            {
                "rid": report_id,
                "key": section_key,
                "new_content": json.dumps(new_content),
                "expected_version": expected_version,
                "uid": user_id,
                "source": source,
            },
        )
    ).mappings().first()

    if row is None:
        return None
    return {
        "edit_id": row["edit_id"],
        "new_version": row["new_version"],
        "content": row["content"],
    }
