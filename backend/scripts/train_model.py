"""
Model Training & Evaluation Script for SmartVerify ML Fraud Detection
──────────────────────────────────────────────────────────────────────
Trains XGBoost + Isolation Forest ensemble on synthetic (or real) data.

Outputs:
  - Trained models saved to ml_models/
  - Classification report (precision, recall, F1)
  - AUC-ROC score
  - Feature importance ranking
  - Confusion matrix

Usage:
    python scripts/train_model.py
"""

import os
import sys
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import pandas as pd

# Ensure the backend directory is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.ml_fraud_model import MLFraudPredictor, FEATURE_NAMES


def main():
    print("=" * 60)
    print("SmartVerify — ML Fraud Model Training")
    print("=" * 60)

    # ── Load data ────────────────────────────────────────────────
    data_path = os.path.join(os.path.dirname(__file__), "..", "ml_models", "training_data.csv")
    if not os.path.exists(data_path):
        print(f"\n[FAIL] Training data not found at {data_path}")
        print("   Run `python scripts/generate_training_data.py` first.")
        sys.exit(1)

    df = pd.read_csv(data_path)
    print(f"\n[DATA] Loaded {len(df)} samples from {data_path}")
    print(f"   Features: {len(FEATURE_NAMES)}")
    print(f"   Class distribution: {dict(df['is_fraud'].value_counts())}")

    X = df[FEATURE_NAMES].values
    y = df["is_fraud"].values

    # ── Train/Test split ─────────────────────────────────────────
    from sklearn.model_selection import train_test_split

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n   Train: {len(X_train)} | Test: {len(X_test)}")

    # ── Apply SMOTE for class balancing on training set ───────────
    try:
        # pyrefly: ignore [missing-import]
        from imblearn.over_sampling import SMOTE

        smote = SMOTE(random_state=42)
        X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)
        print(f"   After SMOTE: {len(X_train_balanced)} training samples")
        print(f"   Balanced distribution: {dict(zip(*np.unique(y_train_balanced, return_counts=True)))}")
    except ImportError:
        print("   [WARN] imbalanced-learn not installed — training without SMOTE")
        X_train_balanced, y_train_balanced = X_train, y_train

    # ── Train models ─────────────────────────────────────────────
    print("\n[BUILD] Training XGBoost + Isolation Forest ensemble...")
    xgb_model, iso_model = MLFraudPredictor.train(
        X_train_balanced, y_train_balanced, save=True
    )

    # ── Evaluate XGBoost ─────────────────────────────────────────
    from sklearn.metrics import (
        classification_report,
        confusion_matrix,
        roc_auc_score,
    )

    y_pred = xgb_model.predict(X_test)
    y_proba = xgb_model.predict_proba(X_test)[:, 1]

    print("\n" + "=" * 60)
    print("[CHART] XGBoost Classification Report")
    print("=" * 60)
    print(classification_report(y_test, y_pred, target_names=["Legitimate", "Fraud"]))

    auc = roc_auc_score(y_test, y_proba)
    print(f"[TARGET] AUC-ROC: {auc:.4f}")

    cm = confusion_matrix(y_test, y_pred)
    print(f"\n[DATA] Confusion Matrix:")
    print(f"   {'':>15} Predicted Legit  Predicted Fraud")
    print(f"   {'Actual Legit':>15}    {cm[0][0]:>8}         {cm[0][1]:>8}")
    print(f"   {'Actual Fraud':>15}    {cm[1][0]:>8}         {cm[1][1]:>8}")

    # ── Feature Importance ───────────────────────────────────────
    print(f"\n[DATA] XGBoost Feature Importance (Top 10):")
    importances = xgb_model.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    for rank, idx in enumerate(sorted_idx[:10], 1):
        bar = "[BAR]" * int(importances[idx] * 50)
        print(f"   {rank:>2}. {FEATURE_NAMES[idx]:>28}: {importances[idx]:.4f} {bar}")

    # ── Evaluate Isolation Forest ────────────────────────────────
    iso_preds = iso_model.predict(X_test)
    # -1 = outlier, 1 = inlier → convert to 0/1
    iso_labels = (iso_preds == -1).astype(int)
    iso_auc = roc_auc_score(y_test, iso_labels)
    print(f"\n[TREE] Isolation Forest AUC-ROC: {iso_auc:.4f}")
    print(f"   Anomalies detected: {iso_labels.sum()} / {len(iso_labels)}")

    # ── Test SHAP explainability ─────────────────────────────────
    print("\n[SEARCH] Testing SHAP explainability...")
    try:
        # pyrefly: ignore [missing-import]
        import shap

        explainer = shap.TreeExplainer(xgb_model)
        sample = X_test[:1]
        shap_values = explainer.shap_values(sample)

        if isinstance(shap_values, list):
            sv = shap_values[1][0]
        else:
            sv = shap_values[0]

        print("   SHAP values for first test sample (fraud class):")
        for name, val in sorted(zip(FEATURE_NAMES, sv), key=lambda x: abs(x[1]), reverse=True)[:5]:
            direction = "-> risk" if val > 0 else "<- risk"
            print(f"      {name:>28}: {val:+.4f} ({direction})")
        print("   [OK] SHAP working correctly")
    except Exception as e:
        print(f"   [WARN] SHAP test failed: {e}")

    # ── Summary ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("[OK] Training Complete!")
    print("=" * 60)
    model_dir = os.path.join(os.path.dirname(__file__), "..", "ml_models")
    print(f"   Models saved to: {os.path.abspath(model_dir)}/")
    print(f"   XGBoost AUC-ROC:          {auc:.4f}")
    print(f"   Isolation Forest AUC-ROC: {iso_auc:.4f}")
    print(f"\n   The models are ready for use in the verification pipeline.")
    print(f"   Restart the backend server to load the new models.")


if __name__ == "__main__":
    main()
