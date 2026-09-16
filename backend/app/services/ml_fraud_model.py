"""
ML-Based Fraud Risk Prediction Module
──────────────────────────────────────
Ensemble model combining XGBoost (supervised) + Isolation Forest (unsupervised)
with SHAP explainability, inspired by Lending Club and Zest AI architectures.

Real-world reference:
  - Lending Club: XGBoost on loan features for default/fraud prediction
  - Zest AI: Gradient boosting + SHAP for explainable credit decisions
  - Upstart: Multi-signal ML underwriting with 1600+ features

This module:
  1. Engineers 15 features from OCR/NLP extraction outputs
  2. Runs XGBoost for supervised fraud probability
  3. Runs Isolation Forest for unsupervised anomaly scoring
  4. Blends scores into a unified ML risk score
  5. Generates SHAP explanations for every prediction
"""

import logging
import os
import re
# pyrefly: ignore [missing-import]
import numpy as np
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Feature names (must match training data column order) ──────────────
FEATURE_NAMES = [
    "monthly_income",
    "loan_amount",
    "loan_to_income_ratio",
    "has_aadhaar",
    "has_pan",
    "has_salary_slip",
    "has_bank_statement",
    "num_documents",
    "pan_valid",
    "aadhaar_valid",
    "name_present",
    "address_present",
    "phone_present",
    "income_to_threshold_ratio",
    "doc_completeness_score",
]


def engineer_features(
    extracted_info: Dict[str, Any],
    documents: List[Dict],
) -> np.ndarray:
    """
    Transform raw OCR/NLP outputs + document metadata into the 15-feature
    vector expected by the ML models.

    Parameters
    ----------
    extracted_info : dict
        Output of `nlp_service.extract_information()`.
    documents : list[dict]
        Each item must have a "document_type" key.

    Returns
    -------
    np.ndarray of shape (1, 15)
    """
    doc_types = {d.get("document_type") for d in documents}

    income = extracted_info.get("monthly_income") or 0.0
    loan = extracted_info.get("loan_amount") or 0.0
    pan = extracted_info.get("pan_number") or ""
    aadhaar = extracted_info.get("aadhaar_number") or ""

    # Derived ratios
    loan_to_income = (loan / (income * 12)) if income > 0 else 0.0
    income_to_threshold = income / 25_000.0  # MIN_INCOME_FOR_LOAN

    # Document completeness: how many of the 4 required types are present
    required = {"aadhaar", "pan", "salary_slip", "bank_statement"}
    doc_completeness = len(doc_types & required) / len(required)

    features = np.array(
        [
            income,                                                  # 0
            loan,                                                    # 1
            loan_to_income,                                          # 2
            1.0 if "aadhaar" in doc_types else 0.0,                  # 3
            1.0 if "pan" in doc_types else 0.0,                      # 4
            1.0 if "salary_slip" in doc_types else 0.0,              # 5
            1.0 if "bank_statement" in doc_types else 0.0,           # 6
            float(len(documents)),                                   # 7
            1.0 if pan and re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan) else 0.0,  # 8
            1.0 if aadhaar and re.match(r"^\d{12}$", aadhaar) else 0.0,          # 9
            1.0 if extracted_info.get("applicant_name") else 0.0,    # 10
            1.0 if extracted_info.get("address") else 0.0,           # 11
            1.0 if extracted_info.get("phone") else 0.0,             # 12
            income_to_threshold,                                     # 13
            doc_completeness,                                        # 14
        ],
        dtype=np.float64,
    ).reshape(1, -1)

    return features


