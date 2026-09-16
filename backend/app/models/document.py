"""Document ORM model."""
# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SAEnum
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.database import Base

class DocumentType(str, enum.Enum):
    aadhaar          = "aadhaar"
    pan              = "pan"
    salary_slip      = "salary_slip"
    employment_cert  = "employment_cert"
    income_cert      = "income_cert"
    form_16          = "form_16"
    bank_statement   = "bank_statement"
    loan_application = "loan_application"
    
    # Property & Site Verification
    sale_deed        = "sale_deed"
    tax_receipt      = "tax_receipt"
    encumbrance_cert = "encumbrance_cert"
    property_image   = "property_image"
    
    site_front_view  = "site_front_view"
    site_side_view   = "site_side_view"
    site_interior    = "site_interior"
    site_entrance    = "site_entrance"
    site_landmark    = "site_landmark"

class Document(Base):
    __tablename__ = "documents"
    id             = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    document_type  = Column(SAEnum(DocumentType), nullable=False)
    file_path      = Column(String(500), nullable=False)
    original_name  = Column(String(255))
    extracted_text = Column(Text)
    structured_data = Column(Text)  # JSON string containing NLP extracted fields
    processed      = Column(Integer, default=0)  # 0=raw,1=preprocessed,2=ocr-done
    joint_applicant_index = Column(Integer, nullable=True, default=None)
    created_at     = Column(DateTime, default=datetime.utcnow)
    application = relationship("Application", back_populates="documents")
