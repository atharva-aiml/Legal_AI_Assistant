from fastapi import FastAPI

from app.web.chat_router import router as chat_router
from app.web.ingest_router import router as ingest_router

# Owns Document Ingestion (OCR -> chunk -> embed, V0.3, SD-004) and AI Chat
# (V0.4, SD-005). Both routers are internal — called by Java after it has
# already handled auth/BR-008, never exposed directly to the browser.

app = FastAPI(title="Legal AI Assistant - AI Backend")
app.include_router(ingest_router)
app.include_router(chat_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
