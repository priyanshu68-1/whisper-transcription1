"""
WhisperSense AI • Task 10 Deployment & Infrastructure Test Suite
Validates:
1. Dockerfile structure, base image, system dependencies (ffmpeg), exposed ports & healthchecks.
2. docker-compose.yml YAML validity, services orchestration, volume mounts & network rules.
3. .dockerignore exclusion rules.
4. Windows 1-click launcher batch files (run_all.bat, run_dashboard.bat, run_api.bat).
5. Live deployed endpoint accessibility (FastAPI :8000 and Streamlit :8501).
6. OpenAPI schema verification for all Milestone 4 endpoints.
7. Workspace file cleanliness and README documentation completeness.
"""

import os
import re
import json
import unittest
import subprocess
import urllib.request
import urllib.error

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

class TestTask10Deployment(unittest.TestCase):

    def setUp(self):
        self.dockerfile_path = os.path.join(PROJECT_ROOT, "Dockerfile")
        self.compose_path = os.path.join(PROJECT_ROOT, "docker-compose.yml")
        self.dockerignore_path = os.path.join(PROJECT_ROOT, ".dockerignore")
        self.run_all_path = os.path.join(PROJECT_ROOT, "run_all.bat")
        self.run_dashboard_path = os.path.join(PROJECT_ROOT, "run_dashboard.bat")
        self.run_api_path = os.path.join(PROJECT_ROOT, "run_api.bat")
        self.readme_path = os.path.join(PROJECT_ROOT, "README.md")

    # -------------------------------------------------------------------------
    # 1. Dockerfile Validation
    # -------------------------------------------------------------------------
    def test_01_dockerfile_structure(self):
        """Verify Dockerfile exists, has correct base image, ffmpeg, ports, and healthcheck."""
        self.assertTrue(os.path.isfile(self.dockerfile_path), "Dockerfile must exist")
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("FROM python:", content, "Dockerfile must use a official Python base image")
        self.assertIn("ffmpeg", content, "Dockerfile must install system ffmpeg for audio decoding")
        self.assertIn("libsndfile1", content, "Dockerfile must install libsndfile1")
        self.assertIn("curl", content, "Dockerfile must install curl for healthchecks")
        self.assertIn("requirements.txt", content, "Dockerfile must install from requirements.txt")
        self.assertIn("8501", content, "Dockerfile must expose port 8501 for Streamlit")
        self.assertIn("8000", content, "Dockerfile must expose port 8000 for FastAPI")
        self.assertIn("HEALTHCHECK", content, "Dockerfile must define a container HEALTHCHECK")
        self.assertIn("CMD", content, "Dockerfile must specify a default CMD entrypoint")

    # -------------------------------------------------------------------------
    # 2. docker-compose.yml Validation
    # -------------------------------------------------------------------------
    def test_02_docker_compose_structure(self):
        """Verify docker-compose.yml is valid YAML, defines api & dashboard services with volumes."""
        self.assertTrue(os.path.isfile(self.compose_path), "docker-compose.yml must exist")
        with open(self.compose_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("services:", content, "Must define services block")
        self.assertIn("api:", content, "Must define api service")
        self.assertIn("dashboard:", content, "Must define dashboard service")
        self.assertIn("8000:8000", content, "api service must expose port 8000")
        self.assertIn("8501:8501", content, "dashboard service must expose port 8501")
        self.assertIn("whisper_meetings.db", content, "Must map persistent database volume")
        self.assertIn("exports", content, "Must map exports volume")
        self.assertIn("depends_on:", content, "Dashboard must depend on API")

    def test_03_docker_compose_cli_validation(self):
        """Verify that docker compose config parses successfully with exit code 0."""
        try:
            res = subprocess.run(
                ["docker", "compose", "config"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=15
            )
            self.assertEqual(res.returncode, 0, f"docker compose config failed: {res.stderr}")
            self.assertIn("whispersense_api", res.stdout)
            self.assertIn("whispersense_dashboard", res.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.skipTest("Docker CLI not available or timed out.")

    # -------------------------------------------------------------------------
    # 3. .dockerignore Validation
    # -------------------------------------------------------------------------
    def test_04_dockerignore_rules(self):
        """Verify .dockerignore contains exclusion patterns for clean container builds."""
        self.assertTrue(os.path.isfile(self.dockerignore_path), ".dockerignore must exist")
        with open(self.dockerignore_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("__pycache__", content, ".dockerignore must ignore python bytecode")
        self.assertIn(".git", content, ".dockerignore must ignore git metadata")
        self.assertIn(".venv", content, ".dockerignore must ignore virtual environment")
        self.assertIn("test_", content, ".dockerignore must exclude test scripts")
        self.assertIn("browser_test_screenshots", content, ".dockerignore must exclude screenshots")

    # -------------------------------------------------------------------------
    # 4. Windows 1-Click Launchers Validation
    # -------------------------------------------------------------------------
    def test_05_windows_launchers(self):
        """Verify run_all.bat, run_dashboard.bat, and run_api.bat exist and have correct targets."""
        self.assertTrue(os.path.isfile(self.run_all_path), "run_all.bat must exist")
        self.assertTrue(os.path.isfile(self.run_dashboard_path), "run_dashboard.bat must exist")
        self.assertTrue(os.path.isfile(self.run_api_path), "run_api.bat must exist")

        with open(self.run_dashboard_path, "r", encoding="utf-8") as f:
            dash_content = f.read()
        self.assertIn("streamlit run app.py", dash_content)
        self.assertIn("8501", dash_content)

        with open(self.run_api_path, "r", encoding="utf-8") as f:
            api_content = f.read()
        self.assertIn("uvicorn api:app", api_content)
        self.assertIn("8000", api_content)

        with open(self.run_all_path, "r", encoding="utf-8") as f:
            all_content = f.read()
        self.assertIn("run_api.bat", all_content)
        self.assertIn("run_dashboard.bat", all_content)
        self.assertIn("http://localhost:8501", all_content)

    # -------------------------------------------------------------------------
    # 5. Live Endpoint & OpenAPI Schema Verification
    # -------------------------------------------------------------------------
    def test_06_live_fastapi_endpoints(self):
        """Verify that the deployed FastAPI service responds with 200 on /docs and /openapi.json."""
        try:
            req = urllib.request.Request("http://127.0.0.1:8000/docs")
            with urllib.request.urlopen(req, timeout=5) as response:
                self.assertEqual(response.status, 200, "FastAPI /docs must return HTTP 200")

            req_schema = urllib.request.Request("http://127.0.0.1:8000/openapi.json")
            with urllib.request.urlopen(req_schema, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                schema = json.loads(resp.read().decode("utf-8"))

            paths = schema.get("paths", {})
            required_endpoints = [
                "/meetings",
                "/meetings/{meeting_id}",
                "/meetings/{meeting_id}/export/pdf",
                "/meetings/{meeting_id}/export/csv",
                "/meetings/{meeting_id}/export/action-items",
                "/integrations/zoom/webhook",
                "/integrations/zoom/sync",
                "/integrations/google-meet/sync",
                "/auth/register",
                "/auth/login",
                "/auth/me",
            ]
            for ep in required_endpoints:
                self.assertIn(ep, paths, f"OpenAPI schema must declare endpoint: {ep}")

        except urllib.error.URLError:
            self.skipTest("FastAPI server on port 8000 is not currently reachable.")

    def test_07_live_streamlit_health(self):
        """Verify that the deployed Streamlit frontend responds with HTTP 200."""
        try:
            req = urllib.request.Request("http://localhost:8501")
            with urllib.request.urlopen(req, timeout=5) as response:
                self.assertEqual(response.status, 200, "Streamlit dashboard must return HTTP 200")
                html = response.read().decode("utf-8", errors="ignore")
                self.assertIn("Streamlit", html)
        except urllib.error.URLError:
            self.skipTest("Streamlit dashboard on port 8501 is not currently reachable.")

    # -------------------------------------------------------------------------
    # 6. Documentation and Workspace Cleanliness
    # -------------------------------------------------------------------------
    def test_08_readme_completeness(self):
        """Verify README.md contains complete Milestone 1-4 documentation, architecture & quick start."""
        self.assertTrue(os.path.isfile(self.readme_path), "README.md must exist")
        with open(self.readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("WhisperSense AI", content)
        self.assertIn("Milestone 1", content)
        self.assertIn("Milestone 2", content)
        self.assertIn("Milestone 3", content)
        self.assertIn("Milestone 4", content)
        self.assertIn("docker-compose", content)
        self.assertIn("run_all.bat", content)
        self.assertIn("ReportLab", content)
        self.assertIn("Zoom", content)
        self.assertIn("Google Meet", content)
        self.assertNotIn("truthshield", content.lower(), "Found leftover old branding 'truthshield'")

    def test_09_workspace_cleanliness(self):
        """Verify there are no lingering temporary scratch export files in the repository root."""
        dangling_files = [
            "scratch_test_dossier.pdf",
            "scratch_test.csv",
            "test_output.wav",
        ]
        for f in dangling_files:
            p = os.path.join(PROJECT_ROOT, f)
            self.assertFalse(os.path.exists(p), f"Temporary scratch file '{f}' must be cleaned up")


if __name__ == "__main__":
    unittest.main()
