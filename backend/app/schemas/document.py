"""Pydantic schemas for Document."""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.document import DocumentType

class DocumentOut(BaseModel):
    id: int
    application_id: int
    document_type: DocumentType
    file_path: str
    original_name: Optional[str]
    extracted_text: Optional[str] = None
    structured_data: Optional[str] = None
    processed: int
    joint_applicant_index: Optional[int] = None
    created_at: datetime
    class Config:
        from_attributes = True
