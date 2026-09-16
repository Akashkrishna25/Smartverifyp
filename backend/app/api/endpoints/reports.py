"""Report retrieval endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from app.db.database import get_db
from app.models.verification_report import VerificationReport
from app.models.user import User
from app.schemas.report import ReportOut
from app.core.security import get_current_user
from app.services.report_service import generate_report

router = APIRouter()


@router.get("/{application_id}", response_model=ReportOut)
def get_report(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(VerificationReport).filter(
        VerificationReport.application_id == application_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{application_id}/download")
def download_report(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(VerificationReport).filter(
        VerificationReport.application_id == application_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Always regenerate to ensure the current report engine (V6) is used.
    try:
        pdf_path = generate_report(application_id=application_id, db=db)
        report.pdf_path = pdf_path
        db.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"SmartVerify_Report_{application_id}.pdf",
    )


@router.post("/{application_id}/regenerate-pdf")
def regenerate_pdf(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """On-demand PDF regeneration without re-running the AI pipeline."""
    report = db.query(VerificationReport).filter(
        VerificationReport.application_id == application_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found. Run AI verification first.")

    try:
        pdf_path = generate_report(application_id=application_id, db=db)
        report.pdf_path = pdf_path
        db.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    return {"message": "PDF regenerated successfully", "pdf_path": pdf_path}
