from fastapi import FastAPI

from app.api.analytics import router as analytics_router
from app.api.ingest import router as ingest_router
from app.api.sentiment import router as sentiment_router

app = FastAPI(title="Vascora Ingestion API", version="0.1.0")
app.include_router(ingest_router)
app.include_router(analytics_router)
app.include_router(sentiment_router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
