"""Loan Application ORM model."""
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.database import Base

class ApplicationStatus(str, enum.Enum):
    pending       = "pending"
    approved      = "approved"
    rejected      = "rejected"
    manual_review = "manual_review"

class Application(Base):
    __tablename__ = "applications"
    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False)
    applicant_name = Column(String(255))
    
    branch         = Column(String(255), nullable=True)
    loan_type      = Column(String(255), nullable=True)
    loan_amount    = Column(Float, nullable=False)
    loan_tenure    = Column(Integer, nullable=True)
    interest_rate  = Column(Float, nullable=True)

    # Applicant persistent fields
    aadhaar_number = Column(String(20), nullable=True)
    pan_number     = Column(String(20), nullable=True)
    dob            = Column(String(50), nullable=True)
    gender         = Column(String(50), nullable=True)
    address        = Column(String(500), nullable=True)
    father_name    = Column(String(255), nullable=True)
    
    status         = Column(SAEnum(ApplicationStatus), default=ApplicationStatus.pending)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user      = relationship("User", back_populates="applications")
    documents = relationship("Document", back_populates="application", cascade="all, delete-orphan")
    report    = relationship("VerificationReport", back_populates="application", uselist=False,
                             cascade="all, delete-orphan")
    site_verification = relationship("SiteVerification", back_populates="application", uselist=False,
                                     cascade="all, delete-orphan")
    gov_verification = relationship("GovVerification", back_populates="application", uselist=False,
                                    cascade="all, delete-orphan")
    joint_applicants = relationship("JointApplicant", back_populates="application", cascade="all, delete-orphan")
    property_details = relationship("PropertyDetails", back_populates="application", uselist=False, cascade="all, delete-orphan")
class SiteVerification(Base):
    __tablename__ = "site_verifications"
    id              = Column(Integer, primary_key=True, index=True)
    application_id  = Column(Integer, ForeignKey("applications.id"), nullable=False, unique=True)
    gps_coordinates      = Column(String(255), nullable=True)
    officer_name         = Column(String(100), nullable=True)
    date                 = Column(String(50), nullable=True)
    time                 = Column(String(50), nullable=True)
    property_condition   = Column(String(100), nullable=True)
    construction_quality = Column(String(100), nullable=True)
    boundary_present     = Column(String(50), nullable=True)
    road_access          = Column(String(50), nullable=True)
    utilities_available  = Column(String(500), nullable=True)
    remarks              = Column(String(1000), nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)
    
    application = relationship("Application", back_populates="site_verification")


class JointApplicant(Base):
    __tablename__ = "joint_applicants"
    id             = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    index          = Column(Integer, nullable=False)
    relationship_type   = Column(String(100), nullable=True)
    mobile         = Column(String(20), nullable=True)
    email          = Column(String(255), nullable=True)
    remarks        = Column(String(1000), nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
    
    application    = relationship("Application", back_populates="joint_applicants")


class PropertyDetails(Base):
    __tablename__ = "property_details"
    id                  = Column(Integer, primary_key=True, index=True)
    application_id      = Column(Integer, ForeignKey("applications.id"), nullable=False, unique=True)
    property_type       = Column(String(100), nullable=True)
    address             = Column(String(500), nullable=True)
    village_city        = Column(String(100), nullable=True)
    taluk               = Column(String(100), nullable=True)
    district            = Column(String(100), nullable=True)
    state               = Column(String(100), nullable=True)
    pin_code            = Column(String(20), nullable=True)
    survey_number       = Column(String(100), nullable=True)
    khata_number        = Column(String(100), nullable=True)
    property_area       = Column(String(100), nullable=True)
    market_value        = Column(Float, nullable=True)
    loan_security_value = Column(Float, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)
    
    application         = relationship("Application", back_populates="property_details")


class GovVerification(Base):
    __tablename__ = "gov_verifications"
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, unique=True)
    pan_aadhaar_link_status = Column(String(50), nullable=True)
    tax_receipt_status = Column(String(50), nullable=True)
    aadhaar_validity_status = Column(String(50), nullable=True)
    aadhaar_screenshot_path = Column(String(1000), nullable=True)
    officer_name = Column(String(100), nullable=True)
    timestamp = Column(String(100), nullable=True)
    remarks = Column(String(1000), nullable=True)
    screenshot_path = Column(String(1000), nullable=True)
    verification_screenshots = Column(String(1000), nullable=True) # Kept for backward compatibility
    created_at = Column(DateTime, default=datetime.utcnow)
    
    application = relationship("Application", back_populates="gov_verification")
