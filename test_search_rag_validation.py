import os
import unittest
import uuid
from datetime import datetime
from fastapi.testclient import TestClient

from database import DatabaseManager
from api import app
from ai_search_service import AISearchEngine

class TestSearchAndRAGValidation(unittest.TestCase):
    """
    MILESTONE 3 – TASK 7: SEARCH & RAG VALIDATION
    Comprehensive validation test suite covering:
    1. Relevant Meeting Retrieval
    2. Irrelevant Query Handling
    3. Multiple Matching Meetings
    4. Date-Based Filtering
    5. Meeting Metadata Filtering
    6. Source Validation
    7. Context Validation
    8. Grounded Answer Validation
    9. Empty Search Results
    10. Defect Identification & Verification
    """

    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager()
        cls.engine = AISearchEngine(db=cls.db)
        cls.client = TestClient(app)

        # Unique IDs for validation fixtures
        cls.mid_mobile = f"VAL-MEET-MOB-{uuid.uuid4().hex[:6].upper()}"
        cls.mid_api = f"VAL-MEET-API-{uuid.uuid4().hex[:6].upper()}"
        cls.mid_sec1 = f"VAL-MEET-SEC1-{uuid.uuid4().hex[:6].upper()}"
        cls.mid_sec2 = f"VAL-MEET-SEC2-{uuid.uuid4().hex[:6].upper()}"
        cls.mid_irrel = f"VAL-MEET-IRR-{uuid.uuid4().hex[:6].upper()}"

        # 1. Seed Mobile Application Meeting
        cls.db.save_meeting(
            meeting_id=cls.mid_mobile,
            title="Q4 Mobile Application Launch Roadmap",
            audio_filename="mobile_launch_audio.mp3",
            file_size_mb=6.5,
            duration_seconds=540.0,
            format_ext=".MP3",
            language="EN",
            transcript="Priya presented the Flutter mobile application update. Priya confirmed she is handling UI testing. Arjun reviewed iOS build.",
            intelligence={
                "summary": "Team aligned on mobile application launch and confirmed Priya leads UI testing.",
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

        # 2. Seed API Integration Meeting
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

        # 3. Seed Security Meeting 1
        cls.db.save_meeting(
            meeting_id=cls.mid_sec1,
            title="Enterprise Security Compliance Sync Part 1",
            audio_filename="sec_part1.wav",
            file_size_mb=9.1,
            duration_seconds=600.0,
            format_ext=".WAV",
            language="EN",
            transcript="Marcus reviewed SOC2 security compliance controls and zero-trust IAM policy enforcement.",
            intelligence={
                "summary": "Security compliance discussion focused on SOC2 trust criteria and IAM credential rotation.",
                "key_points": ["Audit SOC2 security controls.", "Rotate root API keys."],
                "decisions": ["Adopt zero-trust architecture for production VPC."],
                "deadlines": ["December 15th"],
                "priorities": ["Critical"],
                "action_items": [
                    {
                        "task": "Audit SOC2 security controls across AWS accounts",
                        "assignee": "Marcus",
                        "priority": "Critical",
                        "deadline": "December 15th",
                        "status": "Pending"
                    }
                ]
            },
            participant_data={"unique_participants": ["Marcus"], "responsibilities": []},
            validation_info={"is_valid": True, "file_check": "PASSED", "transcript_check": "PASSED", "schema_check": "PASSED"}
        )

        # 4. Seed Security Meeting 2 (Multiple matching partner meeting)
        cls.db.save_meeting(
            meeting_id=cls.mid_sec2,
            title="Enterprise Security Compliance Sync Part 2",
            audio_filename="sec_part2.wav",
            file_size_mb=7.8,
            duration_seconds=480.0,
            format_ext=".WAV",
            language="EN",
            transcript="Elena audited GDPR data privacy and SOC2 security compliance encryption at rest.",
            intelligence={
                "summary": "Second security compliance review covering database encryption and data retention protocols.",
                "key_points": ["Enable AES-256 database encryption.", "Finalize GDPR data retention policy."],
                "decisions": ["Enforce TLS 1.3 across all microservices."],
                "deadlines": ["December 20th"],
                "priorities": ["High"],
                "action_items": [
                    {
                        "task": "Configure TLS 1.3 on cloud load balancers",
                        "assignee": "Elena",
                        "priority": "High",
                        "deadline": "December 20th",
                        "status": "In Progress"
                    }
                ]
            },
            participant_data={"unique_participants": ["Elena"], "responsibilities": []},
            validation_info={"is_valid": True, "file_check": "PASSED", "transcript_check": "PASSED", "schema_check": "PASSED"}
        )

        # 5. Seed Irrelevant Meeting (Catering & Cafeteria Menu)
        cls.db.save_meeting(
            meeting_id=cls.mid_irrel,
            title="Office Cafeteria Catering & Lunch Logistics",
            audio_filename="cafeteria_lunch.mp3",
            file_size_mb=3.0,
            duration_seconds=200.0,
            format_ext=".MP3",
            language="EN",
            transcript="Carlos reviewed coffee machine repairs and vegetarian lunch catering options for Friday.",
            intelligence={
                "summary": "Discussion of office kitchen supplies, coffee machines, and weekly catering schedules.",
                "key_points": ["Order new espresso beans.", "Select Friday taco vendor."],
                "decisions": ["Switch office coffee vendor to local roaster."],
                "deadlines": ["This Friday"],
                "priorities": ["Low"],
                "action_items": [
                    {
                        "task": "Order vegan sandwiches for Friday lunch",
                        "assignee": "Carlos",
                        "priority": "Low",
                        "deadline": "This Friday",
                        "status": "Completed"
                    }
                ]
            },
            participant_data={"unique_participants": ["Carlos"], "responsibilities": []},
            validation_info={"is_valid": True, "file_check": "PASSED", "transcript_check": "PASSED", "schema_check": "PASSED"}
        )

    @classmethod
    def tearDownClass(cls):
        for mid in [cls.mid_mobile, cls.mid_api, cls.mid_sec1, cls.mid_sec2, cls.mid_irrel]:
            try:
                cls.db.delete_meeting(mid)
            except Exception:
                pass

    # -----------------------------------------------------------------------
    # 1. RELEVANT MEETING RETRIEVAL
    # -----------------------------------------------------------------------
    def test_val_01_a_priya_work(self):
        """VAL-01-A: 'What did Priya work on?' retrieves mobile meeting."""
        res = self.engine.answer_question("What did Priya work on?")
        self.assertTrue(res["found"])
        self.assertIn(self.mid_mobile, res["source_meeting_ids"])
        self.assertNotIn(self.mid_api, res["source_meeting_ids"])
        self.assertNotIn(self.mid_irrel, res["source_meeting_ids"])
        ans_lower = res["answer"].lower()
        self.assertTrue("ui testing" in ans_lower or "ios 18" in ans_lower or "priya" in ans_lower)

    def test_val_01_b_mobile_app_decisions(self):
        """VAL-01-B: 'What was decided about the mobile application?' retrieves mobile meeting."""
        res = self.engine.answer_question("What was decided about the mobile application?")
        self.assertTrue(res["found"])
        self.assertIn(self.mid_mobile, res["source_meeting_ids"])
        ans_lower = res["answer"].lower()
        self.assertTrue("react native" in ans_lower or "flutter" in ans_lower or "bridge" in ans_lower or "hybrid" in ans_lower)

    def test_val_01_c_api_integration_status(self):
        """VAL-01-C: 'What was the API integration status?' retrieves API meeting."""
        res = self.engine.answer_question("What was the API integration status?")
        self.assertTrue(res["found"])
        self.assertIn(self.mid_api, res["source_meeting_ids"])
        self.assertNotIn(self.mid_mobile, res["source_meeting_ids"])
        ans_lower = res["answer"].lower()
        self.assertTrue("stripe" in ans_lower or "staging" in ans_lower or "webhook" in ans_lower or "api" in ans_lower)

    def test_val_01_d_ui_testing_responsibility(self):
        """VAL-01-D: 'Who was responsible for UI testing?' retrieves mobile meeting with Priya."""
        res = self.engine.answer_question("Who was responsible for UI testing?")
        self.assertTrue(res["found"])
        self.assertIn(self.mid_mobile, res["source_meeting_ids"])
        self.assertIn("Priya", res["answer"])

    # -----------------------------------------------------------------------
    # 2. IRRELEVANT QUERY HANDLING
    # -----------------------------------------------------------------------
    def test_val_02_a_weather_on_mars(self):
        """VAL-02-A: 'What is the weather on Mars?' must not return unrelated meeting records."""
        # 1. Direct context retrieval must be empty
        retrieved = self.engine.retrieve_context("What is the weather on Mars?")
        self.assertEqual(len(retrieved), 0)

        # 2. End-to-end question answering must return not found
        res = self.engine.answer_question("What is the weather on Mars?")
        self.assertFalse(res["found"])
        self.assertEqual(len(res["source_meeting_ids"]), 0)
        self.assertEqual(len(res["sources"]), 0)
        self.assertIn("not found in the historical meeting records", res["answer"].lower())

    def test_val_02_b_warp_drive_specs(self):
        """VAL-02-B: Query on intergalactic propulsion specs returns not found."""
        retrieved = self.engine.retrieve_context("What are the propulsion specs for intergalactic deep space warp drives?")
        self.assertEqual(len(retrieved), 0)
        res = self.engine.answer_question("What are the propulsion specs for intergalactic deep space warp drives?")
        self.assertFalse(res["found"])
        self.assertEqual(len(res["source_meeting_ids"]), 0)
        self.assertIn("not found in the historical meeting records", res["answer"].lower())

    # -----------------------------------------------------------------------
    # 3. MULTIPLE MATCHING MEETINGS
    # -----------------------------------------------------------------------
    def test_val_03_a_multiple_matching_retrieval(self):
        """VAL-03-A: Question where multiple historical meetings contain relevant info."""
        retrieved = self.engine.retrieve_context("security compliance SOC2")
        mids = [m["meeting_id"] for m in retrieved]
        self.assertIn(self.mid_sec1, mids)
        self.assertIn(self.mid_sec2, mids)
        self.assertNotIn(self.mid_irrel, mids)

    def test_val_03_b_multiple_matching_synthesis(self):
        """VAL-03-B: RAG answer cites both matching meetings and excludes irrelevant."""
        res = self.engine.answer_question("What decisions and action items were discussed for security compliance?")
        self.assertTrue(res["found"])
        self.assertIn(self.mid_sec1, res["source_meeting_ids"])
        self.assertIn(self.mid_sec2, res["source_meeting_ids"])
        self.assertNotIn(self.mid_irrel, res["source_meeting_ids"])
        # Both Marcus and Elena or their tasks should appear in answer
        ans_lower = res["answer"].lower()
        self.assertTrue("soc2" in ans_lower or "tls" in ans_lower or "zero-trust" in ans_lower or "security" in ans_lower)

    # -----------------------------------------------------------------------
    # 4. DATE-BASED FILTERING
    # -----------------------------------------------------------------------
    def test_val_04_a_date_prefix_filter(self):
        """VAL-04-A: Filter search by date prefix (e.g. today's date YYYY-MM-DD)."""
        today_prefix = datetime.now().strftime("%Y-%m-%d")
        results = self.db.search_meetings(query="Mobile Application", date=today_prefix)
        self.assertGreaterEqual(len(results), 1)
        mids = [r["meeting_id"] for r in results]
        self.assertIn(self.mid_mobile, mids)

    def test_val_04_b_date_range_filter(self):
        """VAL-04-B: Filter search using start_date and end_date range."""
        results = self.db.search_meetings(
            query="Security Compliance",
            start_date="2020-01-01",
            end_date="2030-12-31"
        )
        self.assertGreaterEqual(len(results), 2)
        mids = [r["meeting_id"] for r in results]
        self.assertIn(self.mid_sec1, mids)
        self.assertIn(self.mid_sec2, mids)

    def test_val_04_c_out_of_range_date_filter(self):
        """VAL-04-C: Date filter outside meeting creation period returns 0 results."""
        results = self.db.search_meetings(
            query="Mobile Application",
            start_date="2015-01-01",
            end_date="2015-12-31"
        )
        self.assertEqual(len(results), 0)

    # -----------------------------------------------------------------------
    # 5. MEETING METADATA FILTERING
    # -----------------------------------------------------------------------
    def test_val_05_a_filter_by_title(self):
        """VAL-05-A: Filter by title substring."""
        results = self.db.search_meetings(title="Roadmap")
        self.assertGreaterEqual(len(results), 1)
        mids = [r["meeting_id"] for r in results]
        self.assertIn(self.mid_mobile, mids)
        self.assertNotIn(self.mid_api, mids)

    def test_val_05_b_filter_by_participant(self):
        """VAL-05-B: Filter by participant name."""
        results = self.db.search_meetings(participant="Vikram")
        self.assertGreaterEqual(len(results), 1)
        mids = [r["meeting_id"] for r in results]
        self.assertIn(self.mid_api, mids)
        self.assertNotIn(self.mid_mobile, mids)

    def test_val_05_c_filter_by_format(self):
        """VAL-05-C: Filter by format extension (.WAV vs .MP3)."""
        wav_results = self.db.search_meetings(format=".WAV")
        wav_mids = [r["meeting_id"] for r in wav_results]
        self.assertIn(self.mid_sec1, wav_mids)
        self.assertIn(self.mid_sec2, wav_mids)
        self.assertNotIn(self.mid_mobile, wav_mids)

    def test_val_05_d_combined_metadata_filters(self):
        """VAL-05-D: Combined metadata filtering (title + participant)."""
        results = self.db.search_meetings(title="Mobile", participant="Priya")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["meeting_id"], self.mid_mobile)

    # -----------------------------------------------------------------------
    # 6. SOURCE VALIDATION
    # -----------------------------------------------------------------------
    def test_val_06_a_source_meeting_id_retention(self):
        """VAL-06-A: Every RAG result retains valid meeting_id and complete metadata."""
        res = self.engine.answer_question("What was decided about the mobile application?")
        self.assertTrue(res["found"])
        self.assertTrue(len(res["sources"]) > 0)
        for s in res["sources"]:
            self.assertIn("meeting_id", s)
            self.assertTrue(isinstance(s["meeting_id"], str) and len(s["meeting_id"]) > 5)
            self.assertTrue(any(s["meeting_id"].startswith(pfx) for pfx in ["VAL-MEET-", "AI-MEET-", "MEET-", "SEARCH-MEET-"]))
            self.assertIn("title", s)
            self.assertIn("summary", s)
            self.assertIn("action_items", s)
            self.assertIn("decisions", s)

    def test_val_06_b_source_content_contains_fact(self):
        """VAL-06-B: The source meeting actually contains the information used for the answer."""
        res = self.engine.answer_question("What tasks were assigned to Vikram?")
        self.assertTrue(res["found"])
        self.assertIn(self.mid_api, res["source_meeting_ids"])
        source_rec = next((s for s in res["sources"] if s["meeting_id"] == self.mid_api), None)
        self.assertIsNotNone(source_rec)
        tasks = [act["task"] for act in source_rec["action_items"]]
        self.assertTrue(any("OAuth2" in t for t in tasks))

    # -----------------------------------------------------------------------
    # 7. CONTEXT VALIDATION
    # -----------------------------------------------------------------------
    def test_val_07_a_context_comes_only_from_retrieved_meetings(self):
        """VAL-07-A: Context text contains strictly retrieved meetings and no others."""
        meetings = self.engine.retrieve_context("Priya UI testing", max_meetings=2)
        context_text = self.engine.build_prompt_context(meetings)
        self.assertIn(self.mid_mobile, context_text)
        self.assertNotIn(self.mid_irrel, context_text)
        self.assertNotIn(self.mid_api, context_text)

    def test_val_07_b_context_isolation_empty_for_unrelated(self):
        """VAL-07-B: Unrelated query produces no context blocks."""
        meetings = self.engine.retrieve_context("What is the weather on Mars?")
        context_text = self.engine.build_prompt_context(meetings)
        self.assertEqual(context_text, "No meeting records found in repository.")

    # -----------------------------------------------------------------------
    # 8. GROUNDED ANSWER VALIDATION
    # -----------------------------------------------------------------------
    def test_val_08_a_zero_hallucination_on_factual_answers(self):
        """VAL-08-A: Answer uses only retrieved facts and does not invent participants or deadlines."""
        res = self.engine.answer_question("Who was responsible for UI testing?")
        self.assertTrue(res["found"])
        ans = res["answer"]
        self.assertIn("Priya", ans)
        # Should not invent unknown names
        for fake in ["Alice", "Bob", "Charlie", "David", "Zuckerberg", "Musk"]:
            self.assertNotIn(fake, ans)

    def test_val_08_b_missing_detail_returns_not_found(self):
        """VAL-08-B: When query asks about unmentioned detail within a known topic, state not found."""
        res = self.engine.answer_question("What cryptocurrency budget was allocated for the mobile launch?")
        # Mobile launch is known, but cryptocurrency budget was never discussed
        self.assertFalse(res["found"])
        self.assertEqual(len(res["source_meeting_ids"]), 0)
        self.assertIn("not found in the historical meeting records", res["answer"].lower())

    # -----------------------------------------------------------------------
    # 9. EMPTY SEARCH RESULTS
    # -----------------------------------------------------------------------
    def test_val_09_a_no_matching_keyword(self):
        """VAL-09-A: Non-matching keyword search returns empty list without crashing."""
        results = self.db.search_meetings(query="NONEXISTENT_KEYWORD_XYZ_8888")
        self.assertEqual(len(results), 0)

    def test_val_09_b_no_matching_semantic_query(self):
        """VAL-09-B: Non-matching semantic query returns empty list without crashing."""
        results = self.engine.semantic_search("quantum blockchain interstellar teleportation")
        self.assertEqual(len(results), 0)

    def test_val_09_c_unknown_participant(self):
        """VAL-09-C: Unknown participant search returns empty list."""
        results = self.db.search_meetings(participant="DoctorWho_9999")
        self.assertEqual(len(results), 0)

    def test_val_09_d_unknown_meeting_id(self):
        """VAL-09-D: Unknown meeting ID lookup returns None safely."""
        meeting = self.db.get_meeting("MEET-DOESNOTEXIST-000")
        self.assertIsNone(meeting)

    def test_val_09_e_api_empty_search_endpoint(self):
        """VAL-09-E: API GET /search with non-matching query returns total_matches=0 without crashing."""
        resp = self.client.get("/search?q=NONEXISTENT_KEYWORD_XYZ_8888")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_matches"], 0)
        self.assertEqual(len(data["results"]), 0)

    # -----------------------------------------------------------------------
    # 10. DEFECT VERIFICATION & API RAG ENDPOINT TEST
    # -----------------------------------------------------------------------
    def test_val_10_a_api_ask_rag_endpoint(self):
        """VAL-10-A: Authenticated POST /ask endpoint returns grounded answer with meeting_id."""
        resp = self.client.post(
            "/ask",
            json={"question": "What tasks were assigned to Priya?"},
            headers={"X-API-Key": "truthshield-secret-token-2026"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["found"])
        self.assertIn(self.mid_mobile, data["source_meeting_ids"])
        self.assertTrue(len(data["sources"]) > 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
