import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
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
    get_focus_plan,
    get_admin_quality_summary,
    get_daily_status,
    get_diagnostic_state,
    get_mastery_report,
    get_question,
    get_review_queue,
    get_student_summary_for_teacher,
    get_teacher_support_summary,
    get_study_strategy,
    record_answer,
    add_exam_event,
    add_score_record,
    save_beta_feedback,
    schedule_review,
    set_target_exam_date,
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

    def test_focus_plan_modes(self):
        medical = get_focus_plan(self.student['id'], 'medical', 5, self.db)
        engineering = get_focus_plan(self.student['id'], 'engineering', 5, self.db)
        self.assertEqual(medical['mode'], 'medical')
        self.assertTrue(all(item['subject_name'] in {'医学概論・基礎医学', '臨床医学総論'} for item in medical['items']))
        self.assertEqual(engineering['mode'], 'engineering')
        self.assertTrue(engineering['items'])

    def test_exam_strategy_records_scores_and_events(self):
        set_target_exam_date(self.student['id'], (date.today() + timedelta(days=120)).isoformat(), self.db)
        add_exam_event(self.student['id'], 'mock', '第1回模試', (date.today() + timedelta(days=30)).isoformat(), db_path=self.db)
        add_score_record(self.student['id'], 'mock', '第1回模試', date.today().isoformat(), 120, 180, {'医学概論・基礎医学': 70, '臨床医学総論': 65}, db_path=self.db)
        strategy = get_study_strategy(self.student['id'], self.db)
        self.assertEqual(strategy['phase'], 'normal')
        self.assertEqual(strategy['recommended_mode'], 'medical')
        self.assertTrue(strategy['events'])
        self.assertTrue(strategy['radar'])

    def test_daily_status_concurrent_generation_is_stable(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            statuses = list(executor.map(lambda _: get_daily_status(self.student['id'], self.db), range(4)))
        plans = fetch_all('SELECT * FROM daily_study_plans WHERE user_id=? AND plan_date=?', (self.student['id'], date.today().isoformat()), self.db)
        self.assertEqual(len(plans), 1)
        self.assertTrue(all(s['total_count'] == statuses[0]['total_count'] for s in statuses))

    def test_daily_status_tracks_completion_and_streak(self):
        plan = generate_daily_plan(self.student['id'], count=5, db_path=self.db)
        q = get_question(plan['items'][0]['question_id'], self.db)
        record_answer(self.student['id'], q['id'], q['correct_codes'], q.get('numeric_answer'), 'たぶん分かる', 20, 'daily', db_path=self.db)
        status = get_daily_status(self.student['id'], self.db)
        self.assertEqual(status['completed_count'], 1)
        self.assertEqual(status['status'], 'in_progress')
        self.assertGreaterEqual(status['streak_days'], 1)
        self.assertEqual(len(status['weekly']), 7)

    def test_review_queue_labels_due_items(self):
        q = get_question(1, self.db)
        with connect(self.db) as conn:
            conn.execute("INSERT OR IGNORE INTO review_schedules(user_id,question_id,review_type,scheduled_date,priority,status,created_at) VALUES(?,?, 'same_or_similar',?,3,'pending','2026-01-01T00:00:00+00:00')", (self.student['id'], q['id'], date.today().isoformat()))
        queue = get_review_queue(self.student['id'], db_path=self.db)
        self.assertGreaterEqual(queue['due_count'], 1)
        self.assertIn(queue['items'][0]['review_label'], {'今日', '期限超過'})

    def test_beta_feedback_is_saved(self):
        feedback_id = save_beta_feedback(self.student['id'], 5, '使いやすさ', '毎日使えそうです', '/home', 'test-agent', self.db)
        saved = fetch_one('SELECT * FROM beta_feedback WHERE id=?', (feedback_id,), self.db)
        self.assertEqual(saved['user_id'], self.student['id'])
        self.assertEqual(saved['rating'], 5)

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

    def test_teacher_support_summary_contains_risk(self):
        rows = get_teacher_support_summary(self.teacher['id'], self.db)
        self.assertTrue(rows)
        self.assertIn(rows[0]['risk_level'], {'low', 'medium', 'high'})
        self.assertIn('weak_topics', rows[0])

    def test_admin_quality_summary_flags_questions(self):
        summary = get_admin_quality_summary(self.db)
        self.assertGreater(summary['counts']['ready'], 0)
        self.assertTrue(summary['items'])


class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from api import app
        seed_database()
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

    def test_study_summary_api(self):
        token = self._token()
        res = self.client.get('/api/study/summary', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res.status_code, 200)
        self.assertIn('accuracy', res.json())
        self.assertIn('due_reviews', res.json())

    def test_study_mastery_api(self):
        token = self._token()
        res = self.client.get('/api/study/mastery?limit=3', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res.status_code, 200)
        self.assertLessEqual(len(res.json()), 3)

    def test_daily_status_api(self):
        token = self._token()
        res = self.client.get('/api/study/daily-status', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res.status_code, 200)
        self.assertIn('streak_days', res.json())
        self.assertIn('next_action', res.json())

    def test_focus_and_strategy_api(self):
        token = self._token()
        res = self.client.get('/api/study/focus?mode=medical&count=5', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['mode'], 'medical')
        self.assertLessEqual(len(res.json()['items']), 5)
        res = self.client.post('/api/study/target-exam', headers={'Authorization': f'Bearer {token}'}, json={'target_exam_date': (date.today() + timedelta(days=100)).isoformat()})
        self.assertEqual(res.status_code, 200)
        self.assertIn('radar', res.json())
        res = self.client.post('/api/study/exam-events', headers={'Authorization': f'Bearer {token}'}, json={'event_type': 'mock', 'title': '公開模試', 'event_date': (date.today() + timedelta(days=20)).isoformat()})
        self.assertEqual(res.status_code, 200)
        res = self.client.post('/api/study/scores', headers={'Authorization': f'Bearer {token}'}, json={'score_type': 'mock', 'title': '公開模試', 'taken_at': date.today().isoformat(), 'total_score': 110, 'max_score': 180, 'subject_scores': {'医学概論・基礎医学': 62}})
        self.assertEqual(res.status_code, 200)

    def test_review_queue_api(self):
        token = self._token()
        res = self.client.get('/api/study/reviews', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res.status_code, 200)
        self.assertIn('items', res.json())

    def test_beta_feedback_api(self):
        token = self._token()
        res = self.client.post('/api/beta/feedback', headers={'Authorization': f'Bearer {token}'}, json={'rating': 4, 'category': '要望', 'message': '復習の導線を確認しました。', 'page_url': '/reviews'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['status'], 'saved')

    def test_teacher_support_api(self):
        token = self._token('teacher@ce108.local')
        res = self.client.get('/api/teacher/support', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(isinstance(res.json(), list))

    def test_admin_quality_api_forbidden_to_student(self):
        token = self._token()
        res = self.client.get('/api/admin/quality', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res.status_code, 403)


if __name__ == '__main__':
    unittest.main()
