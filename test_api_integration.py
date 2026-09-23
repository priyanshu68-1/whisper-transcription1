import os
import unittest
import uuid
from fastapi.testclient import TestClient

from database import DatabaseManager
from api import app, API_AUTH_TOKEN

class TestAPIIntegration(unittest.TestCase):
    """
    Milestone 3 – Task 6: Integration Test Suite
    Verifies:
    1. GET /meetings: List meetings with pagination (unauthenticated allowed)
    2. GET /meetings/{id}: Retrieve meeting by ID with complete intelligence
    3. GET /meetings/{id}: Returns 404 for non-existent meeting
    4. GET /meetings/{id}: Returns 400 for empty or whitespace meeting ID
    5. GET /search: Search meetings via keyword and query parameters
    6. GET /search: Search with dedicated filters (participant, date, title)
    7. GET /search: Semantic / vector retrieval flag enabled
    8. GET /search: No-result queries return safe empty results
    9. POST /search: Search with JSON payload, filters, and semantic flag
    10. POST /ask: Unauthenticated request returns 401 Unauthorized
    11. POST /ask: Invalid credentials return 401 Unauthorized
    12. POST /ask: Authenticated request with Bearer token succeeds with grounded answer & source IDs
    13. POST /ask: Authenticated request with X-API-Key header succeeds
    14. POST /ask: Empty or whitespace question returns 400 Bad Request
    15. POST /ask: No-result question returns safe 'information not found' answer with zero hallucination
    16. GET /search: Invalid date format returns 400 Bad Request
    17. Backward compatibility: Existing /meetings/search and /meetings/ai-search remain intact
    """

    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager()
        cls.client = TestClient(app)
        cls.auth_token = API_AUTH_TOKEN
        cls.bearer_headers = {"Authorization": f"Bearer {cls.auth_token}"}
        cls.api_key_headers = {"X-API-Key": cls.auth_token}
        cls.invalid_headers = {"Authorization": "Bearer completely-invalid-token-xyz"}

        # Generate unique IDs for test fixtures
        cls.mid_platform = f"INTEG-PLAT-{uuid.uuid4().hex[:6].upper()}"
        cls.mid_security = f"INTEG-SEC-{uuid.uuid4().hex[:6].upper()}"

        # Seed meeting 1: Platform & Redis Architecture
        cls.db.save_meeting(
            meeting_id=cls.mid_platform,
            title="Enterprise Cloud Platform Architecture",
            audio_filename="platform_architecture.mp3",
            file_size_mb=6.2,
            duration_seconds=500.0,
            format_ext=".mp3",
            language="en",
            transcript="Kavita proposed transitioning our session caching to Redis Sentinel clusters. Dev agreed and promised Prometheus latency metrics by Friday.",
            intelligence={
                "summary": "Engineering review of Redis caching clusters, Prometheus telemetry, and session management latency.",
                "key_points": [
                    "Transition caching to Redis cluster to lower P99 response time.",
                    "Integrate Prometheus latency metrics into Grafana dashboards."
                ],
                "decisions": [
                    "Deploy Redis Sentinel cluster in production.",
                    "Set session TTL to 24 hours across all microservices."
                ],
                "deadlines": ["Friday 5pm", "November 1st"],
                "priorities": ["High", "Medium"],
                "action_items": [
                    {
                        "task": "Deploy Redis Sentinel Helm chart to Kubernetes",
                        "assignee": "Kavita",
                        "priority": "High",
                        "deadline": "November 1st",
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

        # Seed meeting 2: Mobile Security & Biometrics
        cls.db.save_meeting(
            meeting_id=cls.mid_security,
            title="Mobile Application Security and Biometric Authentication",
            audio_filename="mobile_security.mp3",
            file_size_mb=4.1,
            duration_seconds=320.0,
            format_ext=".mp3",
            language="en",
            transcript="Aarav demonstrated FaceID biometric login for iOS. Dev raised concerns regarding Android backward compatibility.",
            intelligence={
                "summary": "Security team evaluated biometric authentication flows and agreed to deprecate SMS 2FA.",
                "key_points": [
                    "FaceID biometric login working on iOS 18 test device.",
                    "SMS 2FA security vulnerabilities reviewed."
                ],
                "decisions": [
                    "Mandate biometric authentication for high-value financial transfers.",
                    "Deprecate SMS-based two-factor authentication."
                ],
                "deadlines": ["December 15th"],
                "priorities": ["High"],
                "action_items": [
                    {
                        "task": "Implement biometric prompt wrapper for Android 10 fallback",
                        "assignee": "Dev",
                        "priority": "High",
                        "deadline": "December 15th",
                        "status": "Pending"
                    }
                ]
            },
            participant_data={
                "unique_participants": ["Aarav", "Dev"],
                "responsibilities": []
            },
            validation_info={"is_valid": True, "file_check": "PASSED", "transcript_check": "PASSED", "schema_check": "PASSED"}
        )

    @classmethod
    def tearDownClass(cls):
        cls.db.delete_meeting(cls.mid_platform)
        cls.db.delete_meeting(cls.mid_security)

    # -----------------------------------------------------------------------
    # 1. /meetings Endpoint Tests
    # -----------------------------------------------------------------------
    def test_01_get_meetings_public(self):
        """GET /meetings succeeds without authentication headers (public contract preserved)."""
        resp = self.client.get("/meetings?limit=10")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        self.assertIsInstance(data.get("meetings"), list)
        self.assertGreaterEqual(data.get("total"), 2)

    def test_02_get_meetings_pagination(self):
        """GET /meetings correctly respects limit and offset pagination parameters."""
        resp = self.client.get("/meetings?limit=1&offset=0")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data.get("meetings")), 1)

    # -----------------------------------------------------------------------
    # 2. /meetings/{id} Endpoint Tests
    # -----------------------------------------------------------------------
    def test_03_get_meeting_by_id(self):
        """GET /meetings/{meeting_id} returns 200 with full intelligence for valid meeting."""
        resp = self.client.get(f"/meetings/{self.mid_platform}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("meeting_id"), self.mid_platform)
        self.assertEqual(data.get("title"), "Enterprise Cloud Platform Architecture")
        self.assertIn("Redis Sentinel", data.get("transcript"))
        self.assertIsInstance(data.get("action_items"), list)
        self.assertEqual(len(data.get("action_items")), 2)
        self.assertIn("Kavita", data.get("participants"))

    def test_04_get_meeting_not_found(self):
        """GET /meetings/{id} returns 404 Not Found for non-existent meeting ID."""
        resp = self.client.get("/meetings/NONEXISTENT-MEET-404")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("not found", resp.json().get("detail", "").lower())

    def test_05_get_meeting_invalid_id(self):
        """GET /meetings/{id} returns 400 Bad Request for whitespace or empty meeting ID."""
        resp = self.client.get("/meetings/%20%20")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("invalid meeting id", resp.json().get("detail", "").lower())

    # -----------------------------------------------------------------------
    # 3. /search Endpoint Tests (GET & POST)
    # -----------------------------------------------------------------------
    def test_06_get_search_keyword(self):
        """GET /search?q=... returns matching meetings across transcripts, decisions, and tasks."""
        resp = self.client.get("/search?q=Sentinel")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        self.assertGreaterEqual(data.get("total_matches"), 1)
        found_ids = [m["meeting_id"] for m in data.get("results")]
        self.assertIn(self.mid_platform, found_ids)

    def test_07_get_search_with_filters(self):
        """GET /search with participant filter scopes results to the correct meeting."""
        resp = self.client.get("/search?participant=Aarav")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(data.get("total_matches"), 1)
        found_ids = [m["meeting_id"] for m in data.get("results")]
        self.assertIn(self.mid_security, found_ids)
        self.assertNotIn(self.mid_platform, found_ids)

    def test_08_get_search_semantic_mode(self):
        """GET /search with semantic=true executes semantic/vector retrieval."""
        resp = self.client.get("/search?q=biometric+authentication+mobile&semantic=true")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data.get("semantic"))
        self.assertGreaterEqual(data.get("total_matches"), 1)

    def test_09_get_search_no_results(self):
        """GET /search with non-matching query returns safe empty results without errors."""
        resp = self.client.get("/search?q=SUPER_QUANTUM_WARP_DRIVE_NO_MATCH_999")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("total_matches"), 0)
        self.assertEqual(data.get("results"), [])

    def test_10_post_search_json(self):
        """POST /search accepts structured JSON body with query, filters, and semantic flag."""
        payload = {
            "query": "Prometheus",
            "semantic": False,
            "filters": {"participant": "Dev"},
            "limit": 5
        }
        resp = self.client.post("/search", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        self.assertGreaterEqual(data.get("total_matches"), 1)

    def test_11_search_invalid_date_format(self):
        """GET /search rejects invalid date strings with 400 Bad Request."""
        resp = self.client.get("/search?date=INVALID_DATE_FORMAT_123;;")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("invalid date", resp.json().get("detail", "").lower())

    # -----------------------------------------------------------------------
    # 4. /ask Endpoint Tests (Authentication, RAG, Zero Hallucination)
    # -----------------------------------------------------------------------
    def test_12_ask_unauthenticated_rejected(self):
        """POST /ask without credentials returns 401 Unauthorized."""
        payload = {"question": "What tasks were assigned to Kavita?"}
        resp = self.client.post("/ask", json=payload)
        self.assertEqual(resp.status_code, 401)
        self.assertIn("authentication required", resp.json().get("detail", "").lower())

    def test_13_ask_invalid_token_rejected(self):
        """POST /ask with invalid Bearer token returns 401 Unauthorized."""
        payload = {"question": "What tasks were assigned to Kavita?"}
        resp = self.client.post("/ask", json=payload, headers=self.invalid_headers)
        self.assertEqual(resp.status_code, 401)
        self.assertIn("invalid api key or bearer token", resp.json().get("detail", "").lower())

    def test_14_ask_authenticated_bearer_success(self):
        """POST /ask with valid Bearer token returns grounded answer and source meeting IDs."""
        payload = {"question": "What tasks were assigned to Kavita?"}
        resp = self.client.post("/ask", json=payload, headers=self.bearer_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data.get("found"))
        self.assertIn(self.mid_platform, data.get("source_meeting_ids"))
        self.assertIn("Redis Sentinel", data.get("answer"))

    def test_15_ask_authenticated_api_key_header(self):
        """POST /ask with valid X-API-Key header returns grounded answer."""
        payload = {"question": "What did we decide regarding FaceID and biometrics?"}
        resp = self.client.post("/ask", json=payload, headers=self.api_key_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data.get("found"))
        self.assertIn(self.mid_security, data.get("source_meeting_ids"))

    def test_16_ask_empty_question_bad_request(self):
        """POST /ask with empty or whitespace question returns 400 Bad Request."""
        resp1 = self.client.post("/ask", json={"question": ""}, headers=self.bearer_headers)
        self.assertEqual(resp1.status_code, 400)
        self.assertIn("empty or whitespace", resp1.json().get("detail", "").lower())

        resp2 = self.client.post("/ask", json={"question": "   \n\t  "}, headers=self.bearer_headers)
        self.assertEqual(resp2.status_code, 400)

    def test_17_ask_no_result_zero_hallucination(self):
        """POST /ask returns safe 'information not found' answer with found=False for unrecorded facts."""
        payload = {"question": "What are the warp core injection ratios for starship propulsion?"}
        resp = self.client.post("/ask", json=payload, headers=self.bearer_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get("found"))
        self.assertEqual(data.get("source_meeting_ids"), [])
        self.assertIn("not found in the historical meeting records", data.get("answer"))

    # -----------------------------------------------------------------------
    # 5. Preserved Existing Endpoints Tests
    # -----------------------------------------------------------------------
    def test_18_existing_meetings_search_preserved(self):
        """GET /meetings/search remains fully functional and unchanged."""
        resp = self.client.get("/meetings/search?q=Prometheus")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        self.assertGreaterEqual(data.get("total_matches"), 1)

    def test_19_existing_meetings_ai_search_preserved(self):
        """POST /meetings/ai-search remains functional without breaking existing Milestone 3 suite."""
        resp = self.client.post("/meetings/ai-search", json={"question": "What did we decide about Redis Sentinel?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("found"))
        self.assertIn(self.mid_platform, data.get("source_meeting_ids"))

if __name__ == "__main__":
    unittest.main()
