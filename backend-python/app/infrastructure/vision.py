import base64
import io
import logging

from PIL import Image

from app.infrastructure.llm import complete

log = logging.getLogger(__name__)

# Spiked for real (2026-08-25, gpt-4o-mini; re-spiked 2026-11-21 on Gemini)
# against 3 real embedded images from a real fixture, using the same
# provider/model already in use for chat — no new dependency. Confirmed: a real diagram gets its actual step sequence
# reconstructed (OCR alone returns disconnected words); a real near-blank
# filler image correctly returns NO_CONTENT rather than fabricated content.
_NO_CONTENT = "NO_CONTENT"

_CAPTION_SYSTEM_PROMPT = (
    "You are describing an image embedded in a legal case document, for a search "
    "index a lawyer will later query. Describe factually and specifically what the "
    "image shows -- diagram structure, labeled steps/arrows, any text visible in it "
    "(reproduce numbers/dates/amounts exactly as shown), what it appears to "
    "illustrate. Do not speculate about legal conclusions. 2-4 sentences. If the "
    f"image is blank, near-blank, purely decorative, or has no discernible "
    f"meaningful content at all, respond with exactly: {_NO_CONTENT}"
)


# Formats Gemini decodes as-is, with the MIME type it must be labeled with.
# Anything else is re-encoded to PNG first. Found 2026-11-21: PDFs embed
# JPEG2000 (/JPXDecode) images, which Gemini rejects with 400 "Unable to
# process input image" — and every image used to be labeled image/png
# regardless of its real format.
_GEMINI_NATIVE = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
_NATIVE_MODES = frozenset({"RGB", "RGBA", "L", "LA"})


def _as_gemini_image(image_bytes: bytes) -> tuple[bytes, str]:
    with Image.open(io.BytesIO(image_bytes)) as img:
        if img.format in _GEMINI_NATIVE and img.mode in _NATIVE_MODES:
            return image_bytes, _GEMINI_NATIVE[img.format]
        if img.mode not in _NATIVE_MODES:
            img = img.convert("RGBA" if "A" in img.getbands() or img.mode in ("P", "PA") else "RGB")
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue(), "image/png"


class GeminiImageCaptioner:
    def caption(self, image_bytes: bytes) -> str | None:
        # A caption is an enrichment on top of OCR, never a requirement: any
        # failure (undecodable image, provider 4xx/5xx, every model's quota
        # exhausted) is logged and skipped so the Document still ingests with
        # its OCR text — one diagram must not fail a 60-page document.
        try:
            data, mime = _as_gemini_image(image_bytes)
            b64 = base64.b64encode(data).decode("ascii")
            text = complete(
                [
                    {"role": "system", "content": _CAPTION_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe this image."},
                            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        ],
                    },
                ]
            ).strip()
        except Exception as e:  # noqa: BLE001 — deliberate: see comment above
            log.warning("Image caption skipped (OCR text still used): %s", str(e)[:300])
            return None
        return None if not text or text == _NO_CONTENT else text
