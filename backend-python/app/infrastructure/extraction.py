import hashlib
import io
import re

import threading

import docx
import pdfplumber
from docx.document import Document as DocxDocumentType
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from PIL import Image
from pypdf import PdfReader
from pypdf.generic import ContentStream, IndirectObject
from rapidocr import RapidOCR

from app.application.ports import ImageCaptioner
from app.domain.chunk import ExtractedPage, Segment, _segments_for

_ocr_engine: RapidOCR | None = None
_ocr_lock = threading.Lock()

# Color modes RapidOCR reads wrongly as raw arrays — it would treat CMYK's 4
# channels as RGBA and a palette image's indices as grayscale, returning
# EMPTY text with no error (both found in the 2026-11-21 spike; EasyOCR read
# them). Converted first; every other mode is passed through untouched,
# exactly as spiked.
_TO_RGB_MODES = frozenset({"CMYK", "YCbCr", "LAB", "HSV"})
_TO_RGBA_MODES = frozenset({"P", "PA"})  # RGBA keeps transparency; RapidOCR picks a contrasting background


def _get_ocr_engine() -> RapidOCR:
    # OCR via RapidOCR (PP-OCR models on ONNX Runtime) since 2026-11-21,
    # replacing EasyOCR — which needed PyTorch and crashed the whole process
    # (native access violation) on full-page images on this machine
    # (Technology Decision Log). Loaded lazily and cached, once per process.
    global _ocr_engine
    if _ocr_engine is None:
        with _ocr_lock:
            if _ocr_engine is None:
                _ocr_engine = RapidOCR(params={"Global.log_level": "warning"})
    return _ocr_engine


def _ocr_text(image_bytes: bytes) -> str:
    """All recognized text in reading order, space-joined (same output shape
    the EasyOCR-era `" ".join(readtext(..., detail=0))` produced). Raises on
    bytes that aren't a decodable image — same as before, so a corrupt image
    still resolves the Document to 'failed', never silently empty."""
    image: bytes | Image.Image = image_bytes
    with Image.open(io.BytesIO(image_bytes)) as probe:
        mode = probe.mode
    if mode in _TO_RGB_MODES or mode in _TO_RGBA_MODES:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB" if mode in _TO_RGB_MODES else "RGBA")
    result = _get_ocr_engine()(image)
    return " ".join(result.txts or ()).strip()


class DocumentTextExtractor:
    """REQ-003/REQ-004: extracts native text from PDF/DOCX, OCRs image
    files. Scope boundary: a *scanned* PDF (an image embedded in a PDF
    wrapper, with no text layer) is not yet handled — pypdf returns no
    text for it, which the ingestion service correctly surfaces as a
    'failed' Document rather than silently producing nothing. Only plain
    image uploads (REQ-003's "scanned images") go through OCR in V0.3."""

    def __init__(self, captioner: ImageCaptioner):
        # RAG-Pipeline-Development-History.md gap #2: only embedded
        # diagrams (PDF/DOCX) get vision-captioned — a standalone scanned-
        # image upload is a full document page, already well served by OCR
        # alone, so it's left untouched (deliberate scope limit, not an
        # oversight).
        self.captioner = captioner

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

    def _extract_pdf(self, file_bytes: bytes) -> list[ExtractedPage]:
        # Adaptive (2026-08-20 spike, merged): PDF has no `paragraph.style`
        # to read the way DOCX does, but pdfplumber exposes real per-
        # character font size/weight, which a text-regex heading heuristic
        # tried earlier in this project's history proved unreliable (0/130
        # real chunks detected) — font metadata is a categorically stronger
        # signal. `segments` carries the same heading path / content type
        # through to chunk_pages() as DOCX, funneling through the identical
        # packer. Real page numbers come directly from PDF's own page
        # structure — simpler than DOCX, which had to infer them from
        # explicit page-break markers because DOCX has none of its own.
        segments = _extract_pdf_segments(file_bytes, self.captioner)
        return [ExtractedPage(page_number=None, text="", segments=segments)]

    def _extract_docx(self, file_bytes: bytes) -> list[ExtractedPage]:
        # DOCX has no page concept in the file itself — pages only exist at
        # Word's render time. Treated as one page with page_number=None
        # (honest "not determinable") rather than fabricating "page 1").
        #
        # Adaptive (2026-08-19 spike, validated against 4 real fixtures
        # spanning 0/2/3/4-level heading depth, with/without tables and
        # embedded images): DOCX's structural signals are real, not
        # heuristic — paragraph.style.name for headings, real <w:tbl>
        # objects for tables, real embedded image relationships for
        # pictures — unlike PDF, where the same idea was tried and proven
        # unreliable via text-regex heuristics (0/130 real chunks detected).
        # `segments` carries the heading path + content type through to
        # chunk_pages(), which packs every type through the identical
        # size-bounded packer regardless of source (one fixed output shape).
        document = docx.Document(io.BytesIO(file_bytes))
        segments = _extract_docx_segments(document, self.captioner)
        return [ExtractedPage(page_number=None, text="", segments=segments)]

    @staticmethod
    def _extract_image(file_bytes: bytes) -> list[ExtractedPage]:
        return [ExtractedPage(page_number=1, text=_ocr_text(file_bytes))]

    @staticmethod
    def _extract_text(file_bytes: bytes) -> list[ExtractedPage]:
        # SD-007: a generated draft (Build Plan V0.8) is rendered as plain
        # UTF-8 text, not a real PDF/DOCX — same "no page concept" honesty
        # as DOCX above, since a generated draft has no page boundaries
        # either.
        return [ExtractedPage(page_number=None, text=file_bytes.decode("utf-8"))]


