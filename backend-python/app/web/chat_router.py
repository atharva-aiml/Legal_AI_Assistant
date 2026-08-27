from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.application.chat_service import (
    AssistantUnavailableError,
    ChatMessageNotFoundError,
    ChatService,
    InvalidEditTargetError,
    NoReadyDocumentsError,
)
from app.domain.chat import ChatMessage, Citation
from app.infrastructure.chat_repository import SqlAlchemyChatRepository
from app.infrastructure.embedding import SentenceTransformerEmbedder
from app.infrastructure.llm import OpenAIChatLLM

router = APIRouter()


def _message_dict(service: ChatService, message: ChatMessage, citations: list[Citation]) -> dict:
    return {
        "id": message.id,
        "matterId": message.matter_id,
        "lawyerId": message.lawyer_id,
        "role": message.role,
        "content": message.content,
        "createdAt": message.created_at.isoformat() if message.created_at else None,
        "citations": [_citation_dict(c) for c in citations],
        "pinned": message.pinned,
        # Edit-a-previous-message branching: parentId is null for a root-level
        # message; siblingIds is the ordered id list every "‹ i/N ›" edit-arrow
        # UI is built from (this message's id included) — no separate
        # index/count field, the frontend computes that from the list.
        "parentId": message.parent_id,
        "siblingIds": service.sibling_ids(message),
    }


def _citation_dict(citation: Citation) -> dict:
    return {
        "id": citation.id,
        "documentId": citation.document_id,
        "fileName": citation.file_name,
        "pageNumber": citation.page_number,
        "section": citation.section,
        "excerpt": citation.excerpt,
    }


def _service() -> ChatService:
    repository = SqlAlchemyChatRepository()
    return ChatService(retrieval=repository, messages=repository, embedder=SentenceTransformerEmbedder(), llm=OpenAIChatLLM())


@router.get("/chat/{matter_id}")
def get_history(matter_id: str):
    """Called by Java's GET /api/matters/{id}/chat after it has already
    verified the lawyer's session and the Matter's Firm ownership (BR-008) —
    not exposed to the browser directly, same trust boundary as /ingest."""
    service = _service()
    history = service.history(matter_id)
    return {"messages": [_message_dict(service, m, c) for m, c in history]}


@router.post("/chat/{matter_id}")
def ask(matter_id: str, body: dict):
    """Called by Java's POST /api/matters/{id}/chat, which has already
    resolved lawyer_id and verified Matter ownership — this endpoint trusts
    the lawyer_id it's given rather than re-deriving it (System
    Architecture SD-003: Java is the sole authority on session validity)."""
    lawyer_id = body["lawyerId"]
    question = body["question"]

    service = _service()
    try:
        result = service.ask(matter_id, lawyer_id, question)
    except NoReadyDocumentsError:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "NO_READY_DOCUMENTS", "message": "This Matter has no ready Documents to search yet."}},
        )
    except AssistantUnavailableError:
        return JSONResponse(
            status_code=502,
            content={"error": {"code": "ASSISTANT_UNAVAILABLE", "message": "Couldn't reach the Assistant — retry."}},
        )

    response = _message_dict(service, result.message, result.citations)
    response["lowConfidence"] = result.low_confidence
    response["fullContext"] = result.full_context
    return response


@router.post("/chat/{matter_id}/{message_id}/edit")
def edit(matter_id: str, message_id: str, body: dict):
    """Called by Java's POST /api/matters/{id}/chat/{messageId}/edit, same
    trust boundary as the other chat routes. ChatGPT-style edit: never
    deletes/overwrites the original message — creates a new sibling branch at
    that position with its own new assistant reply, and returns the full new
    active path (not just the two new messages), so the frontend always just
    replaces its message list wholesale on any mutating call."""
    lawyer_id = body["lawyerId"]
    question = body["question"]

    service = _service()
    try:
        path = service.edit(matter_id, message_id, lawyer_id, question)
    except ChatMessageNotFoundError:
        return JSONResponse(status_code=404, content={"error": {"code": "NOT_FOUND", "message": "Chat message not found."}})
    except InvalidEditTargetError:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "VALIDATION", "message": "Only a user message can be edited."}},
        )
    except NoReadyDocumentsError:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "NO_READY_DOCUMENTS", "message": "This Matter has no ready Documents to search yet."}},
        )
    except AssistantUnavailableError:
        return JSONResponse(
            status_code=502,
            content={"error": {"code": "ASSISTANT_UNAVAILABLE", "message": "Couldn't reach the Assistant — retry."}},
        )

    return {"messages": [_message_dict(service, m, c) for m, c in path]}


@router.patch("/chat/{matter_id}/{message_id}/activate")
def activate(matter_id: str, message_id: str):
    """Called by Java's PATCH /api/matters/{id}/chat/{messageId}/activate, same
    trust boundary as the other chat routes. Repoints which sibling branch is
    active — e.g. switching back to a pre-edit branch — without generating
    anything new (the sibling being activated already has its own subtree)."""
    service = _service()
    try:
        path = service.activate_branch(matter_id, message_id)
    except ChatMessageNotFoundError:
        return JSONResponse(status_code=404, content={"error": {"code": "NOT_FOUND", "message": "Chat message not found."}})

    return {"messages": [_message_dict(service, m, c) for m, c in path]}


@router.patch("/chat/{matter_id}/messages/{message_id}/pin")
def toggle_pin(matter_id: str, message_id: str, body: dict):
    """Called by Java's PATCH /api/matters/{id}/chat/{messageId}/pin, same trust
    boundary as the other chat routes. Only an assistant message in this Matter can
    be pinned — anything else (wrong id, a user message, another Matter's message)
    is a 404, not a 400, matching how the rest of this codebase treats an
    out-of-scope id as "not found" rather than a distinct validation error."""
    pinned = body["pinned"]
    service = _service()
    try:
        message = service.toggle_pin(matter_id, message_id, pinned)
    except ChatMessageNotFoundError:
        return JSONResponse(status_code=404, content={"error": {"code": "NOT_FOUND", "message": "Chat message not found."}})
    return {"id": message.id, "pinned": message.pinned}
