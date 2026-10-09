import unittest, json, os
os.environ['SECRET_KEY'] = 'test-secret-key-2026'
from datetime import datetime, date, timedelta
from app import app, db, User, Customer, Lead, Opportunity, FollowUp, AuditLog, valid_email, valid_phone, valid_pwd
from seed import seed_database

class TestAcxiomCRM(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            seed_database(self.app)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_validators(self):
        self.assertTrue(valid_email('user@domain.com'))
        self.assertFalse(valid_email('bad-email'))
        self.assertTrue(valid_phone('+1-555-0199'))
        self.assertFalse(valid_phone('123'))
        v_p, _ = valid_pwd('Admin@123456')
        self.assertTrue(v_p)

    def test_account_lockout(self):
        for i in range(4):
            res = self.client.post('/login', data={'username': 'sales1', 'password': 'WrongPassword123'}, follow_redirects=True)
            self.assertIn(b'Invalid credentials', res.data)

        res5 = self.client.post('/login', data={'username': 'sales1', 'password': 'WrongPassword123'}, follow_redirects=True)
        self.assertIn(b'Account locked', res5.data)

    def test_rbac_user_management(self):
        self.client.post('/login', data={'username': 'sales1', 'password': 'Sales@123456'}, follow_redirects=True)
        res = self.client.get('/users', follow_redirects=True)
        self.assertIn(b'Access denied', res.data)

        self.client.get('/logout', follow_redirects=True)
        self.client.post('/login', data={'username': 'admin', 'password': 'Admin@123456'}, follow_redirects=True)
        res_admin = self.client.get('/users', follow_redirects=True)
        self.assertIn(b'User Administration', res_admin.data)

    def test_lead_conversion_workflow(self):
        self.client.post('/login', data={'username': 'admin', 'password': 'Admin@123456'}, follow_redirects=True)
        with self.app.app_context():
            lead_id = Lead.query.filter_by(contact_name='Robert Chen').first().id

        res = self.client.post(f'/leads/{lead_id}/convert', data={'amount': '25000.00'}, follow_redirects=True)
        self.assertIn(b'Lead converted to Customer', res.data)

    def test_rest_api(self):
        login_res = self.client.post('/api/v1/auth/login', data=json.dumps({'username': 'admin', 'password': 'Admin@123456'}), content_type='application/json')
        self.assertEqual(login_res.status_code, 200)

        cust_res = self.client.get('/api/v1/customers')
        self.assertEqual(cust_res.status_code, 200)

if __name__ == '__main__':
    unittest.main()
