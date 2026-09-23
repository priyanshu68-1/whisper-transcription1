import os
import unittest
import uuid
from datetime import datetime
from fastapi.testclient import TestClient

from database import DatabaseManager
from api import app

class TestMeetingSearchAndRetrieval(unittest.TestCase):
    """
    Milestone 3 – Task 2: Meeting Search & Retrieval Test Suite
    Verifies:
    1. Search across meeting title
    2. Search across metadata (format, language, audio_filename)
    3. Search across Whisper transcript
    4. Search across LLM summary
    5. Search across key points
    6. Search across decisions
    7. Search across action items (task, assignee, priority)
    8. Search across participants
    9. Search across deadlines
    10. Case-insensitive matching
    11. Safe handling of empty search queries
    12. Filtering by participant
    13. Filtering by date
    14. Filtering by title
    15. Safe handling of non-matching queries
    16. Inclusion of meeting_id in all search results
    17. Zero cross-meeting data contamination
    18. API endpoint GET /meetings/search with query, filters, and error handling
    """

    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager()
        cls.client = TestClient(app)

        # Unique IDs for test fixtures
        cls.mid_arch = f"SEARCH-MEET-ARCH-{uuid.uuid4().hex[:6].upper()}"
        cls.mid_sec = f"SEARCH-MEET-SEC-{uuid.uuid4().hex[:6].upper()}"

        # Seed meeting 1: Architecture Sync
        cls.db.save_meeting(
            meeting_id=cls.mid_arch,
            title="Cloud Microservices & Redis Architecture",
            audio_filename="cloud_arch_recording.mp3",
            file_size_mb=8.40,
            duration_seconds=720.0,
            format_ext=".MP3",
            language="EN",
            transcript="Rohan outlined the Kubernetes cluster configuration. Samantha raised concerns about Redis caching latency during peak load.",
            intelligence={
                "summary": "Engineering team evaluated Kubernetes migration and Redis distributed caching for microservices latency reduction.",
                "key_points": [
                    "Evaluate Redis distributed cache latency under 10k RPS.",
                    "Migrate Kubernetes cluster by end of Q4."
                ],
                "decisions": [
                    "Adopt Redis Sentinel for high availability caching.",
                    "Provision secondary Kubernetes staging cluster."
                ],
                "deadlines": ["Next Wednesday 3 PM", "November 15"],
                "priorities": ["Critical", "High"],
                "action_items": [
                    {
                        "task": "Benchmark Redis throughput with synthetic load",
                        "assignee": "Rohan",
                        "priority": "Critical",
                        "deadline": "Next Wednesday 3 PM",
                        "status": "Pending"
                    },
                    {
                        "task": "Draft Kubernetes cluster deployment Helm charts",
                        "assignee": "Samantha",
                        "priority": "High",
                        "deadline": "November 15",
                        "status": "In Progress"
                    }
                ]
            },
            participant_data={
                "unique_participants": ["Rohan Sharma", "Samantha Fox"],
                "responsibilities": []
            },
            validation_info={"is_valid": True, "file_check": "PASSED", "transcript_check": "PASSED", "schema_check": "PASSED"}
        )

        # Seed meeting 2: Security & Compliance Review
        cls.db.save_meeting(
            meeting_id=cls.mid_sec,
            title="SOC2 Compliance & Zero Trust Audit",
            audio_filename="security_audit.wav",
            file_size_mb=15.60,
            duration_seconds=950.0,
            format_ext=".WAV",
            language="FR",
            transcript="Alexandre presented the encryption key rotation policy. Danielle audited the RBAC IAM permissions for SOC2 compliance.",
            intelligence={
                "summary": "Security board reviewed encryption keys, zero trust policies, and finalized the SOC2 audit schedule.",
                "key_points": [
                    "Rotate AES-256 master keys every 90 days.",
                    "Audit IAM least privilege access."
                ],
                "decisions": [
                    "Enforce MFA across all administrative console accounts.",
                    "Formalize Zero Trust protocol for external vendors."
                ],
                "deadlines": ["December 1st", "Next Friday"],
                "priorities": ["High", "Medium"],
                "action_items": [
                    {
                        "task": "Revoke unused AWS IAM credentials",
                        "assignee": "Danielle",
                        "priority": "High",
                        "deadline": "Next Friday",
                        "status": "Pending"
                    },
                    {
                        "task": "Configure automated KMS key rotation",
                        "assignee": "Alexandre",
                        "priority": "Medium",
                        "deadline": "December 1st",
                        "status": "Completed"
                    }
                ]
            },
            participant_data={
                "unique_participants": ["Alexandre", "Danielle"],
                "responsibilities": []
            },
            validation_info={"is_valid": True, "file_check": "PASSED", "transcript_check": "PASSED", "schema_check": "PASSED"}
        )

    @classmethod
    def tearDownClass(cls):
        cls.db.delete_meeting(cls.mid_arch)
        cls.db.delete_meeting(cls.mid_sec)

    # -----------------------------------------------------------------------
    # Requirement 2.1: Search by title
    # -----------------------------------------------------------------------
    def test_01_search_by_title(self):
        results = self.db.search_meetings(query="Microservices")
        self.assertGreaterEqual(len(results), 1)
        mids = [r["meeting_id"] for r in results]
        self.assertIn(self.mid_arch, mids)
        self.assertNotIn(self.mid_sec, mids)
        self.assertIn("title", results[0]["matched_fields"])

    # -----------------------------------------------------------------------
    # Requirement 2.2: Search by metadata (format, filename, language)
    # -----------------------------------------------------------------------
    def test_02_search_by_metadata(self):
        # By filename
        res_file = self.db.search_meetings(query="security_audit")
        mids_file = [r["meeting_id"] for r in res_file]
        self.assertIn(self.mid_sec, mids_file)
        self.assertIn("metadata", res_file[0]["matched_fields"])

        # By format
        res_fmt = self.db.search_meetings(query=".WAV")
        mids_fmt = [r["meeting_id"] for r in res_fmt]
        self.assertIn(self.mid_sec, mids_fmt)

    # -----------------------------------------------------------------------
    # Requirement 2.3: Search by transcript
    # -----------------------------------------------------------------------
    def test_03_search_by_transcript(self):
        results = self.db.search_meetings(query="peak load")
        self.assertGreaterEqual(len(results), 1)
        mids = [r["meeting_id"] for r in results]
        self.assertIn(self.mid_arch, mids)
        self.assertIn("transcript", results[0]["matched_fields"])
        self.assertIn("peak load", results[0]["match_snippets"]["transcript"].lower())

    # -----------------------------------------------------------------------
    # Requirement 2.4: Search by summary
    # -----------------------------------------------------------------------
    def test_04_search_by_summary(self):
        results = self.db.search_meetings(query="latency reduction")
        self.assertGreaterEqual(len(results), 1)
        mids = [r["meeting_id"] for r in results]
        self.assertIn(self.mid_arch, mids)
        self.assertIn("summary", results[0]["matched_fields"])

    # -----------------------------------------------------------------------
    # Requirement 2.5: Search by key points
    # -----------------------------------------------------------------------
    def test_05_search_by_key_points(self):
        results = self.db.search_meetings(query="10k RPS")
        self.assertGreaterEqual(len(results), 1)
        mids = [r["meeting_id"] for r in results]
        self.assertIn(self.mid_arch, mids)
        self.assertIn("key_points", results[0]["matched_fields"])

    # -----------------------------------------------------------------------
    # Requirement 2.6: Search by decisions
    # -----------------------------------------------------------------------
    def test_06_search_by_decisions(self):
        results = self.db.search_meetings(query="Redis Sentinel")
        self.assertGreaterEqual(len(results), 1)
        mids = [r["meeting_id"] for r in results]
        self.assertIn(self.mid_arch, mids)
        self.assertIn("decisions", results[0]["matched_fields"])

    # -----------------------------------------------------------------------
    # Requirement 2.7: Search by action items (task and assignee)
    # -----------------------------------------------------------------------
    def test_07_search_by_action_items(self):
        # By task text
        res_task = self.db.search_meetings(query="Helm charts")
        self.assertGreaterEqual(len(res_task), 1)
        self.assertIn(self.mid_arch, [r["meeting_id"] for r in res_task])
        self.assertIn("action_items", res_task[0]["matched_fields"])

        # By assignee in task
        res_assignee = self.db.search_meetings(query="Danielle")
        self.assertGreaterEqual(len(res_assignee), 1)
        self.assertIn(self.mid_sec, [r["meeting_id"] for r in res_assignee])

    # -----------------------------------------------------------------------
    # Requirement 2.8: Search by participants
    # -----------------------------------------------------------------------
    def test_08_search_by_participants(self):
        results = self.db.search_meetings(query="Samantha Fox")
        self.assertGreaterEqual(len(results), 1)
        mids = [r["meeting_id"] for r in results]
        self.assertIn(self.mid_arch, mids)
        self.assertIn("participants", results[0]["matched_fields"])

    # -----------------------------------------------------------------------
    # Requirement 2.9: Search by deadlines
    # -----------------------------------------------------------------------
    def test_09_search_by_deadlines(self):
        results = self.db.search_meetings(query="November 15")
        self.assertGreaterEqual(len(results), 1)
        mids = [r["meeting_id"] for r in results]
        self.assertIn(self.mid_arch, mids)
        self.assertIn("deadlines", results[0]["matched_fields"])

    # -----------------------------------------------------------------------
    # Requirement 4: Case-insensitive search
    # -----------------------------------------------------------------------
    def test_10_case_insensitivity(self):
        r_lower = self.db.search_meetings(query="kubernetes")
        r_upper = self.db.search_meetings(query="KUBERNETES")
        r_mixed = self.db.search_meetings(query="KuBeRnEtEs")

        self.assertEqual(len(r_lower), len(r_upper))
        self.assertEqual(len(r_lower), len(r_mixed))
        self.assertGreaterEqual(len(r_lower), 1)

    # -----------------------------------------------------------------------
    # Requirement 5: Empty search query handling
    # -----------------------------------------------------------------------
    def test_11_empty_search_query_handling(self):
        # Empty string and whitespace should safely return all meetings without error
        r_empty = self.db.search_meetings(query="")
        r_space = self.db.search_meetings(query="   ")
        r_none = self.db.search_meetings(query=None)

        self.assertGreaterEqual(len(r_empty), 2)
        self.assertEqual(len(r_empty), len(r_space))
        self.assertEqual(len(r_empty), len(r_none))

    # -----------------------------------------------------------------------
    # Requirement 9.1: Filter by participant
    # -----------------------------------------------------------------------
    def test_12_filter_by_participant(self):
        results = self.db.search_meetings(participant="Alexandre")
        self.assertGreaterEqual(len(results), 1)
        for r in results:
            self.assertIn("Alexandre", r["participants"])

    # -----------------------------------------------------------------------
    # Requirement 9.2: Filter by date
    # -----------------------------------------------------------------------
    def test_13_filter_by_date(self):
        today_str = datetime.now().strftime("%Y-%m-%d")
        results = self.db.search_meetings(date=today_str)
        self.assertGreaterEqual(len(results), 2)
        for r in results:
            self.assertTrue(r["created_at"].startswith(today_str))

    # -----------------------------------------------------------------------
    # Requirement 9.3: Filter by title
    # -----------------------------------------------------------------------
    def test_14_filter_by_title(self):
        results = self.db.search_meetings(title="Zero Trust")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["meeting_id"], self.mid_sec)

    # -----------------------------------------------------------------------
    # Requirement 11: Non-matching search query
    # -----------------------------------------------------------------------
    def test_15_non_matching_search_returns_empty_list(self):
        results = self.db.search_meetings(query="NONEXISTENT_KEYWORD_XYZ_99999")
        self.assertEqual(len(results), 0)
        self.assertIsInstance(results, list)

    # -----------------------------------------------------------------------
    # Requirement 7 & 8: meeting_id included and cross-meeting isolation
    # -----------------------------------------------------------------------
    def test_16_meeting_id_inclusion_and_data_integrity(self):
        results = self.db.search_meetings(query="SOC2")
        self.assertGreaterEqual(len(results), 1)
        for r in results:
            self.assertTrue(r["meeting_id"])
            self.assertIn("meeting_id", r)
            # Ensure no internal sqlite autoincrement ids are exposed
            self.assertNotIn("summaries_id", r)
            self.assertNotIn("validation_logs_id", r)

    # -----------------------------------------------------------------------
    # Requirement 3 & 11: REST API GET /meetings/search
    # -----------------------------------------------------------------------
    def test_17_api_search_endpoint(self):
        # 1. Search with query
        res = self.client.get("/meetings/search?q=Microservices")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["total_matches"], 1)
        self.assertIn(self.mid_arch, [r["meeting_id"] for r in data["results"]])

        # 2. Search with participant filter
        res_p = self.client.get("/meetings/search?participant=Rohan")
        self.assertEqual(res_p.status_code, 200)
        self.assertGreaterEqual(res_p.json()["total_matches"], 1)

        # 3. Empty query returns 200 with all results
        res_empty = self.client.get("/meetings/search?q=")
        self.assertEqual(res_empty.status_code, 200)
        self.assertGreaterEqual(res_empty.json()["total_matches"], 2)

        # 4. Invalid date format returns 400 Bad Request
        res_inv_date = self.client.get("/meetings/search?date=INVALID_DATE_;;--")
        self.assertEqual(res_inv_date.status_code, 400)
        self.assertIn("Invalid date", res_inv_date.json()["detail"])

        # 5. Non-matching query returns 200 with empty list
        res_none = self.client.get("/meetings/search?q=ZEBRA_ON_MARS_12345")
        self.assertEqual(res_none.status_code, 200)
        self.assertEqual(res_none.json()["total_matches"], 0)
        self.assertEqual(res_none.json()["results"], [])


if __name__ == "__main__":
    unittest.main()