# ============================================================================
# DOCX adaptive extraction (2026-08-19 spike, merged to production). Walks
# the real document in document order, tracks the active heading stack, and
# routes each block (paragraph / table / embedded image) to its own
# segmentation — all tagged with whatever heading path is active. Every
# segment funnels through chunk.py's `_pack_typed_segments`, the same packer
# regardless of source, which is what "adaptive strategy, fixed chunk
# format" actually means.
# ============================================================================

def _iter_block_items(document: DocxDocumentType):
    """Standard python-docx recipe: `doc.paragraphs`/`doc.tables` are
    separate flat lists, NOT in true document order relative to each other —
    this walks the real XML body so a table appears exactly where it
    actually sits between paragraphs."""
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def _docx_style_heading_level(style_name: str) -> int | None:
    m = re.match(r"^Heading (\d+)$", style_name)
    if m:
        return int(m.group(1))
    if style_name == "Title":
        return 1
    return None


def _paragraph_has_page_break(paragraph: Paragraph) -> bool:
    """A real, explicit "insert page break" marker (`<w:br w:type="page"/>`)
    — reliable, author-placed data already in the file, unlike DOCX's
    *natural* text-overflow pagination, which Word computes only at render
    time and never stores. In every real fixture checked, a page break is
    its own dedicated empty paragraph (one run, no other content) — so
    incrementing the page counter the moment one is seen, before processing
    whatever paragraph comes next, correctly attributes content to the page
    it actually starts on."""
    for run in paragraph.runs:
        for br in run._element.findall(qn("w:br")):
            if br.get(qn("w:type")) == "page":
                return True
    return False


def _paragraph_image_blobs(paragraph: Paragraph, document: DocxDocumentType) -> list[bytes]:
    """Real embedded images referenced by this paragraph's runs, in order."""
    blobs = []
    for run in paragraph.runs:
        for drawing in run._element.findall(".//" + qn("w:drawing")):
            for blip in drawing.findall(".//" + qn("a:blip")):
                rid = blip.get(qn("r:embed"))
                if rid and rid in document.part.rels:
                    blobs.append(document.part.rels[rid].target_part.blob)
    return blobs


def _rows_to_table_segments(
    rows: list[list[str]], heading_path: tuple[str, ...], element_number: int, page_number: int | None
) -> list[Segment]:
    """Each data row becomes one segment, formatted as column:value pairs so
    it's meaningful read in isolation (a bare cell-value dump loses which
    column each number belongs to). Header row supplies the field names.
    Every row of one table shares the same `element_number` — a table is one
    addressable thing ("Table 3"), not N separate ones. Format-agnostic
    (plain string rows) so DOCX's `<w:tbl>` cells and PDF's
    `pdfplumber`-extracted table rows share the same conversion — the row
    text is what a table actually IS, regardless of which format it came
    from."""
    if not rows:
        return []
    header, data_rows = rows[0], rows[1:]
    segments = []
    for row in data_rows:
        pairs = "; ".join(f"{h}: {v}" for h, v in zip(header, row) if v)
        if pairs:
            segments.append(
                Segment(text=pairs, heading_path=heading_path, chunk_type="table_or_list", element_number=element_number, page_number=page_number)
            )
    return segments


