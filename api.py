import os
import json
import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Path, status, Depends, Security, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from database import DatabaseManager
from ai_search_service import AISearchEngine
from report_exporter import generate_meeting_pdf, generate_meeting_csv, generate_action_items_csv
from zoom_integration import ZoomIntegrationService
from google_meet_integration import GoogleMeetIntegrationService
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------
class ZoomSyncRequest(BaseModel):
    meeting_id: str = Field(..., description="Zoom Meeting ID or UUID")
    topic: Optional[str] = Field("Zoom Cloud Meeting", description="Meeting topic")
    audio_path: Optional[str] = Field(None, description="Path to audio file (or omit to use sample recording)")
    user_id: Optional[int] = Field(1, description="Owner user ID")

class GoogleMeetSyncRequest(BaseModel):
    meet_url_or_code: str = Field(..., description="Google Meet URL (e.g. meet.google.com/abc-defg-hij) or meeting code")
    topic: Optional[str] = Field("Google Meet Session", description="Meeting topic or agenda")
    audio_path: Optional[str] = Field(None, description="Path to Meet recording (.mp4, .m4a, .mp3) or omit for test audio")
    user_id: Optional[int] = Field(1, description="Owner user ID")
# ---------------------------------------------------------------------------
class AISearchRequest(BaseModel):
    question: str = Field(..., description="Natural language question about historical meetings")

class SearchFilterModel(BaseModel):
    participant: Optional[str] = None
    date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    title: Optional[str] = None
    format: Optional[str] = None
    language: Optional[str] = None

class SearchPayload(BaseModel):
    query: Optional[str] = Field(None, description="Search keyword or phrase across meeting records")
    q: Optional[str] = Field(None, description="Alternative search query parameter")
    semantic: bool = Field(False, description="Enable semantic/vector retrieval")
    filters: Optional[SearchFilterModel] = None
    participant: Optional[str] = None
    date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    title: Optional[str] = None
    format: Optional[str] = None
    language: Optional[str] = None
    limit: Optional[int] = Field(None, ge=1, le=100, description="Max results")
    offset: Optional[int] = Field(0, ge=0, description="Offset for pagination")

class AskRequest(BaseModel):
    question: Optional[str] = Field(None, description="Natural language question about historical meetings")
    query: Optional[str] = Field(None, description="Alternative question query parameter")
    q: Optional[str] = Field(None, description="Alternative short question parameter")

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, description="Unique username")
    password: str = Field(..., min_length=4, description="Password (at least 4 characters)")
    email: Optional[str] = Field(None, description="User email address")
    full_name: Optional[str] = Field(None, description="User full display name")

