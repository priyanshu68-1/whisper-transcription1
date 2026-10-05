import unittest
import os
import uuid
import tempfile
from fastapi.testclient import TestClient
from database import DatabaseManager, hash_password, verify_password
from api import app

class TestUserAccessAndSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a fresh temporary database to test user registration and strict isolation
        cls.temp_db_fd, cls.temp_db_path = tempfile.mkstemp(suffix=".db")
        cls.db = DatabaseManager(db_path=cls.temp_db_path)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        try:
            os.close(cls.temp_db_fd)
            if os.path.exists(cls.temp_db_path):
                os.remove(cls.temp_db_path)
        except Exception:
            pass

    def test_01_password_hashing_and_verification(self):
        """Test cryptographic salted hash generation and verification."""
        password = "SecretPassword123!"
        pwd_hash, salt = hash_password(password)
        
        self.assertIsNotNone(pwd_hash)
        self.assertIsNotNone(salt)
        self.assertEqual(len(salt), 32)
        
        # Correct password verification
        self.assertTrue(verify_password(password, salt, pwd_hash))
        
        # Incorrect password verification
        self.assertFalse(verify_password("WrongPassword!", salt, pwd_hash))
        self.assertFalse(verify_password("", salt, pwd_hash))

    def test_02_user_registration(self):
        """Test user registration with validation checks."""
        user = self.db.register_user(
            username="alice_test",
            password="alice_password",
            email="alice@example.com",
            full_name="Alice Smith"
        )
        self.assertIn("id", user)
        self.assertEqual(user["username"], "alice_test")
        self.assertEqual(user["full_name"], "Alice Smith")
        self.assertNotIn("password_hash", user)
        self.assertNotIn("salt", user)

        # Duplicate username should raise ValueError
        with self.assertRaises(ValueError):
            self.db.register_user(
                username="alice_test",
                password="another_password"
            )

        # Invalid username length
        with self.assertRaises(ValueError):
            self.db.register_user(username="al", password="valid_password")

    def test_03_user_authentication(self):
        """Test user login and credential validation."""
        self.db.register_user(
            username="bob_test",
            password="bob_password",
            email="bob@example.com",
            full_name="Bob Jones"
        )

        # Valid credentials
        auth_success = self.db.authenticate_user("bob_test", "bob_password")
        self.assertIsNotNone(auth_success)
        self.assertEqual(auth_success["username"], "bob_test")
        self.assertEqual(auth_success["full_name"], "Bob Jones")

        # Invalid password
        auth_wrong_pw = self.db.authenticate_user("bob_test", "wrong_pw")
        self.assertIsNone(auth_wrong_pw)

        # Nonexistent user
        auth_nonexistent = self.db.authenticate_user("ghost_user", "some_pw")
        self.assertIsNone(auth_nonexistent)

    def test_04_multi_user_data_isolation(self):
        """
        Critical Milestone 4 Security Requirement:
        Verify that User A cannot access User B's private meetings.
        """
        # Register User A and User B
        user_a = self.db.register_user("charlie_a", "password_a", full_name="Charlie A")
        user_b = self.db.register_user("david_b", "password_b", full_name="David B")

        meeting_a_id = f"MEET-USERA-{uuid.uuid4().hex[:6].upper()}"
        meeting_b_id = f"MEET-USERB-{uuid.uuid4().hex[:6].upper()}"

        # Save Meeting A for User A
        self.db.save_meeting(
            meeting_id=meeting_a_id,
            title="User A Private Strategy",
            audio_filename="meeting_a.mp3",
            file_size_mb=1.2,
            duration_seconds=60.0,
            format_ext="MP3",
            language="EN",
            transcript="This is a highly confidential meeting for User A.",
            intelligence={"summary": "User A secret plan."},
            participant_data={"unique_participants": ["Charlie A"]},
            validation_info={"is_valid": True},
            user_id=user_a["id"]
        )

        # Save Meeting B for User B
        self.db.save_meeting(
            meeting_id=meeting_b_id,
            title="User B Private Financials",
            audio_filename="meeting_b.mp3",
            file_size_mb=2.0,
            duration_seconds=90.0,
            format_ext="MP3",
            language="EN",
            transcript="This is private financial data for User B.",
            intelligence={"summary": "User B financial budget."},
            participant_data={"unique_participants": ["David B"]},
            validation_info={"is_valid": True},
            user_id=user_b["id"]
        )

        # 1. User A retrieves meetings: should ONLY see Meeting A
        user_a_meetings = self.db.list_all_meetings(user_id=user_a["id"])
        user_a_ids = [m["meeting_id"] for m in user_a_meetings]
        self.assertIn(meeting_a_id, user_a_ids)
        self.assertNotIn(meeting_b_id, user_a_ids, "Security breach: User A sees User B's meeting!")

        # 2. User B retrieves meetings: should ONLY see Meeting B
        user_b_meetings = self.db.list_all_meetings(user_id=user_b["id"])
        user_b_ids = [m["meeting_id"] for m in user_b_meetings]
        self.assertIn(meeting_b_id, user_b_ids)
        self.assertNotIn(meeting_a_id, user_b_ids, "Security breach: User B sees User A's meeting!")

        # 3. Direct access isolation: User A cannot get Meeting B directly
        unauthorized_access = self.db.get_meeting(meeting_b_id, user_id=user_a["id"])
        self.assertIsNone(unauthorized_access, "Security breach: User A fetched User B's meeting via get_meeting!")

        # Authorized access works
        authorized_access = self.db.get_meeting(meeting_a_id, user_id=user_a["id"])
        self.assertIsNotNone(authorized_access)
        self.assertEqual(authorized_access["title"], "User A Private Strategy")

    def test_05_api_auth_endpoints(self):
        """Test FastAPI /auth/register, /auth/login, and /auth/me endpoints."""
        username = f"api_user_{uuid.uuid4().hex[:6]}"
        password = "secure_api_password_123"

        # Register via API
        reg_resp = self.client.post("/auth/register", json={
            "username": username,
            "password": password,
            "email": f"{username}@test.com",
            "full_name": "API Test User"
        })
        self.assertEqual(reg_resp.status_code, 200)
        data = reg_resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["user"]["username"], username)
        user_id = data["user"]["id"]

        # Login via API
        login_resp = self.client.post("/auth/login", json={
            "username": username,
            "password": password
        })
        self.assertEqual(login_resp.status_code, 200)
        login_data = login_resp.json()
        self.assertEqual(login_data["status"], "success")
        self.assertIn("token", login_data)

        # Invalid Login via API
        bad_login_resp = self.client.post("/auth/login", json={
            "username": username,
            "password": "wrong_password_here"
        })
        self.assertEqual(bad_login_resp.status_code, 401)

        # Get Profile via API
        profile_resp = self.client.get(f"/auth/me?user_id={user_id}")
        self.assertEqual(profile_resp.status_code, 200)
        self.assertEqual(profile_resp.json()["username"], username)

if __name__ == "__main__":
    unittest.main()
