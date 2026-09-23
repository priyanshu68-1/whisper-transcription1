import os
import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Path, status, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import DatabaseManager
from ai_search_service import AISearchEngine
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Request Models
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
    title="TruthShield AI • Meeting Knowledge Repository API",
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

# ---------------------------------------------------------------------------
# Authentication Security Dependency
# ---------------------------------------------------------------------------
API_AUTH_TOKEN = os.environ.get("API_AUTH_TOKEN", "truthshield-secret-token-2026")
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

    expected_token = os.environ.get("API_AUTH_TOKEN", "truthshield-secret-token-2026")
    if provided_token != expected_token:
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
            "service": "TruthShield AI Meeting Knowledge Repository API",
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


@app.get("/meetings", tags=["Meeting Knowledge Repository"], summary="List historical meetings")
def list_meetings(
    search: Optional[str] = Query(None, description="Search keyword across titles, transcripts, participants, or IDs"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Max number of meetings to return"),
    offset: Optional[int] = Query(0, ge=0, description="Offset for pagination")
) -> Dict[str, Any]:
    """
    Retrieves a list of meeting metadata records stored in the knowledge repository.
    Supports optional search filtering, pagination (limit and offset).
    """
    try:
        if search and search.strip():
            logger.info(f"Searching meetings with query: '{search.strip()}'")
            results = db.search_meetings(query=search.strip(), limit=limit, offset=offset)
        else:
            logger.info(f"Listing all meetings (limit={limit}, offset={offset})")
            results = db.list_all_meetings(limit=limit, offset=offset)

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


if __name__ == "__main__":
    import uvicorn
    print("Starting TruthShield AI Knowledge Repository API Server...")
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
