"""Shared web-layer helpers for the public /api routers: error shapes,
the session cookie, DTO serializers, and strict request-param parsing.

Response shapes are byte-compatible with what the Java backend returned (the
frontend was built against them): `{ error: { code, message } }` for every
handled error, Spring's `{ timestamp, status, error, path }` for framework-level
4xx/5xx (bad UUIDs, missing params, unknown routes), ISO-8601 instants with a
trailing `Z`, and Tomcat's Set-Cookie attribute order."""

import re
import uuid
from datetime import date, datetime, timezone
from email.utils import format_datetime
from http import HTTPStatus
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from app.application.activity_service import ActivityEntry
from app.application.auth_service import SESSION_COOKIE_NAME, SESSION_DURATION
from app.application.matter_chat_service import ChatHistoryDto, ChatMessageDto, PinToggleDto
from app.domain.client import Client
from app.domain.deadline import Deadline
from app.domain.document import Document
from app.domain.lawyer import Lawyer, LawyerPreferences
from app.domain.matter import Matter
from app.domain.notification import Notification
from app.domain.template import Template
from app.infrastructure.config import SECURE_COOKIES
from app.web.api import container

# ---------------------------------------------------------------- errors


def api_error(status: int, code: str, message: str) -> JSONResponse:
    """The `{ error: { code, message } }` shape (System Architecture §7)."""
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def unauthenticated() -> JSONResponse:
    return api_error(401, "UNAUTHENTICATED", "Not signed in")


def not_found(message: str) -> JSONResponse:
    return api_error(404, "NOT_FOUND", message)


def validation(message: str) -> JSONResponse:
    return api_error(400, "VALIDATION", message)


def framework_error(status: int, path: str) -> JSONResponse:
    """Spring Boot's default error body, which the Java backend returned for
    request-binding failures (malformed UUID/date/int, missing params/body),
    unknown routes, wrong methods and uncaught exceptions."""
    return JSONResponse(
        status_code=status,
        content={"timestamp": instant(datetime.now(timezone.utc)), "status": status, "error": HTTPStatus(status).phrase, "path": path},
    )


class BadRequestParam(Exception):
    """A query/path/body value that can't be bound to its type — rendered as a
    framework-level 400, the same as Spring's binding failure was."""


class UnsupportedMediaType(Exception):
    """A JSON-body endpoint called with a non-JSON Content-Type (Spring's 415)."""


def require_json(request: Request) -> None:
    """Dependency for every route that reads a JSON request body."""
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type != "application/json" and not content_type.endswith("+json"):
        raise UnsupportedMediaType()


# ---------------------------------------------------------------- auth


def resolve_lawyer(request: Request) -> Lawyer | None:
    """Call explicitly at the top of every handler that needs auth — this is
    the real authorization boundary (CLAUDE.md §4), not the frontend's
    middleware.ts cookie-presence check."""
    return container.auth_service.resolve_session(request.cookies.get(SESSION_COOKIE_NAME))


def set_session_cookie(response: Response, raw_token: str) -> None:
    expires = format_datetime(datetime.now(timezone.utc) + SESSION_DURATION, usegmt=True)
    max_age = int(SESSION_DURATION.total_seconds())
    secure = " Secure;" if SECURE_COOKIES else ""
    response.headers.append(
        "set-cookie", f"{SESSION_COOKIE_NAME}={raw_token}; Expires={expires}; Max-Age={max_age}; Path=/;{secure} HttpOnly; SameSite=Lax"
    )


def clear_session_cookie(response: Response) -> None:
    secure = " Secure;" if SECURE_COOKIES else ""
    response.headers.append("set-cookie", f"{SESSION_COOKIE_NAME}=; Expires=Thu, 01 Jan 1970 00:00:10 GMT; Path=/;{secure} HttpOnly")


# ---------------------------------------------------------------- parsing

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_date(value: str | None, *, blank_is_none: bool = True) -> date | None:
    """Strict yyyy-MM-dd (Java's ISO LocalDate format) — not Python's more
    permissive fromisoformat variants."""
    if value is None or (blank_is_none and not value.strip()):
        return None
    if not _ISO_DATE.match(value):
        raise BadRequestParam(value)
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise BadRequestParam(value) from None


def parse_uuid(value: str | None) -> str | None:
    """Optional UUID query param: blank -> None, malformed -> 400."""
    if value is None or not value.strip():
        return None
    try:
        return str(uuid.UUID(value.strip()))
    except ValueError:
        raise BadRequestParam(value) from None


