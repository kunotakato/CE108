from __future__ import annotations
import csv, io, json, math
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from .config import DB_PATH
from .database import connect, execute, fetch_all, fetch_one, utc_now

CONFIDENCE_VALUES={'確実に分かる':1.0,'たぶん分かる':0.82,'迷った':0.58,'勘で答えた':0.35}

def authenticate_user(email:str,password:str,db_path:Path|str=DB_PATH):
    from .security import verify_password
    row=fetch_one('''SELECT u.*,p.display_name,p.grade,p.diagnostic_completed FROM users u JOIN user_profiles p ON p.user_id=u.id WHERE lower(u.email)=lower(?) AND u.status='active' ''',(email.strip(),),db_path)
    return dict(row) if row and verify_password(password,row['password_hash']) else None

def get_user(user_id:int,db_path:Path|str=DB_PATH):
    row=fetch_one('''SELECT u.id,u.email,u.line_user_id,u.role,u.status,p.display_name,p.school_name,p.grade,p.target_exam_year,p.daily_study_minutes,p.target_score,p.notification_time,p.diagnostic_completed FROM users u JOIN user_profiles p ON p.user_id=u.id WHERE u.id=?''',(user_id,),db_path)
    return dict(row) if row else None

def list_topics(db_path:Path|str=DB_PATH):
    return [dict(r) for r in fetch_all('SELECT t.id,t.code,t.name,t.subject_id,s.name subject_name FROM topics t JOIN subjects s ON s.id=t.subject_id ORDER BY s.display_order,t.display_order',(),db_path)]

def get_question(question_id:int,db_path:Path|str=DB_PATH):
    row=fetch_one('''SELECT q.*,s.name subject_name,t.name topic_name,t.id topic_id FROM questions q LEFT JOIN question_topic_mappings m ON m.question_id=q.id AND m.mapping_type='primary' LEFT JOIN topics t ON t.id=m.topic_id LEFT JOIN subjects s ON s.id=t.subject_id WHERE q.id=?''',(question_id,),db_path)
    if not row:return None
    q=dict(row);q['choices']=[dict(r) for r in fetch_all('SELECT choice_code,choice_text,is_correct,explanation,display_order FROM question_choices WHERE question_id=? ORDER BY display_order',(question_id,),db_path)];q['correct_codes']=[c['choice_code'] for c in q['choices'] if c['is_correct']]
    return q

def list_questions(status='published',limit=500,db_path:Path|str=DB_PATH):
    where='WHERE q.status=?' if status else ''
    params=(status,limit) if status else (limit,)
    return [dict(r) for r in fetch_all(f'''SELECT q.id,q.question_type,q.question_text,q.difficulty,q.importance,q.frequency_score,q.source_type,q.status,s.name subject_name,t.name topic_name FROM questions q LEFT JOIN question_topic_mappings m ON m.question_id=q.id AND m.mapping_type='primary' LEFT JOIN topics t ON t.id=m.topic_id LEFT JOIN subjects s ON s.id=t.subject_id {where} ORDER BY q.id LIMIT ?''',params,db_path)]

def public_question(q:dict)->dict:
    safe=dict(q);safe.pop('correct_codes',None);safe.pop('numeric_answer',None)
    safe.pop('explanation_short',None);safe.pop('explanation_standard',None);safe.pop('explanation_detailed',None)
    for c in safe.get('choices',[]):c.pop('is_correct',None);c.pop('explanation',None)
    return safe

def check_answer(q:dict,selected_codes:list[str]|None=None,numeric_answer:float|None=None)->bool:
    if q['question_type']=='numeric':
        return numeric_answer is not None and math.isclose(float(numeric_answer),float(q['numeric_answer']),rel_tol=float(q.get('numeric_tolerance') or .01),abs_tol=float(q.get('numeric_tolerance') or .01))
    return set(selected_codes or [])==set(q['correct_codes'])