def _combine_ocr_and_caption(ocr_text: str, caption: str | None) -> str:
    """RAG-Pipeline-Development-History.md gap #2: OCR alone is exact for
    legible characters but loses a diagram's structure; a vision caption
    recovers structure but is a paraphrase, not a character-exact read —
    combining both keeps OCR's exactness (the SYSTEM_PROMPT's "reproduce
    every concrete detail exactly" rule) while adding the structural
    narrative OCR alone can never provide. Falls back to whichever one
    exists; empty only when NEITHER found anything real (same "don't embed
    an empty placeholder chunk" convention as before this fix)."""
    if ocr_text and caption:
        return f"{ocr_text} Visual description: {caption}"
    return caption or ocr_text


def _prose_segments(text: str, heading_path: tuple[str, ...], page_number: int | None) -> list[Segment]:
    # Reuses chunk.py's own paragraph/sentence splitter — the same tested
    # logic the plain (non-adaptive) path uses, just tagged with a heading
    # path here instead of being packed directly.
    return [Segment(text=s, heading_path=heading_path, chunk_type="prose", page_number=page_number) for s in _segments_for(text)]


def _document_has_any_page_break(document: DocxDocumentType) -> bool:
    return any(_paragraph_has_page_break(p) for p in document.paragraphs)


def _extract_docx_segments(document: DocxDocumentType, captioner: ImageCaptioner) -> list[Segment]:
    segments: list[Segment] = []
    stack: list[tuple[int, str]] = []
    # Sequential, document-wide, 1-indexed — "Table 3"/"Image 2" the way a
    # lawyer would actually refer to them, not reset per section (that would
    # make several different things all "Table 1"). Counted only for
    # tables/images that actually produce a segment — an empty table or a
    # textless image has nothing a user could ask about, so it doesn't
    # consume a number and leave a confusing gap in the visible sequence.
    table_count = 0
    image_count = 0
    # RAG-Pipeline-Development-History.md gap #6 investigation surfaced an
    # adjacent DOCX cost issue: unlike the PDF path, DOCX had no hash-based
    # cache, so the SAME image genuinely embedded in several real paragraphs
    # re-invoked the paid vision captioner on identical bytes every time.
    # Cached by content hash: (content, its element_number) once computed,
    # or None meaning "checked, nothing meaningful" -- every real occurrence
    # still gets its own segment/page attribution, only the OCR+caption call
    # itself is deduplicated.
    image_content_cache: dict[bytes, tuple[str, int] | None] = {}
    # Real page number, tracked only when the document has at least one
    # explicit page-break marker — otherwise every chunk would get a
    # fabricated "page 1", which is worse than the honest `None` this
    # project already uses for "not determinable" (CLAUDE.md §4).
    tracks_pages = _document_has_any_page_break(document)
    page_number: int | None = 1 if tracks_pages else None

    for block in _iter_block_items(document):
        if isinstance(block, Paragraph):
            if tracks_pages and _paragraph_has_page_break(block):
                page_number += 1

            level = _docx_style_heading_level(block.style.name if block.style else "")
            if level is not None:
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, block.text.strip()))
                continue

            path_now = tuple(text for _, text in stack)
            for blob in _paragraph_image_blobs(block, document):
                img_hash = hashlib.sha256(blob).digest()
                if img_hash not in image_content_cache:
                    ocr_text = _ocr_text(blob)
                    content = _combine_ocr_and_caption(ocr_text, captioner.caption(blob))
                    if content:
                        image_count += 1
                        image_content_cache[img_hash] = (content, image_count)
                    else:
                        image_content_cache[img_hash] = None
                cached = image_content_cache[img_hash]
                if cached is not None:
                    content, element_num = cached
                    segments.append(
                        Segment(text=content, heading_path=path_now, chunk_type="image", element_number=element_num, page_number=page_number)
                    )
                # An image with no extractable text AND no meaningful vision
                # caption contributes nothing to text retrieval and is
                # dropped, not embedded as an empty placeholder chunk.

            if block.text.strip():
                segments.extend(_prose_segments(block.text, path_now, page_number))

        elif isinstance(block, Table):
            path_now = tuple(text for _, text in stack)
            rows = [[cell.text.strip() for cell in row.cells] for row in block.rows]
            table_segments = _rows_to_table_segments(rows, path_now, table_count + 1, page_number)
            if table_segments:
                table_count += 1
            segments.extend(table_segments)

    return segments


