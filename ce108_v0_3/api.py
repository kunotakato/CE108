from __future__ import annotations
from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from ce108.admin_service import approve_question, create_question, unpublish_question
from ce108.config import LINE_CHANNEL_SECRET
from ce108.database import execute, utc_now
from ce108.security import create_access_token, decode_access_token, verify_line_signature
from ce108.seed import seed_database
from ce108.services import (
    answer_diagnostic,
    assignment_results_csv,
    authenticate_user,
    create_assignment,
    diagnostic_result,
    generate_daily_plan,
    get_diagnostic_state,
    get_question,
    get_student_summary_for_teacher,
    get_user,
    list_assignment_results,
    list_questions,
    list_students_for_teacher,
    public_question,
    record_answer,
    start_diagnostic,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_database()
    yield

app = FastAPI(title='CE108 API', version='0.3.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:8501', 'http://127.0.0.1:8501'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
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
    return {'status': 'ok', 'version': '0.3.0'}

@app.post('/api/auth/login')
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = authenticate_user(form.username, form.password)
    if not user:
        raise HTTPException(401, 'メールアドレスまたはパスワードが違います。')
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
def today(user=Depends(require_role('student'))):
    return generate_daily_plan(user['id'])

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

@app.post('/api/admin/questions')
def admin_create_question(req: AdminQuestionRequest, user=Depends(require_role('admin'))):
    qid = create_question(user['id'], req.question_type, req.question_text, req.topic_code, req.choices, req.correct_codes, req.numeric_answer, req.unit, req.explanation_short, req.explanation_standard, req.explanation_detailed, req.importance, req.difficulty, req.permission_status, req.status)
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