def _evidence(correct:bool,confidence:str,seconds:int)->float:
    c=CONFIDENCE_VALUES.get(confidence,.5);base=(72*c+18) if correct else (18-8*c);speed=4 if seconds<=60 else (-4 if seconds>=180 else 0);return max(0,min(100,base+speed))

def update_mastery(user_id:int,question_id:int,correct:bool,confidence:str,seconds:int,db_path:Path|str=DB_PATH):
    topics=fetch_all('SELECT topic_id,weight FROM question_topic_mappings WHERE question_id=?',(question_id,),db_path);ev=_evidence(correct,confidence,seconds)
    with connect(db_path) as conn:
        for t in topics:
            cur=conn.execute('SELECT * FROM user_topic_mastery WHERE user_id=? AND topic_id=?',(user_id,t['topic_id'])).fetchone()
            if cur:
                score=float(cur['mastery_score'])*.7+ev*.3*float(t['weight']);ret=float(cur['retention_score'])*.75+(100 if correct else 20)*.25
                conn.execute('''UPDATE user_topic_mastery SET mastery_score=?,confidence_score=?,retention_score=?,total_answers=?,correct_answers=?,last_answered_at=?,updated_at=? WHERE user_id=? AND topic_id=?''',(round(score,2),round(CONFIDENCE_VALUES.get(confidence,.5)*100,2),round(ret,2),cur['total_answers']+1,cur['correct_answers']+int(correct),utc_now(),utc_now(),user_id,t['topic_id']))
            else:
                conn.execute('''INSERT INTO user_topic_mastery(user_id,topic_id,mastery_score,confidence_score,retention_score,total_answers,correct_answers,last_answered_at,updated_at) VALUES(?,?,?,?,?,1,?,?,?)''',(user_id,t['topic_id'],round(ev*float(t['weight']),2),round(CONFIDENCE_VALUES.get(confidence,.5)*100,2),100 if correct else 20,int(correct),utc_now(),utc_now()))

def schedule_review(user_id:int,question_id:int,correct:bool,confidence:str,importance:int,db_path:Path|str=DB_PATH)->str:
    days=1 if (not correct or confidence=='勘で答えた') else 3 if confidence=='迷った' else 7 if confidence=='たぶん分かる' else 14
    if importance>=5 and days>1:days=max(1,days-2)
    target=(date.today()+timedelta(days=days)).isoformat()
    execute("INSERT OR IGNORE INTO review_schedules(user_id,question_id,review_type,scheduled_date,priority,status,created_at) VALUES(?,?, 'same_or_similar',?,?,'pending',?)",(user_id,question_id,target,float(importance),utc_now()),db_path);return target

def record_answer(user_id:int,question_id:int,selected_codes:list[str]|None,numeric_answer:float|None,confidence:str,response_time_seconds:int,answer_mode:str,session_id:str|None=None,db_path:Path|str=DB_PATH):
    q=get_question(question_id,db_path)
    if not q:raise ValueError('問題が見つかりません。')
    if q['status']!='published':raise ValueError('公開中の問題ではありません。')
    if q['question_type']=='numeric' and numeric_answer is None:raise ValueError('数値回答を入力してください。')
    if q['question_type']!='numeric' and not selected_codes:raise ValueError('選択肢を選んでください。')
    correct=check_answer(q,selected_codes,numeric_answer)
    execute('''INSERT INTO answer_history(user_id,question_id,selected_answer,numeric_answer,is_correct,confidence_level,response_time_seconds,answer_mode,session_id,answered_at) VALUES(?,?,?,?,?,?,?,?,?,?)''',(user_id,question_id,json.dumps(selected_codes or [],ensure_ascii=False),numeric_answer,int(correct),confidence,max(0,int(response_time_seconds)),answer_mode,session_id,utc_now()),db_path)
    update_mastery(user_id,question_id,correct,confidence,response_time_seconds,db_path);review=schedule_review(user_id,question_id,correct,confidence,int(q['importance']),db_path)
    return {'is_correct':correct,'review_date':review,'question':q}

