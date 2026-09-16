"""Verification Report ORM model."""
# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Boolean, JSON
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class VerificationReport(Base):
    __tablename__ = "verification_reports"
    id                   = Column(Integer, primary_key=True, index=True)
    application_id       = Column(Integer, ForeignKey("applications.id"), unique=True, nullable=False)
    verification_score   = Column(Float, default=0.0)
    risk_score           = Column(Float, default=0.0)
    fraud_flag           = Column(Boolean, default=False)
    status               = Column(String(50), default="pending")
    extracted_info       = Column(JSON)
    fraud_analysis       = Column(JSON)
    verification_details = Column(JSON)
    pdf_path             = Column(String(500))
    # ── Multi-agent (CrewAI) fields ───────────────────────────────────────
    verification_mode    = Column(String(20), default="rule_based")  # "rule_based" | "agentic"
    agent_summary        = Column(String(2000), nullable=True)
    agent_trace          = Column(JSON, nullable=True)
    
    # ── Multi-agent Intelligence fields (Phase 2 Upgrade) ────────────────
    confidence_score     = Column(Float, default=0.0)
    execution_timeline   = Column(JSON, nullable=True)
    agent_memory         = Column(JSON, nullable=True)
    explainable_ai       = Column(JSON, nullable=True)

    # ── ML Fraud Prediction (XGBoost + Isolation Forest + SHAP) ────────
    ml_prediction        = Column(JSON, nullable=True)
    
    created_at           = Column(DateTime, default=datetime.utcnow)
    application = relationship("Application", back_populates="report")