def content_disposition(file_name: str) -> str:
    try:
        file_name.encode("latin-1")
        return f'attachment; filename="{file_name}"'
    except UnicodeEncodeError:
        # HTTP headers are latin-1; keep an ASCII fallback plus the exact
        # name via RFC 5987 so non-Latin file names still download correctly.
        fallback = file_name.encode("ascii", "replace").decode("ascii")
        return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(file_name)}"


# ---------------------------------------------------------------- serializers


def instant(value: datetime | None) -> str | None:
    """java.time.Instant's ISO-8601 form: UTC, 'Z', fraction in groups of 3."""
    if value is None:
        return None
    value = value.astimezone(timezone.utc)
    base = value.strftime("%Y-%m-%dT%H:%M:%S")
    micros = value.microsecond
    if micros == 0:
        return base + "Z"
    if micros % 1000 == 0:
        return f"{base}.{micros // 1000:03d}Z"
    return f"{base}.{micros:06d}Z"


def lawyer_json(lawyer: Lawyer) -> dict:
    """Never includes password_hash."""
    return {"id": lawyer.id, "name": lawyer.name, "email": lawyer.email, "role": lawyer.role.value}


def preferences_json(prefs: LawyerPreferences) -> dict:
    return {"deadlineRemindersEnabled": prefs.deadline_reminders_enabled}


def client_json(c: Client) -> dict:
    return {
        "id": c.id, "firmId": c.firm_id, "name": c.name, "contactEmail": c.contact_email, "contactPhone": c.contact_phone,
        "notes": c.notes, "createdAt": instant(c.created_at), "updatedAt": instant(c.updated_at),
    }


def matter_json(m: Matter) -> dict:
    return {
        "id": m.id, "firmId": m.firm_id, "clientId": m.client_id, "title": m.title, "status": m.status.value,
        "closedAt": instant(m.closed_at), "createdAt": instant(m.created_at), "updatedAt": instant(m.updated_at),
    }


def deadline_json(d: Deadline) -> dict:
    return {
        "id": d.id, "matterId": d.matter_id, "title": d.title, "dueDate": d.due_date.isoformat(), "status": d.status.value,
        "priority": d.priority.value, "notificationLeadDays": d.notification_lead_days,
        "createdAt": instant(d.created_at), "updatedAt": instant(d.updated_at),
    }


def document_json(d: Document) -> dict:
    return {
        "id": d.id, "matterId": d.matter_id, "fileName": d.file_name, "mimeType": d.mime_type, "sizeBytes": d.size_bytes,
        "status": d.status.value, "isDraft": d.is_draft, "errorMessage": d.error_message, "createdAt": instant(d.created_at),
    }


def notification_json(n: Notification) -> dict:
    return {
        "id": n.id, "lawyerId": n.lawyer_id, "deadlineId": n.deadline_id, "message": n.message,
        "sentAt": instant(n.sent_at), "readAt": instant(n.read_at), "createdAt": instant(n.created_at),
    }


def template_json(t: Template) -> dict:
    return {
        "id": t.id, "firmId": t.firm_id, "name": t.name, "description": t.description,
        "placeholders": sorted(t.placeholders()), "createdAt": instant(t.created_at),
    }


def activity_json(e: ActivityEntry) -> dict:
    return {"type": e.type, "title": e.title, "timestamp": instant(e.timestamp)}


def chat_message_json(m: ChatMessageDto) -> dict:
    return {
        "id": m.id, "matterId": m.matter_id, "lawyerId": m.lawyer_id, "role": m.role, "content": m.content,
        "createdAt": instant(m.created_at),
        "citations": [
            {"id": c.id, "documentId": c.document_id, "fileName": c.file_name, "pageNumber": c.page_number, "section": c.section, "excerpt": c.excerpt}
            for c in m.citations
        ],
        "lowConfidence": m.low_confidence, "fullContext": m.full_context, "pinned": m.pinned,
        "parentId": m.parent_id, "siblingIds": m.sibling_ids,
    }


def chat_history_json(h: ChatHistoryDto) -> dict:
    return {"messages": [chat_message_json(m) for m in h.messages]}


def pin_json(p: PinToggleDto) -> dict:
    return {"id": p.id, "pinned": p.pinned}
