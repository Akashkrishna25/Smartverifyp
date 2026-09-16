import sys, json, os, logging
sys.path.insert(0, r'C:\Users\Hp\Desktop\Smartverify2\backend')
from app.db.database import SessionLocal
from app.agents.crew import LoanVerificationCrew

logging.basicConfig(level=logging.INFO)
db = SessionLocal()
crew = LoanVerificationCrew(db_session=db)

docs = [{
    'id': 1,
    'document_type': 'aadhaar',
    'structured_data': json.dumps({'applicant_name': 'Rahul Sharma', 'aadhaar_number': '123456789012'}),
    'extracted_text': 'Sample Aadhaar OCR text',
    'file_path': 'dummy.jpg',
    'original_name': 'aadhaar.jpg'
}]
gov_record = {
    'aadhaar_number': '123456789012',
    'aadhaar_status': 'Verified',
    'pan_status': 'Verified',
    'tax_receipt_status': 'Verified',
    'screenshot_uploaded': True,
    'timestamp': '2024-05-15T10:00:00Z',
    'officer_name': 'Test Officer',
    'remarks': 'Looks good'
}

print('Running Crew with RAG tools...')
result = crew.run(
    application_id=999,
    applicant_name='Rahul Sharma',
    loan_amount=2500000.0,
    documents=docs,
    loan_type='Home Loan',
    loan_tenure=60,
    gov_verification_record=gov_record
)
print('\n--- RESULT ---')
print(json.dumps(result, indent=2))
