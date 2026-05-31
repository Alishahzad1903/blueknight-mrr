from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.repository.errors import DuplicateShareError


async def create_share(
    session: AsyncSession,
    report_id: int,
    target_user_id: int,
    permission: str,
    granted_by: int,
) -> dict:
    sql = text("""
        INSERT INTO report_shares (report_id, target_user_id, permission, granted_by_user_id)
        VALUES (:rid, :tuid, CAST(:perm AS share_permission), :gby)
        RETURNING id, report_id, target_user_id, permission, granted_by_user_id,
                  created_at AT TIME ZONE 'UTC' AS created_at
    """)
    try:
        row = (
            await session.execute(sql, {"rid": report_id, "tuid": target_user_id, "perm": permission, "gby": granted_by})
        ).mappings().first()
    except IntegrityError as e:
        await session.rollback()
        if "unique" in str(e.orig).lower() or "duplicate" in str(e.orig).lower():
            raise DuplicateShareError() from e
        raise
    d = dict(row)
    d["created_at"] = d["created_at"].isoformat() if hasattr(d["created_at"], "isoformat") else str(d["created_at"])
    return d


async def revoke_share(session: AsyncSession, share_id: int, report_id: int) -> bool:
    sql = text("""
        UPDATE report_shares
           SET revoked_at = now()
         WHERE id = :sid
           AND report_id = :rid
           AND revoked_at IS NULL
        RETURNING id
    """)
    row = (await session.execute(sql, {"sid": share_id, "rid": report_id})).first()
    return row is not None


async def list_active_shares(session: AsyncSession, report_id: int) -> list[dict]:
    sql = text("""
        SELECT id, report_id, target_user_id, permission, granted_by_user_id,
               created_at AT TIME ZONE 'UTC' AS created_at
        FROM report_shares
        WHERE report_id = :rid AND revoked_at IS NULL
        ORDER BY created_at
    """)
    rows = (await session.execute(sql, {"rid": report_id})).mappings().all()
    result = []
    for r in rows:
        d = dict(r)
        d["created_at"] = d["created_at"].isoformat() if hasattr(d["created_at"], "isoformat") else str(d["created_at"])
        result.append(d)
    return result


async def get_user_org(session: AsyncSession, user_id: int) -> int | None:
    sql = text("SELECT org_id FROM users WHERE id = :uid")
    row = (await session.execute(sql, {"uid": user_id})).first()
    return row[0] if row else None
