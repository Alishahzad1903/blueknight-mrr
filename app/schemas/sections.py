from pydantic import BaseModel
from typing import Any


class PatchSectionRequest(BaseModel):
    content: dict[str, Any]


class AIRewriteRequest(BaseModel):
    instruction: str
