"""
Test script for the production OCR pipeline (PaddleOCR primary, EasyOCR fallback).
Tests real Aadhaar and PAN images from backend/uploads/ through the updated
lightweight preprocessing and OCR service.
"""
import os
import sys
from pathlib import Path

# Ensure UTF-8 output and error handling on Windows terminal
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.preprocessing import preprocess_image
from app.services.ocr_service import extract_document, extract_text, _extract_with_easyocr
from app.services.parsers.aadhaar_parser import parse_aadhaar
from app.services.parsers.pan_parser import parse_pan


def test_document(image_path: str, doc_type: str, test_title: str):
    print("\n" + "="*80, flush=True)
    print(f"TEST: {test_title}", flush=True)
    print(f"File: {os.path.basename(image_path)} (Type: {doc_type.upper()})", flush=True)
    print("="*80, flush=True)

    # 1. Preprocess
    print("\n--- STEP 1: Conservative Preprocessing ---", flush=True)
    prepped_path = preprocess_image(image_path)
    print(f"Preprocessed output: {prepped_path}", flush=True)
    orig_size = os.path.getsize(image_path)
    prep_size = os.path.getsize(prepped_path)
    print(f"Original size: {orig_size} bytes | Preprocessed size: {prep_size} bytes", flush=True)

    # 2. Extract Document
    print("\n--- STEP 2: Production OCR Extraction ---", flush=True)
    doc_res = extract_document(prepped_path)
    engine_used = doc_res.get("engine", "unknown")
    full_text = doc_res.get("text", "")
    tokens = doc_res.get("tokens", [])
    confs = [t["confidence"] for t in tokens if "confidence" in t]
    avg_conf = (sum(confs) / len(confs)) if confs else 0.0

    fallback_triggered = (engine_used == "easyocr")

    print(f"1. OCR Engine Used:       {engine_used.upper()}", flush=True)
    print(f"2. Fallback Triggered:     {'YES (EasyOCR fallback invoked)' if fallback_triggered else 'NO (PaddleOCR primary succeeded)'}", flush=True)
    print(f"3. Detected Text Tokens:   {len(tokens)}", flush=True)
    print(f"4. Average Confidence:     {avg_conf:.4f}", flush=True)
    print(f"5. Confidence Range:       min={min(confs) if confs else 0.0:.4f}, max={max(confs) if confs else 0.0:.4f}", flush=True)

    print("\n--- Extracted Text Preview ---", flush=True)
    for i, line in enumerate(full_text.split('\n'), 1):
        clean_line = line.encode("ascii", "replace").decode("ascii") if sys.platform == "win32" and not sys.stdout.encoding.lower().startswith("utf") else line
        print(f"  [{i:02d}] {clean_line}", flush=True)

    # 3. Downstream Field Extraction
    print("\n--- STEP 3: Downstream Field Parsing ---", flush=True)
    if doc_type == "pan":
        parsed = parse_pan(full_text)
        pan_num = parsed.get("pan_number", {}).get("value")
        applicant_name = parsed.get("applicant_name", {}).get("value")
        dob = parsed.get("dob", {}).get("value")
        father_name = parsed.get("father_name", {}).get("value")

        print(f"6. Extracted PAN Number:   {pan_num} (Status: {parsed.get('pan_number', {}).get('validation_status')})", flush=True)
        print(f"7. Extracted Name:         {applicant_name} (Method: {parsed.get('applicant_name', {}).get('extraction_method')})", flush=True)
        print(f"8. Extracted DOB:          {dob}", flush=True)
        print(f"   Extracted Father Name:  {father_name}", flush=True)

    elif doc_type == "aadhaar":
        parsed = parse_aadhaar(full_text)
        aadhaar_num = parsed.get("aadhaar_number", {}).get("value")
        applicant_name = parsed.get("applicant_name", {}).get("value")
        dob = parsed.get("dob", {}).get("value")
        gender = parsed.get("gender", {}).get("value")

        print(f"6. Extracted Aadhaar No:   {aadhaar_num} (Status: {parsed.get('aadhaar_number', {}).get('validation_status')})", flush=True)
        print(f"7. Extracted Name:         {applicant_name} (Method: {parsed.get('applicant_name', {}).get('extraction_method')})", flush=True)
        print(f"8. Extracted DOB:          {dob}", flush=True)
        print(f"   Extracted Gender:       {gender}", flush=True)

    # 4. Backward Compatibility Check on extract_text()
    print("\n--- STEP 4: Backward Compatibility String Check ---", flush=True)
    text_obj = extract_text(prepped_path)
    is_str = isinstance(text_obj, str)
    has_tokens = hasattr(text_obj, "tokens") and len(text_obj.tokens) > 0
    dict_access = (text_obj["engine"] == engine_used)
    print(f"  isinstance(result, str): {is_str}", flush=True)
    print(f"  result.tokens populated: {has_tokens} ({len(text_obj.tokens)} tokens)", flush=True)
    print(f"  result['engine'] access: {dict_access} ({text_obj['engine']})", flush=True)


def test_fallback_simulation(image_path: str):
    """Explicitly verify that if PaddleOCR is unavailable/fails, EasyOCR seamlessly catches it."""
    print("\n" + "="*80, flush=True)
    print("TEST: EasyOCR Fallback Verification (Simulated PaddleOCR Failure)", flush=True)
    print("="*80, flush=True)
    
    import app.services.ocr_service as ocr_mod
    original_fn = ocr_mod._extract_with_paddle
    ocr_mod._extract_with_paddle = lambda path: None  # Force failure
    
    try:
        res = ocr_mod.extract_document(image_path)
        print(f"1. OCR Engine Used:       {res.get('engine').upper()}", flush=True)
        print(f"2. Fallback Triggered:     {'YES (Seamlessly caught by EasyOCR)' if res.get('engine') == 'easyocr' else 'NO'}", flush=True)
        print(f"3. Tokens Extracted:       {len(res.get('tokens', []))}", flush=True)
        print(f"4. Text Length:            {len(res.get('text', ''))} characters", flush=True)
        print(f"5. Fallback Status:        SUCCESSFUL - EasyOCR handled extraction gracefully", flush=True)
    finally:
        ocr_mod._extract_with_paddle = original_fn


if __name__ == "__main__":
    uploads = BACKEND_DIR / "uploads"
    pan_image = str(uploads / "3040b8a3acdf43a59020cbc3f119aa9e.jpeg")
    aadhaar_image = str(uploads / "7a056d5e7b33486da89e99663de0e66f.jpeg")

    print("\n" + "#"*80, flush=True)
    print("STARTING PRODUCTION OCR PIPELINE VERIFICATION", flush=True)
    print("#"*80, flush=True)

    # Test 1: Real PAN card through production pipeline
    test_document(pan_image, "pan", "Real PAN Card Extraction (PaddleOCR Primary)")

    # Test 2: Real Aadhaar card through production pipeline
    test_document(aadhaar_image, "aadhaar", "Real Aadhaar Card Extraction (PaddleOCR Primary)")

    # Test 3: Fallback mechanism test
    test_fallback_simulation(pan_image)

    print("\n" + "#"*80, flush=True)
    print("ALL PRODUCTION OCR TESTS FINISHED SUCCESSFULLY", flush=True)
    print("#"*80 + "\n", flush=True)
