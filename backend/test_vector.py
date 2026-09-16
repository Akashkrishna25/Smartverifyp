import sys, json, os, logging
sys.path.insert(0, r'C:\Users\Hp\Desktop\Smartverify2\backend')
from app.services.vector_service import VectorService
v = VectorService()
print('--- POLICIES ---')
print(json.dumps(v.retrieve_policies('loan eligibility'), indent=2))
print('--- SIMILAR APPS ---')
print(json.dumps(v.find_similar_applications({'applicant_name': 'Rahul Sharma', 'loan_amount': 2500000.0}), indent=2))