def _count(minutes:int)->int:return max(3,min(20,round(minutes/3)))

def generate_daily_plan(user_id:int,count:int|None=None,plan_date:str|None=None,db_path:Path|str=DB_PATH):
    plan_date=plan_date or date.today().isoformat();user=get_user(user_id,db_path);count=count or _count(int(user['daily_study_minutes'] or 15))
    old=fetch_one('SELECT id FROM daily_study_plans WHERE user_id=? AND plan_date=?',(user_id,plan_date),db_path)
    if old:return get_daily_plan(user_id,plan_date,db_path)
    due=[dict(r) for r in fetch_all('''SELECT r.question_id,q.importance FROM review_schedules r JOIN questions q ON q.id=r.question_id WHERE r.user_id=? AND r.status='pending' AND r.scheduled_date<=? AND q.status='published' ORDER BY r.priority DESC,r.scheduled_date LIMIT ?''',(user_id,plan_date,count),db_path)]
    selected=[];ids=set()
    for r in due[:max(1,round(count*.4))]:selected.append((r['question_id'],'復習','復習期限が到来しています'));ids.add(r['question_id'])
    rows=[dict(r) for r in fetch_all('''SELECT q.id,q.importance,q.frequency_score,COALESCE(AVG(m.mastery_score),0) mastery FROM questions q LEFT JOIN question_topic_mappings tm ON tm.question_id=q.id LEFT JOIN user_topic_mastery m ON m.topic_id=tm.topic_id AND m.user_id=? WHERE q.status='published' GROUP BY q.id''',(user_id,),db_path)]
    def priority(r):return (r['importance']/5)*.5+min(1,r['frequency_score']/3)*.25+(1-r['mastery']/100)*.25
    for r in sorted([x for x in rows if x['id'] not in ids],key=priority,reverse=True)[:count-len(selected)]:
        typ,reason=('苦手','理解度が低い分野を優先') if r['mastery']<40 else (('必達','重要度・頻出度が高い') if r['importance']>=4 or r['frequency_score']>=2 else ('新規','未学習範囲を拡張'))
        selected.append((r['id'],typ,reason))
    with connect(db_path) as conn:
        cur=conn.execute("INSERT OR IGNORE INTO daily_study_plans(user_id,plan_date,recommended_count,estimated_minutes,status,generated_at) VALUES(?,?,?,?, 'not_started',?)",(user_id,plan_date,len(selected),max(5,round(len(selected)*2.5)),utc_now()))
        if cur.rowcount:
            pid=int(cur.lastrowid)
            conn.executemany('INSERT INTO daily_study_plan_items(plan_id,question_id,item_type,display_order,reason) VALUES(?,?,?,?,?)',[(pid,q,t,i+1,r) for i,(q,t,r) in enumerate(selected)])
    return get_daily_plan(user_id,plan_date,db_path)

def get_daily_plan(user_id:int,plan_date:str|None=None,db_path:Path|str=DB_PATH):
    plan_date=plan_date or date.today().isoformat();p=fetch_one('SELECT * FROM daily_study_plans WHERE user_id=? AND plan_date=?',(user_id,plan_date),db_path)
    if not p:return None
    items=fetch_all('''SELECT i.*,q.question_text,q.question_type,q.importance,s.name subject_name,t.name topic_name,EXISTS(SELECT 1 FROM answer_history a WHERE a.user_id=? AND a.question_id=i.question_id AND date(a.answered_at)=? AND a.answer_mode='daily') completed FROM daily_study_plan_items i JOIN questions q ON q.id=i.question_id LEFT JOIN question_topic_mappings m ON m.question_id=q.id AND m.mapping_type='primary' LEFT JOIN topics t ON t.id=m.topic_id LEFT JOIN subjects s ON s.id=t.subject_id WHERE i.plan_id=? ORDER BY i.display_order''',(user_id,plan_date,p['id']),db_path)
    d=dict(p);d['items']=[dict(r) for r in items];return d

