import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.application.draft_generation_service import DraftGenerationFailedError
from app.domain.document import InvalidDocumentError
from app.domain.template import InvalidTemplateError
from app.infrastructure.config import MAX_UPLOAD_BYTES
from app.web.api import container
from app.web.api.common import (
    api_error,
    content_disposition,
    document_json,
    framework_error,
    not_found,
    require_json,
    resolve_lawyer,
    template_json,
    unauthenticated,
    validation,
)

router = APIRouter(prefix="/api")


class GenerateDraftRequest(BaseModel):
    """{ template_id, fields } per System Architecture §4's declared request body."""

    template_id: str | None = None
    fields: dict[str, Any] | None = None


@router.get("/matters/{matter_id}/documents")
def list_documents(matter_id: uuid.UUID, request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    if container.matter_service.get(lawyer.firm_id, str(matter_id)) is None:
        return not_found("Matter not found")
    return {"documents": [document_json(d) for d in container.document_service.list(lawyer.firm_id, str(matter_id))]}


@router.post("/matters/{matter_id}/documents")
def upload_document(matter_id: uuid.UUID, request: Request, file: UploadFile = File(...)):
    if file.size is not None and file.size > MAX_UPLOAD_BYTES:
        return framework_error(413, request.url.path)

    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    if container.matter_service.get(lawyer.firm_id, str(matter_id)) is None:
        return not_found("Matter not found")

    try:
        content = file.file.read()
    except OSError:
        return api_error(400, "UPLOAD_FAILED", "Couldn't read the uploaded file.")

    try:
        created = container.document_service.upload(str(matter_id), lawyer.id, file.filename, file.content_type, content)
    except InvalidDocumentError as e:
        return validation(str(e))
    return JSONResponse(status_code=201, content={"documents": [document_json(created)]})


@router.post("/matters/{matter_id}/documents/generate", dependencies=[Depends(require_json)])
def generate_draft(matter_id: uuid.UUID, body: GenerateDraftRequest, request: Request):
    """SD-007 / REQ-015: 201/400/404/502 per System Architecture §4."""
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    if container.matter_service.get(lawyer.firm_id, str(matter_id)) is None:
        return not_found("Matter not found")

    try:
        template_id = str(uuid.UUID(body.template_id))
    except (TypeError, ValueError):
        return validation("A template must be selected.")

    fields = None if body.fields is None else {k: (None if v is None else str(v)) for k, v in body.fields.items()}
    try:
        created = container.draft_generation_service.generate(lawyer.firm_id, str(matter_id), lawyer.id, template_id, fields)
    except InvalidTemplateError as e:
        return validation(str(e))
    except DraftGenerationFailedError:
        return api_error(502, "GENERATION_FAILED", "Couldn't generate document — retry.")
    return JSONResponse(status_code=201, content=document_json(created))


@router.get("/documents/{document_id}")
def get_document(document_id: uuid.UUID, request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    document = container.document_service.get(lawyer.firm_id, str(document_id))
    return document_json(document) if document else not_found("Document not found")


@router.get("/documents/{document_id}/download")
def download_document(document_id: uuid.UUID, request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    document = container.document_service.get(lawyer.firm_id, str(document_id))
    if document is None:
        return not_found("Document not found")
    content = container.document_service.download(lawyer.firm_id, str(document_id))
    if content is None:
        return not_found("Document not found")
    return Response(
        content=content,
        headers={"content-type": document.mime_type, "content-disposition": content_disposition(document.file_name)},
    )


@router.delete("/documents/{document_id}")
def delete_document(document_id: uuid.UUID, request: Request):
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    if not container.document_service.delete(lawyer.firm_id, str(document_id)):
        return not_found("Document not found")
    return Response(status_code=204)


@router.get("/templates")
def list_templates(request: Request):
    """SD-007 / REQ-015: system Templates plus this Firm's own."""
    lawyer = resolve_lawyer(request)
    if lawyer is None:
        return unauthenticated()
    return {"templates": [template_json(t) for t in container.template_service.list(lawyer.firm_id)]}
