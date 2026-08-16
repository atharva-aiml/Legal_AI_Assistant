from app.domain.chunk import chunk_pages
from app.application.ports import FileStorage, TextExtractor, Embedder, IngestionRepository


class IngestionService:
    """SD-004: fetch -> extract -> chunk -> embed -> persist. Every path
    ends in a visible Document status (System Architecture §7's "no
    failure is invisible" rule) — this method never lets an exception
    propagate unresolved; it always resolves to ready or failed."""

    def __init__(self, storage: FileStorage, extractor: TextExtractor, embedder: Embedder, repository: IngestionRepository):
        self.storage = storage
        self.extractor = extractor
        self.embedder = embedder
        self.repository = repository

    def ingest(self, document_id: str, storage_key: str, mime_type: str) -> None:
        try:
            file_bytes = self.storage.read(storage_key)
            pages = self.extractor.extract(file_bytes, mime_type)
            chunks = chunk_pages(pages)

            if not chunks:
                self.repository.mark_failed(document_id, "No extractable text found in this document.")
                return

            embeddings = self.embedder.embed([c.content for c in chunks])
            rows = [(c.content, embedding, c.page_number) for c, embedding in zip(chunks, embeddings)]

            self.repository.save_chunks(document_id, rows)
            self.repository.mark_ready(document_id)
        except Exception as e:  # noqa: BLE001 — intentionally broad: any failure must still resolve to 'failed'
            self.repository.mark_failed(document_id, str(e)[:500])
