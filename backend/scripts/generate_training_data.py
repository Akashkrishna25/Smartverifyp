"""
Synthetic Training Data Generator for SmartVerify ML Fraud Model
─────────────────────────────────────────────────────────────────
Generates ~2000 realistic loan application samples:
  - 85% legitimate applications
  - 15% fraudulent applications (with realistic fraud patterns)

Fraud patterns modelled (based on Indian loan fraud statistics):
  1. Missing critical documents
  2. Inflated income claims
  3. Extreme loan-to-income ratios
  4. Invalid PAN/Aadhaar formats
  5. Missing identity information
  6. Suspiciously low documentation

Usage:
    python scripts/generate_training_data.py
"""

import os
import sys
# pyrefly: ignore [missing-import]
import numpy as np
import pandas as pd

# Ensure the backend directory is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.ml_fraud_model import FEATURE_NAMES

np.random.seed(42)

TOTAL_SAMPLES = 2000
FRAUD_RATE = 0.15
N_FRAUD = int(TOTAL_SAMPLES * FRAUD_RATE)
N_LEGIT = TOTAL_SAMPLES - N_FRAUD


def generate_legitimate(n: int) -> pd.DataFrame:
    """Generate legitimate loan application feature vectors."""
    data = {
        # Income: ₹25K–₹2L/month (normal working range)
        "monthly_income": np.random.uniform(25_000, 200_000, n),
        # Loan: ₹1L–₹50L (typical personal/home loan)
        "loan_amount": np.random.uniform(100_000, 5_000_000, n),
        # Documents: legitimate apps tend to have most docs
        "has_aadhaar": np.random.choice([1.0, 0.0], n, p=[0.95, 0.05]),
        "has_pan": np.random.choice([1.0, 0.0], n, p=[0.93, 0.07]),
        "has_salary_slip": np.random.choice([1.0, 0.0], n, p=[0.88, 0.12]),
        "has_bank_statement": np.random.choice([1.0, 0.0], n, p=[0.80, 0.20]),
        # Total documents: 3–6
        "num_documents": np.random.randint(3, 7, n).astype(float),
        # Valid formats
        "pan_valid": np.random.choice([1.0, 0.0], n, p=[0.92, 0.08]),
        "aadhaar_valid": np.random.choice([1.0, 0.0], n, p=[0.94, 0.06]),
        # Identity data present
        "name_present": np.random.choice([1.0, 0.0], n, p=[0.96, 0.04]),
        "address_present": np.random.choice([1.0, 0.0], n, p=[0.85, 0.15]),
        "phone_present": np.random.choice([1.0, 0.0], n, p=[0.88, 0.12]),
    }
    df = pd.DataFrame(data)

    # Derived features
    df["loan_to_income_ratio"] = df["loan_amount"] / (df["monthly_income"] * 12)
    df["income_to_threshold_ratio"] = df["monthly_income"] / 25_000.0
    required_docs = df[["has_aadhaar", "has_pan", "has_salary_slip", "has_bank_statement"]]
    df["doc_completeness_score"] = required_docs.sum(axis=1) / 4.0

    df["is_fraud"] = 0
    return df


def generate_fraudulent(n: int) -> pd.DataFrame:
    """Generate fraudulent application feature vectors with realistic fraud signals."""
    data = {
        # Income: often inflated (₹0–₹8L) or suspiciously round numbers
        "monthly_income": np.concatenate([
            np.random.uniform(0, 10_000, n // 4),         # Very low (can't afford)
            np.random.uniform(500_001, 800_000, n // 4),   # Suspiciously high
            np.random.choice([100_000, 200_000, 500_000], n // 4),  # Round numbers
            np.random.uniform(30_000, 80_000, n - 3 * (n // 4)),   # Normal-ish
        ]),
        # Loan: often very high relative to income
        "loan_amount": np.concatenate([
            np.random.uniform(5_000_000, 20_000_000, n // 3),   # Extreme
            np.random.uniform(1_000_000, 5_000_000, n // 3),    # High
            np.random.uniform(100_000, 1_000_000, n - 2 * (n // 3)),  # Normal
        ]),
        # Documents: fraudulent apps often missing key docs
        "has_aadhaar": np.random.choice([1.0, 0.0], n, p=[0.55, 0.45]),
        "has_pan": np.random.choice([1.0, 0.0], n, p=[0.50, 0.50]),
        "has_salary_slip": np.random.choice([1.0, 0.0], n, p=[0.35, 0.65]),
        "has_bank_statement": np.random.choice([1.0, 0.0], n, p=[0.30, 0.70]),
        # Fewer total documents
        "num_documents": np.random.randint(1, 4, n).astype(float),
        # Invalid formats more common
        "pan_valid": np.random.choice([1.0, 0.0], n, p=[0.40, 0.60]),
        "aadhaar_valid": np.random.choice([1.0, 0.0], n, p=[0.45, 0.55]),
        # Identity data often missing
        "name_present": np.random.choice([1.0, 0.0], n, p=[0.55, 0.45]),
        "address_present": np.random.choice([1.0, 0.0], n, p=[0.35, 0.65]),
        "phone_present": np.random.choice([1.0, 0.0], n, p=[0.40, 0.60]),
    }
    df = pd.DataFrame(data)

    # Derived features
    df["loan_to_income_ratio"] = df.apply(
        lambda r: r["loan_amount"] / (r["monthly_income"] * 12) if r["monthly_income"] > 0 else 50.0,
        axis=1,
    )
    df["income_to_threshold_ratio"] = df["monthly_income"] / 25_000.0
    required_docs = df[["has_aadhaar", "has_pan", "has_salary_slip", "has_bank_statement"]]
    df["doc_completeness_score"] = required_docs.sum(axis=1) / 4.0

    df["is_fraud"] = 1
    return df


def main():
    print("=" * 60)
    print("SmartVerify — Synthetic Training Data Generator")
    print("=" * 60)

    legit_df = generate_legitimate(N_LEGIT)
    fraud_df = generate_fraudulent(N_FRAUD)

    # Combine and shuffle
    full_df = pd.concat([legit_df, fraud_df], ignore_index=True)
    full_df = full_df.sample(frac=1, random_state=42).reset_index(drop=True)

    # Reorder columns to match FEATURE_NAMES + label
    columns_order = FEATURE_NAMES + ["is_fraud"]
    full_df = full_df[columns_order]

    # Save
    output_dir = os.path.join(os.path.dirname(__file__), "..", "ml_models")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "training_data.csv")
    full_df.to_csv(output_path, index=False)

    print(f"\n[OK] Generated {len(full_df)} samples ({N_LEGIT} legit + {N_FRAUD} fraud)")
    print(f"[DIR] Saved to: {os.path.abspath(output_path)}")
    print(f"\nFeature columns: {FEATURE_NAMES}")
    print(f"\nClass distribution:")
    print(full_df["is_fraud"].value_counts().to_string())
    print(f"\nSample rows:")
    print(full_df.head(5).to_string())


if __name__ == "__main__":
    main()
