from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class LLMMessage:
    role: str  # 'system' | 'user' | 'assistant'
    content: str


@dataclass(slots=True)
class LLMResponse:
    content: str
    input_tokens: int
    output_tokens: int


class LLMClient(Protocol):
    async def call(
        self,
        *,
        operation: str,
        request_id: str,
        messages: list[LLMMessage],
        model: str | None = None,
    ) -> LLMResponse: ...
