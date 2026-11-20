from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.application.auth_service import (
    SESSION_COOKIE_NAME,
    EmailTakenError,
    IncorrectPasswordError,
    InvalidCredentialsError,
    ValidationError,
)
from app.domain.lawyer import InvalidLawyerError
from app.infrastructure.password_hasher import PasswordTooLongError
from app.web.api import container
from app.web.api.common import (
    api_error,
    clear_session_cookie,
    lawyer_json,
    preferences_json,
    require_json,
    resolve_lawyer,
    set_session_cookie,
    unauthenticated,
    validation,
)

router = APIRouter(prefix="/api")


class RegisterRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    password: str | None = None


class LoginRequest(BaseModel):
    email: str | None = None
    password: str | None = None


class UpdateNameRequest(BaseModel):
    name: str | None = None


class ChangePasswordRequest(BaseModel):
    currentPassword: str | None = None
    newPassword: str | None = None


class UpdatePreferencesRequest(BaseModel):
    deadlineRemindersEnabled: bool


@router.post("/auth/register", dependencies=[Depends(require_json)])
def register(body: RegisterRequest):
    try:
        result = container.auth_service.register(body.name, body.email, body.password)
    except (ValidationError, PasswordTooLongError) as e:
        return validation(str(e))
    except EmailTakenError as e:
        return api_error(409, "EMAIL_TAKEN", str(e))
    response = JSONResponse(status_code=201, content={"lawyer": lawyer_json(result.lawyer)})
    set_session_cookie(response, result.raw_session_token)
    return response


@router.post("/auth/login", dependencies=[Depends(require_json)])
def login(body: LoginRequest):
    try:
        result = container.auth_service.login(body.email, body.password)
    except InvalidCredentialsError as e:
        return api_error(401, "INVALID_CREDENTIALS", str(e))
    response = JSONResponse(content={"lawyer": lawyer_json(result.lawyer)})
    set_session_cookie(response, result.raw_session_token)
    return response


@router.get("/auth/email-available")
def email_available(email: str = Query(...)):
    """I-06: pre-auth, read-only — lets the register form hint at a taken email before submit."""
    return {"available": container.auth_service.is_email_available(email)}


@router.get("/auth/me")
def me(request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    return {"lawyer": lawyer_json(lawyer)}


@router.patch("/auth/me", dependencies=[Depends(require_json)])
def update_name(body: UpdateNameRequest, request: Request):
    """I-51: PATCH not POST — a partial update of the existing "current lawyer" resource."""
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    try:
        updated = container.auth_service.update_name(lawyer.id, body.name)
    except InvalidLawyerError as e:
        return validation(str(e))
    return {"lawyer": lawyer_json(updated)}


@router.post("/auth/change-password", dependencies=[Depends(require_json)])
def change_password(body: ChangePasswordRequest, request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    try:
        container.auth_service.change_password(lawyer.id, body.currentPassword, body.newPassword)
    except IncorrectPasswordError as e:
        return api_error(401, "INCORRECT_PASSWORD", str(e))
    except (InvalidLawyerError, PasswordTooLongError) as e:
        return validation(str(e))
    return {}


@router.get("/auth/me/preferences")
def get_preferences(request: Request):
    """I-52: SD-006 — which notification types this Lawyer wants to receive."""
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    return preferences_json(container.preferences_service.get(lawyer.id))


@router.patch("/auth/me/preferences", dependencies=[Depends(require_json)])
def update_preferences(body: UpdatePreferencesRequest, request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    return preferences_json(container.preferences_service.update(lawyer.id, body.deadlineRemindersEnabled))


@router.post("/auth/logout")
def logout(request: Request):
    container.auth_service.logout(request.cookies.get(SESSION_COOKIE_NAME))
    response = JSONResponse(content={})
    clear_session_cookie(response)
    return response


@router.get("/firm/lawyers")
def list_firm_lawyers(request: Request):
    """SCR-15: read-only Firm/team roster. Invite/remove is Build Plan V0.7, not built yet."""
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    return {"lawyers": [lawyer_json(l) for l in container.auth_service.list_firm_members(lawyer.firm_id)]}
