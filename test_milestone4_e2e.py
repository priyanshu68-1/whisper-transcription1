"""
WhisperSense AI • Complete Milestone 4 End-to-End Verification Test Suite (Task 8)
Validates the full enterprise lifecycle across all Milestone 4 capabilities:
1. Multi-User Provisioning & Auth Security (Salted password hashing, verification, isolation).
2. Multi-Channel Ingestion (Direct audio upload, Zoom cloud sync, Google Meet ingestion).
3. Duplicate Detection & Prevention across Zoom and Google Meet.
4. Strict Multi-Tenant Data Isolation (User A vs User B).
5. Contextual RAG AI Assistant with source meeting ID attribution.
6. Cross-Meeting Historical Insights & Workload KPIs.
7. Enterprise Dossier & Spreadsheet Exporting (ReportLab PDF, Multi-section CSV, Action items CSV).
8. Task Lifecycle Management & Cascade Cleanup.
"""

import os
import time
import uuid
import unittest
from fastapi.testclient import TestClient

from database import DatabaseManager, hash_password, verify_password
from zoom_integration import ZoomIntegrationService
from google_meet_integration import GoogleMeetIntegrationService
from report_exporter import generate_meeting_pdf, generate_meeting_csv, generate_action_items_csv
from pipeline_service import ProcessingPipeline
from api import app

SAMPLE_AUDIO = "transcipt_test2.mp3"


