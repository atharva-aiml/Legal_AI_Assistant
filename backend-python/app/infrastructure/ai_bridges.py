"""In-process hand-offs from the public API to the AI modules (Document
Ingestion, SD-004; AI Chat, SD-005). They replace the former Java backend's
HttpIngestionTrigger/HttpChatGateway, which POSTed to this same Python code
over HTTP on :8000. Each one now calls the exact same router function those
HTTP calls landed on (app.web.ingest_router / app.web.chat_router — both
unchanged), and maps its outcome the same way the Java adapters mapped HTTP
status codes, so AI behavior and error semantics are identical; only the
network hop is gone."""

import logging
import threading
from datetime import datetime, timezone

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.application.crud_ports import DocumentRepository
from app.application.matter_chat_service import (
    AssistantUnavailableError,
    ChatHistoryDto,
    ChatMessageDto,
    ChatMessageNotFoundError,
    CitationDto,
    InvalidEditTargetError,
    NoReadyDocumentsError,
    PinToggleDto,
)
from app.domain.document import DocumentStatus
from app.web import chat_router, ingest_router

log = logging.getLogger(__name__)

PROCESSING_FAILED_MESSAGE = "Document processing failed — retry by re-uploading."


class InProcessIngestionTrigger:
    """Fire-and-forget: runs ingestion on its own thread so the upload
    response never waits for it. If the pipeline errors out before it can
    record its own outcome (e.g. the Document row vanished), this marks the
    Document 'failed' — no failure is invisible (System Architecture §7).
    Business-level failures (bad file, no text) are recorded by the pipeline
    itself, as before."""

    def __init__(self, documents: DocumentRepository) -> None:
        self.documents = documents

    def trigger_ingestion(self, document_id: str) -> None:
        threading.Thread(target=self._run, args=(document_id,), name=f"ingest-{document_id}", daemon=True).start()

    def _run(self, document_id: str) -> None:
        try:
            ingest_router.ingest(document_id)
        except HTTPException as e:
            log.error("Ingestion request for document %s failed with status %s", document_id, e.status_code)
            self.documents.update_status(document_id, DocumentStatus.failed, PROCESSING_FAILED_MESSAGE)
        except Exception:
            log.exception("Ingestion crashed for document %s", document_id)
            self.documents.update_status(document_id, DocumentStatus.failed, PROCESSING_FAILED_MESSAGE)


def _parse_instant(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def _message(d: dict) -> ChatMessageDto:
    return ChatMessageDto(
        id=d["id"],
        matter_id=d["matterId"],
        lawyer_id=d.get("lawyerId"),
        role=d["role"],
        content=d["content"],
        created_at=_parse_instant(d.get("createdAt")),
        citations=[
            CitationDto(c.get("id"), c.get("documentId"), c.get("fileName"), c.get("pageNumber"), c.get("section"), c.get("excerpt"))
            for c in d.get("citations") or []
        ],
        low_confidence=d.get("lowConfidence"),
        full_context=d.get("fullContext"),
        pinned=d.get("pinned"),
        parent_id=d.get("parentId"),
        sibling_ids=d.get("siblingIds"),
    )


def _history(d: dict) -> ChatHistoryDto:
    return ChatHistoryDto([_message(m) for m in d["messages"]])


def _call(fn, *args, not_found: bool = False, invalid_edit: bool = False, no_ready: bool = False):
    """Runs one chat_router function and translates its outcome into the
    gateway's exceptions — the same status-code mapping HttpChatGateway did."""
    try:
        result = fn(*args)
    except Exception as e:  # what used to surface as a 5xx from Python
        log.exception("AI Chat call %s failed", fn.__name__)
        raise AssistantUnavailableError(str(e)) from e

    if isinstance(result, JSONResponse):
        status = result.status_code
        if not_found and status == 404:
            raise ChatMessageNotFoundError()
        if invalid_edit and status == 400:
            raise InvalidEditTargetError()
        if no_ready and status == 422:
            raise NoReadyDocumentsError()
        raise AssistantUnavailableError(f"Assistant returned {status}")
    return result


class InProcessChatGateway:
    def ask(self, matter_id: str, lawyer_id: str, question: str) -> ChatMessageDto:
        return _message(_call(chat_router.ask, matter_id, {"lawyerId": lawyer_id, "question": question}, no_ready=True))

    def history(self, matter_id: str) -> ChatHistoryDto:
        return _history(_call(chat_router.get_history, matter_id))

    def toggle_pin(self, matter_id: str, message_id: str, pinned: bool) -> PinToggleDto:
        result = _call(chat_router.toggle_pin, matter_id, message_id, {"pinned": pinned}, not_found=True)
        return PinToggleDto(result["id"], result["pinned"])

    def edit_message(self, matter_id: str, message_id: str, lawyer_id: str, question: str) -> ChatHistoryDto:
        body = {"lawyerId": lawyer_id, "question": question}
        return _history(_call(chat_router.edit, matter_id, message_id, body, not_found=True, invalid_edit=True, no_ready=True))

    def activate_branch(self, matter_id: str, message_id: str) -> ChatHistoryDto:
        return _history(_call(chat_router.activate, matter_id, message_id, not_found=True))
