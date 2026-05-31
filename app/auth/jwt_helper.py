import jwt
from app.config import settings


def encode_token(user_id: int, org_id: int) -> str:
    return jwt.encode({"user_id": user_id, "org_id": org_id}, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
