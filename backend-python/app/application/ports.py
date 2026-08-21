from typing import Protocol

from app.domain.chat import ChatMessage, Citation, DocumentMetadata
from app.domain.chunk import ExtractedPage


class FileStorage(Protocol):
    def read(self, storage_key: str) -> bytes: ...


class TextExtractor(Protocol):
    def extract(self, file_bytes: bytes, mime_type: str) -> list[ExtractedPage]: ...


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class IngestionRepository(Protocol):
    """chunks: list of (content, embedding, page_number, section, chunk_type, element_number)."""

    def save_chunks(self, document_id: str, chunks: list[tuple[str, list[float], int | None, str | None, str, int | None]]) -> None: ...

    def mark_ready(self, document_id: str) -> None: ...

    def mark_failed(self, document_id: str, error_message: str) -> None: ...


class RetrievedChunk(Protocol):
    id: str
    document_id: str
    file_name: str
    page_number: int | None
    content: str
    section: str | None
    chunk_type: str
    element_number: int | None


class ChatRetrievalRepository(Protocol):
    """BR-005: every method here is hard-filtered to one Matter's Ready
    Documents at the SQL level (AI Architecture §3, Grounding Rule 1) —
    a different Matter's chunks are never in the candidate pool to begin
    with, so the rule can't be violated by anything above this layer."""

    def ready_document_count(self, matter_id: str) -> int: ...

    def vector_search(self, matter_id: str, query_embedding: list[float], top_k: int) -> list: ...

    def keyword_search(self, matter_id: str, query: str, top_k: int) -> list: ...

    def document_metadata(self, matter_id: str) -> list[DocumentMetadata]: ...

    def all_ready_chunks(self, matter_id: str) -> list: ...


class ChatMessageRepository(Protocol):
    def save_user_message(self, matter_id: str, lawyer_id: str, content: str) -> ChatMessage: ...

    def save_assistant_message(
        self, matter_id: str, content: str, citations: list[tuple[str, int | None, str, str, str | None]]
    ) -> tuple[ChatMessage, list[Citation]]: ...

    def recent_messages(self, matter_id: str, limit: int) -> list[ChatMessage]: ...

    def list_messages(self, matter_id: str) -> list[tuple[ChatMessage, list[Citation]]]: ...

    def toggle_pin(self, matter_id: str, message_id: str, pinned: bool) -> ChatMessage | None:
        """None means no matching assistant message in this Matter — pinning a user
        message, or a message from a different Matter, is treated as not-found."""
        ...

    def list_pinned(self, matter_id: str) -> list[tuple[ChatMessage, list[Citation]]]: ...


class ChatLLM(Protocol):
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...
