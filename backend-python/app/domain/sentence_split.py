import re

# A bare "punctuation + whitespace + capital letter" heuristic misfires on
# any abbreviation that happens to end a token right before another capitalized
# word — "Apex Components Pvt. Ltd." is exactly this: "Pvt." followed by
# "Ltd" (capitalized) looks like a sentence boundary but isn't. This list
# isn't exhaustive linguistics, just the abbreviations this project's real
# documents (legal/corporate, Indian currency/dates) have actually produced
# false splits on so far — extend it here the moment a new one bites.
_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "hon",
    "pvt", "ltd", "co", "inc", "corp", "llp", "llc", "plc",
    "vs", "etc", "no", "nos", "rs", "st", "ave", "approx",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
}

_CANDIDATE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_WORD_BEFORE_PERIOD_RE = re.compile(r"(\w+)\.$")


def _is_abbreviation(word: str) -> bool:
    if word.lower() in _ABBREVIATIONS:
        return True
    if len(word) == 1 and word.isupper():  # a single initial, e.g. "A. B. Smith"
        return True
    return False


def split_into_sentences(text: str) -> list[str]:
    """Splits text at sentence-ending punctuation followed by a capital
    letter or digit, EXCEPT where the word immediately before the
    punctuation is a known abbreviation — those splits are merged back into
    the following piece instead. Shared by ingestion chunking (chunk.py)
    and chat-answer citation verification (citation_verification.py), which
    independently hit the same class of false-split bug on two different
    abbreviations ("Rs." then "Pvt. Ltd.") before this was extracted.

    Each returned piece keeps its original trailing whitespace (up to the
    start of the next piece) rather than having it stripped away — a
    caller that drops some pieces and concatenates the rest directly
    (`"".join(...)`) preserves the source's original formatting (blank
    lines, markdown lists) instead of collapsing everything to single
    spaces. A caller that doesn't care can still `.strip()` each piece
    itself, same as before."""
    matches = list(_CANDIDATE_SPLIT_RE.finditer(text))
    if not matches:
        return [text]

    raw_pieces: list[str] = []
    start = 0
    for m in matches:
        raw_pieces.append(text[start:m.end()])  # sentence text + its trailing separator
        start = m.end()
    raw_pieces.append(text[start:])

    sentences: list[str] = []
    buffer = raw_pieces[0]
    for piece in raw_pieces[1:]:
        match = _WORD_BEFORE_PERIOD_RE.search(buffer.rstrip())
        if match and _is_abbreviation(match.group(1)):
            buffer += piece  # not a real sentence end — merge, whitespace already embedded
        else:
            sentences.append(buffer)
            buffer = piece
    sentences.append(buffer)
    return sentences
