"""Parse statistical communique image pages using PaddleOCR."""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Callable
from urllib.parse import urljoin

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

_SKIP_IMAGE_KEYWORDS = (
    "guohui",
    "qrcode",
    "beian",
    "red.png",
    "12377",
    "esdhf",
    "slh_icon",
)

_OCR_ENGINE = None


def _get_ocr():
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        from paddleocr import PaddleOCR

        _OCR_ENGINE = PaddleOCR(
            lang="ch",
            text_detection_model_name="PP-OCRv5_mobile_det",
            text_recognition_model_name="PP-OCRv5_mobile_rec",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    return _OCR_ENGINE


def extract_content_image_urls(html: str, base_url: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r'<img[^>]+src="([^"]+)"', html, flags=re.I):
        src = match.group(1).strip()
        if not src.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        if any(keyword in src for keyword in _SKIP_IMAGE_KEYWORDS):
            continue
        full_url = urljoin(base_url, src)
        if full_url in seen:
            continue
        seen.add(full_url)
        urls.append(full_url)
    return urls


def page_needs_ocr(html: str, text: str) -> bool:
    if not extract_content_image_urls(html, ""):
        return False
    metric_keywords = ("地区生产总值", "人均可支配收入", "常住人口", "人均GDP", "人均地区生产总值")
    return not any(keyword in text for keyword in metric_keywords)


def metrics_need_ocr(metrics: dict[str, float]) -> bool:
    return not {"gdp_per_capita", "disposable_income", "population"}.issubset(metrics)


def ocr_image_bytes(image_bytes: bytes) -> str:
    ocr = _get_ocr()
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as handle:
        handle.write(image_bytes)
        temp_path = handle.name
    try:
        result = ocr.predict(temp_path)
    finally:
        os.unlink(temp_path)

    if not result:
        return ""
    rec_texts = result[0].get("rec_texts", []) if isinstance(result[0], dict) else []
    return " ".join(rec_texts)


def ocr_html_images(
    html: str,
    page_url: str,
    fetch_bytes: Callable[[str], tuple[bytes, str]],
) -> str:
    chunks: list[str] = []
    for image_url in extract_content_image_urls(html, page_url):
        try:
            image_bytes, _ = fetch_bytes(image_url)
        except Exception:
            continue
        text = ocr_image_bytes(image_bytes)
        if text.strip():
            chunks.append(text)
    return " ".join(chunks)


def normalize_ocr_text(text: str) -> str:
    text = re.sub(r"(\d)，(\d)", r"\1.\2", text)
    return re.sub(r"\s+", " ", text)
