"""
Confidence Engine
Calculates dynamic confidence scores based on Vision AI, OCR fallback, format validation, and completeness.
"""
from typing import Dict, Any, Optional

def calculate_field_confidence(
    field_name: str, 
    vision_val: Optional[str], 
    ocr_val: Optional[str], 
    validation_status: str
) -> Dict[str, Any]:
    """
    Calculates the confidence of a single field using multiple signals.
    Returns a structured dict with value, confidence, level, status, etc.
    """
    reasons = []
    base_conf = 0.0
    
    if not vision_val:
        reasons.append("Vision AI returned null.")
        if ocr_val:
            reasons.append("Fell back to OCR extraction.")
            # If Vision failed but OCR found it, it's lower confidence
            base_conf = 0.6
            final_val = ocr_val
            source = "ocr_fallback"
        else:
            return {
                "value": None,
                "confidence": 0.0,
                "confidence_level": "low",
                "validation_status": "not_found",
                "reasons": reasons,
                "source": "none"
            }
    else:
        final_val = vision_val
        source = "vision_ai"
        base_conf = 0.8
        reasons.append("Extracted by Vision AI.")
        
        # Boost confidence if OCR also matches
        if ocr_val and str(vision_val).lower().replace(" ", "") == str(ocr_val).lower().replace(" ", ""):
            base_conf += 0.15
            reasons.append("Vision AI and OCR perfectly agree.")
        elif ocr_val:
            reasons.append("Vision AI and OCR disagree.")
            base_conf -= 0.1
            
    # Adjust based on regex format validation
    if validation_status == "valid":
        base_conf += 0.05
        reasons.append("Format strictly validated.")
    elif validation_status == "needs_review":
        base_conf -= 0.2
        reasons.append("Format check flagged for review.")
    elif validation_status == "invalid":
        base_conf -= 0.4
        reasons.append("Format check failed.")
        
    # Cap confidence between 0.0 and 1.0
    confidence = max(0.0, min(1.0, round(base_conf, 2)))
    
    # Determine confidence level
    if confidence >= 0.85:
        level = "high"
    elif confidence >= 0.60:
        level = "medium"
    else:
        level = "low"
        
    return {
        "value": final_val,
        "confidence": confidence,
        "confidence_level": level,
        "validation_status": validation_status,
        "reasons": reasons,
        "source": source
    }

def process_document_confidence(
    doc_type: str, 
    vision_data: Dict[str, Any], 
    ocr_data: Dict[str, Any], 
    validated_status: Dict[str, str]
) -> Dict[str, Any]:
    """
    Processes all fields for a document, producing the final structured_data schema.
    """
    fields_meta = {}
    structured_data = {
        "applicant_name": None,
        "address": None,
        "aadhaar_number": None,
        "pan_number": None,
        "employer_name": None,
        "monthly_income": None,
        "bank_account": None,
        "loan_amount": None,
        "dob": None,
        "phone": None,
        "gender": None,
        "father_name": None,
        "document_type": doc_type,
        "fields": fields_meta
    }
    
    target_fields = ["applicant_name", "aadhaar_number", "dob", "gender", "address"] if doc_type == "aadhaar" else ["applicant_name", "father_name", "pan_number", "dob"]
    
    for f in target_fields:
        v_val = vision_data.get(f)
        o_val = ocr_data.get(f)
        v_status = validated_status.get(f, "unknown")
        
        meta = calculate_field_confidence(f, v_val, o_val, v_status)
        fields_meta[f] = meta
        structured_data[f] = meta["value"]
        
    return structured_data
