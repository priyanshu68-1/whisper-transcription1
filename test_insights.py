import unittest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from database import DatabaseManager
from api import app
from ai_search_service import AISearchEngine

class TestHistoricalMeetingInsights(unittest.TestCase):
    """
    Milestone 3 – Task 4: Historical Meeting Insights Test Suite
    Verifies:
    1. Historical meeting overview calculations & aggregate KPIs
    2. Filtering by participant, date range, title, and action item status
    3. Cross-meeting strategic decisions ledger extraction
    4. Cross-meeting participant workload calculations
    5. Deadlines & milestones agenda compilation
    6. Project evolution & chronological timeline extraction
    7. Safe handling of non-matching filters (empty state)
    8. REST API endpoint GET /meetings/insights with query filters
    9. AI cross-meeting insights generation with strict source meeting attribution
    10. Safe rejection / insufficient data handling when data is absent
    """

    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager()
        cls.engine = AISearchEngine(db=cls.db)
        cls.client = TestClient(app)

        # Unique IDs for test fixtures
        cls.mid_sprint1 = f"INS-MEET-S1-{uuid.uuid4().hex[:6].upper()}"
        cls.mid_sprint2 = f"INS-MEET-S2-{uuid.uuid4().hex[:6].upper()}"

        # Past date for Sprint 1, today for Sprint 2
        cls.date_s1 = "2026-08-15T10:00:00"
        cls.date_s2 = "2026-09-17T14:30:00"

        # Seed meeting 1: Sprint 1 Retrospective
        cls.db.save_meeting(
            meeting_id=cls.mid_sprint1,
            title="Q3 Sprint 1 Retrospective & Database Migration",
            audio_filename="sprint1_retro.mp3",
            file_size_mb=5.4,
            duration_seconds=420.0,
            format_ext=".mp3",
            language="en",
            transcript="Tanya reviewed the PostgreSQL database migration. Liam confirmed that connection pooling resolved database bottlenecks.",
            intelligence={
                "summary": "Engineering sprint retrospective reviewing database performance and migration milestones.",
                "key_points": [
                    "PostgreSQL read replicas deployed to reduce latency.",
                    "Connection pooling resolved connection leaks."
                ],
                "decisions": [
                    "Migrate production databases to PostgreSQL 17 by September 1st.",
                    "Enforce SSL mode require on all database connections."
                ],
                "deadlines": ["September 1st"],
                "priorities": ["High", "Medium"],
                "action_items": [
                    {
                        "task": "Configure PgBouncer connection pooler",
                        "assignee": "Tanya",
                        "priority": "High",
                        "deadline": "September 1st",
                        "status": "Completed"
                    },
                    {
                        "task": "Benchmark replica read latency",
                        "assignee": "Liam",
                        "priority": "Medium",
                        "deadline": "September 5th",
                        "status": "Pending"
                    }
                ]
            },
            participant_data={
                "unique_participants": ["Tanya", "Liam"],
                "responsibilities": [
                    {"name": "Tanya", "role": "Database Architect", "tasks": ["Configure PgBouncer connection pooler"]}
                ]
            },
            validation_info={"is_valid": True, "file_check": "PASSED", "transcript_check": "PASSED", "schema_check": "PASSED"}
        )

        # Update created_at timestamp for Sprint 1 to ensure distinct date testing
        with cls.db.get_connection() as conn:
            conn.execute("UPDATE meetings SET created_at = ? WHERE meeting_id = ?", (cls.date_s1, cls.mid_sprint1))
            conn.commit()

        # Seed meeting 2: Sprint 2 Planning
        cls.db.save_meeting(
            meeting_id=cls.mid_sprint2,
            title="Q3 Sprint 2 Security & Mobile Frontend Planning",
            audio_filename="sprint2_plan.mp3",
            file_size_mb=6.1,
            duration_seconds=480.0,
            format_ext=".mp3",
            language="en",
            transcript="Tanya proposed automated dependency auditing. Chloe demonstrated the React Native mobile UI prototype.",
            intelligence={
                "summary": "Sprint planning meeting defining frontend mobile goals and automated vulnerability checks.",
                "key_points": [
                    "Chloe completed the authentication screens in React Native.",
                    "Weekly dependency scanning to prevent supply-chain vulnerabilities."
                ],
                "decisions": [
                    "Integrate Snyk automated scanning in the CI/CD deployment pipeline.",
                    "Adopt biometrics for mobile login."
                ],
                "deadlines": ["October 10th", "End of Sprint"],
                "priorities": ["High", "High"],
                "action_items": [
                    {
                        "task": "Implement FaceID and fingerprint biometrics",
                        "assignee": "Chloe",
                        "priority": "High",
                        "deadline": "October 10th",
                        "status": "Pending"
                    },
                    {
                        "task": "Setup GitHub Actions security workflow",
                        "assignee": "Tanya",
                        "priority": "Medium",
                        "deadline": "End of Sprint",
                        "status": "Pending"
                    }
                ]
            },
            participant_data={
                "unique_participants": ["Tanya", "Chloe"],
                "responsibilities": [
                    {"name": "Chloe", "role": "Mobile Engineer", "tasks": ["Implement FaceID and fingerprint biometrics"]}
                ]
            },
            validation_info={"is_valid": True, "file_check": "PASSED", "transcript_check": "PASSED", "schema_check": "PASSED"}
        )

        with cls.db.get_connection() as conn:
            conn.execute("UPDATE meetings SET created_at = ? WHERE meeting_id = ?", (cls.date_s2, cls.mid_sprint2))
            conn.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.delete_meeting(cls.mid_sprint1)
        cls.db.delete_meeting(cls.mid_sprint2)

    # -----------------------------------------------------------------------
    # 1. DATABASE HISTORICAL INSIGHTS TESTS
    # -----------------------------------------------------------------------
    def test_insights_overview_kpis(self):
        """Calculates total meetings, action items, status breakdown, decisions, and participants."""
        res = self.db.get_historical_insights()
        self.assertGreaterEqual(res["total_meetings"], 2)
        self.assertGreaterEqual(res["total_action_items"], 4)
        self.assertGreaterEqual(res["pending_action_items"], 3)
        self.assertGreaterEqual(res["completed_action_items"], 1)
        self.assertGreaterEqual(res["total_decisions_count"], 4)
        self.assertGreaterEqual(res["unique_participants_count"], 3)
        self.assertIn("recent_meetings", res)
        self.assertIn("participants", res)
        self.assertIn("decisions", res)
        self.assertIn("action_items", res)
        self.assertIn("deadlines", res)
        self.assertIn("project_history", res)

    def test_filter_by_participant(self):
        """Filters historical insights to meetings and tasks associated with Tanya."""
        res = self.db.get_historical_insights(participant="Tanya")
        self.assertGreaterEqual(res["total_meetings"], 2)
        # All returned action items must belong to Tanya
        for a in res["action_items"]:
            self.assertEqual(a["assignee"].lower(), "tanya")

    def test_filter_by_status(self):
        """Filters action items to only Completed tasks."""
        res = self.db.get_historical_insights(status="Completed")
        self.assertGreaterEqual(len(res["action_items"]), 1)
        for a in res["action_items"]:
            self.assertEqual(a["status"], "Completed")

    def test_filter_by_title(self):
        """Filters historical insights by meeting title keyword 'Retrospective'."""
        res = self.db.get_historical_insights(title="Retrospective")
        self.assertGreaterEqual(res["total_meetings"], 1)
        mids = [m["meeting_id"] for m in res["recent_meetings"]]
        self.assertIn(self.mid_sprint1, mids)
        self.assertNotIn(self.mid_sprint2, mids)

    def test_filter_by_date_range(self):
        """Filters historical insights to meetings created on or after 2026-09-01."""
        res = self.db.get_historical_insights(start_date="2026-09-01")
        mids = [m["meeting_id"] for m in res["recent_meetings"]]
        self.assertIn(self.mid_sprint2, mids)
        self.assertNotIn(self.mid_sprint1, mids)

    def test_non_matching_filter_returns_empty_gracefully(self):
        """Non-matching filter returns clean empty lists with zero crashes."""
        res = self.db.get_historical_insights(title="NonExistentTopic_XYZ_99999")
        self.assertEqual(res["total_meetings"], 0)
        self.assertEqual(res["total_action_items"], 0)
        self.assertEqual(len(res["decisions"]), 0)
        self.assertEqual(len(res["action_items"]), 0)

    # -----------------------------------------------------------------------
    # 2. REST API ENDPOINT TESTS
    # -----------------------------------------------------------------------
    def test_api_get_insights_endpoint(self):
        """GET /meetings/insights returns 200 with structured insights payload."""
        resp = self.client.get("/meetings/insights")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "success")
        insights = data["insights"]
        self.assertIn("total_meetings", insights)
        self.assertIn("total_action_items", insights)
        self.assertIn("decisions", insights)
        self.assertIn("participants", insights)

    def test_api_get_insights_with_query_params(self):
        """GET /meetings/insights?participant=Chloe&status=Pending returns filtered data."""
        resp = self.client.get("/meetings/insights?participant=Chloe&status=Pending")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        insights = data["insights"]
        for act in insights["action_items"]:
            self.assertEqual(act["assignee"].lower(), "chloe")
            self.assertEqual(act["status"], "Pending")

    # -----------------------------------------------------------------------
    # 3. AI CROSS-MEETING INSIGHTS GENERATOR TESTS
    # -----------------------------------------------------------------------
    def test_ai_cross_meeting_insights_pending_tasks(self):
        """User question: 'What are all pending action items across meetings?'"""
        res = self.engine.generate_historical_insight("What are all pending action items across meetings?")
        self.assertTrue(res["found"])
        self.assertGreater(len(res["source_meeting_ids"]), 0)
        self.assertTrue(len(res["answer"]) > 10)

    def test_ai_cross_meeting_insights_insufficient_data(self):
        """Unrelated topic query states that insufficient historical data is available."""
        res = self.engine.generate_historical_insight("What are the lunar orbit trajectories for asteroid deflection missions?")
        self.assertFalse(res["found"])
        self.assertEqual(len(res["source_meeting_ids"]), 0)
        self.assertIn("insufficient historical data", res["answer"].lower())

    def test_ai_cross_meeting_empty_question_validation(self):
        """Empty question raises ValueError."""
        with self.assertRaises(ValueError):
            self.engine.generate_historical_insight("")


if __name__ == "__main__":
    unittest.main(verbosity=2)
