"""
NLP & Document Parsing Integration Service
Extracts structured fields from raw OCR text using document-specific parsers (Aadhaar/PAN)
with fallback to spaCy and regex patterns.
Constructs rich field metadata (value, confidence, source, method, status)
while maintaining top-level flat key compatibility.
"""
import re, logging
from typing import Dict, Any, Optional
from app.services.parsers.aadhaar_parser import parse_aadhaar
from app.services.parsers.pan_parser import parse_pan

logger = logging.getLogger(__name__)

# Lazy-load spaCy model
_nlp = None

def _get_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            from app.core.config import settings
            _nlp = spacy.load(settings.SPACY_MODEL)
            logger.info("spaCy model loaded")
        except Exception as e:
            logger.warning(f"spaCy unavailable: {e}")
    return _nlp


def extract_information(text: str, doc_type: str = "generic") -> Dict[str, Any]:
    """
    Extract key fields from OCR text.
    Returns a dict with all extracted fields (flat values + rich 'fields' metadata).
    """
    info: Dict[str, Any] = {
        "applicant_name": None,
        "address": None,
        "aadhaar_number": None,
        "pan_number": None,
        "employer_name": None,
        "monthly_income": None,
        "bank_account": None,
        "loan_amount": None,
        "dob": None,
        "phone": None,
        "gender": None,
        "father_name": None,
        "document_type": doc_type,
        "fields": {},
    }

    if not text:
        return info

    parsed_fields: Dict[str, Any] = {}

    # Route to document-specific parser
    if doc_type == "aadhaar":
        parsed_fields = parse_aadhaar(text)
    elif doc_type == "pan":
        parsed_fields = parse_pan(text)

    # Populate from parser
    for k, meta in parsed_fields.items():
        if meta and meta.get("value"):
            info[k] = meta["value"]

    # Fallback extraction for generic fields / missing parser fields
    # ── Aadhaar Number ──────────────────────────────────────────────────
    if not info["aadhaar_number"]:
        aadhaar_match = re.search(r"\b(\d{4}[\s-]?\d{4}[\s-]?\d{4})\b", text)
        if aadhaar_match:
            clean_num = re.sub(r"[\s-]", "", aadhaar_match.group(1))
            info["aadhaar_number"] = clean_num
            parsed_fields["aadhaar_number"] = {
                "value": clean_num,
                "confidence": 0.95,
                "source_document": doc_type,
                "extraction_method": "generic_regex",
                "validation_status": "valid" if len(clean_num) == 12 else "needs_review"
            }

    # ── PAN Number ──────────────────────────────────────────────────────
    if not info["pan_number"]:
        pan_match = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text.upper())
        if pan_match:
            pan_val = pan_match.group(1)
            info["pan_number"] = pan_val
            parsed_fields["pan_number"] = {
                "value": pan_val,
                "confidence": 0.99,
                "source_document": doc_type,
                "extraction_method": "generic_regex",
                "validation_status": "valid"
            }

    # ── Phone number ─────────────────────────────────────────────────────
    phone_match = re.search(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b", text)
    if phone_match:
        info["phone"] = phone_match.group()

    # ── Income / Salary ──────────────────────────────────────────────────
    income_patterns = [
        r"(?:net salary|gross salary|monthly income|total salary)[:\s]+(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
        r"(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{1,2})?)",
    ]
    for pat in income_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                info["monthly_income"] = float(m.group(1).replace(",", ""))
                break
            except ValueError:
                pass

    # ── Loan amount ───────────────────────────────────────────────────────
    loan_match = re.search(
        r"(?:loan amount|amount requested)[:\s]+(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
        text, re.IGNORECASE
    )
    if loan_match:
        try:
            info["loan_amount"] = float(loan_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # ── Bank account ──────────────────────────────────────────────────────
    acct_match = re.search(r"(?:account no|account number|a/c no)[.:\s]+([\dX*]+)", text, re.IGNORECASE)
    if acct_match:
        info["bank_account"] = acct_match.group(1)

    # ── Name extraction (regex fallback + spaCy NER) ─────────────────────
    if not info["applicant_name"]:
        name_match = re.search(r"(?:name|applicant name)[.:\s\-\n]+([A-Za-z\s\.]{3,40})", text, re.IGNORECASE)
        if name_match:
            cand = name_match.group(1).strip().split('\n')[0].strip()
            if cand and not re.search(r"(?:father|mother|husband|dob|date|income|tax|card|number)", cand, re.I):
                info["applicant_name"] = cand.title()
                parsed_fields["applicant_name"] = {
                    "value": info["applicant_name"],
                    "confidence": 0.88,
                    "source_document": doc_type,
                    "extraction_method": "regex_fallback",
                    "validation_status": "valid"
                }

    nlp = _get_nlp()
    if nlp:
        doc = nlp(text[:5000])
        persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
        orgs    = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
        if persons and not info["applicant_name"]:
            info["applicant_name"] = persons[0].title()
            parsed_fields["applicant_name"] = {
                "value": info["applicant_name"],
                "confidence": 0.85,
                "source_document": doc_type,
                "extraction_method": "spacy_ner",
                "validation_status": "valid"
            }
        if orgs and not info["employer_name"]:
            info["employer_name"] = orgs[0]

    # ── DOB ───────────────────────────────────────────────────────────────
    if not info["dob"]:
        dob_match = re.search(r"\b(\d{2}[/\-]\d{2}[/\-]\d{4})\b", text)
        if dob_match:
            info["dob"] = dob_match.group(1).replace("-", "/")
            parsed_fields["dob"] = {
                "value": info["dob"],
                "confidence": 0.90,
                "source_document": doc_type,
                "extraction_method": "generic_regex",
                "validation_status": "valid"
            }

    # ── Gender ────────────────────────────────────────────────────────────
    if not info["gender"]:
        gender_match = re.search(r"\b(Male|Female|Transgender)\b", text, re.IGNORECASE)
        if gender_match:
            info["gender"] = gender_match.group(1).title()
            parsed_fields["gender"] = {
                "value": info["gender"],
                "confidence": 0.92,
                "source_document": doc_type,
                "extraction_method": "generic_regex",
                "validation_status": "valid"
            }

    # ── Address ───────────────────────────────────────────────────────────
    if not info["address"]:
        addr_match = re.search(r"([^\n]{20,100}\b\d{6}\b)", text)
        if addr_match:
            info["address"] = addr_match.group(1).strip()
            parsed_fields["address"] = {
                "value": info["address"],
                "confidence": 0.85,
                "source_document": doc_type,
                "extraction_method": "pincode_heuristic",
                "validation_status": "valid"
            }

    # Ensure all primary fields have a structured metadata entry in 'fields'
    for k in ["applicant_name", "aadhaar_number", "pan_number", "dob", "gender", "address", "father_name"]:
        if k not in parsed_fields or not parsed_fields[k].get("value"):
            val = info.get(k)
            parsed_fields[k] = {
                "value": val,
                "confidence": 0.90 if val else 0.0,
                "source_document": doc_type,
                "extraction_method": "integrated_parser" if val else "none",
                "validation_status": "valid" if val else "not_found"
            }

    info["fields"] = parsed_fields
    return info
