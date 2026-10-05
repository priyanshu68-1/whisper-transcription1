import os
import sqlite3
import json
import uuid
import logging
import hashlib
import secrets
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

DB_FILE = os.path.join(os.path.dirname(__file__), "whisper_meetings.db")

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    Computes a cryptographic SHA-256 salted hash for the password.
    Returns (hex_hash, hex_salt).
    """
    if not salt:
        salt = secrets.token_hex(16)
    pwd_bytes = password.encode('utf-8')
    salt_bytes = salt.encode('utf-8')
    pwd_hash = hashlib.sha256(salt_bytes + pwd_bytes).hexdigest()
    return pwd_hash, salt

def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """
    Constant-time password verification against stored salted hash.
    """
    if not password or not salt or not expected_hash:
        return False
    pwd_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(pwd_hash, expected_hash)


# ---------------------------------------------------------------------------
# Structured Logging Setup
# ---------------------------------------------------------------------------
logger = logging.getLogger("whisper_meetings.database")
logger.propagate = False
if not logger.handlers:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
    _handler.setFormatter(_formatter)
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)


class ClosingConnection:
    """
    Context manager wrapper around sqlite3.Connection ensuring both 
    transactional commit/rollback and connection closure upon exiting.
    """
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def __enter__(self) -> sqlite3.Connection:
        self._conn.__enter__()
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self._conn.__exit__(exc_type, exc_val, exc_tb)
        finally:
            self._conn.close()


def _safe_json_loads(data: Any, default: Any = None) -> Any:
    """
    Safely parses JSON strings into Python structures.
    Falls back gracefully if data is null, malformed, or corrupted.
    """
    if default is None:
        default = []
    if data is None:
        return default
    if isinstance(data, (list, dict)):
        return data
    if not isinstance(data, str) or not data.strip():
        return default
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError, ValueError) as err:
        logger.warning(f"Malformed JSON encountered in database: {data!r} - {err}. Using fallback: {default}")
        return default


class DatabaseManager:
    """
    Meeting Knowledge Repository & Relational Persistence
    Provides SQLite relational storage and retrieval for transcripts, summaries, 
    action items, participants, and validation logs with strict isolation.
    """
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> ClosingConnection:
        """
        Creates and returns a SQLite connection wrapper with foreign keys enabled,
        Row factory configured, and auto-closing on context manager exit.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            return ClosingConnection(conn)
        except sqlite3.Error as e:
            logger.error(f"Database connection error to '{self.db_path}': {e}", exc_info=True)
            raise

    def init_db(self):
        """
        Creates required relational database tables if they do not exist.
        Enforces foreign keys, unique constraints, and multi-user data isolation.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 0. Users Core Table (Task 1 & Task 7: Multi-User Authentication & Access Control)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        email TEXT,
                        full_name TEXT,
                        created_at TEXT NOT NULL
                    )
                """)

                # 1. Meetings Core Table (with user_id for multi-user isolation)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS meetings (
                        meeting_id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        audio_filename TEXT,
                        file_size_mb REAL,
                        duration_seconds REAL,
                        format TEXT,
                        language TEXT,
                        transcript TEXT NOT NULL,
                        word_count INTEGER,
                        validation_status TEXT,
                        created_at TEXT NOT NULL,
                        user_id INTEGER DEFAULT 1,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                    )
                """)

                # Check if user_id column exists on meetings for migration
                cursor.execute("PRAGMA table_info(meetings)")
                cols = [r["name"] for r in cursor.fetchall()]
                if "user_id" not in cols:
                    cursor.execute("ALTER TABLE meetings ADD COLUMN user_id INTEGER DEFAULT NULL")

                # Ensure default demo user exists (demo / demo123)
                cursor.execute("SELECT COUNT(*) as count FROM users")
                if cursor.fetchone()["count"] == 0:
                    demo_salt = secrets.token_hex(16)
                    demo_hash, _ = hash_password("demo123", demo_salt)
                    now_str = datetime.now().isoformat()
                    cursor.execute("""
                        INSERT INTO users (id, username, password_hash, salt, email, full_name, created_at)
                        VALUES (1, 'demo', ?, ?, 'demo@whispersense.ai', 'Demo Account', ?)
                    """, (demo_hash, demo_salt, now_str))

                # Ensure any pre-existing meetings have a valid user_id
                cursor.execute("UPDATE meetings SET user_id = 1 WHERE user_id IS NULL")

                # 2. Summaries & Intelligence Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS summaries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        meeting_id TEXT NOT NULL,
                        summary_text TEXT NOT NULL,
                        key_points TEXT,
                        decisions TEXT,
                        deadlines TEXT,
                        priorities TEXT,
                        FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id) ON DELETE CASCADE
                    )
                """)

                # 3. Action Items Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS action_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        meeting_id TEXT NOT NULL,
                        task TEXT NOT NULL,
                        assignee TEXT NOT NULL,
                        priority TEXT DEFAULT 'Medium',
                        deadline TEXT DEFAULT 'Not specified',
                        status TEXT DEFAULT 'Pending',
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id) ON DELETE CASCADE
                    )
                """)

                # 4. Participants Table (Unique per meeting)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS participants (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        meeting_id TEXT NOT NULL,
                        participant_name TEXT NOT NULL,
                        FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id) ON DELETE CASCADE,
                        UNIQUE(meeting_id, participant_name)
                    )
                """)

                # 5. Validation Logs Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS validation_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        meeting_id TEXT NOT NULL,
                        is_valid INTEGER NOT NULL,
                        file_check TEXT,
                        transcript_check TEXT,
                        schema_check TEXT,
                        validated_at TEXT NOT NULL,
                        FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id) ON DELETE CASCADE
                    )
                """)

                # 6. Integration Sync Logs Table (Milestone 4 - Tasks 4 & 5)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS integration_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source TEXT NOT NULL,
                        external_meeting_id TEXT NOT NULL,
                        internal_meeting_id TEXT,
                        title TEXT,
                        status TEXT NOT NULL,
                        details TEXT,
                        created_at TEXT NOT NULL,
                        user_id INTEGER DEFAULT 1,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                    )
                """)

                # Performance & Retrieval Indexes (Milestone 4 - Task 9)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_meetings_user_id ON meetings(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_meetings_created_at ON meetings(created_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_action_items_meeting_id ON action_items(meeting_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_summaries_meeting_id ON summaries(meeting_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_participants_meeting_id ON participants(meeting_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_integration_logs_lookup ON integration_logs(source, external_meeting_id, status)")

                conn.commit()
                logger.debug("Database initialized successfully.")
        except sqlite3.Error as e:
            logger.error(f"Error initializing database tables: {e}", exc_info=True)
            raise

    # -------------------------------------------------------------------------
    # Multi-User Authentication & Security Methods (Milestone 4 - Tasks 1 & 7)
    # -------------------------------------------------------------------------
    def register_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Registers a new user with unique username, salted SHA-256 password hash,
        and returns sanitized user profile without sensitive credentials.
        """
        if not username or not isinstance(username, str) or len(username.strip()) < 3:
            raise ValueError("Username must be at least 3 characters long.")
        if not password or not isinstance(password, str) or len(password) < 4:
            raise ValueError("Password must be at least 4 characters long.")

        clean_user = username.strip().lower()
        clean_email = email.strip() if email else None
        clean_name = full_name.strip() if full_name else clean_user.title()
        now = datetime.now().isoformat()
        pwd_hash, salt = hash_password(password)

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE username = ?", (clean_user,))
                if cursor.fetchone():
                    raise ValueError(f"Username '{clean_user}' is already registered.")

                cursor.execute("""
                    INSERT INTO users (username, password_hash, salt, email, full_name, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (clean_user, pwd_hash, salt, clean_email, clean_name, now))
                conn.commit()
                new_id = cursor.lastrowid
                logger.info(f"User '{clean_user}' registered successfully (id={new_id}).")
                return {
                    "id": new_id,
                    "username": clean_user,
                    "email": clean_email,
                    "full_name": clean_name,
                    "created_at": now
                }
        except sqlite3.IntegrityError:
            raise ValueError(f"Username '{clean_user}' is already registered.")

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticates a user against stored salted hash.
        Returns user metadata dictionary if valid, or None if authentication fails.
        """
        if not username or not password:
            return None

        clean_user = username.strip().lower()
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (clean_user,))
                user_row = cursor.fetchone()
                if not user_row:
                    return None

                user_dict = dict(user_row)
                if verify_password(password, user_dict["salt"], user_dict["password_hash"]):
                    return {
                        "id": user_dict["id"],
                        "username": user_dict["username"],
                        "email": user_dict.get("email"),
                        "full_name": user_dict.get("full_name") or user_dict["username"].title(),
                        "created_at": user_dict.get("created_at")
                    }
                return None
        except sqlite3.Error as e:
            logger.error(f"Error authenticating user '{clean_user}': {e}", exc_info=True)
            return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, username, email, full_name, created_at FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error:
            return None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, username, email, full_name, created_at FROM users WHERE username = ?", (username.strip().lower(),))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error:
            return None

    def save_meeting(
        self,
        meeting_id: str,
        title: str,
        audio_filename: str,
        file_size_mb: float,
        duration_seconds: float,
        format_ext: str,
        language: str,
        transcript: str,
        intelligence: Dict[str, Any],
        participant_data: Dict[str, Any],
        validation_info: Dict[str, Any],
        user_id: Optional[int] = 1
    ) -> str:
        """
        Persists a complete processed meeting transactionally into SQLite with user ownership.
        Guarantees deduplicated participants, isolated links, and safe fallback handling.
        """
        if not meeting_id or not isinstance(meeting_id, str) or not meeting_id.strip():
            raise ValueError(f"Invalid meeting_id: {meeting_id!r}. Must be a non-empty string.")

        clean_meeting_id = meeting_id.strip()
        now = datetime.now().isoformat()
        word_count = len(transcript.split()) if transcript else 0

        # Safe defaults for intelligence dict
        intelligence = intelligence or {}
        participant_data = participant_data or {}
        validation_info = validation_info or {}

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 1. Insert or Replace Meeting record
                cursor.execute("""
                    INSERT OR REPLACE INTO meetings (
                        meeting_id, title, audio_filename, file_size_mb, duration_seconds,
                        format, language, transcript, word_count, validation_status, created_at, user_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    clean_meeting_id,
                    title or "Untitled Meeting",
                    audio_filename or "unknown_audio",
                    float(file_size_mb or 0.0),
                    float(duration_seconds or 0.0),
                    format_ext or "UNKNOWN",
                    language or "EN",
                    transcript or "",
                    word_count,
                    "VALIDATED" if validation_info.get("is_valid", True) else "FAILED",
                    now,
                    int(user_id or 1)
                ))

                # 2. Delete old related records if updating meeting
                cursor.execute("DELETE FROM summaries WHERE meeting_id = ?", (clean_meeting_id,))
                cursor.execute("DELETE FROM action_items WHERE meeting_id = ?", (clean_meeting_id,))
                cursor.execute("DELETE FROM participants WHERE meeting_id = ?", (clean_meeting_id,))
                cursor.execute("DELETE FROM validation_logs WHERE meeting_id = ?", (clean_meeting_id,))

                # 3. Insert Summary record
                summary_text = intelligence.get("summary") or "No summary generated."
                key_points_json = json.dumps(intelligence.get("key_points") or [])
                decisions_json = json.dumps(intelligence.get("decisions") or [])
                deadlines_json = json.dumps(intelligence.get("deadlines") or [])
                priorities_json = json.dumps(intelligence.get("priorities") or [])

                cursor.execute("""
                    INSERT INTO summaries (
                        meeting_id, summary_text, key_points, decisions, deadlines, priorities
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (clean_meeting_id, summary_text, key_points_json, decisions_json, deadlines_json, priorities_json))

                # 4. Insert Action Items from Intelligence & Mapping
                actions = list(intelligence.get("action_items") or [])
                if not actions and "responsibilities" in participant_data:
                    for r in participant_data.get("responsibilities", []):
                        assignees_str = ", ".join(r.get("assignees", ["Unassigned"]))
                        actions.append({
                            "task": r.get("task", ""),
                            "assignee": assignees_str,
                            "priority": r.get("priority", "Medium"),
                            "deadline": r.get("deadline", "Not specified"),
                            "status": "Pending"
                        })

                for act in actions:
                    task = (act.get("task") or "").strip()
                    if not task:
                        continue
                    assignee = act.get("assignee") or act.get("assigned_participant") or "Unassigned"
                    if isinstance(assignee, list):
                        assignee = ", ".join([str(a) for a in assignee if str(a).strip()]) or "Unassigned"
                    priority = act.get("priority") or "Medium"
                    deadline = act.get("deadline") or "Not specified"
                    status = act.get("status") or "Pending"

                    cursor.execute("""
                        INSERT INTO action_items (
                            meeting_id, task, assignee, priority, deadline, status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (clean_meeting_id, task, assignee, priority, deadline, status, now))

                # 5. Insert Participants (Normalize & Deduplicate)
                unique_parts = participant_data.get("unique_participants") or intelligence.get("participants") or []
                clean_participants = []
                seen_participants = set()
                for p in unique_parts:
                    if not p:
                        continue
                    p_name = str(p).strip()
                    p_key = p_name.lower()
                    if p_name and p_key not in seen_participants:
                        seen_participants.add(p_key)
                        clean_participants.append(p_name)

                if not clean_participants:
                    clean_participants = ["Narrator / Speaker"]

                for p_name in clean_participants:
                    cursor.execute("""
                        INSERT OR IGNORE INTO participants (meeting_id, participant_name) VALUES (?, ?)
                    """, (clean_meeting_id, p_name))

                # 6. Insert Validation Log
                cursor.execute("""
                    INSERT INTO validation_logs (
                        meeting_id, is_valid, file_check, transcript_check, schema_check, validated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    clean_meeting_id,
                    1 if validation_info.get("is_valid", True) else 0,
                    validation_info.get("file_check", "PASSED"),
                    validation_info.get("transcript_check", "PASSED"),
                    validation_info.get("schema_check", "PASSED"),
                    now
                ))

                conn.commit()
                logger.info(f"Persisted meeting '{clean_meeting_id}' successfully into database.")
                return clean_meeting_id

        except sqlite3.Error as e:
            logger.error(f"Database error while saving meeting '{clean_meeting_id}': {e}", exc_info=True)
            raise

    def get_meeting(self, meeting_id: str, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves complete meeting record including summary, action items, participants, and validation logs.
        Strictly scopes by meeting_id (and optional user_id) to ensure complete data isolation.
        Handles missing/unknown values safely and guards against malformed records.
        """
        if meeting_id is None or not isinstance(meeting_id, str) or not meeting_id.strip():
            logger.warning(f"Invalid meeting_id provided for retrieval: {meeting_id!r}")
            return None

        clean_id = meeting_id.strip()

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if user_id is not None:
                    cursor.execute("SELECT * FROM meetings WHERE meeting_id = ? AND (user_id = ? OR user_id IS NULL)", (clean_id, user_id))
                else:
                    cursor.execute("SELECT * FROM meetings WHERE meeting_id = ?", (clean_id,))
                m_row = cursor.fetchone()
                if not m_row:
                    logger.info(f"Meeting with ID '{clean_id}' not found in database.")
                    return None

                meeting = dict(m_row)

                # Fetch summary & intelligence with safe parsing
                cursor.execute("SELECT * FROM summaries WHERE meeting_id = ?", (clean_id,))
                s_row = cursor.fetchone()
                if s_row:
                    s_dict = dict(s_row)
                    meeting["summary"] = s_dict.get("summary_text") or ""
                    meeting["key_points"] = _safe_json_loads(s_dict.get("key_points"), default=[])
                    meeting["decisions"] = _safe_json_loads(s_dict.get("decisions"), default=[])
                    meeting["deadlines"] = _safe_json_loads(s_dict.get("deadlines"), default=[])
                    meeting["priorities"] = _safe_json_loads(s_dict.get("priorities"), default=[])
                else:
                    meeting["summary"] = ""
                    meeting["key_points"] = []
                    meeting["decisions"] = []
                    meeting["deadlines"] = []
                    meeting["priorities"] = []

                # Fetch action items strictly for this meeting
                cursor.execute(
                    "SELECT * FROM action_items WHERE meeting_id = ? ORDER BY id ASC",
                    (clean_id,)
                )
                action_items_raw = [dict(r) for r in cursor.fetchall()]
                action_items = []
                for act in action_items_raw:
                    assignee_val = act.get("assignee") or "Unassigned"
                    action_items.append({
                        "id": act.get("id"),
                        "meeting_id": act.get("meeting_id") or clean_id,
                        "task": act.get("task") or "",
                        "assignee": assignee_val,
                        "assigned_participant": assignee_val,
                        "priority": act.get("priority") or "Medium",
                        "deadline": act.get("deadline") or "Not specified",
                        "status": act.get("status") or "Pending",
                        "created_at": act.get("created_at") or ""
                    })
                meeting["action_items"] = action_items

                # Fetch participants strictly for this meeting (deduplicated)
                cursor.execute(
                    "SELECT DISTINCT participant_name FROM participants WHERE meeting_id = ? ORDER BY id ASC",
                    (clean_id,)
                )
                meeting["participants"] = [r["participant_name"] for r in cursor.fetchall()]

                # Fetch validation logs strictly for this meeting
                cursor.execute("SELECT * FROM validation_logs WHERE meeting_id = ?", (clean_id,))
                v_row = cursor.fetchone()
                meeting["validation"] = dict(v_row) if v_row else {}

                return meeting

        except sqlite3.Error as db_err:
            logger.error(f"Database error while retrieving meeting '{clean_id}': {db_err}", exc_info=True)
            raise

    def get_meeting_transcript(self, meeting_id: str) -> Optional[str]:
        """
        Retrieves only the transcript text for a specific meeting.
        """
        meeting = self.get_meeting(meeting_id)
        return meeting.get("transcript") if meeting else None

    def get_meeting_action_items(self, meeting_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves only the action items for a specific meeting.
        """
        meeting = self.get_meeting(meeting_id)
        return meeting.get("action_items") if meeting else None

    def list_all_meetings(self, limit: Optional[int] = None, offset: Optional[int] = None, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Lists summary metadata of all stored meetings ordered by creation time descending.
        Supports optional pagination (limit and offset) and user-specific isolation.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                where_clause = ""
                params = []
                if user_id is not None:
                    where_clause = "WHERE (m.user_id = ? OR m.user_id IS NULL)"
                    params.append(user_id)

                query = f"""
                    SELECT m.*, 
                           (SELECT summary_text FROM summaries s WHERE s.meeting_id = m.meeting_id) as summary,
                           (SELECT COUNT(*) FROM action_items a WHERE a.meeting_id = m.meeting_id) as action_count
                    FROM meetings m
                    {where_clause}
                    ORDER BY created_at DESC
                """
                if limit is not None:
                    query += " LIMIT ?"
                    params.append(limit)
                    if offset is not None:
                        query += " OFFSET ?"
                        params.append(offset)

                cursor.execute(query, params)
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Database error while listing meetings: {e}", exc_info=True)
            raise

    def search_meetings(
        self,
        query: Optional[str] = None,
        participant: Optional[str] = None,
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        title: Optional[str] = None,
        format: Optional[str] = None,
        language: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Comprehensive case-insensitive historical meeting search and retrieval.
        Searches across:
        - Meeting title
        - Meeting metadata (format, language, audio_filename, meeting_id)
        - Full transcript
        - LLM summary
        - Key points
        - Decisions
        - Action items (task description, assignee, deadline, priority)
        - Participants
        - Deadlines

        Supports optional filters:
        - participant: filter by participant name
        - date: filter by creation date prefix (e.g. '2026-09-17' or '2026-09') or range ('start to end')
        - start_date: filter meetings created on or after YYYY-MM-DD
        - end_date: filter meetings created on or before YYYY-MM-DD
        - title: filter by title substring
        - format: filter by audio format (e.g. '.MP3', '.WAV')
        - language: filter by language code (e.g. 'EN', 'FR')

        Returns matching meeting records with metadata, summary, key points, decisions,
        participants, deadlines, action item count, and matched fields/snippets.
        """
        # Parse date range if supplied in date string (e.g. "2026-09-01 to 2026-09-30" or "2026-09-01:2026-09-30")
        effective_start = start_date.strip() if start_date and str(start_date).strip() else None
        effective_end = end_date.strip() if end_date and str(end_date).strip() else None

        if date and str(date).strip():
            raw_d = str(date).strip()
            if " to " in raw_d:
                parts = raw_d.split(" to ")
                effective_start = effective_start or parts[0].strip()
                effective_end = effective_end or parts[1].strip()
            elif ":" in raw_d and len(raw_d.split(":")) == 2 and not raw_d.startswith("http"):
                parts = raw_d.split(":")
                effective_start = effective_start or parts[0].strip()
                effective_end = effective_end or parts[1].strip()
            elif "/" in raw_d and len(raw_d.split("/")) == 2 and len(raw_d.split("/")[0]) >= 4:
                parts = raw_d.split("/")
                effective_start = effective_start or parts[0].strip()
                effective_end = effective_end or parts[1].strip()

        has_query = bool(query and str(query).strip())
        has_participant = bool(participant and str(participant).strip())
        has_date_prefix = bool(date and str(date).strip() and not effective_start and not effective_end)
        has_start_date = bool(effective_start)
        has_end_date = bool(effective_end)
        has_title = bool(title and str(title).strip())
        has_format = bool(format and str(format).strip())
        has_lang = bool(language and str(language).strip())

        # If no query and no filters, fall back to listing meetings
        if not (has_query or has_participant or has_date_prefix or has_start_date or has_end_date or has_title or has_format or has_lang):
            return self.list_all_meetings(limit=limit, offset=offset)

        where_clauses = []
        params = []

        if has_query:
            clean_q = str(query).strip()
            q_pattern = f"%{clean_q}%"
            query_conditions = [
                "m.title LIKE ?",
                "m.meeting_id LIKE ?",
                "m.audio_filename LIKE ?",
                "m.format LIKE ?",
                "m.language LIKE ?",
                "m.transcript LIKE ?",
                "EXISTS (SELECT 1 FROM summaries s WHERE s.meeting_id = m.meeting_id AND (s.summary_text LIKE ? OR s.key_points LIKE ? OR s.decisions LIKE ? OR s.deadlines LIKE ? OR s.priorities LIKE ?))",
                "EXISTS (SELECT 1 FROM action_items a WHERE a.meeting_id = m.meeting_id AND (a.task LIKE ? OR a.assignee LIKE ? OR a.deadline LIKE ? OR a.priority LIKE ?))",
                "EXISTS (SELECT 1 FROM participants p WHERE p.meeting_id = m.meeting_id AND p.participant_name LIKE ?)"
            ]
            where_clauses.append(f"({' OR '.join(query_conditions)})")
            params.extend([q_pattern, q_pattern, q_pattern, q_pattern, q_pattern, q_pattern])
            params.extend([q_pattern, q_pattern, q_pattern, q_pattern, q_pattern])
            params.extend([q_pattern, q_pattern, q_pattern, q_pattern])
            params.append(q_pattern)

        if has_participant:
            clean_part = str(participant).strip()
            where_clauses.append("EXISTS (SELECT 1 FROM participants p2 WHERE p2.meeting_id = m.meeting_id AND p2.participant_name LIKE ?)")
            params.append(f"%{clean_part}%")

        if has_date_prefix:
            clean_date = str(date).strip()
            where_clauses.append("m.created_at LIKE ?")
            params.append(f"%{clean_date}%")

        if has_start_date:
            where_clauses.append("m.created_at >= ?")
            params.append(effective_start)

        if has_end_date:
            ed = effective_end
            if len(ed) == 10:
                ed = f"{ed}T23:59:59"
            where_clauses.append("m.created_at <= ?")
            params.append(ed)

        if has_title:
            clean_title = str(title).strip()
            where_clauses.append("m.title LIKE ?")
            params.append(f"%{clean_title}%")

        if has_format:
            clean_fmt = str(format).strip()
            where_clauses.append("m.format LIKE ?")
            params.append(f"%{clean_fmt}%")

        if has_lang:
            clean_lang = str(language).strip()
            where_clauses.append("m.language LIKE ?")
            params.append(f"%{clean_lang}%")

        if user_id is not None:
            where_clauses.append("(m.user_id = ? OR m.user_id IS NULL)")
            params.append(user_id)

        where_sql = " AND ".join(where_clauses)
        sql = f"""
            SELECT DISTINCT m.*, 
                   (SELECT summary_text FROM summaries s WHERE s.meeting_id = m.meeting_id) as summary,
                   (SELECT COUNT(*) FROM action_items a WHERE a.meeting_id = m.meeting_id) as action_count
            FROM meetings m
            WHERE {where_sql}
            ORDER BY m.created_at DESC
        """

        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
            if offset is not None:
                sql += " OFFSET ?"
                params.append(offset)

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                rows = [dict(r) for r in cursor.fetchall()]

                enriched_results = []
                clean_q_lower = str(query).strip().lower() if has_query else None

                for row in rows:
                    mid = row["meeting_id"]

                    cursor.execute("SELECT * FROM summaries WHERE meeting_id = ?", (mid,))
                    s_row = cursor.fetchone()
                    key_points = _safe_json_loads(s_row["key_points"] if s_row else None, default=[])
                    decisions = _safe_json_loads(s_row["decisions"] if s_row else None, default=[])
                    deadlines = _safe_json_loads(s_row["deadlines"] if s_row else None, default=[])
                    priorities = _safe_json_loads(s_row["priorities"] if s_row else None, default=[])

                    cursor.execute("SELECT DISTINCT participant_name FROM participants WHERE meeting_id = ? ORDER BY id ASC", (mid,))
                    participants = [pr["participant_name"] for pr in cursor.fetchall()]

                    cursor.execute("SELECT task, assignee, deadline, priority, status FROM action_items WHERE meeting_id = ? ORDER BY id ASC", (mid,))
                    action_items = [dict(ar) for ar in cursor.fetchall()]

                    matched_fields = []
                    match_snippets = {}

                    if clean_q_lower:
                        if clean_q_lower in (row.get("title") or "").lower():
                            matched_fields.append("title")
                            match_snippets["title"] = row.get("title")

                        if clean_q_lower in (row.get("meeting_id") or "").lower():
                            matched_fields.append("meeting_id")
                            match_snippets["meeting_id"] = row.get("meeting_id")

                        if clean_q_lower in (row.get("summary") or "").lower():
                            matched_fields.append("summary")
                            match_snippets["summary"] = row.get("summary")

                        if clean_q_lower in (row.get("transcript") or "").lower():
                            matched_fields.append("transcript")
                            t_text = row.get("transcript") or ""
                            idx = t_text.lower().find(clean_q_lower)
                            start_idx = max(0, idx - 40)
                            end_idx = min(len(t_text), idx + len(clean_q_lower) + 60)
                            snippet = ("..." if start_idx > 0 else "") + t_text[start_idx:end_idx].strip() + ("..." if end_idx < len(t_text) else "")
                            match_snippets["transcript"] = snippet

                        matched_kp = [kp for kp in key_points if clean_q_lower in str(kp).lower()]
                        if matched_kp:
                            matched_fields.append("key_points")
                            match_snippets["key_points"] = matched_kp

                        matched_decs = [d for d in decisions if clean_q_lower in str(d).lower()]
                        if matched_decs:
                            matched_fields.append("decisions")
                            match_snippets["decisions"] = matched_decs

                        matched_dl = [dl for dl in deadlines if clean_q_lower in str(dl).lower()]
                        if matched_dl:
                            matched_fields.append("deadlines")
                            match_snippets["deadlines"] = matched_dl

                        matched_parts = [p for p in participants if clean_q_lower in str(p).lower()]
                        if matched_parts:
                            matched_fields.append("participants")
                            match_snippets["participants"] = matched_parts

                        matched_acts = [
                            f"{a.get('task')} ({a.get('assignee')})"
                            for a in action_items
                            if clean_q_lower in str(a.get("task")).lower() or clean_q_lower in str(a.get("assignee")).lower() or clean_q_lower in str(a.get("deadline")).lower()
                        ]
                        if matched_acts:
                            matched_fields.append("action_items")
                            match_snippets["action_items"] = matched_acts

                        meta_hits = []
                        if clean_q_lower in (row.get("audio_filename") or "").lower():
                            meta_hits.append(f"filename: {row.get('audio_filename')}")
                        if clean_q_lower in (row.get("format") or "").lower():
                            meta_hits.append(f"format: {row.get('format')}")
                        if clean_q_lower in (row.get("language") or "").lower():
                            meta_hits.append(f"language: {row.get('language')}")
                        if meta_hits:
                            matched_fields.append("metadata")
                            match_snippets["metadata"] = meta_hits

                    item_record = {
                        "meeting_id": mid,
                        "title": row.get("title", ""),
                        "audio_filename": row.get("audio_filename", ""),
                        "file_size_mb": row.get("file_size_mb", 0.0),
                        "duration_seconds": row.get("duration_seconds", 0.0),
                        "format": row.get("format", ""),
                        "language": row.get("language", ""),
                        "word_count": row.get("word_count", 0),
                        "validation_status": row.get("validation_status", ""),
                        "created_at": row.get("created_at", ""),
                        "summary": row.get("summary") or "",
                        "action_count": row.get("action_count", 0),
                        "key_points": key_points,
                        "decisions": decisions,
                        "deadlines": deadlines,
                        "priorities": priorities,
                        "participants": participants,
                        "action_items": action_items,
                        "matched_fields": matched_fields,
                        "match_snippets": match_snippets
                    }
                    enriched_results.append(item_record)

                logger.info(f"search_meetings query='{query}' filters=(part={participant}, date={date}, title={title}) -> {len(enriched_results)} results")
                return enriched_results
        except sqlite3.Error as e:
            logger.error(f"Database error while searching meetings: {e}", exc_info=True)
            raise

    def update_action_item_status(self, action_id: int, new_status: str) -> bool:
        """
        Updates the status of a specific action item (e.g. Pending, In Progress, Completed).
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE action_items SET status = ? WHERE id = ?", (new_status, action_id))
                conn.commit()
                updated = cursor.rowcount > 0
                if updated:
                    logger.info(f"Updated action item {action_id} status to '{new_status}'.")
                return updated
        except sqlite3.Error as e:
            logger.error(f"Database error updating action item {action_id}: {e}", exc_info=True)
            raise

    def add_action_item(
        self,
        meeting_id: str,
        task: str,
        assignee: str = "Unassigned",
        priority: str = "Medium",
        deadline: str = "Not specified",
        status: str = "Pending"
    ) -> int:
        """
        Inserts a new action item for an existing meeting.
        """
        if not meeting_id or not meeting_id.strip():
            raise ValueError("meeting_id is required to add an action item.")
        now = datetime.now().isoformat()
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO action_items (
                        meeting_id, task, assignee, priority, deadline, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    meeting_id.strip(),
                    task.strip(),
                    assignee.strip() or "Unassigned",
                    priority.strip() or "Medium",
                    deadline.strip() or "Not specified",
                    status.strip() or "Pending",
                    now
                ))
                conn.commit()
                last_id = cursor.lastrowid
                logger.info(f"Added action item {last_id} to meeting '{meeting_id}'.")
                return last_id
        except sqlite3.Error as e:
            logger.error(f"Database error adding action item to meeting '{meeting_id}': {e}", exc_info=True)
            raise

    def delete_meeting(self, meeting_id: str) -> bool:
        """
        Deletes a meeting and all cascading dependent records.
        """
        if not meeting_id or not isinstance(meeting_id, str) or not meeting_id.strip():
            logger.warning(f"delete_meeting called with invalid meeting_id: {meeting_id!r}")
            return False

        clean_id = meeting_id.strip()
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM summaries WHERE meeting_id = ?", (clean_id,))
                cursor.execute("DELETE FROM action_items WHERE meeting_id = ?", (clean_id,))
                cursor.execute("DELETE FROM participants WHERE meeting_id = ?", (clean_id,))
                cursor.execute("DELETE FROM validation_logs WHERE meeting_id = ?", (clean_id,))
                cursor.execute("DELETE FROM meetings WHERE meeting_id = ?", (clean_id,))
                conn.commit()
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"Deleted meeting '{clean_id}' and all linked records.")
                else:
                    logger.warning(f"Meeting '{clean_id}' not found for deletion.")
                return deleted
        except sqlite3.Error as e:
            logger.error(f"Database error deleting meeting '{clean_id}': {e}", exc_info=True)
            raise

    def get_dashboard_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculates aggregate repository statistics for dashboard and API display.
        When user_id is provided, scopes calculations to that user's meetings.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if user_id is not None:
                    cursor.execute("SELECT COUNT(*) as total_meetings FROM meetings WHERE (user_id = ? OR user_id IS NULL)", (user_id,))
                    total_m = cursor.fetchone()["total_meetings"]

                    cursor.execute("""
                        SELECT COUNT(*) as total_actions FROM action_items a
                        JOIN meetings m ON a.meeting_id = m.meeting_id
                        WHERE (m.user_id = ? OR m.user_id IS NULL)
                    """, (user_id,))
                    total_act = cursor.fetchone()["total_actions"]

                    cursor.execute("""
                        SELECT COUNT(*) as pending_actions FROM action_items a
                        JOIN meetings m ON a.meeting_id = m.meeting_id
                        WHERE (m.user_id = ? OR m.user_id IS NULL) AND a.status = 'Pending'
                    """, (user_id,))
                    pending_act = cursor.fetchone()["pending_actions"]

                    cursor.execute("""
                        SELECT COUNT(*) as completed_actions FROM action_items a
                        JOIN meetings m ON a.meeting_id = m.meeting_id
                        WHERE (m.user_id = ? OR m.user_id IS NULL) AND a.status = 'Completed'
                    """, (user_id,))
                    completed_act = cursor.fetchone()["completed_actions"]
                else:
                    cursor.execute("SELECT COUNT(*) as total_meetings FROM meetings")
                    total_m = cursor.fetchone()["total_meetings"]

                    cursor.execute("SELECT COUNT(*) as total_actions FROM action_items")
                    total_act = cursor.fetchone()["total_actions"]

                    cursor.execute("SELECT COUNT(*) as pending_actions FROM action_items WHERE status = 'Pending'")
                    pending_act = cursor.fetchone()["pending_actions"]

                    cursor.execute("SELECT COUNT(*) as completed_actions FROM action_items WHERE status = 'Completed'")
                    completed_act = cursor.fetchone()["completed_actions"]

                return {
                    "total_meetings": total_m,
                    "total_action_items": total_act,
                    "pending_action_items": pending_act,
                    "completed_action_items": completed_act
                }
        except sqlite3.Error as e:
            logger.error(f"Database error getting dashboard stats: {e}", exc_info=True)
            raise

    def get_historical_insights(
        self,
        participant: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[str] = None,
        title: Optional[str] = None,
        limit: int = 50,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Computes comprehensive cross-meeting historical insights, aggregate KPIs,
        filtered decisions, action items, participants directory, deadlines,
        and project history across the Meeting Knowledge Repository.
        When user_id is provided, scopes the insights to that user's meetings.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Base filtering for meetings
                meeting_where = []
                meeting_params = []

                if user_id is not None:
                    meeting_where.append("(m.user_id = ? OR m.user_id IS NULL)")
                    meeting_params.append(user_id)

                if title and title.strip():
                    meeting_where.append("m.title LIKE ?")
                    meeting_params.append(f"%{title.strip()}%")

                if start_date and start_date.strip():
                    meeting_where.append("m.created_at >= ?")
                    meeting_params.append(start_date.strip())

                if end_date and end_date.strip():
                    ed = end_date.strip()
                    if len(ed) == 10:
                        ed = f"{ed}T23:59:59"
                    meeting_where.append("m.created_at <= ?")
                    meeting_params.append(ed)

                if participant and participant.strip():
                    meeting_where.append("""
                        m.meeting_id IN (
                            SELECT meeting_id FROM participants WHERE participant_name LIKE ?
                            UNION
                            SELECT meeting_id FROM action_items WHERE assignee LIKE ?
                        )
                    """)
                    meeting_params.append(f"%{participant.strip()}%")
                    meeting_params.append(f"%{participant.strip()}%")

                where_clause = ""
                if meeting_where:
                    where_clause = "WHERE " + " AND ".join(meeting_where)

                # 1. Matching Meetings Query
                query_meetings = f"""
                    SELECT m.meeting_id, m.title, m.created_at, m.duration_seconds, m.language,
                           s.summary_text, s.decisions, s.deadlines
                    FROM meetings m
                    LEFT JOIN summaries s ON m.meeting_id = s.meeting_id
                    {where_clause}
                    ORDER BY m.created_at DESC
                    LIMIT ?
                """
                cursor.execute(query_meetings, meeting_params + [limit])
                raw_meetings = cursor.fetchall()

                matching_mids = [r["meeting_id"] for r in raw_meetings]

                # 2. Extract decisions across meetings
                all_decisions = []
                for rm in raw_meetings:
                    decs = _safe_json_loads(rm["decisions"], [])
                    for d in decs:
                        if isinstance(d, str) and d.strip():
                            all_decisions.append({
                                "meeting_id": rm["meeting_id"],
                                "meeting_title": rm["title"],
                                "created_at": rm["created_at"],
                                "decision": d.strip()
                            })

                # 3. Action Items Query (Filtered by status, participant, and matching meetings)
                action_where = []
                action_params = []

                if matching_mids:
                    placeholders = ",".join(["?"] * len(matching_mids))
                    action_where.append(f"a.meeting_id IN ({placeholders})")
                    action_params.extend(matching_mids)
                elif meeting_where:
                    action_where.append("1 = 0")

                if status and status.strip() and status.strip().lower() != "all":
                    action_where.append("LOWER(a.status) = ?")
                    action_params.append(status.strip().lower())

                if participant and participant.strip():
                    action_where.append("a.assignee LIKE ?")
                    action_params.append(f"%{participant.strip()}%")

                act_where_clause = ""
                if action_where:
                    act_where_clause = "WHERE " + " AND ".join(action_where)

                cursor.execute(f"""
                    SELECT a.id, a.meeting_id, a.task, a.assignee, a.priority, 
                           a.deadline, a.status, a.created_at, m.title as meeting_title
                    FROM action_items a
                    JOIN meetings m ON a.meeting_id = m.meeting_id
                    {act_where_clause}
                    ORDER BY 
                        CASE a.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
                        a.created_at DESC
                """, action_params)
                raw_actions = cursor.fetchall()

                action_items_list = [
                    {
                        "id": r["id"],
                        "meeting_id": r["meeting_id"],
                        "meeting_title": r["meeting_title"],
                        "task": r["task"],
                        "assignee": r["assignee"],
                        "priority": r["priority"],
                        "deadline": r["deadline"],
                        "status": r["status"],
                        "created_at": r["created_at"]
                    }
                    for r in raw_actions
                ]

                # 4. Global Action Item Status Counts (for matching meetings)
                if matching_mids:
                    cursor.execute(f"""
                        SELECT status, COUNT(*) as cnt 
                        FROM action_items 
                        WHERE meeting_id IN ({','.join(['?']*len(matching_mids))})
                        GROUP BY status
                    """, matching_mids)
                    status_counts = {r["status"]: r["cnt"] for r in cursor.fetchall()}
                else:
                    status_counts = {}

                pending_cnt = status_counts.get("Pending", 0)
                in_progress_cnt = status_counts.get("In Progress", 0)
                completed_cnt = status_counts.get("Completed", 0)
                total_actions_cnt = sum(status_counts.values())

                # 5. Participants Aggregation (Workload & meetings attended)
                if matching_mids:
                    cursor.execute(f"""
                        SELECT participant_name, COUNT(DISTINCT meeting_id) as meetings_attended
                        FROM participants
                        WHERE meeting_id IN ({','.join(['?']*len(matching_mids))})
                        GROUP BY participant_name
                        ORDER BY meetings_attended DESC, participant_name ASC
                    """, matching_mids)
                    part_rows = cursor.fetchall()
                else:
                    part_rows = []

                participants_workload = []
                for pr in part_rows:
                    pname = pr["participant_name"]
                    p_tasks = [a for a in action_items_list if a["assignee"].lower() == pname.lower()]
                    p_pending = sum(1 for a in p_tasks if a["status"] == "Pending")
                    p_completed = sum(1 for a in p_tasks if a["status"] == "Completed")
                    participants_workload.append({
                        "name": pname,
                        "meetings_attended": pr["meetings_attended"],
                        "total_tasks": len(p_tasks),
                        "pending_tasks": p_pending,
                        "completed_tasks": p_completed
                    })

                # 6. Deadlines Aggregation (From action items and meeting intelligence)
                deadlines_list = []
                seen_deadlines = set()
                for a in action_items_list:
                    dl = a.get("deadline", "").strip()
                    if dl and dl.lower() not in ["not specified", "none", "n/a", ""]:
                        key = (a["meeting_id"], dl, a["task"])
                        if key not in seen_deadlines:
                            seen_deadlines.add(key)
                            deadlines_list.append({
                                "meeting_id": a["meeting_id"],
                                "meeting_title": a["meeting_title"],
                                "deadline": dl,
                                "context": f"Task: {a['task']} ({a['assignee']})",
                                "status": a["status"]
                            })
                for rm in raw_meetings:
                    s_dls = _safe_json_loads(rm["deadlines"], [])
                    for sdl in s_dls:
                        if isinstance(sdl, str) and sdl.strip() and sdl.strip().lower() not in ["none", "not specified"]:
                            key = (rm["meeting_id"], sdl.strip(), "Meeting Target")
                            if key not in seen_deadlines:
                                seen_deadlines.add(key)
                                deadlines_list.append({
                                    "meeting_id": rm["meeting_id"],
                                    "meeting_title": rm["title"],
                                    "deadline": sdl.strip(),
                                    "context": "Meeting Target / Milestone",
                                    "status": "Target"
                                })

                # 7. Recent Meetings structured overview
                recent_meetings_list = []
                for rm in raw_meetings:
                    mid = rm["meeting_id"]
                    cursor.execute("SELECT COUNT(*) as c FROM action_items WHERE meeting_id = ?", (mid,))
                    act_c = cursor.fetchone()["c"]
                    cursor.execute("SELECT COUNT(*) as c FROM participants WHERE meeting_id = ?", (mid,))
                    part_c = cursor.fetchone()["c"]
                    sum_txt = rm["summary_text"] or ""
                    snippet = sum_txt[:180] + ("..." if len(sum_txt) > 180 else "")

                    recent_meetings_list.append({
                        "meeting_id": mid,
                        "title": rm["title"],
                        "created_at": rm["created_at"],
                        "duration_seconds": rm["duration_seconds"] or 0.0,
                        "action_count": act_c,
                        "participant_count": part_c,
                        "summary_snippet": snippet
                    })

                # 8. Project / Topic History
                project_history = []
                for rm in reversed(raw_meetings):
                    decs = _safe_json_loads(rm["decisions"], [])
                    project_history.append({
                        "meeting_id": rm["meeting_id"],
                        "title": rm["title"],
                        "date": rm["created_at"][:10] if rm["created_at"] else "Unknown",
                        "summary": rm["summary_text"] or "",
                        "decisions_count": len(decs),
                        "key_decisions": decs[:3]
                    })

                return {
                    "total_meetings": len(raw_meetings),
                    "total_action_items": total_actions_cnt,
                    "pending_action_items": pending_cnt,
                    "in_progress_action_items": in_progress_cnt,
                    "completed_action_items": completed_cnt,
                    "unique_participants_count": len(participants_workload),
                    "total_decisions_count": len(all_decisions),
                    "total_deadlines_count": len(deadlines_list),
                    "recent_meetings": recent_meetings_list,
                    "participants": participants_workload,
                    "decisions": all_decisions,
                    "action_items": action_items_list,
                    "deadlines": deadlines_list,
                    "project_history": project_history,
                    "filters_applied": {
                        "participant": participant,
                        "start_date": start_date,
                        "end_date": end_date,
                        "status": status,
                        "title": title
                    }
                }
        except sqlite3.Error as e:
            logger.error(f"Database error getting historical insights: {e}", exc_info=True)
            raise

    # -------------------------------------------------------------------------
    # External Integrations Sync & Audit Logging (Milestone 4 - Tasks 4 & 5)
    # -------------------------------------------------------------------------
    def log_integration_event(
        self,
        source: str,
        external_meeting_id: str,
        internal_meeting_id: Optional[str],
        title: Optional[str],
        status: str,
        details: Optional[str] = None,
        user_id: int = 1
    ) -> int:
        """
        Records an external sync event (Zoom / Google Meet) for auditing and duplicate prevention.
        """
        now = datetime.now().isoformat()
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO integration_logs (
                        source, external_meeting_id, internal_meeting_id, title, status, details, created_at, user_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    source.lower().strip(),
                    str(external_meeting_id).strip(),
                    str(internal_meeting_id).strip() if internal_meeting_id else None,
                    str(title).strip() if title else "Untitled Ingested Meeting",
                    status.upper().strip(),
                    str(details) if details else "",
                    now,
                    int(user_id or 1)
                ))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error logging integration event: {e}", exc_info=True)
            return -1

    def is_external_meeting_synced(
        self,
        source: str,
        external_meeting_id: str,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Checks whether an external meeting (Zoom/Google Meet) has already been successfully ingested.
        Prevents redundant Whisper transcription and processing.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT COUNT(*) as count FROM integration_logs WHERE source = ? AND external_meeting_id = ? AND status = 'SUCCESS'"
                params = [source.lower().strip(), str(external_meeting_id).strip()]
                if user_id:
                    query += " AND user_id = ?"
                    params.append(int(user_id))
                cursor.execute(query, params)
                res = cursor.fetchone()
                return bool(res and res["count"] > 0)
        except sqlite3.Error as e:
            logger.error(f"Error checking duplicate integration sync: {e}", exc_info=True)
            return False

    def get_integration_logs(
        self,
        source: Optional[str] = None,
        user_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieves recent integration sync logs for auditing and UI display.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM integration_logs WHERE 1=1"
                params = []
                if source:
                    query += " AND source = ?"
                    params.append(source.lower().strip())
                if user_id:
                    query += " AND user_id = ?"
                    params.append(int(user_id))
                query += " ORDER BY id DESC LIMIT ?"
                params.append(limit)
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving integration logs: {e}", exc_info=True)
            return []


if __name__ == "__main__":
    db = DatabaseManager()
    print("Initializing Database...")
    print("Database path:", db.db_path)

    # Test saving a sample meeting
    sample_id = f"MEET-TEST-{uuid.uuid4().hex[:4].upper()}"
    db.save_meeting(
        meeting_id=sample_id,
        title="Sample Sprint Sync",
        audio_filename="transcipt_test2.mp3",
        file_size_mb=0.14,
        duration_seconds=12.5,
        format_ext=".mp3",
        language="en",
        transcript="Today's meeting date is 27th August and day is Thursday.",
        intelligence={
            "summary": "Team aligned on meeting schedule for 27th August.",
            "key_points": ["Verified date and time"],
            "decisions": ["Proceed with sprint sync"],
            "deadlines": ["27th August"],
            "priorities": ["High"],
            "action_items": [
                {"task": "Prepare report", "assignee": "Priyanshu", "priority": "High", "deadline": "Thursday", "status": "Pending"}
            ]
        },
        participant_data={
            "unique_participants": ["Priyanshu", "Deepasri", "Priyanshu"],  # includes duplicate to test deduplication
            "responsibilities": []
        },
        validation_info={"is_valid": True, "file_check": "PASSED", "transcript_check": "PASSED", "schema_check": "PASSED"}
    )

    retrieved = db.get_meeting(sample_id)
    print("Retrieved Meeting ID:", retrieved["meeting_id"])
    print("Summary:", retrieved["summary"])
    print("Action Items Count:", len(retrieved["action_items"]))
    print("Participants (Deduplicated):", retrieved["participants"])
    print("Dashboard Stats:", db.get_dashboard_stats())
    db.delete_meeting(sample_id)
    print("Cleaned up test record successfully.")

