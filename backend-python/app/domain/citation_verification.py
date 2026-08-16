import re
from dataclasses import dataclass

from app.domain.chat import NOT_FOUND_RESPONSE, OUT_OF_SCOPE_RESPONSE
from app.domain.sentence_split import split_into_sentences

MARKER_RE = re.compile(r"\[(\d+)\]")

GAP_NOTE = "\n\n(Some parts of the answer above referenced source material that couldn't be verified and were removed.)"


@dataclass(frozen=True)
class VerifiedAnswer:
    text: str
    cited_chunk_numbers: list[int]  # 1-indexed, first-cited order, deduplicated
    all_valid: bool


def verify_citations(raw_answer: str, num_chunks: int) -> VerifiedAnswer:
    """Grounding Rules 4/5 (AI Architecture §3): every factual sentence must
    carry a citation marker resolving to a chunk actually retrieved for this
    call — checked here after generation, not trusted from the model. A
    sentence with no marker, or only a marker outside 1..num_chunks, is
    dropped from the final answer rather than kept as if it were verified.
    Pure function — no I/O, no framework dependency, unit-tested alone."""
    stripped = raw_answer.strip()
    if stripped in (NOT_FOUND_RESPONSE, OUT_OF_SCOPE_RESPONSE):
        return VerifiedAnswer(text=stripped, cited_chunk_numbers=[], all_valid=True)

    # Deliberately NOT stripped here (unlike chunk.py's use of the same
    # splitter) — each piece keeps its original trailing whitespace so kept
    # sentences can be concatenated directly below without collapsing the
    # model's own markdown structure (numbered lists, blank lines between
    # sections) into a single flat run of space-joined text.
    sentences = [s for s in split_into_sentences(stripped) if s.strip()]
    if not sentences:
        return VerifiedAnswer(text=NOT_FOUND_RESPONSE, cited_chunk_numbers=[], all_valid=False)

    kept_sentences: list[str] = []
    cited: list[int] = []
    any_dropped = False

    for sentence in sentences:
        markers = [int(m) for m in MARKER_RE.findall(sentence)]
        valid_markers = [m for m in markers if 1 <= m <= num_chunks]

        if not valid_markers:
            # No marker at all, or every marker present was out of range —
            # an unsupported claim (Rule 4), dropped rather than kept.
            any_dropped = True
            continue

        kept_sentences.append(sentence)
        for marker in valid_markers:
            if marker not in cited:
                cited.append(marker)
        if len(valid_markers) < len(markers):
            # Sentence had at least one real citation but also an invalid
            # one — kept (it IS grounded), but the answer as a whole still
            # gets the gap note since part of it couldn't be verified.
            any_dropped = True

    if not kept_sentences:
        return VerifiedAnswer(text=NOT_FOUND_RESPONSE, cited_chunk_numbers=[], all_valid=False)

    # Plain concatenation, not " ".join — each kept sentence already carries
    # its own original trailing whitespace (see split_into_sentences), so
    # adding another separator here would double it up.
    final_text = "".join(kept_sentences).rstrip()
    if any_dropped:
        final_text += GAP_NOTE

    return VerifiedAnswer(text=final_text, cited_chunk_numbers=cited, all_valid=not any_dropped)
