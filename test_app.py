"""
Automated Comprehensive Test Suite for Attendify System
Tests Database initialization, seed data, CRUD operations, Analytics,
Flask routes, role-based access control, and input validation rules.
"""
import os
import sys
import unittest

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
from backend.database import init_db, get_db_connection, seed_sample_data, reset_data
from modules.student import (
    get_all_students, get_student_by_id, add_student,
    update_student, delete_student, get_student_profile_data,
    generate_next_roll, normalize_indian_phone
)
from modules.attendance import (
    get_attendance_sheet, save_batch_attendance,
    get_attendance_history, get_attendance_analysis
)
from modules.performance import (
    get_all_performance, add_performance_record,
    update_performance_record, delete_performance_record,
    get_performance_analysis
)
from modules.dashboard import (
    get_dashboard_metrics, get_dashboard_charts_data,
    get_at_risk_students
)
from modules.reports import (
    generate_attendance_report, generate_performance_report,
    generate_student_dossier, generate_class_summary_report
)


class TestAttendifySystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize DB and seed
        init_db()
        seed_sample_data()
        cls.client = app.test_client()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False

    def test_01_db_initialization_and_seeding(self):
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
        self.assertIsNotNone(user)

        students = conn.execute("SELECT COUNT(*) as count FROM students").fetchone()
        self.assertGreater(students['count'], 0)

        att = conn.execute("SELECT COUNT(*) as count FROM attendance").fetchone()
        self.assertGreater(att['count'], 0)

        perf = conn.execute("SELECT COUNT(*) as count FROM performance").fetchone()
        self.assertGreater(perf['count'], 0)
        conn.close()

    def test_02_student_crud(self):
        # 1. Add student (auto-roll within Class 1-A range 1001-1099)
        new_data = {
            'name': 'Test Student',
            'class_name': 'Class 1',
            'division': 'A',
            'email': 'test.student@apextech.edu',
            'phone': '9876543210',
            'gender': 'Female',
            'date_of_birth': '2019-01-01',
            'admission_date': '2025-07-01'
        }
        success, msg, new_id = add_student(new_data)
        self.assertTrue(success)
        self.assertIsNotNone(new_id)

        st = get_student_by_id(new_id)
        self.assertEqual(st['name'], 'Test Student')
        # Roll encodes section: Class 1-A -> 1001..1099
        self.assertRegex(st['roll'], r'^\d{4}$')
        self.assertTrue(1001 <= int(st['roll']) <= 1099)
        # Phone stored in canonical +91 format
        self.assertTrue(st['phone'].startswith('+91 '))
        self.assertEqual(st['phone'].replace(' ', ''), '+919876543210')

        # 2. Sequential generation within the same section
        success2, _, new_id2 = add_student({**new_data, 'name': 'Second Student'})
        self.assertTrue(success2)
        st2 = get_student_by_id(new_id2)
        self.assertEqual(int(st2['roll']), int(st['roll']) + 1)

        # 3. Manual roll outside the section range is rejected WITH the range
        bad = {**new_data, 'name': 'Range Kid', 'roll': '9999'}
        ok, err, _ = add_student(bad)
        self.assertFalse(ok)
        self.assertIn('1099', err)          # correct range shown in error

        # 4. Duplicate roll numbers are rejected school-wide
        dup = {**new_data, 'name': 'Dup Kid', 'roll': st['roll']}
        ok, err, _ = add_student(dup)
        self.assertFalse(ok)
        self.assertIn('already assigned', err)

        # 5. Non-numeric rolls are rejected
        ok, err, _ = add_student({**new_data, 'name': 'Alpha Kid', 'roll': '10AB'})
        self.assertFalse(ok)
        self.assertIn('digits only', err)

        # 6. Get by ID / update phone (roll immutable)
        up_success, up_msg = update_student(new_id, {**new_data, 'phone': '+91 98765 00000'})
        self.assertTrue(up_success)
        self.assertEqual(get_student_by_id(new_id)['phone'], '+91 98765 00000')
        self.assertEqual(get_student_by_id(new_id)['roll'], st['roll'])

        # 7. Moving a student to a section that contradicts their roll is blocked
        ok, err = update_student(new_id, {**new_data, 'class_name': 'Class 5'})
        self.assertFalse(ok)
        self.assertIn('does not belong', err)

        # 8. Profile Data
        profile = get_student_profile_data(new_id)
        self.assertIsNotNone(profile)
        self.assertEqual(profile['student']['name'], 'Test Student')

        # 9. Deleting a student does NOT release their roll number
        #    (permanent occupancy via roll_ledger). Seeds hold 1001-1003;
        #    the deleted test rolls 1004/1005 stay burned -> next is 1006.
        del_ok, _ = delete_student(new_id)
        self.assertTrue(del_ok)
        delete_student(new_id2)
        from modules.student import peek_next_roll
        self.assertEqual(peek_next_roll('Class 1', 'A'), '1006')

    def test_03_attendance_operations(self):
        sheet = get_attendance_sheet('Class 3', 'A', 'Mathematics', '2025-02-15')
        self.assertGreater(len(sheet), 0)

        # Save batch attendance
        st_id = sheet[0]['id']
        batch_data = {str(st_id): 'Present'}
        success, msg, count = save_batch_attendance('2025-02-15', 'Mathematics', 'Class 3', 'A', batch_data)
        self.assertTrue(success)
        self.assertEqual(count, 1)

        # Attendance Analysis
        analysis = get_attendance_analysis('Class 3', 'A')
        self.assertIn('summary', analysis)
        self.assertIn('students', analysis)

        # History log
        history = get_attendance_history(class_name='Class 3')
        self.assertIsInstance(history, list)

    def test_04_performance_operations(self):
        students = get_all_students()
        st_id = students[0]['id']

        success, msg, new_id = add_performance_record(
            student_id=st_id,
            subject='Environmental Studies',
            internal_marks=35.0,
            external_marks=52.0,
            semester='Term 1 (Midterm)'
        )
        self.assertTrue(success)

        perf_list = get_all_performance(student_id=st_id)
        self.assertGreater(len(perf_list), 0)

        analysis = get_performance_analysis()
        self.assertGreater(analysis['summary']['total_records'], 0)

        # Delete test record
        del_success, del_msg = delete_performance_record(new_id)
        self.assertTrue(del_success)

    def test_05_dashboard_metrics_and_charts(self):
        metrics = get_dashboard_metrics()
        self.assertIn('total_students', metrics)
        self.assertIn('avg_attendance', metrics)
        self.assertIn('avg_performance', metrics)

        charts = get_dashboard_charts_data()
        self.assertIn('attendance_pie', charts)
        self.assertIn('monthly_trend', charts)
        self.assertIn('performance_dist', charts)
        self.assertIn('subject_performance', charts)
        self.assertIn('correlation', charts)

        at_risk = get_at_risk_students()
        self.assertIsInstance(at_risk, list)

    def test_06_reports_generation(self):
        att_rep = generate_attendance_report()
        self.assertEqual(att_rep['report_type'], 'attendance')

        perf_rep = generate_performance_report()
        self.assertEqual(perf_rep['report_type'], 'performance')

        students = get_all_students()
        dossier = generate_student_dossier(students[0]['id'])
        self.assertEqual(dossier['report_type'], 'student_dossier')

        cls_rep = generate_class_summary_report('Class 3')
        self.assertEqual(cls_rep['report_type'], 'class_summary')

    def test_07_flask_routes_and_authentication(self):
        client = app.test_client()
        client.get('/logout')

        # 1. Access protected route without login -> redirect to login
        res = client.get('/dashboard')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.location)

        # 2. Login as Principal
        login_res = client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Dashboard', login_res.data)

        # 3-13. Key pages render for the Principal
        for path in ['/dashboard', '/students', '/attendance', '/attendance/history',
                     '/attendance/analysis', '/performance', '/performance/analysis',
                     '/reports', '/reports/attendance', '/settings',
                     '/reports/export/students-csv', '/api/dashboard/stats']:
            res = client.get(path)
            self.assertEqual(res.status_code, 200, path)