# ============================================================================
# PDF adaptive extraction (2026-08-20 spike, merged to production). PDF has
# no `paragraph.style` to read — its structural signal is real per-character
# font size/weight instead, extracted via pdfplumber (`pypdf` alone doesn't
# expose this usefully). A text-regex heading heuristic was tried earlier in
# this project's history and scored 0/130 real chunks; font metadata is a
# categorically different, real signal, spike-validated against the known
# real heading structure of the Apex_Meridian fixtures (cross-checked
# against their own DOCX version's real Heading-style paragraphs): every
# real heading recovered, in order, at every fixture size (10/30/60 pages).
# Real page numbers come directly from PDF's own page structure — no
# inference needed, unlike DOCX.
# ============================================================================

_PdfLine = tuple[int, list[dict]]  # (rounded top, words on that line)


def _pdf_line_text(line_words: list[dict]) -> str:
    return " ".join(w["text"] for w in sorted(line_words, key=lambda w: w["x0"]))


def _pdf_page_lines(page) -> list[_PdfLine]:
    """Words grouped into visual lines by rounded vertical position, sorted
    top-to-bottom — pdfplumber has no built-in 'line'/'paragraph' concept,
    only individual positioned words."""
    words = page.extract_words(extra_attrs=["size", "fontname"])
    lines: dict[int, list[dict]] = {}
    for w in words:
        lines.setdefault(round(w["top"]), []).append(w)
    return sorted(lines.items())


def _pdf_body_font_size(pages_lines: list[list[_PdfLine]]) -> float:
    """The most common font size across the whole document, by character
    count — real body text, not an assumed/hardcoded point size (different
    PDFs use different type scales). A heading candidate is real text
    meaningfully larger than this."""
    counts: dict[float, int] = {}
    for page_lines in pages_lines:
        for _, words in page_lines:
            for w in words:
                size = round(w["size"], 1)
                counts[size] = counts.get(size, 0) + len(w["text"])
    return max(counts, key=counts.get) if counts else 0.0


def _pdf_running_header_footer_keys(pages_lines: list[list[_PdfLine]]) -> set[tuple[int, str]]:
    """A (top, text) pair repeated at the same position on more than half
    the document's real pages is a running header/footer (e.g. a title bar
    reprinted on every page) — real content, but never a section heading,
    and excluded from prose too so it isn't duplicated into every page's
    text. Real finding from the spike: a naive "seen 3+ times" count wrongly
    flagged genuinely recurring section titles once tested against 30/60-
    page fixtures; only a page-fraction threshold held up at every size."""
    total_pages = len(pages_lines)
    seen: dict[tuple[int, str], set[int]] = {}
    for pnum, page_lines in enumerate(pages_lines, start=1):
        for top, words in page_lines:
            key = (top, _pdf_line_text(words))
            seen.setdefault(key, set()).add(pnum)
    return {key for key, pages in seen.items() if len(pages) > total_pages * 0.5}


def _pdf_heading_candidate_sizes(pages_lines: list[list[_PdfLine]], body_size: float, header_footer_keys: set[tuple[int, str]]) -> list[float]:
    """Distinct real font sizes used by bold text larger than body text,
    across the whole document, largest first — bucketed into heading levels
    1, 2, 3... the same way DOCX's explicit Heading-N styles are, but
    derived from what this specific PDF's own type scale actually is rather
    than a hardcoded point size."""
    sizes: set[float] = set()
    for page_lines in pages_lines:
        for top, words in page_lines:
            text = _pdf_line_text(words)
            if (top, text) in header_footer_keys or not text.strip():
                continue
            max_size = max(round(w["size"], 1) for w in words)
            is_bold = any("Bold" in w["fontname"] for w in words)
            if is_bold and max_size > body_size:
                sizes.add(max_size)
    return sorted(sizes, reverse=True)


