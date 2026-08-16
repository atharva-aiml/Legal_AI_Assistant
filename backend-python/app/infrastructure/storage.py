import os

from app.infrastructure.config import STORAGE_DIR


class LocalFileStorage:
    """Reads from the same local directory backend-java's
    LocalFilesystemStorageService writes to (System Architecture §6) —
    both dev-only stand-ins for Cloudflare R2, which both services would
    read/write directly in production (no R2 credentials available here)."""

    def read(self, storage_key: str) -> bytes:
        path = os.path.join(STORAGE_DIR, storage_key)
        with open(path, "rb") as f:
            return f.read()
