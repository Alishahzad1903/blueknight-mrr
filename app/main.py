from fastapi import FastAPI
from app.middleware.request_id import RequestIDMiddleware
from app.logging_config import configure_logging
from app.routers import shares, reports, sections

configure_logging()

app = FastAPI(title="BlueKnight MRR Collaborative")
app.add_middleware(RequestIDMiddleware)

app.include_router(shares.router)
app.include_router(reports.router)
app.include_router(sections.router)


@app.get("/healthz")
async def healthz():
    return {"ok": True}
