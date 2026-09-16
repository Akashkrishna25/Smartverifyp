"""Document upload and processing endpoints."""
import os, uuid, logging, json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models.document import Document, DocumentType
from app.models.application import Application
from app.models.user import User
from app.schemas.document import DocumentOut
from app.core.security import get_current_user
from app.core.config import settings
from app.services.preprocessing import preprocess_image
from app.services.ocr_service import extract_text
from app.services.nlp_service import extract_information
from app.services.classification_service import classify_document

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


from typing import List, Optional

@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload_document(
    application_id: int = Form(...),
    document_type: str = Form(...),
    joint_applicant_index: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a single document for an application."""
    # Validate application ownership
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if current_user.role != "admin" and app.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed")

    # Read and size-check
    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large")

    # Persist file
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    # Validate document_type enum
    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid document_type: {document_type}")

    doc = Document(
        application_id=application_id,
        document_type=doc_type,
        joint_applicant_index=joint_applicant_index,
        file_path=file_path,
        original_name=file.filename,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    logger.info(f"Document {doc.id} uploaded for application {application_id}")
    return doc


@router.post("/process/{document_id}", response_model=DocumentOut)
async def process_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Process a document using Vision AI (primary) and OCR (secondary)."""
    from app.services.vision_service import extract_structured_data
    from app.services.confidence_engine import process_document_confidence
    import re

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc_type_val = doc.document_type.value

    # 1. Vision AI (Primary Extraction on ORIGINAL image)
    vision_result = extract_structured_data(doc.file_path, doc_type_val)
    if vision_result and vision_result.get("status") == "failed":
        # Graceful fallback: log warning and proceed with local OCR pipeline
        logger.warning(f"Vision API unavailable or failed ({vision_result.get('error_type')}). Proceeding with local OCR pipeline.")
        vision_data = {}
    else:
        vision_data = vision_result.get("data", {}) if vision_result else {}

    # 2. Preprocess for OCR
    if not doc.file_path.endswith(".pdf"):
        try:
            preprocessed_path = preprocess_image(doc.file_path)
        except Exception as e:
            logger.warning(f"Preprocessing failed: {e}")
            preprocessed_path = doc.file_path
    else:
        preprocessed_path = doc.file_path

    doc.processed = 1
    db.commit()

    # 3. OCR (Secondary/Primary Local Extraction)
    try:
        text = extract_text(preprocessed_path)
        doc.extracted_text = text
        
        # Run NLP on OCR text for fallback signals
        ocr_structured = extract_information(text, doc_type=doc_type_val)
        ocr_data = {k: v for k, v in ocr_structured.items() if k != "fields" and k != "document_type"}
    except Exception as e:
        logger.error(f"OCR/NLP failed for {document_id}: {e}")
        text = ""
        ocr_data = {}

    # 4. Field Validation (Format check on Vision or OCR output)
    validated_status = {}
    target_fields = ["applicant_name", "aadhaar_number", "dob", "gender", "address"] if doc_type_val == "aadhaar" else ["applicant_name", "father_name", "pan_number", "dob"]
    
    for f in target_fields:
        val = vision_data.get(f) or ocr_data.get(f)
        if not val:
            validated_status[f] = "not_found"
            continue
            
        status = "valid"
        if f == "aadhaar_number":
            clean_num = re.sub(r"[\s-]", "", str(val))
            if not re.match(r"^\d{12}$", clean_num):
                status = "invalid"
            else:
                if f in vision_data:
                    vision_data[f] = clean_num
                if f in ocr_data:
                    ocr_data[f] = clean_num
        elif f == "pan_number":
            clean_pan = str(val).strip().upper()
            if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", clean_pan):
                status = "invalid"
            else:
                if f in vision_data:
                    vision_data[f] = clean_pan
                if f in ocr_data:
                    ocr_data[f] = clean_pan
        elif f == "dob":
            if not re.search(r"\d{2}[/\-]\d{2}[/\-]\d{4}", str(val)):
                status = "needs_review"
                
        validated_status[f] = status

    # 5. Confidence Engine
    final_structured = process_document_confidence(doc_type_val, vision_data, ocr_data, validated_status)
    doc.structured_data = json.dumps(final_structured)
    
    doc.processed = 2
    db.commit()
    logger.info(f"Vision and OCR complete for document {document_id}")

    # 6. Cross-Document Validation & Auto-populate (if applicable)
    if doc_type_val in ["aadhaar", "pan"]:
        from app.services.cross_doc_validator import validate_cross_documents
        # Get all docs for this application
        all_docs = db.query(Document).filter(
            Document.application_id == doc.application_id,
            Document.processed == 2,
            Document.joint_applicant_index == None
        ).all()
        
        aadhaar_doc = next((d for d in all_docs if d.document_type.value == "aadhaar"), None)
        pan_doc = next((d for d in all_docs if d.document_type.value == "pan"), None)
        
        if aadhaar_doc and pan_doc and aadhaar_doc.structured_data and pan_doc.structured_data:
            try:
                a_data = json.loads(aadhaar_doc.structured_data)
                p_data = json.loads(pan_doc.structured_data)
                cross_val_result = validate_cross_documents(a_data, p_data)
                logger.info(f"Cross-Document Validation Result for app {doc.application_id}: {cross_val_result['overall_status']}")
                
                # Append cross validation to the document data or log it
                # For this implementation, we log it and it becomes available to CrewAI during verification
                
            except json.JSONDecodeError:
                pass

    db.refresh(doc)
    return doc


@router.get("/{application_id}", response_model=List[DocumentOut])
def list_documents(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Document).filter(Document.application_id == application_id).all()
