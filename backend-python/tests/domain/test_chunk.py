from app.domain.chunk import CHUNK_OVERLAP_CHARS, CHUNK_SIZE_CHARS, TABLE_CHUNK_SIZE_CHARS, ExtractedPage, Segment, chunk_pages


def test_empty_pages_produce_no_chunks():
    assert chunk_pages([]) == []
    assert chunk_pages([ExtractedPage(page_number=1, text="")]) == []
    assert chunk_pages([ExtractedPage(page_number=1, text="   ")]) == []


def test_short_page_produces_one_chunk_tagged_with_its_real_page_number():
    chunks = chunk_pages([ExtractedPage(page_number=1, text="The tenant shall pay rent by the 5th of each month.")])
    assert len(chunks) == 1
    assert chunks[0].content == "The tenant shall pay rent by the 5th of each month."
    assert chunks[0].page_number == 1


def test_a_chunk_never_mixes_content_from_two_different_pages():
    # The exact bug reported: page_number 0 contained text from pages 1, 2, and 3
    # because extraction joined every page into one blob before chunking.
    page1 = ExtractedPage(page_number=1, text="Page one content about the lease term. " * 100)
    page2 = ExtractedPage(page_number=2, text="Page two content about the rent clause. " * 100)

    chunks = chunk_pages([page1, page2])

    for chunk in chunks:
        if chunk.page_number == 1:
            assert "rent clause" not in chunk.content
        elif chunk.page_number == 2:
            assert "lease term" not in chunk.content


def test_page_numbers_start_at_1_not_0():
    chunks = chunk_pages([ExtractedPage(page_number=1, text="First page text.")])
    assert all(c.page_number != 0 for c in chunks)
    assert chunks[0].page_number == 1


def test_chunk_indices_stay_sequential_across_pages():
    page1 = ExtractedPage(page_number=1, text="Short page one.")
    page2 = ExtractedPage(page_number=2, text="Short page two.")
    chunks = chunk_pages([page1, page2])
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_docx_pages_carry_no_page_number_rather_than_a_fabricated_one():
    # DOCX has no real page concept in the file itself (CLAUDE.md §4) —
    # None is the honest answer, not "page 1" for everything.
    chunks = chunk_pages([ExtractedPage(page_number=None, text="Some DOCX paragraph text.")])
    assert chunks[0].page_number is None


def test_a_chunk_never_breaks_mid_word_real_bug_repro():
    # Reproduces the exact reported symptom: real PDF text wraps every
    # visual line with a bare "\n" (no blank-line paragraphs), and the old
    # character-offset slicer cut wherever the 2800th character happened to
    # land, including mid-word. This builds a page just over one chunk's
    # worth of size, entirely out of complete sentences, and asserts every
    # resulting chunk starts and ends on a real word/sentence boundary.
    sentences = [f"Clause {i}.{i} governs the obligations of the parties in respect of matter {i}." for i in range(1, 80)]
    page_text = " ".join(sentences)
    assert len(page_text) > CHUNK_SIZE_CHARS * 2  # actually exercises multiple chunks

    chunks = chunk_pages([ExtractedPage(page_number=5, text=page_text)])

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.page_number == 5
        # Starts at a real, complete word — every sentence in this fixture
        # begins with the literal word "Clause", never a fragment of it.
        assert chunk.content.split(" ", 1)[0] == "Clause"
        # Ends on sentence-ending punctuation, not an arbitrary character.
        assert chunk.content.rstrip()[-1] in ".!?"


def test_consecutive_chunks_overlap_on_a_whole_sentence_not_a_raw_character_cut():
    sentences = [f"This is sentence number {i} in a long legal recital about the parties." for i in range(1, 60)]
    page_text = " ".join(sentences)
    chunks = chunk_pages([ExtractedPage(page_number=1, text=page_text)])

    assert len(chunks) > 1
    # The tail of chunk 0 and the head of chunk 1 share at least one whole,
    # unbroken sentence (real overlap), not an arbitrary substring.
    shared = set(chunks[0].content.split(". ")) & set(chunks[1].content.split(". "))
    assert len(shared) >= 1


