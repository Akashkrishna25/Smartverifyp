"""Verification pipeline endpoints.

Exposes three verification strategies sharing the same underlying
services and the same VerificationReport storage:

    GET  /verify/rag/{application_id}        – Hybrid RAG evidence retrieval
    POST /verify/{application_id}            – deterministic rule-based pipeline
    POST /verify/{application_id}/agentic    – CrewAI multi-agent pipeline
"""
import logging
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, Query
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.db.database import get_db
from app.models.application import Application
from app.models.document import Document
from app.models.verification_report import VerificationReport
from app.models.user import User
from app.schemas.report import ReportOut
from app.core.security import get_current_user
from app.core.config import settings
from app.services.nlp_service import extract_information
from app.services.verification_engine import VerificationEngine
from app.services.fraud_detection import FraudDetector
from app.services.report_service import generate_report

router = APIRouter()
logger = logging.getLogger(__name__)


def _load_application_and_documents(application_id: int, db: Session):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    docs = db.query(Document).filter(Document.application_id == application_id).all()
    if not docs:
        raise HTTPException(status_code=400, detail="No documents uploaded for this application")

    return app, docs


def _get_or_create_report(application_id: int, db: Session) -> VerificationReport:
    report = db.query(VerificationReport).filter(
        VerificationReport.application_id == application_id
    ).first()
    if not report:
        report = VerificationReport(application_id=application_id)
        db.add(report)
    return report


