from dataclasses import dataclass
from fastapi import Depends, HTTPException, Header
from app.auth.jwt_helper import decode_token


@dataclass
class CurrentUser:
    user_id: int
    org_id: int


async def get_current_user(authorization: str = Header(default="")) -> CurrentUser:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer")
    try:
        payload = decode_token(authorization[7:])
    except Exception:
        raise HTTPException(401, "invalid token")
    return CurrentUser(user_id=payload["user_id"], org_id=payload["org_id"])
