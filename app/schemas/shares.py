from pydantic import BaseModel
from typing import Literal


class CreateShareRequest(BaseModel):
    target_user_id: int
    permission: Literal["view", "edit"]


class ShareResponse(BaseModel):
    id: int
    report_id: int
    target_user_id: int
    permission: str
    granted_by_user_id: int
    created_at: str