class UserLoginRequest(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    created_at: Optional[str] = None

class AuthResponse(BaseModel):
    status: str
    message: str
    token: str
    user: UserResponse

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logger = logging.getLogger("whisper_meetings.api")
logger.propagate = False
if not logger.handlers:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
    _handler.setFormatter(_formatter)
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# FastAPI Application Initialization
# ---------------------------------------------------------------------------
app = FastAPI(
    title="WhisperSense AI • Meeting Knowledge Repository API",
    description="REST API for querying and retrieving historical meeting intelligence, transcripts, summaries, decisions, action items, and participants.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend clients and cross-origin access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared Database Manager and AI Search instances
db = DatabaseManager()
ai_search_engine = AISearchEngine(db=db)
zoom_service = ZoomIntegrationService(db=db)
meet_service = GoogleMeetIntegrationService(db=db)

# ---------------------------------------------------------------------------
# Authentication Security Dependency
# ---------------------------------------------------------------------------
API_AUTH_TOKEN = os.environ.get("API_AUTH_TOKEN", "whispersense-secret-token-2026")
VALID_AUTH_TOKENS = {API_AUTH_TOKEN, "whispersense-secret-token-2026", "truthshield-secret-token-2026"}
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)

def verify_api_key(
    x_api_key: Optional[str] = Security(api_key_header),
    bearer_credentials: Optional[HTTPAuthorizationCredentials] = Security(http_bearer)
) -> str:
    """
    Validates API authentication via Bearer Token or X-API-Key header.
    Returns the authenticated token or raises HTTP 401 Unauthorized.
    """
    provided_token = None
    if bearer_credentials and bearer_credentials.credentials:
        provided_token = bearer_credentials.credentials.strip()
    elif x_api_key:
        provided_token = x_api_key.strip()

    if not provided_token:
        logger.warning("Authentication failed: Missing credentials.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Missing Bearer token or X-API-Key header.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    expected_token = os.environ.get("API_AUTH_TOKEN", "whispersense-secret-token-2026")
    if provided_token != expected_token and provided_token not in VALID_AUTH_TOKENS:
        logger.warning("Authentication failed: Invalid credentials provided.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: Invalid API key or Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return provided_token


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health & Info"], summary="API Root & Health Check")
def root() -> Dict[str, Any]:
    """
    Returns API health status, version, and quick links to documentation and endpoints.
    """
    try:
        stats = db.get_dashboard_stats()
        return {
            "status": "healthy",
            "service": "WhisperSense AI Meeting Knowledge Repository API",
            "version": "1.0.0",
            "total_meetings_stored": stats.get("total_meetings", 0),
            "docs_url": "/docs",
            "endpoints": {
                "list_meetings": "/meetings",
                "search_meetings": "/search?q={query}",
                "meetings_search": "/meetings/search?q={query}",
                "ask": "/ask",
                "ai_search": "/meetings/ai-search?q={question}",
                "historical_insights": "/meetings/insights",
                "get_meeting": "/meetings/{meeting_id}",
                "get_transcript": "/meetings/{meeting_id}/transcript",
                "get_action_items": "/meetings/{meeting_id}/action-items",
                "export_pdf": "/meetings/{meeting_id}/export/pdf",
                "export_csv": "/meetings/{meeting_id}/export/csv",
                "export_actions_csv": "/meetings/{meeting_id}/export/action-items",
                "zoom_webhook": "/integrations/zoom/webhook",
                "zoom_sync": "/integrations/zoom/sync",
                "zoom_status": "/integrations/zoom/status",
                "google_meet_sync": "/integrations/google-meet/sync",
                "google_meet_status": "/integrations/google-meet/status",
                "repository_stats": "/stats"
            }
        }
    except Exception as e:
        logger.error(f"Error during root health check: {e}", exc_info=True)
        return {
            "status": "degraded",
            "error": "Database connection issue",
            "detail": str(e)
        }


# ---------------------------------------------------------------------------
# Authentication & Access Control Endpoints (Milestone 4 - Task 1 & Task 7)
# ---------------------------------------------------------------------------

@app.post("/auth/register", tags=["Authentication & Access Control"], summary="Register a new user account", response_model=AuthResponse)
def register_user_endpoint(payload: UserRegisterRequest):
    """
    Registers a new user account with salted password hashing and returns credentials.
    """
    try:
        user = db.register_user(
            username=payload.username,
            password=payload.password,
            email=payload.email,
            full_name=payload.full_name
        )
        return {
            "status": "success",
            "message": "User registered successfully.",
            "token": f"user-token-{user['id']}-{user['username']}",
            "user": user
        }
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )
    except Exception as e:
        logger.error(f"Error registering user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user."
        )

@app.post("/auth/login", tags=["Authentication & Access Control"], summary="User login & authentication", response_model=AuthResponse)
def login_user_endpoint(payload: UserLoginRequest):
    """
    Authenticates username and password against cryptographic salted hash.
    """
    user = db.authenticate_user(username=payload.username, password=payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return {
        "status": "success",
        "message": "Authentication successful.",
        "token": f"user-token-{user['id']}-{user['username']}",
        "user": user
    }

@app.get("/auth/me", tags=["Authentication & Access Control"], summary="Get current user profile")
def get_current_user_profile(user_id: int = Query(..., description="ID of the user")):
    """
    Retrieves the user profile without sensitive credentials.
    """
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


@app.get("/meetings", tags=["Meeting Knowledge Repository"], summary="List historical meetings")
def list_meetings(
    search: Optional[str] = Query(None, description="Search keyword across titles, transcripts, participants, or IDs"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Max number of meetings to return"),
    offset: Optional[int] = Query(0, ge=0, description="Offset for pagination"),
    user_id: Optional[int] = Query(None, description="Scope meetings to authenticated user ID")
) -> Dict[str, Any]:
    """
    Retrieves a list of meeting metadata records stored in the knowledge repository.
    Supports optional search filtering, pagination (limit and offset), and user data isolation.
    """
    try:
        if search and search.strip():
            logger.info(f"Searching meetings with query: '{search.strip()}' (user_id={user_id})")
            results = db.search_meetings(query=search.strip(), limit=limit, offset=offset, user_id=user_id)
        else:
            logger.info(f"Listing meetings (limit={limit}, offset={offset}, user_id={user_id})")
            results = db.list_all_meetings(limit=limit, offset=offset, user_id=user_id)

        return {
            "status": "success",
            "success": True,
            "total": len(results),
            "meetings": results
        }
    except Exception as e:
        logger.error(f"Error listing meetings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database retrieval failure: {str(e)}"
        )


def execute_search(
    query: Optional[str] = None,
    semantic: bool = False,
    participant: Optional[str] = None,
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    title: Optional[str] = None,
    format: Optional[str] = None,
    language: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = 0
) -> Dict[str, Any]:
    """
    Unified search executor supporting both relational keyword and semantic retrieval.
    Gracefully handles errors and falls back to relational retrieval if vector/semantic fails.
    """
    # Validate date format if provided (allows single date, ISO timestamps, and range formats like YYYY-MM-DD to YYYY-MM-DD)
    if date and not all(c in "0123456789-/:T to" for c in date.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date filter format. Expected format like YYYY-MM-DD or date range."
        )

    clean_q = query.strip() if query and query.strip() else None

    if semantic and clean_q:
        try:
            logger.info(f"Executing semantic retrieval for: '{clean_q}'")
            results = ai_search_engine.semantic_search(clean_q, limit=limit or 10)
        except Exception as sem_err:
            logger.warning(f"Semantic search failed: {sem_err}. Falling back to database keyword search.")
            results = db.search_meetings(
                query=clean_q,
                participant=participant,
                date=date,
                start_date=start_date,
                end_date=end_date,
                title=title,
                format=format,
                language=language,
                limit=limit,
                offset=offset or 0
            )
    else:
        results = db.search_meetings(
            query=clean_q,
            participant=participant,
            date=date,
            start_date=start_date,
            end_date=end_date,
            title=title,
            format=format,
            language=language,
            limit=limit,
            offset=offset or 0
        )

    return {
        "status": "success",
        "success": True,
        "query": clean_q or "",
        "semantic": bool(semantic),
        "filters": {
            "participant": participant,
            "date": date,
            "start_date": start_date,
            "end_date": end_date,
            "title": title,
            "format": format,
            "language": language
        },
        "total_matches": len(results),
        "results": results
    }


@app.get("/meetings/search", tags=["Meeting Knowledge Repository"], summary="Search historical meetings (Keyword & Filters)")
def search_meetings(
    q: Optional[str] = Query(None, description="Search keyword across title, metadata, transcript, summary, key points, decisions, tasks, participants, deadlines"),
    participant: Optional[str] = Query(None, description="Optional filter by participant name"),
    date: Optional[str] = Query(None, description="Optional filter by creation date (YYYY-MM-DD, range, or partial ISO date)"),
    start_date: Optional[str] = Query(None, description="Optional filter meetings on or after YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Optional filter meetings on or before YYYY-MM-DD"),
    title: Optional[str] = Query(None, description="Optional filter by meeting title"),
    format: Optional[str] = Query(None, description="Optional filter by audio format (.MP3, .WAV)"),
    language: Optional[str] = Query(None, description="Optional filter by language code (EN, FR)"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Max number of results to return"),
    offset: Optional[int] = Query(0, ge=0, description="Offset for pagination")
) -> Dict[str, Any]:
    """
    Case-insensitive search across historical meetings supporting:
    - Meeting title & metadata (format, language, filename)
    - Full transcript, LLM summary, key points, decisions, tasks, participants, deadlines
    - Dedicated filters for participant, date, start_date, end_date, title, format, language
    """
    try:
        return execute_search(
            query=q,
            semantic=False,
            participant=participant,
            date=date,
            start_date=start_date,
            end_date=end_date,
            title=title,
            format=format,
            language=language,
            limit=limit,
            offset=offset or 0
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing search query '{q}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database search failure: {str(e)}"
        )


@app.get("/search", tags=["Search"], summary="Search historical meetings with optional semantic retrieval (GET)")
def search_get(
    q: Optional[str] = Query(None, description="Search keyword or natural language query"),
    query: Optional[str] = Query(None, description="Alternative query parameter"),
    semantic: bool = Query(False, description="Enable semantic/vector retrieval"),
    participant: Optional[str] = Query(None, description="Optional filter by participant name"),
    date: Optional[str] = Query(None, description="Optional filter by creation date (YYYY-MM-DD or range)"),
    start_date: Optional[str] = Query(None, description="Optional filter meetings on or after YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Optional filter meetings on or before YYYY-MM-DD"),
    title: Optional[str] = Query(None, description="Optional filter by meeting title"),
    format: Optional[str] = Query(None, description="Optional filter by audio format"),
    language: Optional[str] = Query(None, description="Optional filter by language code"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Max results to return"),
    offset: Optional[int] = Query(0, ge=0, description="Offset for pagination")
) -> Dict[str, Any]:
    """
    GET /search:
    Connects search with optional semantic/vector retrieval and relational filtering.
    """
    search_q = q if q is not None else query
    try:
        return execute_search(
            query=search_q,
            semantic=semantic,
            participant=participant,
            date=date,
            start_date=start_date,
            end_date=end_date,
            title=title,
            format=format,
            language=language,
            limit=limit,
            offset=offset or 0
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in GET /search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search execution failure: {str(e)}"
        )


@app.post("/search", tags=["Search"], summary="Search historical meetings with optional semantic retrieval (POST)")
def search_post(payload: SearchPayload) -> Dict[str, Any]:
    """
    POST /search:
    Executes search over JSON body supporting semantic search, custom filters, and pagination.
    """
    search_q = payload.query if payload.query is not None else payload.q
    participant = payload.participant
    date = payload.date
    start_date = payload.start_date
    end_date = payload.end_date
    title = payload.title
    format_filter = payload.format
    language = payload.language

    if payload.filters:
        participant = participant or payload.filters.participant
        date = date or payload.filters.date
        start_date = start_date or payload.filters.start_date
        end_date = end_date or payload.filters.end_date
        title = title or payload.filters.title
        format_filter = format_filter or payload.filters.format
        language = language or payload.filters.language

    try:
        return execute_search(
            query=search_q,
            semantic=bool(payload.semantic),
            participant=participant,
            date=date,
            start_date=start_date,
            end_date=end_date,
            title=title,
            format=format_filter,
            language=language,
            limit=payload.limit,
            offset=payload.offset or 0
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in POST /search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search execution failure: {str(e)}"
        )


@app.post("/ask", tags=["RAG & Question Answering"], summary="Ask grounded questions about historical meetings (POST)")
def ask_endpoint(
    payload: AskRequest,
    auth_token: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Authenticated RAG endpoint:
    User question -> Existing authentication -> Semantic search / retrieval
    -> Relevant meeting context -> Existing LLM/RAG service -> Grounded answer with source meeting IDs.
    """
    raw_q = payload.question or payload.query or payload.q or ""
    if not raw_q or not raw_q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty or whitespace."
        )

    clean_q = raw_q.strip()
    if len(clean_q) > 4000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question exceeds maximum permitted length of 4000 characters."
        )

    try:
        return ai_search_engine.answer_question(clean_q)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /ask: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG processing error: {str(e)}"
        )


# ---------------------------------------------------------------------------
# AI / Contextual Search Endpoints
# ---------------------------------------------------------------------------

@app.post("/meetings/ai-search", tags=["AI Contextual Search"], summary="Ask natural language questions about historical meetings (POST)")
def ai_search_post(payload: AISearchRequest) -> Dict[str, Any]:
    """
    Answers natural language questions about historical meetings using retrieved context and LLM.
    Strictly grounded with source meeting IDs.
    """
    if not payload.question or not payload.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty or whitespace."
        )
    try:
        return ai_search_engine.answer_question(payload.question.strip())
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as e:
        logger.error(f"Error in ai_search_post: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI Search processing error: {str(e)}"
        )


@app.get("/meetings/ai-search", tags=["AI Contextual Search"], summary="Ask natural language questions about historical meetings (GET)")
def ai_search_get(
    q: str = Query(..., description="Natural language question about historical meetings")
) -> Dict[str, Any]:
    """
    Answers natural language questions via GET query parameter.
    """
    if not q or not q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question query parameter 'q' cannot be empty or whitespace."
        )
    try:
        return ai_search_engine.answer_question(q.strip())
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as e:
        logger.error(f"Error in ai_search_get: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI Search processing error: {str(e)}"
        )


@app.get("/meetings/insights", tags=["Historical Insights"], summary="Retrieve aggregate historical meeting insights & metrics")
def get_historical_insights_endpoint(
    participant: Optional[str] = Query(None, description="Filter by participant name"),
    start_date: Optional[str] = Query(None, description="Filter meetings created on or after YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Filter meetings created on or before YYYY-MM-DD"),
    status: Optional[str] = Query(None, description="Filter action items by status (Pending, In Progress, Completed)"),
    title: Optional[str] = Query(None, description="Filter by meeting title keywords"),
    limit: int = Query(50, ge=1, le=200, description="Max meeting records to evaluate")
) -> Dict[str, Any]:
    """
    Computes cross-meeting historical insights and aggregates:
    - Overview KPIs (meetings, action items, pending/completed tasks, participants, decisions, deadlines)
    - Filterable action items with priorities and deadlines
    - Cross-meeting strategic decisions ledger
    - Participant workload directory
    - Deadlines & milestones agenda
    - Project/topic evolution history
    """
    try:
        insights = db.get_historical_insights(
            participant=participant,
            start_date=start_date,
            end_date=end_date,
            status=status,
            title=title,
            limit=limit
        )
        return {
            "success": True,
            "status": "success",
            "insights": insights
        }
    except Exception as e:
        logger.error(f"Error computing historical insights: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error computing historical insights: {str(e)}"
        )


@app.get("/meetings/{meeting_id}", tags=["Meeting Knowledge Repository"], summary="Retrieve complete meeting intelligence")
def get_meeting(
    meeting_id: str = Path(..., description="Unique meeting ID (e.g. MEET-E08D338E)")
) -> Dict[str, Any]:
    """
    Retrieves the complete structured meeting record for a given `meeting_id`.
    Returns:
    - Metadata (ID, title, audio file, duration, format, language, word count, validation status)
    - Whisper Transcript
    - LLM-generated Summary
    - Key Points
    - Decisions
    - Action Items (task, assigned participant, deadline, priority, status)
    - Participants (deduplicated)
    - Deadlines
    - Priorities
    - Validation Logs
    """
    # Validation for invalid meeting ID
    if not meeting_id or not meeting_id.strip():
        logger.warning("get_meeting called with empty meeting_id")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid meeting ID: meeting_id cannot be empty or whitespace."
        )

    clean_id = meeting_id.strip()

    try:
        meeting = db.get_meeting(clean_id)
        if not meeting:
            logger.warning(f"Meeting not found: '{clean_id}'")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Meeting '{clean_id}' was not found in the knowledge repository."
            )

        return {
            "status": "success",
            **meeting
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database failure retrieving meeting '{clean_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection or retrieval failure: {str(e)}"
        )


@app.get("/meetings/{meeting_id}/transcript", tags=["Meeting Knowledge Repository"], summary="Retrieve meeting transcript")
def get_meeting_transcript(
    meeting_id: str = Path(..., description="Unique meeting ID")
) -> Dict[str, Any]:
    """
    Retrieves only the Whisper-generated transcript and basic metadata for a meeting.
    """
    if not meeting_id or not meeting_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid meeting ID: meeting_id cannot be empty or whitespace."
        )

    clean_id = meeting_id.strip()
    try:
        meeting = db.get_meeting(clean_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Meeting '{clean_id}' was not found."
            )

        return {
            "status": "success",
            "meeting_id": clean_id,
            "title": meeting.get("title", ""),
            "word_count": meeting.get("word_count", 0),
            "transcript": meeting.get("transcript", "")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching transcript for '{clean_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database retrieval failure: {str(e)}"
        )


@app.get("/meetings/{meeting_id}/action-items", tags=["Meeting Knowledge Repository"], summary="Retrieve action items for a meeting")
def get_meeting_action_items(
    meeting_id: str = Path(..., description="Unique meeting ID")
) -> Dict[str, Any]:
    """
    Retrieves the list of extracted action items linked to a meeting.
    """
    if not meeting_id or not meeting_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid meeting ID: meeting_id cannot be empty or whitespace."
        )

    clean_id = meeting_id.strip()
    try:
        meeting = db.get_meeting(clean_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Meeting '{clean_id}' was not found."
            )

        action_items = meeting.get("action_items", [])
        return {
            "status": "success",
            "meeting_id": clean_id,
            "count": len(action_items),
            "action_items": action_items
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching action items for '{clean_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database retrieval failure: {str(e)}"
        )


@app.get("/stats", tags=["Dashboard & Metrics"], summary="Get aggregate repository statistics")
def get_stats() -> Dict[str, Any]:
    """
    Returns aggregate repository metrics: total meetings, total actions, pending actions, completed actions.
    """
    try:
        stats = db.get_dashboard_stats()
        return {
            "status": "success",
            "success": True,
            "total_meetings": stats.get("total_meetings", 0),
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error retrieving repository stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate repository stats: {str(e)}"
        )
# ---------------------------------------------------------------------------
# Reports & Export Endpoints (Milestone 4 - Task 6)
# ---------------------------------------------------------------------------

@app.get("/meetings/{meeting_id}/export/pdf", tags=["Reports & Export"], summary="Export comprehensive meeting PDF report")
def export_meeting_pdf(
    meeting_id: str = Path(..., description="Unique meeting ID")
):
    """
    Generates and returns an executive PDF intelligence dossier for the meeting.
    Includes metadata, executive summary, key discussion points, decisions ledger, action items table, participants, and deadlines.
    """
    if not meeting_id or not meeting_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid meeting ID: meeting_id cannot be empty or whitespace."
        )

    clean_id = meeting_id.strip()
    try:
        meeting = db.get_meeting(clean_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Meeting '{clean_id}' was not found in the knowledge repository."
            )

        pdf_bytes = generate_meeting_pdf(meeting)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{clean_id}_intelligence_report.pdf"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating PDF report for '{clean_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failure: {str(e)}"
        )


@app.get("/meetings/{meeting_id}/export/csv", tags=["Reports & Export"], summary="Export meeting intelligence CSV report")
def export_meeting_csv(
    meeting_id: str = Path(..., description="Unique meeting ID")
):
    """
    Generates and returns a structured multi-section CSV report containing meeting metadata, summary, key points, decisions, action items, participants, and deadlines.
    """
    if not meeting_id or not meeting_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid meeting ID: meeting_id cannot be empty or whitespace."
        )

    clean_id = meeting_id.strip()
    try:
        meeting = db.get_meeting(clean_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Meeting '{clean_id}' was not found in the knowledge repository."
            )

        csv_data = generate_meeting_csv(meeting)
        return Response(
            content=csv_data,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{clean_id}_report.csv"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating CSV report for '{clean_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CSV generation failure: {str(e)}"
        )


@app.get("/meetings/{meeting_id}/export/action-items", tags=["Reports & Export"], summary="Export action items CSV")
def export_action_items_csv(
    meeting_id: str = Path(..., description="Unique meeting ID")
):
    """
    Generates and returns a dedicated action items CSV table formatted for Jira/Excel/Notion import.
    """
    if not meeting_id or not meeting_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid meeting ID: meeting_id cannot be empty or whitespace."
        )

    clean_id = meeting_id.strip()
    try:
        meeting = db.get_meeting(clean_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Meeting '{clean_id}' was not found in the knowledge repository."
            )

        csv_data = generate_action_items_csv(meeting)
        return Response(
            content=csv_data,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{clean_id}_action_items.csv"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating action items CSV for '{clean_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Action items CSV generation failure: {str(e)}"
        )


# ---------------------------------------------------------------------------
# Zoom Integration Endpoints (Milestone 4 - Task 4)
# ---------------------------------------------------------------------------

@app.post("/integrations/zoom/webhook", tags=["Integrations - Zoom"], summary="Zoom Webhook Receiver")
async def zoom_webhook_endpoint(
    request: Request,
    x_zm_signature: Optional[str] = Header(None, alias="x-zm-signature"),
    x_zm_request_timestamp: Optional[str] = Header(None, alias="x-zm-request-timestamp")
):
    """
    Receives and processes Zoom Cloud Recording webhooks:
    - Automatically handles Zoom endpoint URL validation challenges (endpoint.url_validation).
    - Verifies HMAC SHA-256 signatures if secret is configured.
    - Triggers end-to-end ingestion on 'recording.completed'.
    """
    try:
        body_bytes = await request.body()
        payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
    except Exception as parse_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid JSON payload: {parse_err}")

    # 1. Zoom URL Validation Challenge
    if payload.get("event") == "endpoint.url_validation":
        plain_token = payload.get("payload", {}).get("plainToken", "")
        res = zoom_service.handle_url_validation(plain_token)
        return JSONResponse(status_code=200, content=res)

    # 2. Signature verification (if signature header provided)
    if x_zm_signature and x_zm_request_timestamp:
        valid_sig = zoom_service.verify_webhook_signature(body_bytes, x_zm_signature, x_zm_request_timestamp)
        if not valid_sig:
            logger.warning("Zoom webhook signature verification failed.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Zoom webhook signature.")

    # 3. Process recording.completed
    if payload.get("event") == "recording.completed":
        success, res_data, msg = zoom_service.process_recording_completed_event(payload)
        return {
            "status": "success" if success else "handled",
            "success": success,
            "message": msg,
            "data": res_data
        }

    return {"status": "ignored", "event": payload.get("event"), "message": "Event received but no action required."}


@app.post("/integrations/zoom/sync", tags=["Integrations - Zoom"], summary="Trigger manual Zoom meeting sync")
def zoom_sync_endpoint(payload: ZoomSyncRequest):
    """
    Manually triggers ingestion for a Zoom meeting ID with optional recording path or built-in test audio.
    """
    clean_id = payload.meeting_id.strip()
    if not clean_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="meeting_id is required.")

    if zoom_service.is_duplicate(clean_id, user_id=payload.user_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Zoom meeting '{clean_id}' has already been synced."
        )

    event_payload = {
        "event": "recording.completed",
        "payload": {
            "object": {
                "id": clean_id,
                "uuid": f"manual-zoom-{clean_id}",
                "topic": payload.topic or f"Zoom Sync {clean_id}",
                "duration": 15
            }
        }
    }

    success, res_data, msg = zoom_service.process_recording_completed_event(
        event_payload=event_payload,
        user_id=payload.user_id or 1,
        mock_audio_path=payload.audio_path
    )

    if res_data.get("duplicate"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Zoom meeting '{clean_id}' has already been synced."
        )

    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)

    return {
        "status": "success",
        "message": msg,
        "meeting": res_data
    }


@app.get("/integrations/zoom/status", tags=["Integrations - Zoom"], summary="Get Zoom integration status and sync history")
def zoom_status_endpoint(user_id: Optional[int] = Query(None, description="Scope sync logs to user")):
    """
    Returns integration readiness, webhook endpoints, and recent sync audit logs.
    """
    return zoom_service.get_status(user_id=user_id)


# ---------------------------------------------------------------------------
# Google Meet Integration Endpoints (Milestone 4 - Task 5)
# ---------------------------------------------------------------------------

@app.post("/integrations/google-meet/sync", tags=["Integrations - Google Meet"], summary="Trigger Google Meet recording sync")
def google_meet_sync_endpoint(payload: GoogleMeetSyncRequest):
    """
    Ingests a Google Meet recording by Meet URL or meeting code:
    - Normalizes URL or code into canonical format (abc-defg-hij).
    - Checks for duplicate ingestions to avoid redundant processing.
    - Runs full Whisper pipeline and persists into repository.
    """
    clean_code = meet_service.parse_meet_code(payload.meet_url_or_code)
    if not clean_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google Meet URL or code format. Expected format like 'abc-defg-hij' or 'meet.google.com/abc-defg-hij'."
        )

    if meet_service.is_duplicate(clean_code, user_id=payload.user_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Google Meet '{clean_code}' has already been synced."
        )

    success, res_data, msg = meet_service.process_meet_recording(
        meet_code_or_url=clean_code,
        topic=payload.topic,
        audio_file_path=payload.audio_path,
        user_id=payload.user_id or 1
    )

    if res_data.get("duplicate"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Google Meet '{clean_code}' has already been synced."
        )

    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)

    return {
        "status": "success",
        "message": msg,
        "meeting": res_data
    }


@app.get("/integrations/google-meet/status", tags=["Integrations - Google Meet"], summary="Get Google Meet integration status")
def google_meet_status_endpoint(user_id: Optional[int] = Query(None, description="Scope sync logs to user")):
    """
    Returns integration readiness and recent Google Meet sync audit history.
    """
    return meet_service.get_status(user_id=user_id)


if __name__ == "__main__":
    import uvicorn
    print("Starting WhisperSense AI Knowledge Repository API Server...")
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)

