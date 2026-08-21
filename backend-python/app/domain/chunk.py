import re
from dataclasses import dataclass, field
from typing import Literal

from app.domain.sentence_split import split_into_sentences

# Real bug, found by spike (2026-08-19): the ~4-chars/token approximation
# below was wrong for this corpus. all-MiniLM-L6-v2's REAL max_seq_length is
# 256 tokens (verified against the loaded model, not assumed), but this
# project's actual legal-text fixtures tokenize at ~5-5.1 chars/token, not 4
# — number/citation/punctuation-heavy legal text is less token-efficient
# than plain prose. At the old CHUNK_SIZE_CHARS=2800, real measured chunks
# ran 265-560 tokens: MOST chunks (45-100% depending on format) silently
# exceeded the model's limit and had their back half truncated by
# `model.encode()` with no error, no log line — silently unfindable by
# vector search. Re-picked by sweeping candidate sizes against every real
# test fixture (10/30/60-page, DOCX+PDF) with the real tokenizer: 1000 chars
# keeps every real chunk's actual token count at 216 max (256 limit, ~15%
# safety margin) — see AI Architecture §2's addendum for the full sweep.
# Overlap kept at the same ~14% ratio as before.
CHUNK_SIZE_CHARS = 1000
CHUNK_OVERLAP_CHARS = 150

# DOCX-adaptive chunking (2026-08-19 spike): table/list segments (key:value
# pairs, IDs, punctuation) measure less token-dense than prose — a table
# chunk hit 264 real tokens at 994 chars, over the 256 limit, even at the
# corrected CHUNK_SIZE_CHARS above. Same packer, tighter budget for this one
# segment type — verified 0 over-limit across every real table-bearing DOCX
# fixture tested (see AI Architecture §2's addendum).
TABLE_CHUNK_SIZE_CHARS = 850

ChunkType = Literal["prose", "table_or_list", "image"]

# pypdf/python-docx text has no reliable blank-line paragraph markers (a real
# extraction check against this project's own test PDFs showed every
# visually-wrapped line separated by a single "\n", paragraph or not) — this
# still catches paragraph breaks on the inputs that DO have them (DOCX
# double-newlines), and degrades gracefully to one "paragraph" per page when
# they're absent, letting sentence splitting below do the real work.
PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")


@dataclass(frozen=True)
class Segment:
    """One pre-split unit of structured content (a sentence, a table row, an
    OCR'd image caption) tagged with the heading path active when it
    occurred. Produced by adaptive extraction (currently DOCX only —
    extraction.py branches on mime type, which is the right layer for that;
    this module only branches on whether `segments` is populated, per
    CLAUDE.md's domain-purity rule)."""

    text: str
    heading_path: tuple[str, ...] = ()
    chunk_type: ChunkType = "prose"
    # The Nth table, or the Nth image, encountered in the document so far —
    # meaning depends on chunk_type (a table's rows all share one number;
    # each image gets its own); always None for prose, where "the Nth
    # paragraph" isn't something a user names the way "Table 3" is.
    element_number: int | None = None
    # 2026-08-20: real page number, derived from explicit page-break markers
    # in the DOCX (`<w:br w:type="page"/>`) when the document has at least
    # one — None when it has none at all (honest "not determinable", same
    # convention as ExtractedPage.page_number; DOCX's *natural*, text-
    # overflow page breaks are never stored in the file regardless).
    page_number: int | None = None


@dataclass(frozen=True)
class ExtractedPage:
    """One page's raw text plus its real page number — `None` for formats
    with no page concept (DOCX: pages are a Word-render-time notion, not
    present in the file itself; see CLAUDE.md §4).

    `segments`, when populated, opts a page into the adaptive packer instead
    of the plain text/sentence-splitting path below — the SHAPE of the data
    decides, not the source file type."""

    page_number: int | None
    text: str
    segments: list[Segment] | None = None


@dataclass(frozen=True)
class ChunkMetadata:
    section: str | None = None
    chunk_type: ChunkType = "prose"
    element_number: int | None = None


@dataclass(frozen=True)
class TextChunk:
    content: str
    index: int
    page_number: int | None
    metadata: ChunkMetadata = field(default_factory=ChunkMetadata)


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


