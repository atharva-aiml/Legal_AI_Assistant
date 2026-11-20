from app.application.crud_ports import DocumentRepository, IngestionTrigger, StorageService, TemplateRepository
from app.domain.document import Document, DocumentStatus
from app.domain.template import InvalidTemplateError


class DraftGenerationFailedError(Exception):
    pass


DRAFT_MIME_TYPE = "text/plain"


class DraftGenerationService:
    """SD-007: renders a Template with lawyer-supplied field values into a new
    Document (is_draft=true), then hands it to the same ingestion pipeline every
    uploaded Document goes through (REQ-015) — mirrors DocumentService.upload's
    shape: validate -> store -> create row -> mark processing -> trigger."""

    def __init__(self, template_repository: TemplateRepository, document_repository: DocumentRepository, storage: StorageService, ingestion_trigger: IngestionTrigger) -> None:
        self.template_repository = template_repository
        self.document_repository = document_repository
        self.storage = storage
        self.ingestion_trigger = ingestion_trigger

    def generate(self, firm_id: str, matter_id: str, lawyer_id: str, template_id: str, fields: dict[str, str | None] | None) -> Document:
        template = self.template_repository.find_available(firm_id, template_id)
        if template is None:
            raise InvalidTemplateError("Template not found.")

        # Rendered (and its placeholder-completeness check run) before any
        # storage I/O — same "validate before writing" ordering as upload.
        content = template.render(fields).encode("utf-8")
        file_name = f"{template.name}.txt"

        try:
            storage_key = self.storage.store(file_name, content)
        except OSError as e:
            raise DraftGenerationFailedError("Couldn't save the generated draft.") from e

        draft = Document.create_draft(matter_id, lawyer_id, file_name, storage_key, DRAFT_MIME_TYPE, len(content), template.id)
        created = self.document_repository.create_draft(draft)
        self.document_repository.update_status(created.id, DocumentStatus.processing, None)
        self.ingestion_trigger.trigger_ingestion(created.id)
        return created
