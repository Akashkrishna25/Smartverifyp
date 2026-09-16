"""
SmartVerify - Autonomous AI System for Intelligent Loan Verification
Main FastAPI Application Entry Point
"""
import logging, os

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api.endpoints import auth, documents, verification, applications, dashboard, reports
from app.db.database import engine, Base

setup_logging()
logger = logging.getLogger(__name__)

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SmartVerify API",
    description="Autonomous AI System for Intelligent Loan Verification",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.REPORT_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/reports", StaticFiles(directory=settings.REPORT_DIR), name="reports")

app.include_router(auth.router,         prefix="/auth",         tags=["Authentication"])
app.include_router(documents.router,    prefix="/documents",    tags=["Documents"])
app.include_router(verification.router, prefix="/verify",       tags=["Verification"])
app.include_router(applications.router, prefix="/applications", tags=["Applications"])
app.include_router(dashboard.router,    prefix="/dashboard",    tags=["Dashboard"])
app.include_router(reports.router,      prefix="/report",       tags=["Reports"])


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "service": "SmartVerify API", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
