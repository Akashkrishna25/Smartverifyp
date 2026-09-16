"""
OCR Service
Primary OCR Engine: PaddleOCR (returns text, bounding boxes, and per-token confidence).
Fallback OCR Engine: EasyOCR (triggered only if PaddleOCR fails or yields empty text).

Maintains complete backward compatibility:
- extract_text(file_path) -> returns OCRText (a str subclass with .tokens and .engine attributes,
  plus dictionary access for {"text", "tokens", "engine"}).
- extract_document(file_path) -> returns dict {"text": ..., "tokens": [...], "engine": ...}
"""
import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image

# Ensure PaddleOCR flags on Windows CPU prevent oneDNN PIR executor conflicts
os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "False")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ.setdefault("FLAGS_use_onednn", "0")

# Pre-import torch so torch and paddle runtime DLLs initialize cleanly on Windows
try:
    import torch
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Lazy-loaded engine instances
_paddleocr_engine = None
_easyocr_reader = None


class OCRText(str):
    """
    Backward-compatible string subclass that carries structured OCR metadata
    while behaving identically to a standard Python string.
    Supports attribute access (.tokens, .engine) and dict access (['tokens'], ['engine'], ['text']).
    """
    tokens: List[Dict[str, Any]]
    engine: str

    def __new__(cls, text: str, tokens: Optional[List[Dict[str, Any]]] = None, engine: str = "unknown"):
        instance = super().__new__(cls, text)
        instance.tokens = tokens if tokens is not None else []
        instance.engine = engine
        return instance

    def __getitem__(self, item):
        if item == "text":
            return str(self)
        elif item == "tokens":
            return self.tokens
        elif item == "engine":
            return self.engine
        return super().__getitem__(item)

    def get(self, key: str, default: Any = None) -> Any:
        if key == "text":
            return str(self)
        elif key == "tokens":
            return self.tokens
        elif key == "engine":
            return self.engine
        return default

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": str(self),
            "tokens": self.tokens,
            "engine": self.engine,
        }


def _get_paddleocr():
    """Lazy initialization of PaddleOCR."""
    global _paddleocr_engine
    if _paddleocr_engine is None:
        try:
            from paddleocr import PaddleOCR
            # Fast, high-accuracy settings on CPU (without heavy unwarping)
            _paddleocr_engine = PaddleOCR(
                lang="en",
                use_doc_unwarping=False,
                use_doc_orientation_classify=False
            )
            logger.info("PaddleOCR engine initialised successfully as primary OCR")
        except Exception as e:
            logger.warning(f"PaddleOCR initialisation failed: {e}")
            _paddleocr_engine = None
    return _paddleocr_engine


def _get_easyocr():
    """Lazy initialization of EasyOCR reader (fallback)."""
    global _easyocr_reader
    if _easyocr_reader is None:
        try:
            import easyocr
            _easyocr_reader = easyocr.Reader(["en"], gpu=False)
            logger.info("EasyOCR reader initialised as fallback OCR")
        except Exception as e:
            logger.warning(f"EasyOCR initialisation failed: {e}")
            _easyocr_reader = None
    return _easyocr_reader


def _extract_with_paddle(image_path: str) -> Optional[Dict[str, Any]]:
    """Attempt extraction using primary PaddleOCR engine."""
    engine = _get_paddleocr()
    if engine is None:
        return None

    try:
        import cv2
        img = cv2.imread(image_path)
        if img is None:
            return None

        # Execute prediction
        predict_gen = engine.predict(img)
        results = list(predict_gen)

        if not results or len(results) == 0:
            return None

        res = results[0]
        rec_texts = res.get("rec_texts", [])
        rec_scores = res.get("rec_scores", [])
        dt_polys = res.get("dt_polys", [])

        tokens: List[Dict[str, Any]] = []
        text_lines: List[str] = []

        for i in range(len(rec_texts)):
            t = str(rec_texts[i]).strip()
            s = float(rec_scores[i]) if i < len(rec_scores) else 0.0
            poly = dt_polys[i].tolist() if i < len(dt_polys) and hasattr(dt_polys[i], "tolist") else []

            if t:
                text_lines.append(t)
                tokens.append({
                    "text": t,
                    "confidence": round(s, 4),
                    "bbox": poly
                })

        full_text = "\n".join(text_lines).strip()
        # Verify meaningful text was extracted (at least 3 non-whitespace characters)
        if len(full_text) < 3:
            return None

        return {
            "text": full_text,
            "tokens": tokens,
            "engine": "paddleocr"
        }
    except Exception as e:
        logger.warning(f"PaddleOCR extraction failed on {image_path}: {e}")
        return None


