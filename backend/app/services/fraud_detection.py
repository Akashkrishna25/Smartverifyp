"""
Fraud Detection Module
Analyses extracted info and documents for anomalies, duplicates,
and suspicious patterns. Returns a risk score (0–100) and fraud flags.

Now integrates ML-based risk prediction (XGBoost + Isolation Forest)
alongside the existing rule-based checks. The final risk score is a
weighted blend:
    40% rule-based  +  40% XGBoost  +  20% Isolation Forest

Real-world reference: This hybrid approach mirrors how Lending Club
and HDFC Bank combine deterministic rules with ML scoring.
"""
import re, logging
from typing import Dict, Any, List
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Lazy-loaded singleton to avoid model loading on every request
_ml_predictor = None


def _get_ml_predictor():
    """Lazy-load the ML fraud predictor singleton."""
    global _ml_predictor
    if _ml_predictor is None:
        try:
            from app.services.ml_fraud_model import MLFraudPredictor
            _ml_predictor = MLFraudPredictor()
        except Exception as e:
            logger.warning("ML fraud predictor unavailable: %s", e)
    return _ml_predictor


class FraudDetector:

    def analyse(
        self,
        extracted_info: Dict[str, Any],
        documents: List[Dict],
        application_id: int,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Run all fraud checks (rule-based + ML). Returns:
          - risk_score: 0–100  (blended if ML available, otherwise rule-only)
          - fraud_flag: bool
          - alerts: list of alert strings
          - details: per-check breakdown
          - ml_prediction: dict with ML model outputs + SHAP explanation
        """
        alerts = []
        details = []
        rule_risk_score = 0.0

        # ── 1. Missing critical documents ─────────────────────────────────
        doc_types = {d.get("document_type") for d in documents}
        missing = []
        for req in ("aadhaar", "pan", "salary_slip"):
            if req not in doc_types:
                missing.append(req)
        if missing:
            score_add = 10 * len(missing)
            rule_risk_score += score_add
            msg = f"Missing required documents: {missing}"
            alerts.append(msg)
            details.append({"check": "missing_documents", "risk_added": score_add, "detail": msg})

        # ── 2. Duplicate Aadhaar / PAN check ─────────────────────────────
        from app.models.verification_report import VerificationReport
        aadhaar = extracted_info.get("aadhaar_number")
        pan     = extracted_info.get("pan_number")

        if aadhaar:
            # SQLite compatible check across VerificationReport table
            existing = 0
            reports = db.query(VerificationReport).filter(VerificationReport.application_id != application_id).all()
            for r in reports:
                if r.extracted_info and r.extracted_info.get("aadhaar_number") == aadhaar:
                    existing += 1
            if existing:
                rule_risk_score += 30
                msg = f"Duplicate Aadhaar detected in {existing} other application(s)"
                alerts.append(msg)
                details.append({"check": "duplicate_aadhaar", "risk_added": 30, "detail": msg})

        # ── 3. Unusually high income claim ────────────────────────────────
        income = extracted_info.get("monthly_income")
        loan   = extracted_info.get("loan_amount", 0) or 0
        if income and income > 500000:
            rule_risk_score += 15
            msg = f"Unusually high claimed income: ₹{income}/month"
            alerts.append(msg)
            details.append({"check": "high_income_claim", "risk_added": 15, "detail": msg})

        # ── 4. Loan-to-income ratio ────────────────────────────────────────
        if income and loan:
            lti = loan / (income * 12)
            if lti > 10:
                rule_risk_score += 20
                msg = f"Loan-to-annual-income ratio is very high: {lti:.1f}x"
                alerts.append(msg)
                details.append({"check": "high_lti_ratio", "risk_added": 20, "detail": msg})

        # ── 5. Applicant name inconsistency ──────────────────────────────
        # (In production: compare per-document extracted names)
        if not extracted_info.get("applicant_name"):
            rule_risk_score += 10
            msg = "Applicant name could not be extracted"
            alerts.append(msg)
            details.append({"check": "missing_name", "risk_added": 10, "detail": msg})

        # ── 6. PAN format check ───────────────────────────────────────────
        if pan and not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan):
            rule_risk_score += 25
            msg = f"PAN number format is invalid: {pan}"
            alerts.append(msg)
            details.append({"check": "invalid_pan", "risk_added": 25, "detail": msg})

        rule_risk_score = min(rule_risk_score, 100.0)

        # ── 7. ML-based risk prediction ───────────────────────────────────
        ml_prediction = None
        predictor = _get_ml_predictor()
        if predictor and predictor.is_available:
            try:
                ml_prediction = predictor.predict(extracted_info, documents)
                ml_risk = ml_prediction.get("ml_risk_score", 0.0) or 0.0

                # Blend: 40% rules + 40% XGBoost + 20% Isolation Forest
                # (XGBoost and IsoForest are already blended inside ml_risk)
                blended_score = round(0.4 * rule_risk_score + 0.6 * ml_risk, 2)
                blended_score = min(blended_score, 100.0)

                # Add SHAP-based alerts for top risk factors
                shap_exp = ml_prediction.get("shap_explanation")
                if shap_exp and shap_exp.get("top_features"):
                    top_risky = [
                        f for f in shap_exp["top_features"]
                        if f["direction"] == "increases_risk"
                    ][:3]
                    if top_risky:
                        feature_names = [f["feature"].replace("_", " ") for f in top_risky]
                        msg = f"ML model top risk factors: {', '.join(feature_names)}"
                        alerts.append(msg)
                        details.append({
                            "check": "ml_risk_factors",
                            "risk_added": 0,
                            "detail": msg,
                            "shap_features": top_risky,
                        })

                logger.info(
                    "ML fraud prediction: rule=%.1f, ml=%.1f, blended=%.1f (app=%d)",
                    rule_risk_score, ml_risk, blended_score, application_id,
                )
            except Exception as e:
                logger.error("ML prediction failed, using rule-only score: %s", e)
                blended_score = rule_risk_score
        else:
            blended_score = rule_risk_score
            logger.debug("ML model not available — using rule-only score")

        fraud_flag = blended_score >= 70

        return {
            "risk_score": round(blended_score, 2),
            "rule_risk_score": round(rule_risk_score, 2),
            "fraud_flag": fraud_flag,
            "alerts": alerts,
            "details": details,
            "ml_prediction": ml_prediction,
        }
