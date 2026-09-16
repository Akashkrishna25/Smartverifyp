"""Pydantic schemas for VerificationReport."""
# pyrefly: ignore [missing-import]
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any

class ReportOut(BaseModel):
    verification_score: float
    risk_score: float
    fraud_flag: bool
    status: str
    extracted_info: Optional[Any]
    fraud_analysis: Optional[Any]
    verification_details: Optional[Any]
    pdf_path: Optional[str]
    verification_mode: Optional[str] = "rule_based"
    agent_summary: Optional[str] = None
    agent_trace: Optional[Any] = None
    ml_prediction: Optional[Any] = None
    created_at: datetime
    class Config:
        from_attributes = True

