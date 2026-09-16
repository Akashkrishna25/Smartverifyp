"""Dashboard analytics endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.db.database import get_db
from app.models.application import Application
from app.models.verification_report import VerificationReport
from app.models.document import Document
from app.models.user import User
from app.core.security import get_current_user

router = APIRouter()


from typing import Optional

@router.get("/stats")
def get_stats(branch: Optional[str] = None, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Return aggregate statistics for the dashboard."""
    base_q = db.query(Application)
    if current_user.role != "admin":
        base_q = base_q.filter(Application.user_id == current_user.id)
    
    if branch:
        base_q = base_q.filter(Application.branch == branch)

    pending_apps = base_q.filter(Application.status == "pending").count()
    under_verification = base_q.filter(Application.status == "manual_review").count()
    
    # Pending Site Visits = Applications without a SiteVerification
    pending_site_visits = base_q.outerjoin(Application.site_verification).filter(
        Application.site_verification == None
    ).count()

    # Monthly applications trend
    if db.bind.dialect.name == "sqlite":
        month_expr = func.strftime("%Y-%m", Application.created_at)
    else:
        month_expr = func.date_trunc("month", Application.created_at)

    monthly = db.query(
        month_expr.label("month"),
        func.count(Application.id).label("count"),
    )
    if current_user.role != "admin":
        monthly = monthly.filter(Application.user_id == current_user.id)
    if branch:
        monthly = monthly.filter(Application.branch == branch)
        
    monthly = monthly.group_by("month").order_by(text("month")).limit(6).all()

    return {
        "pending_applications": pending_apps,
        "applications_under_verification": under_verification,
        "pending_site_visits": pending_site_visits,
        "average_processing_time": "2.4 Days", # Placeholder or calculated value
        "monthly_trend": [
            {"month": str(m.month)[:7], "count": m.count} for m in monthly if m.month
        ],
    }