class TestRoleBasedAccess(unittest.TestCase):
    """Role-based authentication: Principal full access, Teacher class-scoped."""

    @classmethod
    def setUpClass(cls):
        init_db()
        seed_sample_data()
        app.config['TESTING'] = True

    def _login(self, username, password):
        client = app.test_client()
        client.get('/logout')
        return client, client.post(
            '/login',
            data={'username': username, 'password': password},
            follow_redirects=False
        )

    def test_08_teacher_accounts_exist_with_assignments(self):
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT username, role, standard, division FROM users WHERE role = 'Teacher'"
        ).fetchall()
        conn.close()
        # Primary school: 6 standards x 2 divisions = 12 class teachers
        self.assertEqual(len(rows), 12)
        for r in rows:
            self.assertIsNotNone(r['standard'])
            self.assertIsNotNone(r['division'])

    def test_09_teacher_login_redirects_to_class_dashboard(self):
        client, res = self._login('teacher3a', 'teach123')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/teacher-dashboard', res.location)

        # Principal login goes to the school-wide dashboard instead
        client.get('/logout')
        _, res = self._login('admin', 'admin123')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/dashboard', res.location)

    def test_10_teacher_dashboard_is_scoped_to_assigned_class(self):
        conn = get_db_connection()
        expected = conn.execute(
            "SELECT COUNT(*) c FROM students WHERE class_name='Class 3' AND division='A'"
        ).fetchone()['c']
        total = conn.execute("SELECT COUNT(*) c FROM students").fetchone()['c']
        other_id = conn.execute(
            "SELECT id FROM students WHERE NOT (class_name='Class 3' AND division='A') LIMIT 1"
        ).fetchone()['id']
        own_id = conn.execute(
            "SELECT id FROM students WHERE class_name='Class 3' AND division='A' LIMIT 1"
        ).fetchone()['id']
        conn.close()

        client, res = self._login('teacher3a', 'teach123')

        # Dashboard renders and shows the assigned section
        dash = client.get('/teacher-dashboard')
        self.assertEqual(dash.status_code, 200)
        html = dash.data.decode('utf-8', 'ignore')
        self.assertIn('Class 3', html)
        self.assertIn('Division A', html)

        # API metrics scoped to the assigned section only
        stats = client.get('/api/dashboard/stats').get_json()
        self.assertEqual(stats['total_students'], expected)
        self.assertNotEqual(stats['total_students'], total)

        # Own-class student accessible; other-class student blocked
        self.assertEqual(client.get(f'/students/{own_id}').status_code, 200)
        res_other = client.get(f'/students/{other_id}')
        self.assertEqual(res_other.status_code, 302)

    def test_11_teacher_cannot_modify_other_class_data(self):
        client, _ = self._login('teacher3a', 'teach123')

        # Forged attendance save for another class is rejected
        res = client.post('/attendance/save', data={
            'date': '2026-01-15', 'subject': 'Mathematics',
            'class_name': 'Class 5', 'division': 'B',
            'attendance_1': 'Present'
        })
        self.assertEqual(res.status_code, 302)

        # Settings are Principal-only
        res = client.get('/settings', follow_redirects=True)
        self.assertIn(b'Access denied', res.data)

    def test_12_principal_has_school_wide_access(self):
        client, _ = self._login('admin', 'admin123')

        stats = client.get('/api/dashboard/stats').get_json()
        conn = get_db_connection()
        total = conn.execute("SELECT COUNT(*) c FROM students").fetchone()['c']
        conn.close()

        self.assertEqual(stats['total_students'], total)
        self.assertEqual(client.get('/settings').status_code, 200)
        self.assertEqual(client.get('/dashboard').status_code, 200)


