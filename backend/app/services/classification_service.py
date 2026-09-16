"""
Document Classification Service
Classifies uploaded documents into predefined categories using keyword heuristics
and an optional transformer-based zero-shot classifier.
"""
import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)

# Keyword-based classification rules (fast, no model required)
CLASSIFICATION_RULES = {
    "aadhaar": [
        "aadhaar", "aadhar", "uid", "unique identification", "uidai",
        "enrolment no", "dob", "government of india"
    ],
    "pan": [
        "permanent account number", "income tax department", "pan",
        "father's name", "govt. of india"
    ],
    "salary_slip": [
        "salary slip", "pay slip", "payslip", "basic pay", "hra",
        "gross salary", "net salary", "pf deduction", "employee id"
    ],
    "income_cert": [
        "income certificate", "annual income", "hereby certify",
        "taluk", "tahsildar", "revenue department"
    ],

    "bank_statement": [
        "bank statement", "account statement", "transaction", "debit",
        "credit", "balance", "ifsc", "branch", "closing balance"
    ],
    "loan_application": [
        "loan application", "loan request", "amount requested",
        "purpose of loan", "repayment", "emi"
    ],
}


def classify_document(text: str, filename: str = "") -> Tuple[str, float]:
    """
    Classify a document by type.
    Returns (document_type, confidence_score 0-1).
    """
    if not text and not filename:
        return ("unknown", 0.0)

    combined = (text + " " + filename).lower()

    scores = {}
    for doc_type, keywords in CLASSIFICATION_RULES.items():
        hits = sum(1 for kw in keywords if kw in combined)
        scores[doc_type] = hits / len(keywords)

    if not scores:
        return ("unknown", 0.0)

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score < 0.05:
        # Try transformer zero-shot as fallback
        return _transformer_classify(text)

    logger.info(f"Classified as {best_type} (score={best_score:.2f})")
    return (best_type, min(best_score * 5, 1.0))  # normalise


def _transformer_classify(text: str) -> Tuple[str, float]:
    """Zero-shot classification using HuggingFace (fallback)."""
    try:
        from transformers import pipeline
        classifier = pipeline("zero-shot-classification",
                              model="facebook/bart-large-mnli")
        labels = list(CLASSIFICATION_RULES.keys())
        result = classifier(text[:512], candidate_labels=labels)
        return (result["labels"][0], result["scores"][0])
    except Exception as e:
        logger.warning(f"Transformer classification failed: {e}")
        return ("unknown", 0.0)