def _truly_drawn_xobject_identities(page, reader: PdfReader) -> set[tuple[int, int]]:
    """RAG-Pipeline-Development-History.md gap #6: `page.images` lists every
    image reachable via the page's (possibly INHERITED) `/Resources`
    dictionary, regardless of whether that page's own content stream
    actually draws it — real PDF page trees can share one `/Resources` node
    across many pages. The real, verifiable signal is whether this page's
    own content stream contains a `Do` operator actually invoking that
    XObject. Real indirect-object identity (idnum, generation) is compared,
    not the resolved dict content — two distinct images can share identical
    metadata (width/height/colorspace), so comparing resolved dicts would
    give false matches; only the underlying indirect reference is reliable
    (spike-verified 2026-08-25 against real Apex Meridian fixtures)."""
    contents = page.get_contents()
    if contents is None:
        return set()
    resources = page.get("/Resources")
    xobjects = resources.get("/XObject") if resources else None
    if not xobjects:
        return set()
    raw_xobjects = resources.raw_get("/XObject")
    raw_xobjects = raw_xobjects.get_object() if isinstance(raw_xobjects, IndirectObject) else raw_xobjects
    name_to_identity: dict[str, tuple[int, int]] = {}
    for name in xobjects.keys():
        raw_ref = raw_xobjects.raw_get(name)
        if isinstance(raw_ref, IndirectObject):
            name_to_identity[str(name)] = (raw_ref.idnum, raw_ref.generation)

    drawn: set[tuple[int, int]] = set()
    for operands, operator in ContentStream(contents, reader).operations:
        if operator == b"Do" and operands:
            identity = name_to_identity.get(str(operands[0]))
            if identity is not None:
                drawn.add(identity)
    return drawn


