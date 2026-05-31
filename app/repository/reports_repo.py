from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def get_report_access(session: AsyncSession, report_id: int, user_id: int) -> dict | None:
    sql = text("""
        SELECT
            r.id AS report_id,
            r.user_id AS owner_user_id,
            CASE
                WHEN r.user_id = :uid THEN 'owner'
                WHEN s.permission = 'edit' THEN 'editor'
                WHEN s.permission = 'view' THEN 'viewer'
                ELSE NULL
            END AS access
        FROM market_research_reports r
        LEFT JOIN report_shares s
            ON s.report_id = r.id
           AND s.target_user_id = :uid
           AND s.revoked_at IS NULL
        WHERE r.id = :rid
    """)
    row = (await session.execute(sql, {"uid": user_id, "rid": report_id})).mappings().first()
    if row is None:
        return None
    return dict(row)


async def get_report_with_sections(session: AsyncSession, report_id: int) -> dict:
    report_sql = text("""
        SELECT id, user_id, title, created_at
        FROM market_research_reports
        WHERE id = :rid
    """)
    sections_sql = text("""
        SELECT section_key, content, version, updated_at, updated_by_user_id
        FROM report_sections
        WHERE report_id = :rid
    """)

    report_row = (await session.execute(report_sql, {"rid": report_id})).mappings().first()
    section_rows = (await session.execute(sections_sql, {"rid": report_id})).mappings().all()

    return {
        "id": report_row["id"],
        "user_id": report_row["user_id"],
        "title": report_row["title"],
        "created_at": report_row["created_at"].isoformat(),
        "sections": [dict(r) for r in section_rows],
    }
