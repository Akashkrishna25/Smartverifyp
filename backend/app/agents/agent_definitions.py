"""
SmartVerify Multi-Agent Definitions
─────────────────────────────────────
Defines the specialised CrewAI agents for Milestone 2:

    1. Document Analyst
    2. Data Extraction Specialist
    3. Loan Verification Officer
    4. Government Verification Agent
    5. Compliance Reporter
"""

import logging
import os
from crewai import Agent, LLM

from app.core.config import settings
from app.agents.tools import (
    MemoryTool, PolicyRetrievalTool, SimilaritySearchTool,
    OCRTool, InformationExtractionTool, FraudDetectionTool, ReportGenerationTool
)

logger = logging.getLogger(__name__)


def get_llm() -> LLM:
    """Build a LiteLLM-backed LLM instance using Google Gemini."""
    return LLM(
        model=settings.CREWAI_MODEL,          # e.g. "gemini/gemini-2.5-flash"
        temperature=settings.CREWAI_TEMPERATURE,
        api_key=os.environ.get("GEMINI_API_KEY", ""),
    )


def build_agents(db_session, shared_context=None) -> dict:
    llm = get_llm()
    memory_tool = MemoryTool(shared_context=shared_context)
    policy_tool = PolicyRetrievalTool()
    similarity_tool = SimilaritySearchTool()
    ocr_tool = OCRTool()
    extraction_tool = InformationExtractionTool()
    fraud_tool = FraudDetectionTool(db_session=db_session)
    report_tool = ReportGenerationTool()

    document_analyst = Agent(
        role="Document Analyst",
        goal=(
            "Review the provided OCR text and Structured JSON to verify document quality, "
            "detect missing documents, validate document types, and flag unreadable documents."
        ),
        backstory=(
            "You are a meticulous document processing specialist. You use the document_ocr_tool "
            "to extract text from submitted documents, then assess the quality, completeness, "
            "and readability of those documents."
        ),
        tools=[ocr_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    extraction_specialist = Agent(
        role="Data Extraction Specialist",
        goal=(
            "Consume ONLY the Structured JSON provided. Validate extracted values, "
            "normalize names, addresses, and dates, detect missing mandatory fields, "
            "and produce a cleaned applicant profile."
        ),
        backstory=(
            "You are an expert in data normalization. You use the information_extraction_tool "
            "to pull structured data from raw OCR text, normalize names, addresses, and dates, "
            "and flag any missing required fields to create a cleaned applicant profile."
        ),
        tools=[extraction_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    verification_officer = Agent(
        role="Loan Verification Officer",
        goal=(
            "Check eligibility, validate income and loan amount against the cleaned applicant "
            "profile and loan details, and produce a preliminary recommendation."
        ),
        backstory=(
            "You are a senior loan verification officer. You strictly use the provided "
            "Applicant Profile and Loan Details to determine eligibility. You must use "
            "the PolicyRetrievalTool to retrieve Bank Policies, Loan Eligibility Policies, "
            "and Income Policies from the vector database before making any recommendation."
        ),
        tools=[memory_tool, policy_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    gov_verification_agent = Agent(
        role="Government Verification Agent",
        goal=(
            "Consume Aadhaar and PAN numbers, read the simulated/existing verification status, "
            "compare OCR values with verification status, flag mismatches or missing verifications, "
            "and produce a verification summary."
        ),
        backstory=(
            "You are a government ID verification specialist. You check Aadhaar and PAN "
            "validity statuses using the manual UI record. You must use the "
            "SimilaritySearchTool to retrieve similar historical applications, and the "
            "fraud_detection_tool to calculate a risk score based on duplicates and inconsistencies."
        ),
        tools=[memory_tool, similarity_tool, fraud_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    compliance_reporter = Agent(
        role="Compliance Reporter",
        goal=(
            "Consume outputs from all previous agents and generate the Final AI Output JSON, "
            "including the Final Recommendation, Human-in-the-loop Recommendation, and "
            "Consolidated AI Summary."
        ),
        backstory=(
            "You are responsible for the final audit and synthesis. You review the findings "
            "of all agents and compile them into a final decision. You use the "
            "pdf_report_generation_tool to generate a final downloadable PDF report."
        ),
        tools=[memory_tool, report_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    return {
        "document_analyst": document_analyst,
        "extraction_specialist": extraction_specialist,
        "verification_officer": verification_officer,
        "gov_verification_agent": gov_verification_agent,
        "compliance_reporter": compliance_reporter,
    }
