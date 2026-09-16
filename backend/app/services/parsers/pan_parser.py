"""
PAN Document Parser & Field Validator
Extracts structured metadata (value, confidence, source, extraction_method, validation_status)
from raw OCR text lines for PAN cards.
"""
import re
from typing import Dict, Any, Optional

def parse_pan(text: str) -> Dict[str, Any]:
    """Parse PAN card OCR text and return structured metadata per field."""
    results = {
        "pan_number":     _build_field(None, 0.0, "pan", "none", "not_found"),
        "applicant_name": _build_field(None, 0.0, "pan", "none", "not_found"),
        "father_name":    _build_field(None, 0.0, "pan", "none", "not_found"),
        "dob":            _build_field(None, 0.0, "pan", "none", "not_found"),
    }

    if not text:
        return results

    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # 1. PAN Number (5 letters + 4 digits + 1 letter)
    pan_match = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text.upper())
    if pan_match:
        pan_val = pan_match.group(1)
        results["pan_number"] = _build_field(
            value=pan_val,
            confidence=0.99,
            source="pan",
            method="regex_pattern_verifier",
            status="valid",
            evidence=pan_match.group(0)
        )

    # 2. DOB (Date of Birth)
    dob_match = re.search(r"\b(\d{2}[/\-]\d{2}[/\-]\d{4})\b", text)
    if dob_match:
        raw_dob = dob_match.group(1).replace("-", "/")
        results["dob"] = _build_field(
            value=raw_dob,
            confidence=0.98,
            source="pan",
            method="regex_date_parser",
            status="valid",
            evidence=dob_match.group(0)
        )

    # 3. Layout Strategy for Applicant Name and Father's Name
    # On Indian PAN Cards, lines between GOVT OF INDIA / INCOME TAX DEPARTMENT and DOB are:
    # Line 1: Applicant Name
    # Line 2 (and 3): Father's Name
    header_idx = -1
    for i, line in enumerate(lines):
        if re.search(r"(?:income tax|govt|india|department)", line, re.I):
            header_idx = i

    dob_idx = -1
    for i, line in enumerate(lines):
        if re.search(r"\b\d{2}[/\-]\d{2}[/\-]\d{4}\b", line):
            dob_idx = i
            break

    candidate_lines = []
    start_k = header_idx + 1 if header_idx >= 0 else 0
    end_k = dob_idx if dob_idx > start_k else len(lines)

    for k in range(start_k, end_k):
        cl = _clean_ocr_name(lines[k])
        if len(cl) >= 3 and _is_valid_name(cl):
            candidate_lines.append(cl)

    # Also fallback to explicit labels if layout index is ambiguous
    if not candidate_lines:
        for line in lines:
            fm = re.search(r"(?:father(?:'s)?\s*name)[:\s\-\.]*([A-Za-z\s\.]{3,50})", line, re.I)
            if fm:
                candidate_lines.append(_clean_ocr_name(fm.group(1)))

    if len(candidate_lines) >= 1:
        results["applicant_name"] = _build_field(
            value=candidate_lines[0],
            confidence=0.95,
            source="pan",
            method="pan_layout_parser",
            status="valid",
            evidence=candidate_lines[0]
        )

    if len(candidate_lines) >= 2:
        father_val = " ".join(candidate_lines[1:])
        results["father_name"] = _build_field(
            value=father_val,
            confidence=0.93,
            source="pan",
            method="pan_layout_parser",
            status="valid",
            evidence=father_val
        )

    return results


def _build_field(value: Optional[str], confidence: float, source: str, method: str, status: str, evidence: Optional[str] = None) -> Dict[str, Any]:
    return {
        "value": value,
        "confidence": confidence,
        "source_document": source,
        "extraction_method": method,
        "validation_status": status,
        "raw_match": evidence
    }


def _clean_ocr_name(val: str) -> str:
    if not val:
        return ""
    # Normalize common OCR symbol misreads in Indian names
    cleaned = val.replace("$", "S")
    cleaned = re.sub(r"(?i)^(?:applicant\s*)?name[:\s\-\.]*", "", cleaned)
    cleaned = re.sub(r"(?i)^(?:father(?:'s)?\s*)?name[:\s\-\.]*", "", cleaned)
    cleaned = re.sub(r"[^A-Za-z\s\.]", "", cleaned).strip()
    return re.sub(r"\s+", " ", cleaned)


def _is_valid_name(val: str) -> bool:
    if len(val) < 3 or len(val) > 50:
        return False
    if re.search(r"(?:income|tax|department|govt|india|permanent|account|number|card|signature|date|birth|father)", val, re.I):
        return False
    return True