def get_mastery_report(user_id:int,db_path:Path|str=DB_PATH):
    return [dict(r) for r in fetch_all('''SELECT s.name subject_name,t.name topic_name,COALESCE(m.mastery_score,0) mastery_score,COALESCE(m.retention_score,0) retention_score,COALESCE(m.total_answers,0) total_answers,COALESCE(m.correct_answers,0) correct_answers,m.last_answered_at FROM topics t JOIN subjects s ON s.id=t.subject_id LEFT JOIN user_topic_mastery m ON m.topic_id=t.id AND m.user_id=? ORDER BY mastery_score,s.display_order,t.display_order''',(user_id,),db_path)]

def get_learning_summary(user_id:int,db_path:Path|str=DB_PATH):
    r=fetch_one('SELECT COUNT(*) total,COALESCE(SUM(is_correct),0) correct,COALESCE(AVG(response_time_seconds),0) avg_seconds FROM answer_history WHERE user_id=?',(user_id,),db_path);due=fetch_one("SELECT COUNT(*) due FROM review_schedules WHERE user_id=? AND status='pending' AND scheduled_date<=?",(user_id,date.today().isoformat()),db_path);total=int(r['total']);correct=int(r['correct']);return {'total':total,'correct':correct,'accuracy':round(correct/total*100,1) if total else 0,'avg_seconds':round(r['avg_seconds'],1),'due_reviews':due['due']}

def list_due_reviews(user_id:int,db_path:Path|str=DB_PATH):
    return [dict(r) for r in fetch_all('''SELECT r.scheduled_date,r.priority,q.id question_id,q.question_text,s.name subject_name,t.name topic_name FROM review_schedules r JOIN questions q ON q.id=r.question_id LEFT JOIN question_topic_mappings m ON m.question_id=q.id AND m.mapping_type='primary' LEFT JOIN topics t ON t.id=m.topic_id LEFT JOIN subjects s ON s.id=t.subject_id WHERE r.user_id=? AND r.status='pending' ORDER BY r.scheduled_date,r.priority DESC''',(user_id,),db_path)]

def _iso_date(value:str)->date:
    return datetime.fromisoformat(value.replace('Z','+00:00')).date()

def _answer_dates(user_id:int,db_path:Path|str=DB_PATH)->list[date]:
    rows=fetch_all("SELECT DISTINCT date(answered_at) d FROM answer_history WHERE user_id=? ORDER BY d DESC",(user_id,),db_path)
    return [_iso_date(r['d']) for r in rows if r['d']]

def _streak(dates:list[date],today:date)->int:
    done=set(dates);cur=today;count=0
    while cur in done:
        count+=1;cur-=timedelta(days=1)
    return count

def get_daily_status(user_id:int,db_path:Path|str=DB_PATH):
    today=date.today();plan=generate_daily_plan(user_id,db_path=db_path);items=plan.get('items',[]) if plan else []
    completed=sum(1 for i in items if i.get('completed'));total=len(items);dates=_answer_dates(user_id,db_path)
    week_start=today-timedelta(days=6);week=[{'date':(week_start+timedelta(days=i)).isoformat(),'completed':(week_start+timedelta(days=i)) in set(dates)} for i in range(7)]
    due=fetch_one("SELECT COUNT(*) due FROM review_schedules WHERE user_id=? AND status='pending' AND scheduled_date<=?",(user_id,today.isoformat()),db_path)
    tomorrow_count=fetch_one("SELECT COUNT(*) n FROM review_schedules WHERE user_id=? AND status='pending' AND scheduled_date=?",(user_id,(today+timedelta(days=1)).isoformat()),db_path)
    status='completed' if total and completed>=total else ('in_progress' if completed else 'not_started')
    return {'date':today.isoformat(),'status':status,'completed_count':completed,'total_count':total,'estimated_minutes':plan.get('estimated_minutes',0) if plan else 0,'streak_days':_streak(dates,today),'weekly':week,'due_reviews':int(due['due']),'tomorrow_preview':{'review_count':int(tomorrow_count['n']),'message':'明日は復習から始めましょう。' if tomorrow_count['n'] else '明日も今日のペースで5問進めましょう。'},'next_action':'復習から始める' if int(due['due']) else ('続きから再開' if status=='in_progress' else '今日の5問を始める')}

