import io

import easyocr
from docx import Document as DocxDocument
from pypdf import PdfReader

from app.domain.chunk import ExtractedPage

_ocr_reader: easyocr.Reader | None = None


def _get_ocr_reader() -> easyocr.Reader:
    # Loaded lazily and cached — the ~30s model init (spiked in Technology
    # Decision Log) only happens once per process, not per request.
    global _ocr_reader
    if _ocr_reader is None:
        _ocr_reader = easyocr.Reader(["en"], gpu=False)
    return _ocr_reader


class DocumentTextExtractor:
    """REQ-003/REQ-004: extracts native text from PDF/DOCX, OCRs image
    files. Scope boundary: a *scanned* PDF (an image embedded in a PDF
    wrapper, with no text layer) is not yet handled — pypdf returns no
    text for it, which the ingestion service correctly surfaces as a
    'failed' Document rather than silently producing nothing. Only plain
    image uploads (REQ-003's "scanned images") go through OCR in V0.3."""

    def extract(self, file_bytes: bytes, mime_type: str) -> list[ExtractedPage]:
        if mime_type == "application/pdf":
            return self._extract_pdf(file_bytes)
        if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return self._extract_docx(file_bytes)
        if mime_type.startswith("image/"):
            return self._extract_image(file_bytes)
        if mime_type == "text/plain":
            return self._extract_text(file_bytes)
        raise ValueError(f"Unsupported mime type for extraction: {mime_type}")

    @staticmethod
    def _extract_pdf(file_bytes: bytes) -> list[ExtractedPage]:
        # Real page boundaries, 1-indexed — previously joined into one blob
        # before chunking, which is why a chunk could span several real
        # pages and "page_number" ended up meaning "chunk index" instead.
        reader = PdfReader(io.BytesIO(file_bytes))
        return [ExtractedPage(page_number=i, text=page.extract_text() or "") for i, page in enumerate(reader.pages, start=1)]

    @staticmethod
    def _extract_docx(file_bytes: bytes) -> list[ExtractedPage]:
        # DOCX has no page concept in the file itself — pages only exist at
        # Word's render time. Treated as one page with page_number=None
        # (honest "not determinable") rather than fabricating "page 1".
        doc = DocxDocument(io.BytesIO(file_bytes))
        return [ExtractedPage(page_number=None, text="\n".join(p.text for p in doc.paragraphs))]

    @staticmethod
    def _extract_image(file_bytes: bytes) -> list[ExtractedPage]:
        reader = _get_ocr_reader()
        results = reader.readtext(file_bytes, detail=0)
        return [ExtractedPage(page_number=1, text=" ".join(results))]

    @staticmethod
    def _extract_text(file_bytes: bytes) -> list[ExtractedPage]:
        # SD-007: a generated draft (Build Plan V0.8) is rendered as plain
        # UTF-8 text, not a real PDF/DOCX — same "no page concept" honesty
        # as DOCX above, since a generated draft has no page boundaries
        # either.
        return [ExtractedPage(page_number=None, text=file_bytes.decode("utf-8"))]