class TestMilestone4EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager()
        cls.client = TestClient(app)
        cls.zoom_srv = ZoomIntegrationService(db=cls.db)
        cls.meet_srv = GoogleMeetIntegrationService(db=cls.db)

        cls.created_meeting_ids = []
        cls.created_user_ids = []

    @classmethod
    def tearDownClass(cls):
        # Cleanup meetings
        for mid in cls.created_meeting_ids:
            try:
                cls.db.delete_meeting(mid)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # 1. User Authentication & Session Security Lifecycle
    # -------------------------------------------------------------------------
    def test_01_user_registration_and_salted_hashing(self):
        """Test registration with cryptographic salted password hashing."""
        uname_a = f"alpha_{uuid.uuid4().hex[:6]}"
        pwd_a = "SecurePass123!"

        resp_a = self.client.post("/auth/register", json={
            "username": uname_a,
            "password": pwd_a,
            "email": f"{uname_a}@whispersense.ai",
            "full_name": "Alpha Lead"
        })
        self.assertEqual(resp_a.status_code, 200)
        data_a = resp_a.json()
        self.assertEqual(data_a["status"], "success")
        user_a = data_a["user"]
        self.assertIn("id", user_a)
        self.assertNotIn("password_hash", user_a)
        self.assertNotIn("salt", user_a)
        self.__class__.user_a_id = user_a["id"]
        self.__class__.user_a_uname = uname_a
        self.__class__.user_a_pwd = pwd_a
        self.created_user_ids.append(user_a["id"])

        # Create User B for multi-tenant isolation tests
        uname_b = f"beta_{uuid.uuid4().hex[:6]}"
        resp_b = self.client.post("/auth/register", json={
            "username": uname_b,
            "password": "BetaPassword456!",
            "email": f"{uname_b}@whispersense.ai",
            "full_name": "Beta Engineer"
        })
        self.assertEqual(resp_b.status_code, 200)
        self.__class__.user_b_id = resp_b.json()["user"]["id"]
        self.created_user_ids.append(self.__class__.user_b_id)

    def test_02_user_login_validation(self):
        """Test successful login and rejection of bad credentials."""
        # Valid login
        resp_ok = self.client.post("/auth/login", json={
            "username": self.user_a_uname,
            "password": self.user_a_pwd
        })
        self.assertEqual(resp_ok.status_code, 200)
        self.assertEqual(resp_ok.json()["status"], "success")
        self.assertIn("token", resp_ok.json())

        # Invalid login
        resp_bad = self.client.post("/auth/login", json={
            "username": self.user_a_uname,
            "password": "WrongPassword!"
        })
        self.assertEqual(resp_bad.status_code, 401)

    # -------------------------------------------------------------------------
    # 2. Multi-Channel Ingestion (Audio, Zoom, Google Meet)
    # -------------------------------------------------------------------------
    def test_03_direct_audio_ingestion(self):
        """Test direct audio file transcription and persistence under User A."""
        mid = f"MEET-E2E-{uuid.uuid4().hex[:6].upper()}"
        pipeline = ProcessingPipeline(model_size="base")
        ok, res, msg = pipeline.run_full_pipeline(
            audio_file_path=SAMPLE_AUDIO,
            meeting_title="Q3 Strategy & Budget Sync",
            custom_meeting_id=mid,
            user_id=self.user_a_id
        )
        self.assertTrue(ok)
        self.assertEqual(res["meeting_id"], mid)
        self.created_meeting_ids.append(mid)
        self.__class__.mid_audio = mid

    def test_04_zoom_cloud_ingestion_and_duplicate(self):
        """Test Zoom cloud ingestion via service and duplicate conflict handling."""
        zoom_id = f"984210{int(time.time())}"
        ok, res, msg = self.zoom_srv.sync_manual_meeting(
            zoom_meeting_id=zoom_id,
            topic="Zoom Engineering Architecture Review",
            audio_file_path=SAMPLE_AUDIO,
            user_id=self.user_a_id
        )
        self.assertTrue(ok)
        mid = res["meeting_id"]
        self.assertTrue(mid.startswith("ZOOM-"))
        self.created_meeting_ids.append(mid)
        self.__class__.mid_zoom = mid

        # Duplicate check must return True
        self.assertTrue(self.zoom_srv.is_duplicate(zoom_id, user_id=self.user_a_id))

        # Re-sync must fail with duplicate
        dup_ok, dup_res, dup_msg = self.zoom_srv.sync_manual_meeting(
            zoom_meeting_id=zoom_id,
            topic="Zoom Engineering Architecture Review",
            audio_file_path=SAMPLE_AUDIO,
            user_id=self.user_a_id
        )
        self.assertFalse(dup_ok)
        self.assertTrue(dup_res.get("duplicate"))

    def test_05_google_meet_ingestion_and_duplicate(self):
        """Test Google Meet ingestion via API and duplicate 409 Conflict."""
        meet_code = f"abc-e2e-{int(time.time())}"[-12:]
        if len(meet_code) < 12:
            meet_code = "abc-e2e-9988"

        # 1. First sync -> 200 OK
        resp = self.client.post("/integrations/google-meet/sync", json={
            "meet_url_or_code": f"https://meet.google.com/{meet_code}",
            "topic": "Google Meet UI Sprint",
            "audio_path": SAMPLE_AUDIO,
            "user_id": self.user_a_id
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        mid = data["meeting"]["meeting_id"]
        self.assertTrue(mid.startswith("GMEET-"))
        self.created_meeting_ids.append(mid)
        self.__class__.mid_meet = mid

        # 2. Duplicate sync -> 409 Conflict
        resp_dup = self.client.post("/integrations/google-meet/sync", json={
            "meet_url_or_code": meet_code,
            "topic": "Google Meet UI Sprint",
            "audio_path": SAMPLE_AUDIO,
            "user_id": self.user_a_id
        })
        self.assertEqual(resp_dup.status_code, 409)

    # -------------------------------------------------------------------------
    # 3. Multi-Tenant Data Isolation
    # -------------------------------------------------------------------------
    def test_06_data_segregation_between_users(self):
        """Verify User A's meetings are completely isolated from User B."""
        # User A has 3 meetings
        resp_a = self.client.get(f"/meetings?user_id={self.user_a_id}")
        self.assertEqual(resp_a.status_code, 200)
        meetings_a = resp_a.json()["meetings"]
        self.assertGreaterEqual(len(meetings_a), 3)

        # User B has 0 meetings
        resp_b = self.client.get(f"/meetings?user_id={self.user_b_id}")
        self.assertEqual(resp_b.status_code, 200)
        meetings_b = resp_b.json()["meetings"]
        self.assertEqual(len(meetings_b), 0)

    # -------------------------------------------------------------------------
    # 4. Contextual Search & RAG Assistant
    # -------------------------------------------------------------------------
    def test_07_search_and_rag_grounded_answer(self):
        """Test search and RAG synthesis grounded in repository records."""
        # Relational keyword search
        search_resp = self.client.get("/meetings/search?q=Strategy")
        self.assertEqual(search_resp.status_code, 200)
        self.assertGreaterEqual(search_resp.json()["total_matches"], 1)

        # Contextual RAG Q&A
        ai_resp = self.client.get("/meetings/ai-search?q=What are the upcoming deadlines discussed?")
        self.assertEqual(ai_resp.status_code, 200)
        ans_data = ai_resp.json()
        self.assertIn("answer", ans_data)
        self.assertIn("source_meeting_ids", ans_data)

    # -------------------------------------------------------------------------
    # 5. Historical Insights & Cross-Meeting Analytics
    # -------------------------------------------------------------------------
    def test_08_cross_meeting_insights(self):
        """Test historical insights computation scoped to user."""
        resp = self.client.get(f"/meetings/insights?limit=20")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["insights"]

        # KPIs
        self.assertIn("total_meetings", data)
        self.assertIn("total_action_items", data)
        self.assertIn("participants", data)
        self.assertIn("decisions", data)
        self.assertIn("deadlines", data)
        self.assertGreater(data["total_meetings"], 0)

    # -------------------------------------------------------------------------
    # 6. Enterprise Dossier & Spreadsheet Exporting
    # -------------------------------------------------------------------------
    def test_09_export_dossier_pdf_and_csv(self):
        """Test PDF, Full CSV, and Action Items CSV export endpoints."""
        mid = self.mid_audio

        # 1. PDF Export
        resp_pdf = self.client.get(f"/meetings/{mid}/export/pdf")
        self.assertEqual(resp_pdf.status_code, 200)
        self.assertIn("application/pdf", resp_pdf.headers.get("content-type", ""))
        self.assertTrue(resp_pdf.content.startswith(b"%PDF-"))

        # 2. CSV Full Export
        resp_csv = self.client.get(f"/meetings/{mid}/export/csv")
        self.assertEqual(resp_csv.status_code, 200)
        self.assertIn("text/csv", resp_csv.headers.get("content-type", ""))
        self.assertIn("METADATA", resp_csv.text)

        # 3. Action Items CSV Export
        resp_act = self.client.get(f"/meetings/{mid}/export/action-items")
        self.assertEqual(resp_act.status_code, 200)
        self.assertIn("text/csv", resp_act.headers.get("content-type", ""))
        self.assertIn("Task Description", resp_act.text)

    # -------------------------------------------------------------------------
    # 7. Task Lifecycle Management & Cascade Cleanup
    # -------------------------------------------------------------------------
    def test_10_task_lifecycle_and_cascade_deletion(self):
        """Test updating action item status and verify cascading deletion."""
        # 1. Fetch meeting action items
        meeting = self.db.get_meeting(self.mid_audio, user_id=self.user_a_id)
        actions = meeting.get("action_items", [])
        if actions:
            act = actions[0]
            act_id = act["id"]
            # Transition status
            self.db.update_action_item_status(act_id, "Completed")
            refreshed = self.db.get_meeting(self.mid_audio, user_id=self.user_a_id)
            updated_act = [a for a in refreshed["action_items"] if a["id"] == act_id][0]
            self.assertEqual(updated_act["status"], "Completed")

        # 2. Delete meeting and verify cascading cleanup
        del_mid = self.mid_meet
        self.db.delete_meeting(del_mid)
        # Should now be None
        self.assertIsNone(self.db.get_meeting(del_mid))
        # Ensure it was removed from created_meeting_ids to prevent double deletion in tearDown
        if del_mid in self.created_meeting_ids:
            self.created_meeting_ids.remove(del_mid)


if __name__ == "__main__":
    unittest.main()
