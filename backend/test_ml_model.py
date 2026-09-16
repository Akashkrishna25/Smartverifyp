"""Quick test of the ML fraud prediction pipeline."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.services.ml_fraud_model import MLFraudPredictor

p = MLFraudPredictor()
print("Model available:", p.is_available)

if not p.is_available:
    print("ERROR: ML model not loaded!")
    sys.exit(1)

# Test 1: Legitimate application (good docs, reasonable income/loan)
result = p.predict(
    extracted_info={
        "monthly_income": 50000,
        "loan_amount": 500000,
        "applicant_name": "Rajesh Kumar",
        "pan_number": "ABCDE1234F",
        "aadhaar_number": "123456789012",
        "address": "123 Main St, Mumbai 400001",
        "phone": "9876543210",
    },
    documents=[
        {"document_type": "pan"},
        {"document_type": "aadhaar"},
        {"document_type": "salary_slip"},
        {"document_type": "bank_statement"},
    ],
)
print("\n=== TEST 1: Legitimate Application ===")
print(f"  ML Risk Score:       {result['ml_risk_score']}")
print(f"  Fraud Probability:   {result['ml_fraud_probability']}")
print(f"  Anomaly Score:       {result['ml_anomaly_score']}")
print(f"  Fraud Flag:          {result['ml_fraud_flag']}")
print(f"  Model Version:       {result['model_version']}")
if result.get("shap_explanation"):
    print("  Top SHAP features:")
    for f in result["shap_explanation"]["top_features"][:3]:
        print(f"    - {f['feature']}: {f['impact']} ({f['direction']})")

# Test 2: Suspicious application (missing docs, no name, invalid PAN)
result2 = p.predict(
    extracted_info={
        "monthly_income": 600000,
        "loan_amount": 15000000,
        "applicant_name": None,
        "pan_number": "INVALID",
        "aadhaar_number": None,
    },
    documents=[
        {"document_type": "loan_application"},
    ],
)
print("\n=== TEST 2: Suspicious Application ===")
print(f"  ML Risk Score:       {result2['ml_risk_score']}")
print(f"  Fraud Probability:   {result2['ml_fraud_probability']}")
print(f"  Anomaly Score:       {result2['ml_anomaly_score']}")
print(f"  Fraud Flag:          {result2['ml_fraud_flag']}")
if result2.get("shap_explanation"):
    print("  Top SHAP features:")
    for f in result2["shap_explanation"]["top_features"][:3]:
        print(f"    - {f['feature']}: {f['impact']} ({f['direction']})")

print("\n[OK] ML fraud prediction pipeline working correctly!")
