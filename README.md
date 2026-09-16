# SmartVerify – Autonomous AI System for Intelligent Loan Verification

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi" />
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react" />
  <img src="https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker" />
  <img src="https://img.shields.io/badge/AI-OCR%20%7C%20NLP%20%7C%20ML-blueviolet" />
</p>

SmartVerify automates the end-to-end loan document verification process using OCR, NLP, machine-learning classification, rule-based verification, and fraud detection — generating downloadable PDF reports with minimal human effort.

---

## Table of Contents
1. [Architecture](#architecture)
2. [Folder Structure](#folder-structure)
3. [Prerequisites](#prerequisites)
4. [Quick Start (Docker)](#quick-start-docker)
5. [Manual Setup](#manual-setup)
6. [API Reference](#api-reference)
7. [AI/ML Pipeline](#aiml-pipeline)
8. [Database Schema](#database-schema)
9. [Environment Variables](#environment-variables)
10. [Workflow](#workflow)
11. [Testing](#testing)
12. [Deployment Guide](#deployment-guide)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     React Frontend                       │
│   Dashboard │ Applications │ Upload │ Verify │ Reports  │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS / REST
┌──────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend                        │
│  Auth  │  Documents  │  Verify  │  Dashboard  │  Reports│
├─────────────────────────────────────────────────────────┤
│                   AI/ML Services                        │
│  Preprocessing │ OCR │ NLP │ Classifier │ Fraud Detect  │
├─────────────────────────────────────────────────────────┤
│               PostgreSQL Database                        │
│  users │ applications │ documents │ verification_reports│
└─────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
smartverify/
├── backend/
│   ├── app/
│   │   ├── api/endpoints/      # Route handlers (auth, docs, verify, …)
│   │   ├── core/               # Config, security, logging
│   │   ├── db/                 # SQLAlchemy engine + session
│   │   ├── models/             # ORM models
│   │   ├── schemas/            # Pydantic schemas
│   │   └── services/           # AI/ML business logic
│   │       ├── preprocessing.py     # OpenCV image enhancement
│   │       ├── ocr_service.py       # EasyOCR + Tesseract
│   │       ├── nlp_service.py       # spaCy + regex extraction
│   │       ├── classification_service.py  # Document classifier
│   │       ├── verification_engine.py     # Rule-based verification
│   │       ├── fraud_detection.py         # Fraud analysis
│   │       └── report_service.py          # ReportLab PDF generator
│   ├── alembic/                # DB migrations
│   ├── scripts/seed.py         # Database seeder
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── auth/           # PrivateRoute
│   │   │   ├── layout/         # Sidebar, Header, Layout
│   │   │   └── ui/             # StatCard, StatusBadge, ScoreGauge, etc.
│   │   ├── context/            # AuthContext (JWT + user state)
│   │   ├── pages/              # LoginPage, Dashboard, Applications, Upload, Verify, Reports
│   │   ├── services/api.js     # Axios client + all API calls
│   │   └── utils/formatters.js
│   └── Dockerfile
│
├── docker/init.sql
├── docker-compose.yml
└── README.md
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Docker | 24+ |
| Docker Compose | v2 |
| Node.js (manual only) | 20+ |
| Python (manual only) | 3.11+ |
| Tesseract OCR (manual only) | 5+ |

---

## Quick Start (Docker)

```bash
# 1. Clone the repo
git clone https://github.com/your-org/smartverify.git
cd smartverify

# 2. Copy and configure environment
cp backend/.env.example backend/.env
# Edit backend/.env – set SECRET_KEY at minimum

# 3. Build and start everything
docker-compose up --build

# 4. Seed the database (in a new terminal)
docker-compose exec backend python scripts/seed.py

# 5. Open the app
# Frontend:  http://localhost:3000
# API Docs:  http://localhost:8000/api/docs
```

**Default credentials**

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@smartverify.com | admin123 |
| Loan Officer | officer@smartverify.com | officer123 |

---

## Manual Setup

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv && .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Install Tesseract (Ubuntu/Debian)
sudo apt-get install tesseract-ocr tesseract-ocr-eng poppler-utils

# Configure environment
cp .env.example .env
# Set DATABASE_URL to your PostgreSQL connection string

# Run migrations
alembic upgrade head

# Seed database
python scripts/seed.py

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
REACT_APP_API_URL=http://localhost:8000 
npm start
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Register new user |
| `POST` | `/auth/login` | Login, returns JWT |
| `GET`  | `/auth/me` | Current user info |
| `POST` | `/applications/` | Create loan application |
| `GET`  | `/applications/` | List applications |
| `DELETE` | `/applications/{id}` | Delete application |
| `POST` | `/documents/upload` | Upload a document (multipart) |
| `POST` | `/documents/process/{id}` | Preprocess + OCR a document |
| `GET`  | `/documents/{app_id}` | List documents for an application |
| `POST` | `/verify/{app_id}` | **Run rule-based AI verification pipeline** |
| `POST` | `/verify/{app_id}/agentic` | **Run multi-agent (CrewAI) verification pipeline** |
| `GET`  | `/report/{app_id}` | Get verification report (JSON) |
| `GET`  | `/report/{app_id}/download` | Download PDF report |
| `GET`  | `/dashboard/stats` | Aggregate analytics stats |

Full interactive docs: `http://localhost:8000/api/docs`

---

## Multi-Agent Verification (CrewAI)

In addition to the deterministic rule-based pipeline, SmartVerify includes a
**multi-agent verification system built on [CrewAI](https://www.crewai.com/)**.
A crew of five specialised agents collaborates — each with its own role,
goal, and toolset — to process a loan application end-to-end and produce a
natural-language summary alongside the same structured outputs as the
rule-based pipeline.

### Agent Pipeline

```
┌────────────────────┐
│  Document Analyst   │  OCR every document, classify its type
└─────────┬───────────┘
          ▼
┌────────────────────────┐
│ Extraction Specialist   │  NLP/NER extraction → structured applicant profile
└─────────┬───────────────┘
          ▼
┌─────────────────────┐   ┌──────────────────────┐
│ Verification Officer │   │  Fraud Investigator   │
│ (eligibility rules)  │   │  (risk scoring)       │
└─────────┬─────────────┘   └──────────┬────────────┘
          │                            │
          └──────────────┬─────────────┘
                          ▼
              ┌──────────────────────┐
              │  Compliance Reporter  │  Final decision + PDF + summary
              └──────────────────────┘
```

| Agent | Role | Tools |
|-------|------|-------|
| **Document Analyst** | Runs OCR and classifies each uploaded document | `document_ocr_tool`, `document_classification_tool` |
| **Data Extraction Specialist** | Extracts a structured applicant profile from combined OCR text | `information_extraction_tool` |
| **Loan Verification Officer** | Applies identity/income/documentation rules | `loan_verification_rule_tool` |
| **Fraud Investigator** | Scores fraud risk and raises alerts | `fraud_detection_tool` |
| **Compliance Reporter** | Combines everything into a final status, PDF report, and plain-English summary | `pdf_report_generation_tool` |

Every tool is a thin wrapper around the **same deterministic services**
(`app/services/*`) used by `/verify/{app_id}` — so results stay explainable
and auditable. The agents add cross-checking, reasoning, and a
human-readable summary on top; a safety net in `LoanVerificationCrew` also
guarantees that **a fraud flag always forces `status = rejected`**, even if
an agent's final JSON disagrees.

### Configuration

Set these in `backend/.env`:

```bash
CREWAI_ENABLED=true
CREWAI_MODEL=anthropic/claude-sonnet-4-6   # or openai/gpt-4o-mini, ollama/llama3, etc.
CREWAI_TEMPERATURE=0.2

# Provide the key matching your chosen provider (read by litellm/CrewAI):
ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
```

### Running It

```bash
# Rule-based (fast, deterministic)
curl -X POST http://localhost:8000/verify/1 \
  -H "Authorization: Bearer <token>"

# Multi-agent (CrewAI) — slower, includes a natural-language summary
curl -X POST http://localhost:8000/verify/1/agentic \
  -H "Authorization: Bearer <token>"
```

In the frontend, the **Verify** page has a mode toggle — choose
**"Multi-Agent (CrewAI)"** to run the agentic pipeline. The result includes
an extra "Compliance Reporter Summary" card and a badge indicating which
mode produced the report. Both modes write to the same
`verification_reports` table; `verification_mode` distinguishes them
(`"rule_based"` vs `"agentic"`), and `agent_summary` / `agent_trace` are
populated only for agentic runs.

### New Database Columns

```sql
ALTER TABLE verification_reports
  ADD COLUMN verification_mode VARCHAR(20) DEFAULT 'rule_based',
  ADD COLUMN agent_summary VARCHAR(2000),
  ADD COLUMN agent_trace JSON;
```

This is included as Alembic migration `0001_add_agentic_columns`. New
deployments get these columns automatically via `Base.metadata.create_all`;
existing deployments should run:

```bash
docker-compose exec backend alembic upgrade head
```

---

## AI/ML Pipeline

### 1. Document Preprocessing (`services/preprocessing.py`)
- **Resize**: upscale small images to ≥1000px width
- **Grayscale + Denoise**: OpenCV `fastNlMeansDenoising`
- **Adaptive Thresholding**: local contrast normalisation
- **Deskewing**: Hough transform–based rotation correction

### 2. OCR (`services/ocr_service.py`)
- **Primary**: EasyOCR (deep-learning CNN+CRNN)
- **Fallback**: Tesseract 5 with `eng+hin` language packs
- **PDFs**: `pdf2image` → page-by-page OCR, `pdfplumber` fallback for text PDFs

### 3. NLP Extraction (`services/nlp_service.py`)
- **Regex patterns**: Aadhaar (12-digit), PAN (ABCDE1234F), phone, income, loan amount, bank account
- **spaCy NER**: PERSON entities → applicant name; ORG entities → employer
- **Address**: PIN code anchor pattern

### 4. Document Classification (`services/classification_service.py`)
- **Stage 1**: Keyword-overlap scoring against 7 document type dictionaries
- **Stage 2 fallback**: HuggingFace `facebook/bart-large-mnli` zero-shot classification

### 5. Verification Engine (`services/verification_engine.py`)
Weighted rule checks:

| Check | Weight | Pass Condition |
|-------|--------|----------------|
| Identity verification | 30 | Name + identity document present |
| Income verification | 30 | Income ≥ ₹25,000/month |
| Required documents | 25 | Identity + income docs uploaded |
| PAN format | 10 | Matches `[A-Z]{5}[0-9]{4}[A-Z]` |
| Aadhaar format | 5 | 12-digit number |

**Score ≥ 60** → Approved | **40–59** → Manual Review | **< 40** → Rejected

### 6. Fraud Detection (`services/fraud_detection.py`)
Risk points accumulate for:
- Missing required documents (+10 each)
- Duplicate Aadhaar in another application (+30)
- Monthly income > ₹5,00,000 (+15)
- Loan-to-annual-income ratio > 10x (+20)
- Missing applicant name (+10)
- Invalid PAN format (+25)

**Risk ≥ 70** → Fraud flag → Force rejection

### 7. PDF Report (`services/report_service.py`)
ReportLab-generated A4 PDF with:
- Application summary banner with colour-coded status
- Score gauges (verification + risk)
- Extracted information table (with masked sensitive fields)
- Per-check breakdown table
- Fraud alerts section
- Final recommendation

---

## Database Schema

```sql
users (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  role ENUM('admin','loan_officer') DEFAULT 'loan_officer',
  created_at TIMESTAMP DEFAULT NOW()
);

applications (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  applicant_name VARCHAR(255),
  loan_amount FLOAT NOT NULL,
  status ENUM('pending','approved','rejected','manual_review') DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

documents (
  id SERIAL PRIMARY KEY,
  application_id INTEGER REFERENCES applications(id) ON DELETE CASCADE,
  document_type ENUM('aadhaar','pan','salary_slip','income_cert',
                     'employment_cert','bank_statement','loan_application'),
  file_path VARCHAR(500) NOT NULL,
  original_name VARCHAR(255),
  extracted_text TEXT,
  processed INTEGER DEFAULT 0,   -- 0=raw, 1=preprocessed, 2=ocr-done
  created_at TIMESTAMP DEFAULT NOW()
);

verification_reports (
  id SERIAL PRIMARY KEY,
  application_id INTEGER REFERENCES applications(id) ON DELETE CASCADE UNIQUE,
  verification_score FLOAT DEFAULT 0,
  risk_score FLOAT DEFAULT 0,
  fraud_flag BOOLEAN DEFAULT FALSE,
  status VARCHAR(50) DEFAULT 'pending',
  extracted_info JSONB,
  fraud_analysis JSONB,
  verification_details JSONB,
  pdf_path VARCHAR(500),
  verification_mode VARCHAR(20) DEFAULT 'rule_based',  -- 'rule_based' | 'agentic'
  agent_summary VARCHAR(2000),                         -- CrewAI plain-English summary
  agent_trace JSON,                                    -- raw CrewAI output (audit)
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(required)* | JWT signing secret |
| `DATABASE_URL` | `postgresql://…@db:5432/smartverify` | PostgreSQL connection |
| `ALLOWED_ORIGINS` | `["http://localhost:3000"]` | CORS whitelist |
| `UPLOAD_DIR` | `/app/uploads` | Document storage path |
| `REPORT_DIR` | `/app/reports` | PDF storage path |
| `MIN_INCOME_FOR_LOAN` | `25000` | Monthly income threshold (₹) |
| `MIN_VERIFICATION_SCORE` | `60` | Approval threshold (0–100) |
| `FRAUD_RISK_THRESHOLD` | `70` | Fraud flag threshold (0–100) |
| `CREWAI_ENABLED` | `true` | Enable/disable `/verify/{id}/agentic` |
| `CREWAI_MODEL` | `anthropic/claude-sonnet-4-6` | LLM used by all CrewAI agents |
| `CREWAI_TEMPERATURE` | `0.2` | LLM sampling temperature for agents |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | *(required for agentic mode)* | API key matching `CREWAI_MODEL`'s provider |

---

## Workflow

```
1. LOGIN          → Obtain JWT token
       ↓
2. CREATE APP     → POST /applications/ (applicant name + loan amount)
       ↓
3. UPLOAD DOCS    → POST /documents/upload  (one per document type)
       ↓
4. AUTO OCR       → POST /documents/process/{id}  (auto-triggered after upload)
       ↓
5. VERIFY         → POST /verify/{app_id}
                    ├── Aggregate all OCR text
                    ├── NLP extraction
                    ├── Verification rules engine
                    ├── Fraud detection
                    ├── PDF generation
                    └── Update application status
       ↓
6. REPORTS        → GET /report/{app_id}/download  (PDF)
       ↓
7. DASHBOARD      → GET /dashboard/stats  (analytics)
```

---

## Testing

```bash
# Backend unit tests
cd backend
pytest tests/ -v

# API smoke test (requires running server)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@smartverify.com","password":"admin123"}'
```

---

## Deployment Guide

### Production Docker Compose

```bash
# Generate a strong secret key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Set in backend/.env
SECRET_KEY=<generated-key>
DEBUG=false
DATABASE_URL=postgresql://user:pass@your-db-host:5432/smartverify

# Build production images
docker-compose -f docker-compose.yml up --build -d

# Run DB migrations
docker-compose exec backend alembic upgrade head

# Seed initial users
docker-compose exec backend python scripts/seed.py
```

### Production Checklist

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Set `DEBUG=false`
- [ ] Use a managed PostgreSQL instance (e.g., RDS, Cloud SQL)
- [ ] Mount `uploads/` and `reports/` on persistent storage
- [ ] Place Nginx reverse proxy in front of both services
- [ ] Enable HTTPS (Let's Encrypt via Certbot)
- [ ] Set `ALLOWED_ORIGINS` to your production domain
- [ ] Enable PostgreSQL SSL (`?sslmode=require` in DATABASE_URL)
- [ ] Set up log aggregation (CloudWatch, Datadog, etc.)
- [ ] Configure automated backups for PostgreSQL

### Nginx Sample Config

```nginx
server {
    listen 443 ssl;
    server_name smartverify.yourdomain.com;

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 25M;
    }

    location / {
        proxy_pass http://localhost:3000;
    }
}
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit changes with clear messages
4. Open a pull request

---

## License

MIT License — see [LICENSE](LICENSE) for details.
