import uuid

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.application.matter_chat_service import (
    AssistantUnavailableError,
    ChatMessageNotFoundError,
    InvalidEditTargetError,
    NoReadyDocumentsError,
)
from app.domain.search import InvalidSearchError
from app.web.api import container
from app.web.api.common import (
    api_error,
    chat_history_json,
    chat_message_json,
    client_json,
    matter_json,
    not_found,
    parse_date,
    pin_json,
    require_json,
    resolve_lawyer,
    unauthenticated,
    validation,
)

router = APIRouter(prefix="/api")


class QuestionRequest(BaseModel):
    question: str | None = None


class PinRequest(BaseModel):
    pinned: bool


class RecentSearchRequest(BaseModel):
    query: str | None = None


def _assistant_unavailable():
    return api_error(502, "ASSISTANT_UNAVAILABLE", "Couldn't reach the Assistant — retry.")


def _no_ready_documents():
    return api_error(422, "NO_READY_DOCUMENTS", "This Matter has no ready Documents to search yet.")


def _owned_matter_lawyer(request: Request, matter_id: uuid.UUID):
    """(lawyer, error_response): auth first, then BR-008 Matter ownership."""
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return None, unauthenticated()
    if container.matter_service.get(lawyer.firm_id, str(matter_id)) is None:
        return None, not_found("Matter not found")
    return lawyer, None


# ---------------------------------------------------------------- chat (SD-005)


@router.get("/matters/{matter_id}/chat")
def chat_history(matter_id: uuid.UUID, request: Request):
    lawyer, error = _owned_matter_lawyer(request, matter_id)
    if error:
        return error
    try:
        return chat_history_json(container.chat_service.history(str(matter_id)))
    except AssistantUnavailableError:
        return _assistant_unavailable()


@router.post("/matters/{matter_id}/chat", dependencies=[Depends(require_json)])
def ask(matter_id: uuid.UUID, body: QuestionRequest, request: Request):
    lawyer, error = _owned_matter_lawyer(request, matter_id)
    if error:
        return error
    if not (body.question or "").strip():
        return validation("question is required")
    try:
        return chat_message_json(container.chat_service.ask(str(matter_id), lawyer.id, body.question))
    except NoReadyDocumentsError:
        return _no_ready_documents()
    except AssistantUnavailableError:
        return _assistant_unavailable()


@router.post("/matters/{matter_id}/chat/{message_id}/edit", dependencies=[Depends(require_json)])
def edit_message(matter_id: uuid.UUID, message_id: uuid.UUID, body: QuestionRequest, request: Request):
    lawyer, error = _owned_matter_lawyer(request, matter_id)
    if error:
        return error
    if not (body.question or "").strip():
        return validation("question is required")
    try:
        return chat_history_json(container.chat_service.edit_message(str(matter_id), str(message_id), lawyer.id, body.question))
    except ChatMessageNotFoundError:
        return not_found("Chat message not found")
    except InvalidEditTargetError:
        return validation("Only a user message can be edited")
    except NoReadyDocumentsError:
        return _no_ready_documents()
    except AssistantUnavailableError:
        return _assistant_unavailable()


@router.patch("/matters/{matter_id}/chat/{message_id}/activate")
def activate_branch(matter_id: uuid.UUID, message_id: uuid.UUID, request: Request):
    lawyer, error = _owned_matter_lawyer(request, matter_id)
    if error:
        return error
    try:
        return chat_history_json(container.chat_service.activate_branch(str(matter_id), str(message_id)))
    except ChatMessageNotFoundError:
        return not_found("Chat message not found")
    except AssistantUnavailableError:
        return _assistant_unavailable()


@router.patch("/matters/{matter_id}/chat/{message_id}/pin", dependencies=[Depends(require_json)])
def toggle_pin(matter_id: uuid.UUID, message_id: uuid.UUID, body: PinRequest, request: Request):
    lawyer, error = _owned_matter_lawyer(request, matter_id)
    if error:
        return error
    try:
        return pin_json(container.chat_service.toggle_pin(str(matter_id), str(message_id), body.pinned))
    except ChatMessageNotFoundError:
        return not_found("Chat message not found")
    except AssistantUnavailableError:
        return _assistant_unavailable()


# ---------------------------------------------------------------- search (SD-009)


@router.get("/search")
def search(
    request: Request,
    q: str | None = None,
    status: str | None = None,
    from_: str | None = Query(None, alias="from"),
    to: str | None = None,
):
    """REQ-011: Clients and Matters by name, status and date, scoped to the caller's Firm (BR-008)."""
    from_date = parse_date(from_)
    to_date = parse_date(to)
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    try:
        result = container.search_service.search(lawyer.firm_id, q, status, from_date, to_date)
    except InvalidSearchError as e:
        return validation(str(e))
    return {"clients": [client_json(c) for c in result.clients], "matters": [matter_json(m) for m in result.matters]}


@router.post("/search/recent", dependencies=[Depends(require_json)])
def record_recent_search(body: RecentSearchRequest, request: Request):
    """I-48: record a real search so it can be offered back next time."""
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    try:
        container.recent_search_service.record(lawyer.id, body.query)
    except InvalidSearchError as e:
        return validation(str(e))
    return {}


@router.get("/search/recent")
def recent_searches(request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    return {"queries": [s.query for s in container.recent_search_service.list_recent(lawyer.id)]}
