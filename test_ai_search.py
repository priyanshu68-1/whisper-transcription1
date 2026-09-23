import unittest
import uuid
from fastapi.testclient import TestClient

from database import DatabaseManager
from api import app
from ai_search_service import AISearchEngine

class TestAIContextualMeetingSearch(unittest.TestCase):
    """
    Milestone 3 – Task 3: AI / Contextual Meeting Search Test Suite
    Verifies:
    1. AI Search Engine retrieval of historical meeting context
    2. Preservation of meeting_id on all retrieved context records
    3. Grounded answering of decision questions
    4. Grounded answering of task assignment questions
    5. Grounded answering of deadline questions
    6. Safe rejection / not-found state when info is not in repository (zero hallucination)
    7. Inclusion of source_meeting_ids in all answers
    8. Deterministic fallback grounded synthesis engine
    9. Input validation for empty questions
    10. REST API POST /meetings/ai-search validation & response schema
    11. REST API GET /meetings/ai-search validation & response schema
    """

    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager()
        cls.engine = AISearchEngine(db=cls.db)
        cls.client = TestClient(app)

        # Unique IDs for test fixtures
        cls.mid_mobile = f"AI-MEET-MOB-{uuid.uuid4().hex[:6].upper()}"
        cls.mid_api = f"AI-MEET-API-{uuid.uuid4().hex[:6].upper()}"

        # Seed meeting 1: Mobile App Roadmap
        cls.db.save_meeting(
            meeting_id=cls.mid_mobile,
            title="Q4 Mobile Application Launch Roadmap",
            audio_filename="mobile_launch_audio.mp3",
            file_size_mb=6.5,
            duration_seconds=540.0,
            format_ext=".MP3",
            language="EN",
            transcript="Priya presented the Flutter mobile application update. Arjun confirmed the iOS build is ready for beta testing.",
            intelligence={
                "summary": "The team aligned on the mobile application beta launch and finalized UI testing responsibilities.",
                "key_points": [
                    "Mobile application beta test begins next Monday on TestFlight.",
                    "Priya will manage the Play Store deployment pipeline."
                ],
                "decisions": [
                    "Approve React Native and Flutter hybrid bridge for the mobile application.",
                    "Delay Android tablet layout to Q1 next year."
                ],
                "deadlines": ["October 15th", "Next Monday"],
                "priorities": ["High", "Medium"],
                "action_items": [
                    {
                        "task": "Perform end-to-end UI testing on iOS 18",
                        "assignee": "Priya",
                        "priority": "High",
                        "deadline": "October 15th",
                        "status": "Pending"
                    },
                    {
                        "task": "Upload beta IPA build to TestFlight",
                        "assignee": "Arjun",
                        "priority": "High",
                        "deadline": "Next Monday",
                        "status": "Completed"
                    }
                ]
            },
            participant_data={
                "unique_participants": ["Priya", "Arjun"],
                "responsibilities": [
                    {"name": "Priya", "role": "Mobile Lead", "tasks": ["Perform end-to-end UI testing on iOS 18"]}
                ]
            },
            validation_info={"is_valid": True, "file_check": "PASSED", "transcript_check": "PASSED", "schema_check": "PASSED"}
        )

        # Seed meeting 2: Core API Integration Sync
        cls.db.save_meeting(
            meeting_id=cls.mid_api,
            title="Core Backend & Payment API Integration",
            audio_filename="api_sync_audio.mp3",
            file_size_mb=4.2,
            duration_seconds=360.0,
            format_ext=".MP3",
            language="EN",
            transcript="Vikram summarized the status of the Stripe payment API integration. Rate limiting webhooks are now deployed to staging.",
            intelligence={
                "summary": "Core engineering sync discussing payment API integration, OAuth2 token rotation, and webhook latency.",
                "key_points": [
                    "Stripe API integration completed on staging environment.",
                    "Webhook response time is now under 120ms."
                ],
                "decisions": [
                    "Standardize all partner integrations on REST OpenAPI v3.",
                    "Deprecate legacy SOAP billing endpoints by November."
                ],
                "deadlines": ["November 1st", "Friday 5pm"],
                "priorities": ["High", "Low"],
                "action_items": [
                    {
                        "task": "Finalize OAuth2 refresh token rotation",
                        "assignee": "Vikram",
                        "priority": "High",
                        "deadline": "November 1st",
                        "status": "In Progress"
                    }
                ]
            },
            participant_data={
                "unique_participants": ["Vikram"],
                "responsibilities": []
            },
            validation_info={"is_valid": True, "file_check": "PASSED", "transcript_check": "PASSED", "schema_check": "PASSED"}
        )

    @classmethod
    def tearDownClass(cls):
        cls.db.delete_meeting(cls.mid_mobile)
        cls.db.delete_meeting(cls.mid_api)

    # -----------------------------------------------------------------------
    # 1. CORE AI SEARCH ENGINE TESTS
    # -----------------------------------------------------------------------
    def test_search_decisions_about_mobile_app(self):
        """User question: 'What did we decide about the mobile application?'"""
        res = self.engine.answer_question("What did we decide about the mobile application?")
        self.assertTrue(res["found"])
        self.assertIn(self.mid_mobile, res["source_meeting_ids"])
        # Answer must mention decisions or hybrid bridge / tablet
        ans_lower = res["answer"].lower()
        self.assertTrue("mobile" in ans_lower or "react native" in ans_lower or "flutter" in ans_lower or "bridge" in ans_lower)

    def test_search_tasks_assigned_to_priya(self):
        """User question: 'What tasks were assigned to Priya?'"""
        res = self.engine.answer_question("What tasks were assigned to Priya?")
        self.assertTrue(res["found"])
        self.assertIn(self.mid_mobile, res["source_meeting_ids"])
        ans_lower = res["answer"].lower()
        self.assertTrue("ui testing" in ans_lower or "ios 18" in ans_lower or "priya" in ans_lower)

    def test_search_status_of_api_integration(self):
        """User question: 'What was the status of API integration?'"""
        res = self.engine.answer_question("What was the status of API integration?")
        self.assertTrue(res["found"])
        self.assertIn(self.mid_api, res["source_meeting_ids"])
        ans_lower = res["answer"].lower()
        self.assertTrue("stripe" in ans_lower or "staging" in ans_lower or "webhook" in ans_lower or "api" in ans_lower)

    def test_search_deadlines_discussed(self):
        """User question: 'What deadlines were discussed?'"""
        res = self.engine.answer_question("What deadlines were discussed for the mobile launch?")
        self.assertTrue(res["found"])
        self.assertIn(self.mid_mobile, res["source_meeting_ids"])
        ans_lower = res["answer"].lower()
        self.assertTrue("october 15th" in ans_lower or "next monday" in ans_lower or "deadline" in ans_lower)

    def test_search_non_existent_topic_returns_not_found(self):
        """User question on alien terraforming should state information not found."""
        res = self.engine.answer_question("What are the propulsion specs for intergalactic deep space warp drives?")
        self.assertFalse(res["found"])
        self.assertEqual(len(res["source_meeting_ids"]), 0)
        self.assertIn("not found in the historical meeting records", res["answer"].lower())

    def test_preserve_meeting_id_in_results(self):
        """Ensure meeting_id is strictly preserved on every source meeting record."""
        res = self.engine.answer_question("Who was responsible for UI testing?")
        self.assertTrue(res["found"])
        self.assertTrue(len(res["source_meetings"]) > 0)
        self.assertIn(self.mid_mobile, res["source_meeting_ids"])
        for src in res["source_meetings"]:
            self.assertIn("meeting_id", src)
            self.assertTrue(src["meeting_id"].startswith("AI-MEET-") or src["meeting_id"].startswith("MEET-"))

    def test_empty_question_validation(self):
        """Empty or whitespace-only questions must raise ValueError."""
        with self.assertRaises(ValueError):
            self.engine.answer_question("")
        with self.assertRaises(ValueError):
            self.engine.answer_question("   ")

    def test_fallback_engine_directly(self):
        """Fallback grounded engine generates accurate synthesis when LLM is unavailable."""
        candidates = self.engine.retrieve_relevant_meetings("Priya UI testing", limit=2)
        self.assertTrue(len(candidates) > 0)
        fallback_res = self.engine._fallback_grounded_search("What tasks were assigned to Priya?", candidates)
        self.assertTrue(fallback_res["found"])
        self.assertIn(self.mid_mobile, fallback_res["source_meeting_ids"])
        self.assertIn("Priya", fallback_res["answer"])

    # -----------------------------------------------------------------------
    # 2. REST API ENDPOINT TESTS
    # -----------------------------------------------------------------------
    def test_api_post_ai_search_success(self):
        resp = self.client.post("/meetings/ai-search", json={"question": "What tasks were assigned to Priya?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["question"], "What tasks were assigned to Priya?")
        self.assertTrue(data["found"])
        self.assertIn(self.mid_mobile, data["source_meeting_ids"])
        self.assertIsInstance(data["source_meetings"], list)

    def test_api_post_ai_search_empty_question(self):
        resp = self.client.post("/meetings/ai-search", json={"question": "   "})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("cannot be empty", resp.json()["detail"])

    def test_api_get_ai_search_success(self):
        resp = self.client.get("/meetings/ai-search?q=What+was+the+status+of+API+integration")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["found"])
        self.assertIn(self.mid_api, data["source_meeting_ids"])

    def test_api_get_ai_search_empty_query(self):
        resp = self.client.get("/meetings/ai-search?q=")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("cannot be empty", resp.json()["detail"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
