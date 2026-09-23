"""
Milestone 3 – Task 9: End-to-End Integration Testing Suite
Tests the complete application workflow:
User -> Authentication -> API -> Meeting Data -> Database -> Embedding/Semantic Search
-> Relevant Retrieval -> RAG Context -> LLM -> Grounded Answer -> Source Meeting IDs -> Frontend.

Verifies zero manual database intervention is required.
"""

import os
import sys
import time
import json
import uuid
import unittest
import logging
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from database import DatabaseManager
from ai_search_service import AISearchEngine
from pipeline_service import ProcessingPipeline
from api import app
import api


class TestEndToEndIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager()
        cls.engine = AISearchEngine(db=cls.db)
        cls.client = TestClient(app)

        cls.auth_token = os.environ.get("API_AUTH_TOKEN", "truthshield-secret-token-2026")
        cls.bearer_headers = {"Authorization": f"Bearer {cls.auth_token}"}
        cls.api_key_headers = {"X-API-Key": cls.auth_token}

        cls.created_mids = []

        # 1. Full Real Audio Pipeline Ingestion (transcipt_test2.mp3)
        cls.audio_file = "transcipt_test2.mp3"
        cls.mid_audio = f"E2E-AUDIO-{uuid.uuid4().hex[:6].upper()}"
        cls.created_mids.append(cls.mid_audio)

        pipeline = ProcessingPipeline(model_size="base")
        success, data, msg = pipeline.run_full_pipeline(
            audio_file_path=cls.audio_file,
            meeting_title="Sprint 14 Executive Planning Sync",
            custom_meeting_id=cls.mid_audio
        )
        if not success:
            raise RuntimeError(f"Pipeline audio ingestion failed: {msg}")

        # 2. Seed Historical Meeting 1: Mobile Architecture (Priya)
        cls.mid_mobile = f"E2E-MOB-{uuid.uuid4().hex[:6].upper()}"
        cls.created_mids.append(cls.mid_mobile)
        cls.db.save_meeting(
            meeting_id=cls.mid_mobile,
            title="Mobile Application Architecture & UI Review",
            audio_filename="mobile_sync.mp3",
            file_size_mb=6.4,
            duration_seconds=420.0,
            format_ext=".MP3",
            language="EN",
            transcript="Priya presented the Flutter mobile architecture. The team decided to adopt React Native for cross-platform modules.",
            intelligence={
                "summary": "Engineering sync reviewing mobile architecture and cross-platform framework selection.",
                "key_points": [
                    "Priya completed initial UI testing on iOS 18 devices.",
                    "Selected React Native for cross-platform modules."
                ],
                "decisions": ["Adopt React Native for cross-platform mobile client."],
                "deadlines": ["October 25th"],
                "priorities": ["High"],
                "action_items": [
                    {
                        "task": "Deliver end-to-end UI testing report for iOS 18",
                        "assignee": "Priya",
                        "priority": "High",
                        "deadline": "October 25th",
                        "status": "In Progress"
                    }
                ]
            },
            participant_data={"unique_participants": ["Priya"], "responsibilities": []},
            validation_info={"is_valid": True}
        )

        # 3. Seed Historical Meeting 2: Backend API (Vikram)
        cls.mid_api = f"E2E-API-{uuid.uuid4().hex[:6].upper()}"
        cls.created_mids.append(cls.mid_api)
        cls.db.save_meeting(
            meeting_id=cls.mid_api,
            title="Stripe Payment Gateway Integration Review",
            audio_filename="api_sync.wav",
            file_size_mb=4.1,
            duration_seconds=300.0,
            format_ext=".WAV",
            language="EN",
            transcript="Vikram summarized the status of Stripe payment webhooks. Staging deployment succeeded with latency under 100ms.",
            intelligence={
                "summary": "Core backend sync focused on Stripe webhook integration and OAuth2 token rotation.",
                "key_points": [
                    "Stripe API integration completed on staging environment.",
                    "Webhook response time is now under 100ms."
                ],
                "decisions": ["Enforce OAuth2 refresh token rotation."],
                "deadlines": ["November 10th"],
                "priorities": ["High"],
                "action_items": [
                    {
                        "task": "Finalize OAuth2 refresh token rotation in staging",
                        "assignee": "Vikram",
                        "priority": "High",
                        "deadline": "November 10th",
                        "status": "In Progress"
                    }
                ]
            },
            participant_data={"unique_participants": ["Vikram"], "responsibilities": []},
            validation_info={"is_valid": True}
        )

    @classmethod
    def tearDownClass(cls):
        for mid in cls.created_mids:
            try:
                cls.db.delete_meeting(mid)
            except Exception:
                pass

    # =======================================================================
    # 1. AUTHENTICATED USER ACCESS
    # =======================================================================
    def test_e2e_01_authenticated_user_access(self):
        """E2E-01: Authenticated user accesses protected meeting endpoints via Bearer token and X-API-Key."""
        # Test Bearer token
        resp_bearer = self.client.post("/ask", json={"question": "What did Priya work on?"}, headers=self.bearer_headers)
        self.assertEqual(resp_bearer.status_code, 200)
        self.assertTrue(resp_bearer.json().get("success"))

        # Test X-API-Key
        resp_key = self.client.post("/ask", json={"question": "What was the API integration status?"}, headers=self.api_key_headers)
        self.assertEqual(resp_key.status_code, 200)
        self.assertTrue(resp_key.json().get("success"))

    # =======================================================================
    # 2. RETRIEVE EXISTING MEETINGS (/meetings)
    # =======================================================================
    def test_e2e_02_retrieve_meetings_endpoint(self):
        """E2E-02: Retrieve existing meetings list via GET /meetings with pagination."""
        resp = self.client.get("/meetings?limit=5&offset=0")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("meetings", data)
        self.assertGreaterEqual(data["total"], 3)
        mids = [m["meeting_id"] for m in data["meetings"]]
        self.assertIn(self.mid_mobile, mids)
        self.assertIn(self.mid_api, mids)

    # =======================================================================
    # 3. RETRIEVE SINGLE MEETING (/meetings/{id})
    # =======================================================================
    def test_e2e_03_retrieve_single_meeting_endpoint(self):
        """E2E-03: Retrieve complete structured intelligence for single meeting via GET /meetings/{id}."""
        resp = self.client.get(f"/meetings/{self.mid_mobile}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["meeting_id"], self.mid_mobile)
        self.assertEqual(data["title"], "Mobile Application Architecture & UI Review")
        self.assertIn("Flutter", data["transcript"])
        self.assertIn("React Native", str(data.get("decisions", [])))
        self.assertTrue(len(data.get("action_items", [])) > 0)
        self.assertEqual(data["action_items"][0]["assignee"], "Priya")

    # =======================================================================
    # 4. KEYWORD & SEMANTIC SEARCH (/search)
    # =======================================================================
    def test_e2e_04_search_endpoint_keyword_and_semantic(self):
        """E2E-04: Perform keyword and semantic search via GET and POST /search."""
        # Keyword GET search
        resp_get = self.client.get("/search?q=Priya")
        self.assertEqual(resp_get.status_code, 200)
        data_get = resp_get.json()
        self.assertGreaterEqual(data_get["total_matches"], 1)
        self.assertTrue(any(m["meeting_id"] == self.mid_mobile for m in data_get["results"]))

        # Semantic POST search
        resp_post = self.client.post("/search", json={"query": "Stripe payment webhook staging", "semantic": True})
        self.assertEqual(resp_post.status_code, 200)
        data_post = resp_post.json()
        self.assertGreaterEqual(data_post["total_matches"], 1)
        self.assertTrue(any(m["meeting_id"] == self.mid_api for m in data_post["results"]))

    # =======================================================================
    # 5. ASK HISTORICAL MEETING QUESTION (/ask)
    # =======================================================================
    def test_e2e_05_ask_historical_question(self):
        """E2E-05: Ask natural language question about historical meetings via POST /ask."""
        payload = {"question": "What decisions were made regarding the mobile application?"}
        resp = self.client.post("/ask", json=payload, headers=self.bearer_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("found"))
        self.assertIn(self.mid_mobile, data.get("source_meeting_ids", []))
        self.assertIn("React Native", data.get("answer", ""))

    # =======================================================================
    # 6. VERIFY RETRIEVED MEETING IDS
    # =======================================================================
    def test_e2e_06_verify_retrieved_meeting_ids(self):
        """E2E-06: Verify returned source_meeting_ids accurately point to the evidence-holding meeting."""
        resp = self.client.post("/ask", json={"question": "What tasks were assigned to Vikram?"}, headers=self.bearer_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("found"))
        self.assertIn(self.mid_api, data.get("source_meeting_ids", []))
        self.assertNotIn(self.mid_mobile, data.get("source_meeting_ids", []))

    # =======================================================================
    # 7. VERIFY RETRIEVED CONTEXT
    # =======================================================================
    def test_e2e_07_verify_retrieved_context_isolation(self):
        """E2E-07: Verify retrieved context blocks contain only relevant meeting records."""
        meetings = self.engine.retrieve_context("Priya iOS 18 UI testing", max_meetings=3)
        context_str = self.engine.build_prompt_context(meetings)
        self.assertIn(self.mid_mobile, context_str)
        self.assertNotIn(self.mid_api, context_str)

    # =======================================================================
    # 8. VERIFY GROUNDED ANSWER WITHOUT HALLUCINATION
    # =======================================================================
    def test_e2e_08_verify_grounded_answer(self):
        """E2E-08: Verify synthesized answer contains strictly grounded facts and does not invent participants or dates."""
        resp = self.client.post("/ask", json={"question": "Who was responsible for UI testing on iOS 18?"}, headers=self.bearer_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("found"))
        ans = data.get("answer", "")
        self.assertIn("Priya", ans)
        for fake in ["Alice", "Bob", "Charlie", "Musk", "Zuckerberg"]:
            self.assertNotIn(fake, ans)

    # =======================================================================
    # 9. VERIFY UNKNOWN QUESTIONS
    # =======================================================================
    def test_e2e_09_unknown_questions_safety(self):
        """E2E-09: Unrecorded query returns found=False with clear 'information not found' answer."""
        resp = self.client.post("/ask", json={"question": "What was the hyperdrive warp core status?"}, headers=self.bearer_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get("found"))
        self.assertEqual(len(data.get("source_meeting_ids", [])), 0)
        self.assertIn("not found in the historical meeting records", data.get("answer", "").lower())

    # =======================================================================
    # 10. VERIFY AUTHENTICATION ENFORCEMENT
    # =======================================================================
    def test_e2e_10_authentication_enforcement(self):
        """E2E-10: Unauthorized calls without token or with invalid tokens are strictly rejected with 401."""
        # Missing auth
        r1 = self.client.post("/ask", json={"question": "What are our deadlines?"})
        self.assertEqual(r1.status_code, 401)

        # Invalid Bearer token
        r2 = self.client.post("/ask", json={"question": "What are our deadlines?"}, headers={"Authorization": "Bearer BAD_TOKEN_999"})
        self.assertEqual(r2.status_code, 401)

        # Invalid X-API-Key
        r3 = self.client.post("/ask", json={"question": "What are our deadlines?"}, headers={"X-API-Key": "BAD_API_KEY"})
        self.assertEqual(r3.status_code, 401)

    # =======================================================================
    # 11. VERIFY DATABASE PERSISTENCE WITHOUT MANUAL INTERVENTION
    # =======================================================================
    def test_e2e_11_database_persistence(self):
        """E2E-11: Verify meeting ingested through pipeline is persisted in SQLite with all foreign keys."""
        meeting = self.db.get_meeting(self.mid_audio)
        self.assertIsNotNone(meeting, "Pipeline-processed meeting must be persisted in database")
        self.assertEqual(meeting["meeting_id"], self.mid_audio)
        self.assertIn("27th August", meeting["transcript"])
        self.assertGreater(meeting["duration_seconds"], 0.0)

        # Verify linked SQLite tables
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT summary_text FROM summaries WHERE meeting_id = ?", (self.mid_audio,))
            s_row = cur.fetchone()
            self.assertIsNotNone(s_row)

            cur.execute("SELECT participant_name FROM participants WHERE meeting_id = ?", (self.mid_audio,))
            p_rows = cur.fetchall()
            self.assertGreaterEqual(len(p_rows), 1)

    # =======================================================================
    # 12. VERIFY VECTOR / EMBEDDING RETRIEVAL
    # =======================================================================
    def test_e2e_12_vector_embedding_retrieval(self):
        """E2E-12: Semantic search retrieves candidate meetings correctly without manual query tuning."""
        results = self.engine.semantic_search("React Native cross-platform client", limit=3)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["meeting_id"], self.mid_mobile)

    # =======================================================================
    # 13. VERIFY ERROR HANDLING
    # =======================================================================
    def test_e2e_13_error_handling(self):
        """E2E-13: Validate HTTP 400 on empty question, 404 on missing meeting, and structured JSON responses."""
        # Empty question
        r_bad = self.client.post("/ask", json={"question": ""}, headers=self.bearer_headers)
        self.assertEqual(r_bad.status_code, 400)
        self.assertIn("empty or whitespace", r_bad.json().get("detail", "").lower())

        # Missing meeting ID
        r_notfound = self.client.get("/meetings/MEET-NONEXISTENT-E2E-000")
        self.assertEqual(r_notfound.status_code, 404)
        self.assertIn("not found", r_notfound.json().get("detail", "").lower())

    # =======================================================================
    # 14. VERIFY LOGGING
    # =======================================================================
    def test_e2e_14_logging(self):
        """E2E-14: Verify system operations write to standard application loggers."""
        with self.assertLogs("whisper_meetings.api", level="INFO") as log_api:
            _ = self.client.get("/meetings?limit=1")
            self.assertTrue(any("Listing all meetings" in m for m in log_api.output))

        with self.assertLogs("whisper_meetings.ai_search", level="INFO") as log_ai:
            _ = self.engine.answer_question("Priya?")
            self.assertTrue(any("Processing AI Search question" in m for m in log_ai.output))

    # =======================================================================
    # 15. VERIFY STREAMLIT FRONTEND INTEGRATION
    # =======================================================================
    def test_e2e_15_streamlit_frontend_integration(self):
        """E2E-15: Verify Streamlit app.py resources and data contracts execute cleanly."""
        # Test 1: Validate import and initialization of get_db() and get_ai_search()
        from app import get_db, get_ai_search
        db_inst = get_db()
        self.assertIsInstance(db_inst, DatabaseManager)
        ai_inst = get_ai_search()
        self.assertIsInstance(ai_inst, AISearchEngine)

        # Test 2: Verify answer_question output structure satisfies Streamlit UI display cards
        res = ai_inst.answer_question("What was decided about the mobile application?")
        self.assertIn("found", res)
        self.assertIn("answer", res)
        self.assertIn("source_meeting_ids", res)
        self.assertIn("source_meetings", res)
        self.assertIn("key_findings", res)

        # Check source_meetings format consumed by Streamlit expanders in app.py:1735-1750
        self.assertTrue(len(res["source_meetings"]) > 0)
        sm = res["source_meetings"][0]
        for field in ["meeting_id", "title", "created_at", "summary", "decisions", "action_items"]:
            self.assertIn(field, sm)

        # Test 3: Verify get_historical_insights structure consumed by Streamlit charts in app.py:720-960
        insights = db_inst.get_historical_insights()
        self.assertIn("total_meetings", insights)
        self.assertIn("total_action_items", insights)
        self.assertIn("decisions", insights)
        self.assertIn("participants", insights)
        self.assertIn("deadlines", insights)
        self.assertIn("project_history", insights)

    # =======================================================================
    # 16. MILESTONE 1 & 2 REGRESSION TESTS
    # =======================================================================
    def test_e2e_16_m1_m2_regression_accuracy_and_insights(self):
        """E2E-16: Run regression verification on accuracy (WER), repository persistence, and insights."""
        from test_accuracy import evaluate_accuracy
        speech_ref = "Today's meeting date is 27th August and day is Thursday and the time is 6.45 pm."
        acc_passed = evaluate_accuracy(self.audio_file, speech_ref, model_size="base")
        self.assertTrue(acc_passed, "Transcription accuracy benchmark must pass (>= 90%)")

        # Verify historical insights filtering
        insights_filtered = self.db.get_historical_insights(participant="Priya")
        self.assertGreaterEqual(insights_filtered["total_meetings"], 1)


if __name__ == "__main__":
    unittest.main()
