from fastapi import FastAPI
from app.llm.in_memory import InMemoryLLMClient
from app.llm.client import LLMClient

app = FastAPI(title="BlueKnight MRR Collaborative")

_llm_singleton = InMemoryLLMClient()


def get_llm_client() -> LLMClient:
    return _llm_singleton


@app.get("/healthz")
async def healthz():
    return {"ok": True}
