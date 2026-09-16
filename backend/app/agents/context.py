"""
Shared Agent Context
Stores all the intermediate state across agents to prevent duplicate
processing and provide a unified knowledge source (Phase 4).
"""
import time
from typing import Dict, Any, List

class SharedAgentContext:
    def __init__(self, application_id: int, applicant_name: str, loan_amount: float):
        self.application_id = application_id
        self.applicant_name = applicant_name
        self.loan_amount = loan_amount
        
        # Raw Data
        self.documents: List[Dict[str, Any]] = []
        self.combined_ocr_text: str = ""
        
        # Milestone 2: Structured JSON from OCR+NLP pipeline
        # This is the merged structured_data across all documents
        self.structured_json_data: Dict[str, Any] = {}
        
        # Milestone 4: Government Verification Record (manual checks from officer)
        self.gov_verification_record: Dict[str, Any] = {}
        
        # Extracted / NLP
        self.extracted_profile: Dict[str, Any] = {}
        
        # RAG / Knowledge
        self.retrieved_policies: List[Dict[str, Any]] = []
        self.similar_applications: List[Dict[str, Any]] = []
        
        # Intermediate Outputs
        self.verification_results: Dict[str, Any] = {}
        self.fraud_results: Dict[str, Any] = {}
        
        # Agent Memory (Phase 5)
        self.agent_memory: List[Dict[str, Any]] = []
        
        # Execution Timeline (Phase 8)
        self.execution_timeline: Dict[str, float] = {
            "start_time": time.time(),
            "ocr_duration": 0.0,
            "nlp_duration": 0.0,
            "retrieval_duration": 0.0,
            "similarity_duration": 0.0,
            "verification_duration": 0.0,
            "fraud_duration": 0.0,
            "crewai_duration": 0.0,
            "pdf_duration": 0.0
        }

    def record_timing(self, phase: str, duration: float):
        """Record execution time for a specific phase."""
        key = f"{phase}_duration"
        if key in self.execution_timeline:
            self.execution_timeline[key] = round(duration, 3)
            
    def add_memory(self, agent_role: str, reasoning: str, evidence: str):
        """Allow agents to store reasoning and evidence into shared memory."""
        self.agent_memory.append({
            "agent": agent_role,
            "reasoning": reasoning,
            "evidence": evidence,
            "timestamp": time.time()
        })

    def get_summary_context(self) -> str:
        """Returns a string representation of the context for the LLM prompts."""
        context = f"Application ID: {self.application_id}\n"
        context += f"Applicant: {self.applicant_name}\n"
        context += f"Loan Amount: {self.loan_amount}\n\n"
        
        if self.retrieved_policies:
            context += "--- RETRIEVED POLICIES ---\n"
            for p in self.retrieved_policies:
                context += f"- {p.get('text', '')[:200]}...\n"
                
        if self.similar_applications:
            context += "\n--- SIMILAR HISTORICAL APPLICATIONS ---\n"
            for app in self.similar_applications:
                context += f"- App #{app.get('application_id')}: Sim={app.get('similarity_score')}%, Status={app.get('decision')}\n"
                
        return context
