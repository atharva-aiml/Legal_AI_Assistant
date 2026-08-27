from typing import Protocol

from app.domain.chat import ChatMessage, Citation, DocumentMetadata
from app.domain.chunk import ExtractedPage


class FileStorage(Protocol):
    def read(self, storage_key: str) -> bytes: ...


class TextExtractor(Protocol):
    def extract(self, file_bytes: bytes, mime_type: str) -> list[ExtractedPage]: ...


class ImageCaptioner(Protocol):
    """RAG-Pipeline-Development-History.md gap #2: OCR alone either finds
    nothing (a textless diagram is silently dropped, genuinely absent from
    the corpus) or returns a lossy bag of disconnected words (a flowchart's
    actual structure/relationships are lost). A vision-capable caption
    recovers both. Returns None when the image is blank/decorative with
    nothing meaningful to describe (never fabricated content for real
    nothing) — this is the resolved form of the model's own NO_CONTENT
    sentinel, decided once at the infrastructure boundary."""

    def caption(self, image_bytes: bytes) -> str | None: ...


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

    def exact_match_chunks(self, matter_id: str, refs: list[tuple[str, int]]) -> list:
        """refs: (kind, number) pairs from app.domain.identifier_query,
        kind in {"page", "section", "table", "image"}. Guarantees every
        chunk that really carries that identifier is returned (not subject
        to ranking or a top-K cutoff) — the fix for RAG-Pipeline-Development-
        History.md gap #1."""
        ...


class ChatMessageRepository(Protocol):
    def save_user_message(self, matter_id: str, lawyer_id: str, content: str, parent_id: str | None = None) -> ChatMessage: ...

    def save_assistant_message(
        self,
        matter_id: str,
        content: str,
        citations: list[tuple[str, int | None, str, str, str | None]],
        parent_id: str | None = None,
    ) -> tuple[ChatMessage, list[Citation]]: ...

    def list_messages(self, matter_id: str) -> list[tuple[ChatMessage, list[Citation]]]: ...

    def toggle_pin(self, matter_id: str, message_id: str, pinned: bool) -> ChatMessage | None:
        """None means no matching assistant message in this Matter — pinning a user
        message, or a message from a different Matter, is treated as not-found."""
        ...

    def list_pinned(self, matter_id: str) -> list[tuple[ChatMessage, list[Citation]]]: ...

    def citations_for(self, message_id: str) -> list[Citation]: ...

    # --- Edit-a-previous-message branching ---

    def get_by_id(self, message_id: str) -> ChatMessage | None: ...

    def siblings(self, matter_id: str, parent_id: str | None) -> list[ChatMessage]:
        """Every message sharing this parent_id (the null-parent/root case included),
        ordered by created_at — used to build the ‹ i/N › UI on the frontend."""
        ...

    def set_active_child(self, message_id: str, child_id: str) -> None: ...

    def get_matter_active_root(self, matter_id: str) -> str | None: ...

    def set_matter_active_root(self, matter_id: str, message_id: str) -> None: ...

    def active_path(self, matter_id: str) -> list[ChatMessage]:
        """Walks the Matter's active_root_message_id -> active_child_id chain,
        oldest to newest — this is "the messages" the API returns, not every row."""
        ...

    def history_before(self, message_id: str, limit: int) -> list[ChatMessage]:
        """Walks parent_id backward from message_id (not included) up to limit
        messages, returned oldest -> newest — the real conversation history that
        led up to message_id on ITS branch, unlike a plain "last N by matter_id"
        query which could pull messages from a superseded or sibling branch."""
        ...


class ChatLLM(Protocol):
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...
