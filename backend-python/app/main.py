import logging
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.infrastructure.config import EXPOSE_INTERNAL_AI_ROUTES, FRONTEND_ORIGIN
from app.web.api import container
from app.web.api.auth_routes import router as auth_router
from app.web.api.chat_search_routes import router as chat_search_router
from app.web.api.client_matter_routes import router as client_matter_router
from app.web.api.common import BadRequestParam, UnsupportedMediaType, framework_error
from app.web.api.deadline_notification_routes import router as deadline_notification_router
from app.web.api.document_routes import router as document_router
from app.web.chat_router import router as chat_router
from app.web.ingest_router import router as ingest_router

# The whole backend in one process (formerly Java for auth/CRUD + Python for
# AI): the public /api/* surface the frontend calls, plus Document Ingestion
# (SD-004) and AI Chat (SD-005), which /api reaches in-process
# (app/infrastructure/ai_bridges.py) instead of over HTTP.

logging.basicConfig(level=logging.INFO)

ALLOWED_METHODS = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    container.notification_scheduler.start()  # SD-006: hourly Deadline reminder scan
    yield
    container.notification_scheduler.stop()


app = FastAPI(title="Legal AI Assistant - Backend", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(client_matter_router)
app.include_router(deadline_notification_router)
app.include_router(document_router)
app.include_router(chat_search_router)

if EXPOSE_INTERNAL_AI_ROUTES:
    # Unauthenticated by design (they trusted their only caller, the old Java
    # backend) — debugging aid only, off unless explicitly enabled.
    app.include_router(ingest_router)
    app.include_router(chat_router)


# ---------------------------------------------------------------- CORS
# The browser calls /api cross-origin (frontend :3000 -> backend), so CORS is
# enforced; credentials must be allowed for the session cookie (System
# Architecture §5). Like the Spring config this replaces, a cross-origin
# /api request from any other origin is refused outright (403) rather than
# merely left without CORS headers.

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=ALLOWED_METHODS,
    allow_headers=["*"],
    allow_credentials=True,
)


@app.middleware("http")
async def reject_foreign_origins(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin and request.url.path.startswith("/api/") and origin != FRONTEND_ORIGIN:
        own = urlsplit(str(request.base_url))
        if origin.rstrip("/") != f"{own.scheme}://{own.netloc}":
            return PlainTextResponse("Invalid CORS request", status_code=403)
    return await call_next(request)


# ---------------------------------------------------------------- errors
# /api keeps the Spring-shaped bodies the frontend was built against; the
# internal AI routes keep FastAPI's defaults, exactly as before.


def _is_api(request: Request) -> bool:
    return request.url.path.startswith("/api")


@app.exception_handler(RequestValidationError)
async def on_validation_error(request: Request, exc: RequestValidationError):
    if _is_api(request):
        return framework_error(400, request.url.path)
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(BadRequestParam)
async def on_bad_request_param(request: Request, _: BadRequestParam):
    return framework_error(400, request.url.path)


@app.exception_handler(UnsupportedMediaType)
async def on_unsupported_media_type(request: Request, _: UnsupportedMediaType):
    return framework_error(415, request.url.path)


@app.exception_handler(StarletteHTTPException)
async def on_http_exception(request: Request, exc: StarletteHTTPException):
    if _is_api(request):
        return framework_error(exc.status_code, request.url.path)
    return await http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def on_unhandled(request: Request, exc: Exception):
    logging.getLogger("app").error("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return framework_error(500, request.url.path)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
