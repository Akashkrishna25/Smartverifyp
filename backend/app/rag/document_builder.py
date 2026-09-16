"""
RAG Document Builder
====================
WHAT IT DOES:
    Fetches all loan application data from the database using the application_id
    and converts each piece of information into a text "chunk" (a small paragraph).
    Each chunk has metadata so we always know where the information came from.

WHY WE NEED IT:
    BM25 and FAISS can only search through text.
    This module translates database rows into searchable text chunks.

PRIVACY:
    - Aadhaar numbers are masked: XXXX-XXXX-1234
    - Phone numbers are masked: XXXXXX7890
    - PAN numbers are shown in full (needed for verification checks)

NOTE: This module only READS from the database. It never modifies any record.
"""

import logging
from typing import List, Dict, Any, Optional
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.models.application import (
    Application, SiteVerification, GovVerification,
    JointApplicant, PropertyDetails
)
from app.models.user import User
from app.models.document import Document
from app.models.verification_report import VerificationReport

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Privacy Helpers
# ---------------------------------------------------------------------------

def _mask_aadhaar(aadhaar: Optional[str]) -> str:
    """Show only the last 4 digits: XXXX-XXXX-1234"""
    if not aadhaar:
        return "not provided"
    clean = aadhaar.replace(" ", "").replace("-", "")
    if len(clean) >= 4:
        return f"XXXX-XXXX-{clean[-4:]}"
    return "XXXX-XXXX-XXXX"


def _mask_phone(phone: Optional[str]) -> str:
    """Show only the last 4 digits: XXXXXX7890"""
    if not phone:
        return "not provided"
    clean = phone.replace(" ", "").replace("-", "")
    if len(clean) >= 4:
        return f"XXXXXX{clean[-4:]}"
    return "XXXXXXXXXX"


def _safe(value: Any, default: str = "not provided") -> str:
    """Return a safe string representation of a value."""
    if value is None or value == "":
        return default
    return str(value).strip()


def _fmt_currency(value: Any) -> str:
    """Format a number as Indian Rupees."""
    if value is None:
        return "not provided"
    try:
        return f"Rs. {float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


# ---------------------------------------------------------------------------
# Main Document Builder
# ---------------------------------------------------------------------------

def fetch_loan_data(application_id: int, db: Session) -> Dict[str, Any]:
    """
    Fetch all data related to a loan application from the database.

    Returns a dictionary with keys:
        application, user, documents, site_verification,
        gov_verification, joint_applicants, property_details, report

    All values come directly from the database — nothing is hardcoded.
    Returns None for any related record that doesn't exist yet.
    """
    # 1. Load the main application record
    application = db.query(Application).filter(
        Application.id == application_id
    ).first()

    if not application:
        logger.warning(f"No application found for application_id={application_id}")
        return {}

    # 2. Load the applicant (bank user who submitted the application)
    user = db.query(User).filter(
        User.id == application.user_id
    ).first() if application.user_id else None

    # 3. Load uploaded documents
    documents = db.query(Document).filter(
        Document.application_id == application_id
    ).all()

    # 4. Load site verification record (if done)
    site_ver = db.query(SiteVerification).filter(
        SiteVerification.application_id == application_id
    ).first()

    # 5. Load government verification record (if done)
    gov_ver = db.query(GovVerification).filter(
        GovVerification.application_id == application_id
    ).first()

    # 6. Load joint applicants (co-borrowers if any)
    joint_applicants = db.query(JointApplicant).filter(
        JointApplicant.application_id == application_id
    ).all()

    # 7. Load property details (for home/property loans)
    property_details = db.query(PropertyDetails).filter(
        PropertyDetails.application_id == application_id
    ).first()

    # 8. Load any existing verification report
    report = db.query(VerificationReport).filter(
        VerificationReport.application_id == application_id
    ).first()

    return {
        "application": application,
        "user": user,
        "documents": documents,
        "site_verification": site_ver,
        "gov_verification": gov_ver,
        "joint_applicants": joint_applicants,
        "property_details": property_details,
        "report": report,
    }


