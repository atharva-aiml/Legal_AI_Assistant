from app.domain.chunk import CHUNK_OVERLAP_CHARS, CHUNK_SIZE_CHARS, ExtractedPage, chunk_pages


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


def test_overlap_and_chunk_size_constants_unchanged():
    # Not a behavior test — just guards the AI Architecture §2 numbers
    # (~700 tokens / ~100-token overlap, approximated in characters) from
    # silently drifting.
    assert CHUNK_SIZE_CHARS == 2800
    assert CHUNK_OVERLAP_CHARS == 400
