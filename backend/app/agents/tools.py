"""
CrewAI Tool Wrappers
─────────────────────
Each tool wraps an existing SmartVerify service (OCR, NLP, classification,
verification engine, fraud detection, report generation) so that CrewAI
agents can invoke them as part of their reasoning loop.

Tools are intentionally thin: all real logic stays in app/services/*,
keeping the deterministic pipeline testable independently of the
agentic orchestration layer.
"""

import json
import logging
from typing import Any, Dict, List, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from app.services.ocr_service import extract_text
from app.services.nlp_service import extract_information
from app.services.classification_service import classify_document
from app.services.verification_engine import VerificationEngine
from app.services.fraud_detection import FraudDetector
from app.services.report_service import generate_report

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────
# 1. OCR Tool
# ──────────────────────────────────────────────────────────────────────────
class OCRToolInput(BaseModel):
    file_path: str = Field(..., description="Absolute path to the document file (PDF/JPG/PNG)")


class OCRTool(BaseTool):
    name: str = "document_ocr_tool"
    description: str = (
        "Extracts raw text from a document image or PDF using EasyOCR with a "
        "Tesseract fallback. Input: file_path (string). Returns the extracted "
        "text as a string."
    )
    args_schema: Type[BaseModel] = OCRToolInput

    def _run(self, file_path: str) -> str:
        try:
            text = extract_text(file_path)
            if not text:
                return "NO_TEXT_EXTRACTED"
            return text
        except Exception as e:
            logger.error(f"OCRTool failed for {file_path}: {e}")
            return f"OCR_ERROR: {e}"


# ──────────────────────────────────────────────────────────────────────────
# 2. Document Classification Tool
# ──────────────────────────────────────────────────────────────────────────
class ClassificationToolInput(BaseModel):
    text: str = Field(..., description="OCR-extracted text of the document")
    filename: str = Field(default="", description="Original filename (optional hint)")


class DocumentClassificationTool(BaseTool):
    name: str = "document_classification_tool"
    description: str = (
        "Classifies a document into one of: aadhaar, pan, salary_slip, "
        "income_cert, bank_statement, loan_application. "
        "Input: text (OCR output) and optional filename. Returns a JSON "
        "string with 'document_type' and 'confidence'."
    )
    args_schema: Type[BaseModel] = ClassificationToolInput

    def _run(self, text: str, filename: str = "") -> str:
        try:
            doc_type, confidence = classify_document(text, filename)
            return json.dumps({"document_type": doc_type, "confidence": round(confidence, 3)})
        except Exception as e:
            logger.error(f"ClassificationTool failed: {e}")
            return json.dumps({"document_type": "unknown", "confidence": 0.0, "error": str(e)})


# ──────────────────────────────────────────────────────────────────────────
# 3. Information Extraction (NLP) Tool
# ──────────────────────────────────────────────────────────────────────────
class ExtractionToolInput(BaseModel):
    text: str = Field(..., description="Combined OCR text from all documents")


class InformationExtractionTool(BaseTool):
    name: str = "information_extraction_tool"
    description: str = (
        "Runs NLP/NER + regex extraction over combined OCR text to pull out "
        "applicant_name, address, aadhaar_number, pan_number, employer_name, "
        "monthly_income, bank_account, loan_amount, dob, and phone. "
        "Input: text (string). Returns a JSON string of the extracted fields."
    )
    args_schema: Type[BaseModel] = ExtractionToolInput

    def _run(self, text: str) -> str:
        try:
            info = extract_information(text)
            return json.dumps(info, default=str)
        except Exception as e:
            logger.error(f"ExtractionTool failed: {e}")
            return json.dumps({"error": str(e)})


# ──────────────────────────────────────────────────────────────────────────
# 4. Verification Rule Engine Tool
# ──────────────────────────────────────────────────────────────────────────
class VerificationToolInput(BaseModel):
    extracted_info: str = Field(..., description="JSON string of extracted applicant information")
    documents: str = Field(..., description="JSON string list of documents, e.g. [{\"document_type\": \"pan\"}]")


