"""Small automated tests for the main CRM rules."""

import json
import os
import unittest

# Tests use their own temporary key. Never use this value for deployment.
os.environ.setdefault("SECRET_KEY", "test-only-secret-key")

from app import app
from extensions import db
from models import Lead
from seed import seed_database
from validators import valid_email, valid_phone, valid_pwd


class AcxiomCRMTests(unittest.TestCase):
    def setUp(self):
        app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=False,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        )
        self.client = app.test_client()

        with app.app_context():
            db.drop_all()
            db.create_all()
            seed_database()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, username, password):
        return self.client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )

    def test_input_validation(self):
        self.assertTrue(valid_email("person@example.in"))
        self.assertFalse(valid_email("not-an-email"))
        self.assertTrue(valid_phone("+91 9876543210"))
        self.assertFalse(valid_phone("123"))
        self.assertTrue(valid_pwd("Admin@123456")[0])
        self.assertFalse(valid_pwd("weak")[0])

    def test_five_bad_passwords_lock_the_account(self):
        for _ in range(4):
            response = self.login("sales1", "incorrect-password")
            self.assertIn(b"Invalid credentials", response.data)

        response = self.login("sales1", "incorrect-password")
        self.assertIn(b"Account locked", response.data)

    def test_only_admin_can_open_user_management(self):
        self.login("sales1", "Sales@123456")
        response = self.client.get("/users", follow_redirects=True)
        self.assertIn(b"Access denied", response.data)

        self.client.post("/logout", follow_redirects=True)
        self.login("admin", "Admin@123456")
        response = self.client.get("/users", follow_redirects=True)
        self.assertIn(b"User Administration", response.data)

    def test_lead_can_be_converted(self):
        self.login("admin", "Admin@123456")
        with app.app_context():
            lead_id = Lead.query.filter_by(contact_name="Ravi Kumar").first().id

        response = self.client.post(
            f"/leads/{lead_id}/convert",
            data={"amount": "350000"},
            follow_redirects=True,
        )
        self.assertIn(b"Lead converted to Customer", response.data)

    def test_api_login_and_customer_list(self):
        response = self.client.post(
            "/api/v1/auth/login",
            data=json.dumps({"username": "admin", "password": "Admin@123456"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/api/v1/customers")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(item["name"] == "ABC Technologies" for item in response.json))


if __name__ == "__main__":
    unittest.main(verbosity=2)
