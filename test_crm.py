import unittest
import os
import json
from datetime import datetime, date, timedelta
from app import create_app
from app.models import db, User, Customer, Lead, Opportunity, FollowUp, AuditLog
from app.config import Config
from app.utils.validators import validate_email, validate_phone, validate_password_strength, validate_lead_status_transition, validate_followup_date, validate_opportunity_fields
from seed import seed_database

class TestAcxiomCRM(unittest.TestCase):

    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
            WTF_CSRF_ENABLED = False

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            seed_database()


    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    # ----------------------------------------------------
    # 1. Validation & Policy Unit Tests
    # ----------------------------------------------------
    def test_validators(self):
        # Email validator
        valid_e, _ = validate_email('user@domain.com')
        invalid_e, _ = validate_email('bad-email-format')
        self.assertTrue(valid_e)
        self.assertFalse(invalid_e)

        # Phone validator
        valid_p, _ = validate_phone('+1-555-0199')
        invalid_p, _ = validate_phone('123')
        self.assertTrue(valid_p)
        self.assertFalse(invalid_p)

        # Password strength
        valid_pwd, _ = validate_password_strength('Admin@123456')
        invalid_pwd, _ = validate_password_strength('simple')
        self.assertTrue(valid_pwd)
        self.assertFalse(invalid_pwd)

        # Lead status transition workflow rules
        valid_t, _ = validate_lead_status_transition('New', 'Qualified')
        invalid_t, _ = validate_lead_status_transition('Converted', 'New')
        self.assertTrue(valid_t)
        self.assertFalse(invalid_t)

        # Follow-up date validation
        past_date = (datetime.utcnow() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M')
        future_date = (datetime.utcnow() + timedelta(days=2)).strftime('%Y-%m-%d %H:%M')
        
        v_past, _ = validate_followup_date(past_date, allow_past=False)
        v_future, _ = validate_followup_date(future_date, allow_past=False)
        self.assertFalse(v_past)
        self.assertTrue(v_future)

        # Opportunity field validation
        v_opp_val, res_opp = validate_opportunity_fields(1000.0, 50.0, (date.today() + timedelta(days=10)).strftime('%Y-%m-%d'), is_active=True)
        self.assertTrue(v_opp_val)
        self.assertEqual(res_opp[0], 1000.0)

        v_opp_neg, _ = validate_opportunity_fields(-50.0, 50.0, (date.today() + timedelta(days=10)).strftime('%Y-%m-%d'), is_active=True)
        self.assertFalse(v_opp_neg)

    # ----------------------------------------------------
    # 2. Authentication & Account Lockout Tests
    # ----------------------------------------------------
    def test_account_lockout(self):
        # Fail login 4 times for 'sales1'
        for i in range(4):
            res = self.client.post('/auth/login', data={'username': 'sales1', 'password': 'WrongPassword123'}, follow_redirects=True)
            self.assertIn(b'Invalid credentials', res.data)

        # 5th failed attempt locks the account
        res5 = self.client.post('/auth/login', data={'username': 'sales1', 'password': 'WrongPassword123'}, follow_redirects=True)
        self.assertIn(b'Account has been locked', res5.data)

        # 6th attempt should block due to account lockout
        res6 = self.client.post('/auth/login', data={'username': 'sales1', 'password': 'Sales@123456'}, follow_redirects=True)
        self.assertIn(b'Account is locked', res6.data)

    # ----------------------------------------------------
    # 3. RBAC Access Control Tests
    # ----------------------------------------------------
    def test_rbac_user_management(self):
        # Login as Sales Executive 'sales1'
        self.client.post('/auth/login', data={'username': 'sales1', 'password': 'Sales@123456'}, follow_redirects=True)
        
        # Accessing Admin-only user management should redirect to dashboard with access denied error
        res = self.client.get('/users/', follow_redirects=True)
        self.assertIn(b'Access denied', res.data)

        # Logout sales1 and login as Admin 'admin'
        self.client.get('/auth/logout', follow_redirects=True)
        self.client.post('/auth/login', data={'username': 'admin', 'password': 'Admin@123456'}, follow_redirects=True)
        
        # Admin should access user management successfully
        res_admin = self.client.get('/users/', follow_redirects=True)
        self.assertIn(b'User & Role Administration', res_admin.data)



    # ----------------------------------------------------
    # 4. Customer Duplicate Check & CRUD Tests
    # ----------------------------------------------------
    def test_customer_duplicate_prevention(self):
        self.client.post('/auth/login', data={'username': 'admin', 'password': 'Admin@123456'}, follow_redirects=True)
        
        # Try creating customer with duplicate email of existing Acme Global ('contact@acmeglobal.com')
        res = self.client.post('/customers/create', data={
            'name': 'Duplicate Acme',
            'email': 'contact@acmeglobal.com',
            'phone': '+1-555-9999',
            'status': 'Active'
        }, follow_redirects=True)
        
        self.assertIn(b'already exists', res.data)

    # ----------------------------------------------------
    # 5. Lead Conversion Workflow Test
    # ----------------------------------------------------
    def test_lead_conversion_workflow(self):
        self.client.post('/auth/login', data={'username': 'admin', 'password': 'Admin@123456'}, follow_redirects=True)

        with self.app.app_context():
            lead = Lead.query.filter_by(contact_name='Robert Chen').first()
            lead_id = lead.id

        # Convert qualified lead
        res = self.client.post(f'/leads/{lead_id}/convert', data={
            'customer_name': 'Robert Chen',
            'customer_email': 'rchen@apexfin.com',
            'customer_phone': '+1-555-0312',
            'create_opportunity': 'yes',
            'opp_name': 'Apex Financial Deal',
            'opp_amount': '25000.00',
            'opp_probability': '30',
            'opp_close_date': (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
        }, follow_redirects=True)

        self.assertIn(b'Lead successfully converted', res.data)

        with self.app.app_context():
            updated_lead = Lead.query.get(lead_id)
            self.assertEqual(updated_lead.status, 'Converted')
            new_cust = Customer.query.filter_by(email='rchen@apexfin.com').first()
            self.assertIsNotNone(new_cust)

    # ----------------------------------------------------
    # 6. REST API Endpoint Tests
    # ----------------------------------------------------
    def test_rest_api(self):
        # 1. API Login
        login_res = self.client.post('/api/v1/auth/login', data=json.dumps({
            'username': 'admin',
            'password': 'Admin@123456'
        }), content_type='application/json')
        
        self.assertEqual(login_res.status_code, 200)
        login_json = json.loads(login_res.data)
        self.assertEqual(login_json['status'], 'success')

        # 2. Get Customers API
        cust_res = self.client.get('/api/v1/customers')
        self.assertEqual(cust_res.status_code, 200)
        cust_json = json.loads(cust_res.data)
        self.assertGreaterEqual(cust_json['count'], 2)

        # 3. Create Customer via REST API
        new_cust_payload = {
            'name': 'API Tech Corp',
            'email': 'api@techcorp.io',
            'phone': '+1-555-9876',
            'address': '101 API Way',
            'notes': 'Created via REST API'
        }
        create_res = self.client.post('/api/v1/customers', data=json.dumps(new_cust_payload), content_type='application/json')
        self.assertEqual(create_res.status_code, 201)

if __name__ == '__main__':
    unittest.main()
