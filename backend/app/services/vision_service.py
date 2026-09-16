"""
Vision AI Service using Gemini to extract structured JSON from documents.
"""
import logging
import json
from typing import Dict, Any, Optional
from google import genai
from google.genai.errors import APIError
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Gemini Client
if not settings.gemini_api_key:
    logger.warning("gemini_api_key not found in settings, Vision Service may fail.")

def extract_structured_data(image_path: str, doc_type: str) -> Optional[Dict[str, Any]]:
    """
    Passes original image to Gemini Vision to extract structured JSON data.
    """
    try:
        # Use the latest recommended model for vision tasks
        model_name = "gemini-2.5-flash"
        
        # Load the original image
        try:
            img = Image.open(image_path)
        except Exception as e:
            logger.error(f"Failed to open image for Vision AI: {e}")
            return {"status": "failed", "error_type": "VISION_IMAGE_ERROR"}

        if doc_type == "aadhaar":
            schema = """
{
  "applicant_name": "Full name of the person, or null if not found",
  "aadhaar_number": "12 digit Aadhaar number (digits only), or null",
  "dob": "Date of birth in DD/MM/YYYY format, or null",
  "gender": "Male, Female, Transgender, or null",
  "address": "Full address string, or null"
}"""
            prompt = f"Extract the following fields from this Aadhaar card. Return ONLY a valid JSON object matching this schema. Never hallucinate or guess fields. If a field cannot be confidently identified, use null.\nSchema:\n{schema}"
        elif doc_type == "pan":
            schema = """
{
  "applicant_name": "Full name of the person, or null if not found",
  "father_name": "Full name of the father, or null",
  "pan_number": "10 character PAN number, or null",
  "dob": "Date of birth in DD/MM/YYYY format, or null"
}"""
            prompt = f"Extract the following fields from this PAN card. Return ONLY a valid JSON object matching this schema. Never hallucinate or guess fields. If a field cannot be confidently identified, use null.\nSchema:\n{schema}"
        else:
            return None # Unsupported document type for Vision AI

        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt, img]
        )
        text = response.text
        
        # Parse JSON from response
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            
        data = json.loads(text)
        return {"status": "success", "data": data, "model": model_name}

    except json.JSONDecodeError as e:
        logger.error(f"Vision API returned invalid JSON: {e}")
        return {"status": "failed", "error_type": "VISION_JSON_ERROR"}
    except APIError as e:
        # Avoid logging the full traceback if it contains API keys
        logger.error(f"Vision API exception: {e.message}")
        return {"status": "failed", "error_type": "VISION_API_ERROR", "details": e.message}
    except Exception as e:
        logger.error(f"Vision API unexpected exception: {str(e)}")
        return {"status": "failed", "error_type": "VISION_API_ERROR"}
