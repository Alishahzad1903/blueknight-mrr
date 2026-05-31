from fastapi import FastAPI
from app.llm.in_memory import InMemoryLLMClient
from app.llm.client import LLMClient
from app.middleware.request_id import RequestIDMiddleware
from app.logging_config import configure_logging

configure_logging()

app = FastAPI(title="BlueKnight MRR Collaborative")
app.add_middleware(RequestIDMiddleware)

_llm_singleton = InMemoryLLMClient()


def get_llm_client() -> LLMClient:
    return _llm_singleton


@app.get("/healthz")
async def healthz():
    return {"ok": True}
