from __future__ import annotations
import json, sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from .config import DB_PATH

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

@contextmanager
def connect(db_path: Path | str = DB_PATH):
    path = Path(db_path); path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path); conn.row_factory = sqlite3.Row; conn.execute('PRAGMA foreign_keys=ON')
    try:
        yield conn; conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()

SCHEMA = r'''
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT UNIQUE,password_hash TEXT NOT NULL,line_user_id TEXT UNIQUE,role TEXT NOT NULL CHECK(role IN ('student','teacher','admin')),status TEXT NOT NULL DEFAULT 'active',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS user_profiles(user_id INTEGER PRIMARY KEY,display_name TEXT NOT NULL,school_name TEXT,grade TEXT,target_exam_year INTEGER,daily_study_minutes INTEGER DEFAULT 15,target_score INTEGER DEFAULT 108,notification_time TEXT DEFAULT '20:00',diagnostic_completed INTEGER NOT NULL DEFAULT 0,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS organizations(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,organization_type TEXT DEFAULT 'training_school',status TEXT DEFAULT 'active',created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS organization_memberships(id INTEGER PRIMARY KEY AUTOINCREMENT,organization_id INTEGER NOT NULL,user_id INTEGER NOT NULL,class_name TEXT,academic_year INTEGER,membership_role TEXT NOT NULL,UNIQUE(organization_id,user_id),FOREIGN KEY(organization_id) REFERENCES organizations(id) ON DELETE CASCADE,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS exam_standard_versions(id INTEGER PRIMARY KEY AUTOINCREMENT,version_name TEXT NOT NULL,effective_exam_from INTEGER,effective_exam_to INTEGER,source_url TEXT,status TEXT DEFAULT 'active');
CREATE TABLE IF NOT EXISTS subjects(id INTEGER PRIMARY KEY AUTOINCREMENT,standard_version_id INTEGER NOT NULL,code TEXT UNIQUE NOT NULL,name TEXT NOT NULL,display_order INTEGER NOT NULL,FOREIGN KEY(standard_version_id) REFERENCES exam_standard_versions(id));
CREATE TABLE IF NOT EXISTS topics(id INTEGER PRIMARY KEY AUTOINCREMENT,subject_id INTEGER NOT NULL,parent_topic_id INTEGER,level TEXT NOT NULL DEFAULT 'small',code TEXT UNIQUE NOT NULL,name TEXT NOT NULL,description TEXT,display_order INTEGER DEFAULT 0,FOREIGN KEY(subject_id) REFERENCES subjects(id),FOREIGN KEY(parent_topic_id) REFERENCES topics(id));
CREATE TABLE IF NOT EXISTS questions(id INTEGER PRIMARY KEY AUTOINCREMENT,question_type TEXT NOT NULL,question_text TEXT NOT NULL,numeric_answer REAL,numeric_tolerance REAL DEFAULT 0.01,unit TEXT,explanation_short TEXT NOT NULL,explanation_standard TEXT NOT NULL,explanation_detailed TEXT NOT NULL,difficulty INTEGER NOT NULL DEFAULT 2 CHECK(difficulty BETWEEN 1 AND 5),importance INTEGER NOT NULL DEFAULT 3 CHECK(importance BETWEEN 1 AND 5),frequency_score REAL NOT NULL DEFAULT 1.0,source_type TEXT NOT NULL DEFAULT 'sample_original',status TEXT NOT NULL DEFAULT 'published',created_by INTEGER,approved_by INTEGER,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,FOREIGN KEY(created_by) REFERENCES users(id),FOREIGN KEY(approved_by) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS question_choices(id INTEGER PRIMARY KEY AUTOINCREMENT,question_id INTEGER NOT NULL,choice_code TEXT NOT NULL,choice_text TEXT NOT NULL,is_correct INTEGER NOT NULL DEFAULT 0,explanation TEXT NOT NULL DEFAULT '',display_order INTEGER NOT NULL,UNIQUE(question_id,choice_code),FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS question_topic_mappings(id INTEGER PRIMARY KEY AUTOINCREMENT,question_id INTEGER NOT NULL,topic_id INTEGER NOT NULL,mapping_type TEXT DEFAULT 'primary',weight REAL DEFAULT 1.0,UNIQUE(question_id,topic_id),FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE,FOREIGN KEY(topic_id) REFERENCES topics(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS question_sources(id INTEGER PRIMARY KEY AUTOINCREMENT,question_id INTEGER NOT NULL,exam_number TEXT,exam_year INTEGER,session TEXT,question_number TEXT,source_name TEXT,source_url TEXT,copyright_holder TEXT,permission_status TEXT DEFAULT 'internal_sample',checked_at TEXT,checked_by INTEGER,FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE,FOREIGN KEY(checked_by) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS answer_history(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,question_id INTEGER NOT NULL,selected_answer TEXT,numeric_answer REAL,is_correct INTEGER NOT NULL,confidence_level TEXT NOT NULL,response_time_seconds INTEGER NOT NULL DEFAULT 0,answer_mode TEXT NOT NULL,session_id TEXT,answered_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS user_topic_mastery(user_id INTEGER NOT NULL,topic_id INTEGER NOT NULL,mastery_score REAL NOT NULL DEFAULT 0,confidence_score REAL NOT NULL DEFAULT 0,retention_score REAL NOT NULL DEFAULT 0,total_answers INTEGER NOT NULL DEFAULT 0,correct_answers INTEGER NOT NULL DEFAULT 0,last_answered_at TEXT,updated_at TEXT NOT NULL,PRIMARY KEY(user_id,topic_id),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,FOREIGN KEY(topic_id) REFERENCES topics(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS review_schedules(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,question_id INTEGER NOT NULL,review_type TEXT NOT NULL,scheduled_date TEXT NOT NULL,priority REAL NOT NULL DEFAULT 1.0,status TEXT NOT NULL DEFAULT 'pending',created_at TEXT NOT NULL,UNIQUE(user_id,question_id,scheduled_date),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS daily_study_plans(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,plan_date TEXT NOT NULL,recommended_count INTEGER NOT NULL DEFAULT 5,estimated_minutes INTEGER NOT NULL DEFAULT 12,status TEXT NOT NULL DEFAULT 'not_started',generated_at TEXT NOT NULL,UNIQUE(user_id,plan_date),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS daily_study_plan_items(id INTEGER PRIMARY KEY AUTOINCREMENT,plan_id INTEGER NOT NULL,question_id INTEGER NOT NULL,item_type TEXT NOT NULL,display_order INTEGER NOT NULL,reason TEXT NOT NULL,UNIQUE(plan_id,question_id),FOREIGN KEY(plan_id) REFERENCES daily_study_plans(id) ON DELETE CASCADE,FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS student_exam_plans(user_id INTEGER PRIMARY KEY,target_exam_date TEXT,updated_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS exam_events(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,event_type TEXT NOT NULL CHECK(event_type IN ('mock','past_exam','real_exam')),title TEXT NOT NULL,event_date TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'scheduled',memo TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS score_records(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,score_type TEXT NOT NULL CHECK(score_type IN ('mock','past_exam')),title TEXT NOT NULL,taken_at TEXT NOT NULL,total_score REAL NOT NULL,max_score REAL NOT NULL,morning_score REAL,afternoon_score REAL,subject_scores TEXT NOT NULL DEFAULT '{}',memo TEXT,created_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS diagnostic_sessions(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'in_progress',current_index INTEGER NOT NULL DEFAULT 0,started_at TEXT NOT NULL,completed_at TEXT,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS diagnostic_items(id INTEGER PRIMARY KEY AUTOINCREMENT,diagnostic_session_id INTEGER NOT NULL,question_id INTEGER NOT NULL,display_order INTEGER NOT NULL,answered INTEGER NOT NULL DEFAULT 0,UNIQUE(diagnostic_session_id,question_id),FOREIGN KEY(diagnostic_session_id) REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS assignments(id INTEGER PRIMARY KEY AUTOINCREMENT,teacher_id INTEGER NOT NULL,organization_id INTEGER,title TEXT NOT NULL,description TEXT,start_at TEXT NOT NULL,due_at TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'published',created_at TEXT NOT NULL,FOREIGN KEY(teacher_id) REFERENCES users(id),FOREIGN KEY(organization_id) REFERENCES organizations(id));
CREATE TABLE IF NOT EXISTS assignment_items(id INTEGER PRIMARY KEY AUTOINCREMENT,assignment_id INTEGER NOT NULL,question_id INTEGER NOT NULL,display_order INTEGER NOT NULL,UNIQUE(assignment_id,question_id),FOREIGN KEY(assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,FOREIGN KEY(question_id) REFERENCES questions(id));
CREATE TABLE IF NOT EXISTS assignment_targets(id INTEGER PRIMARY KEY AUTOINCREMENT,assignment_id INTEGER NOT NULL,user_id INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'not_started',UNIQUE(assignment_id,user_id),FOREIGN KEY(assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS tester_requests(id INTEGER PRIMARY KEY AUTOINCREMENT,line_user_id TEXT,message TEXT,requested_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS beta_feedback(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),category TEXT NOT NULL,message TEXT NOT NULL,page_url TEXT,user_agent TEXT,created_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS audit_logs(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,action TEXT NOT NULL,target_type TEXT NOT NULL,target_id TEXT,before_data TEXT,after_data TEXT,created_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id));
CREATE INDEX IF NOT EXISTS idx_answers_user_date ON answer_history(user_id,answered_at);
CREATE INDEX IF NOT EXISTS idx_review_user_date ON review_schedules(user_id,scheduled_date,status);
CREATE INDEX IF NOT EXISTS idx_exam_events_user_date ON exam_events(user_id,event_date);
CREATE INDEX IF NOT EXISTS idx_score_records_user_date ON score_records(user_id,taken_at);
'''

