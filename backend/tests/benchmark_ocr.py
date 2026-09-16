"""
Standalone OCR Benchmark System for SmartVerify
Compares OCR Engines (EasyOCR, PaddleOCR, Tesseract) across multiple preprocessing pipelines
on real Aadhaar and PAN documents.

Does NOT modify or interfere with production services.
"""
import os
import sys

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Configure environment flags for PaddleOCR / PaddlePaddle stability on Windows CPU
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "False"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
os.environ["FLAGS_use_onednn"] = "0"

# Pre-import torch so torch and paddle DLLs initialize safely
try:
    import torch
except ImportError:
    pass

import time
import json
import csv
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ocr_benchmark")

# Add backend directory to sys.path so we can import parsers
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Import existing regex parsers to evaluate downstream extraction compatibility
try:
    from app.services.parsers.aadhaar_parser import parse_aadhaar
    from app.services.parsers.pan_parser import parse_pan
except ImportError:
    logger.warning("Could not import production parsers.")
    parse_aadhaar = None
    parse_pan = None


# =====================================================================
# 1. PREPROCESSING CONFIGURATIONS
# =====================================================================

def prep_original(image: np.ndarray) -> np.ndarray:
    """1. Original unmodified image."""
    return image.copy()

def prep_light_denoise(image: np.ndarray) -> np.ndarray:
    """2. Light denoising preserving text edges."""
    if len(image.shape) == 3:
        return cv2.fastNlMeansDenoisingColored(image, None, h=5, hColor=5, templateWindowSize=7, searchWindowSize=21)
    else:
        return cv2.fastNlMeansDenoising(image, None, h=5, templateWindowSize=7, searchWindowSize=21)

def prep_clahe(image: np.ndarray) -> np.ndarray:
    """3. CLAHE Contrast Enhancement without destroying color information."""
    if len(image.shape) == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        merged = cv2.merge((cl, a, b))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    else:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(image)

def prep_grayscale(image: np.ndarray) -> np.ndarray:
    """4. Standard Grayscale conversion."""
    if len(image.shape) == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image.copy()

def prep_threshold(image: np.ndarray) -> np.ndarray:
    """5. Otsu Thresholding / Binarization."""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

