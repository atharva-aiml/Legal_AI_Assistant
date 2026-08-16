import re
from dataclasses import dataclass

from app.domain.sentence_split import split_into_sentences

# AI Architecture §2: "~700 tokens per chunk, ~100-token overlap." Approximated
# here in characters (~4 chars/token) since precise token-counting needs a
# tokenizer this pipeline doesn't otherwise require.
CHUNK_SIZE_CHARS = 2800
CHUNK_OVERLAP_CHARS = 400

# pypdf/python-docx text has no reliable blank-line paragraph markers (a real
# extraction check against this project's own test PDFs showed every
# visually-wrapped line separated by a single "\n", paragraph or not) — this
# still catches paragraph breaks on the inputs that DO have them (DOCX
# double-newlines), and degrades gracefully to one "paragraph" per page when
# they're absent, letting sentence splitting below do the real work.
PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")


@dataclass(frozen=True)
class ExtractedPage:
    """One page's raw text plus its real page number — `None` for formats
    with no page concept (DOCX: pages are a Word-render-time notion, not
    present in the file itself; see CLAUDE.md §4)."""

    page_number: int | None
    text: str


@dataclass(frozen=True)
class TextChunk:
    content: str
    index: int
    page_number: int | None


def _segments_for(text: str) -> list[str]:
    """Splits one page's text into sentence-level segments, paragraph breaks
    first where they exist. Falls back to the whole paragraph as a single
    segment when it has no sentence-ending punctuation at all (e.g. a table
    of short cell values with no periods) — packed by size at the chunk
    level either way, never cut mid-word."""
    segments: list[str] = []
    for paragraph in PARAGRAPH_SPLIT_RE.split(text):
        collapsed = re.sub(r"\s*\n\s*", " ", paragraph.strip())
        if not collapsed:
            continue
        sentences = [s.strip() for s in split_into_sentences(collapsed) if s.strip()]
        segments.extend(sentences or [collapsed])
    return segments


def _hard_split(segment: str) -> list[str]:
    """Last resort for a single segment longer than one whole chunk (a long
    run-on table row with no sentence punctuation is the realistic case) —
    splits at word boundaries, never mid-word."""
    words = segment.split(" ")
    pieces: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        if current and current_len + len(word) + 1 > CHUNK_SIZE_CHARS:
            pieces.append(" ".join(current))
            current, current_len = [], 0
        current.append(word)
        current_len += len(word) + 1
    if current:
        pieces.append(" ".join(current))
    return pieces


def _pack_segments(segments: list[str]) -> list[str]:
    """Greedily packs segments into ~CHUNK_SIZE_CHARS chunks. Overlap is
    computed by walking back whole segments (not a raw character slice), so
    the next chunk always starts at a sentence boundary rather than
    mid-word."""
    if not segments:
        return []

    expanded: list[str] = []
    for segment in segments:
        if len(segment) <= CHUNK_SIZE_CHARS:
            expanded.append(segment)
        else:
            expanded.extend(_hard_split(segment))

    chunks: list[str] = []
    start = 0
    n = len(expanded)
    while start < n:
        length = 0
        end = start
        while end < n and (length == 0 or length + len(expanded[end]) + 1 <= CHUNK_SIZE_CHARS):
            length += len(expanded[end]) + 1
            end += 1
        chunks.append(" ".join(expanded[start:end]))

        if end >= n:
            break

        overlap_len = 0
        back = end
        while back > start and overlap_len + len(expanded[back - 1]) + 1 <= CHUNK_OVERLAP_CHARS:
            back -= 1
            overlap_len += len(expanded[back]) + 1
        start = back if back > start else end  # guarantee forward progress even with no usable overlap

    return chunks


def chunk_pages(pages: list[ExtractedPage]) -> list[TextChunk]:
    """Chunks each page independently — a chunk never spans two real pages
    (REQ-006's citations need a real, specific page), broken along sentence
    boundaries rather than a raw character offset (previously: a page-blind
    `text[start:end]` slice that regularly cut mid-word — see Build Plan)."""
    chunks: list[TextChunk] = []
    index = 0
    for page in pages:
        for content in _pack_segments(_segments_for(page.text)):
            chunks.append(TextChunk(content=content, index=index, page_number=page.page_number))
            index += 1
    return chunks
