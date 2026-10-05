"""
WhisperSense AI • Test Suite for Milestone 4 - Task 4: Zoom Integration
Uses standard library unittest to verify:
1. Zoom HMAC SHA-256 webhook signature verification.
2. Zoom URL validation challenge response (endpoint.url_validation).
3. Ingestion of 'recording.completed' event into Whisper pipeline.
4. Duplicate detection and rejection to prevent redundant processing.
5. Manual Zoom recording sync.
6. FastAPI endpoints: /integrations/zoom/webhook, /sync, and /status.
"""

import os
import hmac
import hashlib
import json
import time
import unittest
from fastapi.testclient import TestClient

from database import DatabaseManager
from zoom_integration import ZoomIntegrationService
from api import app

SAMPLE_AUDIO = "transcipt_test2.mp3"


class TestZoomIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager()
        cls.client = TestClient(app)
        cls.secret = "test_zoom_secret_xyz123"
        cls.zoom = ZoomIntegrationService(db=cls.db, webhook_secret=cls.secret)
        cls.created_meeting_ids = []

    @classmethod
    def tearDownClass(cls):
        # Cleanup any meetings created during test
        for mid in cls.created_meeting_ids:
            try:
                cls.db.delete_meeting(mid)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # 1. Security & Webhook Validation Tests
    # -------------------------------------------------------------------------
    def test_01_webhook_signature_verification_valid(self):
        """Test valid Zoom webhook signature verification."""
        timestamp = str(int(time.time()))
        payload_bytes = json.dumps({"event": "test"}).encode("utf-8")
        message = f"v0:{timestamp}:{payload_bytes.decode('utf-8')}"
        expected_hash = hmac.new(self.secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
        signature = f"v0={expected_hash}"

        self.assertTrue(self.zoom.verify_webhook_signature(payload_bytes, signature, timestamp))

    def test_02_webhook_signature_verification_invalid(self):
        """Test invalid or tampered signature is rejected."""
        timestamp = str(int(time.time()))
        payload_bytes = json.dumps({"event": "test"}).encode("utf-8")
        bad_sig = "v0=0000000000000000000000000000000000000000000000000000000000000000"

        self.assertFalse(self.zoom.verify_webhook_signature(payload_bytes, bad_sig, timestamp))
        self.assertFalse(self.zoom.verify_webhook_signature(payload_bytes, None, timestamp))
        self.assertFalse(self.zoom.verify_webhook_signature(payload_bytes, bad_sig, None))

    def test_03_url_validation_challenge(self):
        """Test Zoom URL validation challenge encryption."""
        plain_token = "zoom_plain_challenge_token_abc"
        res = self.zoom.handle_url_validation(plain_token)

        self.assertIn("plainToken", res)
        self.assertIn("encryptedToken", res)
        self.assertEqual(res["plainToken"], plain_token)

        expected_enc = hmac.new(self.secret.encode("utf-8"), plain_token.encode("utf-8"), hashlib.sha256).hexdigest()
        self.assertEqual(res["encryptedToken"], expected_enc)

    # -------------------------------------------------------------------------
    # 2. Ingestion & Duplicate Detection Tests
    # -------------------------------------------------------------------------
    def test_04_process_recording_completed_and_duplicate(self):
        """Test recording ingestion followed by duplicate rejection."""
        zoom_id = f"ZTEST{int(time.time())}"
        payload = {
            "event": "recording.completed",
            "payload": {
                "object": {
                    "id": zoom_id,
                    "uuid": f"uuid-{zoom_id}",
                    "topic": "Sprint Planning Sync",
                    "duration": 10,
                    "recording_files": [
                        {"file_type": "M4A", "recording_type": "audio_only", "download_url": ""}
                    ]
                }
            }
        }

        # First ingestion -> SUCCESS
        success, res_data, msg = self.zoom.process_recording_completed_event(
            event_payload=payload,
            user_id=1,
            mock_audio_path=SAMPLE_AUDIO if os.path.exists(SAMPLE_AUDIO) else None
        )

        self.assertTrue(success)
        self.assertIn("meeting_id", res_data)
        mid = res_data["meeting_id"]
        self.created_meeting_ids.append(mid)

        # Check DB reflects success
        self.assertTrue(self.zoom.is_duplicate(f"uuid-{zoom_id}", user_id=1))

        # Second ingestion with same UUID -> DUPLICATE REJECTED
        dup_success, dup_data, dup_msg = self.zoom.process_recording_completed_event(
            event_payload=payload,
            user_id=1,
            mock_audio_path=SAMPLE_AUDIO if os.path.exists(SAMPLE_AUDIO) else None
        )

        self.assertFalse(dup_success)
        self.assertTrue(dup_data.get("duplicate"))
        self.assertIn("Duplicate", dup_msg)

    def test_05_manual_sync(self):
        """Test manual sync helper."""
        if not os.path.exists(SAMPLE_AUDIO):
            self.skipTest(f"Audio file '{SAMPLE_AUDIO}' not available")

        zoom_id = f"ZMANUAL{int(time.time())}"
        ok, res, msg = self.zoom.sync_manual_meeting(
            zoom_meeting_id=zoom_id,
            topic="Executive Q3 Alignment",
            audio_file_path=SAMPLE_AUDIO,
            user_id=1
        )

        self.assertTrue(ok)
        self.assertIn("meeting_id", res)
        self.created_meeting_ids.append(res["meeting_id"])

    # -------------------------------------------------------------------------
    # 3. API Endpoints Tests
    # -------------------------------------------------------------------------
    def test_06_api_zoom_status(self):
        """Test GET /integrations/zoom/status endpoint."""
        resp = self.client.get("/integrations/zoom/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn("webhook_endpoint", data)
        self.assertIn("sync_endpoint", data)

    def test_07_api_zoom_webhook_url_validation(self):
        """Test POST /integrations/zoom/webhook endpoint with URL validation challenge."""
        challenge_payload = {
            "event": "endpoint.url_validation",
            "payload": {
                "plainToken": "challenge_token_xyz"
            }
        }
        resp = self.client.post("/integrations/zoom/webhook", json=challenge_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("plainToken"), "challenge_token_xyz")
        self.assertIn("encryptedToken", data)

    def test_08_api_zoom_sync_endpoint_and_conflict(self):
        """Test POST /integrations/zoom/sync endpoint and 409 Conflict on duplicate."""
        zoom_id = f"ZAPI{int(time.time())}"
        body = {
            "meeting_id": zoom_id,
            "topic": "API Test Meeting",
            "audio_path": SAMPLE_AUDIO if os.path.exists(SAMPLE_AUDIO) else None,
            "user_id": 1
        }

        # First sync -> 200 OK
        resp = self.client.post("/integrations/zoom/sync", json=body)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "success")
        if data.get("meeting", {}).get("meeting_id"):
            self.created_meeting_ids.append(data["meeting"]["meeting_id"])

        # Second sync with same ID -> 409 Conflict
        resp_dup = self.client.post("/integrations/zoom/sync", json=body)
        self.assertEqual(resp_dup.status_code, 409)


if __name__ == "__main__":
    unittest.main()
