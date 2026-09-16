"""
Loan Verification Engine
Applies rule-based checks on extracted information and generates
a verification score + status.
"""
import logging
import re
from typing import Dict, Any, List, Tuple
from app.core.config import settings

logger = logging.getLogger(__name__)


def _normalize_name(name: str) -> str:
    """Lowercase, strip punctuation for fuzzy comparison."""
    if not name:
        return ""
    return re.sub(r"[^a-z ]", "", name.lower()).strip()


def _name_similarity(a: str, b: str) -> float:
    """Simple token-overlap similarity between two name strings."""
    if not a or not b:
        return 0.0
    tokens_a = set(_normalize_name(a).split())
    tokens_b = set(_normalize_name(b).split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / max(len(tokens_a), len(tokens_b))


class VerificationEngine:

    def verify(self, extracted_info: Dict[str, Any], documents: List[Dict]) -> Dict[str, Any]:
        """
        Run all verification checks. Returns a results dict with:
          - checks: list of individual check results
          - verification_score: 0–100
          - status: approved | rejected | manual_review
        """
        checks = []

        # ── 1. Identity verification ─────────────────────────────────────
        checks.append(self._check_identity(extracted_info, documents))

        # ── 2. Income verification ────────────────────────────────────────
        checks.append(self._check_income(extracted_info))

        # ── 3. Required documents present ────────────────────────────────
        checks.append(self._check_required_docs(documents))

        # ── 4. PAN format validation ──────────────────────────────────────
        checks.append(self._check_pan_format(extracted_info))

        # ── 5. Aadhaar format validation ──────────────────────────────────
        checks.append(self._check_aadhaar_format(extracted_info))

        # ── Aggregate score ───────────────────────────────────────────────
        total_weight = sum(c["weight"] for c in checks)
        earned       = sum(c["weight"] * c["score"] for c in checks)
        verification_score = (earned / total_weight) * 100 if total_weight else 0

        # ── Determine status ──────────────────────────────────────────────
        if verification_score >= settings.MIN_VERIFICATION_SCORE:
            status = "approved"
        elif verification_score >= 40:
            status = "manual_review"
        else:
            status = "rejected"

        return {
            "checks": checks,
            "verification_score": round(verification_score, 2),
            "status": status,
        }

    # ── Individual checks ─────────────────────────────────────────────────

    def _check_identity(self, info: Dict, documents: List[Dict]) -> Dict:
        """Cross-verify name across available documents."""
        name = info.get("applicant_name", "")
        # In a real system we'd compare names extracted per-doc; here we check presence.
        has_identity = any(d.get("document_type") in ("aadhaar", "pan") for d in documents)
        score = 1.0 if (name and has_identity) else 0.5 if name else 0.0
        return {
            "name": "Identity Verification",
            "score": score,
            "weight": 30,
            "details": f"Name found: {bool(name)}, Identity document present: {has_identity}",
            "passed": score >= 0.5,
        }

    def _check_income(self, info: Dict) -> Dict:
        """Verify monthly income meets minimum eligibility."""
        income = info.get("monthly_income")
        loan_amount = info.get("loan_amount", 0) or 0
        if income is None:
            return {"name": "Income Verification", "score": 0.0, "weight": 30,
                    "details": "Income information not found", "passed": False}
        eligible = income >= settings.MIN_INCOME_FOR_LOAN
        # Additional: rough EMI affordability (loan / 60 months ≤ 50% income)
        if loan_amount:
            emi = loan_amount / 60
            affordable = emi <= income * 0.5
        else:
            affordable = True
        score = (0.7 if eligible else 0.0) + (0.3 if affordable else 0.0)
        return {
            "name": "Income Verification",
            "score": score,
            "weight": 30,
            "details": f"Monthly income: ₹{income}, Eligible: {eligible}, EMI affordable: {affordable}",
            "passed": eligible,
        }

    def _check_required_docs(self, documents: List[Dict]) -> Dict:
        """Check that at least identity + income proof are present."""
        types = {d.get("document_type") for d in documents}
        has_id     = bool(types & {"aadhaar", "pan"})
        has_income = bool(types & {"salary_slip", "income_cert", "form_16"})
        has_bank   = "bank_statement" in types
        score = (0.4 * has_id) + (0.4 * has_income) + (0.2 * has_bank)
        return {
            "name": "Required Documents",
            "score": score,
            "weight": 25,
            "details": f"Identity: {has_id}, Income: {has_income}, Bank: {has_bank}",
            "passed": has_id and has_income,
        }

    def _check_pan_format(self, info: Dict) -> Dict:
        pan = info.get("pan_number", "")
        valid = bool(pan and re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan))
        return {
            "name": "PAN Format",
            "score": 1.0 if valid else (0.5 if not pan else 0.0),
            "weight": 10,
            "details": f"PAN: {pan or 'not found'}, Valid format: {valid}",
            "passed": valid,
        }

    def _check_aadhaar_format(self, info: Dict) -> Dict:
        aadhaar = info.get("aadhaar_number", "")
        valid = bool(aadhaar and re.match(r"^\d{12}$", aadhaar))
        return {
            "name": "Aadhaar Format",
            "score": 1.0 if valid else (0.5 if not aadhaar else 0.0),
            "weight": 5,
            "details": f"Aadhaar present: {bool(aadhaar)}, Valid format: {valid}",
            "passed": valid,
        }
