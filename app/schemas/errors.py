from pydantic import BaseModel


class ErrorDetail(BaseModel):
    error: str
    detail: str | None = None
