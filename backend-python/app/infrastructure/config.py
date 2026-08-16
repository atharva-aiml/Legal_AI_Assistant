import os

from dotenv import load_dotenv

# Loads backend-python/.env (gitignored) into the process environment —
# needed for OPENAI_API_KEY specifically, since (unlike DATABASE_URL) a
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

# AI Architecture / System Architecture §6: LLM provider, resolved via a
# real spike in V0.4 (Technology Decision Log) — no hardcoded default,
# since a missing key must fail loudly rather than silently.
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_CHAT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")
