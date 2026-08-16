import pytest

from app.domain.chat import (
    Citation,
    DocumentMetadata,
    InvalidChatMessageException,
    NOT_FOUND_RESPONSE,
    OUT_OF_SCOPE_RESPONSE,
    metadata_excerpt,
    validate_assistant_message,
)


def test_an_assistant_answer_with_a_citation_is_valid():
    citation = Citation(id="c1", chat_message_id="m1", document_id="d1", page_number=2, excerpt="the rent is...")
    validate_assistant_message("The monthly rent is Rs. 85,000 [1].", [citation])  # does not raise


def test_the_fixed_not_found_response_needs_zero_citations():
    validate_assistant_message(NOT_FOUND_RESPONSE, [])  # does not raise


def test_the_fixed_out_of_scope_response_needs_zero_citations():
    # "What are the strongest documents for the developer?" — a real
    # question the documents address plenty, but that asks for a
    # strategic judgment, not organized content (Requirements §4 Non-Goals).
    validate_assistant_message(OUT_OF_SCOPE_RESPONSE, [])  # does not raise


def test_br006_a_factual_looking_answer_with_no_citation_is_rejected():
    with pytest.raises(InvalidChatMessageException):
        validate_assistant_message("The monthly rent is Rs. 85,000.", [])


def test_metadata_excerpt_states_the_real_page_count():
    metadata = DocumentMetadata(document_id="d1", file_name="lease.pdf", page_count=11)
    assert metadata_excerpt(metadata) == "lease.pdf has 11 pages."


def test_metadata_excerpt_handles_singular_page_count():
    metadata = DocumentMetadata(document_id="d1", file_name="notice.pdf", page_count=1)
    assert metadata_excerpt(metadata) == "notice.pdf has 1 page."


def test_metadata_excerpt_is_honest_when_page_count_is_not_determinable():
    # DOCX has no real page concept in the file itself (CLAUDE.md §4).
    metadata = DocumentMetadata(document_id="d1", file_name="agreement.docx", page_count=None)
    assert metadata_excerpt(metadata) == "agreement.docx — page count not available."