def get_review_queue(user_id:int,limit:int=20,db_path:Path|str=DB_PATH):
    today=date.today().isoformat();rows=fetch_all('''SELECT r.id review_id,r.scheduled_date,r.priority,r.status,q.id question_id,q.question_text,q.question_type,s.name subject_name,t.name topic_name,EXISTS(SELECT 1 FROM answer_history a WHERE a.user_id=r.user_id AND a.question_id=r.question_id AND date(a.answered_at)>=r.scheduled_date) completed FROM review_schedules r JOIN questions q ON q.id=r.question_id LEFT JOIN question_topic_mappings m ON m.question_id=q.id AND m.mapping_type='primary' LEFT JOIN topics t ON t.id=m.topic_id LEFT JOIN subjects s ON s.id=t.subject_id WHERE r.user_id=? AND r.status='pending' AND q.status='published' ORDER BY CASE WHEN r.scheduled_date<=? THEN 0 ELSE 1 END,r.scheduled_date,r.priority DESC LIMIT ?''',(user_id,today,max(1,min(limit,100))),db_path)
    items=[]
    for r in rows:
        label='完了' if r['completed'] else ('期限超過' if r['scheduled_date']<today else ('今日' if r['scheduled_date']==today else '今後'))
        d=dict(r);d['review_label']=label;d['reason']='復習期限が到来しています' if label in {'期限超過','今日'} else '近日中の復習予定です';items.append(d)
    return {'date':today,'items':items,'due_count':sum(1 for i in items if i['review_label'] in {'期限超過','今日'}),'upcoming_count':sum(1 for i in items if i['review_label']=='今後')}

def save_beta_feedback(user_id:int,rating:int,category:str,message:str,page_url:str|None=None,user_agent:str|None=None,db_path:Path|str=DB_PATH)->int:
    if rating<1 or rating>5:raise ValueError('評価は1から5で入力してください。')
    category=(category or '').strip()
    message=(message or '').strip()
    if category not in {'使いやすさ','問題・解説','不具合','要望','その他'}:raise ValueError('フィードバック種別を選択してください。')
    if len(message)<3:raise ValueError('フィードバック内容を3文字以上で入力してください。')
    return execute('INSERT INTO beta_feedback(user_id,rating,category,message,page_url,user_agent,created_at) VALUES(?,?,?,?,?,?,?)',(user_id,rating,category,message,page_url,user_agent,utc_now()),db_path)

def get_teacher_support_summary(teacher_id:int,db_path:Path|str=DB_PATH):
    students=list_students_for_teacher(teacher_id,db_path);today=date.today();rows=[]
    for s in students:
        last=fetch_one('SELECT MAX(answered_at) last_answered_at FROM answer_history WHERE user_id=?',(s['id'],),db_path)
        due=fetch_one("SELECT COUNT(*) due FROM review_schedules WHERE user_id=? AND status='pending' AND scheduled_date<=?",(s['id'],today.isoformat()),db_path)
        last_date=_iso_date(last['last_answered_at']) if last and last['last_answered_at'] else None
        inactive_days=(today-last_date).days if last_date else None
        risk='high' if (inactive_days is None or inactive_days>=7 or int(due['due'])>=10) else ('medium' if inactive_days>=3 or int(due['due'])>=5 else 'low')
        weak=get_mastery_report(s['id'],db_path)[:3]
        item=dict(s);item.update({'last_answered_at':last['last_answered_at'] if last else None,'inactive_days':inactive_days,'due_reviews':int(due['due']),'risk_level':risk,'weak_topics':weak});rows.append(item)
    return sorted(rows,key=lambda x:({'high':0,'medium':1,'low':2}[x['risk_level']],-(x['due_reviews'] or 0),x['display_name']))

