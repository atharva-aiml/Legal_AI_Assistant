"""Captioner input handling + failure isolation — no real Gemini calls."""
import base64
import io

from PIL import Image

from app.infrastructure import vision
from app.infrastructure.vision import GeminiImageCaptioner, _as_gemini_image


def _encode(img: Image.Image, fmt: str) -> bytes:
    buf = io.BytesIO()
    img.save(buf, fmt)
    return buf.getvalue()


def _sent_format(data: bytes) -> str:
    return Image.open(io.BytesIO(data)).format


def test_png_and_jpeg_are_sent_unchanged_with_their_real_mime_type():
    png = _encode(Image.new("RGB", (40, 20), "white"), "PNG")
    jpg = _encode(Image.new("RGB", (40, 20), "white"), "JPEG")
    assert _as_gemini_image(png) == (png, "image/png")
    assert _as_gemini_image(jpg) == (jpg, "image/jpeg")


def test_jpeg2000_is_reencoded_to_png_regression():
    """2026-11-21: a PDF's embedded JPEG2000 diagram (labeled image/png) got
    Gemini 400 'Unable to process input image' and failed the whole Document."""
    jp2 = _encode(Image.new("LA", (40, 20), (0, 255)), "JPEG2000")
    data, mime = _as_gemini_image(jp2)
    assert mime == "image/png" and _sent_format(data) == "PNG"


def test_unsupported_formats_and_modes_are_reencoded_to_png():
    for img, fmt in [
        (Image.new("RGB", (40, 20), "white"), "TIFF"),
        (Image.new("RGB", (40, 20), "white"), "BMP"),
        (Image.new("CMYK", (40, 20)), "JPEG"),
        (Image.new("RGB", (40, 20), "white").convert("P"), "GIF"),
    ]:
        data, mime = _as_gemini_image(_encode(img, fmt))
        assert mime == "image/png" and _sent_format(data) == "PNG", fmt


def test_a_provider_error_skips_the_caption_instead_of_failing_ingestion(monkeypatch, caplog):
    def boom(_messages):
        raise RuntimeError("Error code: 400 - Unable to process input image")

    monkeypatch.setattr(vision, "complete", boom)
    with caplog.at_level("WARNING"):
        assert GeminiImageCaptioner().caption(_encode(Image.new("RGB", (40, 20), "white"), "PNG")) is None
    assert any("caption skipped" in r.message for r in caplog.records)


def test_undecodable_bytes_skip_the_caption(monkeypatch):
    monkeypatch.setattr(vision, "complete", lambda _m: "should not be called")
    assert GeminiImageCaptioner().caption(b"not an image") is None


def test_the_data_url_carries_the_converted_image_and_matching_mime(monkeypatch):
    seen = {}

    def fake(messages):
        seen["url"] = messages[1]["content"][1]["image_url"]["url"]
        return "A flowchart."

    monkeypatch.setattr(vision, "complete", fake)
    jp2 = _encode(Image.new("RGB", (40, 20), "white"), "JPEG2000")
    assert GeminiImageCaptioner().caption(jp2) == "A flowchart."
    prefix = "data:image/png;base64,"
    assert seen["url"].startswith(prefix)
    assert _sent_format(base64.b64decode(seen["url"][len(prefix):])) == "PNG"
