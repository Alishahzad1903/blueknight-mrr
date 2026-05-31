import base64
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


def _encode_cursor(ts: str, edit_id: int) -> str:
    return base64.urlsafe_b64encode(json.dumps({"ts": ts, "id": edit_id}).encode()).decode()


def _decode_cursor(cursor: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(cursor.encode()))


async def list_edits(
    session: AsyncSession,
    report_id: int,
    section_key: str,
    limit: int,
    cursor: str | None,
) -> tuple[list[dict], str | None]:
    if cursor:
        c = _decode_cursor(cursor)
        sql = text("""
            SELECT id, report_id, section_key, version_before, version_after,
                   content_before, content_after, editor_user_id, source,
                   ts AT TIME ZONE 'UTC' AS ts
            FROM report_section_edits
            WHERE report_id = :rid
              AND section_key = :key
              AND (ts, id) < (:cts::timestamptz, :cid)
            ORDER BY ts DESC, id DESC
            LIMIT :lim
        """)
        rows = (
            await session.execute(
                sql,
                {"rid": report_id, "key": section_key, "cts": c["ts"], "cid": c["id"], "lim": limit + 1},
            )
        ).mappings().all()
    else:
        sql = text("""
            SELECT id, report_id, section_key, version_before, version_after,
                   content_before, content_after, editor_user_id, source,
                   ts AT TIME ZONE 'UTC' AS ts
            FROM report_section_edits
            WHERE report_id = :rid
              AND section_key = :key
            ORDER BY ts DESC, id DESC
            LIMIT :lim
        """)
        rows = (
            await session.execute(sql, {"rid": report_id, "key": section_key, "lim": limit + 1})
        ).mappings().all()

    rows = list(rows)
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    results = []
    for r in rows:
        d = dict(r)
        d["ts"] = d["ts"].isoformat() if hasattr(d["ts"], "isoformat") else str(d["ts"])
        results.append(d)

    next_cursor = None
    if has_more and results:
        last = results[-1]
        next_cursor = _encode_cursor(last["ts"], last["id"])

    return results, next_cursor


async def get_edit_by_id(session: AsyncSession, edit_id: int) -> dict | None:
    sql = text("""
        SELECT id, report_id, section_key, version_before, version_after,
               content_before, content_after, editor_user_id, source, ts
        FROM report_section_edits
        WHERE id = :eid
    """)
    row = (await session.execute(sql, {"eid": edit_id})).mappings().first()
    if row is None:
        return None
    return dict(row)
