from fastapi import FastAPI

app = FastAPI(title="BlueKnight MRR Collaborative")


@app.get("/healthz")
async def healthz():
    return {"ok": True}