class MLFraudPredictor:
    """
    Ensemble fraud predictor: XGBoost + Isolation Forest + SHAP.

    Usage
    -----
    predictor = MLFraudPredictor()          # auto-loads saved model if exists
    result = predictor.predict(extracted_info, documents)
    # result = {
    #   "ml_fraud_probability": 0.82,       # XGBoost P(fraud)
    #   "ml_anomaly_score": 0.71,           # Isolation Forest anomaly score
    #   "ml_risk_score": 68.4,              # blended 0–100
    #   "ml_fraud_flag": False,
    #   "shap_explanation": {
    #       "top_features": [
    #           {"feature": "loan_to_income_ratio", "impact": 0.23, "direction": "increases_risk"},
    #           ...
    #       ]
    #   },
    #   "model_version": "v1_xgb_iforest"
    # }
    """

    MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ml_models")
    XGB_PATH = os.path.join(MODEL_DIR, "xgb_fraud_model.joblib")
    ISO_PATH = os.path.join(MODEL_DIR, "isolation_forest_model.joblib")

    def __init__(self):
        self.xgb_model = None
        self.iso_model = None
        self.shap_explainer = None
        self._load_models()

    def _load_models(self):
        """Load pre-trained models from disk if available."""
        try:
            # pyrefly: ignore [missing-import]
            import joblib

            if os.path.exists(self.XGB_PATH):
                self.xgb_model = joblib.load(self.XGB_PATH)
                logger.info("XGBoost fraud model loaded from %s", self.XGB_PATH)
            else:
                logger.warning("XGBoost model not found at %s — ML predictions disabled", self.XGB_PATH)

            if os.path.exists(self.ISO_PATH):
                self.iso_model = joblib.load(self.ISO_PATH)
                logger.info("Isolation Forest model loaded from %s", self.ISO_PATH)
            else:
                logger.warning("Isolation Forest model not found at %s", self.ISO_PATH)

            # Build SHAP explainer for tree-based model
            if self.xgb_model is not None:
                try:
                    # pyrefly: ignore [missing-import]
                    import shap
                    self.shap_explainer = shap.TreeExplainer(self.xgb_model)
                    logger.info("SHAP TreeExplainer initialized")
                except Exception as e:
                    logger.warning("SHAP explainer initialization failed: %s", e)

        except Exception as e:
            logger.error("Failed to load ML models: %s", e)

    @property
    def is_available(self) -> bool:
        """Return True if at least the XGBoost model is loaded."""
        return self.xgb_model is not None

    def predict(
        self,
        extracted_info: Dict[str, Any],
        documents: List[Dict],
    ) -> Dict[str, Any]:
        """
        Run the ML ensemble on a single application.

        Returns a dict with ml_fraud_probability, ml_anomaly_score,
        ml_risk_score (0-100), ml_fraud_flag, and shap_explanation.
        """
        if not self.is_available:
            return {
                "ml_fraud_probability": None,
                "ml_anomaly_score": None,
                "ml_risk_score": None,
                "ml_fraud_flag": None,
                "shap_explanation": None,
                "model_version": "unavailable",
            }

        features = engineer_features(extracted_info, documents)

        # ── XGBoost: supervised fraud probability ────────────────────
        xgb_proba = float(self.xgb_model.predict_proba(features)[0, 1])

        # ── Isolation Forest: anomaly score ──────────────────────────
        if self.iso_model is not None:
            # decision_function returns negative for outliers;
            # we normalise to 0–1 where 1 = most anomalous
            raw_score = self.iso_model.decision_function(features)[0]
            # Typical range is roughly [-0.5, 0.5]; we clip and invert
            anomaly_score = float(np.clip(0.5 - raw_score, 0.0, 1.0))
        else:
            anomaly_score = 0.0

        # ── Blend: 67% XGBoost + 33% Isolation Forest ───────────────
        ml_risk_score = round((0.67 * xgb_proba + 0.33 * anomaly_score) * 100, 2)
        ml_risk_score = min(ml_risk_score, 100.0)

        # ── SHAP explanation ─────────────────────────────────────────
        shap_explanation = self._explain(features)

        return {
            "ml_fraud_probability": round(xgb_proba, 4),
            "ml_anomaly_score": round(anomaly_score, 4),
            "ml_risk_score": ml_risk_score,
            "ml_fraud_flag": ml_risk_score >= 70.0,
            "shap_explanation": shap_explanation,
            "model_version": "v1_xgb_iforest",
        }

    def _explain(self, features: np.ndarray) -> Optional[Dict]:
        """Generate SHAP feature-importance explanation for a prediction."""
        if self.shap_explainer is None:
            return None

        try:
            # pyrefly: ignore [missing-import]
            import shap
            shap_values = self.shap_explainer.shap_values(features)

            # For binary classification, shap_values may be a list [class_0, class_1]
            if isinstance(shap_values, list):
                sv = shap_values[1][0]  # class 1 = fraud
            else:
                sv = shap_values[0]

            # Build sorted list of feature contributions
            contributions = []
            for i, (name, value) in enumerate(zip(FEATURE_NAMES, sv)):
                contributions.append({
                    "feature": name,
                    "impact": round(abs(float(value)), 4),
                    "direction": "increases_risk" if float(value) > 0 else "decreases_risk",
                    "shap_value": round(float(value), 4),
                })

            # Sort by absolute impact, take top 5
            contributions.sort(key=lambda x: x["impact"], reverse=True)
            top_features = contributions[:5]

            return {
                "top_features": top_features,
                "base_value": round(float(self.shap_explainer.expected_value[1]
                                          if isinstance(self.shap_explainer.expected_value, (list, np.ndarray))
                                          else self.shap_explainer.expected_value), 4),
                "all_contributions": contributions,
            }
        except Exception as e:
            logger.warning("SHAP explanation failed: %s", e)
            return None

    @staticmethod
    def train(
        X: np.ndarray,
        y: np.ndarray,
        save: bool = True,
    ) -> Tuple:
        """
        Train both models from scratch. Called by scripts/train_model.py.

        Parameters
        ----------
        X : np.ndarray of shape (n_samples, 15)
        y : np.ndarray of shape (n_samples,) — 0 = legit, 1 = fraud
        save : bool — persist models to disk

        Returns
        -------
        (xgb_model, iso_model)
        """
        # pyrefly: ignore [missing-import]
        import xgboost as xgb
        from sklearn.ensemble import IsolationForest
        # pyrefly: ignore [missing-import]
        import joblib

        # ── XGBoost ──────────────────────────────────────────────────
        fraud_ratio = (y == 0).sum() / max((y == 1).sum(), 1)
        xgb_model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            scale_pos_weight=fraud_ratio,  # handle class imbalance
            eval_metric="logloss",
            use_label_encoder=False,
            random_state=42,
        )
        xgb_model.fit(X, y)
        logger.info("XGBoost trained — %d samples, %d features", X.shape[0], X.shape[1])

        # ── Isolation Forest ─────────────────────────────────────────
        iso_model = IsolationForest(
            n_estimators=150,
            contamination=0.15,  # expected fraud rate
            random_state=42,
        )
        iso_model.fit(X)
        logger.info("Isolation Forest trained")

        if save:
            os.makedirs(MLFraudPredictor.MODEL_DIR, exist_ok=True)
            joblib.dump(xgb_model, MLFraudPredictor.XGB_PATH)
            joblib.dump(iso_model, MLFraudPredictor.ISO_PATH)
            logger.info("Models saved to %s", MLFraudPredictor.MODEL_DIR)

        return xgb_model, iso_model