def _hard_split(segment: str, size_budget: int = CHUNK_SIZE_CHARS) -> list[str]:
    """Last resort for a single segment longer than one whole chunk (a long
    run-on table row with no sentence punctuation is the realistic case) —
    splits at word boundaries, never mid-word."""
    words = segment.split(" ")
    pieces: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        if current and current_len + len(word) + 1 > size_budget:
            pieces.append(" ".join(current))
            current, current_len = [], 0
        current.append(word)
        current_len += len(word) + 1
    if current:
        pieces.append(" ".join(current))
    return pieces


def _size_budget_for(chunk_type: ChunkType) -> int:
    return TABLE_CHUNK_SIZE_CHARS if chunk_type == "table_or_list" else CHUNK_SIZE_CHARS


def _pack_typed_segments(segments: list[Segment], start_index: int) -> tuple[list[TextChunk], int]:
    """The adaptive counterpart to `_pack_segments` above — same greedy-pack-
    with-sentence-boundary-overlap algorithm, extended to (a) never merge
    across a heading, content-type, element-identity, or page change (all
    four are hard chunk boundaries — "a chunk never spans two real pages"
    applies here exactly as it does to the plain PDF path once a page
    number is actually known; two different tables back to back under the
    same heading must never blend into one "Table 3" chunk), and (b) use a
    type-appropriate size budget. `section` is the deepest active heading;
    `page_number` is real when the source DOCX has explicit page-break
    markers, `None` otherwise (see `Segment.page_number`)."""
    chunks: list[TextChunk] = []
    index = start_index

    groups: list[list[Segment]] = []
    for seg in segments:
        if (
            groups
            and groups[-1][-1].heading_path == seg.heading_path
            and groups[-1][-1].chunk_type == seg.chunk_type
            and groups[-1][-1].element_number == seg.element_number
            and groups[-1][-1].page_number == seg.page_number
        ):
            groups[-1].append(seg)
        else:
            groups.append([seg])

    for group in groups:
        size_budget = _size_budget_for(group[0].chunk_type)
        expanded: list[Segment] = []
        for seg in group:
            if len(seg.text) <= size_budget:
                expanded.append(seg)
            else:
                expanded.extend(
                    Segment(
                        text=piece,
                        heading_path=seg.heading_path,
                        chunk_type=seg.chunk_type,
                        element_number=seg.element_number,
                        page_number=seg.page_number,
                    )
                    for piece in _hard_split(seg.text, size_budget)
                )

        start = 0
        n = len(expanded)
        while start < n:
            length, end = 0, start
            while end < n and (length == 0 or length + len(expanded[end].text) + 1 <= size_budget):
                length += len(expanded[end].text) + 1
                end += 1
            content = " ".join(s.text for s in expanded[start:end])
            heading_path = expanded[start].heading_path
            metadata = ChunkMetadata(
                # 2026-08-20 fix: the full ancestor chain, not just the
                # deepest heading. A document with real nested headings
                # (e.g. "53. Access to Justice" > "Mass claims and
                # vulnerable populations") has a lawyer-meaningful TOP-level
                # section that keeping only the leaf silently discarded —
                # confirmed as the root cause of "page 54"/"section 53"
                # questions never surfacing the real top-level section. A
                # single-heading path is unaffected: `" > ".join((x,)) == x`.
                section=" > ".join(heading_path) if heading_path else None,
                chunk_type=expanded[start].chunk_type,
                element_number=expanded[start].element_number,
            )
            chunks.append(TextChunk(content=content, index=index, page_number=expanded[start].page_number, metadata=metadata))
            index += 1

            if end >= n:
                break
            overlap_len, back = 0, end
            while back > start and overlap_len + len(expanded[back - 1].text) + 1 <= CHUNK_OVERLAP_CHARS:
                back -= 1
                overlap_len += len(expanded[back].text) + 1
            start = back if back > start else end

    return chunks, index


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
    `text[start:end]` slice that regularly cut mid-word — see Build Plan).

    A page with `segments` populated (adaptive extraction — DOCX) routes to
    the heading/type-aware packer instead of the plain text path; this is a
    branch on data shape, not on page/file type, per CLAUDE.md's domain-
    purity rule — extraction.py decides what shape a page arrives in."""
    chunks: list[TextChunk] = []
    index = 0
    for page in pages:
        if page.segments is not None:
            page_chunks, index = _pack_typed_segments(page.segments, index)
            chunks.extend(page_chunks)
        else:
            for content in _pack_segments(_segments_for(page.text)):
                chunks.append(TextChunk(content=content, index=index, page_number=page.page_number))
                index += 1
    return chunks
