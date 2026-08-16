from app.domain.chat import NOT_FOUND_RESPONSE, OUT_OF_SCOPE_RESPONSE
from app.domain.citation_verification import verify_citations


def test_the_fixed_out_of_scope_response_passes_through_as_valid_with_no_citations():
    result = verify_citations(OUT_OF_SCOPE_RESPONSE, num_chunks=5)

    assert result.all_valid is True
    assert result.cited_chunk_numbers == []
    assert result.text == OUT_OF_SCOPE_RESPONSE


def test_a_fully_cited_answer_passes_through_unchanged():
    answer = "The rent is Rs. 85,000 [1]. The term is 36 months [2]."
    result = verify_citations(answer, num_chunks=2)

    assert result.all_valid is True
    assert result.cited_chunk_numbers == [1, 2]
    assert result.text == answer


def test_a_sentence_with_no_citation_marker_is_dropped_grounding_rule_4():
    answer = "The rent is Rs. 85,000 [1]. This seems like a fair deal overall."
    result = verify_citations(answer, num_chunks=1)

    assert result.all_valid is False
    assert "fair deal" not in result.text
    assert "Rs. 85,000" in result.text
    assert result.cited_chunk_numbers == [1]


def test_a_marker_outside_the_retrieved_chunk_range_is_dropped_not_trusted():
    # Only 2 chunks were actually retrieved this call — [5] doesn't resolve to anything real.
    answer = "The landlord's agent is listed in the filing [5]."
    result = verify_citations(answer, num_chunks=2)

    assert result.all_valid is False
    assert result.cited_chunk_numbers == []
    assert result.text == NOT_FOUND_RESPONSE


def test_when_every_sentence_is_dropped_the_result_is_the_fixed_not_found_response():
    answer = "This is definitely true. So is this."
    result = verify_citations(answer, num_chunks=3)

    assert result.text == NOT_FOUND_RESPONSE
    assert result.all_valid is False


def test_the_fixed_not_found_response_passes_through_as_valid_with_no_citations():
    result = verify_citations(NOT_FOUND_RESPONSE, num_chunks=0)

    assert result.all_valid is True
    assert result.cited_chunk_numbers == []
    assert result.text == NOT_FOUND_RESPONSE


def test_a_dropped_sentence_appends_a_gap_note_so_the_lawyer_knows_something_was_removed():
    answer = "The rent is Rs. 85,000 [1]. This is unrelated commentary."
    result = verify_citations(answer, num_chunks=1)

    assert "couldn't be verified" in result.text


def test_markdown_structure_survives_when_every_item_is_cited():
    # Real bug repro: a multi-section markdown answer (numbered headings,
    # bullets, blank lines between sections — exactly what the LLM produces
    # for a broad "explain this document" question) used to get flattened
    # into a single space-joined wall of text by the old " ".join(...)
    # reconstruction, destroying the model's own formatting.
    answer = (
        "1. **Lease Agreement**:\n"
        "   - Apex entered into a five-year lease [1].\n\n"
        "2. **Water Ingress**:\n"
        "   - A monsoon caused damage [2]."
    )
    result = verify_citations(answer, num_chunks=2)

    assert result.all_valid is True
    assert result.text == answer  # byte-for-byte, formatting intact


def test_markdown_structure_survives_around_a_dropped_section():
    # Same shape, but the middle section has no citation and must be
    # dropped — the surviving sections' own formatting (headings, bullets,
    # blank lines) must still read cleanly, not collapse into a run-on line.
    answer = "1. **Kept heading**:\n   - Cited fact [1].\n\n2. **Dropped heading**:\n   - Uncited claim.\n\n3. **Also kept**:\n   - Another cited fact [1]."
    result = verify_citations(answer, num_chunks=1)

    assert result.all_valid is False
    assert "Dropped heading" not in result.text
    assert "Uncited claim" not in result.text
    assert "1. **Kept heading**:\n   - Cited fact [1]." in result.text
    assert "3. **Also kept**:\n   - Another cited fact [1]." in result.text