class VerificationRuleTool(BaseTool):
    name: str = "loan_verification_rule_tool"
    description: str = (
        "Runs the deterministic loan-verification rule engine (identity, "
        "income, required-documents, PAN format, Aadhaar format checks). "
        "Inputs: extracted_info (JSON string) and documents (JSON string list "
        "of {document_type}). Returns a JSON string with 'checks', "
        "'verification_score' (0-100), and 'status' "
        "(approved|manual_review|rejected)."
    )
    args_schema: Type[BaseModel] = VerificationToolInput

    def _run(self, extracted_info: str, documents: str) -> str:
        try:
            info = json.loads(extracted_info) if isinstance(extracted_info, str) else extracted_info
            docs = json.loads(documents) if isinstance(documents, str) else documents
            engine = VerificationEngine()
            result = engine.verify(info, docs)
            return json.dumps(result, default=str)
        except Exception as e:
            logger.error(f"VerificationRuleTool failed: {e}")
            return json.dumps({"error": str(e), "verification_score": 0, "status": "manual_review", "checks": []})


# ──────────────────────────────────────────────────────────────────────────
# 5. Fraud Detection Tool
# ──────────────────────────────────────────────────────────────────────────
class FraudToolInput(BaseModel):
    extracted_info: str = Field(..., description="JSON string of extracted applicant information")
    documents: str = Field(..., description="JSON string list of documents, e.g. [{\"document_type\": \"pan\"}]")
    application_id: int = Field(..., description="The loan application ID, used for duplicate checks")


class FraudDetectionTool(BaseTool):
    name: str = "fraud_detection_tool"
    description: str = (
        "Analyses extracted applicant info and uploaded documents for fraud "
        "indicators: missing documents, duplicate Aadhaar across "
        "applications, abnormal income claims, high loan-to-income ratio, "
        "missing name, invalid PAN format. Inputs: extracted_info (JSON "
        "string), documents (JSON string list), application_id (int). "
        "Returns a JSON string with 'risk_score' (0-100), 'fraud_flag' "
        "(bool), and 'alerts' (list of strings)."
    )
    args_schema: Type[BaseModel] = FraudToolInput

    # db session is injected at construction time (not part of the LLM-visible schema)
    def __init__(self, db_session=None, **kwargs):
        super().__init__(**kwargs)
        self._db = db_session

    def _run(self, extracted_info: str, documents: str, application_id: int) -> str:
        try:
            info = json.loads(extracted_info) if isinstance(extracted_info, str) else extracted_info
            docs = json.loads(documents) if isinstance(documents, str) else documents
            detector = FraudDetector()
            result = detector.analyse(info, docs, application_id, self._db)
            return json.dumps(result, default=str)
        except Exception as e:
            logger.error(f"FraudDetectionTool failed: {e}")
            return json.dumps({"error": str(e), "risk_score": 0, "fraud_flag": False, "alerts": []})


# ──────────────────────────────────────────────────────────────────────────
# 6. PDF Report Generation Tool
# ──────────────────────────────────────────────────────────────────────────
class ReportToolInput(BaseModel):
    application_id: int = Field(..., description="Loan application ID")
    applicant_name: str = Field(..., description="Applicant's full name")
    loan_amount: float = Field(..., description="Requested loan amount")
    extracted_info: str = Field(..., description="JSON string of extracted applicant information")
    verification_result: str = Field(..., description="JSON string output of the verification rule tool")
    fraud_result: str = Field(..., description="JSON string output of the fraud detection tool")


