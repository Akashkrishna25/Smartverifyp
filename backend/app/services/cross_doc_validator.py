"""
Cross-Document Validator
Compares Aadhaar and PAN fields. Provides fuzzy matching for names and exact matching for DOB.
"""
from typing import Dict, Any
import re

def normalize_name(name: str) -> str:
    """
    Normalizes a name for token/order-insensitive matching.
    Example: "Lakshmi B S" -> "B LAKSHMI S"
    """
    if not name:
        return ""
    # Remove special chars, lower case
    clean = re.sub(r'[^a-zA-Z\s]', '', name).lower()
    # Tokenize and sort
    tokens = sorted([t for t in clean.split() if t])
    return " ".join(tokens)

def normalize_dob(dob: str) -> str:
    if not dob:
        return ""
    # Normalize slashes and dashes to slashes
    return dob.replace("-", "/").strip()

def validate_cross_documents(aadhaar_data: Dict[str, Any], pan_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compares the fields of an Aadhaar and PAN document.
    Returns structured comparison results.
    """
    results = {
        "overall_status": "MATCH",
        "severity": "none",
        "comparisons": []
    }
    
    # 1. Name Comparison
    a_name = aadhaar_data.get("applicant_name")
    p_name = pan_data.get("applicant_name")
    
    if a_name and p_name:
        norm_a = normalize_name(a_name)
        norm_p = normalize_name(p_name)
        
        if norm_a == norm_p:
            results["comparisons"].append({
                "field": "name",
                "status": "MATCH",
                "aadhaar_value": a_name,
                "pan_value": p_name,
                "explanation": "Names match exactly (order insensitive)."
            })
        else:
            results["comparisons"].append({
                "field": "name",
                "status": "MISMATCH",
                "aadhaar_value": a_name,
                "pan_value": p_name,
                "explanation": "Names do not match."
            })
            results["overall_status"] = "MISMATCH"
            results["severity"] = "high"
            
    # 2. DOB Comparison
    a_dob = aadhaar_data.get("dob")
    p_dob = pan_data.get("dob")
    
    if a_dob and p_dob:
        if normalize_dob(a_dob) == normalize_dob(p_dob):
            results["comparisons"].append({
                "field": "dob",
                "status": "MATCH",
                "aadhaar_value": a_dob,
                "pan_value": p_dob,
                "explanation": "DOB matches exactly."
            })
        else:
            results["comparisons"].append({
                "field": "dob",
                "status": "MISMATCH",
                "aadhaar_value": a_dob,
                "pan_value": p_dob,
                "explanation": "DOB does not match."
            })
            results["overall_status"] = "MISMATCH"
            results["severity"] = "high"
            
    return results