def _extract_with_easyocr(image_path: str) -> Dict[str, Any]:
    """Fallback extraction using EasyOCR."""
    reader = _get_easyocr()
    if reader is None:
        logger.error("EasyOCR reader unavailable during fallback")
        return {"text": "", "tokens": [], "engine": "none"}

    try:
        results = reader.readtext(image_path, detail=1, paragraph=False)
        tokens: List[Dict[str, Any]] = []
        text_lines: List[str] = []

        for item in results:
            bbox, text, conf = item
            clean_text = str(text).strip()
            if clean_text:
                text_lines.append(clean_text)
                bbox_list = [list(map(int, pt)) for pt in bbox] if hasattr(bbox, "__iter__") else []
                tokens.append({
                    "text": clean_text,
                    "confidence": round(float(conf), 4),
                    "bbox": bbox_list
                })

        full_text = "\n".join(text_lines).strip()
        logger.info(f"EasyOCR fallback extracted {len(tokens)} tokens from {image_path}")
        return {
            "text": full_text,
            "tokens": tokens,
            "engine": "easyocr"
        }
    except Exception as e:
        logger.error(f"EasyOCR fallback also failed for {image_path}: {e}")
        return {"text": "", "tokens": [], "engine": "failed"}


def extract_document(image_path: str) -> Dict[str, Any]:
    """
    Extract structured text and bounding box tokens from an image.
    Tries PaddleOCR as primary engine. If it fails or returns empty text,
    falls back to EasyOCR.
    Returns:
        {
            "text": str,
            "tokens": [{"text": str, "confidence": float, "bbox": list}],
            "engine": "paddleocr" | "easyocr"
        }
    """
    # 1. Primary: PaddleOCR
    res = _extract_with_paddle(image_path)
    if res and res.get("text"):
        logger.info(f"PaddleOCR extracted {len(res.get('tokens', []))} tokens from {image_path}")
        return res

    # 2. Fallback: EasyOCR (only if PaddleOCR failed or produced empty text)
    logger.warning(f"Primary PaddleOCR produced no usable text for {image_path}. Invoking EasyOCR fallback.")
    return _extract_with_easyocr(image_path)


def extract_text_from_image(image_path: str) -> OCRText:
    """
    Extract text line-by-line using PaddleOCR with EasyOCR fallback.
    Returns backward-compatible OCRText string with metadata.
    """
    doc = extract_document(image_path)
    return OCRText(doc["text"], tokens=doc["tokens"], engine=doc["engine"])


def extract_text_from_pdf(pdf_path: str) -> OCRText:
    """Extract text from PDF pages (converts each page to image first)."""
    all_texts = []
    all_tokens = []
    engines_used = set()

    try:
        import pdf2image
        pages = pdf2image.convert_from_path(pdf_path, dpi=200)
        for i, page in enumerate(pages):
            tmp_path = pdf_path + f"_page_{i}.png"
            page.save(tmp_path, "PNG")
            doc = extract_document(tmp_path)
            if doc["text"]:
                all_texts.append(doc["text"])
                all_tokens.extend(doc["tokens"])
                engines_used.add(doc["engine"])
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        combined_text = "\n".join(all_texts).strip()
        engine_str = "/".join(sorted(engines_used)) if engines_used else "none"
        return OCRText(combined_text, tokens=all_tokens, engine=engine_str)

    except Exception as e:
        logger.error(f"PDF image conversion failed for {pdf_path}: {e}")
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                plain_text = "\n".join(p.extract_text() or "" for p in pdf.pages).strip()
                return OCRText(plain_text, tokens=[], engine="pdfplumber")
        except Exception as e2:
            logger.error(f"pdfplumber also failed: {e2}")
            return OCRText("", tokens=[], engine="failed")


def extract_text(file_path: str) -> OCRText:
    """
    Route file to the appropriate extractor.
    Returns backward-compatible OCRText (usable as plain str or structured dict).
    """
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    else:
        return extract_text_from_image(file_path)
