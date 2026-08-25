import re

# Gap #1 in RAG-Pipeline-Development-History.md: for a Matter large enough to
# fall onto the RRF-ranked retrieval path (chat_service.FULL_CONTEXT_CHAR_CAP),
# a question naming a specific page/section/table/image number has no
# guarantee its chunk is even in the top-K candidate pool — vector/keyword
# search can only find it by accident. This pure function detects that a
# question names a real, verifiable identifier at all, so the application
# layer can go fetch it directly instead of hoping ranking surfaces it.
#
# Scope deliberately limited to page/section/table/image — the only
# identifiers document_chunks actually stores as queryable columns today
# (page_number, section, element_number+chunk_type). Clause/exhibit/annexure
# references have no column to exact-match against yet (would need an
# ingestion-time change first), so they're not recognized here.
_IDENTIFIER_RE = re.compile(
    r"\b(page|pg|section|sec|table|tbl|image|img|figure|fig)s?\.?\s*(?:no\.?\s*)?#?\s*(\d+)\b",
    re.IGNORECASE,
)

_KIND_ALIASES = {
    "page": "page",
    "pg": "page",
    "section": "section",
    "sec": "section",
    "table": "table",
    "tbl": "table",
    "image": "image",
    "img": "image",
    "figure": "image",
    "fig": "image",
}


def extract_identifier_refs(question: str) -> list[tuple[str, int]]:
    """Returns deduplicated (kind, number) pairs, kind in {"page", "section",
    "table", "image"}, in first-seen order. Empty list means the question
    named no recognizable numbered identifier."""
    seen: dict[tuple[str, int], None] = {}
    for raw_kind, raw_number in _IDENTIFIER_RE.findall(question):
        ref = (_KIND_ALIASES[raw_kind.lower()], int(raw_number))
        seen.setdefault(ref, None)
    return list(seen.keys())