def test_a_long_run_on_line_with_no_sentence_punctuation_is_hard_split_at_word_boundaries():
    # Mirrors a real table row pypdf extracts as one unbroken line of short
    # values with no periods at all (Financial Loss Ledger in the real test PDF).
    words = [f"Item{i}" for i in range(1200)]  # long enough to exceed one chunk, no punctuation anywhere
    page_text = " ".join(words)

    chunks = chunk_pages([ExtractedPage(page_number=3, text=page_text)])

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.content) <= CHUNK_SIZE_CHARS
        # Every chunk is made of whole "Item123" tokens — never a word sliced in half.
        for token in chunk.content.split(" "):
            assert token.startswith("Item")


# --- Adaptive (segment-aware) packing path — DOCX-adaptive chunking, merged 2026-08-19 ---


def test_a_page_with_segments_routes_to_the_adaptive_packer_and_tags_its_section():
    page = ExtractedPage(
        page_number=None,
        text="",
        segments=[
            Segment(text="First sentence under this heading.", heading_path=("Section 1",), chunk_type="prose"),
            Segment(text="Second sentence under the same heading.", heading_path=("Section 1",), chunk_type="prose"),
        ],
    )
    chunks = chunk_pages([page])

    assert len(chunks) == 1
    assert chunks[0].page_number is None  # DOCX has no page concept, same as the plain path
    assert chunks[0].metadata.section == "Section 1"
    assert chunks[0].metadata.chunk_type == "prose"
    assert "First sentence" in chunks[0].content and "Second sentence" in chunks[0].content


def test_a_nested_headings_section_is_the_full_breadcrumb_not_just_the_leaf():
    # Real bug (2026-08-20): a document with genuine multi-level headings
    # (e.g. "53. Access to Justice" > "Mass claims and vulnerable
    # populations") had its lawyer-meaningful TOP-level heading silently
    # discarded -- only the deepest heading was ever kept as `section`, so
    # "what is section 53 Access to Justice" could never find it and
    # "explain page 54" never mentioned it.
    page = ExtractedPage(
        page_number=None,
        text="",
        segments=[
            Segment(
                text="Content nested three headings deep.",
                heading_path=("53. Access to Justice", "Mass claims and vulnerable populations", "Section-specific legal record"),
            )
        ],
    )
    chunks = chunk_pages([page])

    assert chunks[0].metadata.section == "53. Access to Justice > Mass claims and vulnerable populations > Section-specific legal record"


def test_a_segment_with_no_active_heading_gets_section_none_not_a_fabricated_one():
    # The graceful-fallback case: a real flat DOCX with zero heading styles
    # (verified live against Donoghue v Stevenson) — never a fabricated section.
    page = ExtractedPage(page_number=None, text="", segments=[Segment(text="Plain paragraph, no heading above it.")])
    chunks = chunk_pages([page])

    assert chunks[0].metadata.section is None


def test_a_heading_change_is_a_hard_chunk_boundary_even_for_tiny_segments():
    page = ExtractedPage(
        page_number=None,
        text="",
        segments=[
            Segment(text="Short line under heading A.", heading_path=("Heading A",)),
            Segment(text="Short line under heading B.", heading_path=("Heading B",)),
        ],
    )
    chunks = chunk_pages([page])

    # Two segments that would easily fit in one chunk by size never merge
    # across a heading change — each heading gets its own chunk(s).
    assert len(chunks) == 2
    assert chunks[0].metadata.section == "Heading A"
    assert chunks[1].metadata.section == "Heading B"


def test_a_content_type_change_is_a_hard_chunk_boundary():
    # A chunk is never "half table, half prose" — same heading, different type.
    page = ExtractedPage(
        page_number=None,
        text="",
        segments=[
            Segment(text="Prose sentence under this section.", heading_path=("Section 1",), chunk_type="prose"),
            Segment(text="Column: value", heading_path=("Section 1",), chunk_type="table_or_list"),
        ],
    )
    chunks = chunk_pages([page])

    assert len(chunks) == 2
    assert chunks[0].metadata.chunk_type == "prose"
    assert chunks[1].metadata.chunk_type == "table_or_list"