def get_admin_quality_summary(db_path:Path|str=DB_PATH):
    rows=fetch_all('''SELECT q.id,q.question_type,q.question_text,q.status,q.explanation_short,q.explanation_standard,q.explanation_detailed,COALESCE(s.permission_status,'missing') permission_status,(SELECT COUNT(*) FROM question_choices c WHERE c.question_id=q.id) choice_count FROM questions q LEFT JOIN question_sources s ON s.question_id=q.id WHERE s.id IS NULL OR s.id=(SELECT MAX(id) FROM question_sources WHERE question_id=q.id) ORDER BY q.id''',(),db_path)
    items=[];counts={'ready':0,'needs_review':0,'blocked':0}
    for r in rows:
        issues=[]
        if r['permission_status'] not in {'permission_confirmed','internal_sample','public_domain'}:issues.append('権利状態の確認が必要です')
        if min(len(r['explanation_short'] or ''),len(r['explanation_standard'] or ''),len(r['explanation_detailed'] or ''))<2:issues.append('解説が不足しています')
        if r['question_type']!='numeric' and int(r['choice_count'])<2:issues.append('選択肢が不足しています')
        quality='blocked' if any('権利' in x for x in issues) else ('needs_review' if issues else 'ready')
        counts[quality]+=1;items.append({'id':r['id'],'question_type':r['question_type'],'status':r['status'],'permission_status':r['permission_status'],'quality_status':quality,'issues':issues,'question_text':r['question_text']})
    return {'counts':counts,'items':items}

def start_diagnostic(user_id:int,question_count:int=30,db_path:Path|str=DB_PATH):
    old=fetch_one("SELECT * FROM diagnostic_sessions WHERE user_id=? AND status='in_progress' ORDER BY id DESC LIMIT 1",(user_id,),db_path)
    if old:return dict(old)
    ids=[r['id'] for r in fetch_all("SELECT id FROM questions WHERE status='published' ORDER BY importance DESC,id LIMIT ?",(question_count,),db_path)]
    if len(ids)<question_count:raise ValueError('診断問題が不足しています。')
    sid=execute("INSERT INTO diagnostic_sessions(user_id,status,current_index,started_at) VALUES(?,'in_progress',0,?)",(user_id,utc_now()),db_path)
    with connect(db_path) as conn:conn.executemany('INSERT INTO diagnostic_items(diagnostic_session_id,question_id,display_order) VALUES(?,?,?)',[(sid,q,i+1) for i,q in enumerate(ids)])
    return dict(fetch_one('SELECT * FROM diagnostic_sessions WHERE id=?',(sid,),db_path))

def get_diagnostic_state(user_id:int,session_id:int|None=None,db_path:Path|str=DB_PATH):
    s=fetch_one('SELECT * FROM diagnostic_sessions WHERE id=? AND user_id=?',(session_id,user_id),db_path) if session_id else fetch_one('SELECT * FROM diagnostic_sessions WHERE user_id=? ORDER BY id DESC LIMIT 1',(user_id,),db_path)
    if not s:return None
    d=dict(s);d['items']=[dict(r) for r in fetch_all('SELECT * FROM diagnostic_items WHERE diagnostic_session_id=? ORDER BY display_order',(s['id'],),db_path)];return d

