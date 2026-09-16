"""Application management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.application import Application
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationOut
from app.core.security import get_current_user

router = APIRouter()


@router.post("/", response_model=ApplicationOut, status_code=201)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new loan application."""
    app = Application(
        user_id=current_user.id,
        applicant_name=payload.applicant_name,
        aadhaar_number=payload.aadhaar_number,
        pan_number=payload.pan_number,
        dob=payload.dob,
        gender=payload.gender,
        address=payload.address,
        father_name=payload.father_name,
        branch=payload.branch,
        loan_type=payload.loan_type,
        loan_amount=payload.loan_amount,
        loan_tenure=payload.loan_tenure,
        interest_rate=payload.interest_rate,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@router.get("/", response_model=List[ApplicationOut])
def list_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List applications (admins see all; officers see their own)."""
    if current_user.role == "admin":
        return db.query(Application).order_by(Application.created_at.desc()).all()
    return db.query(Application).filter(Application.user_id == current_user.id)\
            .order_by(Application.created_at.desc()).all()


@router.get("/{app_id}", response_model=ApplicationOut)
def get_application(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if current_user.role != "admin" and app.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return app

from app.schemas.application import ApplicantDetailsUpdate

@router.put("/{app_id}/applicant_details", response_model=ApplicationOut)
def update_applicant_details(
    app_id: int,
    payload: ApplicantDetailsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update reviewed applicant details for an application."""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if current_user.role != "admin" and app.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(app, key, value)

    db.commit()
    db.refresh(app)
    return app


@router.delete("/{app_id}", status_code=204)
def delete_application(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if current_user.role != "admin" and app.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    db.delete(app)
    db.commit()

from app.schemas.application import SiteVerificationCreate, SiteVerificationOut, JointApplicantCreate, JointApplicantOut, PropertyDetailsCreate, PropertyDetailsOut
from app.models.application import SiteVerification, JointApplicant, PropertyDetails

@router.post("/{app_id}/site_verification", response_model=SiteVerificationOut, status_code=201)
def create_site_verification(
    app_id: int,
    payload: SiteVerificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if current_user.role != "admin" and app.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    site_ver = db.query(SiteVerification).filter(SiteVerification.application_id == app_id).first()
    if site_ver:
        # Update existing
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(site_ver, key, value)
    else:
        site_ver = SiteVerification(
            application_id=app_id,
            **payload.model_dump(exclude_unset=True)
        )
        db.add(site_ver)
    db.commit()
    db.refresh(site_ver)
    return site_ver

@router.post("/{app_id}/joint_applicants", response_model=JointApplicantOut, status_code=201)
def upsert_joint_applicant(
    app_id: int,
    payload: JointApplicantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if current_user.role != "admin" and app.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    ja = db.query(JointApplicant).filter(
        JointApplicant.application_id == app_id,
        JointApplicant.index == payload.index
    ).first()
    
    if ja:
        if payload.relationship is not None: ja.relationship_type = payload.relationship
        if payload.mobile is not None: ja.mobile = payload.mobile
        if payload.email is not None: ja.email = payload.email
        if payload.remarks is not None: ja.remarks = payload.remarks
    else:
        ja = JointApplicant(
            application_id=app_id,
            index=payload.index,
            relationship_type=payload.relationship,
            mobile=payload.mobile,
            email=payload.email,
            remarks=payload.remarks,
        )
        db.add(ja)
        
    db.commit()
    db.refresh(ja)
    return ja

@router.post("/{app_id}/property_details", response_model=PropertyDetailsOut, status_code=201)
def upsert_property_details(
    app_id: int,
    payload: PropertyDetailsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if current_user.role != "admin" and app.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    pd = db.query(PropertyDetails).filter(PropertyDetails.application_id == app_id).first()
    
    if pd:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(pd, key, value)
    else:
        pd = PropertyDetails(application_id=app_id, **payload.model_dump(exclude_unset=True))
        db.add(pd)
        
    db.commit()
    db.refresh(pd)
    return pd

from app.schemas.application import GovVerificationCreate, GovVerificationOut
from app.models.application import GovVerification

@router.post("/{app_id}/gov_verification", response_model=GovVerificationOut, status_code=201)
def upsert_gov_verification(
    app_id: int,
    payload: GovVerificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if current_user.role != "admin" and app.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    gv = db.query(GovVerification).filter(GovVerification.application_id == app_id).first()
    
    if gv:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(gv, key, value)
    else:
        gv = GovVerification(application_id=app_id, **payload.model_dump(exclude_unset=True))
        db.add(gv)
        
    db.commit()
    db.refresh(gv)
    return gv