@router.post("/{application_id}", response_model=ReportOut)
def run_verification(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deterministic rule-based verification pipeline:
    1. Aggregate OCR text from all documents
    2. NLP extraction
    3. Verification engine
    4. Fraud detection
    5. PDF report generation
    """
    app, docs = _load_application_and_documents(application_id, db)

    # ── 1. Aggregate all OCR text ─────────────────────────────────────
    combined_text = " ".join(d.extracted_text or "" for d in docs)

    # ── 2. NLP extraction ─────────────────────────────────────────────
    extracted_info = extract_information(combined_text)
    if not extracted_info.get("loan_amount"):
        extracted_info["loan_amount"] = app.loan_amount
    if not extracted_info.get("applicant_name") and app.applicant_name:
        extracted_info["applicant_name"] = app.applicant_name

    # ── 3. Verification engine ────────────────────────────────────────
    doc_dicts = [{"document_type": d.document_type, "id": d.id} for d in docs]
    engine = VerificationEngine()
    verification_result = engine.verify(extracted_info, doc_dicts)

    # ── 4. Fraud detection ────────────────────────────────────────────
    detector = FraudDetector()
    fraud_result = detector.analyse(extracted_info, doc_dicts, application_id, db)

    # ── 5. Determine final status ─────────────────────────────────────
    final_status = verification_result["status"]
    if fraud_result["fraud_flag"]:
        final_status = "rejected"

    # ── 6. Update application status ─────────────────────────────────
    app.status = final_status
    if extracted_info.get("applicant_name") and not app.applicant_name:
        app.applicant_name = extracted_info["applicant_name"]
    db.commit()

    # ── 7. PDF report ─────────────────────────────────────────────────
    try:
        pdf_path = generate_report(application_id=app.id, db=db)
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        pdf_path = None

    # ── 8. Save / update report record ───────────────────────────────
    report = _get_or_create_report(application_id, db)
    report.verification_score   = verification_result["verification_score"]
    report.risk_score           = fraud_result["risk_score"]
    report.fraud_flag           = fraud_result["fraud_flag"]
    report.status               = final_status
    report.extracted_info       = extracted_info
    report.fraud_analysis       = fraud_result
    report.verification_details = verification_result
    report.pdf_path             = pdf_path
    report.verification_mode    = "rule_based"
    report.agent_summary        = None
    report.agent_trace          = None
    report.ml_prediction        = fraud_result.get("ml_prediction")
    db.commit()
    db.refresh(report)

    logger.info(f"[rule_based] Verification complete for app {application_id}: {final_status}")
    return report


@router.post("/{application_id}/agentic", response_model=ReportOut)
def run_agentic_verification(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Multi-agent (CrewAI) verification pipeline.

    A crew of five specialised agents collaborates to read documents,
    extract applicant information, apply verification rules, assess
    fraud risk, and compile the final PDF report:

        Document Analyst → Data Extraction Specialist
            → Loan Verification Officer
            → Fraud Investigator
                → Compliance Reporter

    The underlying tools call the exact same deterministic services as
    POST /verify/{application_id}, so results are explainable and
    consistent — the agents add reasoning, cross-checking, and a
    natural-language summary on top.
    """
    if not settings.CREWAI_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Agentic verification is disabled (CREWAI_ENABLED=false).",
        )

    app, docs = _load_application_and_documents(application_id, db)

    doc_payload = [
        {
            "id": d.id,
            "document_type": d.document_type.value if hasattr(d.document_type, "value") else d.document_type,
            "file_path": d.file_path,
            "original_name": d.original_name,
            "structured_data": d.structured_data,
            "extracted_text": d.extracted_text,
        }
        for d in docs
    ]

    # Import here to avoid CrewAI/LLM provider startup cost on every
    # request to the non-agentic endpoint.
    from app.agents.crew import LoanVerificationCrew

    from app.models.application import GovVerification
    gov_ver = db.query(GovVerification).filter(GovVerification.application_id == application_id).first()
    gov_record = {}
    if gov_ver:
        gov_record = {
            # V2: unified PAN-Aadhaar Link status
            "pan_aadhaar_link_status": gov_ver.pan_aadhaar_link_status,
            # V3: New Aadhaar Validity status
            "aadhaar_validity_status": gov_ver.aadhaar_validity_status,
            "aadhaar_screenshot_path": gov_ver.aadhaar_screenshot_path,
            "tax_receipt_status": gov_ver.tax_receipt_status,
            "officer_name": gov_ver.officer_name,
            "timestamp": gov_ver.timestamp,
            "remarks": gov_ver.remarks,
            "screenshot_path": gov_ver.screenshot_path,
        }

    try:
        crew = LoanVerificationCrew(db_session=db)
        result = crew.run(
            application_id=application_id,
            applicant_name=app.applicant_name or "",
            loan_amount=app.loan_amount,
            loan_type=app.loan_type or "Home Loan",
            loan_tenure=app.loan_tenure or 60,
            documents=doc_payload,
            gov_verification_record=gov_record,
        )
    except Exception as e:
        logger.error(f"Agentic verification crew failed for app {application_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Agentic verification failed: {e}")

    final_status        = result["final_status"]
    extracted_info       = result.get("extracted_info") or {}
    verification_result = result.get("verification_details") or {}
    fraud_result         = result.get("fraud_analysis") or {}
    pdf_path             = result.get("pdf_path")

    # ── Update application status ─────────────────────────────────────
    app.status = final_status
    if extracted_info.get("applicant_name") and not app.applicant_name:
        app.applicant_name = extracted_info["applicant_name"]
    db.commit()

    # ── Fallback: if the crew failed to produce a PDF, generate one
    #    deterministically so the user always has a downloadable report. ──
    if not pdf_path:
        try:
            pdf_path = generate_report(application_id=application_id, db=db)
        except Exception as e:
            logger.error(f"Fallback PDF generation failed: {e}")
            pdf_path = None

    # ── Save / update report record ───────────────────────────────────
    report = _get_or_create_report(application_id, db)
    report.verification_score   = result.get("verification_score", 0.0)
    report.risk_score           = result.get("risk_score", 0.0)
    report.fraud_flag           = result.get("fraud_flag", False)
    report.status               = final_status
    report.extracted_info       = extracted_info
    report.fraud_analysis       = fraud_result
    report.verification_details = verification_result
    report.pdf_path             = pdf_path
    report.verification_mode    = "agentic"
    report.agent_summary        = result.get("summary")
    report.agent_trace          = {
        "raw": result.get("agent_trace"),
        "agent_findings": result.get("agent_findings", {}),
        "recommendation": result.get("recommendation", ""),
        "human_review": result.get("human_review", ""),
    }
    
    # New Multi-Agent Fields (Phases 6, 7, 8)
    report.confidence_score     = result.get("confidence_score", 0.0)
    report.explainable_ai       = result.get("explainable_ai", {})
    report.agent_memory         = result.get("agent_memory", [])
    report.execution_timeline   = result.get("execution_timeline", {})
    report.ml_prediction        = fraud_result.get("ml_prediction") if isinstance(fraud_result, dict) else None
    
    db.commit()
    db.refresh(report)

    # ── Store Application in Vector Database for Similarity Search (Phase 3) ──
    try:
        from app.services.vector_service import VectorService
        VectorService().store_application_vector(
            app_id=application_id,
            extracted_info=extracted_info,
            fraud_result=fraud_result,
            verification_score=report.verification_score,
            status=final_status
        )
    except Exception as e:
        logger.error(f"Failed to index application for similarity search: {e}")

    logger.info(f"[agentic] Verification complete for app {application_id}: {final_status}")
    return report


