from __future__ import annotations

from app.application.crud_ports import DocumentRepository, IngestionTrigger, StorageService
from app.domain.document import UNSUPPORTED_TYPE_MESSAGE, Document, DocumentStatus, InvalidDocumentError


class UploadFailedError(Exception):
    pass


class DocumentService:
    def __init__(self, repository: DocumentRepository, storage: StorageService, ingestion_trigger: IngestionTrigger) -> None:
        self.repository = repository
        self.storage = storage
        self.ingestion_trigger = ingestion_trigger

    def upload(self, matter_id: str, uploaded_by: str, file_name: str | None, mime_type: str | None, content: bytes) -> Document:
        """Stores the file, persists the Document row, then fires ingestion
        (SD-004) without waiting for it — REQ-004's "queryable after upload" is
        a property of the async pipeline, not of this call returning."""
        # Validated before any storage I/O — an unsupported type never gets
        # written to storage, so there's no orphan file to clean up.
        if not Document.is_supported_mime_type(mime_type):
            raise InvalidDocumentError(UNSUPPORTED_TYPE_MESSAGE)

        try:
            storage_key = self.storage.store(file_name, content)
        except OSError as e:
            raise UploadFailedError("Couldn't store the uploaded file.") from e

        created = self.repository.create(Document.create(matter_id, uploaded_by, file_name, storage_key, mime_type, len(content)))
        self.repository.update_status(created.id, DocumentStatus.processing, None)
        self.ingestion_trigger.trigger_ingestion(created.id)
        return created

    def list(self, firm_id: str, matter_id: str) -> list[Document]:
        return self.repository.list_by_matter(firm_id, matter_id)

    def get(self, firm_id: str, document_id: str) -> Document | None:
        return self.repository.find_by_id(firm_id, document_id)

    def download(self, firm_id: str, document_id: str) -> bytes | None:
        document = self.repository.find_by_id(firm_id, document_id)
        if document is None:
            return None
        try:
            return self.storage.retrieve(document.storage_key)
        except OSError as e:
            raise UploadFailedError("Couldn't read the stored file.") from e

    def delete(self, firm_id: str, document_id: str) -> bool:
        """REQ-027 — unrestricted by explicit user decision (not gated on Matter
        status). File first, then the row (whose deletion cascades
        document_chunks) — a row pointing at a missing file is a safer failure
        mode than an orphaned file with no row pointing at it."""
        document = self.repository.find_by_id(firm_id, document_id)
        if document is None:
            return False

        try:
            self.storage.delete(document.storage_key)
        except OSError as e:
            raise UploadFailedError("Couldn't delete the stored file.") from e

        return self.repository.delete(firm_id, document_id)
