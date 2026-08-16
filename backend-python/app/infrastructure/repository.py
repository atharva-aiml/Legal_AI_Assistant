from sqlalchemy import text

from app.infrastructure.db import engine


class SqlAlchemyIngestionRepository:
    """Writes DocumentChunk rows and updates Document.status directly —
    Python has its own DB connection to the shared Postgres instance
    (System Architecture §2's "shared database, two backend languages").
    Raw SQL with an explicit ::vector cast, rather than fighting an ORM's
    type system for a Postgres extension type it doesn't know natively."""

    def save_chunks(self, document_id: str, chunks: list[tuple[str, list[float], int | None]]) -> None:
        with engine.begin() as conn:
            for content, embedding, page_number in chunks:
                vector_literal = "[" + ",".join(str(x) for x in embedding) + "]"
                conn.execute(
                    text(
                        "INSERT INTO document_chunks (id, document_id, page_number, content, embedding, created_at) "
                        "VALUES (gen_random_uuid(), :document_id, :page_number, :content, CAST(:embedding AS vector), now())"
                    ),
                    {"document_id": document_id, "page_number": page_number, "content": content, "embedding": vector_literal},
                )

    def mark_ready(self, document_id: str) -> None:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE documents SET status = 'ready', error_message = NULL WHERE id = :id"),
                {"id": document_id},
            )

    def mark_failed(self, document_id: str, error_message: str) -> None:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE documents SET status = 'failed', error_message = :msg WHERE id = :id"),
                {"id": document_id, "msg": error_message},
            )

    def get_document(self, document_id: str) -> dict | None:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT id, storage_key, mime_type FROM documents WHERE id = :id"),
                {"id": document_id},
            ).mappings().first()
            return dict(row) if row else None
