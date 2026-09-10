import os
import sqlite3
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

DB_FILE = os.path.join(os.path.dirname(__file__), "whisper_meetings.db")

class DatabaseManager:
    """
    Task 5: Meeting Data Model & Database Persistence
    Provides SQLite relational persistence for transcripts, summaries, 
    action items, participants, and validation logs.
    """
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """
        Creates required relational database tables if they do not exist.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Meetings Core Table
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
                    created_at TEXT NOT NULL
                )
            """)

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

            # 4. Participants Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meeting_id TEXT NOT NULL,
                    participant_name TEXT NOT NULL,
                    FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id) ON DELETE CASCADE
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

            conn.commit()

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
        validation_info: Dict[str, Any]
    ) -> str:
        """
        Persists a complete processed meeting transactionally into SQLite.
        """
        now = datetime.now().isoformat()
        word_count = len(transcript.split()) if transcript else 0

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Insert Meeting record
            cursor.execute("""
                INSERT OR REPLACE INTO meetings (
                    meeting_id, title, audio_filename, file_size_mb, duration_seconds,
                    format, language, transcript, word_count, validation_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                meeting_id, title, audio_filename, file_size_mb, duration_seconds,
                format_ext, language, transcript, word_count,
                "VALIDATED" if validation_info.get("is_valid", True) else "FAILED",
                now
            ))

            # Delete old related records if updating
            cursor.execute("DELETE FROM summaries WHERE meeting_id = ?", (meeting_id,))
            cursor.execute("DELETE FROM action_items WHERE meeting_id = ?", (meeting_id,))
            cursor.execute("DELETE FROM participants WHERE meeting_id = ?", (meeting_id,))
            cursor.execute("DELETE FROM validation_logs WHERE meeting_id = ?", (meeting_id,))

            # Insert Summary record
            summary_text = intelligence.get("summary", "No summary generated.")
            key_points_json = json.dumps(intelligence.get("key_points", []))
            decisions_json = json.dumps(intelligence.get("decisions", []))
            deadlines_json = json.dumps(intelligence.get("deadlines", []))
            priorities_json = json.dumps(intelligence.get("priorities", []))

            cursor.execute("""
                INSERT INTO summaries (
                    meeting_id, summary_text, key_points, decisions, deadlines, priorities
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (meeting_id, summary_text, key_points_json, decisions_json, deadlines_json, priorities_json))

            # Insert Action Items from Intelligence & Mapping
            actions = intelligence.get("action_items", [])
            if not actions and participant_data and "responsibilities" in participant_data:
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
                task = act.get("task", "").strip()
                if not task:
                    continue
                assignee = act.get("assignee", "Unassigned")
                if isinstance(assignee, list):
                    assignee = ", ".join(assignee)
                priority = act.get("priority", "Medium")
                deadline = act.get("deadline", "Not specified")
                status = act.get("status", "Pending")

                cursor.execute("""
                    INSERT INTO action_items (
                        meeting_id, task, assignee, priority, deadline, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (meeting_id, task, assignee, priority, deadline, status, now))

            # Insert Participants
            unique_parts = participant_data.get("unique_participants", []) if participant_data else intelligence.get("participants", [])
            if not unique_parts:
                unique_parts = ["Narrator / Speaker"]

            for p_name in unique_parts:
                cursor.execute("""
                    INSERT INTO participants (meeting_id, participant_name) VALUES (?, ?)
                """, (meeting_id, str(p_name)))

            # Insert Validation Log
            cursor.execute("""
                INSERT INTO validation_logs (
                    meeting_id, is_valid, file_check, transcript_check, schema_check, validated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                meeting_id,
                1 if validation_info.get("is_valid", True) else 0,
                validation_info.get("file_check", "PASSED"),
                validation_info.get("transcript_check", "PASSED"),
                validation_info.get("schema_check", "PASSED"),
                now
            ))

            conn.commit()
            return meeting_id

    def get_meeting(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves complete meeting record including summary, action items, participants, and validation logs.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM meetings WHERE meeting_id = ?", (meeting_id,))
            m_row = cursor.fetchone()
            if not m_row:
                return None

            meeting = dict(m_row)

            # Fetch summary
            cursor.execute("SELECT * FROM summaries WHERE meeting_id = ?", (meeting_id,))
            s_row = cursor.fetchone()
            if s_row:
                s_dict = dict(s_row)
                meeting["summary"] = s_dict.get("summary_text")
                meeting["key_points"] = json.loads(s_dict.get("key_points") or "[]")
                meeting["decisions"] = json.loads(s_dict.get("decisions") or "[]")
                meeting["deadlines"] = json.loads(s_dict.get("deadlines") or "[]")
                meeting["priorities"] = json.loads(s_dict.get("priorities") or "[]")
            else:
                meeting["summary"] = ""
                meeting["key_points"] = []
                meeting["decisions"] = []
                meeting["deadlines"] = []
                meeting["priorities"] = []

            # Fetch action items
            cursor.execute("SELECT * FROM action_items WHERE meeting_id = ?", (meeting_id,))
            meeting["action_items"] = [dict(r) for r in cursor.fetchall()]

            # Fetch participants
            cursor.execute("SELECT participant_name FROM participants WHERE meeting_id = ?", (meeting_id,))
            meeting["participants"] = [r["participant_name"] for r in cursor.fetchall()]

            # Fetch validation logs
            cursor.execute("SELECT * FROM validation_logs WHERE meeting_id = ?", (meeting_id,))
            v_row = cursor.fetchone()
            meeting["validation"] = dict(v_row) if v_row else {}

            return meeting

    def list_all_meetings(self) -> List[Dict[str, Any]]:
        """
        Lists summary metadata of all stored meetings ordered by creation time descending.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT m.*, 
                       (SELECT summary_text FROM summaries s WHERE s.meeting_id = m.meeting_id) as summary,
                       (SELECT COUNT(*) FROM action_items a WHERE a.meeting_id = m.meeting_id) as action_count
                FROM meetings m
                ORDER BY created_at DESC
            """)
            return [dict(r) for r in cursor.fetchall()]

    def search_meetings(self, query: str) -> List[Dict[str, Any]]:
        """
        Searches meetings by title, transcript text, or participant name.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            q = f"%{query.strip()}%"
            cursor.execute("""
                SELECT DISTINCT m.*, 
                       (SELECT summary_text FROM summaries s WHERE s.meeting_id = m.meeting_id) as summary,
                       (SELECT COUNT(*) FROM action_items a WHERE a.meeting_id = m.meeting_id) as action_count
                FROM meetings m
                LEFT JOIN participants p ON m.meeting_id = p.meeting_id
                WHERE m.title LIKE ? OR m.transcript LIKE ? OR p.participant_name LIKE ? OR m.meeting_id LIKE ?
                ORDER BY m.created_at DESC
            """, (q, q, q, q))
            return [dict(r) for r in cursor.fetchall()]

    def update_action_item_status(self, action_id: int, new_status: str) -> bool:
        """
        Updates the status of a specific action item (e.g. Pending, In Progress, Completed).
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE action_items SET status = ? WHERE id = ?", (new_status, action_id))
            conn.commit()
            return cursor.rowcount > 0

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
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO action_items (
                    meeting_id, task, assignee, priority, deadline, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (meeting_id, task.strip(), assignee.strip() or "Unassigned", priority, deadline.strip() or "Not specified", status, now))
            conn.commit()
            return cursor.lastrowid

    def delete_meeting(self, meeting_id: str) -> bool:
        """
        Deletes a meeting and all cascading dependent records.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM meetings WHERE meeting_id = ?", (meeting_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """
        Calculates aggregate repository statistics for dashboard display.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
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
            "unique_participants": ["Priyanshu", "Deepasri"],
            "responsibilities": []
        },
        validation_info={"is_valid": True, "file_check": "PASSED", "transcript_check": "PASSED", "schema_check": "PASSED"}
    )

    retrieved = db.get_meeting(sample_id)
    print("Retrieved Meeting ID:", retrieved["meeting_id"])
    print("Summary:", retrieved["summary"])
    print("Action Items Count:", len(retrieved["action_items"]))
    print("Dashboard Stats:", db.get_dashboard_stats())
    db.delete_meeting(sample_id)
    print("Cleaned up test record successfully.")
