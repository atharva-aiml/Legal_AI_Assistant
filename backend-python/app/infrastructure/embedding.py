from sentence_transformers import SentenceTransformer

from app.infrastructure.config import EMBEDDING_MODEL_NAME

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


class SentenceTransformerEmbedder:
    """System Architecture §6: all-MiniLM-L6-v2, 384 dimensions, runs
    fully locally (no API key, no per-call cost)."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = _get_model().encode(texts)
        return [v.tolist() for v in vectors]
