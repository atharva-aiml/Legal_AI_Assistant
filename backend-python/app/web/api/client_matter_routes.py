import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.application.matter_service import MatterHasOpenDeadlinesError
from app.domain.client import InvalidClientError
from app.domain.matter import InvalidMatterError, MatterStatus
from app.web.api import container
from app.web.api.common import (
    BadRequestParam,
    activity_json,
    client_json,
    deadline_json,
    matter_json,
    not_found,
    parse_uuid,
    require_json,
    resolve_lawyer,
    unauthenticated,
    validation,
)

router = APIRouter(prefix="/api")


class ClientRequest(BaseModel):
    name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    notes: str | None = None


class CreateMatterRequest(BaseModel):
    client_id: str | None = None
    title: str | None = None


class RenameMatterRequest(BaseModel):
    title: str | None = None


# ---------------------------------------------------------------- clients


@router.get("/clients")
def list_clients(request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    return {"clients": [client_json(c) for c in container.client_service.list(lawyer.firm_id)]}


@router.post("/clients", dependencies=[Depends(require_json)])
def create_client(body: ClientRequest, request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    try:
        created = container.client_service.create(lawyer.firm_id, body.name, body.contact_email, body.contact_phone, body.notes)
    except InvalidClientError as e:
        return validation(str(e))
    return JSONResponse(status_code=201, content=client_json(created))


@router.get("/clients/{client_id}")
def get_client(client_id: uuid.UUID, request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    client = container.client_service.get(lawyer.firm_id, str(client_id))
    return {"client": client_json(client)} if client else not_found("Client not found")


@router.patch("/clients/{client_id}", dependencies=[Depends(require_json)])
def update_client(client_id: uuid.UUID, body: ClientRequest, request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    try:
        updated = container.client_service.update(lawyer.firm_id, str(client_id), body.name, body.contact_email, body.contact_phone, body.notes)
    except InvalidClientError as e:
        return validation(str(e))
    return client_json(updated) if updated else not_found("Client not found")


@router.delete("/clients/{client_id}")
def delete_client(client_id: uuid.UUID, request: Request):
    """Irreversible: cascade-deletes every Matter under this Client and
    everything under those (ClientService.delete_cascade). Confirmation is the
    frontend's job before this is ever called."""
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    if not container.client_service.delete_cascade(lawyer.firm_id, str(client_id)):
        return not_found("Client not found")
    return Response(status_code=204)


# ---------------------------------------------------------------- matters


@router.get("/matters/recent")
def recent_matters(request: Request):
    """I-07: declared above /matters/{id}, or "recent" would be parsed as a Matter UUID."""
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    matters = []
    for view in container.matter_view_service.list_recently_viewed(lawyer.id):
        matter = container.matter_service.get(lawyer.firm_id, view.matter_id)
        if matter is not None:
            matters.append(matter_json(matter))
    return {"matters": matters}


@router.get("/matters")
def list_matters(request: Request, clientId: str | None = None, status: str | None = None):
    client_id = parse_uuid(clientId)
    matter_status = None
    if status is not None and status.strip():
        try:
            matter_status = MatterStatus(status.strip())
        except ValueError:
            raise BadRequestParam(status) from None

    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    return {"matters": [matter_json(m) for m in container.matter_service.list(lawyer.firm_id, client_id, matter_status)]}


@router.post("/matters", dependencies=[Depends(require_json)])
def create_matter(body: CreateMatterRequest, request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()

    try:
        client_id = str(uuid.UUID(body.client_id)) if body.client_id is not None else None
    except ValueError:
        client_id = None  # a malformed id is treated as "no Client" -> BR-001's validation message

    # Confirm the Client is real AND in the caller's Firm before creating the
    # Matter (BR-008) — a cross-entity authorization check, not a Matter rule.
    if client_id is not None and container.client_service.get(lawyer.firm_id, client_id) is None:
        return not_found("Client not found")

    try:
        created = container.matter_service.create(lawyer.firm_id, client_id, body.title)
    except InvalidMatterError as e:
        return validation(str(e))
    return JSONResponse(status_code=201, content=matter_json(created))


@router.get("/matters/{matter_id}")
def get_matter(matter_id: uuid.UUID, request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    matter = container.matter_service.get(lawyer.firm_id, str(matter_id))
    if matter is None:
        return not_found("Matter not found")
    client = container.client_service.get(lawyer.firm_id, matter.client_id)
    return {"matter": matter_json(matter), "client": client_json(client) if client else None}


@router.post("/matters/{matter_id}/view")
def record_matter_view(matter_id: uuid.UUID, request: Request):
    """I-07: separate from GET so opening Matter Detail has one explicit, idempotent write."""
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    if container.matter_service.get(lawyer.firm_id, str(matter_id)) is None:
        return not_found("Matter not found")
    container.matter_view_service.record_view(lawyer.id, str(matter_id))
    return {}


@router.get("/matters/{matter_id}/activity")
def matter_activity(matter_id: uuid.UUID, request: Request):
    """I-32: read-only merge of Documents, Deadlines and Chat questions."""
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    if container.matter_service.get(lawyer.firm_id, str(matter_id)) is None:
        return not_found("Matter not found")
    return {"entries": [activity_json(e) for e in container.activity_service.for_matter(lawyer.firm_id, str(matter_id))]}


@router.patch("/matters/{matter_id}", dependencies=[Depends(require_json)])
def rename_matter(matter_id: uuid.UUID, body: RenameMatterRequest, request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    try:
        renamed = container.matter_service.rename(lawyer.firm_id, str(matter_id), body.title or "")
    except InvalidMatterError as e:
        return validation(str(e))
    return matter_json(renamed) if renamed else not_found("Matter not found")


@router.post("/matters/{matter_id}/close")
def close_matter(matter_id: uuid.UUID, request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    try:
        closed = container.matter_service.close(lawyer.firm_id, str(matter_id))
    except MatterHasOpenDeadlinesError as e:
        # BR-003's 409 carries the specific blocking Deadlines, not just a message.
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "OPEN_DEADLINES", "message": str(e), "openDeadlines": [deadline_json(d) for d in e.open_deadlines]}},
        )
    return matter_json(closed) if closed else not_found("Matter not found")


@router.post("/matters/{matter_id}/reopen")
def reopen_matter(matter_id: uuid.UUID, request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    try:
        reopened = container.matter_service.reopen(lawyer.firm_id, str(matter_id))
    except InvalidMatterError as e:
        return validation(str(e))
    return matter_json(reopened) if reopened else not_found("Matter not found")


@router.delete("/matters/{matter_id}")
def delete_matter(matter_id: uuid.UUID, request: Request):
    """Irreversible: cascade-deletes this Matter's Documents/Deadlines/chat
    history/views (MatterService.delete_cascade)."""
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    if not container.matter_service.delete_cascade(lawyer.firm_id, str(matter_id)):
        return not_found("Matter not found")
    return Response(status_code=204)
