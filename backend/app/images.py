"""Convert uploaded PDFs/images into base64 data-URLs for Groq vision."""

from __future__ import annotations

import base64
import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

# qwen/qwen3.6-27b accepts at most 3 images per request (Groq returns 400 above that).
MAX_PAGES = 3
MAX_IMAGE_EDGE = 2400

logger = logging.getLogger(__name__)


class UnreadableDocumentError(Exception):
    """Raised when a file cannot be opened or rendered."""


@dataclass(frozen=True)
class PreparedImages:
    data_urls: list[str]
    metas: list[dict[str, Any]]
    pages_total: int
    pages_sent: int

    @property
    def truncated(self) -> bool:
        return self.pages_total > self.pages_sent


def assert_file_looks_valid(file_path: Path, content_type: str) -> None:
    """Reject obviously corrupt/mismatched files before calling the vision model."""
    suffix = file_path.suffix.lower()
    try:
        head = file_path.read_bytes()[:16]
    except OSError as exc:
        raise UnreadableDocumentError(f"Could not read file: {exc}") from exc

    if not head:
        raise UnreadableDocumentError("Uploaded file is empty")

    is_pdf = content_type == "application/pdf" or suffix == ".pdf"
    is_png = content_type == "image/png" or suffix == ".png"
    is_jpeg = content_type in {"image/jpeg", "image/jpg"} or suffix in {".jpg", ".jpeg"}

    if is_pdf and not head.startswith(b"%PDF"):
        raise UnreadableDocumentError("File extension is PDF but content is not a valid PDF")
    if is_png and not head.startswith(b"\x89PNG\r\n\x1a\n"):
        raise UnreadableDocumentError("File extension is PNG but content is not a valid PNG")
    if is_jpeg and not head.startswith(b"\xff\xd8\xff"):
        raise UnreadableDocumentError("File extension is JPEG but content is not a valid JPEG")


def file_to_image_data_urls(file_path: Path, content_type: str) -> PreparedImages:
    """Return data-URLs plus per-image metadata (width/height/format)."""
    suffix = file_path.suffix.lower()
    is_pdf = content_type == "application/pdf" or suffix == ".pdf"

    try:
        if is_pdf:
            images, pages_total = _pdf_to_pil_images(file_path)
        else:
            images = [_open_image(file_path)]
            pages_total = 1
    except UnreadableDocumentError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise UnreadableDocumentError(f"Could not read document: {exc}") from exc

    if not images:
        raise UnreadableDocumentError("Document produced no readable pages")

    urls: list[str] = []
    metas: list[dict[str, Any]] = []
    for img in images[:MAX_PAGES]:
        url, meta = _pil_to_data_url(img)
        urls.append(url)
        metas.append(meta)

    prepared = PreparedImages(
        data_urls=urls,
        metas=metas,
        pages_total=pages_total,
        pages_sent=len(urls),
    )
    if prepared.truncated:
        logger.warning(
            "Document has %s pages; only first %s sent to vision model",
            prepared.pages_total,
            prepared.pages_sent,
        )
    return prepared


def _open_image(path: Path) -> Image.Image:
    try:
        img = Image.open(path)
        img.load()
    except Exception as exc:  # noqa: BLE001
        raise UnreadableDocumentError(f"Unreadable image file: {exc}") from exc
    return img.convert("RGB")


def _pdf_to_pil_images(path: Path) -> tuple[list[Image.Image], int]:
    """Render PDF pages with PyMuPDF (no Poppler dependency on Windows)."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise UnreadableDocumentError(
            "PDF support requires pymupdf. Run: pip install pymupdf"
        ) from exc

    try:
        doc = fitz.open(path)
    except Exception as exc:  # noqa: BLE001
        raise UnreadableDocumentError(f"Unreadable PDF: {exc}") from exc

    images: list[Image.Image] = []
    try:
        pages_total = len(doc)
        if pages_total == 0:
            return [], 0
        page_count = min(pages_total, MAX_PAGES)
        # ~216 DPI equivalent via matrix scale (PDF default user space is 72 DPI)
        matrix = fitz.Matrix(3.0, 3.0)
        for i in range(page_count):
            pix = doc[i].get_pixmap(matrix=matrix, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            images.append(img)
    finally:
        doc.close()
    return images, pages_total


def render_preview_png(file_path: Path, content_type: str) -> bytes:
    """Rasterize the first page/image to PNG for reliable UI preview."""
    suffix = file_path.suffix.lower()
    is_pdf = content_type == "application/pdf" or suffix == ".pdf"
    try:
        if is_pdf:
            images, _total = _pdf_to_pil_images(file_path)
        else:
            images = [_open_image(file_path)]
    except UnreadableDocumentError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise UnreadableDocumentError(f"Could not render preview: {exc}") from exc

    if not images:
        raise UnreadableDocumentError("Document produced no readable pages")

    img = _downscale(images[0].convert("RGB"))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _pil_to_data_url(img: Image.Image) -> tuple[str, dict[str, Any]]:
    img = _downscale(img.convert("RGB"))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    meta = {"width": img.width, "height": img.height, "format": "png"}
    return f"data:image/png;base64,{b64}", meta


def _downscale(img: Image.Image) -> Image.Image:
    w, h = img.size
    longest = max(w, h)
    if longest <= MAX_IMAGE_EDGE:
        return img
    scale = MAX_IMAGE_EDGE / longest
    return img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
