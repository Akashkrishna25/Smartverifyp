"""
SmartVerify Loan Verification Crew
─────────────────────────────────────
Orchestrates the multi-agent pipeline:

    Document Analyst → Extraction Specialist → Verification Officer
                                              ↘ Fraud Investigator ↗
                                                       ↓
                                              Compliance Reporter

Produces a single structured result dict that mirrors the shape of the
previous (non-agentic) verification pipeline, so the FastAPI endpoint and
VerificationReport model don't need to change shape.
"""

import json
import logging
import re
from typing import Any, Dict, List

from crewai import Crew, Process

from app.agents.agent_definitions import build_agents
from app.agents.tasks import build_tasks

logger = logging.getLogger(__name__)


class LoanVerificationCrew:
    """Builds and runs the multi-agent loan verification crew for one application."""

    def __init__(self, db_session):
        self.db = db_session

    def run(
        self,
        application_id: int,
        applicant_name: str,
        loan_amount: float,
        documents: List[Dict[str, Any]],
        loan_type: str = "Home Loan",
        loan_tenure: int = 60,
        gov_verification_record: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Execute the crew end-to-end.

        `documents` is a list of dicts:
        [{id, document_type, file_path, original_name, structured_data, extracted_text}]

        Returns a dict shaped like:
            {
              "final_status": "approved" | "manual_review" | "rejected",
              "verification_score": float,
              "risk_score": float,
              "fraud_flag": bool,
              "extracted_info": {...},
              "verification_details": {...},
              "fraud_analysis": {...},
              "pdf_path": str | None,
              "summary": str,
              "agent_trace": str,   # raw crew output for audit/debug
            }
        """
        import time
        from app.agents.context import SharedAgentContext
        
        # Phase 4: Shared Context
        shared_context = SharedAgentContext(
            application_id=application_id,
            applicant_name=applicant_name,
            loan_amount=loan_amount
        )
        
        start_time = time.time()
        
        agents = build_agents(self.db, shared_context=shared_context)
        tasks = build_tasks(
            agents,
            run_context={
                "application_id": application_id,
                "applicant_name": applicant_name,
                "loan_amount": loan_amount,
                "loan_type": loan_type,
                "loan_tenure": loan_tenure,
                "documents": documents,
                "gov_verification_record": gov_verification_record or {},
                "shared_context_summary": shared_context.get_summary_context()
            },
        )

        crew = Crew(
            agents=list(agents.values()),
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
        )

        # Crew AI execution (Phase 8 Timeline tracking)
        shared_context.record_timing("crewai_start", time.time())
        crew_output = crew.kickoff()
        shared_context.record_timing("crewai", time.time() - start_time)

        raw_output = self._extract_raw(crew_output)
        result = self._parse_final_json(raw_output)
        result["agent_trace"] = raw_output

        # Defensive defaults in case the LLM omitted a field
        result.setdefault("final_status", "manual_review")
        result.setdefault("verification_score", 0.0)
        result.setdefault("risk_score", 0.0)
        result.setdefault("fraud_flag", False)
        result.setdefault("extracted_info", {})
        result.setdefault("verification_details", {})
        result.setdefault("fraud_analysis", {})
        result.setdefault("pdf_path", None)
        result.setdefault("summary", "")
        result.setdefault("agent_findings", {})
        result.setdefault("recommendation", "")
        result.setdefault("human_review", "")
        
        # New Phase 6 & 7 & 8 fields
        result.setdefault("explainable_ai", {})
        result.setdefault("confidence_score", 0.0)
        result["agent_memory"] = shared_context.agent_memory
        
        shared_context.record_timing("total", time.time() - start_time)
        result["execution_timeline"] = shared_context.execution_timeline

        # Safety net: fraud flag always forces rejection, even if the
        # compliance reporter agent got this wrong.
        if result.get("fraud_flag") and result["final_status"] != "rejected":
            logger.warning(
                "Crew set final_status=%s despite fraud_flag=True; forcing 'rejected'.",
                result["final_status"],
            )
            result["final_status"] = "rejected"

        return result

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_raw(crew_output: Any) -> str:
        """Normalise CrewOutput (or plain string) into a raw string."""
        if hasattr(crew_output, "raw"):
            return crew_output.raw
        return str(crew_output)

    @staticmethod
    def _parse_final_json(raw_output: str) -> Dict[str, Any]:
        """
        Parse the compliance reporter's final JSON object out of the raw
        crew output, tolerating markdown code fences or surrounding prose.
        """
        if not raw_output:
            return {}

        text = raw_output.strip()

        # Strip ```json ... ``` or ``` ... ``` fences if present
        fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1)

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Fallback: find the last top-level-looking {...} block
        brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
        if brace_match:
            candidate = brace_match.group(1)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse crew JSON output: {e}\nRaw: {text[:1000]}")

        logger.error(f"Could not extract JSON from crew output: {text[:1000]}")
        return {}