def test_table_segments_use_the_tighter_table_size_budget_not_the_prose_one():
    # Real bug found by the spike: table-formatted text (key:value pairs) is
    # less token-dense than prose, so it needs a tighter char budget to stay
    # within the embedding model's token limit. A single segment sized
    # between the table and prose budgets must still get hard-split.
    long_row = " ".join(f"Field{i}: value{i}" for i in range(1, 60))
    assert TABLE_CHUNK_SIZE_CHARS < len(long_row) < CHUNK_SIZE_CHARS

    page = ExtractedPage(
        page_number=None, text="", segments=[Segment(text=long_row, heading_path=("Table Section",), chunk_type="table_or_list")]
    )
    chunks = chunk_pages([page])

    assert len(chunks) > 1, "a segment over the table budget must be split, even though it fits under the prose budget"
    for c in chunks:
        assert len(c.content) <= TABLE_CHUNK_SIZE_CHARS
        assert c.metadata.chunk_type == "table_or_list"


def test_chunk_indices_stay_sequential_across_a_plain_page_and_an_adaptive_page():
    plain_page = ExtractedPage(page_number=1, text="Short plain page text.")
    adaptive_page = ExtractedPage(
        page_number=None,
        text="",
        segments=[
            Segment(text="First adaptive sentence.", heading_path=("A",)),
            Segment(text="Second adaptive sentence.", heading_path=("B",)),
        ],
    )
    chunks = chunk_pages([plain_page, adaptive_page])

    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_a_tables_element_number_flows_into_chunk_metadata():
    page = ExtractedPage(
        page_number=None,
        text="",
        segments=[Segment(text="Col: value", heading_path=("Records",), chunk_type="table_or_list", element_number=3)],
    )
    chunks = chunk_pages([page])

    assert chunks[0].metadata.element_number == 3
    assert chunks[0].metadata.chunk_type == "table_or_list"


def test_two_different_tables_under_the_same_heading_never_merge_into_one_chunk():
    # 2026-08-20 fix: without element_number in the grouping key, two tables
    # back to back under the same heading (same heading_path, same
    # chunk_type) would blend into one chunk, corrupting "Table 3" into a
    # mix of table 3 and table 4's rows.
    page = ExtractedPage(
        page_number=None,
        text="",
        segments=[
            Segment(text="Table 3 row.", heading_path=("Records",), chunk_type="table_or_list", element_number=3),
            Segment(text="Table 4 row.", heading_path=("Records",), chunk_type="table_or_list", element_number=4),
        ],
    )
    chunks = chunk_pages([page])

    assert len(chunks) == 2
    assert chunks[0].metadata.element_number == 3
    assert chunks[1].metadata.element_number == 4


def test_a_segments_real_page_number_flows_into_the_chunks_top_level_page_number():
    # 2026-08-20: explicit DOCX page-break markers now give a real page
    # number, threaded the same way page_number already works for PDF —
    # a top-level TextChunk field, not just metadata.
    page = ExtractedPage(
        page_number=None,
        text="",
        segments=[Segment(text="Some content.", heading_path=("Section 1",), page_number=12)],
    )
    chunks = chunk_pages([page])

    assert chunks[0].page_number == 12


def test_a_page_number_change_is_a_hard_chunk_boundary_even_under_the_same_heading():
    page = ExtractedPage(
        page_number=None,
        text="",
        segments=[
            Segment(text="Content on page 3.", heading_path=("Section 1",), page_number=3),
            Segment(text="Content on page 4.", heading_path=("Section 1",), page_number=4),
        ],
    )
    chunks = chunk_pages([page])

    assert len(chunks) == 2
    assert chunks[0].page_number == 3
    assert chunks[1].page_number == 4


def test_a_docx_with_no_page_break_markers_still_gets_no_page_number():
    # Graceful fallback, unchanged: a segment with no real page data (the
    # default) must never be assigned a fabricated page.
    page = ExtractedPage(page_number=None, text="", segments=[Segment(text="Flat content, no page breaks in the source.")])
    chunks = chunk_pages([page])

    assert chunks[0].page_number is None


def test_overlap_and_chunk_size_constants_unchanged():
    # Not a behavior test — just guards the real, spike-verified numbers
    # (AI Architecture §2's 2026-08-19 addendum: 1000 chars keeps every real
    # chunk under all-MiniLM-L6-v2's actual 256-token limit; the old
    # 2800/400 pair assumed ~4 chars/token when this corpus actually
    # tokenizes at ~5-5.1) from silently drifting back toward the old,
    # wrong values.
    assert CHUNK_SIZE_CHARS == 1000
    assert CHUNK_OVERLAP_CHARS == 150
