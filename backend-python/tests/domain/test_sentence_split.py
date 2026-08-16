from app.domain.sentence_split import split_into_sentences


def test_a_plain_two_sentence_string_splits_cleanly():
    result = split_into_sentences("The lease term is 36 months. The rent is due monthly.")
    assert [s.strip() for s in result] == ["The lease term is 36 months.", "The rent is due monthly."]


def test_pvt_ltd_company_suffix_is_not_mistaken_for_a_sentence_boundary():
    # Exact real bug report: "Apex Components Pvt. Ltd." got split into
    # "Apex Components Pvt." and "Ltd. ..." because "Ltd" is capitalized,
    # silently detaching the citation marker from the sentence and causing
    # the whole claim to be dropped as "unsupported" downstream.
    text = "The client is Apex Components Pvt. Ltd. [1][2]. Apex is the party claiming damages [1]."
    result = split_into_sentences(text)
    assert [s.strip() for s in result] == [
        "The client is Apex Components Pvt. Ltd. [1][2].",
        "Apex is the party claiming damages [1].",
    ]


def test_rs_currency_abbreviation_is_not_mistaken_for_a_sentence_boundary():
    text = "The monthly rent is Rs. 85,000. The term is 36 months."
    result = split_into_sentences(text)
    assert [s.strip() for s in result] == ["The monthly rent is Rs. 85,000.", "The term is 36 months."]


def test_common_legal_corporate_abbreviations_are_recognized():
    text = "Meridian Industrial Estates LLP disputed the claim. Apex Components Pvt. Ltd. denied any alteration."
    result = split_into_sentences(text)
    assert [s.strip() for s in result] == [
        "Meridian Industrial Estates LLP disputed the claim.",
        "Apex Components Pvt. Ltd. denied any alteration.",
    ]


def test_a_single_initial_is_not_mistaken_for_a_sentence_boundary():
    text = "The report was signed by A. B. Smith on 3 March 2025. It was later notarized."
    result = split_into_sentences(text)
    assert [s.strip() for s in result] == [
        "The report was signed by A. B. Smith on 3 March 2025.",
        "It was later notarized.",
    ]


def test_dated_chronology_entries_still_split_correctly():
    text = "Apex reported the damage. 03 Sep 2024 — Meridian disputed liability."
    result = split_into_sentences(text)
    assert [s.strip() for s in result] == ["Apex reported the damage.", "03 Sep 2024 — Meridian disputed liability."]


def test_no_sentence_punctuation_at_all_returns_the_whole_text_as_one_piece():
    assert split_into_sentences("Date Loss category Source Amount") == ["Date Loss category Source Amount"]


def test_concatenating_every_piece_exactly_reproduces_the_original_text():
    # The actual point of returning pieces with embedded trailing whitespace
    # rather than stripped: a caller that keeps every piece must be able to
    # rebuild the source exactly, including markdown-list-style formatting
    # (numbered headings, blank lines between sections) an LLM answer often
    # uses — losing that when a caller strips-and-rejoins is a real defect,
    # not a cosmetic one (see the "explain this document" bug it caused).
    text = "Section one. It has details.\n\n1. Heading one:\n   - A bullet point. Another bullet.\n\n2. Heading two:\n   - Final point."
    assert "".join(split_into_sentences(text)) == text


def test_a_dropped_sentence_does_not_leave_double_whitespace_behind():
    # If a caller keeps sentence 1 and 3 but drops sentence 2, concatenating
    # the survivors shouldn't collapse into an ugly double-space/newline —
    # each kept piece's own trailing whitespace should read naturally.
    text = "Kept one. Dropped two. Kept three."
    pieces = split_into_sentences(text)
    kept = pieces[0] + pieces[2]  # simulate dropping the middle sentence
    assert kept == "Kept one. Kept three."