class ReportGenerationTool(BaseTool):
    name: str = "pdf_report_generation_tool"
    description: str = (
        "Generates the final downloadable PDF verification report combining "
        "applicant details, extracted information, verification checks, "
        "risk analysis, and a recommendation. Returns a JSON string with "
        "'pdf_path' pointing to the generated file."
    )
    args_schema: Type[BaseModel] = ReportToolInput

    def _run(
        self,
        application_id: int,
        applicant_name: str,
        loan_amount: float,
        extracted_info: str,
        verification_result: str,
        fraud_result: str,
    ) -> str:
        try:
            from app.db.database import SessionLocal
            db = SessionLocal()
            try:
                pdf_path = generate_report(application_id=application_id, db=db)
            finally:
                db.close()
            return json.dumps({"pdf_path": pdf_path})
        except Exception as e:
            logger.error(f"ReportGenerationTool failed: {e}")
            return json.dumps({"error": str(e), "pdf_path": None})


# ──────────────────────────────────────────────────────────────────────────
# 7. Policy Retrieval Tool (Phase 2 Upgrade)
# ──────────────────────────────────────────────────────────────────────────
class PolicyRetrievalInput(BaseModel):
    query: str = Field(..., description="Query to search bank policies, KYC rules, or RBI guidelines")

class PolicyRetrievalTool(BaseTool):
    name: str = "policy_retrieval_tool"
    description: str = (
        "Retrieves the top-k relevant policies from the vector database. "
        "Input: query (string). Returns a JSON string of matched policies."
    )
    args_schema: Type[BaseModel] = PolicyRetrievalInput

    def _run(self, query: str) -> str:
        try:
            from app.services.vector_service import VectorService
            service = VectorService()
            policies = service.retrieve_policies(query=query)
            return json.dumps(policies, default=str)
        except Exception as e:
            logger.error(f"PolicyRetrievalTool failed: {e}")
            return json.dumps({"error": str(e)})


# ──────────────────────────────────────────────────────────────────────────
# 8. Similarity Search Tool (Phase 3 Upgrade)
# ──────────────────────────────────────────────────────────────────────────
class SimilaritySearchInput(BaseModel):
    extracted_info: str = Field(..., description="JSON string of extracted applicant profile")

class SimilaritySearchTool(BaseTool):
    name: str = "similarity_search_tool"
    description: str = (
        "Retrieves Top-K similar historical applications to check for past "
        "decisions and fraud cases. Input: extracted_info (JSON string). "
        "Returns a JSON string of similar applications."
    )
    args_schema: Type[BaseModel] = SimilaritySearchInput

    def _run(self, extracted_info: str) -> str:
        try:
            from app.services.vector_service import VectorService
            info = json.loads(extracted_info) if isinstance(extracted_info, str) else extracted_info
            service = VectorService()
            similars = service.find_similar_applications(extracted_info=info)
            return json.dumps(similars, default=str)
        except Exception as e:
            logger.error(f"SimilaritySearchTool failed: {e}")
            return json.dumps({"error": str(e)})


# ──────────────────────────────────────────────────────────────────────────
# 9. Memory Tool (Phase 5 Upgrade)
# ──────────────────────────────────────────────────────────────────────────
class MemoryToolInput(BaseModel):
    agent_role: str = Field(..., description="Role of the agent storing the memory")
    reasoning: str = Field(..., description="Reasoning or decision made")
    evidence: str = Field(..., description="Evidence supporting the reasoning")

class MemoryTool(BaseTool):
    name: str = "memory_tool"
    description: str = (
        "Stores an agent's reasoning and evidence into the shared context memory "
        "to be reused by subsequent agents or included in the explainability report. "
        "Input: agent_role, reasoning, evidence. Returns success message."
    )
    args_schema: Type[BaseModel] = MemoryToolInput

    def __init__(self, shared_context=None, **kwargs):
        super().__init__(**kwargs)
        self._context = shared_context

    def _run(self, agent_role: str, reasoning: str, evidence: str) -> str:
        try:
            if self._context:
                self._context.add_memory(agent_role, reasoning, evidence)
                return json.dumps({"status": "success", "message": "Memory stored successfully."})
            return json.dumps({"error": "No shared context provided."})
        except Exception as e:
            logger.error(f"MemoryTool failed: {e}")
            return json.dumps({"error": str(e)})