# ─────────────────────────────────────────────────────────────────────────────
# Hybrid RAG + Reranking Evidence Retrieval Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/rag/{application_id}", response_model=Dict[str, Any])
def rag_evidence_retrieval(
    application_id: int,
    query: str = Query(
        default="What information supports this loan application?",
        description=(
            "Natural language question about the loan application. "
            "Examples: 'What is the applicant income?', "
            "'Is KYC verified?', 'What is the loan amount?'"
        ),
    ),
    top_k: int = Query(
        default=5,
        ge=1,
        le=20,
        description="Number of top evidence chunks to return (1–20).",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    **Hybrid RAG Evidence Retrieval**

    Retrieves the most relevant evidence from the loan application data
    using a Hybrid RAG (Retrieval-Augmented Generation) pipeline:

    1. **Document Builder** — Converts all DB records to text chunks
    2. **BM25** — Keyword-based retrieval (exact term matching)
    3. **FAISS** — Semantic vector search (meaning-based retrieval)
    4. **RRF Fusion** — Combines BM25 and FAISS rankings
    5. **Cross-Encoder Reranker** — Precision reranking of top candidates

    ⚠️ This endpoint returns **evidence only**.
    It does NOT approve or reject the loan application.
    Use POST /verify/{application_id} for the full verification decision.

    **Example queries:**
    - `What is the applicant's income?`
    - `Is KYC verified?`
    - `What is the requested loan amount?`
    - `What is the vehicle or property verification status?`
    - `What information supports this loan application?`
    """
    # Verify application exists before running the expensive pipeline
    application = db.query(Application).filter(
        Application.id == application_id
    ).first()
    if not application:
        raise HTTPException(
            status_code=404,
            detail=f"Application with id={application_id} not found."
        )

    logger.info(
        f"[RAG endpoint] application_id={application_id}, "
        f"query='{query}', top_k={top_k}"
    )

    try:
        from app.rag.pipeline import smartverify_rag
        result = smartverify_rag(
            application_id=application_id,
            query=query,
            db=db,
            top_k=top_k,
        )
    except Exception as e:
        logger.error(f"RAG pipeline failed for app {application_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"RAG pipeline error: {str(e)}"
        )

    return result


@router.get("/rag/{application_id}/batch", response_model=list)
def rag_batch_evidence_retrieval(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    **Batch RAG Evidence Retrieval** — runs all standard viva demo queries at once.

    Useful for generating a full evidence report during a demo or viva.
    Builds the index once and runs 5 standard queries efficiently.

    ⚠️ Returns evidence only. Does NOT make any loan decision.
    """
    application = db.query(Application).filter(
        Application.id == application_id
    ).first()
    if not application:
        raise HTTPException(
            status_code=404,
            detail=f"Application with id={application_id} not found."
        )

    standard_queries = [
        "What is the applicant's income?",
        "Is KYC verified?",
        "What is the requested loan amount and type?",
        "What is the property or vehicle verification status?",
        "What information supports this loan application?",
    ]

    try:
        from app.rag.pipeline import batch_smartverify_rag
        results = batch_smartverify_rag(
            application_id=application_id,
            queries=standard_queries,
            db=db,
            top_k=3,
        )
    except Exception as e:
        logger.error(f"Batch RAG pipeline failed for app {application_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Batch RAG pipeline error: {str(e)}"
        )

    return results
