from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from app.models.application import ApplicationStatus

class SiteVerificationCreate(BaseModel):
    gps_coordinates: Optional[str] = None
    officer_name: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    property_condition: Optional[str] = None
    construction_quality: Optional[str] = None
    boundary_present: Optional[str] = None
    road_access: Optional[str] = None
    utilities_available: Optional[str] = None
    remarks: Optional[str] = None

class SiteVerificationOut(BaseModel):
    id: int
    application_id: int
    gps_coordinates: Optional[str]
    officer_name: Optional[str]
    date: Optional[str]
    time: Optional[str]
    property_condition: Optional[str]
    construction_quality: Optional[str]
    boundary_present: Optional[str]
    road_access: Optional[str]
    utilities_available: Optional[str]
    remarks: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

class ApplicationCreate(BaseModel):
    loan_amount: float
    branch: Optional[str] = None
    loan_type: Optional[str] = None
    loan_tenure: Optional[int] = None
    interest_rate: Optional[float] = None
    applicant_name: Optional[str] = None
    aadhaar_number: Optional[str] = None
    pan_number: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    father_name: Optional[str] = None

class ApplicantDetailsUpdate(BaseModel):
    applicant_name: Optional[str] = None
    aadhaar_number: Optional[str] = None
    pan_number: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    father_name: Optional[str] = None

class JointApplicantCreate(BaseModel):
    index: int
    relationship: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    remarks: Optional[str] = None

class JointApplicantOut(BaseModel):
    id: int
    application_id: int
    index: int
    relationship: Optional[str] = Field(None, validation_alias="relationship_type")
    mobile: Optional[str]
    email: Optional[str]
    remarks: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

class PropertyDetailsCreate(BaseModel):
    property_type: Optional[str] = None
    address: Optional[str] = None
    village_city: Optional[str] = None
    taluk: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None
    survey_number: Optional[str] = None
    khata_number: Optional[str] = None
    property_area: Optional[str] = None
    market_value: Optional[float] = None
    loan_security_value: Optional[float] = None

class PropertyDetailsOut(BaseModel):
    id: int
    application_id: int
    property_type: Optional[str]
    address: Optional[str]
    village_city: Optional[str]
    taluk: Optional[str]
    district: Optional[str]
    state: Optional[str]
    pin_code: Optional[str]
    survey_number: Optional[str]
    khata_number: Optional[str]
    property_area: Optional[str]
    market_value: Optional[float]
    loan_security_value: Optional[float]
    created_at: datetime
    class Config:
        from_attributes = True

class GovVerificationCreate(BaseModel):
    pan_aadhaar_link_status: Optional[str] = None
    tax_receipt_status: Optional[str] = None
    aadhaar_validity_status: Optional[str] = None
    aadhaar_screenshot_path: Optional[str] = None
    officer_name: Optional[str] = None
    timestamp: Optional[str] = None
    remarks: Optional[str] = None
    screenshot_path: Optional[str] = None
    verification_screenshots: Optional[str] = None # Backward compatibility

class GovVerificationOut(BaseModel):
    id: int
    application_id: int
    pan_aadhaar_link_status: Optional[str]
    tax_receipt_status: Optional[str]
    aadhaar_validity_status: Optional[str]
    aadhaar_screenshot_path: Optional[str]
    officer_name: Optional[str]
    timestamp: Optional[str]
    remarks: Optional[str]
    screenshot_path: Optional[str]
    verification_screenshots: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

class ApplicationOut(BaseModel):
    id: int
    user_id: int
    applicant_name: Optional[str]
    aadhaar_number: Optional[str] = None
    pan_number: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    father_name: Optional[str] = None
    branch: Optional[str]
    loan_type: Optional[str]
    loan_amount: float
    loan_tenure: Optional[int]
    interest_rate: Optional[float]
    status: ApplicationStatus
    created_at: datetime
    site_verification: Optional[SiteVerificationOut] = None
    gov_verification: Optional[GovVerificationOut] = None
    joint_applicants: List[JointApplicantOut] = []
    property_details: Optional[PropertyDetailsOut] = None
    class Config:
        from_attributes = True