def answer_diagnostic(user_id:int,session_id:int,question_id:int,selected_codes:list[str]|None,numeric_answer:float|None,confidence:str,seconds:int,db_path:Path|str=DB_PATH):
    state=get_diagnostic_state(user_id,session_id,db_path);item=next((x for x in state['items'] if x['question_id']==question_id),None) if state else None
    if not item or item['answered']:raise ValueError('回答できない問題です。')
    result=record_answer(user_id,question_id,selected_codes,numeric_answer,confidence,seconds,'diagnostic',str(session_id),db_path)
    with connect(db_path) as conn:
        conn.execute('UPDATE diagnostic_items SET answered=1 WHERE id=?',(item['id'],));n=conn.execute('SELECT COUNT(*) n FROM diagnostic_items WHERE diagnostic_session_id=? AND answered=1',(session_id,)).fetchone()['n'];total=len(state['items']);conn.execute('UPDATE diagnostic_sessions SET current_index=? WHERE id=?',(n,session_id))
        if n>=total:conn.execute("UPDATE diagnostic_sessions SET status='completed',completed_at=? WHERE id=?",(utc_now(),session_id));conn.execute('UPDATE user_profiles SET diagnostic_completed=1 WHERE user_id=?',(user_id,))
    return result

def diagnostic_result(user_id:int,session_id:int,db_path:Path|str=DB_PATH):
    rows=fetch_all('''SELECT s.name subject_name,COUNT(*) total,SUM(a.is_correct) correct FROM answer_history a JOIN questions q ON q.id=a.question_id JOIN question_topic_mappings m ON m.question_id=q.id AND m.mapping_type='primary' JOIN topics t ON t.id=m.topic_id JOIN subjects s ON s.id=t.subject_id WHERE a.user_id=? AND a.answer_mode='diagnostic' AND a.session_id=? GROUP BY s.id ORDER BY s.display_order''',(user_id,str(session_id)),db_path);subjects=[]
    for r in rows:subjects.append({'subject_name':r['subject_name'],'total':r['total'],'correct':r['correct'],'accuracy':round(r['correct']/r['total']*100,1)})
    total=sum(x['total'] for x in subjects);correct=sum(x['correct'] for x in subjects);return {'total':total,'correct':correct,'accuracy':round(correct/total*100,1) if total else 0,'estimated_score':round(correct/total*180) if total else 0,'subjects':subjects,'weak_subjects':sorted(subjects,key=lambda x:x['accuracy'])[:3]}

def list_students_for_teacher(teacher_id:int,db_path:Path|str=DB_PATH):
    return [dict(r) for r in fetch_all('''SELECT u.id,p.display_name,p.grade,p.school_name,COUNT(a.id) answers,COALESCE(ROUND(AVG(a.is_correct)*100,1),0) accuracy FROM organization_memberships tm JOIN organization_memberships sm ON sm.organization_id=tm.organization_id AND sm.membership_role='student' JOIN users u ON u.id=sm.user_id JOIN user_profiles p ON p.user_id=u.id LEFT JOIN answer_history a ON a.user_id=u.id WHERE tm.user_id=? AND tm.membership_role='teacher' GROUP BY u.id ORDER BY p.display_name''',(teacher_id,),db_path)]

def teacher_can_access_student(teacher_id:int,student_id:int,db_path:Path|str=DB_PATH)->bool:
    row=fetch_one('''SELECT 1 FROM organization_memberships tm JOIN organization_memberships sm ON sm.organization_id=tm.organization_id AND sm.membership_role='student' WHERE tm.user_id=? AND tm.membership_role='teacher' AND sm.user_id=? LIMIT 1''',(teacher_id,student_id),db_path)
    return bool(row)

def get_student_summary_for_teacher(teacher_id:int,student_id:int,db_path:Path|str=DB_PATH):
    if not teacher_can_access_student(teacher_id,student_id,db_path):raise PermissionError('担当外の学生は閲覧できません。')
    row=fetch_one('''SELECT u.id,p.display_name,p.grade,p.school_name,COUNT(a.id) answers,COALESCE(SUM(a.is_correct),0) correct,COALESCE(ROUND(AVG(a.is_correct)*100,1),0) accuracy FROM users u JOIN user_profiles p ON p.user_id=u.id LEFT JOIN answer_history a ON a.user_id=u.id WHERE u.id=? AND u.role='student' GROUP BY u.id''',(student_id,),db_path)
    if not row:raise ValueError('学生が見つかりません。')
    return dict(row)

