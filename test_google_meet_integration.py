"""
WhisperSense AI • Test Suite for Milestone 4 - Task 5: Google Meet Integration
Uses standard library unittest to verify:
1. Google Meet URL & code normalization (canonical 3-4-3 format).
2. End-to-end recording ingestion via Whisper pipeline.
3. Duplicate detection & conflict rejection.
4. FastAPI endpoints: /integrations/google-meet/sync, /status.
"""

import os
import time
import unittest
from fastapi.testclient import TestClient

from database import DatabaseManager
from google_meet_integration import GoogleMeetIntegrationService
from api import app

SAMPLE_AUDIO = "transcipt_test2.mp3"


class TestGoogleMeetIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager()
        cls.client = TestClient(app)
        cls.service = GoogleMeetIntegrationService(db=cls.db)
        cls.created_meeting_ids = []

    @classmethod
    def tearDownClass(cls):
        for mid in cls.created_meeting_ids:
            try:
                cls.db.delete_meeting(mid)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # 1. URL & Meeting Code Parsing Tests
    # -------------------------------------------------------------------------
    def test_01_parse_meet_code_formats(self):
        """Test URL & code normalization across varied user inputs."""
        # Full https URL
        self.assertEqual(
            self.service.parse_meet_code("https://meet.google.com/abc-defg-hij"),
            "abc-defg-hij"
        )
        # URL with query params
        self.assertEqual(
            self.service.parse_meet_code("https://meet.google.com/abc-defg-hij?authuser=0&hl=en"),
            "abc-defg-hij"
        )
        # Domain only
        self.assertEqual(
            self.service.parse_meet_code("meet.google.com/xyz-uvwx-rst"),
            "xyz-uvwx-rst"
        )
        # Raw canonical code
        self.assertEqual(
            self.service.parse_meet_code("abc-defg-hij"),
            "abc-defg-hij"
        )
        # Raw 10-char string without hyphens
        self.assertEqual(
            self.service.parse_meet_code("abcdefghij"),
            "abc-defg-hij"
        )
        # Empty or invalid
        self.assertEqual(self.service.parse_meet_code(""), "")
        self.assertEqual(self.service.parse_meet_code(None), "")

    # -------------------------------------------------------------------------
    # 2. Ingestion & Duplicate Detection Tests
    # -------------------------------------------------------------------------
    def test_02_process_recording_and_duplicate_prevention(self):
        """Test Meet recording processing and subsequent duplicate rejection."""
        unique_suffix = str(int(time.time()))[-4:]
        meet_code = f"abc-defg-{unique_suffix}"

        # 1. First sync -> SUCCESS
        ok, res_data, msg = self.service.process_meet_recording(
            meet_code_or_url=meet_code,
            topic="Frontend Component Planning",
            audio_file_path=SAMPLE_AUDIO if os.path.exists(SAMPLE_AUDIO) else None,
            user_id=1
        )

        self.assertTrue(ok)
        self.assertIn("meeting_id", res_data)
        mid = res_data["meeting_id"]
        self.assertTrue(mid.startswith("GMEET-"))
        self.created_meeting_ids.append(mid)

        # 2. Verify duplicate check returns True
        self.assertTrue(self.service.is_duplicate(meet_code, user_id=1))
        # Should also be True for full URL containing that code
        self.assertTrue(self.service.is_duplicate(f"https://meet.google.com/{meet_code}", user_id=1))

        # 3. Second sync -> DUPLICATE REJECTED
        dup_ok, dup_data, dup_msg = self.service.process_meet_recording(
            meet_code_or_url=meet_code,
            topic="Frontend Component Planning",
            audio_file_path=SAMPLE_AUDIO if os.path.exists(SAMPLE_AUDIO) else None,
            user_id=1
        )

        self.assertFalse(dup_ok)
        self.assertTrue(dup_data.get("duplicate"))
        self.assertIn("Duplicate", dup_msg)

    # -------------------------------------------------------------------------
    # 3. API Endpoints Tests
    # -------------------------------------------------------------------------
    def test_03_api_meet_status(self):
        """Test GET /integrations/google-meet/status endpoint."""
        resp = self.client.get("/integrations/google-meet/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("service", data)
        self.assertIn("status", data)
        self.assertEqual(data["status"], "ready")
        self.assertIn("sync_endpoint", data)

    def test_04_api_meet_sync_endpoint_and_conflict(self):
        """Test POST /integrations/google-meet/sync endpoint and 409 Conflict on duplicate."""
        unique_suffix = str(int(time.time()))[-4:]
        meet_url = f"https://meet.google.com/xyz-team-{unique_suffix}"

        body = {
            "meet_url_or_code": meet_url,
            "topic": "API Sprint Review",
            "audio_path": SAMPLE_AUDIO if os.path.exists(SAMPLE_AUDIO) else None,
            "user_id": 1
        }

        # 1. First sync -> 200 OK
        resp = self.client.post("/integrations/google-meet/sync", json=body)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "success")
        if data.get("meeting", {}).get("meeting_id"):
            self.created_meeting_ids.append(data["meeting"]["meeting_id"])

        # 2. Duplicate sync -> 409 Conflict
        resp_dup = self.client.post("/integrations/google-meet/sync", json=body)
        self.assertEqual(resp_dup.status_code, 409)

    def test_05_api_meet_sync_invalid_code(self):
        """Test POST /integrations/google-meet/sync with invalid code returns 400."""
        body = {
            "meet_url_or_code": "   ",
            "topic": "Invalid Code Meeting",
            "user_id": 1
        }
        resp = self.client.post("/integrations/google-meet/sync", json=body)
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
