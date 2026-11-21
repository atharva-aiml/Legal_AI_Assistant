import os

from dotenv import load_dotenv

# Loads backend-python/.env (gitignored) into the process environment —
# needed for GOOGLE_API_KEY specifically, since (unlike DATABASE_URL) a
# secret must never ship a hardcoded default.
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://legal_ai:legal_ai_dev_password@localhost:5432/legal_ai_assistant",
)

# Shared with backend-java's LocalFilesystemStorageService — both point at
# the same repo-root directory (System Architecture §2's "shared database,
# two backend languages" note extends to shared local storage in dev).
STORAGE_DIR = os.environ.get("STORAGE_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads"))

EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
# Where fastembed keeps the ONNX model. Its own default is the OS temp dir,
# which disk cleanup can wipe (forcing a silent ~90 MB re-download on the next
# upload) — pinned to backend-python/.model-cache (gitignored) instead. A
# deploy image bakes the model in and points this at that path.
EMBEDDING_CACHE_DIR = os.environ.get(
    "EMBEDDING_CACHE_DIR", os.path.join(os.path.dirname(__file__), "..", "..", ".model-cache")
)

# AI Architecture / System Architecture §6: LLM provider. Was OpenAI
# gpt-4o-mini (V0.4); switched 2026-11-21 to Google Gemini's free tier via its
# OpenAI-compatible endpoint, after a real spike against real Matters
# (Technology Decision Log). No hardcoded key default — a missing key must
# fail loudly rather than silently.
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
# The free tier caps input tokens per minute PER MODEL (250K at spike time) —
# one full-context question on a large Matter is ~83K tokens. On a 429 the
# adapter moves on to the next model in this list, each with its own quota.
LLM_CHAT_MODELS = [
    m.strip()
    for m in os.environ.get("LLM_CHAT_MODELS", "gemini-3.5-flash-lite,gemini-3.1-flash-lite").split(",")
    if m.strip()
]

# --- Public API (auth + CRUD; formerly backend-java's application.properties) ---

# The browser calls this API cross-origin from the Next.js dev server, so CORS
# must name the exact origin (credentials can't be combined with "*").
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")

# Secure-flag on the session cookie — false only for local http:// dev.
SECURE_COOKIES = os.environ.get("SECURE_COOKIES", "false").strip().lower() == "true"

# Same 25 MB ceiling the Java backend's multipart config enforced.
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))

# The pre-merge internal routes (POST /ingest/{id}, /chat/{matter_id}...) carry
# no auth of their own — they used to sit behind the Java backend on a
# separate port. Now that this one process is browser-facing, they're only
# mounted when explicitly asked for (e.g. to re-trigger ingestion while
# debugging — see CLAUDE.md §4's duplicate-chunks gotcha first).
EXPOSE_INTERNAL_AI_ROUTES = os.environ.get("EXPOSE_INTERNAL_AI_ROUTES", "false").strip().lower() == "true"
