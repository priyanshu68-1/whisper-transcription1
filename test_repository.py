import os
import unittest
import uuid
import json
from datetime import datetime
from fastapi.testclient import TestClient

from database import DatabaseManager, _safe_json_loads
from api import app

class TestMeetingKnowledgeRepository(unittest.TestCase):
    """
    Milestone 3 – Task 1: Meeting Knowledge Repository Test Suite
    Verifies:
    1. Retrieving an existing meeting
    2. Retrieving a non-existing meeting (returns None in DB, 404 in API)
    3. Retrieving multiple meetings
    4. Checking meeting_id linkage across summary, transcript, decisions, deadlines
    5. Checking action item linkage and required fields (task, assignee, deadline, priority, status)
    6. Checking participant linkage and deduplication
    7. Cross-meeting data isolation (Meeting A data never appears in Meeting B)
    8. Safe handling of malformed records & invalid meeting IDs
    9. API endpoint retrieval through FastAPI TestClient
    """

    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager()
        cls.client = TestClient(app)

        # Unique IDs for test fixtures
        cls.test_meeting_id_1 = f"TEST-MEET-{uuid.uuid4().hex[:6].upper()}"
        cls.test_meeting_id_2 = f"TEST-MEET-{uuid.uuid4().hex[:6].upper()}"

        # Seed test meeting 1
        cls.db.save_meeting(
            meeting_id=cls.test_meeting_id_1,
            title="Q3 Strategic Architecture Review",
            audio_filename="strategic_review_q3.mp3",
            file_size_mb=4.25,
            duration_seconds=360.0,
            format_ext=".MP3",
            language="EN",
            transcript="Priyanshu discussed the knowledge repository architecture. Ravi agreed to implement FastAPI endpoints by Friday. Deepasri will run UI validation tests.",
            intelligence={
                "summary": "The team aligned on the knowledge repository architecture and assigned API and UI validation tasks.",
                "key_points": [
                    "Knowledge repository stores transcripts, summaries, and tasks.",
                    "FastAPI endpoints will expose meeting data.",
                    "Testing suite verifies data integrity and isolation."
                ],
                "decisions": [
                    "Adopt SQLite relational model with foreign keys.",
                    "Use FastAPI for REST retrieval endpoints."
                ],
                "deadlines": ["Friday", "End of Sprint"],
                "priorities": ["High", "Medium"],
                "action_items": [
                    {
                        "task": "Implement FastAPI endpoints",
                        "assignee": "Ravi",
                        "priority": "High",
                        "deadline": "Friday",
                        "status": "Pending"
                    },
                    {
                        "task": "Run UI validation tests",
                        "assignee": "Deepasri",
                        "priority": "Medium",
                        "deadline": "Next Monday",
                        "status": "In Progress"
                    }
                ]
            },
            participant_data={
                # Intentionally provide duplicate participant entries to test deduplication
                "unique_participants": ["Priyanshu", "Ravi", "Deepasri", "Priyanshu", "ravi"],
                "responsibilities": []
            },
            validation_info={
                "is_valid": True,
                "file_check": "PASSED",
                "transcript_check": "PASSED",
                "schema_check": "PASSED"
            }
        )

        # Seed test meeting 2 (to verify multiple meetings and isolation)
        cls.db.save_meeting(
            meeting_id=cls.test_meeting_id_2,
            title="Design System & Styling Sync",
            audio_filename="design_sync.mp4",
            file_size_mb=12.10,
            duration_seconds=620.5,
            format_ext=".MP4",
            language="EN",
            transcript="Cindy presented the colorful dark mode UI tokens. William reviewed accessibility contrast.",
            intelligence={
                "summary": "Design team finalized vibrant color tokens and confirmed contrast standards.",
                "key_points": ["Color palette updated", "Accessible contrast verified"],
                "decisions": ["Proceed with vibrant styling theme"],
                "deadlines": ["Thursday 5 PM"],
                "priorities": ["High"],
                "action_items": [
                    {
                        "task": "Update CSS design tokens in Streamlit app",
                        "assignee": "Cindy",
                        "priority": "High",
                        "deadline": "Thursday 5 PM",
                        "status": "Completed"
                    }
                ]
            },
            participant_data={
                "unique_participants": ["Cindy", "William"],
                "responsibilities": []
            },
            validation_info={
                "is_valid": True,
                "file_check": "PASSED",
                "transcript_check": "PASSED",
                "schema_check": "PASSED"
            }
        )

    @classmethod
    def tearDownClass(cls):
        # Clean up test records
        cls.db.delete_meeting(cls.test_meeting_id_1)
        cls.db.delete_meeting(cls.test_meeting_id_2)

    # -----------------------------------------------------------------------
    # Requirement 20.1: Retrieving an existing meeting
    # -----------------------------------------------------------------------
    def test_01_retrieve_existing_meeting(self):
        meeting = self.db.get_meeting(self.test_meeting_id_1)
        self.assertIsNotNone(meeting, "Expected existing meeting to be found")
        self.assertEqual(meeting["meeting_id"], self.test_meeting_id_1)
        self.assertEqual(meeting["title"], "Q3 Strategic Architecture Review")
        self.assertIn("knowledge repository", meeting["transcript"])
        self.assertIn("aligned on the knowledge repository", meeting["summary"])
        self.assertGreater(len(meeting["key_points"]), 0)
        self.assertGreater(len(meeting["decisions"]), 0)
        self.assertGreater(len(meeting["action_items"]), 0)
        self.assertGreater(len(meeting["participants"]), 0)

    # -----------------------------------------------------------------------
    # Requirement 20.2: Retrieving a non-existing meeting
    # -----------------------------------------------------------------------
    def test_02_retrieve_non_existing_meeting(self):
        non_existent_id = "MEET-DOES-NOT-EXIST-9999"
        result = self.db.get_meeting(non_existent_id)
        self.assertIsNone(result, "Expected None when retrieving non-existent meeting from database")

        # Via API: should return 404
        response = self.client.get(f"/meetings/{non_existent_id}")
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"].lower())

    # -----------------------------------------------------------------------
    # Requirement 20.3: Retrieving multiple meetings
    # -----------------------------------------------------------------------
    def test_03_retrieve_multiple_meetings(self):
        meetings = self.db.list_all_meetings()
        self.assertIsInstance(meetings, list)
        self.assertGreaterEqual(len(meetings), 2, "Expected at least 2 meetings in database")

        meeting_ids = [m["meeting_id"] for m in meetings]
        self.assertIn(self.test_meeting_id_1, meeting_ids)
        self.assertIn(self.test_meeting_id_2, meeting_ids)

        # Via API
        response = self.client.get("/meetings")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["total"], 2)

    # -----------------------------------------------------------------------
    # Requirement 20.4: Checking meeting_id linkage
    # -----------------------------------------------------------------------
    def test_04_meeting_id_linkage(self):
        m1 = self.db.get_meeting(self.test_meeting_id_1)
        self.assertEqual(m1["meeting_id"], self.test_meeting_id_1)

        # Check transcript linkage
        transcript = self.db.get_meeting_transcript(self.test_meeting_id_1)
        self.assertEqual(transcript, m1["transcript"])

        # Check decisions & deadlines linkage
        self.assertIn("Adopt SQLite relational model with foreign keys.", m1["decisions"])
        self.assertIn("Friday", m1["deadlines"])

        # Check validation linkage
        self.assertIn("validation", m1)
        self.assertEqual(m1["validation"]["meeting_id"], self.test_meeting_id_1)

    # -----------------------------------------------------------------------
    # Requirement 20.5: Checking action item linkage
    # -----------------------------------------------------------------------
    def test_05_action_item_linkage(self):
        m1 = self.db.get_meeting(self.test_meeting_id_1)
        action_items = m1["action_items"]
        self.assertEqual(len(action_items), 2)

        for item in action_items:
            # Every action item must strictly link to meeting_id
            self.assertEqual(item["meeting_id"], self.test_meeting_id_1)
            # Must include task, assigned participant, deadline, priority, status
            self.assertTrue(item.get("task"))
            self.assertTrue(item.get("assignee"))
            self.assertTrue(item.get("assigned_participant"))
            self.assertTrue(item.get("deadline"))
            self.assertTrue(item.get("priority"))
            self.assertTrue(item.get("status"))

        tasks = [a["task"] for a in action_items]
        self.assertIn("Implement FastAPI endpoints", tasks)
        self.assertIn("Run UI validation tests", tasks)

    # -----------------------------------------------------------------------
    # Requirement 20.6: Checking participant linkage & deduplication
    # -----------------------------------------------------------------------
    def test_06_participant_linkage_and_deduplication(self):
        m1 = self.db.get_meeting(self.test_meeting_id_1)
        participants = m1["participants"]

        # Initial list had ["Priyanshu", "Ravi", "Deepasri", "Priyanshu", "ravi"]
        # After deduplication, should have exactly 3 unique participants
        self.assertEqual(len(participants), 3)
        self.assertEqual(set(participants), {"Priyanshu", "Ravi", "Deepasri"})

    # -----------------------------------------------------------------------
    # Cross-Meeting Data Isolation (Zero Leakage)
    # -----------------------------------------------------------------------
    def test_07_cross_meeting_data_isolation(self):
        m1 = self.db.get_meeting(self.test_meeting_id_1)
        m2 = self.db.get_meeting(self.test_meeting_id_2)

        # Confirm different titles and transcripts
        self.assertNotEqual(m1["title"], m2["title"])
        self.assertNotEqual(m1["transcript"], m2["transcript"])

        # M1 action items must NOT appear in M2
        m1_task_names = {a["task"] for a in m1["action_items"]}
        m2_task_names = {a["task"] for a in m2["action_items"]}
        self.assertTrue(m1_task_names.isdisjoint(m2_task_names), "Action items must not leak across meetings")

        # M1 participants must NOT leak into M2
        m1_parts = set(m1["participants"])
        m2_parts = set(m2["participants"])
        self.assertTrue(m1_parts.isdisjoint(m2_parts), "Participants must not leak across distinct meetings")

    # -----------------------------------------------------------------------
    # Error Handling & Malformed Record Resilience
    # -----------------------------------------------------------------------
    def test_08_error_handling_invalid_id_and_malformed_records(self):
        # 1. Invalid / Empty ID
        self.assertIsNone(self.db.get_meeting(""))
        self.assertIsNone(self.db.get_meeting("   "))
        self.assertIsNone(self.db.get_meeting(None))

        # Via API: invalid ID returns 400 Bad Request
        res_empty = self.client.get("/meetings/%20%20")
        self.assertEqual(res_empty.status_code, 400)

        # 2. Safe parsing of malformed JSON
        malformed_json_str = "['unclosed, broken json"
        safe_result = _safe_json_loads(malformed_json_str, default=["fallback"])
        self.assertEqual(safe_result, ["fallback"])

        safe_empty = _safe_json_loads(None, default=[])
        self.assertEqual(safe_empty, [])

    # -----------------------------------------------------------------------
    # API Endpoints Test Cases (FastAPI)
    # -----------------------------------------------------------------------
    def test_09_api_endpoints(self):
        # 1. GET / (Health Check)
        res_root = self.client.get("/")
        self.assertEqual(res_root.status_code, 200)
        self.assertEqual(res_root.json()["status"], "healthy")

        # 2. GET /meetings/{meeting_id}
        res_get = self.client.get(f"/meetings/{self.test_meeting_id_1}")
        self.assertEqual(res_get.status_code, 200)
        body = res_get.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["meeting_id"], self.test_meeting_id_1)
        self.assertEqual(body["title"], "Q3 Strategic Architecture Review")

        # 3. GET /meetings/{meeting_id}/transcript
        res_tr = self.client.get(f"/meetings/{self.test_meeting_id_1}/transcript")
        self.assertEqual(res_tr.status_code, 200)
        tr_body = res_tr.json()
        self.assertEqual(tr_body["meeting_id"], self.test_meeting_id_1)
        self.assertIn("knowledge repository", tr_body["transcript"])

        # 4. GET /meetings/{meeting_id}/action-items
        res_act = self.client.get(f"/meetings/{self.test_meeting_id_1}/action-items")
        self.assertEqual(res_act.status_code, 200)
        act_body = res_act.json()
        self.assertEqual(act_body["count"], 2)

        # 5. GET /stats
        res_stats = self.client.get("/stats")
        self.assertEqual(res_stats.status_code, 200)
        self.assertIn("total_meetings", res_stats.json()["stats"])


if __name__ == "__main__":
    unittest.main()
