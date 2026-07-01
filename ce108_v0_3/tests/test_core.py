import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from ce108.admin_service import approve_question, create_question
from ce108.database import connect, fetch_all, fetch_one
from ce108.security import hash_password
from ce108.seed import seed_database
from ce108.services import (
    answer_diagnostic,
    authenticate_user,
    check_answer,
    generate_daily_plan,
    get_diagnostic_state,
    get_mastery_report,
    get_question,
    get_student_summary_for_teacher,
    record_answer,
    schedule_review,
    start_diagnostic,
)


class TestCore(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.db = Path(self.t.name) / 'test.db'
        seed_database(self.db)
        self.student = authenticate_user('student@ce108.local', 'demo1234', self.db)
        self.teacher = authenticate_user('teacher@ce108.local', 'demo1234', self.db)
        self.admin = authenticate_user('admin@ce108.local', 'demo1234', self.db)

    def tearDown(self):
        self.t.cleanup()

    def test_demo_login(self):
        self.assertEqual(self.student['role'], 'student')

    def test_invalid_login(self):
        self.assertIsNone(authenticate_user('student@ce108.local', 'wrong-password', self.db))

    def test_diagnostic_has_30_unique_questions(self):
        session = start_diagnostic(self.student['id'], 30, self.db)
        items = get_diagnostic_state(self.student['id'], session['id'], self.db)['items']
        ids = [i['question_id'] for i in items]
        self.assertEqual(len(ids), 30)
        self.assertEqual(len(set(ids)), 30)

    def test_diagnostic_duplicate_answer_is_rejected(self):
        session = start_diagnostic(self.student['id'], 30, self.db)
        item = get_diagnostic_state(self.student['id'], session['id'], self.db)['items'][0]
        q = get_question(item['question_id'], self.db)
        answer_diagnostic(self.student['id'], session['id'], q['id'], q['correct_codes'], q.get('numeric_answer'), '確実に分かる', 20, self.db)
        with self.assertRaises(ValueError):
            answer_diagnostic(self.student['id'], session['id'], q['id'], q['correct_codes'], q.get('numeric_answer'), '確実に分かる', 20, self.db)

    def test_answer_save_and_correct_judgement(self):
        q = get_question(1, self.db)
        result = record_answer(self.student['id'], q['id'], q['correct_codes'], None, '確実に分かる', 30, 'test', db_path=self.db)
        saved = fetch_one('SELECT * FROM answer_history WHERE user_id=? AND question_id=?', (self.student['id'], q['id']), self.db)
        self.assertTrue(result['is_correct'])
        self.assertEqual(saved['is_correct'], 1)

    def test_numeric_tolerance(self):
        q = next(get_question(r['id'], self.db) for r in fetch_all("SELECT id FROM questions WHERE question_type='numeric'", (), self.db))
        self.assertTrue(check_answer(q, [], q['numeric_answer'] + (q['numeric_tolerance'] / 2)))

    def test_mastery_is_updated(self):
        q = get_question(1, self.db)
        record_answer(self.student['id'], q['id'], q['correct_codes'], None, 'たぶん分かる', 45, 'test', db_path=self.db)
        rows = [r for r in get_mastery_report(self.student['id'], self.db) if r['total_answers']]
        self.assertTrue(rows)
        self.assertGreater(rows[0]['mastery_score'], 0)

    def test_review_date_decision(self):
        q = get_question(1, self.db)
        review = schedule_review(self.student['id'], q['id'], False, '迷った', 3, self.db)
        self.assertEqual(review, (date.today() + timedelta(days=1)).isoformat())

    def test_daily_plan_generation(self):
        plan = generate_daily_plan(self.student['id'], count=5, db_path=self.db)
        self.assertEqual(len(plan['items']), 5)

    def test_unconfirmed_question_cannot_be_published(self):
        with self.assertRaises(ValueError):
            create_question(self.admin['id'], 'single', '権利未確認の問題', 'MED-ANAT', ['A', 'B'], ['1'], None, None, '短', '標準', '詳細', 3, 2, 'checking', 'published', self.db)

    def test_teacher_cannot_access_unassigned_student(self):
        now = '2026-01-01T00:00:00+00:00'
        with connect(self.db) as conn:
            uid = conn.execute("INSERT INTO users(email,password_hash,role,status,created_at,updated_at) VALUES(?,?, 'student','active',?,?)", ('other@student.local', hash_password('demo1234'), now, now)).lastrowid
            conn.execute("INSERT INTO user_profiles(user_id,display_name,school_name,grade) VALUES(?, '担当外学生','別校','4年')", (uid,))
        with self.assertRaises(PermissionError):
            get_student_summary_for_teacher(self.teacher['id'], uid, self.db)

    def test_approval_requires_permission(self):
        qid = create_question(self.admin['id'], 'single', '承認前問題', 'MED-ANAT', ['A', 'B'], ['1'], None, None, '短', '標準', '詳細', 3, 2, 'checking', 'draft', self.db)
        with self.assertRaises(ValueError):
            approve_question(qid, self.admin['id'], self.db)


class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from api import app
        cls.client = TestClient(app)

    def _token(self, username='student@ce108.local', password='demo1234'):
        res = self.client.post('/api/auth/login', data={'username': username, 'password': password})
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()['access_token']

    def test_demo_login_api(self):
        token = self._token()
        res = self.client.get('/api/users/me', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['role'], 'student')

    def test_invalid_login_api(self):
        res = self.client.post('/api/auth/login', data={'username': 'student@ce108.local', 'password': 'bad'})
        self.assertEqual(res.status_code, 401)

    def test_student_admin_api_is_forbidden(self):
        token = self._token()
        res = self.client.get('/api/admin/questions', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res.status_code, 403)

    def test_question_api_hides_answer_before_response(self):
        token = self._token()
        res = self.client.get('/api/questions/1', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res.status_code, 200)
        text = json.dumps(res.json(), ensure_ascii=False)
        self.assertNotIn('correct_codes', text)
        self.assertNotIn('is_correct', text)
        self.assertNotIn('numeric_answer', text)
        self.assertNotIn('explanation_short', text)
        self.assertNotIn('explanation_standard', text)
        self.assertNotIn('explanation_detailed', text)


if __name__ == '__main__':
    unittest.main()
