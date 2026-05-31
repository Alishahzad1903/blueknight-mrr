from app.llm.in_memory import InMemoryLLMClient
from app.llm.client import LLMClient

_llm_singleton = InMemoryLLMClient()


def get_llm_client() -> LLMClient:
    return _llm_singleton
