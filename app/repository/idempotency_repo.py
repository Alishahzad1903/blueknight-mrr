import json
from sqlalchemy import text


async def get_cached(session, key: str, user_id: int) -> dict | None:
    row = (await session.execute(
        text(
            "SELECT request_hash, status_code, response_body "
            "FROM idempotency_keys WHERE key = :key AND user_id = :uid"
        ),
        {"key": key, "uid": user_id},
    )).mappings().first()
    return dict(row) if row else None


async def store(
    session,
    key: str,
    user_id: int,
    request_hash: str,
    status_code: int,
    response_body: dict,
) -> None:
    await session.execute(
        text(
            "INSERT INTO idempotency_keys "
            "(key, user_id, request_hash, status_code, response_body) "
            "VALUES (:key, :uid, :hash, :sc, CAST(:body AS jsonb)) "
            "ON CONFLICT (key, user_id) DO NOTHING"
        ),
        {
            "key": key,
            "uid": user_id,
            "hash": request_hash,
            "sc": status_code,
            "body": json.dumps(response_body),
        },
    )
    await session.commit()
