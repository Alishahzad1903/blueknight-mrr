from app.llm.client import LLMMessage, LLMResponse


class InMemoryLLMClient:
    def __init__(self) -> None:
        self.call_count = 0
        self.last_call: dict | None = None
        self._exception: Exception | None = None

    def inject_exception(self, exc: Exception) -> None:
        """Next call() will raise this exception once, then clear."""
        self._exception = exc

    async def call(
        self,
        *,
        operation: str,
        request_id: str,
        messages: list[LLMMessage],
        model: str | None = None,
    ) -> LLMResponse:
        self.call_count += 1
        self.last_call = {
            "operation": operation,
            "request_id": request_id,
            "messages": messages,
            "model": model,
        }
        if self._exception is not None:
            exc, self._exception = self._exception, None
            raise exc
        last_user = next(
            (m.content for m in reversed(messages) if m.role == "user"),
            "",
        )
        rewritten = last_user.upper()
        return LLMResponse(
            content=rewritten,
            input_tokens=len(last_user),
            output_tokens=len(rewritten),
        )