def create_assignment(teacher_id:int,title:str,description:str,question_ids:list[int],target_user_ids:list[int],due_at:str,db_path:Path|str=DB_PATH):
    if not title.strip():raise ValueError('課題名を入力してください。')
    if not question_ids:raise ValueError('問題を選択してください。')
    if not target_user_ids:raise ValueError('対象学生を選択してください。')
    for uid in target_user_ids:
        if not teacher_can_access_student(teacher_id,uid,db_path):raise PermissionError('担当外の学生は課題対象にできません。')
    published={r['id'] for r in fetch_all("SELECT id FROM questions WHERE status='published' AND id IN (%s)"%(','.join('?' for _ in question_ids)),question_ids,db_path)}
    if set(question_ids)!=published:raise ValueError('公開中の既存問題だけを課題にできます。')
    m=fetch_one("SELECT organization_id FROM organization_memberships WHERE user_id=? AND membership_role='teacher' LIMIT 1",(teacher_id,),db_path);aid=execute("INSERT INTO assignments(teacher_id,organization_id,title,description,start_at,due_at,status,created_at) VALUES(?,?,?,?,?,?,'published',?)",(teacher_id,m['organization_id'] if m else None,title,description,utc_now(),due_at,utc_now()),db_path)
    with connect(db_path) as conn:conn.executemany('INSERT INTO assignment_items(assignment_id,question_id,display_order) VALUES(?,?,?)',[(aid,q,i+1) for i,q in enumerate(question_ids)]);conn.executemany("INSERT INTO assignment_targets(assignment_id,user_id,status) VALUES(?,?,'not_started')",[(aid,u) for u in target_user_ids])
    return aid

def list_assignments_for_student(user_id:int,db_path:Path|str=DB_PATH):
    return [dict(r) for r in fetch_all('''SELECT a.id,a.title,a.description,a.due_at,a.status,at.status student_status,COUNT(ai.id) question_count FROM assignment_targets at JOIN assignments a ON a.id=at.assignment_id LEFT JOIN assignment_items ai ON ai.assignment_id=a.id WHERE at.user_id=? GROUP BY a.id ORDER BY a.due_at''',(user_id,),db_path)]

def list_assignment_results(teacher_id:int,assignment_id:int,db_path:Path|str=DB_PATH):
    a=fetch_one('SELECT * FROM assignments WHERE id=? AND teacher_id=?',(assignment_id,teacher_id),db_path)
    if not a:raise PermissionError('課題が見つからないか閲覧権限がありません。')
    return [dict(r) for r in fetch_all('''SELECT at.user_id,p.display_name,p.grade,COUNT(DISTINCT ai.question_id) assigned_questions,COUNT(ah.id) answers,COALESCE(ROUND(AVG(ah.is_correct)*100,1),0) accuracy,MAX(ah.answered_at) last_answered_at FROM assignment_targets at JOIN user_profiles p ON p.user_id=at.user_id JOIN assignment_items ai ON ai.assignment_id=at.assignment_id LEFT JOIN answer_history ah ON ah.user_id=at.user_id AND ah.question_id=ai.question_id WHERE at.assignment_id=? GROUP BY at.user_id ORDER BY p.display_name''',(assignment_id,),db_path)]

def assignment_results_csv(teacher_id:int,assignment_id:int,db_path:Path|str=DB_PATH)->str:
    rows=list_assignment_results(teacher_id,assignment_id,db_path);buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=['user_id','display_name','grade','assigned_questions','answers','accuracy','last_answered_at']);writer.writeheader();writer.writerows(rows);return buf.getvalue()
