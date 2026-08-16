from fastapi import APIRouter, HTTPException

from app.application.ingestion_service import IngestionService
from app.infrastructure.embedding import SentenceTransformerEmbedder
from app.infrastructure.extraction import DocumentTextExtractor
from app.infrastructure.repository import SqlAlchemyIngestionRepository
from app.infrastructure.storage import LocalFileStorage

router = APIRouter()


@router.post("/ingest/{document_id}")
def ingest(document_id: str):
    """Called by Java right after upload (System Architecture §5/§6) —
    processed synchronously here; Java doesn't wait for this to return.
    A 404 means Java pointed at a Document that doesn't exist (a real
    integration bug); 200 covers both a successful ingestion AND a
    business-level ingestion failure (bad file, no text) — the latter
    is a legitimate outcome recorded on the Document itself, not a
    transport-level error Java needs to react to."""
    repository = SqlAlchemyIngestionRepository()
    document = repository.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    service = IngestionService(
        storage=LocalFileStorage(),
        extractor=DocumentTextExtractor(),
        embedder=SentenceTransformerEmbedder(),
        repository=repository,
    )
    service.ingest(document_id, document["storage_key"], document["mime_type"])
    return {"status": "processed"}
