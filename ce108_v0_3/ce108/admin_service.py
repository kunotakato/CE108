from __future__ import annotations
import csv,io
from pathlib import Path
from .config import DB_PATH
from .database import audit,connect,utc_now
REQ={'question_type','question_text','correct_codes','topic_code','explanation_short','explanation_standard','explanation_detailed','difficulty','importance','frequency_score','source_type','permission_status','status'}
VALID_TYPES={'single','multiple','truefalse','numeric'}
PUBLISHABLE={'permission_confirmed','internal_sample','public_domain'}

def _validate_question(question_type:str,question_text:str,choices:list[str],correct_codes:set[str],numeric_answer:float|None,short:str,standard:str,detailed:str,difficulty:int,importance:int)->None:
    if question_type not in VALID_TYPES:raise ValueError('question_typeが不正です。')
    if not question_text.strip():raise ValueError('問題文を入力してください。')
    if not short.strip() or not standard.strip() or not detailed.strip():raise ValueError('解説を入力してください。')
    if difficulty<1 or difficulty>5 or importance<1 or importance>5:raise ValueError('難易度と重要度は1〜5で入力してください。')
    if question_type=='numeric':
        if numeric_answer is None:raise ValueError('数値問題にはnumeric_answerが必要です。')
        return
    active=[c for c in choices if c.strip()]
    if question_type=='truefalse' and len(active)!=2:raise ValueError('正誤問題は選択肢を2つ入力してください。')
    if question_type in {'single','multiple'} and len(active)<2:raise ValueError('選択問題は選択肢を2つ以上入力してください。')
    if not correct_codes:raise ValueError('正答コードを入力してください。')
    if not correct_codes.issubset({str(i) for i in range(1,len(active)+1)}):raise ValueError('正答コードが選択肢範囲外です。')
    if question_type in {'single','truefalse'} and len(correct_codes)!=1:raise ValueError('単一選択・正誤問題の正答は1つです。')

