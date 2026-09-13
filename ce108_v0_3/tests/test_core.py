import json
import tempfile
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from ce108.admin_service import approve_question, create_question, import_questions_csv
from ce108.database import connect, fetch_all, fetch_one
from ce108.security import hash_password
from ce108.seed import seed_database
from scripts.export_question_review_csv import export_review_csv
from scripts.export_first_paid_tester_pack import export_first_paid_pack
from ce108.services import (
    answer_diagnostic,
    authenticate_user,
    check_answer,
    create_beta_student,
    generate_daily_plan,
    get_focus_plan,
    get_first_paid_tester_pack,
    get_admin_quality_summary,
    get_answered_question_detail,
    get_beta_feedback_summary,
    get_beta_tester_activity,
    get_daily_status,
    get_frequent_topics,
    get_learning_history,
    get_diagnostic_state,
    get_mastery_report,
    get_note_question,
    get_question,
    get_review_queue,
    get_student_summary_for_teacher,
    get_teacher_support_summary,
    get_study_strategy,
    is_question_bookmarked,
    list_bookmarked_questions,
    public_question,
    create_student_note,
    extract_note_upload_text,
    generate_note_questions,
    answer_note_question,
    record_answer,
    add_exam_event,
    add_score_record,
    save_beta_feedback,
    set_question_bookmark,
    record_login_event,
    schedule_review,
    set_target_exam_date,
    set_user_password,
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

    def test_answer_returns_choice_feedback_and_related_questions(self):
        q = get_question(1, self.db)
        wrong = next(c['choice_code'] for c in q['choices'] if c['choice_code'] not in q['correct_codes'])
        result = record_answer(self.student['id'], q['id'], [wrong], None, '迷った', 40, 'test', db_path=self.db)
        self.assertIn('choice_feedback', result['question'])
        self.assertIn('learning_point', result['question'])
        self.assertIn('answer_statistics', result['question'])
        self.assertIn('visual_aid', result['question'])
        self.assertEqual(result['question']['answer_statistics']['total_answers'], 1)
        self.assertGreaterEqual(len(result['question']['visual_aid']['steps']), 3)
        self.assertIn(result['question']['visual_aid']['kind'], {'anatomy', 'flow', 'exchange', 'map', 'calculation'})
        selected_feedback = [c for c in result['question']['choice_feedback'] if c['selected']]
        self.assertTrue(selected_feedback)
        self.assertFalse(selected_feedback[0]['is_correct'])
        self.assertTrue(selected_feedback[0]['explanation'])
        self.assertIn('正答の', selected_feedback[0]['explanation'])
        self.assertIn('related_questions', result)

    def test_answered_question_detail_requires_history_and_returns_explanation(self):
        q = get_question(1, self.db)
        with self.assertRaises(ValueError):
            get_answered_question_detail(self.student['id'], q['id'], self.db)
        record_answer(self.student['id'], q['id'], q['correct_codes'], None, '迷った', 40, 'daily', db_path=self.db)
        detail = get_answered_question_detail(self.student['id'], q['id'], self.db)
        self.assertTrue(detail['is_correct'])
        self.assertIn('visual_aid', detail['question'])
        self.assertIn('choice_feedback', detail['question'])
        self.assertIn('explanation_standard', detail['question'])
        public_correct = [c['choice_code'] for c in detail['question']['choice_feedback'] if c['is_correct']]
        self.assertEqual(detail['latest_answer']['selected_codes'], public_correct)

    def test_learning_history_contains_recent_answers(self):
        q = get_question(1, self.db)
        record_answer(self.student['id'], q['id'], q['correct_codes'], None, 'たぶん分かる', 30, 'daily', db_path=self.db)
        history = get_learning_history(self.student['id'], 10, self.db)
        self.assertEqual(history['total'], 1)
        self.assertEqual(history['items'][0]['question_id'], q['id'])
        self.assertTrue(history['items'][0]['is_correct'])
        self.assertEqual(history['items'][0]['selected_codes'], q['correct_codes'])

    def test_numeric_tolerance(self):
        q = next(get_question(r['id'], self.db) for r in fetch_all("SELECT id FROM questions WHERE question_type='numeric'", (), self.db))
        self.assertTrue(check_answer(q, [], q['numeric_answer'] + (q['numeric_tolerance'] / 2)))

    def test_calculation_question_returns_formula_visual_aid(self):
        row = fetch_one("SELECT id FROM questions WHERE question_text LIKE '%圧力%' AND question_type='numeric' ORDER BY id LIMIT 1", (), self.db)
        q = get_question(row['id'], self.db)
        result = record_answer(self.student['id'], q['id'], [], q['numeric_answer'], 'たぶん分かる', 30, 'test', db_path=self.db)
        self.assertEqual(result['question']['visual_aid']['kind'], 'calculation')
        self.assertIn('formula', result['question']['visual_aid'])
        self.assertIn('P = F / A', result['question']['visual_aid']['formula']['formula'])

    def test_visual_aid_variants_cover_exam_like_topics(self):
        cases = [
            ("SELECT id FROM questions WHERE question_text LIKE '%P波%' ORDER BY id LIMIT 1", 'signal'),
            ("SELECT id FROM questions WHERE question_text LIKE '%アシドーシス%' ORDER BY id LIMIT 1", 'acidbase'),
            ("SELECT id FROM questions WHERE question_text LIKE '%ショック%' ORDER BY id LIMIT 1", 'circulation'),
            ("SELECT id FROM questions WHERE question_text LIKE '%電圧計%' ORDER BY id LIMIT 1", 'circuit'),
            ("SELECT id FROM questions WHERE question_text LIKE '%透析%' ORDER BY id LIMIT 1", 'dialysis'),
            ("SELECT id FROM questions WHERE question_text LIKE '%PEEP%' ORDER BY id LIMIT 1", 'ventilation'),
        ]
        for sql, kind in cases:
            with self.subTest(kind=kind):
                row = fetch_one(sql, (), self.db)
                q = get_question(row['id'], self.db)
                result = record_answer(self.student['id'], q['id'], q.get('correct_codes') or [], q.get('numeric_answer'), 'たぶん分かる', 30, 'test', db_path=self.db)
                self.assertEqual(result['question']['visual_aid']['kind'], kind)

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

    def test_mobile_daily_plan_limits_existing_plan_to_five(self):
        plan = generate_daily_plan(self.student['id'], count=7, db_path=self.db)
        self.assertEqual(len(plan['items']), 7)
        limited = generate_daily_plan(self.student['id'], count=5, db_path=self.db)
        self.assertEqual(len(limited['items']), 5)
        for item in limited['items']:
            q = get_question(item['question_id'], self.db)
            record_answer(self.student['id'], q['id'], q['correct_codes'], q.get('numeric_answer'), 'たぶん分かる', 20, 'daily', db_path=self.db)
        status = get_daily_status(self.student['id'], count=5, db_path=self.db)
        self.assertEqual(status['completed_count'], 5)
        self.assertEqual(status['total_count'], 5)
        self.assertEqual(status['status'], 'completed')

    def test_seed_contains_expanded_original_questions_with_choice_explanations(self):
        total = fetch_one('SELECT COUNT(*) total FROM questions', (), self.db)['total']
        empty = fetch_one("SELECT COUNT(*) total FROM question_choices WHERE TRIM(COALESCE(explanation,''))=''", (), self.db)['total']
        self.assertGreaterEqual(total, 300)
        self.assertEqual(empty, 0)

    def test_question_review_csv_export(self):
        output = Path(self.t.name) / 'question_review_export.csv'
        export_review_csv(output, self.db)
        text = output.read_text(encoding='utf-8-sig')
        self.assertIn('medical_engineering_review', text)
        self.assertIn('国試風オリジナル', text)

    def test_seed_adds_missing_questions_to_existing_database(self):
        text = '血圧を規定する要素として最も基本的な組合せはどれか。'
        with connect(self.db) as conn:
            qid = conn.execute('SELECT id FROM questions WHERE question_text=?', (text,)).fetchone()['id']
            conn.execute('DELETE FROM questions WHERE id=?', (qid,))
        seed_database(self.db)
        restored = fetch_one('SELECT id FROM questions WHERE question_text=?', (text,), self.db)
        self.assertIsNotNone(restored)

    def test_note_ai_generates_private_questions_and_answers(self):
        note_id = create_student_note(self.student['id'], '呼吸メモ', '人工呼吸管理ではPEEPにより呼気終末の肺胞虚脱を抑える。PaCO2上昇は肺胞換気不足を示唆するため注意が必要である。', db_path=self.db)
        generated = generate_note_questions(self.student['id'], note_id, 2, self.db)
        self.assertEqual(generated['generated_count'], 2)
        question = get_note_question(self.student['id'], generated['questions'][0]['id'], self.db)
        text = json.dumps(question, ensure_ascii=False)
        self.assertNotIn('correct_code', text)
        self.assertNotIn('choice_feedback', text)
        self.assertNotIn('visual_aid', text)
        result = answer_note_question(self.student['id'], question['id'], '1', 'たぶん分かる', 20, self.db)
        self.assertTrue(result['is_correct'])
        self.assertIn('choice_feedback', result['question'])
        self.assertIn('learning_point', result['question'])
        self.assertIn('visual_aid', result['question'])
        self.assertEqual(result['question']['answer_statistics']['total_answers'], 1)
        self.assertGreaterEqual(len(result['question']['visual_aid']['steps']), 3)
        self.assertIn('本文の中心', result['question']['choice_feedback'][0]['explanation'])

    def test_note_upload_text_extraction(self):
        result = extract_note_upload_text(self.student['id'], 'lecture.md', 'text/markdown', '人工呼吸管理ではPEEPにより肺胞虚脱を抑える。PaCO2上昇は肺胞換気不足を示唆する。'.encode('utf-8'), self.db)
        self.assertEqual(result['source_type'], 'uploaded_text')
        self.assertIn('人工呼吸管理', result['text'])

    def test_note_upload_short_text_extracts_with_warning(self):
        result = extract_note_upload_text(self.student['id'], 'memo.txt', 'application/octet-stream', '短いメモ'.encode('utf-8'), self.db)
        self.assertEqual(result['source_type'], 'uploaded_text')
        self.assertEqual(result['text'], '短いメモ')
        self.assertIn('20文字以上', result['warning'])

    def test_note_upload_image_requires_ocr_provider(self):
        with self.assertRaises(ValueError) as ctx:
            extract_note_upload_text(self.student['id'], 'note.png', 'image/png', b'\x89PNG\r\n', self.db)
        self.assertIn('写真・PDF読み取り', str(ctx.exception))

    def test_focus_plan_modes(self):
        medical = get_focus_plan(self.student['id'], 'medical', 5, self.db)
        engineering = get_focus_plan(self.student['id'], 'engineering', 5, self.db)
        self.assertEqual(medical['mode'], 'medical')
        self.assertTrue(all(item['subject_name'] in {'医学概論・基礎医学', '臨床医学総論'} for item in medical['items']))
        self.assertEqual(engineering['mode'], 'engineering')
        self.assertTrue(engineering['items'])

    def test_bookmark_lifecycle_and_plan(self):
        q = get_question(1, self.db)
        self.assertFalse(is_question_bookmarked(self.student['id'], q['id'], self.db))
        saved = set_question_bookmark(self.student['id'], q['id'], True, db_path=self.db)
        self.assertTrue(saved['bookmarked'])
        self.assertTrue(is_question_bookmarked(self.student['id'], q['id'], self.db))
        bookmarks = list_bookmarked_questions(self.student['id'], 10, self.db)
        self.assertEqual(bookmarks['total'], 1)
        plan = get_focus_plan(self.student['id'], 'bookmarked', 5, self.db)
        self.assertEqual(plan['mode'], 'bookmarked')
        self.assertEqual(plan['items'][0]['question_id'], q['id'])
        removed = set_question_bookmark(self.student['id'], q['id'], False, db_path=self.db)
        self.assertFalse(removed['bookmarked'])

    def test_wrong_and_frequent_focus_plans(self):
        q = get_question(1, self.db)
        wrong = next(c['choice_code'] for c in q['choices'] if c['choice_code'] not in q['correct_codes'])
        record_answer(self.student['id'], q['id'], [wrong], None, '迷った', 30, 'daily', db_path=self.db)
        wrong_plan = get_focus_plan(self.student['id'], 'wrong', 5, self.db)
        self.assertEqual(wrong_plan['mode'], 'wrong')
        self.assertTrue(any(item['question_id'] == q['id'] for item in wrong_plan['items']))
        frequent = get_focus_plan(self.student['id'], 'frequent', 5, self.db)
        topics = get_frequent_topics(self.student['id'], 5, self.db)
        self.assertEqual(frequent['mode'], 'frequent')
        self.assertTrue(frequent['items'])
        self.assertTrue(topics['items'])
        self.assertIn('recommended_reason', topics['items'][0])

    def test_first_paid_tester_pack_has_30_questions(self):
        pack = get_first_paid_tester_pack(self.student['id'], self.db)
        self.assertEqual(pack['name'], 'First Paid Tester Pack')
        self.assertEqual(pack['available_questions'], 30)
        self.assertEqual(len(pack['items']), 30)
        subjects = {item['subject_name'] for item in pack['items']}
        self.assertIn('医学概論・基礎医学', subjects)
        self.assertIn('医用電気電子工学', subjects)

    def test_public_question_shuffles_choices_without_leaking_correctness(self):
        qid = fetch_one("SELECT id FROM questions WHERE question_text=?", ('血圧を規定する要素として最も基本的な組合せはどれか。',), self.db)['id']
        q = get_question(qid, self.db)
        public = public_question(q, self.student['id'])
        self.assertEqual([c['choice_code'] for c in public['choices']], ['1', '2', '3', '4', '5'])
        self.assertNotEqual([c['choice_text'] for c in public['choices']], [c['choice_text'] for c in q['choices']])
        self.assertNotIn('correct_codes', public)
        self.assertNotIn('numeric_answer', public)
        self.assertTrue(all('is_correct' not in c and 'explanation' not in c for c in public['choices']))
        correct_text = next(c['choice_text'] for c in q['choices'] if c['choice_code'] in q['correct_codes'])
        public_correct_code = next(c['choice_code'] for c in public['choices'] if c['choice_text'] == correct_text)
        result = record_answer(self.student['id'], q['id'], [public_correct_code], None, '確実に分かる', 20, 'test', db_path=self.db, public_choice_codes=True)
        self.assertTrue(result['is_correct'])
        self.assertEqual(result['question']['correct_codes'], [public_correct_code])
        self.assertTrue(any(c['choice_code'] == public_correct_code and c['is_correct'] for c in result['question']['choice_feedback']))

    def test_first_paid_pack_distractors_are_plausible(self):
        qid = fetch_one("SELECT id FROM questions WHERE question_text=?", ('ショックで共通して問題となる病態として最も適切なのはどれか。',), self.db)['id']
        q = get_question(qid, self.db)
        choices = {c['choice_text'] for c in q['choices']}
        self.assertIn('組織灌流の不足', choices)
        self.assertIn('心拍出量の増加', choices)
        self.assertIn('末梢血管抵抗の上昇のみ', choices)
        self.assertNotIn('視力の改善', choices)
        self.assertNotIn('骨形成の亢進', choices)

    def test_first_paid_tester_pack_csv_export(self):
        output = Path(self.t.name) / 'first_paid_tester_pack.csv'
        export_first_paid_pack(output, self.db)
        lines = output.read_text(encoding='utf-8-sig').splitlines()
        self.assertEqual(len(lines), 31)
        self.assertIn('First Paid Tester Pack', lines[1])

    def test_exam_strategy_records_scores_and_events(self):
        set_target_exam_date(self.student['id'], (date.today() + timedelta(days=120)).isoformat(), self.db)
        add_exam_event(self.student['id'], 'mock', '第1回模試', (date.today() + timedelta(days=30)).isoformat(), db_path=self.db)
        add_score_record(self.student['id'], 'mock', '第1回模試', date.today().isoformat(), 120, 180, {'医学概論・基礎医学': 70, '臨床医学総論': 65}, db_path=self.db)
        strategy = get_study_strategy(self.student['id'], self.db)
        self.assertEqual(strategy['phase'], 'normal')
        self.assertEqual(strategy['recommended_mode'], 'medical')
        self.assertTrue(strategy['events'])
        self.assertTrue(strategy['radar'])
        self.assertEqual(strategy['target_score_rate'], 80.0)
        self.assertIn('readiness_label', strategy)
        self.assertTrue(strategy['next_actions'])

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

    def test_beta_feedback_summary_prioritizes_urgent_items(self):
        save_beta_feedback(self.student['id'], 2, '不具合', 'ログインできないです', '/login', 'test-agent', self.db)
        save_beta_feedback(self.student['id'], 5, '使いやすさ', '毎日続けられそうです', '/home', 'test-agent', self.db)
        summary = get_beta_feedback_summary(self.db)
        self.assertEqual(summary['total'], 2)
        self.assertEqual(summary['category_counts']['不具合'], 1)
        self.assertEqual(summary['priority_counts']['高'], 1)
        self.assertEqual(summary['items'][0]['priority'], '低')

    def test_beta_tester_activity_tracks_login_answers_and_feedback(self):
        tester = create_beta_student('activity@example.com', 'tester1234', '活動確認', db_path=self.db)
        record_login_event(tester, self.db)
        q = get_question(1, self.db)
        record_answer(tester['id'], q['id'], q['correct_codes'], None, 'たぶん分かる', 30, 'daily', db_path=self.db)
        save_beta_feedback(tester['id'], 4, '要望', '続け方を確認しました', '/home', 'test-agent', self.db)
        rows = get_beta_tester_activity(db_path=self.db)
        row = next(r for r in rows if r['email'] == 'activity@example.com')
        self.assertEqual(row['status_label'], 'フィードバック済み')
        self.assertEqual(row['login_count'], 1)
        self.assertEqual(row['answer_count'], 1)
        self.assertEqual(row['feedback_count'], 1)

    def test_beta_tester_activity_shows_answered_without_login_event(self):
        tester = create_beta_student('answered-before-tracking@example.com', 'tester1234', '履歴前回答', db_path=self.db)
        q = get_question(1, self.db)
        record_answer(tester['id'], q['id'], q['correct_codes'], None, 'たぶん分かる', 30, 'daily', db_path=self.db)
        rows = get_beta_tester_activity(db_path=self.db)
        row = next(r for r in rows if r['email'] == 'answered-before-tracking@example.com')
        self.assertEqual(row['status_label'], '回答済み')

    def test_create_beta_student_can_login_and_is_assigned(self):
        user = create_beta_student('beta1@example.com', 'tester1234', '外部β1', db_path=self.db)
        logged_in = authenticate_user('beta1@example.com', 'tester1234', self.db)
        membership = fetch_one('SELECT * FROM organization_memberships WHERE user_id=?', (user['id'],), self.db)
        self.assertEqual(user['role'], 'student')
        self.assertEqual(logged_in['id'], user['id'])
        self.assertIsNotNone(membership)

    def test_create_beta_student_rejects_duplicate_email(self):
        create_beta_student('beta2@example.com', 'tester1234', '外部β2', db_path=self.db)
        with self.assertRaises(ValueError):
            create_beta_student('BETA2@example.com', 'tester1234', '外部β2 duplicate', db_path=self.db)

    def test_set_user_password_rotates_demo_admin_password(self):
        set_user_password('admin@ce108.local', 'new-admin-pass', self.db)
        self.assertIsNone(authenticate_user('admin@ce108.local', 'demo1234', self.db))
        self.assertEqual(authenticate_user('admin@ce108.local', 'new-admin-pass', self.db)['role'], 'admin')

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

    def test_admin_question_choice_explanations_are_saved(self):
        qid = create_question(self.admin['id'], 'single', '選択肢解説つき問題', 'MED-ANAT', ['A', 'B'], ['1'], None, None, '短', '標準', '詳細', 3, 2, 'internal_sample', 'published', self.db, ['Aが正しい理由', 'Bが誤りの理由'])
        q = get_question(qid, self.db)
        self.assertEqual(q['choices'][0]['explanation'], 'Aが正しい理由')
        self.assertEqual(q['choices'][1]['explanation'], 'Bが誤りの理由')

    def test_csv_choice_explanations_are_saved(self):
        content = '\n'.join([
            'question_type,question_text,choice_1,choice_2,choice_3,choice_4,choice_5,choice_1_explanation,choice_2_explanation,choice_3_explanation,choice_4_explanation,choice_5_explanation,correct_codes,numeric_answer,numeric_tolerance,unit,topic_code,explanation_short,explanation_standard,explanation_detailed,difficulty,importance,frequency_score,source_type,source_name,source_url,copyright_holder,permission_status,status',
            'single,CSV選択肢解説問題,A,B,,,,Aが正しい理由,Bが誤りの理由,,,,1,,0.01,,MED-ANAT,短,標準,詳細,2,3,1.0,original,CE108,,CE108,internal_sample,published',
        ]).encode('utf-8-sig')
        result = import_questions_csv(content, self.admin['id'], self.db)
        self.assertEqual(result['inserted'], 1)
        qid = fetch_one("SELECT id FROM questions WHERE question_text='CSV選択肢解説問題'", (), self.db)['id']
        q = get_question(qid, self.db)
        self.assertEqual(q['choices'][1]['explanation'], 'Bが誤りの理由')

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
        self.assertNotIn('choice_feedback', text)

    def test_study_summary_api(self):
        token = self._token()
        res = self.client.get('/api/study/summary', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res.status_code, 200)
        self.assertIn('accuracy', res.json())
        self.assertIn('due_reviews', res.json())
        self.assertGreaterEqual(res.json()['question_bank_total'], 300)
        self.assertIn('weekly_answers', res.json())

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

    def test_bookmark_wrong_and_frequent_api(self):
        token = self._token()
        headers = {'Authorization': f'Bearer {token}'}
        marked = self.client.post('/api/questions/2/bookmark', headers=headers, json={'bookmarked': True})
        self.assertEqual(marked.status_code, 200, marked.text)
        self.assertTrue(marked.json()['bookmarked'])
        bookmarks = self.client.get('/api/study/bookmarks', headers=headers)
        self.assertEqual(bookmarks.status_code, 200, bookmarks.text)
        self.assertGreaterEqual(bookmarks.json()['total'], 1)
        bookmarked_plan = self.client.get('/api/study/focus?mode=bookmarked&count=5', headers=headers)
        self.assertEqual(bookmarked_plan.status_code, 200, bookmarked_plan.text)
        self.assertEqual(bookmarked_plan.json()['mode'], 'bookmarked')
        self.client.post('/api/questions/2/answer', headers=headers, json={'selected_codes': ['999'], 'numeric_answer': None, 'confidence': '迷った', 'response_time_seconds': 20, 'answer_mode': 'daily'})
        wrong_plan = self.client.get('/api/study/focus?mode=wrong&count=5', headers=headers)
        self.assertEqual(wrong_plan.status_code, 200, wrong_plan.text)
        self.assertEqual(wrong_plan.json()['mode'], 'wrong')
        frequent = self.client.get('/api/study/frequent-topics', headers=headers)
        self.assertEqual(frequent.status_code, 200, frequent.text)
        self.assertTrue(frequent.json()['items'])
        pack = self.client.get('/api/study/first-paid-pack', headers=headers)
        self.assertEqual(pack.status_code, 200, pack.text)
        self.assertEqual(pack.json()['available_questions'], 30)
        first_paid = self.client.get('/api/study/focus?mode=first_paid&count=30', headers=headers)
        self.assertEqual(first_paid.status_code, 200, first_paid.text)
        self.assertEqual(len(first_paid.json()['items']), 30)
        unmarked = self.client.post('/api/questions/2/bookmark', headers=headers, json={'bookmarked': False})
        self.assertFalse(unmarked.json()['bookmarked'])

    def test_review_queue_api(self):
        token = self._token()
        res = self.client.get('/api/study/reviews', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res.status_code, 200)
        self.assertIn('items', res.json())

    def test_history_and_answered_detail_api(self):
        token = self._token()
        question = self.client.get('/api/questions/1', headers={'Authorization': f'Bearer {token}'}).json()
        res = self.client.post('/api/questions/1/answer', headers={'Authorization': f'Bearer {token}'}, json={'selected_codes': ['1'], 'numeric_answer': None, 'confidence': 'たぶん分かる', 'response_time_seconds': 20, 'answer_mode': 'daily'})
        self.assertEqual(res.status_code, 200, res.text)
        history = self.client.get('/api/study/history', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(history.status_code, 200)
        self.assertGreaterEqual(history.json()['total'], 1)
        detail = self.client.get('/api/study/answered-questions/1', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(detail.status_code, 200, detail.text)
        body = detail.json()
        self.assertIn('visual_aid', body['question'])
        self.assertIn('choice_feedback', body['question'])
        self.assertNotIn('explanation_standard', json.dumps(question, ensure_ascii=False))

    def test_beta_feedback_api(self):
        token = self._token()
        res = self.client.post('/api/beta/feedback', headers={'Authorization': f'Bearer {token}'}, json={'rating': 4, 'category': '要望', 'message': '復習の導線を確認しました。', 'page_url': '/reviews'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['status'], 'saved')

    def test_note_ai_api_flow(self):
        token = self._token()
        res = self.client.post('/api/notes', headers={'Authorization': f'Bearer {token}'}, json={'title': '透析メモ', 'content': '透析では拡散により小分子溶質を除去する。除水量を過大に設定すると循環血液量が低下し血圧低下に注意が必要である。'})
        self.assertEqual(res.status_code, 200, res.text)
        note_id = res.json()['note_id']
        res = self.client.post(f'/api/notes/{note_id}/generate', headers={'Authorization': f'Bearer {token}'}, json={'count': 2})
        self.assertEqual(res.status_code, 200, res.text)
        q = res.json()['questions'][0]
        self.assertNotIn('correct_code', json.dumps(q, ensure_ascii=False))
        res = self.client.post(f"/api/note-questions/{q['id']}/answer", headers={'Authorization': f'Bearer {token}'}, json={'selected_code': '1', 'confidence': 'たぶん分かる', 'response_time_seconds': 10})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertTrue(res.json()['is_correct'])
        body = res.json()['question']
        self.assertIn('explanation', body)
        self.assertIn('choice_feedback', body)
        self.assertIn('visual_aid', body)
        self.assertGreaterEqual(len(body['visual_aid']['steps']), 3)

    def test_note_extract_api_reads_text_file(self):
        token = self._token()
        res = self.client.post('/api/notes/extract', headers={'Authorization': f'Bearer {token}'}, files={'file': ('memo.txt', '血液透析では拡散と限外濾過を理解する。除水設定は循環動態に注意する。'.encode('utf-8'), 'text/plain')})
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(body['source_type'], 'uploaded_text')
        self.assertIn('血液透析', body['text'])

    def test_note_extract_api_reads_octet_stream_text_file(self):
        token = self._token()
        res = self.client.post('/api/notes/extract', headers={'Authorization': f'Bearer {token}'}, files={'file': ('memo.txt', '短いメモ'.encode('utf-8'), 'application/octet-stream')})
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(body['source_type'], 'uploaded_text')
        self.assertIn('20文字以上', body['warning'])

    def test_note_extract_api_rejects_image_without_ocr_provider(self):
        token = self._token()
        res = self.client.post('/api/notes/extract', headers={'Authorization': f'Bearer {token}'}, files={'file': ('memo.png', b'\x89PNG\r\n', 'image/png')})
        self.assertEqual(res.status_code, 400)
        self.assertIn('写真・PDF読み取り', res.text)

    def test_teacher_support_api(self):
        token = self._token('teacher@ce108.local')
        res = self.client.get('/api/teacher/support', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(isinstance(res.json(), list))

    def test_admin_quality_api_forbidden_to_student(self):
        token = self._token()
        res = self.client.get('/api/admin/quality', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res.status_code, 403)

    def test_admin_beta_feedback_and_activity_api(self):
        admin_token = self._token('admin@ce108.local')
        student_token = self._token()
        res = self.client.post('/api/beta/feedback', headers={'Authorization': f'Bearer {student_token}'}, json={'rating': 2, 'category': '不具合', 'message': 'Failed to fetch が出ました', 'page_url': '/login'})
        self.assertEqual(res.status_code, 200)
        summary = self.client.get('/api/admin/beta-feedback/summary', headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(summary.status_code, 200)
        self.assertGreaterEqual(summary.json()['priority_counts']['高'], 1)
        activity = self.client.get('/api/admin/tester-students/activity', headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(activity.status_code, 200)
        self.assertTrue(isinstance(activity.json(), list))

    def test_student_cannot_read_admin_beta_feedback_api(self):
        token = self._token()
        res = self.client.get('/api/admin/beta-feedback/summary', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res.status_code, 403)

    def test_admin_can_create_tester_student_api(self):
        token = self._token('admin@ce108.local')
        email = f"api-beta-{uuid.uuid4().hex}@example.com"
        res = self.client.post('/api/admin/tester-students', headers={'Authorization': f'Bearer {token}'}, json={'email': email, 'password': 'tester1234', 'display_name': 'API外部β'})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()['role'], 'student')
        login_res = self.client.post('/api/auth/login', data={'username': email, 'password': 'tester1234'})
        self.assertEqual(login_res.status_code, 200, login_res.text)

    def test_student_cannot_create_tester_student_api(self):
        token = self._token()
        res = self.client.post('/api/admin/tester-students', headers={'Authorization': f'Bearer {token}'}, json={'email': 'blocked-beta@example.com', 'password': 'tester1234', 'display_name': 'Blocked'})
        self.assertEqual(res.status_code, 403)


if __name__ == '__main__':
    unittest.main()