def initialize_database(db_path: Path | str = DB_PATH) -> None:
    with connect(db_path) as conn: conn.executescript(SCHEMA)

def fetch_one(sql: str, params: Iterable[Any]=(), db_path: Path | str=DB_PATH):
    with connect(db_path) as conn: return conn.execute(sql, tuple(params)).fetchone()

def fetch_all(sql: str, params: Iterable[Any]=(), db_path: Path | str=DB_PATH):
    with connect(db_path) as conn: return conn.execute(sql, tuple(params)).fetchall()

def execute(sql: str, params: Iterable[Any]=(), db_path: Path | str=DB_PATH) -> int:
    with connect(db_path) as conn:
        cur=conn.execute(sql, tuple(params)); return int(cur.lastrowid)

def audit(user_id:int|None,action:str,target_type:str,target_id:str|int|None=None,before:Any=None,after:Any=None,db_path:Path|str=DB_PATH)->None:
    execute('INSERT INTO audit_logs(user_id,action,target_type,target_id,before_data,after_data,created_at) VALUES(?,?,?,?,?,?,?)',(user_id,action,target_type,str(target_id) if target_id is not None else None,json.dumps(before,ensure_ascii=False) if before is not None else None,json.dumps(after,ensure_ascii=False) if after is not None else None,utc_now()),db_path)