class TestValidationRules(unittest.TestCase):
    """Indian phone validation + automatic roll number sequence."""

    @classmethod
    def setUpClass(cls):
        init_db()
        seed_sample_data()
        app.config['TESTING'] = True

    def test_13_phone_accepts_valid_formats(self):
        cases = {
            '9876543210': '+91 98765 43210',           # bare 10 digits
            '98765 43210': '+91 98765 43210',          # spaced
            '+91 98765 43210': '+91 98765 43210',      # full format
            '+919876543210': '+91 98765 43210',        # pasted country code
            '919876543210': '+91 98765 43210',         # country code no plus
            '7894561230': '+91 78945 61230',           # starts with 7
            '6123456789': '+91 61234 56789',           # starts with 6
        }
        for raw, expected in cases.items():
            self.assertEqual(normalize_indian_phone(raw), expected, raw)

    def test_14_phone_rejects_invalid_values(self):
        bad = [
            '', None, '12345',                    # too short
            '98765432109876543210',               # way too long
            '987654321',                          # 9 digits
            '98765432101',                        # 11 digits
            'abcdefghij',                         # alphabets
            '98765@4321',                         # special chars, <10 digits
            '0123456789',                         # starts with 0
            '5123456789',                         # starts with 5
            '+44 9876543210',                     # foreign country code digits
        ]
        for raw in bad:
            self.assertIsNone(normalize_indian_phone(raw), repr(raw))

    def test_15_roll_ranges_match_class_and_division(self):
        from modules.student import (
            get_roll_range, peek_next_roll, build_roll_range_map
        )

        # Exact specification ranges for all 12 sections
        expected = {
            ('Class 1', 'A'): (1001, 1099), ('Class 1', 'B'): (1101, 1199),
            ('Class 2', 'A'): (2001, 2099), ('Class 2', 'B'): (2101, 2199),
            ('Class 3', 'A'): (3001, 3099), ('Class 3', 'B'): (3101, 3199),
            ('Class 4', 'A'): (4001, 4099), ('Class 4', 'B'): (4101, 4199),
            ('Class 5', 'A'): (5001, 5099), ('Class 5', 'B'): (5101, 5199),
            ('Class 6', 'A'): (6001, 6099), ('Class 6', 'B'): (6101, 6199),
        }
        for (cls, div), rng in expected.items():
            self.assertEqual(get_roll_range(cls, div), rng)

        # Invalid combinations do not exist
        self.assertIsNone(get_roll_range('Class 7', 'A'))
        self.assertIsNone(get_roll_range('Class 3', 'C'))
        self.assertIsNone(get_roll_range('Nursery', 'A'))

        # Frontend map mirrors the spec and covers exactly 12 sections
        roll_map = build_roll_range_map()
        self.assertEqual(len(roll_map), 12)
        self.assertEqual(roll_map['Class 6|A'], [6001, 6099])
        self.assertEqual(roll_map['Class 1|B'], [1101, 1199])

        # Seeded sections have seats 1-3 taken; next free is seat 4
        self.assertEqual(peek_next_roll('Class 3', 'A'), '3004')
        self.assertEqual(peek_next_roll('Class 6', 'B'), '6104')

    def test_16_add_student_rejects_bad_phone(self):
        new_data = {
            'name': 'Bad Phone Kid',
            'class_name': 'Class 2',
            'division': 'B',
            'email': 'badphone@example.com',
            'phone': '12345',                     # invalid: only 5 digits
            'gender': 'Male'
        }
        success, msg, new_id = add_student(new_data)
        self.assertFalse(success)
        self.assertIsNone(new_id)
        self.assertIn('10-digit', msg)

    def test_17_wrong_series_rolls_rejected(self):
        """Spec examples: a roll from another series must never save."""
        cases = [
            # (class, division, roll, why-invalid)
            ('Class 3', 'A', '4205'),   # 4205 belongs to Class 4-A series
            ('Class 2', 'B', '2050'),   # 2050 is Class 2-A's series, not B
            ('Class 5', 'A', '6105'),   # 6105 belongs to Class 6-B series
        ]
        for cls, div, roll in cases:
            data = {
                'name': f'Wrong Series {roll}',
                'class_name': cls,
                'division': div,
                'email': f'ws{roll}@example.com',
                'phone': '9876500000',
                'gender': 'Male',
                'roll': roll,
            }
            success, msg, new_id = add_student(data)
            self.assertFalse(success, f'{cls}-{div} + {roll} must be rejected')
            self.assertIsNone(new_id)
            self.assertIn('belongs to another class/division series', msg)

        # Verify the correct range is quoted in each error message
        _, msg, _ = add_student({
            'name': 'Range Check', 'class_name': 'Class 3', 'division': 'A',
            'email': 'rc@example.com', 'phone': '9876511111',
            'gender': 'Male', 'roll': '4205'})
        self.assertIn('3001-3099', msg)

    def test_18_duplicate_roll_permanently_blocked(self):
        """Once assigned, a roll can never be reused - even after deletion."""
        base = {
            'name': 'First Owner', 'class_name': 'Class 3', 'division': 'B',
            'email': 'owner3105@example.com', 'phone': '9876522222',
            'gender': 'Female', 'roll': '3105',
        }
        ok, msg, owner_id = add_student(base)
        self.assertTrue(ok)
        self.assertEqual(get_student_by_id(owner_id)['roll'], '3105')

        # Second student trying the same roll -> rejected with exact wording
        ok, msg, _ = add_student({**base, 'name': 'Second Owner',
                                  'email': 'second@example.com'})
        self.assertFalse(ok)
        self.assertEqual(
            msg,
            'Roll number 3105 is already assigned to another student. '
            'Please choose an available roll number from the valid series.')

        # Delete the original owner: the number stays permanently burned
        delete_student(owner_id)
        ok, msg, _ = add_student({**base, 'name': 'Third Attempt',
                                  'email': 'third@example.com'})
        self.assertFalse(ok)
        self.assertIn('already assigned to another student', msg)

        # Suggestion skips burned numbers too (3004... wait: 3-B seeds are
        # 3101-3103; 3105 was burned; next free suggestion must be 3104).
        from modules.student import peek_next_roll
        self.assertEqual(peek_next_roll('Class 3', 'B'), '3104')

    def test_19_phone_field_allows_all_ten_digits(self):
        """Regression suite for the phone input UX:
        1) maxlength must be 11 (10 digits + auto-inserted display space)
        2) HTML5 pattern must tolerate the display space, otherwise the
           browser blocks valid numbers at submit ('only taking 9 digits'
           / 'proper number not accepted' bugs)."""
        client = app.test_client()
        client.get('/logout')
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})

        html = client.get('/students/add').data.decode('utf-8')
        self.assertIn('maxlength="11"', html)
        self.assertIn('pattern="[6-9](\\s?\\d){9}"', html)
        self.assertNotIn('pattern="[6-9][0-9]{9}"', html)

        # Edit form too
        conn = get_db_connection()
        sid = conn.execute('SELECT id FROM students LIMIT 1').fetchone()['id']
        conn.close()
        html = client.get(f'/students/{sid}/edit').data.decode('utf-8')
        self.assertIn('maxlength="11"', html)
        self.assertIn('pattern="[6-9](\\s?\\d){9}"', html)

        # Full form POST with the spaced format the JS produces on screen:
        # must be accepted and stored in canonical +91 form.
        r = client.post('/students/add', data={
            'name': 'Spaced Phone Kid', 'class_name': 'Class 2', 'division': 'A',
            'email': 'spaced@x.com', 'phone': '98765 43210',   # 11 chars incl space
            'gender': 'Male',
        }, follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        new_id = int(r.location.rstrip('/').split('/')[-1])
        row = get_student_by_id(new_id)
        self.assertEqual(row['phone'], '+91 98765 43210')
        delete_student(new_id)


if __name__ == '__main__':
    unittest.main()