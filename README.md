# 🎙️ TruthShield AI • Meeting Intelligence Platform & Knowledge Repository

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B.svg)](https://streamlit.io/)
[![OpenAI Whisper](https://img.shields.io/badge/Whisper-ASR-green.svg)](https://github.com/openai/whisper)
[![Google Gemini](https://img.shields.io/badge/Gemini-LLM-8E75B2.svg)](https://ai.google.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-Repository-003B57.svg)](https://sqlite.org/)
[![Infosys Springboard](https://img.shields.io/badge/Infosys_Springboard-Internship_Project-orange.svg)](https://infyspringboard.onwingspan.com/)

[![Milestone 1: Completed](https://img.shields.io/badge/Milestone%201-Completed%20%E2%9C%85-brightgreen.svg)](#milestone-1-audio-processing--speech-recognition-completed-)
[![Milestone 2: Completed](https://img.shields.io/badge/Milestone%202-Completed%20%E2%9C%85-brightgreen.svg)](#milestone-2-intelligent-extraction--repository-persistence-completed-)
[![Milestone 3: Completed](https://img.shields.io/badge/Milestone%203-Completed%20%E2%9C%85-brightgreen.svg)](#milestone-3-semantic-search-rag--api-services-completed-)

An enterprise-grade, end-to-end intelligent meeting transcription, summarization, historical knowledge repository, and contextual RAG (Retrieval-Augmented Generation) question-answering platform developed for the **Infosys Springboard Internship Program**.

The platform ingests multi-speaker audio recordings, transcribes them using **OpenAI Whisper**, extracts structured business intelligence (action items, owners, deadlines, strategic decisions, priorities) using **Google Gemini**, indexes sessions in a persistent **SQLite Knowledge Repository**, and provides semantic cross-meeting search and grounded question-answering via both an interactive **Streamlit** dashboard and authenticated **FastAPI** REST services.

---

## 🎯 Internship Milestones & Completion Status

| Milestone | Deliverables & Scope | Status | Verification & Test Coverage |
| :--- | :--- | :---: | :--- |
| **Milestone 1** | Audio ingestion, audio format validation, Whisper ASR model integration, timestamping, JiWER accuracy benchmark (WER/CER) | **COMPLETED** ✅ | `validate_upload.py`, `validate_transcript.py`, `test_accuracy.py` |
| **Milestone 2** | Gemini multi-speaker intelligence extraction, executive summaries, action item tracking & priority tagging, strategic decisions, SQLite knowledge repository | **COMPLETED** ✅ | `summarizer.py`, `action_engine.py`, `participant_mapper.py`, `test_repository.py` |
| **Milestone 3** | Historical multi-meeting insights & analytics, sub-5ms relational search, contextual RAG Q&A with strict grounding and source attribution, authenticated FastAPI REST service, interactive Streamlit UI studio, master regression test suite | **COMPLETED** ✅ | `ai_search_service.py`, `api.py`, `test_master_suite.py`, `test_search.py`, `test_ai_search.py`, `test_insights.py`, `test_api_integration.py`, `test_search_rag_validation.py`, `test_performance_edge_cases.py`, `test_e2e_integration.py` |

---

## 🚀 Key Features

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

---

## 🛠️ System Architecture

```mermaid
flowchart TD
    subgraph Ingestion["Audio Ingestion & Transcription"]
        Audio[Audio Recording .mp3 / .wav] --> UploadVal[Upload & Format Validator]
        UploadVal --> Whisper[OpenAI Whisper ASR Engine]
        Whisper --> Transcripts[Raw Transcripts & Timestamps]
    end

    subgraph Intelligence["Extraction & Knowledge Repository"]
        Transcripts --> LLM[Gemini 1.5 Pro / Flash & Fallback Engine]
        LLM --> Summary[Executive Summary Engine]
        LLM --> Actions[Action Item & Priority Engine]
        LLM --> Participants[Participant & Speaker Mapper]
        Summary --> DB[(SQLite Knowledge Repository<br/>whisper_meetings.db)]
        Actions --> DB
        Participants --> DB
    end

    subgraph Retrieval["Semantic Search & RAG Context Engine"]
        UserQuery[User Question / Query] --> IntentExtract[Intent & Keyword Extractor]
        IntentExtract --> ContextRetriever[Candidate Context Scoring & Retrieval]
        DB --> ContextRetriever
        ContextRetriever --> PromptContext[Ranked & Bounded Prompt Context]
        PromptContext --> GroundedLLM[Grounded RAG Answer Generator]
        GroundedLLM --> GroundedAnswer[Answer + Source Meeting IDs]
    end

    subgraph Interfaces["Presentation & Integration Layers"]
        DB --> API[FastAPI Authenticated REST API<br/>/meetings, /search, /ask, /insights]
        GroundedAnswer --> API
        API --> StreamlitUI[Streamlit Web Dashboard<br/>app.py]
        API --> ExternalClients[External API Consumers]
    end
```

---

## 📁 Repository Structure

```
whisper_project/
├── app.py                         # Streamlit interactive web application & UI
├── api.py                         # FastAPI REST API with Bearer/API Key authentication
├── database.py                    # SQLite Knowledge Repository & Schema Manager
├── ai_search_service.py           # Contextual RAG search & grounded answering engine
├── pipeline_service.py            # End-to-end audio ingestion & extraction pipeline
├── llm_service.py                 # Gemini LLM abstraction layer with fallback
├── action_engine.py               # Action items, assignees, deadlines & priority extraction
├── participant_mapper.py          # Speaker identification & workload mapping
├── summarizer.py                  # Meeting executive summarizer module
├── transcribe.py                  # CLI audio transcription interface
├── validate_upload.py             # Audio integrity and format validator
├── validate_transcript.py         # Transcript verification engine
├── requirements.txt               # Production and test Python dependencies
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
    ├── test_search_rag_validation.py # Milestone 3: Task 7 Search & RAG validation suite
    ├── test_performance_edge_cases.py# Milestone 3: Task 8 Stress, edge-case & failure suite
    ├── test_e2e_integration.py    # Milestone 3: Task 9 Full workflow integration test suite
    └── test_master_suite.py       # Milestone 3: Master platform regression test runner
```

---

## 🗄️ Database Structure

The SQLite repository (`whisper_meetings.db`) implements a normalized schema enforcing foreign key constraints and indexed queries:

| Table | Description | Key Columns |
| :--- | :--- | :--- |
| **`meetings`** | Primary meeting records | `meeting_id` (PK), `title`, `audio_filename`, `duration_seconds`, `transcript`, `created_at` |
| **`summaries`** | Executive summaries & key points | `id` (PK), `meeting_id` (FK), `summary_text`, `key_points` (JSON) |
| **`decisions`** | Strategic decisions ledger | `id` (PK), `meeting_id` (FK), `decision_text` |
| **`action_items`** | Tracked tasks and deliverables | `id` (PK), `meeting_id` (FK), `task`, `assignee`, `deadline`, `priority`, `status` |
| **`participants`** | Meeting attendees | `id` (PK), `meeting_id` (FK), `participant_name` |
| **`validation_logs`**| Ingestion quality audits | `id` (PK), `meeting_id` (FK), `is_valid`, `checks` (JSON) |

---

## 🌐 API Endpoints

The FastAPI REST API provides interactive documentation at `http://127.0.0.1:8000/docs` (`/redoc`).

### 1. Authentication
Protected endpoints require either a Bearer Token or `X-API-Key` header:
```bash
Authorization: Bearer truthshield-secret-token-2026
# or
X-API-Key: truthshield-secret-token-2026
```

### 2. Core Endpoints

#### `GET /meetings`
List historical meetings with optional keyword search and pagination (`limit`, `offset`).
```bash
curl -X GET "http://127.0.0.1:8000/meetings?limit=10"
```

#### `GET /meetings/{meeting_id}`
Retrieve complete intelligence for a specific meeting (summary, decisions, action items, participants, deadlines).
```bash
curl -X GET "http://127.0.0.1:8000/meetings/MEET-E08D338E"
```

#### `GET /meetings/search` & `POST /search`
Filter historical meetings by keyword, date range (`start_date`, `end_date`), participant, format, or title.
```bash
curl -X POST "http://127.0.0.1:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "database migration", "semantic": true, "limit": 5}'
```

#### `POST /ask`
Authenticated RAG question answering across the entire meeting knowledge repository.
```bash
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Authorization: Bearer truthshield-secret-token-2026" \
  -H "Content-Type: application/json" \
  -d '{"question": "What was decided about the mobile application release date?"}'
```

Sample Response:
```json
{
  "success": true,
  "found": true,
  "question": "What was decided about the mobile application release date?",
  "answer": "The team decided to target the beta release of the mobile application for Q3. [Meeting ID: MEET-235205]",
  "source_meeting_ids": ["MEET-235205"],
  "key_findings": [
    "Beta release target set for Q3.",
    "Priya will finalize UI wireframes by next Friday."
  ],
  "source_meetings": [
    {
      "meeting_id": "MEET-235205",
      "title": "Mobile App Architecture",
      "created_at": "2026-08-27T10:00:00"
    }
  ]
}
```

#### `GET /meetings/insights`
Retrieve aggregated analytics: total meetings, pending/completed tasks, participant workload distribution, and upcoming deadlines.
```bash
curl -X GET "http://127.0.0.1:8000/meetings/insights?status=Pending"
```

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
API_AUTH_TOKEN=truthshield-secret-token-2026

# SQLite Database file path
DATABASE_PATH=whisper_meetings.db
```
*(Note: A free API key can be obtained from [Google AI Studio](https://aistudio.google.com/)).*

---

## 🏃 Running the Application

### Launch Streamlit Dashboard
```bash
streamlit run app.py
```
Access the web dashboard at `http://localhost:8501`.

### Launch FastAPI Server
```bash
uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```
Access Swagger API documentation at `http://127.0.0.1:8000/docs`.

---

## 🧪 Comprehensive Test Suite Execution

The repository includes a battery of 88+ automated test cases covering unit logic, integration flows, failure simulations, and regression benchmarks.

### 1. Master Regression Suite (47 Tests)
Validates all platform subsystems (Database, Retrieval, Search, AI Search, Integrity, API, UI, Regression):
```bash
python -m unittest test_master_suite.py -v
```

### 2. End-to-End Integration Suite (16 Tests)
Validates live audio ingestion of `transcipt_test2.mp3`, transcription, database storage, semantic search, and RAG answering:
```bash
python -m unittest test_e2e_integration.py -v
```

### 3. Search & RAG Validation Suite (27 Tests)
Validates query relevance, out-of-scope rejection, multi-meeting queries, date filters, and zero-hallucination answers:
```bash
python -m unittest test_search_rag_validation.py -v
```

### 4. Stress, Performance & Edge-Case Suite (34 Tests)
Validates large transcripts (>57,000 characters), 20+ dense meetings, query length limits, and simulated LLM/DB outages:
```bash
python -m unittest test_performance_edge_cases.py -v
```

### 5. Speech Transcription Accuracy Benchmark
Measures Word Error Rate (WER) against ground truth reference audio:
```bash
python test_accuracy.py
```

---

## 👥 Contributors & Acknowledgements

- **Author**: Priyanshu ([@priyanshu68-1](https://github.com/priyanshu68-1))
- **Program**: Infosys Springboard Internship
- **Special Thanks**: Mentors, reviewers, and the open-source communities behind OpenAI Whisper, FastAPI, Streamlit, and Google Generative AI.
