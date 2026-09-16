"""
Seed the ChromaDB Vector Database with initial policies and guidelines.
"""
import logging
from app.services.vector_service import VectorService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLICIES = [
    {
        "id": "policy_rbi_001",
        "text": "RBI Guidelines 2023: All loan applications exceeding ₹500,000 require a verified PAN card and the last 6 months of bank statements.",
        "metadata": {"type": "RBI_Guideline", "category": "KYC"}
    },
    {
        "id": "policy_kyc_002",
        "text": "KYC Rules: The Aadhaar card is mandatory for identity verification. The name on the Aadhaar must exactly match the loan application.",
        "metadata": {"type": "KYC_Rule", "category": "Identity"}
    },
    {
        "id": "policy_fraud_001",
        "text": "Fraud Rules: If an applicant has applied for more than 3 loans in the past month across any financial institution, flag the application for manual review due to high risk of loan stacking.",
        "metadata": {"type": "Fraud_Rule", "category": "Risk"}
    },
    {
        "id": "policy_loan_001",
        "text": "Bank Loan Eligibility: To be eligible for a personal loan, the applicant must have a minimum monthly income of ₹25,000 and be employed at the current company for at least 6 months.",
        "metadata": {"type": "Bank_Policy", "category": "Eligibility"}
    }
]

def seed_db():
    service = VectorService()
    if not service.client:
        logger.error("Vector service failed to initialize.")
        return
        
    for p in POLICIES:
        success = service.index_policy(doc_id=p["id"], text=p["text"], metadata=p["metadata"])
        if success:
            logger.info(f"Indexed policy: {p['id']}")
        else:
            logger.error(f"Failed to index policy: {p['id']}")
            
    logger.info("Database seeding completed.")

if __name__ == "__main__":
    seed_db()
