from fastapi import FastAPI

from app.api.sentiment import router as sentiment_router

app = FastAPI(title="Vascora Ingestion API", version="0.1.0")
app.include_router(sentiment_router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
