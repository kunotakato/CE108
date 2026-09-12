from __future__ import annotations
from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from ce108.admin_service import approve_question, create_question, unpublish_question
from ce108.config import CORS_ORIGINS, LINE_CHANNEL_SECRET
from ce108.database import execute, utc_now
from ce108.security import create_access_token, decode_access_token, verify_line_signature
from ce108.seed import seed_database
from ce108.services import (
    answer_note_question,
    answer_diagnostic,
    assignment_results_csv,
    authenticate_user,
    create_beta_student,
    create_student_note,
    create_assignment,
    diagnostic_result,
    extract_note_upload_text,
    generate_daily_plan,
    generate_note_questions,
    get_focus_plan,
    get_diagnostic_state,
    get_admin_quality_summary,
    get_answered_question_detail,
    get_beta_feedback_summary,
    get_beta_tester_activity,
    get_daily_status,
    get_frequent_topics,
    get_learning_history,
    get_question,
    get_learning_summary,
    get_mastery_report,
    get_note_question,
    get_review_queue,
    get_student_summary_for_teacher,
    get_teacher_support_summary,
    get_user,
    get_study_strategy,
    list_assignment_results,
    list_note_questions,
    list_bookmarked_questions,
    list_questions,
    list_students_for_teacher,
    list_student_notes,
    public_question,
    record_answer,
    record_login_event,
    add_exam_event,
    add_score_record,
    save_beta_feedback,
    set_question_bookmark,
    set_target_exam_date,
    start_diagnostic,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_database()
    yield

app = FastAPI(title='CE108 API', version='0.4.4', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
oauth = OAuth2PasswordBearer(tokenUrl='/api/auth/login')

class AnswerRequest(BaseModel):
    selected_codes: list[str] = Field(default_factory=list)
    numeric_answer: float | None = None
    confidence: str
    response_time_seconds: int = Field(default=0, ge=0)
    answer_mode: str = 'api'

class DiagnosticAnswerRequest(AnswerRequest):
    question_id: int

class AssignmentRequest(BaseModel):
    title: str
    description: str = ''
    question_ids: list[int]
    target_user_ids: list[int]
    due_at: str

class AdminQuestionRequest(BaseModel):
    question_type: str
    question_text: str
    topic_code: str
    choices: list[str] = Field(default_factory=list)
    choice_explanations: list[str] = Field(default_factory=list)
    correct_codes: list[str] = Field(default_factory=list)
    numeric_answer: float | None = None
    unit: str | None = None
    explanation_short: str
    explanation_standard: str
    explanation_detailed: str
    importance: int = Field(ge=1, le=5)
    difficulty: int = Field(ge=1, le=5)
    permission_status: str = 'internal_sample'
    status: str = 'draft'

class BetaFeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    category: str
    message: str = Field(min_length=3, max_length=2000)
    page_url: str | None = None
    user_agent: str | None = None

class TargetExamDateRequest(BaseModel):
    target_exam_date: str

class ExamEventRequest(BaseModel):
    event_type: str
    title: str
    event_date: str
    memo: str = ''

class ScoreRecordRequest(BaseModel):
    score_type: str
    title: str
    taken_at: str
    total_score: float = Field(ge=0)
    max_score: float = Field(gt=0)
    morning_score: float | None = None
    afternoon_score: float | None = None
    subject_scores: dict[str, float] = Field(default_factory=dict)
    memo: str = ''

class NoteRequest(BaseModel):
    title: str = '無題ノート'
    content: str = Field(min_length=20, max_length=20000)
    source_type: str = 'manual_note'

class NoteGenerateRequest(BaseModel):
    count: int = Field(default=5, ge=1, le=10)

class NoteAnswerRequest(BaseModel):
    selected_code: str
    confidence: str = 'たぶん分かる'
    response_time_seconds: int = Field(default=0, ge=0)

class BetaStudentRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    display_name: str
    grade: str = '4年'
    school_name: str = 'CE108外部β'
    target_exam_year: int | None = None

class BookmarkRequest(BaseModel):
    bookmarked: bool = True
    note: str = ''

def current_user(token: Annotated[str, Depends(oauth)]):
    try:
        payload = decode_access_token(token)
        user = get_user(int(payload['sub']))
        if not user:
            raise ValueError
        return user
    except Exception as exc:
        raise HTTPException(401, '無効な認証です。') from exc

def require_role(*roles: str):
    def _dep(user=Depends(current_user)):
        if user['role'] not in roles:
            raise HTTPException(403, 'この操作の権限がありません。')
        return user
    return _dep

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return Response(content=str(exc), status_code=400, media_type='text/plain; charset=utf-8')

@app.exception_handler(PermissionError)
async def permission_error_handler(request: Request, exc: PermissionError):
    return Response(content=str(exc), status_code=403, media_type='text/plain; charset=utf-8')

@app.get('/health')
def health():
    return {'status': 'ok', 'version': '0.4.4'}

@app.post('/api/auth/login')
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = authenticate_user(form.username, form.password)
    if not user:
        raise HTTPException(401, 'メールアドレスまたはパスワードが違います。')
    record_login_event(user)
    return {'access_token': create_access_token(user['id'], user['role']), 'token_type': 'bearer', 'user': get_user(user['id'])}

@app.get('/api/users/me')
def me(user=Depends(current_user)):
    return user

@app.get('/api/questions')
def questions(limit: int = 100, user=Depends(current_user)):
    return list_questions(limit=min(limit, 500))

@app.get('/api/questions/{qid}')
def question(qid: int, user=Depends(current_user)):
    q = get_question(qid)
    if not q or (q['status'] != 'published' and user['role'] != 'admin'):
        raise HTTPException(404, '問題がありません。')
    return public_question(q)

@app.post('/api/questions/{qid}/answer')
def answer(qid: int, req: AnswerRequest, user=Depends(require_role('student'))):
    return record_answer(user['id'], qid, req.selected_codes, req.numeric_answer, req.confidence, req.response_time_seconds, req.answer_mode)

@app.get('/api/study/today')
def today(count: int = 5, user=Depends(require_role('student'))):
    return generate_daily_plan(user['id'], count=max(1, min(count, 20)))

@app.get('/api/study/focus')
def study_focus(mode: str = 'balanced', count: int = 5, user=Depends(require_role('student'))):
    return get_focus_plan(user['id'], mode=mode, count=count)

@app.get('/api/study/frequent-topics')
def study_frequent_topics(limit: int = 10, user=Depends(require_role('student'))):
    return get_frequent_topics(user['id'], limit=limit)

@app.get('/api/study/bookmarks')
def study_bookmarks(limit: int = 50, user=Depends(require_role('student'))):
    return list_bookmarked_questions(user['id'], limit=limit)

@app.post('/api/questions/{qid}/bookmark')
def question_bookmark(qid: int, req: BookmarkRequest, user=Depends(require_role('student'))):
    return set_question_bookmark(user['id'], qid, req.bookmarked, req.note)

@app.get('/api/study/daily-status')
def daily_status(count: int = 5, user=Depends(require_role('student'))):
    return get_daily_status(user['id'], count=max(1, min(count, 20)))

@app.get('/api/study/reviews')
def review_queue(limit: int = 20, user=Depends(require_role('student'))):
    return get_review_queue(user['id'], limit=limit)

@app.get('/api/study/history')
def study_history(limit: int = 50, user=Depends(require_role('student'))):
    return get_learning_history(user['id'], limit=limit)

@app.get('/api/study/answered-questions/{qid}')
def answered_question(qid: int, user=Depends(require_role('student'))):
    return get_answered_question_detail(user['id'], qid)

@app.get('/api/study/summary')
def study_summary(user=Depends(require_role('student'))):
    return get_learning_summary(user['id'])

@app.get('/api/study/mastery')
def study_mastery(limit: int = 3, user=Depends(require_role('student'))):
    rows = get_mastery_report(user['id'])
    return rows[:max(1, min(limit, 10))]

@app.get('/api/study/strategy')
def study_strategy(user=Depends(require_role('student'))):
    return get_study_strategy(user['id'])

@app.post('/api/study/target-exam')
def study_target_exam(req: TargetExamDateRequest, user=Depends(require_role('student'))):
    try:
        return set_target_exam_date(user['id'], req.target_exam_date)
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post('/api/study/exam-events')
def study_exam_event(req: ExamEventRequest, user=Depends(require_role('student'))):
    try:
        return add_exam_event(user['id'], req.event_type, req.title, req.event_date, req.memo)
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post('/api/study/scores')
def study_score(req: ScoreRecordRequest, user=Depends(require_role('student'))):
    try:
        return add_score_record(user['id'], req.score_type, req.title, req.taken_at, req.total_score, req.max_score, req.subject_scores, req.morning_score, req.afternoon_score, req.memo)
    except Exception as e:
        raise HTTPException(400, str(e))

@app.get('/api/notes')
def notes(user=Depends(require_role('student'))):
    return list_student_notes(user['id'])

@app.post('/api/notes')
def note_create(req: NoteRequest, user=Depends(require_role('student'))):
    try:
        return {'note_id': create_student_note(user['id'], req.title, req.content, req.source_type)}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post('/api/notes/extract')
async def note_extract(file: UploadFile = File(...), user=Depends(require_role('student'))):
    try:
        data = await file.read()
        return extract_note_upload_text(user['id'], file.filename or 'upload', file.content_type or '', data)
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post('/api/notes/{note_id}/generate')
def note_generate(note_id: int, req: NoteGenerateRequest, user=Depends(require_role('student'))):
    try:
        return generate_note_questions(user['id'], note_id, req.count)
    except Exception as e:
        raise HTTPException(400, str(e))

@app.get('/api/notes/{note_id}/questions')
def note_questions(note_id: int, user=Depends(require_role('student'))):
    try:
        return list_note_questions(user['id'], note_id)
    except Exception as e:
        raise HTTPException(404, str(e))

@app.get('/api/note-questions/{question_id}')
def note_question(question_id: int, user=Depends(require_role('student'))):
    try:
        return get_note_question(user['id'], question_id)
    except Exception as e:
        raise HTTPException(404, str(e))

@app.post('/api/note-questions/{question_id}/answer')
def note_answer(question_id: int, req: NoteAnswerRequest, user=Depends(require_role('student'))):
    try:
        return answer_note_question(user['id'], question_id, req.selected_code, req.confidence, req.response_time_seconds)
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post('/api/beta/feedback')
def beta_feedback(req: BetaFeedbackRequest, user=Depends(require_role('student'))):
    feedback_id = save_beta_feedback(user['id'], req.rating, req.category, req.message, req.page_url, req.user_agent)
    return {'feedback_id': feedback_id, 'status': 'saved'}

@app.post('/api/diagnostics/start')
def diag_start(user=Depends(require_role('student'))):
    return start_diagnostic(user['id'])

@app.get('/api/diagnostics/{sid}')
def diag_state(sid: int, user=Depends(require_role('student'))):
    return get_diagnostic_state(user['id'], sid)

@app.post('/api/diagnostics/{sid}/answer')
def diag_answer(sid: int, req: DiagnosticAnswerRequest, user=Depends(require_role('student'))):
    return answer_diagnostic(user['id'], sid, req.question_id, req.selected_codes, req.numeric_answer, req.confidence, req.response_time_seconds)

@app.get('/api/diagnostics/{sid}/result')
def diag_result(sid: int, user=Depends(require_role('student'))):
    return diagnostic_result(user['id'], sid)

@app.get('/api/teacher/students')
def teacher_students(user=Depends(require_role('teacher'))):
    return list_students_for_teacher(user['id'])

@app.get('/api/teacher/support')
def teacher_support(user=Depends(require_role('teacher'))):
    return get_teacher_support_summary(user['id'])

@app.get('/api/teacher/students/{student_id}/summary')
def teacher_student_summary(student_id: int, user=Depends(require_role('teacher'))):
    return get_student_summary_for_teacher(user['id'], student_id)

@app.post('/api/teacher/assignments')
def teacher_create_assignment(req: AssignmentRequest, user=Depends(require_role('teacher'))):
    aid = create_assignment(user['id'], req.title, req.description, req.question_ids, req.target_user_ids, req.due_at)
    return {'assignment_id': aid}

@app.get('/api/teacher/assignments/{assignment_id}/results')
def teacher_assignment_results(assignment_id: int, user=Depends(require_role('teacher'))):
    return list_assignment_results(user['id'], assignment_id)

@app.get('/api/teacher/assignments/{assignment_id}/results.csv')
def teacher_assignment_results_csv(assignment_id: int, user=Depends(require_role('teacher'))):
    return Response(assignment_results_csv(user['id'], assignment_id), media_type='text/csv; charset=utf-8', headers={'Content-Disposition': f'attachment; filename=assignment_{assignment_id}_results.csv'})

@app.get('/api/admin/questions')
def admin_questions(limit: int = 500, user=Depends(require_role('admin'))):
    return list_questions(status='', limit=min(limit, 1000))

@app.get('/api/admin/quality')
def admin_quality(user=Depends(require_role('admin'))):
    return get_admin_quality_summary()

@app.get('/api/admin/beta-feedback')
def admin_beta_feedback(limit: int = 200, user=Depends(require_role('admin'))):
    return get_beta_feedback_summary()['items'][:max(1, min(limit, 1000))]

@app.get('/api/admin/beta-feedback/summary')
def admin_beta_feedback_summary(user=Depends(require_role('admin'))):
    return get_beta_feedback_summary()

@app.get('/api/admin/tester-students/activity')
def admin_tester_activity(limit: int = 200, user=Depends(require_role('admin'))):
    return get_beta_tester_activity(limit)

@app.post('/api/admin/tester-students')
def admin_create_tester_student(req: BetaStudentRequest, user=Depends(require_role('admin'))):
    return create_beta_student(req.email, req.password, req.display_name, req.grade, req.school_name, req.target_exam_year)

@app.post('/api/admin/questions')
def admin_create_question(req: AdminQuestionRequest, user=Depends(require_role('admin'))):
    qid = create_question(user['id'], req.question_type, req.question_text, req.topic_code, req.choices, req.correct_codes, req.numeric_answer, req.unit, req.explanation_short, req.explanation_standard, req.explanation_detailed, req.importance, req.difficulty, req.permission_status, req.status, choice_explanations=req.choice_explanations)
    return {'question_id': qid}

@app.post('/api/admin/questions/{qid}/approve')
def admin_approve_question(qid: int, user=Depends(require_role('admin'))):
    approve_question(qid, user['id'])
    return {'ok': True}

@app.post('/api/admin/questions/{qid}/unpublish')
def admin_unpublish_question(qid: int, user=Depends(require_role('admin'))):
    unpublish_question(qid, user['id'])
    return {'ok': True}

@app.post('/api/line/webhook')
async def line_webhook(request: Request, x_line_signature: str | None = Header(default=None)):
    raw = await request.body()
    if LINE_CHANNEL_SECRET and not verify_line_signature(raw, x_line_signature or '', LINE_CHANNEL_SECRET):
        raise HTTPException(400, 'Invalid LINE signature')
    payload = await request.json()
    for event in payload.get('events', []):
        text = (event.get('message', {}).get('text') or '').strip()
        if event.get('type') == 'message' and text == 'テスター希望':
            execute('INSERT INTO tester_requests(line_user_id,message,requested_at) VALUES(?,?,?)', (event.get('source', {}).get('userId'), 'テスター希望', utc_now()))
    return {'ok': True, 'demo_mode': not bool(LINE_CHANNEL_SECRET)}
