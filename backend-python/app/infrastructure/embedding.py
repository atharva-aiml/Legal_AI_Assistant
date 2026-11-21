import logging
import threading

from fastembed import TextEmbedding
from tokenizers import Tokenizer

from app.infrastructure.config import EMBEDDING_CACHE_DIR, EMBEDDING_MODEL_NAME

log = logging.getLogger(__name__)

# The model's real max_seq_length (sentence-transformers' own
# sentence_bert_config.json for all-MiniLM-L6-v2). Every vector already in
# document_chunks was produced under this limit, so the ONNX runtime must
# truncate at exactly the same point — enforced in _get_model(), not trusted
# to fastembed's default.
MAX_SEQ_LENGTH = 256

# sentence-transformers' default. fastembed's own default (256) ran ONNX
# Runtime out of memory ("bad allocation") on this 7.3 GB machine during the
# 2026-11-21 spike — never leave it to the library default.
BATCH_SIZE = 32

_model: TextEmbedding | None = None
_counting_tokenizer: Tokenizer | None = None
_lock = threading.Lock()


def _fastembed_name(name: str) -> str:
    # The setting predates fastembed and uses sentence-transformers' short
    # name ("all-MiniLM-L6-v2"); fastembed wants the hub id.
    return name if "/" in name else f"sentence-transformers/{name}"


def _get_model() -> TextEmbedding:
    global _model, _counting_tokenizer
    if _model is None:
        with _lock:  # ingestion threads and chat requests can race the first load
            if _model is None:
                model = TextEmbedding(_fastembed_name(EMBEDDING_MODEL_NAME), cache_dir=EMBEDDING_CACHE_DIR)
                tokenizer = model.model.tokenizer
                tokenizer.enable_truncation(max_length=MAX_SEQ_LENGTH)
                # A separate, non-truncating copy just for counting tokens in
                # the truncation warning — the shared one truncates by design,
                # so it can't report how much would be lost.
                counting = Tokenizer.from_str(tokenizer.to_str())
                counting.no_truncation()
                counting.no_padding()
                _counting_tokenizer = counting
                _model = model
    return _model


def count_tokens(text: str) -> int:
    """The real token count the model sees before truncation (incl. [CLS]/[SEP])."""
    _get_model()
    assert _counting_tokenizer is not None
    return len(_counting_tokenizer.encode(text, add_special_tokens=True).ids)


class OnnxEmbedder:
    """System Architecture §6: all-MiniLM-L6-v2, 384 dimensions, runs
    fully locally (no API key, no per-call cost) — via ONNX Runtime
    (fastembed) rather than PyTorch since 2026-11-21. Same model, same
    weights: the spike reproduced the vectors already stored in
    document_chunks at cosine 1.000000, so no re-ingestion was needed
    (Technology Decision Log).

    Real bug found by spike (2026-08-19): the model silently truncates any
    text longer than MAX_SEQ_LENGTH tokens with no error and no log line —
    the chunker's char-based size approximation was wrong and most chunks
    were losing their back half to this, invisibly (see app/domain/chunk.py's
    CHUNK_SIZE_CHARS comment for the fix). The chunker is now sized to make
    this rare, but this check is the safety net for whatever still slips
    through — a silent truncation must never be silent twice.
    """

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._warn_if_any_would_truncate(texts)
        vectors = _get_model().embed(texts, batch_size=BATCH_SIZE)
        return [v.tolist() for v in vectors]

    @staticmethod
    def _warn_if_any_would_truncate(texts: list[str]) -> None:
        for text in texts:
            token_count = count_tokens(text)
            if token_count > MAX_SEQ_LENGTH:
                log.warning(
                    "Embedding input has %d tokens, exceeding %s's %d-token limit — "
                    "the back %d tokens will be silently truncated by the model. "
                    "Text preview: %r",
                    token_count, EMBEDDING_MODEL_NAME, MAX_SEQ_LENGTH, token_count - MAX_SEQ_LENGTH, text[:120],
                )