def prep_production_pipeline(image: np.ndarray) -> np.ndarray:
    """6. Current production preprocessing (upscale + clahe + denoise + sharpen + adaptiveThreshold + deskew)."""
    try:
        img = image.copy()
        h, w = img.shape[:2]
        if w < 1500:
            scale = 1500.0 / w
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        denoised = cv2.fastNlMeansDenoising(enhanced, h=10)
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
        sharpened = cv2.filter2D(denoised, -1, kernel)
        thresh = cv2.adaptiveThreshold(
            sharpened, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        return thresh
    except Exception as e:
        logger.error(f"Production pipeline failed: {e}")
        return image.copy()

PREPROCESSING_CONFIGS = {
    "original": prep_original,
    "light_denoise": prep_light_denoise,
    "clahe": prep_clahe,
    "grayscale": prep_grayscale,
    "threshold": prep_threshold,
    "production_prep": prep_production_pipeline,
}


# =====================================================================
# 2. OCR ENGINES WRAPPERS
# =====================================================================

class EasyOCREngine:
    def __init__(self):
        self.name = "EasyOCR"
        self.reader = None
        self.available = False
        self.error_msg = ""
        try:
            import easyocr
            self.reader = easyocr.Reader(["en"], gpu=False)
            self.available = True
        except Exception as e:
            self.error_msg = str(e)
            logger.warning(f"EasyOCR initialization failed: {e}")

    def run(self, image: np.ndarray) -> Dict[str, Any]:
        if not self.available:
            return {"error": f"EasyOCR unavailable: {self.error_msg}", "text": "", "conf": 0.0, "boxes": 0, "time_ms": 0}
        
        t0 = time.perf_counter()
        try:
            results = self.reader.readtext(image, detail=1, paragraph=False)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            texts = []
            confs = []
            boxes_data = []

            for item in results:
                bbox, text, conf = item
                text_clean = text.strip()
                if text_clean:
                    texts.append(text_clean)
                    confs.append(float(conf))
                    boxes_data.append({
                        "text": text_clean,
                        "confidence": round(float(conf), 4),
                        "bbox": [list(map(int, pt)) for pt in bbox]
                    })

            avg_conf = float(np.mean(confs)) if confs else 0.0
            full_text = "\n".join(texts)

            return {
                "text": full_text,
                "conf": round(avg_conf, 4),
                "boxes": len(boxes_data),
                "time_ms": round(elapsed_ms, 2),
                "details": boxes_data,
                "error": None
            }
        except Exception as e:
            return {"error": str(e), "text": "", "conf": 0.0, "boxes": 0, "time_ms": round((time.perf_counter() - t0)*1000, 2)}


class PaddleOCREngine:
    def __init__(self):
        self.name = "PaddleOCR"
        self.ocr = None
        self.available = False
        self.error_msg = ""
        try:
            from paddleocr import PaddleOCR
            # Fast, high-accuracy configuration (without heavy unwarping)
            self.ocr = PaddleOCR(lang="en", use_doc_unwarping=False, use_doc_orientation_classify=False)
            self.available = True
        except Exception as e:
            self.error_msg = str(e)
            logger.warning(f"PaddleOCR initialization failed: {e}")

    def run(self, image: np.ndarray) -> Dict[str, Any]:
        if not self.available:
            return {"error": f"PaddleOCR unavailable: {self.error_msg}", "text": "", "conf": 0.0, "boxes": 0, "time_ms": 0}

        t0 = time.perf_counter()
        try:
            if len(image.shape) == 2:
                img_input = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            else:
                img_input = image

            predict_generator = self.ocr.predict(img_input)
            results = list(predict_generator)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            texts = []
            confs = []
            boxes_data = []

            if results and len(results) > 0:
                res = results[0]
                rec_texts = res.get("rec_texts", [])
                rec_scores = res.get("rec_scores", [])
                dt_polys = res.get("dt_polys", [])

                for i in range(len(rec_texts)):
                    t = str(rec_texts[i]).strip()
                    s = float(rec_scores[i]) if i < len(rec_scores) else 0.0
                    poly = dt_polys[i].tolist() if i < len(dt_polys) and hasattr(dt_polys[i], "tolist") else []
                    if t:
                        texts.append(t)
                        confs.append(s)
                        boxes_data.append({
                            "text": t,
                            "confidence": round(s, 4),
                            "bbox": poly
                        })

            avg_conf = float(np.mean(confs)) if confs else 0.0
            full_text = "\n".join(texts)

            return {
                "text": full_text,
                "conf": round(avg_conf, 4),
                "boxes": len(boxes_data),
                "time_ms": round(elapsed_ms, 2),
                "details": boxes_data,
                "error": None
            }
        except Exception as e:
            return {"error": str(e), "text": "", "conf": 0.0, "boxes": 0, "time_ms": round((time.perf_counter() - t0)*1000, 2)}


class TesseractEngine:
    def __init__(self):
        self.name = "Tesseract"
        self.available = False
        self.version = ""
        self.path = ""
        self.error_msg = ""
        self._detect_and_configure()

    def _detect_and_configure(self):
        try:
            import pytesseract
            self.pytesseract = pytesseract
            
            cmd = shutil.which("tesseract")
            standard_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
                os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
            ]
            
            if cmd:
                self.path = cmd
            else:
                for p in standard_paths:
                    if os.path.exists(p):
                        self.path = p
                        break

            if self.path:
                self.pytesseract.pytesseract.tesseract_cmd = self.path
                self.version = str(self.pytesseract.get_tesseract_version())
                self.available = True
                logger.info(f"Tesseract {self.version} configured from {self.path}")
            else:
                self.error_msg = (
                    "Tesseract binary NOT found on Windows. "
                    "Download and install UB-Mannheim Windows binary from: "
                    "https://github.com/UB-Mannheim/tesseract/wiki or add C:\\Program Files\\Tesseract-OCR to PATH."
                )
                logger.warning(self.error_msg)
        except Exception as e:
            self.error_msg = f"Tesseract configuration failed: {e}"
            logger.warning(self.error_msg)

    def run(self, image: np.ndarray) -> Dict[str, Any]:
        if not self.available:
            return {"error": f"Tesseract unavailable: {self.error_msg}", "text": "", "conf": 0.0, "boxes": 0, "time_ms": 0}

        t0 = time.perf_counter()
        try:
            from pytesseract import Output
            if len(image.shape) == 2:
                pil_img = Image.fromarray(image)
            else:
                pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

            data = self.pytesseract.image_to_data(pil_img, lang="eng", output_type=Output.DICT)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            words = []
            confs = []
            boxes_data = []

            n_boxes = len(data["level"])
            for i in range(n_boxes):
                text = data["text"][i].strip()
                conf = float(data["conf"][i])
                if text and conf > 0:
                    words.append(text)
                    confs.append(conf / 100.0)
                    boxes_data.append({
                        "text": text,
                        "confidence": round(conf / 100.0, 4),
                        "bbox": [data["left"][i], data["top"][i], data["width"][i], data["height"][i]]
                    })

            full_text = self.pytesseract.image_to_string(pil_img, lang="eng").strip()
            avg_conf = float(np.mean(confs)) if confs else 0.0

            return {
                "text": full_text,
                "conf": round(avg_conf, 4),
                "boxes": len(boxes_data),
                "time_ms": round(elapsed_ms, 2),
                "details": boxes_data,
                "error": None
            }
        except Exception as e:
            return {"error": str(e), "text": "", "conf": 0.0, "boxes": 0, "time_ms": round((time.perf_counter() - t0)*1000, 2)}


