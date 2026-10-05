"""
WhisperSense AI • Test Suite for Milestone 4 - Task 6: Reports & Export (PDF & CSV)
Uses standard library unittest to run seamlessly without external test runner dependencies.

Verifies:
1. Executive PDF generation with ReportLab formatting, metadata, and tables.
2. Full meeting CSV generation with structured sections.
3. Dedicated Action Items CSV generation for external tool import (Jira/Excel).
4. FastAPI export endpoints (/meetings/{id}/export/pdf, /export/csv, /export/action-items).
5. Edge cases: Empty/minimal meeting data, missing optional fields, 404 for non-existent meetings.
"""

import os
import io
import csv
import unittest
from fastapi.testclient import TestClient

from database import DatabaseManager
from report_exporter import (
    generate_meeting_pdf,
    generate_meeting_csv,
    generate_action_items_csv
)
from api import app

SAMPLE_MEETING = {
    "meeting_id": "MEET-EXP-TEST01",
    "title": "Q3 Executive Roadmap & Resource Planning",
    "audio_filename": "q3_roadmap.mp3",
    "duration_seconds": 1845.5,
    "format": "MP3",
    "language": "EN",
    "word_count": 2840,
    "created_at": "2026-09-15 14:30:00",
    "summary": "The executive committee aligned on the Q3 roadmap focusing on AI search and enterprise security.",
    "key_points": [
        "Infrastructure migration to scalable cloud clusters.",
        "Strict multi-tenant security and user data segregation.",
        "Q3 launch targeted for late October."
    ],
    "decisions": [
        "Adopted salted SHA-256 for credential authentication.",
        "Approved ReportLab PDF dossier generation pipeline."
    ],
    "action_items": [
        {
            "id": 101,
            "task": "Finalize Docker containerization and health checks",
            "assignee": "DevOps Lead",
            "priority": "High",
            "deadline": "2026-10-15",
            "status": "In Progress"
        },
        {
            "id": 102,
            "task": "Review API token rotation security policy",
            "assignee": "Security Engineer",
            "priority": "Medium",
            "deadline": "2026-10-20",
            "status": "Pending"
        }
    ],
    "participants": ["DevOps Lead", "Security Engineer", "Product Manager"],
    "deadlines": ["2026-10-15", "2026-10-20"]
}

MINIMAL_MEETING = {
    "meeting_id": "MEET-MINIMAL-01",
    "title": "Minimal Sync",
    "summary": "Brief discussion without explicit tasks."
}


class TestReportsExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = DatabaseManager()
        # Seed test meeting using save_meeting signature
        cls.db.save_meeting(
            meeting_id=SAMPLE_MEETING["meeting_id"],
            title=SAMPLE_MEETING["title"],
            audio_filename=SAMPLE_MEETING["audio_filename"],
            file_size_mb=2.5,
            duration_seconds=SAMPLE_MEETING["duration_seconds"],
            format_ext="MP3",
            language="EN",
            transcript="Today's meeting discussed executive roadmap and cloud migration.",
            intelligence={
                "summary": SAMPLE_MEETING["summary"],
                "key_points": SAMPLE_MEETING["key_points"],
                "decisions": SAMPLE_MEETING["decisions"],
                "action_items": SAMPLE_MEETING["action_items"],
                "deadlines": SAMPLE_MEETING["deadlines"]
            },
            participant_data={"unique_participants": SAMPLE_MEETING["participants"]},
            validation_info={"is_valid": True},
            user_id=1
        )

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.delete_meeting(SAMPLE_MEETING["meeting_id"])
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # PDF Unit Tests
    # -------------------------------------------------------------------------
    def test_01_generate_meeting_pdf_valid(self):
        """Verify PDF is generated with valid binary header and non-trivial content."""
        pdf_bytes = generate_meeting_pdf(SAMPLE_MEETING)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_02_generate_meeting_pdf_minimal(self):
        """Verify PDF generator handles missing optional fields gracefully."""
        pdf_bytes = generate_meeting_pdf(MINIMAL_MEETING)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_03_generate_meeting_pdf_file_output(self):
        """Verify PDF can be written directly to a specified file path."""
        test_path = "scratch_test_dossier.pdf"
        try:
            pdf_bytes = generate_meeting_pdf(SAMPLE_MEETING, output_path=test_path)
            self.assertTrue(os.path.exists(test_path))
            self.assertEqual(os.path.getsize(test_path), len(pdf_bytes))
        finally:
            if os.path.exists(test_path):
                os.remove(test_path)

    # -------------------------------------------------------------------------
    # CSV Unit Tests
    # -------------------------------------------------------------------------
    def test_04_generate_meeting_csv_content(self):
        """Verify full meeting CSV contains all expected sections and rows."""
        csv_str = generate_meeting_csv(SAMPLE_MEETING)
        self.assertIsInstance(csv_str, str)

        reader = list(csv.reader(io.StringIO(csv_str)))
        self.assertGreater(len(reader), 5)

        # Check header
        self.assertEqual(reader[0], ["SECTION", "FIELD / ITEM", "ASSIGNEE", "PRIORITY", "DEADLINE", "STATUS", "DETAILS"])

        # Check sections present
        sections = {row[0] for row in reader[1:] if row}
        self.assertIn("METADATA", sections)
        self.assertIn("SUMMARY", sections)
        self.assertIn("KEY_POINT", sections)
        self.assertIn("DECISION", sections)
        self.assertIn("ACTION_ITEM", sections)
        self.assertIn("PARTICIPANT", sections)
        self.assertIn("DEADLINE", sections)

        full_text = "\n".join([",".join(row) for row in reader])
        self.assertIn("Q3 Executive Roadmap", full_text)
        self.assertIn("Finalize Docker containerization", full_text)
        self.assertIn("DevOps Lead", full_text)

    def test_05_generate_meeting_csv_minimal(self):
        """Verify CSV generation succeeds even with minimal data."""
        csv_str = generate_meeting_csv(MINIMAL_MEETING)
        self.assertIn("Minimal Sync", csv_str)
        self.assertIn("Brief discussion", csv_str)

    def test_06_generate_action_items_csv(self):
        """Verify dedicated action items CSV format."""
        csv_str = generate_action_items_csv(SAMPLE_MEETING)
        reader = list(csv.reader(io.StringIO(csv_str)))

        # Header + 2 action items = 3 rows
        self.assertEqual(len(reader), 3)
        self.assertEqual(reader[0], ["Meeting ID", "Meeting Title", "Task Description", "Assignee", "Priority", "Deadline", "Status"])
        self.assertEqual(reader[1][2], "Finalize Docker containerization and health checks")
        self.assertEqual(reader[1][3], "DevOps Lead")
        self.assertEqual(reader[1][4], "High")
        self.assertEqual(reader[1][5], "2026-10-15")
        self.assertEqual(reader[1][6], "In Progress")

    # -------------------------------------------------------------------------
    # API Integration Tests
    # -------------------------------------------------------------------------
    def test_07_api_export_pdf(self):
        """Test GET /meetings/{id}/export/pdf endpoint."""
        resp = self.client.get(f"/meetings/{SAMPLE_MEETING['meeting_id']}/export/pdf")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/pdf", resp.headers.get("content-type", ""))
        self.assertTrue(resp.content.startswith(b"%PDF-"))
        self.assertIn("attachment", resp.headers.get("content-disposition", ""))

    def test_08_api_export_csv(self):
        """Test GET /meetings/{id}/export/csv endpoint."""
        resp = self.client.get(f"/meetings/{SAMPLE_MEETING['meeting_id']}/export/csv")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.headers.get("content-type", ""))
        self.assertIn("METADATA", resp.text)
        self.assertIn("Q3 Executive Roadmap", resp.text)

    def test_09_api_export_action_items(self):
        """Test GET /meetings/{id}/export/action-items endpoint."""
        resp = self.client.get(f"/meetings/{SAMPLE_MEETING['meeting_id']}/export/action-items")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.headers.get("content-type", ""))
        self.assertIn("Task Description", resp.text)
        self.assertIn("Finalize Docker containerization", resp.text)

    def test_10_api_export_404_nonexistent(self):
        """Test export endpoints return 404 for non-existent meeting IDs."""
        resp_pdf = self.client.get("/meetings/MEET-NONEXISTENT-9999/export/pdf")
        self.assertEqual(resp_pdf.status_code, 404)

        resp_csv = self.client.get("/meetings/MEET-NONEXISTENT-9999/export/csv")
        self.assertEqual(resp_csv.status_code, 404)

        resp_act = self.client.get("/meetings/MEET-NONEXISTENT-9999/export/action-items")
        self.assertEqual(resp_act.status_code, 404)

    def test_11_api_root_lists_export_endpoints(self):
        """Verify root health check endpoint includes export endpoints."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("endpoints", data)
        self.assertIn("export_pdf", data["endpoints"])
        self.assertIn("export_csv", data["endpoints"])


if __name__ == "__main__":
    unittest.main()
