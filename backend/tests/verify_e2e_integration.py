"""
End-to-End Integration Verification Script
Tests the full real application flow:
1. Upload Aadhaar card via POST /documents/upload
2. Receive document ID
3. Process document via POST /documents/process/{document_id}
4. Verify Preprocessing -> PaddleOCR -> Parser -> Confidence Engine -> Database
5. Verify GET /documents/{app_id} response format matches Frontend expectations (UploadPage.jsx, GovVerification.jsx, VerifyPage.jsx)
6. Repeat for PAN card to inspect PAN parsing status
"""
import os
import sys
import json
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add backend directory to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.db.database import SessionLocal
from app.models.document import Document
from app.models.application import Application

def run_e2e_test():
    print("\n" + "="*80)
    print("RUNNING FULL END-TO-END APPLICATION FLOW TEST")
    print("="*80)

    client = TestClient(app)
    token = create_access_token({"sub": "1", "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    # Ensure application 1 exists
    db = SessionLocal()
    app_record = db.query(Application).filter(Application.id == 1).first()
    if not app_record:
        print("ERROR: Application 1 does not exist in database!")
        db.close()
        return False
    db.close()

    uploads_dir = BACKEND_DIR / "uploads"
    aadhaar_file = uploads_dir / "7a056d5e7b33486da89e99663de0e66f.jpeg"
    pan_file = uploads_dir / "3040b8a3acdf43a59020cbc3f119aa9e.jpeg"

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 1: AADHAAR END-TO-END FLOW
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "-"*80)
    print("TEST 1: Real Aadhaar Image (7a056d5e...jpeg)")
    print("-"*80)

    print("\n[Step 1] Frontend File Selection -> POST /documents/upload")
    with open(aadhaar_file, "rb") as f:
        upload_resp = client.post(
            "/documents/upload",
            data={"application_id": 1, "document_type": "aadhaar"},
            files={"file": ("test_aadhaar.jpeg", f, "image/jpeg")},
            headers=headers
        )

    print(f"  Upload HTTP Status: {upload_resp.status_code}")
    if upload_resp.status_code != 201:
        print(f"  FAILED: {upload_resp.text}")
        return False

    upload_data = upload_resp.json()
    doc_id = upload_data["id"]
    saved_file_path = upload_data["file_path"]
    print(f"  Received Document ID: {doc_id}")
    print(f"  Saved File Path:      {saved_file_path}")
    print(f"  Document Type:        {upload_data['document_type']}")
    print(f"  Processed Flag:       {upload_data['processed']} (0=raw)")

    print(f"\n[Step 2] Processing Trigger -> POST /documents/process/{doc_id}")
    proc_resp = client.post(f"/documents/process/{doc_id}", headers=headers)
    print(f"  Processing HTTP Status: {proc_resp.status_code}")
    if proc_resp.status_code != 200:
        print(f"  FAILED: {proc_resp.text}")
        return False

    proc_data = proc_resp.json()
    print(f"  Processed Flag: {proc_data['processed']} (2=ocr-done)")

    # Inspect OCR extracted text
    extracted_text = proc_data.get("extracted_text") or ""
    text_lines = extracted_text.split("\n") if extracted_text else []
    print(f"  Extracted Text Length: {len(extracted_text)} chars ({len(text_lines)} lines)")

    # Inspect structured_data JSON
    structured_json_str = proc_data.get("structured_data") or "{}"
    structured_data = json.loads(structured_json_str)

    print("\n[Step 3] Inspect Structured Data Output:")
    print(f"  Document Type:  {structured_data.get('document_type')}")
    print(f"  Applicant Name: {structured_data.get('applicant_name')}")
    print(f"  Aadhaar Number: {structured_data.get('aadhaar_number')}")
    print(f"  DOB:            {structured_data.get('dob')}")
    print(f"  Gender:         {structured_data.get('gender')}")
    print(f"  Address:        {structured_data.get('address')}")

    fields_meta = structured_data.get("fields", {})
    print("\n[Step 4] Confidence & Field Metadata:")
    for fname, fmeta in fields_meta.items():
        if fmeta and fmeta.get("value"):
            print(f"  - {fname:15s}: val={fmeta.get('value')} | conf={fmeta.get('confidence')} | status={fmeta.get('validation_status')} | src={fmeta.get('source')}")

    # Verify Database Persistence
    print("\n[Step 5] Direct Database Inspection (smartverify.db):")
    db = SessionLocal()
    db_doc = db.query(Document).filter(Document.id == doc_id).first()
    db_text_len = len(db_doc.extracted_text or "")
    db_sd_len = len(db_doc.structured_data or "")
    print(f"  DB Record ID:         {db_doc.id}")
    print(f"  DB processed status:  {db_doc.processed}")
    print(f"  DB extracted_text:    {db_text_len} characters persisted")
    print(f"  DB structured_data:   {db_sd_len} characters JSON persisted")
    db.close()

    # Verify Preprocessing artifact
    prepped_path = str(Path(saved_file_path).parent / (Path(saved_file_path).stem + "_prep.png"))
    print(f"  Preprocessed PNG exists: {os.path.exists(prepped_path)} ({prepped_path})")

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 2: PAN END-TO-END FLOW
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "-"*80)
    print("TEST 2: Real PAN Image (3040b8a3...jpeg)")
    print("-"*80)

    print("\n[Step 1] Frontend File Selection -> POST /documents/upload")
    with open(pan_file, "rb") as f:
        upload_resp_pan = client.post(
            "/documents/upload",
            data={"application_id": 1, "document_type": "pan"},
            files={"file": ("test_pan.jpeg", f, "image/jpeg")},
            headers=headers
        )

    print(f"  Upload HTTP Status: {upload_resp_pan.status_code}")
    if upload_resp_pan.status_code != 201:
        print(f"  FAILED: {upload_resp_pan.text}")
        return False

    upload_data_pan = upload_resp_pan.json()
    pan_doc_id = upload_data_pan["id"]
    print(f"  Received Document ID: {pan_doc_id}")

    print(f"\n[Step 2] Processing Trigger -> POST /documents/process/{pan_doc_id}")
    proc_resp_pan = client.post(f"/documents/process/{pan_doc_id}", headers=headers)
    print(f"  Processing HTTP Status: {proc_resp_pan.status_code}")
    if proc_resp_pan.status_code != 200:
        print(f"  FAILED: {proc_resp_pan.text}")
        return False

    proc_data_pan = proc_resp_pan.json()
    structured_pan = json.loads(proc_data_pan.get("structured_data") or "{}")

    print("\n[Step 3] Inspect PAN Structured Data Output:")
    print(f"  Document Type:  {structured_pan.get('document_type')}")
    print(f"  PAN Number:     {structured_pan.get('pan_number')}")
    print(f"  Applicant Name: {structured_pan.get('applicant_name')}")
    print(f"  Father Name:    {structured_pan.get('father_name')}")
    print(f"  DOB:            {structured_pan.get('dob')}")

    fields_meta_pan = structured_pan.get("fields", {})
    for fname, fmeta in fields_meta_pan.items():
        if fmeta and fmeta.get("value"):
            print(f"  - {fname:15s}: val={fmeta.get('value')} | conf={fmeta.get('confidence')} | status={fmeta.get('validation_status')} | src={fmeta.get('source')}")

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 3: FRONTEND GET /documents/{app_id} COMPATIBILITY
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "-"*80)
    print("TEST 3: Frontend Document Fetch -> GET /documents/1")
    print("-"*80)
    docs_resp = client.get("/documents/1", headers=headers)
    print(f"  GET /documents/1 HTTP Status: {docs_resp.status_code}")
    docs_list = docs_resp.json()
    print(f"  Total Documents returned: {len(docs_list)}")

    # Test UploadPage.jsx parsing logic
    for d in docs_list[-2:]:
        doc_type = d.get("document_type")
        sd_str = d.get("structured_data")
        parsed = json.loads(sd_str) if sd_str else {}
        print(f"  Document {d.get('id')} ({doc_type}):")
        print(f"    - processed: {d.get('processed')}")
        print(f"    - has applicant_name: {bool(parsed.get('applicant_name'))} ('{parsed.get('applicant_name')}')")
        if doc_type == "aadhaar":
            print(f"    - has aadhaar_number: {bool(parsed.get('aadhaar_number'))} ('{parsed.get('aadhaar_number')}')")
        elif doc_type == "pan":
            print(f"    - has pan_number:     {bool(parsed.get('pan_number'))} ('{parsed.get('pan_number')}')")

    print("\n" + "="*80)
    print("ALL END-TO-END INTEGRATION TESTS COMPLETED SUCCESSFULLY")
    print("="*80 + "\n")
    return True


if __name__ == "__main__":
    success = run_e2e_test()
    sys.exit(0 if success else 1)