# =====================================================================
# 3. FIELD EXTRACTION & EVALUATION
# =====================================================================

import re

def detect_document_type(text: str) -> str:
    """Detect whether text represents an Aadhaar or PAN card."""
    text_upper = text.upper()
    pan_indicators = ["INCOME TAX", "PERMANENT ACCOUNT NUMBER", "FATHER'S NAME", "GOVT. OF INDIA"]
    aadhaar_indicators = ["AADHAAR", "UIDAI", "UNIQUE IDENTIFICATION", "MERA AADHAAR", "ENROLLMENT"]

    pan_score = sum(1 for ind in pan_indicators if ind in text_upper)
    aadhaar_score = sum(1 for ind in aadhaar_indicators if ind in text_upper)

    if re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", text_upper):
        pan_score += 3
    if re.search(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", text):
        aadhaar_score += 3

    if pan_score > aadhaar_score:
        return "pan"
    elif aadhaar_score > pan_score:
        return "aadhaar"
    return "unknown"


def extract_fields_from_ocr(text: str, doc_type: str) -> Dict[str, Any]:
    """Extract fields using document parsers and regex patterns."""
    extracted = {
        "id_number": None,
        "is_valid_id": False,
        "name": None,
        "dob": None,
        "father_name": None,
        "gender": None,
    }
    if not text:
        return extracted

    if doc_type == "pan":
        # 1. PAN Number
        m = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text.upper())
        if m:
            extracted["id_number"] = m.group(1)
            extracted["is_valid_id"] = True
        
        # 2. Parsed via pan_parser
        if parse_pan:
            parsed = parse_pan(text)
            if parsed.get("applicant_name", {}).get("value"):
                extracted["name"] = parsed["applicant_name"]["value"]
            if parsed.get("dob", {}).get("value"):
                extracted["dob"] = parsed["dob"]["value"]
            if parsed.get("father_name", {}).get("value"):
                extracted["father_name"] = parsed["father_name"]["value"]
        
        # Fallback for DOB
        if not extracted["dob"]:
            m_dob = re.search(r"\b(\d{2}[/\-]\d{2}[/\-]\d{4})\b", text)
            if m_dob:
                extracted["dob"] = m_dob.group(1).replace("-", "/")

    elif doc_type == "aadhaar":
        # 1. Aadhaar Number (12 digits)
        m = re.search(r"\b(\d{4}[\s-]?\d{4}[\s-]?\d{4})\b", text)
        if m:
            num = re.sub(r"[\s-]", "", m.group(1))
            if len(num) == 12:
                extracted["id_number"] = num
                extracted["is_valid_id"] = True

        # 2. Parsed via aadhaar_parser
        if parse_aadhaar:
            parsed = parse_aadhaar(text)
            if parsed.get("applicant_name", {}).get("value"):
                extracted["name"] = parsed["applicant_name"]["value"]
            if parsed.get("dob", {}).get("value"):
                extracted["dob"] = parsed["dob"]["value"]
            if parsed.get("gender", {}).get("value"):
                extracted["gender"] = parsed["gender"]["value"]

        # Fallback for DOB
        if not extracted["dob"]:
            m_dob = re.search(r"(?:dob|birth)[:\s,]*(\d{2}[/,\-]\d{2}[/,\-]\d{4}|\d{4})", text, re.I)
            if not m_dob:
                m_dob = re.search(r"\b(\d{2}[/,\-]\d{2}[/,\-]\d{4})\b", text)
            if m_dob:
                extracted["dob"] = m_dob.group(1).replace(",", "/").replace("-", "/")

        # Fallback for Gender
        if not extracted["gender"]:
            m_gen = re.search(r"\b(Female|Male|Transgender)\b", text, re.I)
            if m_gen:
                extracted["gender"] = m_gen.group(1).title()

    return extracted


