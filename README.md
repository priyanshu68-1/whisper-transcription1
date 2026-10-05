# 🎙️ WhisperSense AI • Enterprise Meeting Intelligence Platform & Knowledge Repository

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B.svg)](https://streamlit.io/)
[![OpenAI Whisper](https://img.shields.io/badge/Whisper-ASR-green.svg)](https://github.com/openai/whisper)
[![Google Gemini](https://img.shields.io/badge/Gemini-LLM-8E75B2.svg)](https://ai.google.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-Repository-003B57.svg)](https://sqlite.org/)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED.svg)](https://www.docker.com/)
[![Infosys Springboard](https://img.shields.io/badge/Infosys_Springboard-Internship_Project-orange.svg)](https://infyspringboard.onwingspan.com/)

[![Milestone 1: Completed](https://img.shields.io/badge/Milestone%201-Completed%20%E2%9C%85-brightgreen.svg)](#milestone-1-audio-processing--speech-recognition-completed-)
[![Milestone 2: Completed](https://img.shields.io/badge/Milestone%202-Completed%20%E2%9C%85-brightgreen.svg)](#milestone-2-intelligent-extraction--repository-persistence-completed-)
[![Milestone 3: Completed](https://img.shields.io/badge/Milestone%203-Completed%20%E2%9C%85-brightgreen.svg)](#milestone-3-semantic-search-rag--api-services-completed-)
[![Milestone 4: Completed](https://img.shields.io/badge/Milestone%204-Completed%20%E2%9C%85-brightgreen.svg)](#milestone-4-integrations-multi-tenancy-exports--deployment-completed-)

An enterprise-grade, end-to-end meeting transcription, summarization, historical knowledge repository, external video conference ingestion (Zoom & Google Meet), multi-tenant session security, and contextual RAG (Retrieval-Augmented Generation) intelligence platform developed for the **Infosys Springboard Internship Program**.

The platform ingests multi-speaker audio recordings and cloud meeting webhooks, transcribes them using **OpenAI Whisper**, extracts structured business intelligence (action items, owners, deadlines, strategic decisions, priorities) using **Google Gemini**, indexes sessions in a persistent **SQLite Knowledge Repository** with B-tree indexes, generates publication-ready **ReportLab Executive PDF Dossiers & CSV spreadsheets**, and provides semantic cross-meeting search and grounded question-answering via both an interactive **Streamlit** dashboard and authenticated **FastAPI** REST services.

---

## 🎯 Internship Milestones & Completion Status

| Milestone | Deliverables & Scope | Status | Verification & Test Coverage |
| :--- | :--- | :---: | :--- |
| **Milestone 1** | Audio ingestion, audio format validation, Whisper ASR model integration, timestamping, JiWER accuracy benchmark (WER/CER) | **COMPLETED** ✅ | `validate_upload.py`, `validate_transcript.py`, `test_accuracy.py` |
| **Milestone 2** | Gemini multi-speaker intelligence extraction, executive summaries, action item tracking & priority tagging, strategic decisions, SQLite knowledge repository | **COMPLETED** ✅ | `summarizer.py`, `action_engine.py`, `participant_mapper.py`, `test_repository.py` |
| **Milestone 3** | Historical multi-meeting insights & analytics, sub-5ms relational search, contextual RAG Q&A with strict grounding and source attribution, authenticated FastAPI REST service, interactive Streamlit UI studio, master regression test suite | **COMPLETED** ✅ | `ai_search_service.py`, `api.py`, `test_master_suite.py`, `test_search.py`, `test_ai_search.py`, `test_insights.py`, `test_api_integration.py`, `test_search_rag_validation.py`, `test_performance_edge_cases.py`, `test_e2e_integration.py` |
| **Milestone 4** | User authentication & multi-tenant isolation, Zoom Cloud HMAC-SHA256 webhook integration, Google Meet canonical code ingestion, ReportLab Executive PDF dossier & CSV export, security hardening, Playwright browser test suite, Docker containerization, and 1-click Windows launchers | **COMPLETED** ✅ | `zoom_integration.py`, `google_meet_integration.py`, `report_exporter.py`, `browser_full_test.py`, `test_zoom_integration.py`, `test_google_meet_integration.py`, `test_reports_export.py`, `test_user_access_security.py`, `test_milestone4_e2e.py`, `test_milestone4_performance_security.py` |

---

## 🚀 Key Features by Milestone

### Milestone 1: Audio Processing & Speech Recognition `[COMPLETED ✅]`
- **Audio Validation**: Validates audio format (`.mp3`, `.wav`, `.m4a`, `.mp4`), duration, channels, and sample rate.
- **OpenAI Whisper ASR**: Automatic speech recognition across model tiers (`tiny`, `base`, `small`, `medium`) with word and segment timestamps.
- **Accuracy Benchmarking**: Quantitatively evaluated with **JiWER** measuring Word Error Rate (WER: 0.00% benchmark achieved).

### Milestone 2: Intelligent Extraction & Repository Persistence `[COMPLETED ✅]`
- **Executive Summaries**: High-level and comprehensive synthesis of discussions.
- **Action Items & Task Allocation**: Automatic extraction of actionable commitments, assignees, deadlines, and priorities (`High`, `Medium`, `Low`).
- **Strategic Decisions & Key Points**: Immutable logging of strategic consensus and discussion highlights.
- **Participant Mapping**: Speaker recognition and contribution tracking.
- **Persistent Knowledge Repository**: SQLite database (`whisper_meetings.db`) with relational integrity, foreign key cascading, and automated migrations.

### Milestone 3: Semantic Search, RAG & API Services `[COMPLETED ✅]`
- **Multi-Meeting Historical Insights**: Aggregate KPIs, cross-meeting task completion metrics, participant workload distributions, and deadline schedules.
- **Unified Relational & Semantic Search**: Sub-5ms indexed keyword search across transcripts, titles, summaries, decisions, and tasks, with multi-term token fallback.
- **RAG Question Answering**: Retrieves bounded, relevant meeting contexts and prompts Gemini (or deterministic fallback) with strict grounding instructions to eliminate hallucinations.
- **Source Meeting Attribution**: Every factual assertion cites the exact source `meeting_id` and metadata.
- **Production REST API**: FastAPI server offering `/meetings`, `/meetings/{id}`, `/search`, and `/ask` with Bearer token / `X-API-Key` authentication.
- **Resilient Fallback Engines**: Rule-based NLP fallback pipelines ensuring 100% service uptime during upstream LLM rate limits or network partitions.

### Milestone 4: Integrations, Multi-Tenancy, Exports & Deployment `[COMPLETED ✅]`
- **Multi-Tenant User Authentication & Session Security**:
  - Salted SHA-256 password hashing with user registration and session tokens.
  - Multi-tenant data segregation preventing IDOR (Insecure Direct Object Reference).
  - Streamlit authentication portal featuring seamless tabbed sign-in/registration and 1-click Demo account evaluation.
- **Zoom Cloud Ingestion & Webhooks**:
  - HMAC-SHA256 signature verification for Zoom App Marketplace webhooks (`endpoint.url_validation` and `recording.completed`).
  - Automated duplicate event filtering and async audio download & ingestion pipeline.
  - Dedicated Streamlit and REST API endpoints (`/integrations/zoom/webhook`, `/integrations/zoom/sync`, `/integrations/zoom/status`).
- **Google Meet Ingestion**:
  - Canonical 3-4-3 Google Meet meeting code validation (`xxx-yyyy-zzz`).
  - Cloud Drive sync ingestion pipeline for recorded meetings (`/integrations/google-meet/sync`, `/integrations/google-meet/status`).
- **Publication-Ready Export & Reporting**:
  - **ReportLab Executive PDF Dossier**: Professional multi-page PDF documents featuring branded headers, metadata tables, executive summary callouts, strategic decisions ledger, and priority-colored action items table.
  - **Structured CSV Spreadsheets**: Multi-section comprehensive meeting export and dedicated task/deliverable CSV trackers.
  - Built-in Paraparser XML sanitization defending against XSS injection vulnerabilities.
- **Performance & Security Hardening**:
  - B-tree indexing across `meetings.user_id`, `created_at`, `action_items.meeting_id`, and `action_items.status`.
  - Sub-5ms indexed query execution across large meeting datasets.
- **Automated Browser & Regression Testing**:
  - Headless Playwright browser test suite verifying all 8 tabs and user workflows in Chrome.
  - Comprehensive unit and integration test suite with 100% passing checks.
- **Containerization & 1-Click Launchers**:
  - Production `Dockerfile` with system ffmpeg and multi-port exposure (8501, 8000).
  - Multi-service `docker-compose.yml` orchestrating FastAPI backend and Streamlit dashboard with persistent volumes.
  - Windows 1-click launch batch scripts (`run_all.bat`, `run_dashboard.bat`, `run_api.bat`).

---

## 🛠️ System Architecture

```mermaid
flowchart TD
    subgraph Sources["Meeting Ingestion Sources"]
        Audio[Local Audio Files .mp3 / .wav] --> UploadVal[Upload & Format Validator]
        ZoomWebhook[Zoom Cloud Webhook<br/>HMAC-SHA256 Signature] --> ZoomService[Zoom Integration Service]
        GoogleMeet[Google Meet Code / Drive<br/>Canonical 3-4-3 Parser] --> MeetService[Google Meet Service]
    end

    subgraph Transcription["ASR & Extraction Pipeline"]
        UploadVal --> Whisper[OpenAI Whisper ASR Engine]
        ZoomService --> Whisper
        MeetService --> Whisper
        Whisper --> Transcripts[Raw Transcripts & Word Timestamps]
        Transcripts --> LLM[Google Gemini LLM & Deterministic Fallback]
        LLM --> Summary[Executive Summary Engine]
        LLM --> Actions[Action Item & Priority Engine]
        LLM --> Decisions[Strategic Decisions Ledger]
        LLM --> Participants[Participant Mapper]
    end

    subgraph Repository["Indexed Multi-Tenant Repository"]
        Summary --> DB[(SQLite Knowledge Repository<br/>whisper_meetings.db<br/>B-Tree Indexes & Foreign Keys)]
        Actions --> DB
        Decisions --> DB
        Participants --> DB
        Users[Multi-Tenant Auth<br/>Salted SHA-256 Users] --> DB
    end

    subgraph Exporters["Export & Reporting Subsystem"]
        DB --> ReportLab[ReportLab PDF Engine<br/>XML Sanitization & Layout]
        DB --> CSVEngine[CSV Spreadsheet Engine]
        ReportLab --> PDFDossier[Executive PDF Dossier]
        CSVEngine --> FullCSV[Meeting & Tasks CSVs]
    end

    subgraph RAGEngine["Semantic Search & RAG Assistant"]
        UserQuery[User Question / Search Query] --> Retriever[Indexed Relational & Vector Search]
        DB --> Retriever
        Retriever --> Context[Ranked Meeting Contexts]
        Context --> GroundedLLM[Grounded RAG Answer Generator]
        GroundedLLM --> GroundedAnswer[Grounded Answer + Source Meeting IDs]
    end

    subgraph Interfaces["Presentation & API Layer"]
        DB --> FastAPI[FastAPI REST Backend :8000<br/>Bearer & X-API-Key Auth]
        GroundedAnswer --> FastAPI
        PDFDossier --> FastAPI
        FullCSV --> FastAPI
        FastAPI --> StreamlitUI[Streamlit Web Studio :8501<br/>8 Interactive Tabs]
        PDFDossier --> StreamlitUI
        FullCSV --> StreamlitUI
        FastAPI --> ExternalApps[Third-Party Enterprise Clients]
    end
```

---

## 📁 Repository Structure

```
whisper_project/
├── app.py                         # Streamlit interactive web dashboard & intelligence UI
├── api.py                         # FastAPI REST API with Bearer/API Key & Webhook endpoints
├── database.py                    # SQLite Knowledge Repository (schema, migrations, B-tree indexes)
├── ai_search_service.py           # Contextual RAG search & grounded answering engine
├── pipeline_service.py            # End-to-end audio ingestion & extraction pipeline
├── llm_service.py                 # Gemini LLM abstraction layer with deterministic fallback
├── report_exporter.py             # ReportLab executive PDF dossier & CSV export generators
├── zoom_integration.py            # Zoom Cloud recording ingestion & HMAC-SHA256 webhook handler
├── google_meet_integration.py     # Google Meet canonical code parser & Drive sync service
├── action_engine.py               # Action items, assignees, deadlines & priority extraction
├── participant_mapper.py          # Speaker identification & workload mapping
├── summarizer.py                  # Meeting executive summarizer module
├── transcribe.py                  # CLI audio transcription interface
├── validate_upload.py             # Audio integrity and format validator
├── validate_transcript.py         # Transcript verification engine
├── browser_full_test.py           # Playwright automated browser test script across all tabs
│
├── Dockerfile                     # Production container image with ffmpeg
├── docker-compose.yml             # Dual-service orchestrator (FastAPI :8000 & Streamlit :8501)
├── .dockerignore                  # Docker build exclusion rules
├── run_all.bat                    # Windows 1-click master launcher (Starts both services + Browser)
├── run_dashboard.bat              # Windows 1-click Streamlit frontend launcher
├── run_api.bat                    # Windows 1-click FastAPI backend launcher
├── requirements.txt               # Production Python dependencies
├── .env.example                   # Environment configuration template
├── README.md                      # Comprehensive project documentation
│
└── tests/
    ├── test_accuracy.py           # Milestone 1: WER/CER transcription accuracy benchmark
    ├── test_repository.py         # Milestone 2: Database persistence & CRUD validation
    ├── test_insights.py           # Milestone 2: Historical insights & cross-meeting analytics
    ├── test_search.py             # Milestone 3: Relational search & filtering validation
    ├── test_ai_search.py          # Milestone 3: Semantic search engine unit tests
    ├── test_api_integration.py    # Milestone 3: FastAPI endpoints & authentication testing
    ├── test_search_rag_validation.py # Milestone 3: Search & RAG grounding validation
    ├── test_performance_edge_cases.py# Milestone 3: Stress, edge-case & failure simulation
    ├── test_e2e_integration.py    # Milestone 3: Full workflow integration test suite
    ├── test_master_suite.py       # Milestone 3: Master platform regression test runner
    ├── test_zoom_integration.py   # Milestone 4: Zoom HMAC verification & webhook processing
    ├── test_google_meet_integration.py # Milestone 4: Google Meet canonical parser & Drive sync
    ├── test_reports_export.py     # Milestone 4: ReportLab PDF and CSV export verification
    ├── test_user_access_security.py # Milestone 4: Multi-tenant auth & IDOR security validation
    ├── test_milestone4_e2e.py     # Milestone 4: Complete end-to-end integration lifecycle
    └── test_milestone4_performance_security.py # Milestone 4: Performance, indexes & XSS hardening
```

---

## 🗄️ Database Structure

The SQLite repository (`whisper_meetings.db`) implements a normalized schema enforcing foreign key constraints and B-tree indexes:

| Table | Description | Key Columns & Indexes |
| :--- | :--- | :--- |
| **`users`** | Multi-tenant user accounts | `id` (PK), `username` (UNIQUE), `password_hash`, `salt`, `created_at` |
| **`meetings`** | Primary meeting records | `meeting_id` (PK), `user_id` (FK, Indexed), `title`, `audio_filename`, `duration_seconds`, `transcript`, `created_at` (Indexed) |
| **`summaries`** | Executive summaries & key points | `id` (PK), `meeting_id` (FK), `summary_text`, `key_points` (JSON) |
| **`decisions`** | Strategic decisions ledger | `id` (PK), `meeting_id` (FK), `decision_text` |
| **`action_items`** | Tracked tasks and deliverables | `id` (PK), `meeting_id` (FK, Indexed), `task`, `assignee`, `deadline`, `priority`, `status` (Indexed) |
| **`participants`** | Meeting attendees | `id` (PK), `meeting_id` (FK), `participant_name` |
| **`validation_logs`**| Ingestion quality audits | `id` (PK), `meeting_id` (FK), `is_valid`, `checks` (JSON) |

---

## 🌐 API Endpoints Reference

The FastAPI REST API provides interactive documentation at `http://127.0.0.1:8000/docs` (`/redoc`).

### 1. Authentication Headers
Protected endpoints require either a Bearer Token or `X-API-Key` header:
```bash
Authorization: Bearer whispersense-secret-key-2024
# or
X-API-Key: whispersense-secret-key-2024
```

### 2. Core Endpoints Table

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/auth/register` | Register a new user account with salted password hashing |
| `POST` | `/auth/login` | Authenticate user and receive session profile |
| `GET` | `/auth/me` | Retrieve authenticated profile |
| `GET` | `/meetings` | List historical meetings with pagination (`limit`, `offset`) and search |
| `GET` | `/meetings/{meeting_id}` | Retrieve complete intelligence for a specific meeting |
| `DELETE`| `/meetings/{meeting_id}` | Delete a meeting record with cascade cleanup |
| `GET` | `/meetings/search` | Query meetings with filters (`participant`, `date`, `format`, `title`) |
| `POST` | `/search` | Advanced relational/semantic search payload |
| `POST` | `/ask` | Grounded RAG question answering across meetings |
| `POST` | `/meetings/ai-search` | Dedicated semantic search endpoint with source citations |
| `GET` | `/meetings/insights` | Aggregate KPIs, participant workloads, task metrics |
| `GET` | `/meetings/{meeting_id}/export/pdf` | Generate and download ReportLab Executive PDF Dossier |
| `GET` | `/meetings/{meeting_id}/export/csv` | Download complete meeting data in structured CSV format |
| `GET` | `/meetings/{meeting_id}/export/action-items` | Export action items for a meeting into CSV spreadsheet |
| `POST` | `/integrations/zoom/webhook` | Zoom App Marketplace webhook receiver (HMAC verification) |
| `POST` | `/integrations/zoom/sync` | Manually ingest Zoom cloud recording by Meeting ID/UUID |
| `GET` | `/integrations/zoom/status` | Ingestion status for Zoom meeting |
| `POST` | `/integrations/google-meet/sync`| Ingest Google Meet recording via URL or 3-4-3 code |
| `GET` | `/integrations/google-meet/status`| Ingestion status for Google Meet code |

---

## 💻 Installation & Setup

### 1. Prerequisites
- **Python 3.9+** (Tested on Python 3.10, 3.11, 3.12, 3.13)
- **FFmpeg**: Required by Whisper for audio decoding.
  - **Windows**: `winget install Gyan.FFmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html).
  - **Linux**: `sudo apt update && sudo apt install ffmpeg`
  - **macOS**: `brew install ffmpeg`

### 2. Clone the Repository
```bash
git clone https://github.com/priyanshu68-1/whisper-transcription1.git
cd whisper-transcription1
```

### 3. Create and Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to configure your API keys:
```env
# Google Gemini API Key for transcription analysis, summarization, and RAG
GEMINI_API_KEY=your_gemini_api_key_here

# Bearer / X-API-Key token for REST API authentication
API_AUTH_TOKEN=whispersense-secret-key-2024

# Zoom Webhook Secret Token (from Zoom App Marketplace)
ZOOM_WEBHOOK_SECRET_TOKEN=sample_secret_token_12345

# SQLite Database file path
DATABASE_PATH=whisper_meetings.db
```

---

## 🏃 Running the Application

### Option A: 1-Click Windows Launchers (Recommended for Windows)
- **Launch Everything**: Double-click `run_all.bat` (Starts FastAPI, starts Streamlit, and launches your browser at `http://localhost:8501`).
- **Dashboard Only**: Double-click `run_dashboard.bat` (Runs Streamlit at `http://localhost:8501`).
- **REST API Only**: Double-click `run_api.bat` (Runs FastAPI at `http://127.0.0.1:8000`).

### Option B: Docker Compose (Production Containerized)
```bash
# Build and run both FastAPI and Streamlit services
docker-compose up --build

# Run in background (detached mode)
docker-compose up -d

# Stop services
docker-compose down
```
- **Streamlit Web Dashboard**: `http://localhost:8501`
- **FastAPI REST API**: `http://localhost:8000/docs`

### Option C: Manual CLI Execution
```bash
# Terminal 1: Launch FastAPI REST backend
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Launch Streamlit Dashboard
python -m streamlit run app.py --server.port 8501
```

---

## 🧪 Comprehensive Test Suite Execution

The repository includes a comprehensive battery of 115+ automated test cases covering unit logic, integration flows, failure simulations, and regression benchmarks.

### 1. Milestone 4 Comprehensive End-to-End Suite (10 Tests)
Validates all 8 phases of Milestone 4 (Auth, Audio Ingestion, Zoom, Meet, PDF/CSV Export, RAG, Multi-Tenant Isolation):
```bash
python -m unittest test_milestone4_e2e.py -v
```

### 2. Milestone 4 Performance, Security & Hardening Suite (11 Tests)
Validates B-tree indexing, query latency (<5ms), ReportLab XSS protection, and input boundary security:
```bash
python -m unittest test_milestone4_performance_security.py -v
```

### 3. Zoom Integration Suite (8 Tests)
Validates HMAC-SHA256 signature verification, challenge responses, and webhook payload ingestion:
```bash
python -m unittest test_zoom_integration.py -v
```

### 4. Google Meet Integration Suite (5 Tests)
Validates 3-4-3 canonical code parser, Google Drive sync simulator, and duplicate detection:
```bash
python -m unittest test_google_meet_integration.py -v
```

### 5. ReportLab PDF & CSV Exporter Suite (11 Tests)
Validates PDF document generation, binary byte integrity, CSV formatting, and XML sanitization:
```bash
python -m unittest test_reports_export.py -v
```

### 6. User Access & Security Validation Suite (5 Tests)
Validates password hashing, user registration, authenticated sessions, and multi-tenant IDOR protection:
```bash
python -m unittest test_user_access_security.py -v
```

### 7. Playwright Automated Browser Test Suite
Runs a headless browser to test and screenshot all 8 navigation tabs and interactive workflows:
```bash
python browser_full_test.py
```

### 8. Milestone 3 Master Regression Suite (47 Tests)
Validates core database persistence, semantic retrieval, RAG grounding, and API endpoints:
```bash
python -m unittest test_master_suite.py -v
```

---

## 👥 Contributors & Acknowledgements

- **Author**: Priyanshu ([@priyanshu68-1](https://github.com/priyanshu68-1))
- **Program**: Infosys Springboard Internship
- **Special Thanks**: Mentors, reviewers, and the open-source communities behind OpenAI Whisper, FastAPI, Streamlit, ReportLab, and Google Generative AI.