def _extract_pdf_segments(file_bytes: bytes, captioner: ImageCaptioner) -> list[Segment]:
    segments: list[Segment] = []
    reader = PdfReader(io.BytesIO(file_bytes))

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        pages_lines = [_pdf_page_lines(page) for page in pdf.pages]
        body_size = _pdf_body_font_size(pages_lines)
        header_footer_keys = _pdf_running_header_footer_keys(pages_lines)
        ordered_sizes = _pdf_heading_candidate_sizes(pages_lines, body_size, header_footer_keys)

        stack: list[tuple[int, str]] = []
        table_count = 0
        image_count = 0
        # Real bug (2026-08-21 spike): a PDF page's real embedded images can
        # be reported by pypdf on *every* page, not just the one they're
        # actually drawn on — a real PDF-structure quirk where the page
        # tree shares/inherits one `/Resources` dictionary across pages, so
        # `page.images` (which just enumerates that dictionary) sees every
        # image on every page, whether or not that page's own content
        # stream actually draws it. A real 60-page fixture hit this hard:
        # 3 real diagrams reported 60 times each (180 total) — OCR-ing
        # every "occurrence" made ingestion take 5+ minutes and read as a
        # hung/failed upload.
        #
        # RAG-Pipeline-Development-History.md gap #6 (2026-08-25): the fix
        # above (dedup by content hash, keep only the first-encountered
        # page) traded that performance bug for a correctness one — a real
        # spike against the real Apex Meridian fixtures found the same few
        # template images are genuinely, truly drawn on several distinct
        # real pages each (confirmed via `_truly_drawn_xobject_identities`'s
        # content-stream `Do`-check, not just resource-dict reachability),
        # and every occurrence after the first was being silently dropped —
        # not "attributed to the wrong page," genuinely absent for every
        # page but the first. Fixed properly: OCR+caption is still computed
        # once per unique image hash (preserving the performance fix), but
        # now every page real Do-check confirms as a true drawing page gets
        # its own segment sharing that cached content and `element_number`
        # — an image resource-reachable but never actually drawn anywhere
        # is correctly dropped entirely, same as before.
        image_content_cache: dict[bytes, tuple[str, int] | None] = {}

        for pnum, page in enumerate(pdf.pages, start=1):
            tables = page.find_tables()
            table_bboxes = [t.bbox for t in tables]

            # Table cell text would otherwise also be picked up as stray
            # "prose" lines, duplicating every table's content — excluded
            # from the text pass by real bounding box, not by guessing.
            text_page = page
            for bbox in table_bboxes:
                text_page = text_page.outside_bbox(bbox)
            text_lines = _pdf_page_lines(text_page)

            # One unified, position-sorted walk per page — headings, prose
            # lines, and tables interleaved by real vertical position, the
            # same "process in true document order" principle as DOCX's
            # `_iter_block_items`, just built from positional data instead
            # of an XML tree.
            elements: list[tuple[float, str, object]] = []
            for top, words in text_lines:
                text = _pdf_line_text(words)
                if not text.strip() or (top, text) in header_footer_keys:
                    continue
                max_size = max(round(w["size"], 1) for w in words)
                is_bold = any("Bold" in w["fontname"] for w in words)
                if is_bold and max_size in ordered_sizes:
                    elements.append((top, "heading", (max_size, text)))
                else:
                    elements.append((top, "text", text))
            for table, bbox in zip(tables, table_bboxes):
                elements.append((bbox[1], "table", table))
            elements.sort(key=lambda e: e[0])

            # A heading that visually wraps onto multiple lines (e.g. a long
            # title) becomes multiple same-size heading-candidate lines in a
            # row — real bug (2026-08-21 spike): each was treated as a new
            # sibling replacing the last, so only the wrapped title's FINAL
            # line ever survived as the real heading text. Consecutive
            # same-size heading elements are real continuations of one
            # heading, not real siblings, and are merged into one.
            merged_elements: list[tuple[float, str, object]] = []
            for top, kind, payload in elements:
                if (
                    kind == "heading"
                    and merged_elements
                    and merged_elements[-1][1] == "heading"
                    and merged_elements[-1][2][0] == payload[0]
                ):
                    prev_top, _, (size, prev_text) = merged_elements[-1]
                    merged_elements[-1] = (prev_top, "heading", (size, f"{prev_text} {payload[1]}"))
                else:
                    merged_elements.append((top, kind, payload))
            elements = merged_elements

            prose_buffer: list[str] = []

            def flush_prose(path_now: tuple[str, ...]) -> None:
                nonlocal prose_buffer
                if prose_buffer:
                    segments.extend(_prose_segments(" ".join(prose_buffer), path_now, pnum))
                    prose_buffer = []

            for _, kind, payload in elements:
                path_now = tuple(t for _, t in stack)
                if kind == "heading":
                    flush_prose(path_now)
                    size, text = payload
                    level = ordered_sizes.index(size) + 1
                    while stack and stack[-1][0] >= level:
                        stack.pop()
                    stack.append((level, text))
                elif kind == "text":
                    prose_buffer.append(payload)
                elif kind == "table":
                    flush_prose(path_now)
                    rows = [[(cell or "").strip() for cell in row] for row in (payload.extract() or [])]
                    table_segments = _rows_to_table_segments(rows, path_now, table_count + 1, pnum)
                    if table_segments:
                        table_count += 1
                    segments.extend(table_segments)

            flush_prose(tuple(t for _, t in stack))

            # Embedded images — appended after this page's text/tables since
            # pypdf doesn't expose a reliable position to interleave them
            # precisely; associated with whichever heading is active by the
            # end of the page, the same approximation DOCX makes implicitly
            # by tying an image to its containing paragraph's heading.
            path_now = tuple(t for _, t in stack)
            truly_drawn = _truly_drawn_xobject_identities(reader.pages[pnum - 1], reader)
            for img in reader.pages[pnum - 1].images:
                ref = img.indirect_reference
                identity = (ref.idnum, ref.generation) if isinstance(ref, IndirectObject) else None
                if identity is None or identity not in truly_drawn:
                    # Resource-reachable via the (possibly inherited) page
                    # tree, but this page's own content stream never actually
                    # draws it — a real PDF-structure artifact, not a real
                    # occurrence on this page.
                    continue

                img_hash = hashlib.sha256(img.data).digest()
                if img_hash not in image_content_cache:
                    ocr_text = _ocr_text(img.data)
                    content = _combine_ocr_and_caption(ocr_text, captioner.caption(img.data))
                    if content:
                        image_count += 1
                        image_content_cache[img_hash] = (content, image_count)
                    else:
                        image_content_cache[img_hash] = None
                cached = image_content_cache[img_hash]
                if cached is not None:
                    content, element_num = cached
                    segments.append(
                        Segment(text=content, heading_path=path_now, chunk_type="image", element_number=element_num, page_number=pnum)
                    )
                # An image with no extractable text AND no meaningful vision
                # caption contributes nothing to text retrieval and is
                # dropped, not embedded as an empty placeholder chunk — same
                # convention as DOCX.

    return segments
