"""
Unit Tests for MatriSuraksha True Two-Factor Authentication (Option A)
Tests RFC 6238 TOTP verification, individual per-user cryptographic secrets,
password-gated access, and impersonation resistance without network or SMS dependencies.
"""

import unittest
import time
import os
import sys

# Add project root and app to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "app"))

import db
from app import app


class TestTwoFactorAuthenticationOptionA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()

    def test_totp_rfc6238_generation_and_verification(self):
        """Test standard RFC 6238 TOTP generation and verification."""
        secret = "JBSWY3DPEHPK3PXP"
        otp = db.generate_totp(secret)
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())
        self.assertTrue(db.verify_totp(otp, secret))

        # Test invalid token format
        self.assertFalse(db.verify_totp("12345", secret))
        self.assertFalse(db.verify_totp("abcdef", secret))
        self.assertFalse(db.verify_totp("", secret))

        # Test incorrect token
        wrong_token = "999999" if otp != "999999" else "888888"
        self.assertFalse(db.verify_totp(wrong_token, secret))

    def test_per_user_secret_isolation(self):
        """Verify each authorized user has their own unique secret and cannot impersonate others."""
        users = ["dr.biswas", "dr.arka", "dr.bhakta", "dr.phc", "dr.referral", "cmoh.dd"]
        user_records = {}
        for u in users:
            rec = db.get_user_by_username(u)
            self.assertIsNotNone(rec, f"User {u} should exist in database")
            self.assertTrue(rec.get("totp_secret"), f"User {u} must have a unique totp_secret")
            user_records[u] = rec

        # Ensure all secrets are unique
        secrets = [user_records[u]["totp_secret"] for u in users]
        self.assertEqual(len(secrets), len(set(secrets)), "Each authorized user must have a unique secret")

        # Code generated for dr.arka should NOT verify on dr.biswas
        arka_otp = db.generate_totp(user_records["dr.arka"]["totp_secret"])
        self.assertTrue(db.verify_totp(arka_otp, user_records["dr.arka"]["totp_secret"]))
        self.assertFalse(db.verify_totp(arka_otp, user_records["dr.biswas"]["totp_secret"]))

    def test_verify_user_dual_factor_enforcement(self):
        """Verify that login requires BOTH Factor 1 (Password) AND Factor 2 (Dynamic OTP)."""
        u_rec = db.get_user_by_username("dr.biswas")
        secret = u_rec["totp_secret"]
        valid_otp = db.generate_totp(secret)

        # 1. Invalid username
        u, err = db.verify_user("dr.nonexistent", "matri123", valid_otp)
        self.assertIsNone(u)
        self.assertIn("not recognized", err.lower())

        # 2. Correct username, wrong password
        u, err = db.verify_user("dr.biswas", "wrongpass", valid_otp)
        self.assertIsNone(u)
        self.assertIn("invalid security password", err.lower())

        # 3. Correct username, correct password, but missing OTP
        u, err = db.verify_user("dr.biswas", "matri123", "")
        self.assertIsNone(u)
        self.assertIn("otp is required", err.lower())

        # 4. Correct username, correct password, but wrong OTP
        u, err = db.verify_user("dr.biswas", "matri123", "000000")
        self.assertIsNone(u)
        self.assertIn("invalid or expired", err.lower())

        # 5. Correct username, correct password, but cross-user OTP (impersonation attempt)
        arka_rec = db.get_user_by_username("dr.arka")
        arka_otp = db.generate_totp(arka_rec["totp_secret"])
        u, err = db.verify_user("dr.biswas", "matri123", arka_otp)
        self.assertIsNone(u)
        self.assertIn("invalid or expired", err.lower())

        # 6. Correct username, correct password, correct user dynamic OTP -> SUCCESS
        u, err = db.verify_user("dr.biswas", "matri123", valid_otp)
        self.assertIsNotNone(u)
        self.assertIsNone(err)
        self.assertEqual(u["username"], "dr.biswas")

    def test_setup_2fa_api_password_gated(self):
        """Verify the /api/auth/setup-2fa endpoint is strictly gated by password."""
        client = app.test_client()

        # Without credentials -> 400
        res = client.post("/api/auth/setup-2fa", json={})
        self.assertEqual(res.status_code, 400)

        # With wrong password -> 401 Access Denied
        res = client.post("/api/auth/setup-2fa", json={"username": "dr.arka", "password": "wrong"})
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("incorrect password", data["error"].lower())

        # With correct password -> 200 Success with offline QR image
        res = client.post("/api/auth/setup-2fa", json={"username": "dr.arka", "password": "matri123"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["username"], "dr.arka")
        self.assertEqual(data["totp_secret"], "HXDMVJECJJWSRZ3U")
        self.assertTrue(data["qr_image_data"].startswith("data:image/png;base64,"))


if __name__ == "__main__":
    unittest.main()