def build_documents(application_id: int, db: Session) -> List[Dict[str, Any]]:
    """
    Convert all database records for an application into a flat list of
    text chunks, each with metadata.

    Each chunk has this structure:
    {
        "text"             : "Applicant Rahul Kumar has requested a car loan of Rs. 500000.",
        "source"           : "loan_info",        # category/section name
        "document_type"    : "loan",             # broad type
        "field"            : "loan_amount",      # specific field name
        "application_id"   : 5
    }

    All values come from the database -- never hardcoded.
    """
    data = fetch_loan_data(application_id, db)
    if not data:
        logger.error(f"Cannot build documents: no data for application_id={application_id}")
        return []

    chunks: List[Dict[str, Any]] = []
    app = data["application"]

    # Helper to create a chunk dict
    def chunk(text: str, source: str, doc_type: str, field: str) -> Dict:
        return {
            "text": text,
            "source": source,
            "document_type": doc_type,
            "field": field,
            "application_id": application_id,
        }

    # ------------------------------------------------------------------
    # SECTION 1: Core Applicant Information
    # ------------------------------------------------------------------
    name = _safe(app.applicant_name, "Unknown Applicant")
    chunks.append(chunk(
        f"The applicant's name is {name}.",
        "applicant_info", "applicant", "applicant_name"
    ))

    if app.dob:
        chunks.append(chunk(
            f"Applicant {name} was born on {_safe(app.dob)}.",
            "applicant_info", "applicant", "dob"
        ))

    if app.gender:
        chunks.append(chunk(
            f"Applicant {name} is {_safe(app.gender)}.",
            "applicant_info", "applicant", "gender"
        ))

    if app.address:
        chunks.append(chunk(
            f"Applicant {name}'s residential address is: {_safe(app.address)}.",
            "applicant_info", "applicant", "address"
        ))

    if app.father_name:
        chunks.append(chunk(
            f"Applicant {name}'s father's name is {_safe(app.father_name)}.",
            "applicant_info", "applicant", "father_name"
        ))

    # ------------------------------------------------------------------
    # SECTION 2: Identity Documents (PAN, Aadhaar) — privacy masked
    # ------------------------------------------------------------------
    if app.pan_number:
        chunks.append(chunk(
            f"Applicant {name}'s PAN number is {_safe(app.pan_number)}.",
            "identity_info", "identity", "pan_number"
        ))

    if app.aadhaar_number:
        chunks.append(chunk(
            f"Applicant {name}'s Aadhaar number ends with {_mask_aadhaar(app.aadhaar_number)}.",
            "identity_info", "identity", "aadhaar_number"
        ))

    # ------------------------------------------------------------------
    # SECTION 3: Loan Information
    # ------------------------------------------------------------------
    loan_type = _safe(app.loan_type, "Unspecified")
    chunks.append(chunk(
        f"Applicant {name} has applied for a {loan_type} of {_fmt_currency(app.loan_amount)}.",
        "loan_info", "loan", "loan_amount"
    ))

    if app.loan_tenure:
        chunks.append(chunk(
            f"The requested loan tenure is {_safe(app.loan_tenure)} months.",
            "loan_info", "loan", "loan_tenure"
        ))

    if app.interest_rate:
        chunks.append(chunk(
            f"The applicable interest rate for this loan is {_safe(app.interest_rate)}% per annum.",
            "loan_info", "loan", "interest_rate"
        ))

    if app.branch:
        chunks.append(chunk(
            f"The loan application was submitted at the {_safe(app.branch)} branch.",
            "loan_info", "loan", "branch"
        ))

    chunks.append(chunk(
        f"The current status of the loan application is: {_safe(app.status)}.",
        "loan_info", "loan", "status"
    ))

    # ------------------------------------------------------------------
    # SECTION 4: Uploaded Documents
    # ------------------------------------------------------------------
    docs = data["documents"]
    if docs:
        doc_names = [
            d.document_type.value if hasattr(d.document_type, "value") else str(d.document_type)
            for d in docs
        ]
        chunks.append(chunk(
            f"The following documents have been uploaded for applicant {name}: "
            f"{', '.join(doc_names)}.",
            "document_info", "documents", "uploaded_documents"
        ))

        for doc in docs:
            dtype = doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type)
            chunks.append(chunk(
                f"A {dtype} document named '{_safe(doc.original_name, dtype)}' has been "
                f"uploaded (processed status: {doc.processed}).",
                "document_info", "documents", dtype
            ))
    else:
        chunks.append(chunk(
            f"No documents have been uploaded yet for applicant {name}.",
            "document_info", "documents", "uploaded_documents"
        ))

    # ------------------------------------------------------------------
    # SECTION 5: Government Verification (KYC)
    # ------------------------------------------------------------------
    gov = data["gov_verification"]
    if gov:
        pan_link = _safe(gov.pan_aadhaar_link_status, "not checked")
        aadhaar_validity = _safe(gov.aadhaar_validity_status, "not checked")
        tax_status = _safe(gov.tax_receipt_status, "not checked")

        chunks.append(chunk(
            f"KYC verification status: PAN-Aadhaar link is {pan_link}. "
            f"Aadhaar validity is {aadhaar_validity}. "
            f"Tax receipt status is {tax_status}.",
            "kyc_info", "kyc", "kyc_status"
        ))

        if gov.officer_name:
            chunks.append(chunk(
                f"Government KYC verification was conducted by officer {_safe(gov.officer_name)} "
                f"on {_safe(gov.timestamp, 'date not recorded')}.",
                "kyc_info", "kyc", "kyc_officer"
            ))

        if gov.remarks:
            chunks.append(chunk(
                f"KYC officer remarks: {_safe(gov.remarks)}",
                "kyc_info", "kyc", "kyc_remarks"
            ))
    else:
        chunks.append(chunk(
            f"Government KYC verification has not been completed for applicant {name}.",
            "kyc_info", "kyc", "kyc_status"
        ))

    # ------------------------------------------------------------------
    # SECTION 6: Site Verification
    # ------------------------------------------------------------------
    site = data["site_verification"]
    if site:
        chunks.append(chunk(
            f"Site verification was conducted for the property. "
            f"Property condition: {_safe(site.property_condition, 'not assessed')}. "
            f"Construction quality: {_safe(site.construction_quality, 'not assessed')}. "
            f"Road access: {_safe(site.road_access, 'not assessed')}.",
            "site_verification_info", "site_verification", "site_status"
        ))

        if site.gps_coordinates:
            chunks.append(chunk(
                f"The property GPS coordinates are {_safe(site.gps_coordinates)}.",
                "site_verification_info", "site_verification", "gps_coordinates"
            ))

        if site.officer_name:
            chunks.append(chunk(
                f"Site inspection was carried out by officer {_safe(site.officer_name)} "
                f"on {_safe(site.date, 'date not recorded')} at {_safe(site.time, 'time not recorded')}.",
                "site_verification_info", "site_verification", "site_officer"
            ))

        if site.remarks:
            chunks.append(chunk(
                f"Site verification officer's remarks: {_safe(site.remarks)}",
                "site_verification_info", "site_verification", "site_remarks"
            ))
    else:
        chunks.append(chunk(
            f"Site verification has not been completed for this application.",
            "site_verification_info", "site_verification", "site_status"
        ))

    # ------------------------------------------------------------------
    # SECTION 7: Property Details
    # ------------------------------------------------------------------
    prop = data["property_details"]
    if prop:
        chunks.append(chunk(
            f"Property type: {_safe(prop.property_type, 'not specified')}. "
            f"Located at {_safe(prop.address, 'address not available')}, "
            f"{_safe(prop.village_city)}, {_safe(prop.district)}, {_safe(prop.state)} "
            f"- PIN {_safe(prop.pin_code)}.",
            "property_info", "property", "property_address"
        ))

        if prop.market_value:
            chunks.append(chunk(
                f"The market value of the property is {_fmt_currency(prop.market_value)}. "
                f"Loan security value is {_fmt_currency(prop.loan_security_value)}.",
                "property_info", "property", "property_value"
            ))

        if prop.survey_number:
            chunks.append(chunk(
                f"Property survey number: {_safe(prop.survey_number)}. "
                f"Khata number: {_safe(prop.khata_number)}. "
                f"Property area: {_safe(prop.property_area)}.",
                "property_info", "property", "property_legal"
            ))
    else:
        chunks.append(chunk(
            f"Property details have not been recorded for this application.",
            "property_info", "property", "property_status"
        ))

    # ------------------------------------------------------------------
    # SECTION 8: Joint Applicants (Co-borrowers)
    # ------------------------------------------------------------------
    joint = data["joint_applicants"]
    if joint:
        chunks.append(chunk(
            f"This loan application has {len(joint)} joint applicant(s) / co-borrower(s).",
            "joint_applicant_info", "joint_applicant", "joint_applicant_count"
        ))
        for idx, ja in enumerate(joint, start=1):
            rel = _safe(ja.relationship_type, "co-applicant")
            chunks.append(chunk(
                f"Joint applicant {idx} has relationship type '{rel}' with the primary applicant. "
                f"Contact (masked): {_mask_phone(ja.mobile)}.",
                "joint_applicant_info", "joint_applicant", f"joint_applicant_{idx}"
            ))
    else:
        chunks.append(chunk(
            f"There are no joint applicants for this loan application.",
            "joint_applicant_info", "joint_applicant", "joint_applicant_count"
        ))

    # ------------------------------------------------------------------
    # SECTION 9: Verification Report Summary (if already processed)
    # ------------------------------------------------------------------
    report = data["report"]
    if report:
        chunks.append(chunk(
            f"The verification report shows a verification score of "
            f"{_safe(report.verification_score, 'N/A')} out of 100. "
            f"The fraud risk score is {_safe(report.risk_score, 'N/A')} out of 100. "
            f"Fraud flag: {'Yes — flagged as suspicious' if report.fraud_flag else 'No — not flagged'}.",
            "report_summary", "report", "verification_score"
        ))

        if report.status:
            chunks.append(chunk(
                f"The final verification decision recorded is: {_safe(report.status)}.",
                "report_summary", "report", "decision"
            ))

        if report.agent_summary:
            chunks.append(chunk(
                f"AI Agent analysis summary: {_safe(report.agent_summary)}",
                "report_summary", "report", "agent_summary"
            ))

        # Include extracted income from the report if available
        if report.extracted_info and isinstance(report.extracted_info, dict):
            income = report.extracted_info.get("monthly_income")
            if income:
                chunks.append(chunk(
                    f"Applicant {name}'s verified monthly income is {_fmt_currency(income)}.",
                    "income_info", "income", "monthly_income"
                ))
    else:
        chunks.append(chunk(
            f"No verification report has been generated yet for this application.",
            "report_summary", "report", "verification_score"
        ))

    logger.info(
        f"Built {len(chunks)} RAG document chunks for application_id={application_id}"
    )
    return chunks
