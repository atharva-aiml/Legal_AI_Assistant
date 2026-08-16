from app.application.ingestion_service import IngestionService
from app.domain.chunk import CHUNK_SIZE_CHARS, ExtractedPage


class InMemoryStorage:
    def __init__(self, files: dict[str, bytes]):
        self.files = files

    def read(self, storage_key: str) -> bytes:
        return self.files[storage_key]


class FakeExtractor:
    def __init__(self, pages: list[ExtractedPage] | None = None, text: str = "", raise_error: bool = False):
        self.pages = pages if pages is not None else [ExtractedPage(page_number=1, text=text)]
        self.raise_error = raise_error

    def extract(self, file_bytes: bytes, mime_type: str) -> list[ExtractedPage]:
        if self.raise_error:
            raise ValueError("corrupt file")
        return self.pages


class FakeEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


class InMemoryRepository:
    def __init__(self):
        self.saved_chunks: list[tuple[str, str, list[float], int | None]] = []  # (document_id, content, embedding, page_number)
        self.status: dict[str, str] = {}
        self.error_messages: dict[str, str] = {}

    def save_chunks(self, document_id, chunks):
        self.saved_chunks.extend((document_id, content, emb, page_number) for content, emb, page_number in chunks)

    def mark_ready(self, document_id):
        self.status[document_id] = "ready"

    def mark_failed(self, document_id, error_message):
        self.status[document_id] = "failed"
        self.error_messages[document_id] = error_message


def make_service(text="Some legal text here.", pages=None, raise_error=False, storage_files=None):
    # NB: use `is None`, not truthy `or` — an empty dict {} is falsy in
    # Python and would silently fall back to the default, defeating the
    # storage-failure test below.
    storage = InMemoryStorage(storage_files if storage_files is not None else {"key1": b"fake bytes"})
    extractor = FakeExtractor(pages=pages, text=text, raise_error=raise_error)
    embedder = FakeEmbedder()
    repository = InMemoryRepository()
    return IngestionService(storage, extractor, embedder, repository), repository


def test_ingest_extracts_chunks_embeds_and_marks_ready():
    service, repo = make_service(text="A short lease clause about rent.")
    service.ingest("doc-1", "key1", "application/pdf")

    assert repo.status["doc-1"] == "ready"
    assert len(repo.saved_chunks) == 1
    _, content, embedding, page_number = repo.saved_chunks[0]
    assert content == "A short lease clause about rent."
    assert page_number == 1
    assert len(embedding) == 3


def test_ingest_marks_failed_when_extraction_throws():
    service, repo = make_service(raise_error=True)
    service.ingest("doc-2", "key1", "application/pdf")

    assert repo.status["doc-2"] == "failed"
    assert "corrupt file" in repo.error_messages["doc-2"]
    assert repo.saved_chunks == []


def test_ingest_marks_failed_when_no_text_extracted():
    service, repo = make_service(text="   ")
    service.ingest("doc-3", "key1", "application/pdf")

    assert repo.status["doc-3"] == "failed"
    assert repo.saved_chunks == []


def test_ingest_produces_multiple_chunks_for_long_text():
    long_text = "Legal text. " * (CHUNK_SIZE_CHARS // 10)
    service, repo = make_service(text=long_text)
    service.ingest("doc-4", "key1", "application/pdf")

    assert repo.status["doc-4"] == "ready"
    assert len(repo.saved_chunks) > 1


def test_ingest_marks_failed_when_storage_read_fails():
    service, repo = make_service(storage_files={})  # key1 not present -> KeyError
    service.ingest("doc-5", "key1", "application/pdf")

    assert repo.status["doc-5"] == "failed"


def test_ingest_tags_every_chunk_with_its_real_source_page_not_a_chunk_index():
    # The exact bug reported: page_number ended up meaning "chunk index"
    # rather than a real page — this proves the real page number now flows
    # end to end through the application layer, not just chunk_pages() alone.
    pages = [
        ExtractedPage(page_number=1, text="Page one content about the lease term."),
        ExtractedPage(page_number=2, text="Page two content about the rent clause."),
    ]
    service, repo = make_service(pages=pages)
    service.ingest("doc-6", "key1", "application/pdf")

    assert repo.status["doc-6"] == "ready"
    page_numbers = {page_number for _, _, _, page_number in repo.saved_chunks}
    assert page_numbers == {1, 2}


def test_ingest_preserves_docx_pages_null_page_number():
    pages = [ExtractedPage(page_number=None, text="Some DOCX content with no real page concept.")]
    service, repo = make_service(pages=pages)
    service.ingest("doc-7", "key1", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    assert repo.status["doc-7"] == "ready"
    assert repo.saved_chunks[0][3] is None
