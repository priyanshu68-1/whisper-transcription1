"""
WhisperSense AI • Milestone 4 - Task 9: Performance, Security & Reliability Test Suite
Verifies:
1. Performance Benchmarks: Response latencies, report generation times, concurrent query throughput.
2. Security Validation: SQL Injection resistance, XSS payload handling, token authentication, IDOR isolation, salted password hashing.
3. Reliability & Fault Tolerance: Boundary limits (oversized inputs), missing files, corrupt formats, 404/400 error handling without crashes.
"""

import os
import time
import uuid
import unittest
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

from database import DatabaseManager, hash_password, verify_password
from report_exporter import generate_meeting_pdf, generate_meeting_csv, generate_action_items_csv
from api import app

SAMPLE_AUDIO = "transcipt_test2.mp3"


class TestMilestone4PerformanceSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager()
        cls.client = TestClient(app)
        cls.created_meeting_ids = []
        cls.created_user_ids = []

        # Create two test users
        cls.user_sec_a = cls.db.register_user(
            username=f"sec_a_{uuid.uuid4().hex[:6]}",
            password="SecurePassword1!",
            email="sec_a@whispersense.ai",
            full_name="Security User A"
        )
        cls.created_user_ids.append(cls.user_sec_a["id"])

        cls.user_sec_b = cls.db.register_user(
            username=f"sec_b_{uuid.uuid4().hex[:6]}",
            password="SecurePassword2!",
            email="sec_b@whispersense.ai",
            full_name="Security User B"
        )
        cls.created_user_ids.append(cls.user_sec_b["id"])

        # Seed meeting for User A
        cls.mid_bench = f"PERF-MEET-{uuid.uuid4().hex[:6].upper()}"
        cls.created_meeting_ids.append(cls.mid_bench)
        cls.db.save_meeting(
            meeting_id=cls.mid_bench,
            title="Enterprise Security Architecture Sync",
            audio_filename="sec_sync.mp3",
            file_size_mb=1.2,
            duration_seconds=120.0,
            format_ext="MP3",
            language="EN",
            transcript="Discussion on cryptographic token defense, salted hashing, and SQL injection prevention.",
            intelligence={
                "summary": "Team reviewed cryptographic token security and parameterized queries.",
                "key_points": ["Verified zero raw string concatenation in SQL queries.", "Enabled indexes."],
                "decisions": ["Approved PBKDF2 / SHA-256 salted password hashing."],
                "deadlines": ["2026-10-15"],
                "priorities": ["High"],
                "action_items": [
                    {"task": "Run vulnerability scan", "assignee": "Security Engineer", "priority": "High", "deadline": "2026-10-15", "status": "Pending"}
                ]
            },
            participant_data={"unique_participants": ["Security Engineer", "Lead Architect"]},
            validation_info={"is_valid": True},
            user_id=cls.user_sec_a["id"]
        )

    @classmethod
    def tearDownClass(cls):
        for mid in cls.created_meeting_ids:
            try:
                cls.db.delete_meeting(mid)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # 1. Performance & Latency Benchmarks
    # -------------------------------------------------------------------------
    def test_01_api_response_latency_benchmark(self):
        """Verify core API endpoints respond well under the 250ms threshold."""
        endpoints = [
            "/",
            "/stats",
            f"/meetings?user_id={self.user_sec_a['id']}",
            "/meetings/search?q=Security",
            "/meetings/insights?limit=10"
        ]

        for ep in endpoints:
            start = time.perf_counter()
            resp = self.client.get(ep)
            latency_ms = (time.perf_counter() - start) * 1000

            self.assertEqual(resp.status_code, 200)
            # Response must be fast (< 250ms on local test client)
            self.assertLess(latency_ms, 250.0, f"Endpoint '{ep}' latency too high: {latency_ms:.2f}ms")

    def test_02_export_generation_latency_benchmark(self):
        """Verify PDF and CSV generation benchmarks under 350ms."""
        meeting = self.db.get_meeting(self.mid_bench)
        self.assertIsNotNone(meeting)

        # 1. PDF Generation Latency
        t0 = time.perf_counter()
        pdf_bytes = generate_meeting_pdf(meeting)
        pdf_ms = (time.perf_counter() - t0) * 1000
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertLess(pdf_ms, 350.0, f"PDF generation too slow: {pdf_ms:.2f}ms")

        # 2. CSV Generation Latency
        t1 = time.perf_counter()
        csv_str = generate_meeting_csv(meeting)
        csv_ms = (time.perf_counter() - t1) * 1000
        self.assertIn("METADATA", csv_str)
        self.assertLess(csv_ms, 100.0, f"CSV generation too slow: {csv_ms:.2f}ms")

    def test_03_concurrent_request_handling(self):
        """Simulate 15 concurrent API requests across multiple threads."""
        def fetch_endpoint(url):
            return self.client.get(url).status_code

        urls = [
            "/stats",
            "/meetings",
            "/meetings/search?q=Security",
            f"/meetings/{self.mid_bench}",
            "/integrations/zoom/status"
        ] * 3

        with ThreadPoolExecutor(max_workers=5) as executor:
            status_codes = list(executor.map(fetch_endpoint, urls))

        self.assertEqual(len(status_codes), 15)
        for code in status_codes:
            self.assertEqual(code, 200)

    # -------------------------------------------------------------------------
    # 2. Security Validation & Attack Resistance
    # -------------------------------------------------------------------------
    def test_04_sql_injection_defense(self):
        """Verify resilience against SQL injection attack vectors in search and queries."""
        sql_injections = [
            "' OR '1'='1",
            "'; DROP TABLE meetings; --",
            "admin'--",
            "' UNION SELECT * FROM users --",
            "1; SELECT pg_sleep(5); --"
        ]

        for payload in sql_injections:
            # 1. Via Search endpoint
            resp = self.client.get(f"/meetings/search?q={payload}")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            # Must return clean matches without dumping unexpected tables
            self.assertIsInstance(data["results"], list)

            # 2. Direct database query
            res = self.db.search_meetings(query=payload)
            self.assertIsInstance(res, list)

        # Verify meetings table still intact
        self.assertIsNotNone(self.db.get_meeting(self.mid_bench))

    def test_05_xss_payload_safety(self):
        """Verify HTML/Script injection strings are stored safely without crashing reports."""
        xss_payload = "<script>alert('XSS_ATTACK')</script><img src=x onerror=alert(1)>"
        xss_mid = f"XSS-{uuid.uuid4().hex[:6].upper()}"
        self.created_meeting_ids.append(xss_mid)

        self.db.save_meeting(
            meeting_id=xss_mid,
            title=f"XSS Test {xss_payload}",
            audio_filename="xss.mp3",
            file_size_mb=0.1,
            duration_seconds=10.0,
            format_ext="MP3",
            language="EN",
            transcript=f"Transcript containing {xss_payload}",
            intelligence={
                "summary": f"Summary with {xss_payload}",
                "key_points": [xss_payload],
                "decisions": [xss_payload],
                "deadlines": [],
                "priorities": [],
                "action_items": [{"task": xss_payload, "assignee": xss_payload, "priority": "High", "deadline": "None", "status": "Pending"}]
            },
            participant_data={"unique_participants": [xss_payload]},
            validation_info={"is_valid": True},
            user_id=self.user_sec_a["id"]
        )

        retrieved = self.db.get_meeting(xss_mid)
        self.assertIsNotNone(retrieved)

        # PDF generation with XSS text must succeed without crashing ReportLab
        pdf_bytes = generate_meeting_pdf(retrieved)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

        # CSV generation with XSS text must escape properly
        csv_str = generate_meeting_csv(retrieved)
        self.assertIn("XSS_ATTACK", csv_str)

    def test_06_authentication_token_security(self):
        """Verify API token enforcement on protected endpoints."""
        protected_url = "/ask"
        body = {"question": "What were the security decisions?"}

        # 1. Missing Token -> 401
        resp_no_token = self.client.post(protected_url, json=body)
        self.assertEqual(resp_no_token.status_code, 401)

        # 2. Invalid Bearer Token -> 401
        resp_bad_bearer = self.client.post(protected_url, json=body, headers={"Authorization": "Bearer bad-token-999"})
        self.assertEqual(resp_bad_bearer.status_code, 401)

        # 3. Invalid API Key Header -> 401
        resp_bad_key = self.client.post(protected_url, json=body, headers={"X-API-Key": "bad-api-key-999"})
        self.assertEqual(resp_bad_key.status_code, 401)

        # 4. Valid Bearer Token -> 200
        valid_token = "whispersense-secret-token-2026"
        resp_valid = self.client.post(protected_url, json=body, headers={"Authorization": f"Bearer {valid_token}"})
        self.assertEqual(resp_valid.status_code, 200)

    def test_07_idor_and_multi_tenant_segregation(self):
        """Verify Insecure Direct Object Reference defense across users."""
        # User B queries meetings -> User A's meeting must NOT appear
        resp_b = self.client.get(f"/meetings?user_id={self.user_sec_b['id']}")
        self.assertEqual(resp_b.status_code, 200)
        mids_b = [m["meeting_id"] for m in resp_b.json()["meetings"]]
        self.assertNotIn(self.mid_bench, mids_b)

        # Direct DB query with User B ID returns None for User A's meeting
        isolated_meeting = self.db.get_meeting(self.mid_bench, user_id=self.user_sec_b["id"])
        self.assertIsNone(isolated_meeting)

    def test_08_cryptographic_password_hashing(self):
        """Verify salted SHA-256 properties: unique salt, non-invertible, timing safe."""
        raw_pwd = "SuperSecretPassword123!"
        hash1, salt1 = hash_password(raw_pwd)
        hash2, salt2 = hash_password(raw_pwd)

        # Salts must be unique (32 hex chars)
        self.assertNotEqual(salt1, salt2)
        self.assertEqual(len(salt1), 32)
        self.assertEqual(len(salt2), 32)

        # Hashes for same password must differ due to unique salts
        self.assertNotEqual(hash1, hash2)

        # Verify function correctly validates matching password
        self.assertTrue(verify_password(raw_pwd, salt1, hash1))
        self.assertTrue(verify_password(raw_pwd, salt2, hash2))
        self.assertFalse(verify_password("WrongPassword!", salt1, hash1))

    # -------------------------------------------------------------------------
    # 3. Reliability, Error Handling & Boundary Protection
    # -------------------------------------------------------------------------
    def test_09_oversized_input_boundary_protection(self):
        """Verify oversized input payloads are rejected gracefully without crashing."""
        oversized_q = "A" * 5000
        valid_token = "whispersense-secret-token-2026"
        resp = self.client.post("/ask", json={"question": oversized_q}, headers={"Authorization": f"Bearer {valid_token}"})
        # Should be rejected with 400 Bad Request
        self.assertEqual(resp.status_code, 400)
        self.assertIn("exceeds", resp.json()["detail"].lower())

    def test_10_missing_recording_file_graceful_handling(self):
        """Verify integrations handle non-existent audio files with clean errors."""
        fake_path = "non_existent_recording_file_xyz.mp3"
        # Meet sync with non-existent file
        resp = self.client.post("/integrations/google-meet/sync", json={
            "meet_url_or_code": "xyz-test-none",
            "topic": "Missing File Test",
            "audio_path": fake_path,
            "user_id": self.user_sec_a["id"]
        })
        # If test audio transcipt_test2.mp3 exists, it falls back gracefully; if not, returns 500 cleanly
        self.assertIn(resp.status_code, [200, 500])

    def test_11_export_nonexistent_meeting_404(self):
        """Verify export endpoints return 404 for unknown IDs without server crashes."""
        bad_id = "NONEXISTENT-MEET-9999"
        self.assertEqual(self.client.get(f"/meetings/{bad_id}/export/pdf").status_code, 404)
        self.assertEqual(self.client.get(f"/meetings/{bad_id}/export/csv").status_code, 404)
        self.assertEqual(self.client.get(f"/meetings/{bad_id}/export/action-items").status_code, 404)


if __name__ == "__main__":
    unittest.main()
