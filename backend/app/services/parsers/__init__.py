"""Document Parsers Module"""
from app.services.parsers.aadhaar_parser import parse_aadhaar
from app.services.parsers.pan_parser import parse_pan

__all__ = ["parse_aadhaar", "parse_pan"]
