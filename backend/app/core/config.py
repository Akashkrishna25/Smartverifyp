"""Application configuration via environment variables."""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "SmartVerify"
    DEBUG: bool = False
    SECRET_KEY: str = "changeme-use-strong-secret-in-production"
    gemini_api_key: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    DATABASE_URL: str = "postgresql://postgres:admin@db:5432/smartverify"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost"]

    UPLOAD_DIR: str = "/app/uploads"
    REPORT_DIR: str = "/app/reports"
    MAX_UPLOAD_SIZE_MB: int = 20

    OCR_LANGUAGE: str = "en"
    SPACY_MODEL: str = "en_core_web_sm"
    MIN_INCOME_FOR_LOAN: float = 25000.0
    MIN_VERIFICATION_SCORE: float = 60.0
    FRAUD_RISK_THRESHOLD: float = 70.0

    CHROMADB_DIR: str = "/app/chroma_db"


    # ── CrewAI Multi-Agent System ─────────────────────────────────────────
    # Toggle between the deterministic pipeline (/verify) and the
    # multi-agent CrewAI pipeline (/verify-agentic).
    CREWAI_ENABLED: bool = True
    # Model string passed to CrewAI's LLM wrapper via LiteLLM, e.g.:
    #   "gemini/gemini-2.5-flash"
    #   "openai/gpt-4o-mini"
    #   "ollama/llama3"
    CREWAI_MODEL: str = "gemini/gemini-2.5-flash"
    CREWAI_TEMPERATURE: float = 0.2
    # API keys for the chosen LLM provider are read directly from the
    # environment by CrewAI/LiteLLM (e.g. GEMINI_API_KEY, OPENAI_API_KEY).

    class Config:
        env_file = ".env"

settings = Settings()
