"""Real-engine OCR tests (RapidOCR, ONNX). Images are generated in-test so
the expected text is known exactly."""
import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.application.ports import ImageCaptioner
from app.infrastructure.extraction import DocumentTextExtractor, _ocr_text

TEXT = "Notice of Hearing Docket 88213"


def _rendered(size=(900, 160), text=TEXT) -> Image.Image:
    img = Image.new("RGB", size, "white")
    ImageDraw.Draw(img).text((30, 50), text, fill="black", font=ImageFont.load_default(size=48))
    return img


def _encode(img: Image.Image, fmt: str, **kw) -> bytes:
    buf = io.BytesIO()
    img.save(buf, fmt, **kw)
    return buf.getvalue()


def _words(s: str) -> set[str]:
    return set(s.lower().replace(",", " ").split())


@pytest.mark.parametrize(
    "label,data",
    [
        ("rgb png", lambda: _encode(_rendered(), "PNG")),
        ("grayscale png", lambda: _encode(_rendered().convert("L"), "PNG")),
        ("bilevel tiff g4", lambda: _encode(_rendered().convert("1"), "TIFF", compression="group4")),
        ("jpeg", lambda: _encode(_rendered(), "JPEG")),
        ("webp", lambda: _encode(_rendered(), "WEBP")),
        # Regressions from the 2026-11-21 spike: RapidOCR returned "" for these
        # two until extraction.py normalized their color modes (EasyOCR read them).
        ("cmyk jpeg", lambda: _encode(_rendered().convert("CMYK"), "JPEG")),
        ("palette gif", lambda: _encode(_rendered().convert("P"), "GIF")),
        ("transparent png", lambda: _encode(_transparent(), "PNG")),
    ],
)
def test_every_supported_color_mode_reads_the_same_text(label, data):
    assert {"notice", "hearing", "docket", "88213"} <= _words(_ocr_text(data())), label


def _transparent() -> Image.Image:
    img = Image.new("RGBA", (900, 160), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((30, 50), TEXT, fill=(0, 0, 0, 255), font=ImageFont.load_default(size=48))
    return img


def test_a_full_page_scan_does_not_crash_the_process():
    """EasyOCR (the previous engine) died with a native access violation —
    taking the whole backend process with it — on page-sized images like a
    150-dpi A4 scan. A full page must simply return its text."""
    page = Image.new("L", (1241, 1754), 255)
    draw = ImageDraw.Draw(page)
    font = ImageFont.load_default(size=28)
    for i in range(30):
        draw.text((90, 90 + i * 52), f"Clause {i + 1}. The lessee shall pay rent of Rs. {85000 + i} monthly.", fill=0, font=font)

    text = _ocr_text(_encode(page, "JPEG", quality=60))

    assert "lessee" in text.lower()
    assert "clause 30" in text.lower()


def test_a_blank_image_yields_empty_text_not_an_error():
    assert _ocr_text(_encode(Image.new("RGB", (1, 1), "white"), "PNG")) == ""


def test_undecodable_bytes_raise_so_ingestion_marks_the_document_failed():
    with pytest.raises(Exception):
        _ocr_text(b"not an image at all")


class _NoCaption(ImageCaptioner):
    def caption(self, image_bytes: bytes) -> str | None:
        return None


def test_image_upload_extraction_path_returns_ocr_text_on_page_one():
    pages = DocumentTextExtractor(_NoCaption()).extract(_encode(_rendered(), "PNG"), "image/png")

    assert len(pages) == 1 and pages[0].page_number == 1
    assert "88213" in pages[0].text
