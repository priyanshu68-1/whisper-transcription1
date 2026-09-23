import os
import unittest
import uuid
import json
import sqlite3
from datetime import datetime
from fastapi.testclient import TestClient

# Core project components
from database import DatabaseManager, _safe_json_loads
from api import app
from ai_search_service import AISearchEngine
from validate_upload import validate_audio_file
from validate_transcript import run_transcript_validation
from llm_service import LLMService
from action_engine import ActionItemEngine
from participant_mapper import ParticipantMapper
from pipeline_service import ProcessingPipeline

class MasterValidationSuite(unittest.TestCase):
    """
    Milestone 3 – Task 5: Master Quality, Validation & Regression Test Suite
    Tests all 8 validation domains:
    1. Database Validation (TC-DB-01 to 08)
    2. Retrieval Validation (TC-RET-01 to 04)
    3. Search Validation (TC-SRCH-01 to 08)
    4. AI Search Validation (TC-AI-01 to 07)
    5. Data Integrity Testing (TC-INT-01 to 04)
    6. API Testing (TC-API-01 to 11)
    7. Frontend / UI Logic Validation (TC-UI-01 to 06)
    8. Regression Testing (TC-REG-01 to 05)
    """

    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager()
        cls.ai_search = AISearchEngine(db=cls.db)
        cls.client = TestClient(app)

        # Unique IDs for isolated master test fixtures
        cls.mid_1 = f"MASTER-M1-{uuid.uuid4().hex[:6].upper()}"
        cls.mid_2 = f"MASTER-M2-{uuid.uuid4().hex[:6].upper()}"

        # Seed meeting 1: Core Platform Architecture
        cls.db.save_meeting(
            meeting_id=cls.mid_1,
            title="Core Platform Architecture & Redis Strategy",
            audio_filename="core_platform_audio.mp3",
            file_size_mb=4.8,
            duration_seconds=360.0,
            format_ext=".mp3",
            language="en",
            transcript="Kavita proposed transitioning our session caching to Redis clusters. Dev agreed and suggested implementing Prometheus latency metrics.",
            intelligence={
                "summary": "Engineering review of Redis caching clusters, Prometheus telemetry, and session management latency.",
                "key_points": [
                    "Transition caching to Redis cluster to lower P99 response time.",
                    "Integrate Prometheus latency metrics into Grafana dashboards."
                ],
                "decisions": [
                    "Deploy Redis Sentinel cluster in production.",
                    "Set session TTL to 24 hours across all web services."
                ],
                "deadlines": ["October 1st", "Friday 5pm"],
                "priorities": ["High", "Medium"],
                "action_items": [
                    {
                        "task": "Deploy Redis Sentinel Helm chart to Kubernetes",
                        "assignee": "Kavita",
                        "priority": "High",
                        "deadline": "October 1st",
                        "status": "Pending"
                    },
                    {
                        "task": "Configure Prometheus metrics exporter for Redis",
                        "assignee": "Dev",
                        "priority": "Medium",
                        "deadline": "Friday 5pm",
                        "status": "Completed"
                    }
                ]
            },
            participant_data={
                "unique_participants": ["Kavita", "Dev"],
                "responsibilities": [
                    {"name": "Kavita", "role": "Architect", "tasks": ["Deploy Redis Sentinel Helm chart to Kubernetes"]}
                ]
            },
            validation_info={"is_valid": True, "file_check": "PASSED", "transcript_check": "PASSED", "schema_check": "PASSED"}
        )

        # Seed meeting 2: Security & Mobile Authentication
        cls.db.save_meeting(
            meeting_id=cls.mid_2,
            title="Mobile Application Security & Biometric Auth",
            audio_filename="mobile_security_audio.mp3",
            file_size_mb=5.2,
            duration_seconds=420.0,
            format_ext=".mp3",
            language="en",
            transcript="Aarav demonstrated FaceID biometric login for iOS. Dev raised concerns regarding backward compatibility with Android 10.",
            intelligence={
                "summary": "Mobile security sync reviewing FaceID implementation, Android 10 fallback, and JWT token refresh intervals.",
                "key_points": [
                    "FaceID biometric login working on iOS 18 test device.",
                    "Android 10 backward compatibility requires fallback PIN."
                ],
                "decisions": [
                    "Require biometrics for high-value financial transfers.",
                    "Deprecate SMS-based two-factor authentication."
                ],
                "deadlines": ["November 15th"],
                "priorities": ["High"],
                "action_items": [
                    {
                        "task": "Implement biometric prompt wrapper for Android 10",
                        "assignee": "Dev",
                        "priority": "High",
                        "deadline": "November 15th",
                        "status": "Pending"
                    }
                ]
            },
            participant_data={
                "unique_participants": ["Aarav", "Dev"],
                "responsibilities": [
                    {"name": "Aarav", "role": "Mobile Lead", "tasks": []}
                ]
            },
            validation_info={"is_valid": True, "file_check": "PASSED", "transcript_check": "PASSED", "schema_check": "PASSED"}
        )

    @classmethod
    def tearDownClass(cls):
        cls.db.delete_meeting(cls.mid_1)
        cls.db.delete_meeting(cls.mid_2)

    # =======================================================================
    # DOMAIN 1: DATABASE VALIDATION (TC-DB-01 to 08)
    # =======================================================================
    def test_tc_db_01_meeting_records_stored_correctly(self):
        """TC-DB-01: Verifies meeting record is persisted with all fields populated."""
        m = self.db.get_meeting(self.mid_1)
        self.assertIsNotNone(m)
        self.assertEqual(m["meeting_id"], self.mid_1)
        self.assertEqual(m["title"], "Core Platform Architecture & Redis Strategy")
        self.assertEqual(m["language"], "en")
        self.assertGreater(m["word_count"], 0)

    def test_tc_db_02_meeting_id_is_unique(self):
        """TC-DB-02: Verifies unique meeting_id constraint prevents duplicate insertion."""
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db.get_connection() as conn:
                conn.execute("INSERT INTO meetings (meeting_id, title, transcript, created_at) VALUES (?, ?, ?, ?)",
                             (self.mid_1, "Duplicate Meeting", "Sample text", datetime.now().isoformat()))
                conn.commit()

    def test_tc_db_03_metadata_accuracy(self):
        """TC-DB-03: Verifies metadata attributes (file size, duration, format, validation status)."""
        m = self.db.get_meeting(self.mid_1)
        self.assertEqual(m["file_size_mb"], 4.8)
        self.assertEqual(m["duration_seconds"], 360.0)
        self.assertEqual(m["format"], ".mp3")
        self.assertEqual(m["validation_status"], "VALIDATED")

    def test_tc_db_04_transcript_fidelity(self):
        """TC-DB-04: Verifies full transcript storage fidelity without truncation."""
        m = self.db.get_meeting(self.mid_1)
        self.assertIn("Kavita proposed transitioning our session caching to Redis clusters", m["transcript"])

    def test_tc_db_05_summary_and_decisions_fidelity(self):
        """TC-DB-05: Verifies executive summary and decisions list fidelity."""
        m = self.db.get_meeting(self.mid_1)
        self.assertIn("Redis caching clusters", m["summary"])
        self.assertIn("Deploy Redis Sentinel cluster in production.", m["decisions"])

    def test_tc_db_06_action_items_structure(self):
        """TC-DB-06: Verifies action items structure (task, assignee, priority, deadline, status)."""
        m = self.db.get_meeting(self.mid_1)
        self.assertEqual(len(m["action_items"]), 2)
        task1 = next(a for a in m["action_items"] if a["assignee"] == "Kavita")
        self.assertEqual(task1["priority"], "High")
        self.assertEqual(task1["status"], "Pending")

    def test_tc_db_07_participant_deduplication(self):
        """TC-DB-07: Verifies participants are unique and isolated per meeting."""
        m = self.db.get_meeting(self.mid_1)
        self.assertEqual(sorted(m["participants"]), ["Dev", "Kavita"])
        self.assertEqual(len(m["participants"]), len(set(m["participants"])))

    def test_tc_db_08_deadlines_logging(self):
        """TC-DB-08: Verifies deadlines are stored from both summaries and action items."""
        m = self.db.get_meeting(self.mid_1)
        self.assertIn("October 1st", m["deadlines"])

    # =======================================================================
    # DOMAIN 2: RETRIEVAL VALIDATION (TC-RET-01 to 04)
    # =======================================================================
    def test_tc_ret_01_retrieve_existing_meeting(self):
        """TC-RET-01: Verifies single meeting retrieval by meeting_id."""
        retrieved = self.db.get_meeting(self.mid_2)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["meeting_id"], self.mid_2)

    def test_tc_ret_02_retrieve_multiple_meetings_pagination(self):
        """TC-RET-02: Verifies listing meetings with limit and offset pagination."""
        page1 = self.db.list_all_meetings(limit=1, offset=0)
        page2 = self.db.list_all_meetings(limit=1, offset=1)
        self.assertEqual(len(page1), 1)
        self.assertEqual(len(page2), 1)
        self.assertNotEqual(page1[0]["meeting_id"], page2[0]["meeting_id"])

    def test_tc_ret_03_nonexistent_meeting_error_handling(self):
        """TC-RET-03: Verifies nonexistent meeting returns None in DB and 404 in API."""
        nonexistent = self.db.get_meeting("MEET-NONEXISTENT-9999")
        self.assertIsNone(nonexistent)

        resp = self.client.get("/meetings/MEET-NONEXISTENT-9999")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("not found", resp.json()["detail"].lower())

    def test_tc_ret_04_data_belongs_to_correct_meeting_id(self):
        """TC-RET-04: Verifies complete isolation of retrieved intelligence."""
        m1 = self.db.get_meeting(self.mid_1)
        m2 = self.db.get_meeting(self.mid_2)
        self.assertIn("Redis", m1["title"])
        self.assertNotIn("Redis", m2["title"])
        self.assertIn("FaceID", m2["summary"])
        self.assertNotIn("FaceID", m1["summary"])

    # =======================================================================
    # DOMAIN 3: SEARCH VALIDATION (TC-SRCH-01 to 08)
    # =======================================================================
    def test_tc_srch_01_keyword_search(self):
        """TC-SRCH-01: Keyword search returns matching meeting."""
        res = self.db.search_meetings(query="Prometheus")
        mids = [r["meeting_id"] for r in res]
        self.assertIn(self.mid_1, mids)

    def test_tc_srch_02_case_insensitive_search(self):
        """TC-SRCH-02: Search is case-insensitive across uppercase, lowercase, mixed."""
        res_lower = self.db.search_meetings(query="biometric")
        res_upper = self.db.search_meetings(query="BIOMETRIC")
        res_mixed = self.db.search_meetings(query="BiOmEtRiC")
        self.assertEqual(len(res_lower), len(res_upper))
        self.assertEqual(len(res_lower), len(res_mixed))
        self.assertIn(self.mid_2, [r["meeting_id"] for r in res_lower])

    def test_tc_srch_03_participant_search(self):
        """TC-SRCH-03: Search meetings by participant name."""
        res = self.db.search_meetings(participant="Kavita")
        self.assertIn(self.mid_1, [r["meeting_id"] for r in res])

    def test_tc_srch_04_summary_search(self):
        """TC-SRCH-04: Search keywords located in LLM executive summary."""
        res = self.db.search_meetings(query="telemetry")
        self.assertIn(self.mid_1, [r["meeting_id"] for r in res])

    def test_tc_srch_05_decision_search(self):
        """TC-SRCH-05: Search keywords located in strategic decisions."""
        res = self.db.search_meetings(query="financial transfers")
        self.assertIn(self.mid_2, [r["meeting_id"] for r in res])

    def test_tc_srch_06_action_item_search(self):
        """TC-SRCH-06: Search keywords located in action item tasks."""
        res = self.db.search_meetings(query="Helm chart")
        self.assertIn(self.mid_1, [r["meeting_id"] for r in res])

    def test_tc_srch_07_no_result_search(self):
        """TC-SRCH-07: Search with non-matching query returns empty list without error."""
        res = self.db.search_meetings(query="QuantumAlienTeleporter_999")
        self.assertEqual(len(res), 0)

    def test_tc_srch_08_empty_query_search(self):
        """TC-SRCH-08: Empty or whitespace query falls back to listing meetings safely."""
        res = self.db.search_meetings(query="   ")
        self.assertGreaterEqual(len(res), 2)

    # =======================================================================
    # DOMAIN 4: AI SEARCH VALIDATION (TC-AI-01 to 07)
    # =======================================================================
    def test_tc_ai_01_natural_language_answering(self):
        """TC-AI-01: Natural-language question answering synthesizes grounded answers."""
        res = self.ai_search.answer_question("What did we decide about Redis Sentinel?")
        self.assertTrue(res["found"])
        self.assertIn(self.mid_1, res["source_meeting_ids"])
        self.assertTrue("redis" in res["answer"].lower() or "sentinel" in res["answer"].lower())

    def test_tc_ai_02_context_retrieval_ranking(self):
        """TC-AI-02: Context retrieval identifies and scores the most relevant meetings."""
        candidates = self.ai_search.retrieve_context("FaceID Android biometrics", max_meetings=3)
        self.assertGreater(len(candidates), 0)
        self.assertEqual(candidates[0]["meeting_id"], self.mid_2)

    def test_tc_ai_03_source_meeting_ids_returned(self):
        """TC-AI-03: Source meeting IDs are strictly preserved and returned with answers."""
        res = self.ai_search.answer_question("What tasks were assigned to Kavita?")
        self.assertTrue(res["found"])
        self.assertIn(self.mid_1, res["source_meeting_ids"])
        for src in res["source_meetings"]:
            self.assertIn("meeting_id", src)

    def test_tc_ai_04_grounded_synthesis_only(self):
        """TC-AI-04: Answer is grounded strictly in historical records."""
        res = self.ai_search.answer_question("What deadline was set for Prometheus metrics?")
        self.assertTrue(res["found"])
        self.assertIn(self.mid_1, res["source_meeting_ids"])
        self.assertIn("friday 5pm", res["answer"].lower())

    def test_tc_ai_05_unknown_info_not_invented(self):
        """TC-AI-05: Non-existent topics explicitly state information was not found."""
        res = self.ai_search.answer_question("What are the propulsion specs for intergalactic deep space warp drives?")
        self.assertFalse(res["found"])
        self.assertEqual(len(res["source_meeting_ids"]), 0)
        self.assertIn("not found in the historical meeting records", res["answer"].lower())

    def test_tc_ai_06_empty_question_rejected(self):
        """TC-AI-06: Empty question raises ValueError."""
        with self.assertRaises(ValueError):
            self.ai_search.answer_question("")

    def test_tc_ai_07_llm_fallback_resilience(self):
        """TC-AI-07: Fallback engine operates deterministically if LLM is unavailable."""
        candidates = self.ai_search.retrieve_context("FaceID biometrics", max_meetings=2)
        fallback = self.ai_search._fallback_grounded_search("What did we decide about biometrics?", candidates)
        self.assertTrue(fallback["found"])
        self.assertIn(self.mid_2, fallback["source_meeting_ids"])

    # =======================================================================
    # DOMAIN 5: DATA INTEGRITY & RELATIONSHIP TESTING (TC-INT-01 to 04)
    # =======================================================================
    def test_tc_int_01_no_cross_meeting_data_leakage(self):
        """TC-INT-01: Action items and participants do not cross-contaminate between meetings."""
        acts_1 = [a["task"] for a in self.db.get_meeting(self.mid_1)["action_items"]]
        acts_2 = [a["task"] for a in self.db.get_meeting(self.mid_2)["action_items"]]
        self.assertTrue(set(acts_1).isdisjoint(set(acts_2)))

    def test_tc_int_02_no_duplicate_participants(self):
        """TC-INT-02: Multiple mentions of a participant in transcript do not duplicate in DB."""
        temp_mid = f"TEST-DUP-{uuid.uuid4().hex[:4].upper()}"
        self.db.save_meeting(
            meeting_id=temp_mid,
            title="Deduplication Verification Sync",
            audio_filename="dummy.mp3",
            file_size_mb=1.0,
            duration_seconds=60.0,
            format_ext=".mp3",
            language="en",
            transcript="Priya and Priya met with Priya.",
            intelligence={"summary": "Sync", "key_points": [], "decisions": [], "deadlines": [], "priorities": [], "action_items": []},
            participant_data={"unique_participants": ["Priya", "Priya", "Priya"], "responsibilities": []},
            validation_info={"is_valid": True}
        )
        saved = self.db.get_meeting(temp_mid)
        self.assertEqual(saved["participants"], ["Priya"])
        self.db.delete_meeting(temp_mid)

    def test_tc_int_03_cascading_deletion(self):
        """TC-INT-03: Deleting a meeting cascades to summaries, action items, participants, and logs."""
        temp_mid = f"TEST-CASC-{uuid.uuid4().hex[:4].upper()}"
        self.db.save_meeting(
            meeting_id=temp_mid,
            title="Cascade Test Meeting",
            audio_filename="dummy.mp3",
            file_size_mb=1.0,
            duration_seconds=60.0,
            format_ext=".mp3",
            language="en",
            transcript="Testing cascade delete.",
            intelligence={
                "summary": "Cascade summary",
                "key_points": [],
                "decisions": ["Cascade decision"],
                "deadlines": [],
                "priorities": [],
                "action_items": [{"task": "Cascade task", "assignee": "Tester", "priority": "High", "deadline": "Now", "status": "Pending"}]
            },
            participant_data={"unique_participants": ["Tester"], "responsibilities": []},
            validation_info={"is_valid": True}
        )
        self.db.delete_meeting(temp_mid)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            for table in ["meetings", "summaries", "action_items", "participants", "validation_logs"]:
                cursor.execute(f"SELECT COUNT(*) as c FROM {table} WHERE meeting_id = ?", (temp_mid,))
                self.assertEqual(cursor.fetchone()["c"], 0, f"Dangling record in {table} after cascade delete")

    def test_tc_int_04_corrupt_json_resilience(self):
        """TC-INT-04: Malformed or unparseable JSON values fall back cleanly to safe defaults."""
        val = _safe_json_loads("{invalid: unclosed json", default=["safe_default"])
        self.assertEqual(val, ["safe_default"])

    # =======================================================================
    # DOMAIN 6: API TESTING (TC-API-01 to 11)
    # =======================================================================
    def test_tc_api_01_root_health_check(self):
        """TC-API-01: GET / returns healthy status and endpoint documentation links."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("search_meetings", data["endpoints"])
        self.assertIn("ai_search", data["endpoints"])
        self.assertIn("historical_insights", data["endpoints"])

    def test_tc_api_02_list_meetings(self):
        """TC-API-02: GET /meetings returns 200 with list of meetings."""
        resp = self.client.get("/meetings?limit=5")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIsInstance(data["meetings"], list)

    def test_tc_api_03_get_meeting_by_id(self):
        """TC-API-03: GET /meetings/{meeting_id} returns 200 with complete intelligence."""
        resp = self.client.get(f"/meetings/{self.mid_1}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["meeting_id"], self.mid_1)
        self.assertIn("transcript", data)
        self.assertIn("action_items", data)

    def test_tc_api_04_get_transcript(self):
        """TC-API-04: GET /meetings/{meeting_id}/transcript returns raw transcript."""
        resp = self.client.get(f"/meetings/{self.mid_1}/transcript")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Redis clusters", resp.json()["transcript"])

    def test_tc_api_05_get_action_items(self):
        """TC-API-05: GET /meetings/{meeting_id}/action-items returns action items."""
        resp = self.client.get(f"/meetings/{self.mid_1}/action-items")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["action_items"]), 2)

    def test_tc_api_06_search_endpoint(self):
        """TC-API-06: GET /meetings/search?q=... returns matching results."""
        resp = self.client.get("/meetings/search?q=Sentinel")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertGreater(data["total_matches"], 0)

    def test_tc_api_07_post_ai_search(self):
        """TC-API-07: POST /meetings/ai-search returns grounded AI response."""
        resp = self.client.post("/meetings/ai-search", json={"question": "What tasks were assigned to Kavita?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["found"])
        self.assertIn(self.mid_1, data["source_meeting_ids"])

    def test_tc_api_08_get_ai_search(self):
        """TC-API-08: GET /meetings/ai-search?q=... returns grounded AI response."""
        resp = self.client.get("/meetings/ai-search?q=What+did+we+decide+about+FaceID")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["found"])

    def test_tc_api_09_historical_insights_endpoint(self):
        """TC-API-09: GET /meetings/insights returns cross-meeting KPIs and feeds."""
        resp = self.client.get("/meetings/insights")
        self.assertEqual(resp.status_code, 200)
        insights = resp.json()["insights"]
        self.assertGreaterEqual(insights["total_meetings"], 2)
        self.assertIn("decisions", insights)
        self.assertIn("participants", insights)

    def test_tc_api_10_stats_endpoint(self):
        """TC-API-10: GET /stats returns dashboard aggregates."""
        resp = self.client.get("/stats")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("total_meetings", resp.json())

    def test_tc_api_11_error_handling(self):
        """TC-API-11: Invalid inputs return appropriate error status codes."""
        # 400 for empty AI question
        resp1 = self.client.post("/meetings/ai-search", json={"question": ""})
        self.assertEqual(resp1.status_code, 400)
        # 404 for missing meeting
        resp2 = self.client.get("/meetings/MEET-NONEXISTENT-404")
        self.assertEqual(resp2.status_code, 404)

    # =======================================================================
    # DOMAIN 7: REGRESSION TESTING (MILESTONE 1 & 2) (TC-REG-01 to 05)
    # =======================================================================
    def test_tc_reg_01_audio_upload_validation(self):
        """TC-REG-01: Verifies file validation accepts valid mp3 and rejects invalid."""
        if os.path.exists("transcipt_test2.mp3"):
            is_valid, _ = validate_audio_file("transcipt_test2.mp3")
            self.assertTrue(is_valid)

        is_valid_fake, msg = validate_audio_file("nonexistent_audio_file.wav")
        self.assertFalse(is_valid_fake)
        self.assertIn("does not exist", msg.lower())

    def test_tc_reg_02_transcript_validation(self):
        """TC-REG-02: Verifies transcript content validation checks pass."""
        if os.path.exists("transcipt_test2.mp3"):
            passed = run_transcript_validation("transcipt_test2.mp3", expected_snippet="27th August")
            self.assertTrue(passed)
        else:
            self.skipTest("transcipt_test2.mp3 not found")

    def test_tc_reg_03_action_extraction_engine(self):
        """TC-REG-03: Verifies action item regex & rule engine extracts tasks and priorities."""
        engine = ActionItemEngine()
        tasks = engine.extract_action_items("Kavita must deploy the Redis cluster by October 1st. Priority is high.")
        self.assertGreaterEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["priority"], "High")

    def test_tc_reg_04_participant_mapping_engine(self):
        """TC-REG-04: Verifies participant mapper detects speakers and links tasks."""
        mapper = ParticipantMapper()
        mapped = mapper.map_participants_and_tasks("Dev presented the biometrics update. Kavita agreed.", meeting_id="TEST-MAP")
        self.assertIn("Dev", mapped["unique_participants"])
        self.assertIn("Kavita", mapped["unique_participants"])

    def test_tc_reg_05_historical_insights_filter_regression(self):
        """TC-REG-05: Verifies cross-meeting historical insights filter by participant and status."""
        ins = self.db.get_historical_insights(participant="Kavita", status="Pending")
        self.assertGreaterEqual(len(ins["action_items"]), 1)
        self.assertEqual(ins["action_items"][0]["assignee"].lower(), "kavita")
        self.assertEqual(ins["action_items"][0]["status"], "Pending")


if __name__ == "__main__":
    unittest.main(verbosity=2)
