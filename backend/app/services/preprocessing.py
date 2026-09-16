"""
Document Preprocessing Service
Lightweight and conservative preprocessing pipeline for ID documents (Aadhaar, PAN, etc.):
- Aspect-ratio preserving resizing (only when dimensions are suboptimal for OCR)
- Preservation of natural document color channels
- Conservative CLAHE contrast enhancement in LAB color space (chromaticity preserved)
- Gentle edge-preserving noise reduction
- NO adaptive thresholding or forced binarization (prevents noise on colored ID cards)
- Graceful fallback to original image or PIL
"""
import cv2
import numpy as np
from PIL import Image, ImageEnhance
import logging, os
from pathlib import Path

logger = logging.getLogger(__name__)


def resize_aspect_ratio(image: np.ndarray, min_width: int = 1000, max_width: int = 1800) -> np.ndarray:
    """
    Resize image only if necessary to keep it within an optimal resolution band
    for OCR while strictly preserving the aspect ratio.
    """
    h, w = image.shape[:2]
    if w < min_width:
        scale = float(min_width) / float(w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    elif w > max_width:
        scale = float(max_width) / float(w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return image


def apply_conservative_clahe(image: np.ndarray, clip_limit: float = 1.5) -> np.ndarray:
    """
    Apply Contrast Limited Adaptive Histogram Equalization on the Luminance (L)
    channel in LAB color space. This enhances text contrast without altering
    chromaticity or creating harsh speckles on colored security backgrounds.
    """
    if len(image.shape) == 3 and image.shape[2] == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        merged = cv2.merge((cl, a, b))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    elif len(image.shape) == 2:
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
        return clahe.apply(image)
    return image


def apply_light_denoising(image: np.ndarray) -> np.ndarray:
    """
    Apply edge-preserving gentle filtering (bilateral filter) to smooth
    background sensor noise while keeping character boundaries crisp.
    """
    if len(image.shape) == 3 and image.shape[2] == 3:
        # Bilateral filter preserves high-frequency text edges while smoothing flat noise
        return cv2.bilateralFilter(image, d=5, sigmaColor=25, sigmaSpace=25)
    elif len(image.shape) == 2:
        return cv2.bilateralFilter(image, d=5, sigmaColor=25, sigmaSpace=25)
    return image


def preprocess_image(input_path: str) -> str:
    """
    Preprocess an ID document image with conservative, non-destructive enhancements.
    Preserves color and gradients, avoiding binarization/thresholding.
    Returns path to the preprocessed file.
    """
    try:
        img = cv2.imread(input_path)
        if img is None:
            logger.warning(f"cv2 could not read {input_path}, falling back to PIL")
            return _pil_preprocess(input_path)

        # 1. Aspect-ratio preserving resize (optimal range ~1000px - 1800px width)
        scaled = resize_aspect_ratio(img, min_width=1000, max_width=1800)

        # 2. Conservative contrast enhancement (CLAHE on luminance channel)
        contrast_enhanced = apply_conservative_clahe(scaled, clip_limit=1.5)

        # 3. Gentle edge-preserving smoothing
        denoised = apply_light_denoising(contrast_enhanced)

        # Save preprocessed image as PNG to avoid compression artifacts
        out_path = _output_path(input_path, "_prep.png")
        cv2.imwrite(out_path, denoised)
        logger.info(f"Conservative preprocessed image saved to {out_path}")
        return out_path

    except Exception as e:
        logger.error(f"Preprocessing failed for {input_path}: {e}")
        return input_path  # Fall back to original image on failure


def _pil_preprocess(input_path: str) -> str:
    """Fallback conservative preprocessing using Pillow."""
    try:
        img = Image.open(input_path)
        # Keep RGB mode; gently enhance contrast
        if img.mode != "RGB":
            img = img.convert("RGB")
        enhancer = ImageEnhance.Contrast(img)
        enhanced = enhancer.enhance(1.2)
        out_path = _output_path(input_path, "_prep.png")
        enhanced.save(out_path, format="PNG")
        return out_path
    except Exception as e:
        logger.error(f"PIL preprocessing failed: {e}")
        return input_path


def _output_path(input_path: str, suffix: str) -> str:
    p = Path(input_path)
    return str(p.parent / (p.stem + suffix))
