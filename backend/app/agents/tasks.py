"""
SmartVerify Multi-Agent Task Definitions — Milestone 2
───────────────────────────────────────────────────────
Defines the strictly sequential tasks for the loan verification crew.

Each task feeds its output to the next agent via CrewAI's `context` mechanism.
No agent repeats OCR or NLP — all agents consume the Structured JSON already
stored by the Milestone 1 pipeline.

Pipeline:
    analyse_documents         (Document Analyst)
        → extract_profile     (Data Extraction Specialist)
            → verify_loan     (Loan Verification Officer)
                → verify_gov  (Government Verification Agent)
                    → compile_report (Compliance Reporter)
"""

import json
from crewai import Task


def build_tasks(agents: dict, run_context: dict) -> list:
    """
    Build the ordered list of CrewAI tasks for a verification run.

    `run_context` is a dict with keys:
        application_id    (int)
        applicant_name    (str)
        loan_amount       (float)
        loan_type         (str, optional)
        loan_tenure       (int, optional)
        gov_verification_record (dict, optional)
        documents         (list[dict]) — each:
                            {id, document_type, file_path,
                             original_name, structured_data, extracted_text}
        shared_context_summary (str, optional)
    """
    application_id = run_context["application_id"]
    applicant_name = run_context.get("applicant_name") or "Unknown Applicant"
    loan_amount    = run_context["loan_amount"]
    loan_type      = run_context.get("loan_type") or "Home Loan"
    loan_tenure    = run_context.get("loan_tenure") or 60
    gov_record     = run_context.get("gov_verification_record") or {}
    documents      = run_context["documents"]

    # ── Build a compact metadata string for Task 1 ───────────────────────
    doc_list_str = "\n".join(
        f"  - doc_id={d['id']}, type={d['document_type']}, "
        f"file={d.get('original_name', '')}"
        for d in documents
    ) or "  (no documents uploaded)"

    # ── Build the merged Structured JSON for Task 1 ──────────────────────
    # Merge all per-document structured_data JSONs into a single dict.
    # Later fields overwrite earlier ones; applicant_name/loan_amount
    # fall back to the application record values.
    merged_structured: dict = {}
    doc_structured_details = []
    for d in documents:
        raw_json = d.get("structured_data") or "{}"
        try:
            parsed = json.loads(raw_json)
        except Exception:
            parsed = {}
        # Merge (prefer non-null values)
        for k, v in parsed.items():
            if v is not None:
                merged_structured[k] = v
        doc_structured_details.append({
            "doc_id": d["id"],
            "document_type": d["document_type"],
            "structured_data": parsed,
        })

    # Fallback applicant profile fields from application record
    if not merged_structured.get("applicant_name"):
        merged_structured["applicant_name"] = applicant_name
    if not merged_structured.get("loan_amount"):
        merged_structured["loan_amount"] = loan_amount

    merged_json_str = json.dumps(merged_structured, indent=2)
    doc_structured_str = json.dumps(doc_structured_details, indent=2)
    doc_types_json = json.dumps(
        [{"document_type": d["document_type"]} for d in documents]
    )

    # ── OCR text summary for quality assessment ──────────────────────────
    ocr_quality_notes = []
    for d in documents:
        text = d.get("extracted_text") or ""
        quality = "good" if len(text) > 50 else ("partial" if len(text) > 5 else "unreadable")
        ocr_quality_notes.append(
            f"  - doc_id={d['id']}, type={d['document_type']}, "
            f"ocr_chars={len(text)}, quality={quality}"
        )
    ocr_quality_str = "\n".join(ocr_quality_notes) or "  (no OCR data)"

    # ─────────────────────────────────────────────────────────────────────
    # TASK 1 — Document Analyst
    # ─────────────────────────────────────────────────────────────────────
    analyse_documents = Task(
        description=(
            f"You are reviewing loan application #{application_id} for applicant: "
            f"{applicant_name} (loan amount: ₹{loan_amount}, type: {loan_type}).\n\n"
            "UPLOADED DOCUMENTS:\n"
            f"{doc_list_str}\n\n"
            "OCR QUALITY ASSESSMENT (pre-extracted):\n"
            f"{ocr_quality_str}\n\n"
            "PER-DOCUMENT STRUCTURED DATA (already extracted by OCR+NLP pipeline):\n"
            f"{doc_structured_str}\n\n"
            "CRITICAL: You MUST use the document_ocr_tool to extract text for each document using its file_path, "
            "then compare it with the pre-extracted OCR text to validate quality and detect corruption.\n\n"
            "Your task is to analyse the above data and produce a JSON object with this exact shape:\n"
            "{\n"
            '  "document_status": "complete" | "incomplete" | "unreadable",\n'
            '  "document_quality": "good" | "partial" | "poor",\n'
            '  "missing_documents": [<list of missing required document types>],\n'
            '  "unreadable_documents": [<doc_ids of unreadable documents>],\n'
            '  "validated_document_types": [<list of confirmed document types>],\n'
            '  "document_summary": "<2-3 sentence summary of document quality and completeness>",\n'
            '  "ocr_confidence": <number 0-100>,\n'
            '  "explainability": {\n'
            '    "input": "<summary of input data>",\n'
            '    "reasoning": "<step-by-step reasoning for document quality and completeness>",\n'
            '    "evidence_used": ["<evidence 1>", "<evidence 2>"],\n'
            '    "tools_invoked": ["document_ocr_tool"],\n'
            '    "confidence": <number 0-100>,\n'
            '    "decision": "<final analytical decision>"\n'
            '  }\n'
            "}\n\n"
            "Required document types for a home loan are: aadhaar, pan, and at least one income document (salary_slip, income_cert, or form_16).\n"
            "Return ONLY this JSON object, with no extra commentary."
        ),
        expected_output=(
            "A single JSON object with document_status, document_quality, "
            "missing_documents, unreadable_documents, validated_document_types, "
            "document_summary, ocr_confidence, and explainability fields."
        ),
        agent=agents["document_analyst"],
    )

    # ─────────────────────────────────────────────────────────────────────
    # TASK 2 — Data Extraction Specialist
    # ─────────────────────────────────────────────────────────────────────
    extract_profile = Task(
        description=(
            "You have received the Document Analyst's assessment from the previous task.\n\n"
            "Now consume the following Structured JSON that was produced by the earlier pipeline:\n"
            f"{merged_json_str}\n\n"
            "CRITICAL: You MUST use the information_extraction_tool by passing the combined OCR text to extract structured data independently, "
            "then validate and merge it with the provided JSON.\n\n"
            "Application defaults (use if field is missing):\n"
            f"  - applicant_name: {applicant_name}\n"
            f"  - loan_amount: {loan_amount}\n\n"
            "Your task:\n"
            "1. Validate each extracted value (e.g., PAN format ABCDE1234F, Aadhaar 12 digits).\n"
            "2. Normalize names to Title Case.\n"
            "3. Normalize dates to DD-MM-YYYY format if possible.\n"
            "4. Identify any missing mandatory fields "
            "(applicant_name, aadhaar_number, pan_number, dob).\n"
            "5. Produce a cleaned applicant profile.\n\n"
            "Return ONLY a JSON object with this exact shape:\n"
            "{\n"
            '  "applicant_profile": {\n'
            '    "applicant_name": "<str>",\n'
            '    "aadhaar_number": "<str>",\n'
            '    "pan_number": "<str>",\n'
            '    "dob": "<str>",\n'
            '    "gender": "<str>",\n'
            '    "address": "<str>",\n'
            '    "phone": "<str>",\n'
            '    "employer_name": "<str>",\n'
            '    "monthly_income": <number or null>,\n'
            '    "loan_amount": <number>,\n'
            '    "bank_account": "<str>"\n'
            "  },\n"
            '  "validation_errors": [<list of validation error strings>],\n'
            '  "missing_fields": [<list of missing mandatory field names>],\n'
            '  "normalized_data": {<same as applicant_profile but with all normalizations noted>},\n'
            '  "extraction_confidence": <number 0-100>,\n'
            '  "explainability": {\n'
            '    "input": "<summary of input data>",\n'
            '    "reasoning": "<step-by-step reasoning for extraction>",\n'
            '    "evidence_used": ["<evidence 1>", "<evidence 2>"],\n'
            '    "tools_invoked": ["information_extraction_tool"],\n'
            '    "confidence": <number 0-100>,\n'
            '    "decision": "<final extraction decision>"\n'
            '  }\n'
            "}\n"
            "Return ONLY this JSON object, with no extra commentary."
        ),
        expected_output=(
            "A single JSON object with applicant_profile, validation_errors, "
            "missing_fields, normalized_data, extraction_confidence, and explainability."
        ),
        agent=agents["extraction_specialist"],
        context=[analyse_documents],
    )

    # ─────────────────────────────────────────────────────────────────────
    # TASK 3 — Loan Verification Officer
    # ─────────────────────────────────────────────────────────────────────
    verify_loan = Task(
        description=(
            "You have received the cleaned Applicant Profile from the Data Extraction Specialist.\n\n"
            "Loan Application Details:\n"
            f"  - Application ID: {application_id}\n"
            f"  - Loan Amount: ₹{loan_amount}\n"
            f"  - Loan Type: {loan_type}\n"
            f"  - Loan Tenure: {loan_tenure} months\n\n"
            "Submitted Document Types:\n"
            f"  {doc_types_json}\n\n"
            "Eligibility Rules to apply:\n"
            "1. Applicant must have a valid Aadhaar AND PAN number.\n"
            "2. Monthly income must be present and ≥ ₹15,000.\n"
            "3. EMI affordability: loan_amount / tenure ≤ 50% of monthly_income.\n"
            "4. At least one income document (salary_slip, income_cert, or form_16) must be present.\n"
            "5. Identity documents (aadhaar, pan) must be present.\n\n"
            "CRITICAL: BEFORE making any recommendation, you MUST use the policy_retrieval_tool to retrieve:\n"
            "  - Relevant Bank Policies\n"
            "  - Loan Eligibility Policies\n"
            "  - Income Policies\n"
            "  - Loan Type Policies\n"
            "You MUST reference the retrieved policies in your reasoning and include them in your output.\n\n"
            "Return ONLY a JSON object with this exact shape:\n"
            "{\n"
            '  "eligibility": "eligible" | "ineligible" | "review_required",\n'
            '  "verification_score": <0-100>,\n'
            '  "checks": [\n'
            '    {"check": "<name>", "passed": <bool>, "detail": "<str>"}\n'
            "  ],\n"
            '  "issues": [<list of issue strings>],\n'
            '  "recommendation": "approve" | "manual_review" | "reject",\n'
            '  "policies_retrieved": <number of policies retrieved>,\n'
            '  "rbi_guidelines": "<mention any RBI guidelines retrieved>",\n'
            '  "policy_references": ["<policy string 1>", "<policy string 2>"],\n'
            '  "verification_confidence": <number 0-100>,\n'
            '  "explainability": {\n'
            '    "input": "<summary of input data>",\n'
            '    "reasoning": "<step-by-step reasoning for eligibility>",\n'
            '    "evidence_used": ["<evidence 1>"],\n'
            '    "tools_invoked": ["policy_retrieval_tool"],\n'
            '    "confidence": <number 0-100>,\n'
            '    "decision": "<final eligibility decision>"\n'
            '  }\n'
            "}\n"
            "Return ONLY this JSON object, with no extra commentary."
        ),
        expected_output=(
            "A single JSON object with eligibility, verification_score, checks, "
            "issues, recommendation, policies_retrieved, policy_references, and explainability."
        ),
        agent=agents["verification_officer"],
        context=[extract_profile],
    )

    # ─────────────────────────────────────────────────────────────────────
    # TASK 4 — Government Verification Agent
    # ─────────────────────────────────────────────────────────────────────
    gov_record_json = json.dumps(gov_record, indent=2)

    verify_gov = Task(
        description=(
            "You have received the Applicant Profile from the Data Extraction Specialist.\n\n"
            "You have also received the following manual verification record entered by the bank officer "
            "using the Government Verification UI (Aadhaar/PAN/Tax portals):\n"
            f"{gov_record_json}\n\n"
            "Your task is to analyze this manual record against the applicant profile.\n"
            "CRITICAL: BEFORE performing verification, you MUST use the similarity_search_tool to retrieve:\n"
            "  - Similar historical applications\n"
            "  - Previous fraud cases\n"
            "  - Similar Aadhaar/PAN records\n"
            "  - Previous loan decisions\n"
            "CRITICAL: You MUST also use the fraud_detection_tool with the applicant profile to check for duplicate Aadhaar, PAN, and other historical fraud patterns.\n"
            "You MUST use this retrieved historical context and fraud tool output in your reasoning.\n\n"
            "Rules:\n"
            "  1. Verify the OCR-extracted aadhaar_number and pan_number from the profile match the officer's record.\n"
            "  2. Verify aadhaar_validity_status in the officer's record is 'Valid'.\n"
            "  3. Verify pan_aadhaar_link_status in the officer's record is 'Linked'.\n"
            "  4. If Aadhaar Valid AND PAN-Aadhaar Linked, confidence should be increased.\n"
            "  5. If Aadhaar Invalid OR PAN-Aadhaar Not Linked, flag application immediately and increase fraud risk score.\n"
            "  6. If either status is 'Pending' or 'Manual Review Required', flag application, mark 'requires_manual_review' = true and add to 'issues'.\n"
            "  7. Check for missing screenshots, missing timestamps, or missing officer names. If any are missing, set verification_status to 'Verification Incomplete' and 'requires_manual_review' = true.\n"
            "  8. If all checks pass and both statuses are positive, set verification_status to 'Government Verification Passed' and 'requires_manual_review' = false.\n\n"
            "Return ONLY a JSON object with this exact shape:\n"
            "{\n"
            '  "government_verification": {\n'
            '    "aadhaar_validity_status": "<status>",\n'
            '    "pan_aadhaar_link_status": "<status>",\n'
            '    "tax_receipt": "<status>",\n'
            '    "verification_status": "Government Verification Passed" | "Verification Incomplete" | "Manual Review",\n'
            '    "issues": ["<issue 1>", "<issue 2>"],\n'
            '    "remarks": "<synthesis of officer remarks and your findings>",\n'
            '    "requires_manual_review": <true/false>,\n'
            '    "similar_cases": <number of similar cases retrieved>,\n'
            '    "similarity_score": "<highest similarity percentage, e.g., 85%>",\n'
            '    "historical_context": ["<case 1 details>", "<case 2 details>"],\n'
            '    "fraud_score": <0-100>,\n'
            '    "fraud_flag": <true/false>,\n'
            '    "fraud_confidence": <number 0-100>,\n'
            '    "explainability": {\n'
            '      "input": "<summary of input data>",\n'
            '      "reasoning": "<step-by-step reasoning for gov verification and fraud detection>",\n'
            '      "evidence_used": ["<evidence 1>"],\n'
            '      "tools_invoked": ["similarity_search_tool", "fraud_detection_tool"],\n'
            '      "confidence": <number 0-100>,\n'
            '      "decision": "<final verification and fraud decision>"\n'
            '    }\n'
            "  }\n"
            "}\n"
            "Return ONLY this JSON object, with no extra commentary."
        ),
        expected_output=(
            "A single JSON object containing a 'government_verification' key, which holds "
            "aadhaar_validity_status, pan_aadhaar_link_status, tax_receipt, verification_status, issues, remarks, requires_manual_review, "
            "fraud fields, and explainability."
        ),
        agent=agents["gov_verification_agent"],
        context=[extract_profile, verify_loan],
    )

    # ─────────────────────────────────────────────────────────────────────
    # TASK 5 — Compliance Reporter
    # ─────────────────────────────────────────────────────────────────────
    compile_report = Task(
        description=(
            "You have the full context from all previous agents:\n"
            "  1. Document Analyst's findings\n"
            "  2. Data Extraction Specialist's cleaned applicant profile\n"
            "  3. Loan Verification Officer's eligibility assessment\n"
            "  4. Government Verification Agent's ID check results\n\n"
            "Synthesise all findings and produce the Final AI Output JSON.\n\n"
            "Decision rules:\n"
            "  - If government verification requires_manual_review == true → final_status = 'manual_review'\n"
            "  - If government verification_status == 'Manual Review' or 'Verification Incomplete' → final_status = 'manual_review'\n"
            "  - If Loan Verification Officer recommendation == 'reject' → "
            "final_status = 'rejected'\n"
            "  - If document_status == 'unreadable' → final_status = 'rejected'\n"
            "  - If recommendation == 'manual_review' OR any issues exist → "
            "final_status = 'manual_review'\n"
            "  - Otherwise → final_status = 'approved'\n\n"
            "CRITICAL: You MUST use the pdf_report_generation_tool to generate the final PDF report. Pass the applicant details, extracted_info (from Task 2), verification_result (from Task 3), and fraud_result (from Task 4).\n\n"
            "Return ONLY a single JSON object with this exact shape "
            "(no markdown fences, no commentary):\n"
            "{\n"
            f'  "application_id": {application_id},\n'
            '  "final_status": "approved" | "manual_review" | "rejected",\n'
            '  "verification_score": <number 0-100 from Loan Verification Officer>,\n'
            '  "risk_score": <number 0-100, inverse of verification_score>,\n'
            '  "fraud_flag": <bool from Government Verification Agent>,\n'
            '  "overall_ai_confidence": <number 0-100 (average of all agent confidences)>,\n'
            '  "extracted_info": <applicant_profile object from Data Extraction Specialist>,\n'
            '  "verification_details": <full JSON from Loan Verification Officer>,\n'
            '  "fraud_analysis": <gov verification JSON from Government Verification Agent>,\n'
            '  "agent_findings": {\n'
            '    "document_analyst": <document analysis JSON>,\n'
            '    "extraction_specialist": <extraction JSON>,\n'
            '    "verification_officer": <verification JSON>,\n'
            '    "gov_verification_agent": <gov verification JSON>\n'
            '  },\n'
            '  "recommendation": "<Final recommendation text>",\n'
            '  "human_review": "<What a human officer should focus on, if any>",\n'
            '  "summary": "<3-5 sentence plain-English summary for the loan officer>",\n'
            '  "pdf_path": "<path returned by pdf_report_generation_tool>"\n'
            "}"
        ),
        expected_output=(
            "A single JSON object with application_id, final_status, verification_score, "
            "risk_score, fraud_flag, overall_ai_confidence, extracted_info, verification_details, fraud_analysis, "
            "agent_findings, recommendation, human_review, summary, and pdf_path."
        ),
        agent=agents["compliance_reporter"],
        context=[analyse_documents, extract_profile, verify_loan, verify_gov],
    )

    return [
        analyse_documents,
        extract_profile,
        verify_loan,
        verify_gov,
        compile_report,
    ]
