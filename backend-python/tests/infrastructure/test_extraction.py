from app.infrastructure.extraction import _combine_ocr_and_caption


def test_both_present_combines_ocr_exactness_with_caption_structure():
    result = _combine_ocr_and_caption("Water enters MIC storage system", "A flowchart showing a 6-step process.")
    assert result == "Water enters MIC storage system Visual description: A flowchart showing a 6-step process."


def test_only_caption_present_uses_caption_alone():
    assert _combine_ocr_and_caption("", "A flowchart with no legible text.") == "A flowchart with no legible text."


def test_only_ocr_present_uses_ocr_alone():
    assert _combine_ocr_and_caption("Gas release Victim claims", None) == "Gas release Victim claims"


def test_neither_present_is_empty_so_the_segment_gets_dropped():
    assert _combine_ocr_and_caption("", None) == ""
