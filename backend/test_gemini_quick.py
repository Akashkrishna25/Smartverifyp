"""
Quick Gemini connectivity + agent pipeline test.
Run from backend/ with: venv\\Scripts\\python.exe test_gemini_quick.py
"""
import sys, os, json, time

sys.path.insert(0, r"C:\Users\Hp\Desktop\Smartverify2\backend")
os.environ.setdefault("DATABASE_URL", "sqlite:///./smartverify.db")
os.environ.setdefault("SECRET_KEY", "test-secret")

print("=" * 60)
print("SMARTVERIFY — GEMINI MIGRATION TEST")
print("=" * 60)

# ── 1. Config check ─────────────────────────────────────────────────
print("\n[1] Checking config...")
from app.core.config import settings
assert settings.CREWAI_MODEL == "gemini/gemini-2.5-flash", f"Wrong model: {settings.CREWAI_MODEL}"
print(f"    CREWAI_MODEL   : {settings.CREWAI_MODEL}  OK")
print(f"    GEMINI_API_KEY : {'SET OK' if settings.gemini_api_key else 'MISSING'}")

# ── 2. LLM object check ─────────────────────────────────────────────
print("\n[2] Building LLM object...")
from app.agents.agent_definitions import get_llm, build_agents
llm = get_llm()
print(f"    llm.model      : {llm.model}  OK")

# ── 3. Agent construction ───────────────────────────────────────────
print("\n[3] Building all 5 agents...")
agents = build_agents(db_session=None)
expected = ["document_analyst","extraction_specialist","verification_officer",
            "gov_verification_agent","compliance_reporter"]
for key in expected:
    assert key in agents, f"Missing agent: {key}"
    print(f"    OK {agents[key].role}")

# ── 4. Full crew run (minimal data) ─────────────────────────────────
print("\n[4] Running full CrewAI pipeline with Gemini...")
print("    (This calls all 5 agents - may take 60-180 seconds)")

from app.agents.crew import LoanVerificationCrew

crew_runner = LoanVerificationCrew(db_session=None)
t0 = time.time()
result = crew_runner.run(
    application_id=9999,
    applicant_name="Test Applicant Gemini",
    loan_amount=500000.0,
    documents=[
        {
            "id": 1,
            "document_type": "aadhaar",
            "file_path": "test.jpg",
            "original_name": "aadhaar_test.jpg",
            "structured_data": json.dumps({
                "applicant_name": "Test Applicant Gemini",
                "aadhaar_number": "123456789012",
                "dob": "01/01/1990",
                "gender": "Male",
                "address": "123 Test St, Bangalore 560001",
                "pan_number": "ABCDE1234F",
                "employer_name": "Test Corp",
                "monthly_income": 75000,
                "bank_account": "9876543210",
            }),
            "extracted_text": "Test Applicant Gemini | Aadhaar: 1234 5678 9012 | DOB: 01/01/1990",
        }
    ],
    loan_type="Home Loan",
    loan_tenure=240,
    gov_verification_record={
        "aadhaar_verified": True,
        "pan_verified": True,
        "aadhaar_number": "123456789012",
        "pan_number": "ABCDE1234F",
    },
)
elapsed = time.time() - t0

print(f"\n{'='*60}")
print(f"CREW COMPLETED in {elapsed:.1f}s")
print(f"{'='*60}")
print(f"  final_status       : {result.get('final_status')}")
print(f"  verification_score : {result.get('verification_score')}")
print(f"  risk_score         : {result.get('risk_score')}")
print(f"  fraud_flag         : {result.get('fraud_flag')}")
print(f"  summary (first 200): {str(result.get('summary',''))[:200]}")
print(f"  agent_trace length : {len(result.get('agent_trace',''))} chars")
print(f"\nALL 5 AGENTS EXECUTED SUCCESSFULLY WITH GOOGLE GEMINI")
