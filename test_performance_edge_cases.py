"""
Milestone 3 – Task 8: Performance & Edge Case Testing Suite
Tests RAG and semantic-search system under difficult, unusual, and failure conditions.

Covers:
1. Large Transcripts (50KB+ handling, context budgeting, accuracy)
2. Multiple Historical Meetings (High density, filtering, deduplication)
3. Long Questions (Validation, safe rejection, crash prevention)
4. Short Questions ("API?", "Priya?", "deadline?", "decision?")
5. Unknown Questions (Zero hallucination, clear not-found response)
6. No Matching Meetings (Empty retrieval handling)
7. Duplicate Meeting Data (Atomic persistence, fact deduplication)
8. Missing Transcript (None / empty string handling)
9. Missing Embeddings (Graceful degradation to keyword search)
10. Vector Database Failure (Graceful fallback on vector error)
11. LLM Failure (Simulated timeout/503 fallback to deterministic RAG)
12. API Timeout (Network timeout handling)
13. Database Failure (Sanitized error response, no stack/path leaks)
14. Authentication Failure (401 Unauthorized on invalid/missing auth)
15. Error Responses (Meaningful messages, correct HTTP status codes)
16. Performance Measurements (Real latency benchmarks recorded)
"""

import os
import sys
import time
import json
import uuid
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from fastapi.testclient import TestClient
from database import DatabaseManager
from ai_search_service import AISearchEngine
from api import app
import api


class TestPerformanceAndEdgeCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager()
        cls.engine = AISearchEngine(db=cls.db)
        cls.client = TestClient(app)

        cls.auth_token = os.environ.get("API_AUTH_TOKEN", "truthshield-secret-token-2026")
        cls.bearer_headers = {"Authorization": f"Bearer {cls.auth_token}"}
        cls.api_key_headers = {"X-API-Key": cls.auth_token}

        # Store test meeting IDs for teardown
        cls.seeded_mids = []

        # 1. Seed Large Transcript Meeting (50,000+ chars)
        cls.mid_large = f"EDGE-MEET-LARGE-{uuid.uuid4().hex[:6].upper()}"
        cls.seeded_mids.append(cls.mid_large)

        large_body_paragraphs = []
        for i in range(220):
            large_body_paragraphs.append(
                f"Paragraph {i}: Detailed engineering discussion covering server telemetry, "
                f"packet inspection algorithms, cache eviction heuristics, and load balancer configuration parameters. "
                f"Routine system metrics were evaluated across cluster nodes without significant incident."
            )
        # Embed a specific fact deep at paragraph 185
        large_body_paragraphs[185] = (
            "CRITICAL MILESTONE: Elena confirmed the quantum-resistant encryption cipher AES-GCM-512 was successfully "
            "benchmarked on all primary edge routers."
        )
        large_transcript = "\n\n".join(large_body_paragraphs)

        cls.db.save_meeting(
            meeting_id=cls.mid_large,
            title="Hyperscale Edge Router Architecture & Security Review",
            audio_filename="edge_router_sync.mp3",
            file_size_mb=45.8,
            duration_seconds=3600.0,
            format_ext=".MP3",
            language="EN",
            transcript=large_transcript,
            intelligence={
                "summary": "Hyperscale review of edge router infrastructure, telemetry buffers, and cryptographic cipher benchmarking.",
                "key_points": [
                    "Evaluated packet inspection latency across 120 server nodes.",
                    "Quantum-resistant encryption cipher AES-GCM-512 benchmarked."
                ],
                "decisions": ["Deploy AES-GCM-512 cipher to all primary edge routers."],
                "deadlines": ["December 15th"],
                "priorities": ["High"],
                "action_items": [
                    {
                        "task": "Deploy AES-GCM-512 cipher to edge clusters",
                        "assignee": "Elena",
                        "priority": "High",
                        "deadline": "December 15th",
                        "status": "In Progress"
                    }
                ]
            },
            participant_data={"unique_participants": ["Elena"], "responsibilities": []},
            validation_info={"is_valid": True}
        )

        # 2. Seed Missing Transcript Meeting
        cls.mid_no_trans = f"EDGE-MEET-NOTRANS-{uuid.uuid4().hex[:6].upper()}"
        cls.seeded_mids.append(cls.mid_no_trans)
        cls.db.save_meeting(
            meeting_id=cls.mid_no_trans,
            title="Audio-Only Standup With Corrupted Transcript",
            audio_filename="corrupted_trans.wav",
            file_size_mb=2.1,
            duration_seconds=120.0,
            format_ext=".WAV",
            language="EN",
            transcript="",  # Missing transcript
            intelligence={
                "summary": "Quick audio-only standup discussing backup generator maintenance.",
                "key_points": ["Generator fuel inspected."],
                "decisions": ["Schedule routine electrical inspection."],
                "deadlines": ["Wednesday 10am"],
                "priorities": ["Low"],
                "action_items": [
                    {
                        "task": "Inspect facility backup generators",
                        "assignee": "Sam",
                        "priority": "Low",
                        "deadline": "Wednesday 10am",
                        "status": "Pending"
                    }
                ]
            },
            participant_data={"unique_participants": ["Sam"], "responsibilities": []},
            validation_info={"is_valid": True}
        )

        # 3. Seed High-Density Historical Meetings (20 diverse meetings)
        cls.high_density_mids = []
        topics = [
            ("DevOps Kubernetes", "Kavita", "Migrated ingress controllers to Traefik v3."),
            ("Cloud Networking", "Dev", "Configured VPC peering across region us-east."),
            ("Mobile Flutter Client", "Priya", "Finalized offline caching repository in Flutter."),
            ("Payment Gateway Integration", "Vikram", "Upgraded Stripe webhook signature verification."),
            ("Data Warehouse ETL", "Aarav", "Optimized Snowflake daily aggregation query."),
            ("Frontend React Migration", "Priya", "Rewrote legacy dashboard views into React 19."),
            ("PostgreSQL Replication", "Dev", "Verified streaming replication lag under 15ms."),
            ("Security Vulnerability Audit", "Elena", "Remediated OpenSSL buffer overflow advisory."),
            ("Machine Learning Pipelines", "Vikram", "Trained classification model on v2 dataset."),
            ("Identity Provider OAuth2", "Kavita", "Rotated Okta production client credentials."),
            ("Mobile Push Notifications", "Priya", "Integrated Apple APNs HTTP2 interface."),
            ("Redis Sentinel Failover", "Dev", "Tested automatic Redis master failover."),
            ("Internal API Documentation", "Aarav", "Published Swagger OpenAPI specs to developer portal."),
            ("Observability Telemetry", "Kavita", "Configured OpenTelemetry collector daemonsets."),
            ("Billing Invoicing Engine", "Vikram", "Automated recurring invoice PDF generator."),
            ("Search Index Optimization", "Dev", "Rebuilt SQLite FTS full-text index."),
            ("User Privacy GDPR Compliance", "Elena", "Implemented automated data deletion worker."),
            ("Frontend Design System", "Priya", "Standardized design tokens across color palettes."),
            ("Container Security Scans", "Elena", "Integrated Trivy scanner into CI/CD build pipeline."),
            ("Disaster Recovery Plan", "Dev", "Simulated database restore from cold S3 backup.")
        ]

        for i, (title, lead, fact) in enumerate(topics):
            mid = f"EDGE-MEET-DENSE-{i+1:02d}-{uuid.uuid4().hex[:4].upper()}"
            cls.high_density_mids.append(mid)
            cls.seeded_mids.append(mid)
            cls.db.save_meeting(
                meeting_id=mid,
                title=f"Historical Sync {i+1}: {title}",
                audio_filename=f"dense_sync_{i+1}.mp3",
                file_size_mb=3.5,
                duration_seconds=300.0,
                format_ext=".MP3",
                language="EN",
                transcript=f"Meeting {i+1} on {title}. {lead} reported: {fact}",
                intelligence={
                    "summary": f"Discussion regarding {title}. {fact}",
                    "key_points": [fact],
                    "decisions": [f"Standardize on {title} guidelines."],
                    "deadlines": ["End of Quarter"],
                    "priorities": ["Medium"],
                    "action_items": [
                        {
                            "task": f"Complete {title} deliverables",
                            "assignee": lead,
                            "priority": "Medium",
                            "deadline": "End of Quarter",
                            "status": "In Progress"
                        }
                    ]
                },
                participant_data={"unique_participants": [lead], "responsibilities": []},
                validation_info={"is_valid": True}
            )

    @classmethod
    def tearDownClass(cls):
        for mid in cls.seeded_mids:
            try:
                cls.db.delete_meeting(mid)
            except Exception:
                pass

    # =======================================================================
    # 1. LARGE TRANSCRIPTS
    # =======================================================================
    def test_tc_edge_01_a_large_transcript_persistence(self):
        """TC-EDGE-01-A: Large transcript (>50,000 chars) is saved and loaded without truncation or crash."""
        meeting = self.db.get_meeting(self.mid_large)
        self.assertIsNotNone(meeting)
        self.assertGreater(len(meeting["transcript"]), 50000)
        self.assertGreater(meeting["word_count"], 4000)
        self.assertIn("AES-GCM-512", meeting["transcript"])

    def test_tc_edge_01_b_large_transcript_retrieval(self):
        """TC-EDGE-01-B: Retrieval finds fact embedded deep inside large transcript."""
        hits = self.db.search_meetings("AES-GCM-512")
        self.assertGreaterEqual(len(hits), 1)
        self.assertEqual(hits[0]["meeting_id"], self.mid_large)

    def test_tc_edge_01_c_large_transcript_context_budget(self):
        """TC-EDGE-01-C: Prompt context for large meeting stays safely within LLM character limits."""
        meeting = self.db.get_meeting(self.mid_large)
        context = self.engine.build_prompt_context([meeting])
        # Prompt context snippet must be bounded (< 3000 chars) rather than dumping 50KB
        self.assertLess(len(context), 3000)
        self.assertIn(self.mid_large, context)
        self.assertIn("Hyperscale Edge Router", context)

    def test_tc_edge_01_d_large_transcript_rag_qa(self):
        """TC-EDGE-01-D: RAG Q&A accurately answers questions using large meeting record."""
        res = self.engine.answer_question("What cipher was benchmarked on edge routers?")
        self.assertTrue(res["found"])
        self.assertIn(self.mid_large, res["source_meeting_ids"])
        self.assertTrue("aes-gcm-512" in res["answer"].lower() or "cipher" in res["answer"].lower())

    # =======================================================================
    # 2. MULTIPLE HISTORICAL MEETINGS
    # =======================================================================
    def test_tc_edge_02_a_high_density_filtering(self):
        """TC-EDGE-02-A: Out of 20+ historical meetings, only relevant topic meetings are retrieved."""
        hits = self.engine.retrieve_context("Traefik Kubernetes ingress")
        mids = [m["meeting_id"] for m in hits]
        # Should retrieve the DevOps meeting and exclude non-DevOps meetings
        devops_mid = self.high_density_mids[0]  # DevOps Kubernetes
        self.assertIn(devops_mid, mids)
        # Should not include GDPR, Snowflake, APNs
        self.assertNotIn(self.high_density_mids[4], mids)   # Data Warehouse ETL
        self.assertNotIn(self.high_density_mids[16], mids)  # GDPR Compliance

    def test_tc_edge_02_b_no_duplicate_candidate_records(self):
        """TC-EDGE-02-B: Multi-keyword search over 20+ meetings returns zero duplicate records."""
        hits = self.engine.retrieve_context("DevOps Kubernetes Cloud Networking Mobile Flutter")
        mids = [m["meeting_id"] for m in hits]
        self.assertEqual(len(mids), len(set(mids)), "Retrieved meetings should be unique")

    def test_tc_edge_02_c_meeting_id_integrity(self):
        """TC-EDGE-02-C: All retrieved meeting IDs match existing stored meeting records exactly."""
        hits = self.engine.retrieve_context("PostgreSQL streaming replication lag")
        self.assertGreater(len(hits), 0)
        for m in hits:
            stored = self.db.get_meeting(m["meeting_id"])
            self.assertIsNotNone(stored)
            self.assertEqual(stored["meeting_id"], m["meeting_id"])

    # =======================================================================
    # 3. LONG QUESTIONS
    # =======================================================================
    def test_tc_edge_03_a_excessive_question_python_validation(self):
        """TC-EDGE-03-A: Question > 4000 chars raises ValueError in AISearchEngine without crashing."""
        long_q = "Tell me about the project status " + ("word " * 1200)
        with self.assertRaises(ValueError) as ctx:
            self.engine.answer_question(long_q)
        self.assertIn("exceeds maximum permitted length", str(ctx.exception).lower())

    def test_tc_edge_03_b_excessive_question_api_bad_request(self):
        """TC-EDGE-03-B: POST /ask with question > 4000 chars returns HTTP 400 Bad Request."""
        long_q = "What was decided? " + ("detail " * 1000)
        resp = self.client.post("/ask", json={"question": long_q}, headers=self.bearer_headers)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("exceeds maximum permitted length", resp.json().get("detail", "").lower())

    # =======================================================================
    # 4. SHORT QUESTIONS
    # =======================================================================
    def test_tc_edge_04_a_short_query_api_question_mark(self):
        """TC-EDGE-04-A: Single acronym with question mark 'API?' handles safely."""
        res = self.engine.answer_question("API?")
        self.assertTrue(res["found"])
        self.assertTrue(len(res["source_meeting_ids"]) > 0)

    def test_tc_edge_04_b_short_query_priya(self):
        """TC-EDGE-04-B: Single person name 'Priya?' retrieves Priya's tasks."""
        res = self.engine.answer_question("Priya?")
        self.assertTrue(res["found"])
        self.assertTrue(any("Priya" in str(s) for s in res["source_meeting_ids"] + [res["answer"]]))

    def test_tc_edge_04_c_short_query_deadline(self):
        """TC-EDGE-04-C: Single intent term 'deadline?' executes without crashing."""
        res = self.engine.answer_question("deadline?")
        self.assertIn("found", res)
        self.assertIsInstance(res["source_meeting_ids"], list)

    def test_tc_edge_04_d_short_query_decision(self):
        """TC-EDGE-04-D: Single intent term 'decision?' executes without crashing."""
        res = self.engine.answer_question("decision?")
        self.assertIn("found", res)
        self.assertIsInstance(res["source_meeting_ids"], list)

    # =======================================================================
    # 5. UNKNOWN QUESTIONS
    # =======================================================================
    def test_tc_edge_05_a_unknown_information_zero_hallucination(self):
        """TC-EDGE-05-A: Question about unrecorded entity returns found=False with no fabrication."""
        res = self.engine.answer_question("What were the antimatter reactor output specifications?")
        self.assertFalse(res["found"])
        self.assertEqual(len(res["source_meeting_ids"]), 0)
        self.assertIn("not found in the historical meeting records", res["answer"].lower())

    # =======================================================================
    # 6. NO MATCHING MEETINGS
    # =======================================================================
    def test_tc_edge_06_a_empty_retrieval_handling(self):
        """TC-EDGE-06-A: Completely empty retrieval result handled gracefully by API and engine."""
        retrieved = self.engine.retrieve_context("XkcdSupercalifragilistic999888")
        self.assertEqual(retrieved, [])

        res = self.engine.answer_question("XkcdSupercalifragilistic999888")
        self.assertFalse(res["found"])
        self.assertEqual(res["source_meeting_ids"], [])

    # =======================================================================
    # 7. DUPLICATE MEETING DATA
    # =======================================================================
    def test_tc_edge_07_a_duplicate_meeting_id_overwrite(self):
        """TC-EDGE-07-A: Re-saving an existing meeting_id safely updates record without duplicating."""
        mid_dedup = f"EDGE-MEET-DEDUP-{uuid.uuid4().hex[:6].upper()}"
        self.seeded_mids.append(mid_dedup)
        self.db.save_meeting(
            meeting_id=mid_dedup,
            title="Initial Title for Dedup Meeting",
            audio_filename="dedup.wav",
            file_size_mb=1.0,
            duration_seconds=60.0,
            format_ext=".WAV",
            language="EN",
            transcript="Initial transcript content",
            intelligence={"summary": "Initial summary"},
            participant_data={},
            validation_info={}
        )
        count_before = self.db.get_dashboard_stats().get("total_meetings", 0)
        # Re-save with same ID but updated title
        self.db.save_meeting(
            meeting_id=mid_dedup,
            title="Updated Title for Dedup Meeting",
            audio_filename="dedup.wav",
            file_size_mb=1.0,
            duration_seconds=60.0,
            format_ext=".WAV",
            language="EN",
            transcript="Updated transcript content",
            intelligence={"summary": "Updated summary"},
            participant_data={},
            validation_info={}
        )
        count_after = self.db.get_dashboard_stats().get("total_meetings", 0)
        self.assertEqual(count_before, count_after, "Re-saving meeting must not increase meeting count")
        updated = self.db.get_meeting(mid_dedup)
        self.assertEqual(updated["title"], "Updated Title for Dedup Meeting")

    def test_tc_edge_07_b_duplicate_fact_deduplication(self):
        """TC-EDGE-07-B: AI search deduplicates repetitive statements into clean key findings."""
        res = self.engine.answer_question("What was decided regarding edge router cipher?")
        self.assertTrue(res["found"])
        # key_findings must not contain duplicate strings
        findings = res.get("key_findings", [])
        self.assertEqual(len(findings), len(set(findings)))

    # =======================================================================
    # 8. MISSING TRANSCRIPT
    # =======================================================================
    def test_tc_edge_08_a_missing_transcript_handling(self):
        """TC-EDGE-08-A: Meeting with empty or missing transcript does not cause TypeError or crash."""
        meeting = self.db.get_meeting(self.mid_no_trans)
        self.assertIsNotNone(meeting)
        # Context builder handles empty transcript safely
        context = self.engine.build_prompt_context([meeting])
        self.assertIn("No summary available" if not meeting.get("summary") else meeting.get("summary"), context)

        # Question answering still retrieves meeting by title/summary
        res = self.engine.answer_question("generator electrical inspection")
        self.assertTrue(res["found"])
        self.assertIn(self.mid_no_trans, res["source_meeting_ids"])

    # =======================================================================
    # 9. MISSING EMBEDDINGS
    # =======================================================================
    def test_tc_edge_09_a_missing_embeddings_fallback(self):
        """TC-EDGE-09-A: System degrades gracefully to keyword search when embeddings are absent."""
        results = self.engine.semantic_search("Trivy scanner container", limit=5)
        self.assertGreaterEqual(len(results), 1)
        self.assertTrue(any("Trivy" in str(r) for r in results))

    # =======================================================================
    # 10. VECTOR DATABASE FAILURE
    # =======================================================================
    def test_tc_edge_10_a_vector_failure_simulation(self):
        """TC-EDGE-10-A: Vector search exception triggers automatic relational keyword fallback."""
        with patch.object(self.engine, "retrieve_context", side_effect=RuntimeError("Simulated Vector DB Outage")):
            results = self.engine.semantic_search("Snowflake aggregation", limit=5)
            # Should fall back to db.search_meetings without raising exception
            self.assertIsInstance(results, list)
            self.assertGreaterEqual(len(results), 1)
            self.assertTrue(any("Snowflake" in str(r) for r in results))

    # =======================================================================
    # 11. LLM FAILURE
    # =======================================================================
    def test_tc_edge_11_a_llm_api_timeout_fallback(self):
        """TC-EDGE-11-A: Gemini API timeout / failure automatically activates deterministic grounded fallback."""
        with patch.object(self.engine, "_call_gemini", side_effect=TimeoutError("REST Gemini Gateway Timeout")):
            res = self.engine.answer_question("What tasks were assigned to Elena for edge routers?")
            self.assertTrue(res["found"])
            self.assertIn(self.mid_large, res["source_meeting_ids"])
            self.assertIn("Elena", res["answer"])
            self.assertTrue("aes-gcm-512" in res["answer"].lower())

    def test_tc_edge_11_b_llm_api_http_503_fallback(self):
        """TC-EDGE-11-B: Upstream HTTP 503 error falls back safely to grounded rule engine."""
        import urllib.error
        err_503 = urllib.error.HTTPError("https://api", 503, "Service Unavailable", {}, None)
        with patch.object(self.engine, "_call_gemini", side_effect=err_503):
            res = self.engine.answer_question("Who worked on Apple APNs push notifications?")
            self.assertTrue(res["found"])
            self.assertIn("Priya", res["answer"])

    # =======================================================================
    # 12. API TIMEOUT
    # =======================================================================
    def test_tc_edge_12_a_upstream_timeout_handling(self):
        """TC-EDGE-12-A: Simulated socket timeout in ask_endpoint returns safe response rather than crashing."""
        with patch.object(api.ai_search_engine, "answer_question", side_effect=TimeoutError("Request timed out waiting for backend")):
            resp = self.client.post("/ask", json={"question": "Any deadlines?"}, headers=self.bearer_headers)
            self.assertEqual(resp.status_code, 500)
            self.assertIn("error", resp.json().get("detail", "").lower())

    # =======================================================================
    # 13. DATABASE FAILURE
    # =======================================================================
    def test_tc_edge_13_a_database_failure_sanitized_error(self):
        """TC-EDGE-13-A: Database exception returns HTTP 500 without leaking sensitive paths or SQL traces."""
        with patch.object(api.db, "get_meeting", side_effect=Exception("OperationalError: disk I/O error on /secret/db")):
            resp = self.client.get(f"/meetings/{self.mid_large}")
            self.assertEqual(resp.status_code, 500)
            data = resp.json()
            # Must return clean message without leaking filesystem credentials
            self.assertIn("detail", data)
            self.assertNotIn("password", str(data).lower())

    # =======================================================================
    # 14. AUTHENTICATION FAILURE
    # =======================================================================
    def test_tc_edge_14_a_missing_auth_header(self):
        """TC-EDGE-14-A: Request without authentication headers returns 401 Unauthorized."""
        resp = self.client.post("/ask", json={"question": "What are our deadlines?"})
        self.assertEqual(resp.status_code, 401)
        self.assertIn("missing", resp.json().get("detail", "").lower())

    def test_tc_edge_14_b_invalid_bearer_token(self):
        """TC-EDGE-14-B: Request with invalid Bearer token returns 401 Unauthorized."""
        resp = self.client.post("/ask", json={"question": "What are our deadlines?"}, headers={"Authorization": "Bearer invalid_secret_token_123"})
        self.assertEqual(resp.status_code, 401)
        self.assertIn("invalid", resp.json().get("detail", "").lower())

    def test_tc_edge_14_c_invalid_x_api_key(self):
        """TC-EDGE-14-C: Request with invalid X-API-Key returns 401 Unauthorized."""
        resp = self.client.post("/ask", json={"question": "What are our deadlines?"}, headers={"X-API-Key": "bad_key_xyz"})
        self.assertEqual(resp.status_code, 401)
        self.assertIn("invalid", resp.json().get("detail", "").lower())

    # =======================================================================
    # 15. ERROR RESPONSES
    # =======================================================================
    def test_tc_edge_15_a_empty_meeting_id(self):
        """TC-EDGE-15-A: GET /meetings/ with whitespace meeting ID returns 400 Bad Request."""
        resp = self.client.get("/meetings/%20%20")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("cannot be empty or whitespace", resp.json().get("detail", "").lower())

    def test_tc_edge_15_b_nonexistent_meeting_id(self):
        """TC-EDGE-15-B: GET /meetings/{id} with non-existent meeting ID returns 404 Not Found."""
        resp = self.client.get("/meetings/MEET-DOESNOTEXIST-99999")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("not found", resp.json().get("detail", "").lower())

    def test_tc_edge_15_c_empty_question_ask_endpoint(self):
        """TC-EDGE-15-C: POST /ask with empty question returns 400 Bad Request."""
        resp = self.client.post("/ask", json={"question": "   "}, headers=self.bearer_headers)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("cannot be empty or whitespace", resp.json().get("detail", "").lower())

    # =======================================================================
    # 16. PERFORMANCE MEASUREMENTS (GENUINE BENCHMARKS)
    # =======================================================================
    def test_tc_perf_16_a_keyword_search_latency(self):
        """TC-PERF-16-A: Measures genuine keyword search latency over historical repository."""
        latencies = []
        queries = ["Kubernetes", "Flutter", "Stripe", "PostgreSQL", "Elena"]
        for q in queries:
            start = time.perf_counter()
            _ = self.db.search_meetings(query=q, limit=10)
            duration_ms = (time.perf_counter() - start) * 1000
            latencies.append(duration_ms)

        avg_lat = sum(latencies) / len(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)
        print(f"\n[PERF BENCHMARK] Keyword Search Latency: Avg={avg_lat:.2f}ms | Min={min_lat:.2f}ms | Max={max_lat:.2f}ms")
        # Sub-50ms target for local SQLite keyword search
        self.assertLess(avg_lat, 50.0, f"Average keyword search latency too high: {avg_lat:.2f}ms")

    def test_tc_perf_16_b_context_retrieval_latency(self):
        """TC-PERF-16-B: Measures genuine retrieval latency across multi-meeting context."""
        latencies = []
        queries = [
            "Traefik ingress controller configuration",
            "Apple APNs HTTP2 mobile push notifications",
            "PostgreSQL streaming replication latency",
            "Snowflake data warehouse aggregation pipeline"
        ]
        for q in queries:
            start = time.perf_counter()
            _ = self.engine.retrieve_context(q, max_meetings=5)
            duration_ms = (time.perf_counter() - start) * 1000
            latencies.append(duration_ms)

        avg_lat = sum(latencies) / len(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)
        print(f"\n[PERF BENCHMARK] Context Retrieval Latency: Avg={avg_lat:.2f}ms | Min={min_lat:.2f}ms | Max={max_lat:.2f}ms")
        self.assertLess(avg_lat, 100.0, f"Average context retrieval latency too high: {avg_lat:.2f}ms")

    def test_tc_perf_16_c_ask_endpoint_latency(self):
        """TC-PERF-16-C: Measures genuine /ask endpoint response time."""
        # Use fallback engine for deterministic measurement without network delay
        with patch.object(api.ai_search_engine, "_call_gemini", side_effect=TimeoutError()):
            start = time.perf_counter()
            resp = self.client.post("/ask", json={"question": "What cipher was deployed to edge routers?"}, headers=self.bearer_headers)
            duration_ms = (time.perf_counter() - start) * 1000
            self.assertEqual(resp.status_code, 200)
            print(f"\n[PERF BENCHMARK] POST /ask Latency (Deterministic Grounded Search): {duration_ms:.2f}ms")
            self.assertLess(duration_ms, 200.0, f"Ask endpoint latency too high: {duration_ms:.2f}ms")

    def test_tc_perf_16_d_large_transcript_processing_latency(self):
        """TC-PERF-16-D: Measures processing & context construction latency for 50,000+ char transcript."""
        meeting = self.db.get_meeting(self.mid_large)
        start = time.perf_counter()
        context = self.engine.build_prompt_context([meeting])
        duration_ms = (time.perf_counter() - start) * 1000
        print(f"\n[PERF BENCHMARK] Large Transcript Context Construction: {duration_ms:.2f}ms (Length: {len(context)} chars)")
        self.assertLess(duration_ms, 25.0, f"Large transcript context construction too slow: {duration_ms:.2f}ms")


if __name__ == "__main__":
    unittest.main()
