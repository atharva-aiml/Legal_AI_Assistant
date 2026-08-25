from app.domain.identifier_query import extract_identifier_refs


def test_extracts_a_page_number():
    assert extract_identifier_refs("what is on page 54") == [("page", 54)]


def test_extracts_a_section_number():
    assert extract_identifier_refs("explain section 53 in detail") == [("section", 53)]


def test_extracts_a_table_number():
    assert extract_identifier_refs("what does table 3 say") == [("table", 3)]


def test_extracts_an_image_number():
    assert extract_identifier_refs("describe image 2") == [("image", 2)]


def test_figure_is_aliased_to_image():
    assert extract_identifier_refs("what's in fig 4") == [("image", 4)]


def test_extracts_multiple_distinct_refs_in_first_seen_order():
    assert extract_identifier_refs("brief me on page 9 and page 12") == [("page", 9), ("page", 12)]


def test_deduplicates_a_repeated_ref():
    assert extract_identifier_refs("page 54, seriously, page 54") == [("page", 54)]


def test_abbreviations_and_a_no_prefix_are_recognized():
    assert extract_identifier_refs("explain table no. 5") == [("table", 5)]
    assert extract_identifier_refs("pg 9") == [("page", 9)]
    assert extract_identifier_refs("sec 3") == [("section", 3)]


def test_a_bare_number_with_no_keyword_is_not_a_false_positive():
    # Real spike finding: dollar amounts and bare years must never be
    # mistaken for a page/section/table/image reference.
    assert extract_identifier_refs("how much was the settlement, was it 470 million dollars") == []
    assert extract_identifier_refs("what happened in 1991") == []


def test_a_question_with_no_number_at_all_returns_nothing():
    assert extract_identifier_refs("summarize the whole document") == []


def test_clause_is_a_known_gap_not_yet_recognized():
    # Deliberate scope limit (see identifier_query.py docstring): no
    # clause_number column exists to exact-match against yet.
    assert extract_identifier_refs("what is clause 7.2 about") == []
