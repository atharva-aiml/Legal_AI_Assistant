import os
import uuid

from app.infrastructure.config import STORAGE_DIR


class LocalFilesystemStorage:
    """Dev/local-only StorageService (SD-008, System Architecture §6) — no
    Cloudflare R2 credentials in this environment. Writes to the same
    repo-root uploads/ directory LocalFileStorage (ingestion's reader) reads
    from, under the same key scheme the Java backend used (random UUID +
    original extension), so every already-uploaded file keeps resolving."""

    def __init__(self, root: str = STORAGE_DIR) -> None:
        self.root = os.path.abspath(root)
        os.makedirs(self.root, exist_ok=True)

    def store(self, original_file_name: str | None, content: bytes) -> str:
        key = f"{uuid.uuid4()}{_extension_of(original_file_name)}"
        with open(os.path.join(self.root, key), "wb") as f:
            f.write(content)
        return key

    def retrieve(self, storage_key: str) -> bytes:
        with open(os.path.join(self.root, storage_key), "rb") as f:
            return f.read()

    def delete(self, storage_key: str) -> None:
        try:
            os.remove(os.path.join(self.root, storage_key))
        except FileNotFoundError:
            pass  # REQ-027: deletion is idempotent


def _extension_of(file_name: str | None) -> str:
    """Everything from the last '.', e.g. ".pdf" — or "" when there's no dot."""
    if not file_name:
        return ""
    dot = file_name.rfind(".")
    return file_name[dot:] if dot >= 0 else ""