# =====================================================================
# 4. BENCHMARK RUNNER
# =====================================================================

def run_benchmark(
    image_paths: List[str],
    output_dir: str,
    ground_truth: Optional[Dict[str, Dict[str, Any]]] = None
) -> Tuple[List[Dict[str, Any]], str, str]:
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "ocr_benchmark_results.csv")
    json_path = os.path.join(output_dir, "ocr_benchmark_results.json")

    print("\n" + "="*85)
    print("INITIALIZING OCR ENGINES FOR BENCHMARK")
    print("="*85)
    engines = [
        EasyOCREngine(),
        PaddleOCREngine(),
        TesseractEngine()
    ]

    for e in engines:
        status_text = "READY" if e.available else f"UNAVAILABLE ({e.error_msg})"
        print(f"  - {e.name:<12}: {status_text}")

    print("\n" + "="*85)
    print("RUNNING BENCHMARK MATRIX")
    print("="*85)
    print(f"Test Images : {len(image_paths)}")
    print(f"Engines     : {[e.name for e in engines if e.available]}")
    print(f"Pipelines   : {list(PREPROCESSING_CONFIGS.keys())}")
    print("="*85 + "\n")

    all_results = []
    total_runs = len(image_paths) * len(engines) * len(PREPROCESSING_CONFIGS)
    run_idx = 0

    for img_path in image_paths:
        fname = os.path.basename(img_path)
        img_bgr = cv2.imread(img_path)
        if img_bgr is None:
            logger.error(f"Could not read image: {img_path}")
            continue

        gt = ground_truth.get(fname, {}) if ground_truth else {}
        expected_type = gt.get("document_type", "unknown")

        print(f"\n>>> Document: {fname} (Type: {expected_type.upper()})")

        for prep_name, prep_fn in PREPROCESSING_CONFIGS.items():
            t_prep_0 = time.perf_counter()
            try:
                prepped = prep_fn(img_bgr)
            except Exception as e:
                logger.error(f"Preprocessing {prep_name} failed on {fname}: {e}")
                prepped = img_bgr
            prep_time_ms = round((time.perf_counter() - t_prep_0) * 1000.0, 2)

            for engine in engines:
                run_idx += 1
                prefix = f"[{run_idx:02d}/{total_runs:02d}] {engine.name} + {prep_name}"
                
                res = engine.run(prepped)
                raw_text = res.get("text", "")
                conf = res.get("conf", 0.0)
                boxes = res.get("boxes", 0)
                ocr_time_ms = res.get("time_ms", 0.0)
                total_time_ms = round(prep_time_ms + ocr_time_ms, 2)
                err = res.get("error")

                detected_doc = detect_document_type(raw_text)
                eval_doc = expected_type if expected_type != "unknown" else detected_doc

                fields = extract_fields_from_ocr(raw_text, eval_doc)

                gt_matches = {}
                if gt:
                    if gt.get("id_number"):
                        clean_extracted = (fields.get("id_number") or "").replace(" ", "")
                        clean_gt = gt["id_number"].replace(" ", "")
                        gt_matches["id_match"] = (clean_extracted == clean_gt)
                    if gt.get("name"):
                        cand = (fields.get("name") or "").strip().upper()
                        target = gt["name"].strip().upper()
                        gt_matches["name_match"] = (cand == target)
                    if gt.get("dob"):
                        cand_dob = (fields.get("dob") or "").strip()
                        target_dob = gt["dob"].strip()
                        gt_matches["dob_match"] = (cand_dob == target_dob)

                record = {
                    "engine": engine.name,
                    "preprocessing": prep_name,
                    "image": fname,
                    "doc_type": eval_doc,
                    "valid_id_format": "Yes" if fields["is_valid_id"] else "No",
                    "extracted_id": fields.get("id_number"),
                    "extracted_name": fields.get("name"),
                    "extracted_dob": fields.get("dob"),
                    "extracted_gender": fields.get("gender"),
                    "extracted_father": fields.get("father_name"),
                    "confidence": conf,
                    "text_regions": boxes,
                    "ocr_time_ms": ocr_time_ms,
                    "prep_time_ms": prep_time_ms,
                    "total_time_ms": total_time_ms,
                    "gt_matches": gt_matches,
                    "error": err,
                    "raw_text": raw_text
                }
                all_results.append(record)

                status_mark = "OK" if not err else "ERR"
                id_disp = fields.get("id_number") or "None"
                name_disp = fields.get("name") or "None"
                dob_disp = fields.get("dob") or "None"
                print(f"  {prefix:<32} | {status_mark} | ID: {id_disp:<13} | Name: {name_disp:<15} | DOB: {dob_disp:<10} | Conf: {conf:.2f} | Time: {total_time_ms:6.1f}ms")

    # Save to CSV
    fieldnames = [
        "engine", "preprocessing", "image", "doc_type",
        "valid_id_format", "extracted_id", "extracted_name", "extracted_dob",
        "extracted_gender", "extracted_father", "confidence", "text_regions",
        "ocr_time_ms", "prep_time_ms", "total_time_ms", "error"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in all_results:
            writer.writerow(r)

    # Save to JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print("\n" + "="*85)
    print(f"BENCHMARK COMPLETE. Results saved to:")
    print(f"  CSV:  {csv_path}")
    print(f"  JSON: {json_path}")
    print("="*85 + "\n")

    return all_results, csv_path, json_path


if __name__ == "__main__":
    UPLOADS = Path(__file__).resolve().parent.parent / "uploads"
    
    pan_img = str(UPLOADS / "3040b8a3acdf43a59020cbc3f119aa9e.jpeg")
    aadhaar_img = str(UPLOADS / "7a056d5e7b33486da89e99663de0e66f.jpeg")

    images = [pan_img, aadhaar_img]
    
    ground_truth = {
        "3040b8a3acdf43a59020cbc3f119aa9e.jpeg": {
            "document_type": "pan",
            "id_number": "AEUPL2459L",
            "name": "B S LAKSHMI",
            "dob": "08/09/1990",
            "father_name": "VISHWANATH SATHISH"
        },
        "7a056d5e7b33486da89e99663de0e66f.jpeg": {
            "document_type": "aadhaar",
            "id_number": "319132036859",
            "name": "Lakshmi B S",
            "dob": "08/09/1990",
            "gender": "Female"
        }
    }

    out_dir = str(Path(__file__).resolve().parent)
    run_benchmark(images, out_dir, ground_truth)
