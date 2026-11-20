import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.domain.deadline import DeadlinePriority, DeadlineStatus, InvalidDeadlineError
from app.web.api import container
from app.web.api.common import (
    deadline_json,
    not_found,
    notification_json,
    parse_date,
    require_json,
    resolve_lawyer,
    unauthenticated,
    validation,
)

router = APIRouter(prefix="/api")


class CreateDeadlineRequest(BaseModel):
    title: str | None = None
    dueDate: str | None = None
    priority: str | None = None
    notificationLeadDays: int | None = None


class UpdateDeadlineRequest(BaseModel):
    """All fields optional — PATCH semantics, omitted fields keep their current value."""

    title: str | None = None
    dueDate: str | None = None
    status: str | None = None
    priority: str | None = None
    notificationLeadDays: int | None = None


def _enum(enum_type, raw: str | None, label: str):
    """Exact (case-sensitive, untrimmed) enum lookup; returns (value, error_response)."""
    if raw is None:
        return None, None
    try:
        return enum_type(raw), None
    except ValueError:
        return None, validation(f"Unknown Deadline {label}: {raw}")


@router.get("/matters/{matter_id}/deadlines")
def list_deadlines(matter_id: uuid.UUID, request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    if container.matter_service.get(lawyer.firm_id, str(matter_id)) is None:
        return not_found("Matter not found")
    return {"deadlines": [deadline_json(d) for d in container.deadline_service.list(lawyer.firm_id, str(matter_id))]}


@router.post("/matters/{matter_id}/deadlines", dependencies=[Depends(require_json)])
def create_deadline(matter_id: uuid.UUID, body: CreateDeadlineRequest, request: Request):
    due_date = parse_date(body.dueDate, blank_is_none=False)
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    if container.matter_service.get(lawyer.firm_id, str(matter_id)) is None:
        return not_found("Matter not found")

    priority, error = _enum(DeadlinePriority, body.priority, "priority")
    if error:
        return error

    try:
        created = container.deadline_service.create(str(matter_id), body.title, due_date, priority, body.notificationLeadDays)
    except InvalidDeadlineError as e:
        return validation(str(e))
    return JSONResponse(status_code=201, content=deadline_json(created))


@router.get("/deadlines/upcoming")
def upcoming_deadlines(request: Request, days: int = 7):
    """Declared above /deadlines/{id}, or "upcoming" would be parsed as a Deadline UUID."""
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    return {"deadlines": [deadline_json(d) for d in container.deadline_service.upcoming(lawyer.firm_id, days)]}


@router.get("/deadlines/{deadline_id}")
def get_deadline(deadline_id: uuid.UUID, request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    deadline = container.deadline_service.get(lawyer.firm_id, str(deadline_id))
    return deadline_json(deadline) if deadline else not_found("Deadline not found")


@router.patch("/deadlines/{deadline_id}", dependencies=[Depends(require_json)])
def update_deadline(deadline_id: uuid.UUID, body: UpdateDeadlineRequest, request: Request):
    due_date = parse_date(body.dueDate, blank_is_none=False)
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()

    status, error = _enum(DeadlineStatus, body.status, "status")
    if error:
        return error
    priority, error = _enum(DeadlinePriority, body.priority, "priority")
    if error:
        return error

    try:
        updated = container.deadline_service.update(lawyer.firm_id, str(deadline_id), body.title, due_date, status, priority, body.notificationLeadDays)
    except InvalidDeadlineError as e:
        return validation(str(e))
    return deadline_json(updated) if updated else not_found("Deadline not found")


# ---------------------------------------------------------------- notifications


@router.get("/notifications")
def list_notifications(request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    return {"notifications": [notification_json(n) for n in container.notification_service.list(lawyer.id)]}


@router.patch("/notifications/read-all")
def mark_all_notifications_read(request: Request):
    """I-44."""
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    return {"markedCount": container.notification_service.mark_all_read(lawyer.id)}


@router.patch("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: uuid.UUID, request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    notification = container.notification_service.mark_read(lawyer.id, str(notification_id))
    return notification_json(notification) if notification else not_found("Notification not found")
