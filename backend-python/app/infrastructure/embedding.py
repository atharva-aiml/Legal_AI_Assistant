import logging

from sentence_transformers import SentenceTransformer

from app.infrastructure.config import EMBEDDING_MODEL_NAME

_model: SentenceTransformer | None = None

log = logging.getLogger(__name__)


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


class SentenceTransformerEmbedder:
    """System Architecture §6: all-MiniLM-L6-v2, 384 dimensions, runs
    fully locally (no API key, no per-call cost).

    Real bug found by spike (2026-08-19): `model.encode()` silently
    truncates any text longer than `model.max_seq_length` (256 tokens for
    this model) with no error and no log line — the chunker's char-based
    size approximation was wrong and most chunks were losing their back
    half to this, invisibly (see app/domain/chunk.py's CHUNK_SIZE_CHARS
    comment for the fix). The chunker is now sized to make this rare, but
    this check is the safety net for whatever still slips through — a
    silent truncation must never be silent twice.
    """

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._warn_if_any_would_truncate(texts)
        vectors = _get_model().encode(texts)
        return [v.tolist() for v in vectors]

    @staticmethod
    def _warn_if_any_would_truncate(texts: list[str]) -> None:
        model = _get_model()
        limit = model.max_seq_length
        tokenizer = model.tokenizer
        for text in texts:
            token_count = len(tokenizer.encode(text, add_special_tokens=True))
            if token_count > limit:
                log.warning(
                    "Embedding input has %d tokens, exceeding %s's %d-token limit — "
                    "the back %d tokens will be silently truncated by model.encode(). "
                    "Text preview: %r",
                    token_count, EMBEDDING_MODEL_NAME, limit, token_count - limit, text[:120],
                )
