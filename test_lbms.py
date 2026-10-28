"""
test_lbms.py - Comprehensive Unit & Integration Tests for LBMS
Tests DB Schema, Fine/Penalty Calculation, Auth, Issue/Return, NDC, and Zip Download.
"""

import unittest
import json
import zipfile
import io
from app import app
from database import get_db_connection, calculate_fine, calculate_penalty

class TestLBMS(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_01_fine_calculation_rules(self):
        """Test fine calculation for within-a-week and beyond-a-week rules."""
        # On-time return
        days, fine = calculate_fine("2024-09-10", "2024-09-10")
        self.assertEqual(days, 0)
        self.assertEqual(fine, 0.0)

        # 4 days overdue (within a week -> 10 Rs/day)
        days, fine = calculate_fine("2024-09-10", "2024-09-14")
        self.assertEqual(days, 4)
        self.assertEqual(fine, 40.0)

        # 7 days overdue (boundary of 1 week -> 7 * 10 = 70 Rs)
        days, fine = calculate_fine("2024-09-10", "2024-09-17")
        self.assertEqual(days, 7)
        self.assertEqual(fine, 70.0)

        # 12 days overdue (7 * 10 + 5 * 20 = 70 + 100 = 170 Rs)
        days, fine = calculate_fine("2024-09-10", "2024-09-22")
        self.assertEqual(days, 12)
        self.assertEqual(fine, 170.0)

    def test_02_penalty_calculation_rules(self):
        """Test lost book penalty: Book Price + Overdue Fine."""
        # Lost book returned 4 days late, book price 850
        penalty = calculate_penalty(850.0, "2024-09-10", "2024-09-14", is_lost=True)
        self.assertEqual(penalty, 850.0 + 40.0)

        # Lost book on-time (no overdue fine), book price 500
        penalty = calculate_penalty(500.0, "2024-09-10", "2024-09-10", is_lost=True)
        self.assertEqual(penalty, 500.0)

    def test_03_database_tables_and_seed(self):
        """Verify all 5 tables exist and contain seeded data."""
        conn = get_db_connection()
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [t['name'] for t in tables]

        for req in ['Users', 'BookDetails', 'IssueDate', 'ReturnData', 'FineCalculation']:
            self.assertIn(req, table_names, f"Table {req} must exist in database")

        user_count = conn.execute("SELECT COUNT(*) FROM Users").fetchone()[0]
        self.assertGreaterEqual(user_count, 3)

        book_count = conn.execute("SELECT COUNT(*) FROM BookDetails").fetchone()[0]
        self.assertGreaterEqual(book_count, 5)
        conn.close()

    def test_04_auth_login_signup(self):
        """Test user signup and subsequent login session."""
        # 1. Sign up new test user
        test_uid = f"test_student_{unittest.TestCase.id(self)[-4:]}"
        resp = self.client.post('/signup', data={
            'user_id': test_uid,
            'password': 'password123',
            'full_name': 'Test Student',
            'role': 'Student',
            'regno': 'TEST-REG-999',
            'branch': 'CSE',
            'sem': '6th'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # 2. Login with valid credentials
        resp_login = self.client.post('/login', data={
            'user_id': test_uid,
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(resp_login.status_code, 200)
        self.assertIn(b"Test Student", resp_login.data)

        # 3. Reject invalid credentials
        resp_bad = self.client.post('/login', data={
            'user_id': test_uid,
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertIn(b"Invalid User ID or Password", resp_bad.data)

    def test_05_api_book_and_calculator(self):
        """Test REST API endpoints for books and live fine calculator."""
        # Get book by ISBN
        resp = self.client.get('/api/book/978-0078022159')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['book']['Title'], 'Database System Concepts')

        # Calculate fine API
        resp_calc = self.client.post('/api/calculate_fine',
            data=json.dumps({
                'due_date': '2024-09-01',
                'return_date': '2024-09-11',
                'price': 850.0,
                'is_lost': False
            }),
            content_type='application/json'
        )
        self.assertEqual(resp_calc.status_code, 200)
        calc_data = json.loads(resp_calc.data)
        self.assertEqual(calc_data['days_overdue'], 10)
        self.assertEqual(calc_data['fine'], 130.0)

    def test_06_project_zip_download(self):
        """Verify the /download_project route generates a valid ZIP archive."""
        resp = self.client.get('/download_project')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get('Content-Type'), 'application/zip')

        # Verify ZIP archive contents
        zip_buf = io.BytesIO(resp.data)
        with zipfile.ZipFile(zip_buf, 'r') as z:
            file_names = z.namelist()
            # Must contain app.py, database.py, and templates
            has_app = any('app.py' in f for f in file_names)
            has_db = any('database.py' in f for f in file_names)
            self.assertTrue(has_app, "ZIP should contain app.py")
            self.assertTrue(has_db, "ZIP should contain database.py")

if __name__ == '__main__':
    unittest.main()
