from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class InvalidDocumentError(ValueError):
    pass


class DocumentStatus(StrEnum):
    """Values match Postgres's native `document_status` enum labels."""

    uploading = "uploading"
    processing = "processing"
    ready = "ready"
    failed = "failed"


# REQ-003: "PDF, DOCX, scanned images."
ALLOWED_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/png",
        "image/jpeg",
        "image/tiff",
        "image/webp",
    }
)

UNSUPPORTED_TYPE_MESSAGE = "Unsupported file type — only PDF, DOCX, and common image formats are accepted (REQ-003)."


@dataclass(frozen=True)
class NewDocument:
    matter_id: str
    uploaded_by: str
    file_name: str
    storage_key: str
    mime_type: str
    size_bytes: int


@dataclass(frozen=True)
class NewDraftDocument:
    """SD-007: a generated draft's mime type is controlled internally
    (DraftGenerationService), not REQ-003's upload allow-list."""

    matter_id: str
    uploaded_by: str
    file_name: str
    storage_key: str
    mime_type: str
    size_bytes: int
    source_template_id: str


def _require_owner_fields(matter_id: str | None, uploaded_by: str | None, file_name: str | None) -> str:
    if not matter_id:
        raise InvalidDocumentError("A Document must belong to a Matter (BR-002).")
    if not uploaded_by:
        raise InvalidDocumentError("A Document must record who uploaded it.")
    trimmed = (file_name or "").strip()
    if not trimmed:
        raise InvalidDocumentError("A file name is required.")
    return trimmed


@dataclass(frozen=True)
class Document:
    id: str
    matter_id: str
    uploaded_by: str
    file_name: str
    storage_key: str
    mime_type: str
    size_bytes: int
    status: DocumentStatus
    is_draft: bool
    source_template_id: str | None
    error_message: str | None
    created_at: datetime

    @staticmethod
    def is_supported_mime_type(mime_type: str | None) -> bool:
        return mime_type is not None and mime_type in ALLOWED_MIME_TYPES

    @staticmethod
    def create(matter_id, uploaded_by, file_name, storage_key, mime_type, size_bytes: int) -> NewDocument:
        """BR-002: a Document must belong to exactly one Matter. A new Document
        always starts "uploading" — "processing" once stored, "ready" only after
        SD-004's ingestion pipeline succeeds (REQ-004)."""
        trimmed = _require_owner_fields(matter_id, uploaded_by, file_name)
        if not Document.is_supported_mime_type(mime_type):
            raise InvalidDocumentError(UNSUPPORTED_TYPE_MESSAGE)
        if size_bytes <= 0:
            raise InvalidDocumentError("Uploaded file is empty.")
        if not storage_key or not storage_key.strip():
            raise InvalidDocumentError("A Document must have a storage location.")
        return NewDocument(matter_id, uploaded_by, trimmed, storage_key, mime_type, size_bytes)

    @staticmethod
    def create_draft(matter_id, uploaded_by, file_name, storage_key, mime_type, size_bytes: int, source_template_id) -> NewDraftDocument:
        """SD-007: a generated draft is a Document like any other (REQ-015) —
        same BR-002/required-fields invariants, plus it must record which
        Template produced it."""
        trimmed = _require_owner_fields(matter_id, uploaded_by, file_name)
        if not mime_type or not mime_type.strip():
            raise InvalidDocumentError("A generated draft must have a content type.")
        if size_bytes <= 0:
            raise InvalidDocumentError("Generated draft content is empty.")
        if not storage_key or not storage_key.strip():
            raise InvalidDocumentError("A Document must have a storage location.")
        if not source_template_id:
            raise InvalidDocumentError("A generated draft must record which Template it came from.")
        return NewDraftDocument(matter_id, uploaded_by, trimmed, storage_key, mime_type, size_bytes, source_template_id)