def import_questions_csv(content:bytes,admin_id:int,db_path:Path|str=DB_PATH):
    reader=csv.DictReader(io.StringIO(content.decode('utf-8-sig')));missing=REQ-set(reader.fieldnames or [])
    if missing:raise ValueError('CSV必須列が不足: '+','.join(sorted(missing)))
    inserted=0;errors=[]
    with connect(db_path) as conn:
        topics={r['code']:r['id'] for r in conn.execute('SELECT id,code FROM topics')}
        for line,row in enumerate(reader,2):
            try:
                tid=topics.get((row['topic_code'] or '').strip())
                if not tid:raise ValueError('topic_codeが存在しません')
                permission=row['permission_status'].strip();status=row['status'].strip() or 'draft';qtype=row['question_type'].strip()
                correct={x.strip() for x in (row.get('correct_codes') or '').split(',') if x.strip()}
                numeric=float(row['numeric_answer']) if row.get('numeric_answer') else None
                choices=[row.get(f'choice_{i}') or '' for i in range(1,6)]
                _validate_question(qtype,row['question_text'],choices,correct,numeric,row['explanation_short'],row['explanation_standard'],row['explanation_detailed'],int(row['difficulty']),int(row['importance']))
                if status=='published' and permission not in PUBLISHABLE:status='draft'
                qid=conn.execute('''INSERT INTO questions(question_type,question_text,numeric_answer,numeric_tolerance,unit,explanation_short,explanation_standard,explanation_detailed,difficulty,importance,frequency_score,source_type,status,created_by,approved_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(row['question_type'].strip(),row['question_text'].strip(),float(row['numeric_answer']) if row.get('numeric_answer') else None,float(row.get('numeric_tolerance') or .01),row.get('unit') or None,row['explanation_short'],row['explanation_standard'],row['explanation_detailed'],int(row['difficulty']),int(row['importance']),float(row['frequency_score']),row['source_type'],status,admin_id,admin_id if status=='published' else None,utc_now(),utc_now())).lastrowid
                for i in range(1,6):
                    ch=(row.get(f'choice_{i}') or '').strip()
                    if ch:conn.execute("INSERT INTO question_choices(question_id,choice_code,choice_text,is_correct,explanation,display_order) VALUES(?,?,?,?, '',?)",(qid,str(i),ch,int(str(i) in correct),i))
                conn.execute("INSERT INTO question_topic_mappings(question_id,topic_id,mapping_type,weight) VALUES(?,?,'primary',1.0)",(qid,tid));conn.execute('''INSERT INTO question_sources(question_id,source_name,source_url,copyright_holder,permission_status,checked_at,checked_by) VALUES(?,?,?,?,?,?,?)''',(qid,row.get('source_name'),row.get('source_url'),row.get('copyright_holder'),permission,utc_now(),admin_id));inserted+=1
            except Exception as e:errors.append(f'{line}行目: {e}')
    audit(admin_id,'csv_import','questions',after={'inserted':inserted,'errors':errors},db_path=db_path);return {'inserted':inserted,'errors':errors}

def create_question(admin_id:int,question_type:str,question_text:str,topic_code:str,choices:list[str],correct_codes:list[str],numeric_answer:float|None,unit:str|None,short:str,standard:str,detailed:str,importance:int,difficulty:int,permission_status='internal_sample',status='draft',db_path:Path|str=DB_PATH):
    _validate_question(question_type,question_text,choices,set(correct_codes),numeric_answer,short,standard,detailed,difficulty,importance)
    with connect(db_path) as conn:
        t=conn.execute('SELECT id FROM topics WHERE code=?',(topic_code,)).fetchone()
        if not t:raise ValueError('出題基準コードがありません。')
        if status=='published' and permission_status not in PUBLISHABLE:raise ValueError('権利確認未完了の問題は公開できません。')
        qid=conn.execute("""INSERT INTO questions(question_type,question_text,numeric_answer,numeric_tolerance,unit,explanation_short,explanation_standard,explanation_detailed,difficulty,importance,frequency_score,source_type,status,created_by,approved_by,created_at,updated_at) VALUES(?,?,?,.01,?,?,?,?,?,?,1.0,'original',?,?,?,?,?)""",(question_type,question_text,numeric_answer,unit,short,standard,detailed,difficulty,importance,status,admin_id,admin_id if status=='published' else None,utc_now(),utc_now())).lastrowid
        for i,ch in enumerate(choices,1):
            if ch.strip():conn.execute("INSERT INTO question_choices(question_id,choice_code,choice_text,is_correct,explanation,display_order) VALUES(?,?,?,?, '',?)",(qid,str(i),ch.strip(),int(str(i) in correct_codes),i))
        conn.execute("INSERT INTO question_topic_mappings(question_id,topic_id,mapping_type,weight) VALUES(?,?,'primary',1.0)",(qid,t['id']));conn.execute("INSERT INTO question_sources(question_id,source_name,copyright_holder,permission_status,checked_at,checked_by) VALUES(?,'管理画面作成','CE108',?,?,?)",(qid,permission_status,utc_now(),admin_id))
    audit(admin_id,'create','question',qid,db_path=db_path);return qid

def approve_question(question_id:int,admin_id:int,db_path:Path|str=DB_PATH):
    with connect(db_path) as conn:
        s=conn.execute('SELECT permission_status FROM question_sources WHERE question_id=? ORDER BY id DESC LIMIT 1',(question_id,)).fetchone()
        if not s or s['permission_status'] not in PUBLISHABLE:raise ValueError('権利確認が完了していません。')
        conn.execute("UPDATE questions SET status='published',approved_by=?,updated_at=? WHERE id=?",(admin_id,utc_now(),question_id))
    audit(admin_id,'approve','question',question_id,db_path=db_path)

def unpublish_question(question_id:int,admin_id:int,db_path:Path|str=DB_PATH):
    with connect(db_path) as conn:
        before=conn.execute('SELECT id,status FROM questions WHERE id=?',(question_id,)).fetchone()
        if not before:raise ValueError('問題が見つかりません。')
        conn.execute("UPDATE questions SET status='archived',updated_at=? WHERE id=?",(utc_now(),question_id))
    audit(admin_id,'unpublish','question',question_id,before=dict(before),after={'status':'archived'},db_path=db_path)
