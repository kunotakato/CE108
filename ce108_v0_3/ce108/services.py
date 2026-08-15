from __future__ import annotations
import csv, io, json, math, os, re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
from .config import DB_PATH, NOTE_OCR_MAX_BYTES, NOTE_OCR_PROVIDER
from .database import connect, execute, fetch_all, fetch_one, utc_now

CONFIDENCE_VALUES={'確実に分かる':1.0,'たぶん分かる':0.82,'迷った':0.58,'勘で答えた':0.35}
FOCUS_MODES={
    'medical': {'label':'医学重点','subjects':{'MED','CLIN'},'reason':'医学・臨床医学を8割へ近づけるために選びました。'},
    'engineering': {'label':'工学重点','subjects':{'EEE','MECH','MAT','SUP','THER','MEAS','SAFE'},'reason':'工学・装置・安全分野を固めるために選びました。'},
    'balanced': {'label':'バランス','subjects':set(),'reason':'全分野をバランスよく回すために選びました。'},
}
NOTE_TOPIC_KEYWORDS=[
    ('SUP-RESP',{'呼吸','換気','肺胞','酸素','co2','二酸化炭素','peep','fio2','人工呼吸'}),
    ('SUP-HD',{'透析','除水','拡散','限外濾過','膜','シャント'}),
    ('SUP-ECC',{'人工心肺','体外循環','act','ヘパリン','遠心ポンプ','人工肺'}),
    ('SAFE-ELEC',{'漏れ電流','接地','ミクロショック','電撃','安全'}),
    ('EEE-CIR',{'電圧','電流','抵抗','オーム','電力','回路'}),
    ('EEE-SIG',{'周波数','交流','コンデンサ','リアクタンス','インダクタンス'}),
    ('MECH-FLUID',{'圧力','流量','半径','粘度','流体'}),
    ('MEAS-SPO2',{'spo2','パルスオキシメータ','赤外光','脈波','酸素飽和度'}),
    ('CLIN-PATH',{'ショック','心不全','腎不全','病態','肺うっ血'}),
    ('MED-BIO',{'代謝','血糖','インスリン','ホルモン','アシドーシス'}),
    ('MED-ANAT',{'心臓','血圧','血液','腎','肺','神経','解剖','生理'}),
]

def _tz():
    try:return ZoneInfo(os.getenv('CE108_TIMEZONE','Asia/Tokyo'))
    except Exception:return ZoneInfo('Asia/Tokyo')

def _today()->date:
    return datetime.now(_tz()).date()

def _local_date(value:str)->date:
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    return dt.astimezone(_tz()).date() if dt.tzinfo else dt.date()

def authenticate_user(email:str,password:str,db_path:Path|str=DB_PATH):
    from .security import verify_password
    row=fetch_one('''SELECT u.*,p.display_name,p.grade,p.diagnostic_completed FROM users u JOIN user_profiles p ON p.user_id=u.id WHERE lower(u.email)=lower(?) AND u.status='active' ''',(email.strip(),),db_path)
    return dict(row) if row and verify_password(password,row['password_hash']) else None

def get_user(user_id:int,db_path:Path|str=DB_PATH):
    row=fetch_one('''SELECT u.id,u.email,u.line_user_id,u.role,u.status,p.display_name,p.school_name,p.grade,p.target_exam_year,p.daily_study_minutes,p.target_score,p.notification_time,p.diagnostic_completed FROM users u JOIN user_profiles p ON p.user_id=u.id WHERE u.id=?''',(user_id,),db_path)
    return dict(row) if row else None

def record_login_event(user:dict,db_path:Path|str=DB_PATH)->int:
    return execute('INSERT INTO login_events(user_id,role,email,logged_in_at) VALUES(?,?,?,?)',(user['id'],user['role'],user['email'],utc_now()),db_path)

def create_beta_student(email:str,password:str,display_name:str,grade:str='4年',school_name:str='CE108外部β',target_exam_year:int|None=None,db_path:Path|str=DB_PATH):
    from .security import hash_password
    email=(email or '').strip().lower()
    display_name=(display_name or '').strip()
    grade=(grade or '').strip() or '4年'
    school_name=(school_name or '').strip() or 'CE108外部β'
    if not email or '@' not in email:raise ValueError('メールアドレスを確認してください。')
    if len(password or '')<8:raise ValueError('パスワードは8文字以上にしてください。')
    if not display_name:raise ValueError('表示名を入力してください。')
    now=utc_now()
    with connect(db_path) as conn:
        exists=conn.execute('SELECT id FROM users WHERE lower(email)=lower(?)',(email,)).fetchone()
        if exists:raise ValueError('このメールアドレスは既に登録されています。')
        uid=conn.execute("INSERT INTO users(email,password_hash,role,status,created_at,updated_at) VALUES(?,?, 'student','active',?,?)",(email,hash_password(password),now,now)).lastrowid
        conn.execute('''INSERT INTO user_profiles(user_id,display_name,school_name,grade,target_exam_year,daily_study_minutes,target_score,notification_time,diagnostic_completed) VALUES(?,?,?,?,?,15,108,'20:00',0)''',(uid,display_name,school_name,grade,target_exam_year))
        org=conn.execute("SELECT id FROM organizations WHERE status='active' ORDER BY CASE WHEN name='CE108デモ養成校' THEN 0 ELSE 1 END,id LIMIT 1").fetchone()
        if not org:
            org_id=conn.execute("INSERT INTO organizations(name,organization_type,status,created_at) VALUES('CE108外部β','training_school','active',?)",(now,)).lastrowid
        else:
            org_id=org['id']
        conn.execute("INSERT OR IGNORE INTO organization_memberships(organization_id,user_id,class_name,academic_year,membership_role) VALUES(?,?, '外部β',?, 'student')",(org_id,uid,_today().year))
    return get_user(uid,db_path)

def set_user_password(email:str,password:str,db_path:Path|str=DB_PATH):
    from .security import hash_password
    email=(email or '').strip().lower()
    if not email or '@' not in email:raise ValueError('メールアドレスを確認してください。')
    if len(password or '')<8:raise ValueError('パスワードは8文字以上にしてください。')
    user=fetch_one('SELECT id FROM users WHERE lower(email)=lower(?)',(email,),db_path)
    if not user:raise ValueError('ユーザーが見つかりません。')
    execute('UPDATE users SET password_hash=?,updated_at=? WHERE id=?',(hash_password(password),utc_now(),user['id']),db_path)
    return get_user(user['id'],db_path)

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

def related_questions(user_id:int,question_id:int,limit:int=3,db_path:Path|str=DB_PATH):
    topic=fetch_one("SELECT topic_id FROM question_topic_mappings WHERE question_id=? AND mapping_type='primary'",(question_id,),db_path)
    if not topic:return []
    rows=fetch_all('''SELECT q.id,q.question_text,q.question_type,q.importance,s.name subject_name,t.name topic_name,
        EXISTS(SELECT 1 FROM answer_history a WHERE a.user_id=? AND a.question_id=q.id) answered
        FROM question_topic_mappings m
        JOIN questions q ON q.id=m.question_id
        JOIN topics t ON t.id=m.topic_id
        JOIN subjects s ON s.id=t.subject_id
        WHERE m.topic_id=? AND q.id<>? AND q.status='published'
        ORDER BY answered ASC,q.importance DESC,q.id LIMIT ?''',(user_id,topic['topic_id'],question_id,max(1,min(limit,10))),db_path)
    return [dict(r) for r in rows]

def _choice_feedback(q:dict,selected_codes:list[str]|None):
    selected=set(selected_codes or [])
    correct=set(q.get('correct_codes') or [])
    correct_text='・'.join(c['choice_text'] for c in q.get('choices',[]) if c.get('choice_code') in correct) or '正答'
    items=[]
    for choice in q.get('choices',[]):
        d=dict(choice)
        d['selected']=d['choice_code'] in selected
        d['is_correct']=bool(d.get('is_correct'))
        explanation=(d.get('explanation') or '').strip()
        if (not d['is_correct']) and ('本問の正答ではありません' in explanation or 'この選択肢は正答ではありません' in explanation):
            explanation=f'{d["choice_text"]}は、正答の「{correct_text}」と役割・条件が異なります。どの語が正答根拠とずれているかを確認しましょう。'
        if not explanation:
            if d['is_correct']:
                explanation=q.get('explanation_short') or 'この選択肢が正解です。'
            elif d['selected']:
                explanation=f'{d["choice_text"]}は、正答の「{correct_text}」と役割・条件が異なります。どの語が正答根拠とずれているかを確認しましょう。'
            else:
                explanation=f'{d["choice_text"]}は正答の「{correct_text}」ではありません。用語の意味と適用場面を区別して覚えましょう。'
        d['explanation']=explanation
        if d['choice_code'] in correct:
            d['feedback_label']='正答'
        elif d['choice_code'] in selected:
            d['feedback_label']='選んだ誤答'
        else:
            d['feedback_label']='誤答'
        items.append(d)
    return items

def _question_learning_point(q:dict)->str:
    subject=q.get('subject_name') or 'この分野'
    topic=q.get('topic_name') or '関連テーマ'
    importance=int(q.get('importance') or 3)
    standard=(q.get('explanation_standard') or q.get('explanation_short') or '').strip()
    cue=standard[:70]+'...' if len(standard)>70 else standard
    if cue:
        return f'{subject}「{topic}」で、正答根拠と誤答のずれを説明できるようにします。重要度{importance}/5。要点: {cue}'
    return f'{subject}「{topic}」で、正答根拠と誤答のずれを説明できるようにします。重要度{importance}/5。'

def _answer_statistics(question_id:int,db_path:Path|str=DB_PATH):
    r=fetch_one('SELECT COUNT(*) total,COALESCE(SUM(is_correct),0) correct FROM answer_history WHERE question_id=?',(question_id,),db_path)
    total=int(r['total'] or 0);correct=int(r['correct'] or 0)
    rate=round(correct/total*100,1) if total else None
    label=f'β内正答率 {rate}%（{total}件）' if total else 'β内正答率はまだ集計中'
    return {'total_answers':total,'correct_answers':correct,'correct_rate':rate,'label':label}

def _visual_aid(title:str,kind:str,steps:list[str],summary:str,formula:dict[str,str]|None=None)->dict[str,Any]:
    aid={'title':title,'kind':kind,'steps':steps[:6],'summary':summary}
    if formula:aid['formula']=formula
    return aid

def _question_visual_aid(q:dict)->dict[str,Any]:
    text=' '.join(str(q.get(k) or '') for k in ('question_text','explanation_short','explanation_standard','topic_name','subject_name')).lower()
    if any(k in text for k in ('洞房結節','房室結節','his束','purkinje','刺激伝導')):
        return _visual_aid('心臓の中で見る刺激伝導','anatomy',['右心房の洞房結節','房室結節で一度受ける','His束を通る','右脚・左脚に分かれる','Purkinje線維で心室へ広がる'],'洞房結節は右心房側にある最初のペースメーカーです。心臓の中の位置と伝わる順番を一緒に覚えます。')
    if any(k in text for k in ('肺胞','paco2','二酸化炭素','酸素','換気','拡散')):
        return _visual_aid('肺胞でのガス交換','exchange',['肺胞気','分圧差','肺胞膜','毛細血管','換気でCO2排出'],'肺胞と血液の間では、分圧差に沿って酸素と二酸化炭素が移動します。換気不足ではCO2が上がりやすくなります。')
    if 'p＝f/a' in text or 'p=f/a' in text or ('圧力' in text and 'pa' in text):
        return _visual_aid('圧力計算のイメージ','calculation',['力Fを確認','面積Aを確認','P=F/Aに代入','単位Paで答える'],'圧力は、同じ力でも面積が小さいほど大きくなります。力を面積で割る場面としてイメージします。',{'given':'F=100 N、A=0.02 m²','formula':'P = F / A','substitution':'100 / 0.02 = 5,000','result':'5,000 Pa'})
    if 't＝1/f' in text or 't=1/f' in text or ('周期' in text and 'hz' in text):
        return _visual_aid('周波数と周期のイメージ','calculation',['1秒間の波の数を見る','周期は1回分の時間','T=1/fに代入','秒で答える'],'Hzは1秒あたりの回数です。周期は1回にかかる時間なので、周波数の逆数になります。',{'given':'f=50 Hz','formula':'T = 1 / f','substitution':'1 / 50 = 0.02','result':'0.02 秒'})
    if 'p＝i²r' in text or 'p=i' in text and 'r' in text:
        return _visual_aid('電力計算のイメージ','calculation',['電流Iを確認','抵抗Rを確認','P=I²Rに代入','Wで答える'],'抵抗で消費される電力は、電流の二乗に比例します。電流を二乗してから抵抗を掛けます。',{'given':'I=0.5 A、R=10 Ω','formula':'P = I² R','substitution':'0.5² × 10 = 2.5','result':'2.5 W'})
    if any(k in text for k in ('腎小体','糸球体','原尿','濾過','腎')):
        return _visual_aid('腎小体の濾過','flow',['輸入細動脈','糸球体','濾過膜','Bowman嚢','原尿'],'血液から濾過膜を通って原尿が作られる流れを押さえると、腎機能の問題を整理しやすくなります。')
    if any(k in text for k in ('透析','限外濾過','除水','透析膜','シャント')):
        return _visual_aid('透析で起きる移動','exchange',['血液側','透析膜','透析液側','拡散','限外濾過'],'小分子は濃度差で拡散し、水分は圧差で限外濾過されます。何が何の差で動くかを分けて覚えます。')
    if any(k in text for k in ('ヘモグロビン','酸素運搬','血液')):
        return _visual_aid('酸素運搬の見取り図','flow',['肺胞','赤血球','ヘモグロビン','動脈血','組織'],'酸素は肺で血液に取り込まれ、主にヘモグロビンと結合して組織へ運ばれます。')
    return _visual_aid('正答根拠の見取り図','map',['問題文の条件','正答根拠','誤答との差分','次に解く関連問題'],'文章だけで終わらせず、条件・根拠・誤答との差分を一列に並べて確認します。')

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
    target=(_today()+timedelta(days=days)).isoformat()
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
    q['choice_feedback']=_choice_feedback(q,selected_codes)
    q['learning_point']=_question_learning_point(q)
    q['answer_statistics']=_answer_statistics(question_id,db_path)
    q['visual_aid']=_question_visual_aid(q)
    return {'is_correct':correct,'review_date':review,'question':q,'related_questions':related_questions(user_id,question_id,db_path=db_path)}

def _count(minutes:int)->int:return max(3,min(20,round(minutes/3)))

def generate_daily_plan(user_id:int,count:int|None=None,plan_date:str|None=None,db_path:Path|str=DB_PATH):
    plan_date=plan_date or _today().isoformat();user=get_user(user_id,db_path);count=count or _count(int(user['daily_study_minutes'] or 15))
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
    plan_date=plan_date or _today().isoformat();p=fetch_one('SELECT * FROM daily_study_plans WHERE user_id=? AND plan_date=?',(user_id,plan_date),db_path)
    if not p:return None
    items=fetch_all('''SELECT i.*,q.question_text,q.question_type,q.importance,s.name subject_name,t.name topic_name FROM daily_study_plan_items i JOIN questions q ON q.id=i.question_id LEFT JOIN question_topic_mappings m ON m.question_id=q.id AND m.mapping_type='primary' LEFT JOIN topics t ON t.id=m.topic_id LEFT JOIN subjects s ON s.id=t.subject_id WHERE i.plan_id=? ORDER BY i.display_order''',(p['id'],),db_path)
    answered={r['question_id'] for r in fetch_all("SELECT question_id,answered_at FROM answer_history WHERE user_id=? AND answer_mode='daily'",(user_id,),db_path) if _local_date(r['answered_at']).isoformat()==plan_date}
    d=dict(p);d['items']=[{**dict(r),'completed':r['question_id'] in answered} for r in items];return d

def get_focus_plan(user_id:int,mode:str='balanced',count:int=5,db_path:Path|str=DB_PATH):
    mode=mode if mode in FOCUS_MODES else 'balanced';cfg=FOCUS_MODES[mode];count=max(3,min(10,int(count or 5)))
    params=[user_id]
    where="WHERE q.status='published'"
    if cfg['subjects']:
        marks=','.join('?' for _ in cfg['subjects'])
        where+=f" AND s.code IN ({marks})";params.extend(sorted(cfg['subjects']))
    rows=[dict(r) for r in fetch_all(f'''SELECT q.id question_id,q.question_text,q.question_type,q.importance,q.frequency_score,s.name subject_name,s.code subject_code,t.name topic_name,COALESCE(m.mastery_score,0) mastery,EXISTS(SELECT 1 FROM answer_history a WHERE a.user_id=? AND a.question_id=q.id) answered FROM questions q JOIN question_topic_mappings tm ON tm.question_id=q.id AND tm.mapping_type='primary' JOIN topics t ON t.id=tm.topic_id JOIN subjects s ON s.id=t.subject_id LEFT JOIN user_topic_mastery m ON m.topic_id=t.id AND m.user_id=? {where} GROUP BY q.id ORDER BY answered ASC,((q.importance/5.0)*0.45 + MIN(1,q.frequency_score/3.0)*0.25 + (1-COALESCE(m.mastery_score,0)/100.0)*0.30) DESC,q.id LIMIT ?''',[user_id,*params,count],db_path)]
    items=[]
    for i,r in enumerate(rows,1):
        typ='苦手' if float(r['mastery'] or 0)<40 else ('必達' if int(r['importance'])>=4 else '新規')
        items.append({'id':i,'plan_id':0,'question_id':r['question_id'],'item_type':typ,'display_order':i,'reason':cfg['reason'],'question_text':r['question_text'],'question_type':r['question_type'],'importance':r['importance'],'subject_name':r['subject_name'],'topic_name':r['topic_name'],'completed':0})
    return {'id':0,'plan_date':_today().isoformat(),'mode':mode,'mode_label':cfg['label'],'recommended_count':len(items),'estimated_minutes':max(5,round(len(items)*2.5)),'status':'not_started','items':items}

def get_mastery_report(user_id:int,db_path:Path|str=DB_PATH):
    return [dict(r) for r in fetch_all('''SELECT s.name subject_name,t.name topic_name,COALESCE(m.mastery_score,0) mastery_score,COALESCE(m.retention_score,0) retention_score,COALESCE(m.total_answers,0) total_answers,COALESCE(m.correct_answers,0) correct_answers,m.last_answered_at FROM topics t JOIN subjects s ON s.id=t.subject_id LEFT JOIN user_topic_mastery m ON m.topic_id=t.id AND m.user_id=? ORDER BY mastery_score,s.display_order,t.display_order''',(user_id,),db_path)]

def get_learning_summary(user_id:int,db_path:Path|str=DB_PATH):
    r=fetch_one('SELECT COUNT(*) total,COALESCE(SUM(is_correct),0) correct,COALESCE(AVG(response_time_seconds),0) avg_seconds FROM answer_history WHERE user_id=?',(user_id,),db_path);due=fetch_one("SELECT COUNT(*) due FROM review_schedules WHERE user_id=? AND status='pending' AND scheduled_date<=?",(user_id,_today().isoformat()),db_path);total=int(r['total']);correct=int(r['correct']);return {'total':total,'correct':correct,'accuracy':round(correct/total*100,1) if total else 0,'avg_seconds':round(r['avg_seconds'],1),'due_reviews':due['due']}

def set_target_exam_date(user_id:int,target_exam_date:str,db_path:Path|str=DB_PATH):
    datetime.fromisoformat(target_exam_date)
    with connect(db_path) as conn:
        conn.execute('INSERT INTO student_exam_plans(user_id,target_exam_date,updated_at) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET target_exam_date=excluded.target_exam_date,updated_at=excluded.updated_at',(user_id,target_exam_date,utc_now()))
    return get_study_strategy(user_id,db_path)

def add_exam_event(user_id:int,event_type:str,title:str,event_date:str,memo:str='',db_path:Path|str=DB_PATH):
    if event_type not in {'mock','past_exam','real_exam'}:raise ValueError('予定種別が不正です。')
    if not title.strip():raise ValueError('予定名を入力してください。')
    datetime.fromisoformat(event_date)
    eid=execute("INSERT INTO exam_events(user_id,event_type,title,event_date,status,memo,created_at,updated_at) VALUES(?,?,?,?, 'scheduled',?,?,?)",(user_id,event_type,title.strip(),event_date,memo.strip() or None,utc_now(),utc_now()),db_path)
    return {'event_id':eid}

def add_score_record(user_id:int,score_type:str,title:str,taken_at:str,total_score:float,max_score:float,subject_scores:dict[str,float]|None=None,morning_score:float|None=None,afternoon_score:float|None=None,memo:str='',db_path:Path|str=DB_PATH):
    if score_type not in {'mock','past_exam'}:raise ValueError('スコア種別が不正です。')
    if not title.strip():raise ValueError('模試・過去問名を入力してください。')
    datetime.fromisoformat(taken_at)
    total_score=float(total_score);max_score=float(max_score)
    if max_score<=0 or total_score<0 or total_score>max_score:raise ValueError('総合点と満点を確認してください。')
    safe_scores={str(k):max(0,min(100,float(v))) for k,v in (subject_scores or {}).items() if str(k).strip()}
    sid=execute('''INSERT INTO score_records(user_id,score_type,title,taken_at,total_score,max_score,morning_score,afternoon_score,subject_scores,memo,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(user_id,score_type,title.strip(),taken_at,total_score,max_score,morning_score,afternoon_score,json.dumps(safe_scores,ensure_ascii=False),memo.strip() or None,utc_now()),db_path)
    return {'score_id':sid}

def _days_until(target:str|None)->int|None:
    if not target:return None
    return (datetime.fromisoformat(target).date()-_today()).days

def _phase(days:int|None)->str:
    if days is None:return 'undecided'
    if days<=30:return 'final'
    if days<=90:return 'push'
    return 'normal'

def get_study_strategy(user_id:int,db_path:Path|str=DB_PATH):
    plan=fetch_one('SELECT * FROM student_exam_plans WHERE user_id=?',(user_id,),db_path)
    events=[dict(r) for r in fetch_all("SELECT * FROM exam_events WHERE user_id=? ORDER BY event_date LIMIT 10",(user_id,),db_path)]
    latest=fetch_one('SELECT * FROM score_records WHERE user_id=? ORDER BY taken_at DESC,id DESC LIMIT 1',(user_id,),db_path)
    mastery=get_mastery_report(user_id,db_path)
    subject_rows=fetch_all('''SELECT s.name subject_name,s.code subject_code,COALESCE(SUM(m.correct_answers),0) correct,COALESCE(SUM(m.total_answers),0) total,COALESCE(AVG(m.mastery_score),0) mastery FROM subjects s LEFT JOIN topics t ON t.subject_id=s.id LEFT JOIN user_topic_mastery m ON m.topic_id=t.id AND m.user_id=? GROUP BY s.id ORDER BY s.display_order''',(user_id,),db_path)
    score_subjects=json.loads(latest['subject_scores']) if latest and latest['subject_scores'] else {}
    radar=[]
    for r in subject_rows:
        answers=int(r['total'] or 0);accuracy=round(int(r['correct'] or 0)/answers*100,1) if answers else 0
        score_rate=score_subjects.get(r['subject_name'],score_subjects.get(r['subject_code']))
        value=round((float(score_rate)*0.65+accuracy*0.35),1) if score_rate is not None else (round(float(r['mastery'] or 0),1) if answers else 0)
        radar.append({'subject_code':r['subject_code'],'subject_name':r['subject_name'],'value':value,'accuracy':accuracy,'mock_score':score_rate,'answers':answers})
    days=_days_until(plan['target_exam_date'] if plan else None);phase=_phase(days)
    weak=sorted(radar,key=lambda x:x['value'])[:3];strong=sorted(radar,key=lambda x:x['value'],reverse=True)[:3]
    recommended='balanced'
    med=sum(x['value'] for x in radar if x['subject_code'] in {'MED','CLIN'})/max(1,len([x for x in radar if x['subject_code'] in {'MED','CLIN'}]))
    eng=sum(x['value'] for x in radar if x['subject_code'] not in {'MED','CLIN'})/max(1,len([x for x in radar if x['subject_code'] not in {'MED','CLIN'}]))
    if phase=='final':recommended='medical' if med>=eng else 'engineering'
    elif med<75:recommended='medical'
    elif eng<75:recommended='engineering'
    return {'target_exam_date':plan['target_exam_date'] if plan else None,'days_until_exam':days,'phase':phase,'phase_label':{'undecided':'試験日未設定','normal':'通常期','push':'追い込み期','final':'直前期'}[phase],'recommended_mode':recommended,'recommendation':('直前期は得意分野と頻出分野を固めましょう。' if phase=='final' else '苦手分野を優先して底上げしましょう。'),'events':events,'latest_score':dict(latest) if latest else None,'radar':radar,'weak_subjects':weak,'strong_subjects':strong,'weak_topics':mastery[:5]}

def list_due_reviews(user_id:int,db_path:Path|str=DB_PATH):
    return [dict(r) for r in fetch_all('''SELECT r.scheduled_date,r.priority,q.id question_id,q.question_text,s.name subject_name,t.name topic_name FROM review_schedules r JOIN questions q ON q.id=r.question_id LEFT JOIN question_topic_mappings m ON m.question_id=q.id AND m.mapping_type='primary' LEFT JOIN topics t ON t.id=m.topic_id LEFT JOIN subjects s ON s.id=t.subject_id WHERE r.user_id=? AND r.status='pending' ORDER BY r.scheduled_date,r.priority DESC''',(user_id,),db_path)]

def _iso_date(value:str)->date:
    return _local_date(value)

def _answer_dates(user_id:int,db_path:Path|str=DB_PATH)->list[date]:
    rows=fetch_all("SELECT answered_at FROM answer_history WHERE user_id=? ORDER BY answered_at DESC",(user_id,),db_path)
    return sorted({_local_date(r['answered_at']) for r in rows if r['answered_at']},reverse=True)

def _streak(dates:list[date],today:date)->int:
    done=set(dates);cur=today;count=0
    while cur in done:
        count+=1;cur-=timedelta(days=1)
    return count

def get_daily_status(user_id:int,db_path:Path|str=DB_PATH):
    today=_today();plan=generate_daily_plan(user_id,db_path=db_path);items=plan.get('items',[]) if plan else []
    completed=sum(1 for i in items if i.get('completed'));total=len(items);dates=_answer_dates(user_id,db_path)
    week_start=today-timedelta(days=6);week=[{'date':(week_start+timedelta(days=i)).isoformat(),'completed':(week_start+timedelta(days=i)) in set(dates)} for i in range(7)]
    due=fetch_one("SELECT COUNT(*) due FROM review_schedules WHERE user_id=? AND status='pending' AND scheduled_date<=?",(user_id,today.isoformat()),db_path)
    tomorrow_count=fetch_one("SELECT COUNT(*) n FROM review_schedules WHERE user_id=? AND status='pending' AND scheduled_date=?",(user_id,(today+timedelta(days=1)).isoformat()),db_path)
    status='completed' if total and completed>=total else ('in_progress' if completed else 'not_started')
    return {'date':today.isoformat(),'status':status,'completed_count':completed,'total_count':total,'estimated_minutes':plan.get('estimated_minutes',0) if plan else 0,'streak_days':_streak(dates,today),'weekly':week,'due_reviews':int(due['due']),'tomorrow_preview':{'review_count':int(tomorrow_count['n']),'message':'明日は復習から始めましょう。' if tomorrow_count['n'] else '明日も今日のペースで5問進めましょう。'},'next_action':'復習から始める' if int(due['due']) else ('続きから再開' if status=='in_progress' else '今日の5問を始める')}

def get_review_queue(user_id:int,limit:int=20,db_path:Path|str=DB_PATH):
    today=_today().isoformat();rows=fetch_all('''SELECT r.id review_id,r.scheduled_date,r.priority,r.status,q.id question_id,q.question_text,q.question_type,s.name subject_name,t.name topic_name,EXISTS(SELECT 1 FROM answer_history a WHERE a.user_id=r.user_id AND a.question_id=r.question_id AND substr(a.answered_at,1,10)>=r.scheduled_date) completed FROM review_schedules r JOIN questions q ON q.id=r.question_id LEFT JOIN question_topic_mappings m ON m.question_id=q.id AND m.mapping_type='primary' LEFT JOIN topics t ON t.id=m.topic_id LEFT JOIN subjects s ON s.id=t.subject_id WHERE r.user_id=? AND r.status='pending' AND q.status='published' ORDER BY CASE WHEN r.scheduled_date<=? THEN 0 ELSE 1 END,r.scheduled_date,r.priority DESC LIMIT ?''',(user_id,today,max(1,min(limit,100))),db_path)
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

def _feedback_priority(r:dict)->str:
    message=(r.get('message') or '').lower()
    urgent_words={'failed','fetch','error','エラー','ログインできない','動かない','開けない','回答できない','保存できない','消え','落ちる','真っ白'}
    if r.get('category')=='不具合' or int(r.get('rating') or 0)<=2 or any(w in message for w in urgent_words):return '高'
    if int(r.get('rating') or 0)==3 or r.get('category') in {'問題・解説','要望'}:return '中'
    return '低'

def list_beta_feedback(limit:int=200,db_path:Path|str=DB_PATH):
    rows=fetch_all('''SELECT f.id,f.rating,f.category,f.message,f.page_url,f.user_agent,f.created_at,u.email,p.display_name
        FROM beta_feedback f
        JOIN users u ON u.id=f.user_id
        JOIN user_profiles p ON p.user_id=u.id
        ORDER BY f.created_at DESC,f.id DESC
        LIMIT ?''',(max(1,min(int(limit or 200),1000)),),db_path)
    items=[]
    for row in rows:
        d=dict(row);d['priority']=_feedback_priority(d);items.append(d)
    return items

def get_beta_feedback_summary(db_path:Path|str=DB_PATH):
    items=list_beta_feedback(1000,db_path)
    counts={'高':0,'中':0,'低':0}
    categories={}
    pages={}
    for item in items:
        counts[item['priority']]+=1
        categories[item['category']]=categories.get(item['category'],0)+1
        page=item.get('page_url') or '未記録'
        pages[page]=pages.get(page,0)+1
    avg=round(sum(int(i['rating']) for i in items)/len(items),2) if items else 0
    return {'total':len(items),'avg_rating':avg,'priority_counts':counts,'category_counts':categories,'page_counts':pages,'items':items}

def get_beta_tester_activity(limit:int=200,db_path:Path|str=DB_PATH):
    rows=fetch_all('''SELECT u.id,u.email,p.display_name,p.school_name,p.grade,
        MAX(l.logged_in_at) last_login_at,
        COUNT(DISTINCT l.id) login_count,
        COUNT(DISTINCT a.id) answer_count,
        COALESCE(ROUND(AVG(a.is_correct)*100,1),0) accuracy,
        COUNT(DISTINCT f.id) feedback_count,
        MAX(f.created_at) last_feedback_at
        FROM users u
        JOIN user_profiles p ON p.user_id=u.id
        LEFT JOIN login_events l ON l.user_id=u.id
        LEFT JOIN answer_history a ON a.user_id=u.id
        LEFT JOIN beta_feedback f ON f.user_id=u.id
        WHERE u.role='student' AND (p.school_name LIKE '%外部β%' OR u.email NOT LIKE '%@ce108.local')
        GROUP BY u.id
        ORDER BY COALESCE(last_login_at,'') DESC,u.id DESC
        LIMIT ?''',(max(1,min(int(limit or 200),1000)),),db_path)
    items=[]
    for r in rows:
        d=dict(r)
        d['status_label']='フィードバック済み' if int(d['feedback_count'] or 0)>0 else ('回答済み' if int(d['answer_count'] or 0)>0 else ('ログイン済み' if d['last_login_at'] else '未ログイン'))
        items.append(d)
    return items

def get_teacher_support_summary(teacher_id:int,db_path:Path|str=DB_PATH):
    students=list_students_for_teacher(teacher_id,db_path);today=_today();rows=[]
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

def create_student_note(user_id:int,title:str,content:str,source_type:str='manual_note',db_path:Path|str=DB_PATH)->int:
    title=(title or '').strip() or '無題ノート'
    content=(content or '').strip()
    if len(content)<20:raise ValueError('ノート本文は20文字以上入力してください。')
    if len(content)>20000:raise ValueError('v0.4.1ではノート本文は20,000文字以内です。')
    return execute('INSERT INTO student_notes(user_id,title,content,source_type,created_at,updated_at) VALUES(?,?,?,?,?,?)',(user_id,title,content,source_type,utc_now(),utc_now()),db_path)

def list_student_notes(user_id:int,db_path:Path|str=DB_PATH):
    return [dict(r) for r in fetch_all('''SELECT n.*,COUNT(q.id) generated_question_count FROM student_notes n LEFT JOIN note_generated_questions q ON q.note_id=n.id WHERE n.user_id=? GROUP BY n.id ORDER BY n.created_at DESC''',(user_id,),db_path)]

TEXT_UPLOAD_EXTENSIONS={'.txt','.md','.markdown','.csv'}
TEXT_UPLOAD_TYPES={'text/plain','text/markdown','text/csv','application/csv','application/vnd.ms-excel'}
OCR_UPLOAD_EXTENSIONS={'.png','.jpg','.jpeg','.webp','.heic','.pdf'}

def extract_note_upload_text(user_id:int,filename:str,content_type:str|None,data:bytes,db_path:Path|str=DB_PATH):
    name=(filename or 'upload').strip()
    suffix=Path(name).suffix.lower()
    mime=(content_type or '').split(';')[0].strip().lower()
    if not data:
        raise ValueError('ファイルが空です。ノート本文が入ったファイルを選んでください。')
    if len(data)>NOTE_OCR_MAX_BYTES:
        mb=max(1,round(NOTE_OCR_MAX_BYTES/1024/1024))
        current=round(len(data)/1024/1024,1)
        raise ValueError(f'ファイルサイズが大きすぎます（約{current}MB）。{mb}MB以内の写真・PDFにしてください。写真を1枚に絞る、スクリーンショットを切り抜く、または本文をテキストで貼り付けてください。')
    is_text=mime.startswith('text/') or mime in TEXT_UPLOAD_TYPES or suffix in TEXT_UPLOAD_EXTENSIONS
    if is_text:
        try:
            text=data.decode('utf-8-sig')
        except UnicodeDecodeError:
            text=data.decode('utf-8',errors='replace')
        text=text.replace('\x00','').strip()
        if len(text)<20:
            raise ValueError('抽出した本文が短すぎます。20文字以上の学習メモを読み込んでください。')
        if len(text)>20000:
            text=text[:20000]
            warning='20,000文字を超えたため、先頭20,000文字だけを読み込みました。'
        else:
            warning=''
        return {'filename':name,'content_type':mime or 'text/plain','source_type':'uploaded_text','text':text,'warning':warning}
    is_ocr_target=mime.startswith('image/') or mime=='application/pdf' or suffix in OCR_UPLOAD_EXTENSIONS
    if is_ocr_target:
        if NOTE_OCR_PROVIDER in {'', 'disabled', 'none', 'off'}:
            raise ValueError('写真・PDFの読み取りは準備中です。今はノート本文を直接貼り付けるか、.txt/.md/.csvファイルで読み込んでください。OCRを有効化すると写真から問題作成できるようになります。')
        raise ValueError(f'NOTE_OCR_PROVIDER={NOTE_OCR_PROVIDER}はまだ接続実装前です。外部AIへ送信する前に、同意文言・保存期間・監査ログを確定してください。')
    raise ValueError('対応していないファイル形式です。.txt、.md、.csv、写真、PDFを選んでください。')

def _note_topic(content:str)->str:
    lowered=content.lower()
    best=('MED-ANAT',0)
    for topic,words in NOTE_TOPIC_KEYWORDS:
        score=sum(1 for word in words if word in lowered)
        if score>best[1]:best=(topic,score)
    return best[0]

def _important_sentences(content:str,count:int)->list[str]:
    parts=[p.strip(' ・\n\t') for p in re.split(r'[。．\n]+',content) if p.strip()]
    def score(sentence:str):
        keywords=['重要','必要','注意','原因','目的','主','低下','上昇','リスク','管理','設定','評価','確認']
        return len(sentence)+sum(80 for k in keywords if k in sentence)
    return sorted(parts,key=score,reverse=True)[:max(1,count)]

def _note_question(sentence:str,topic_code:str,index:int)->dict[str,Any]:
    clean=sentence[:120]
    choices=['ノート本文の重要点として正しい','似た用語だが本文の主旨と異なる','原因と結果を逆にしている','別分野の知識を混同している','本文では判断できない内容を断定している']
    explanations=[
        f'本文の中心は「{clean}」です。この文を自分の言葉で説明できることが学習目標です。',
        f'この選択肢は用語だけ近くても、本文の中心である「{clean}」の条件や結論を示していません。',
        f'本文は「{clean}」という流れで説明しています。原因と結果を逆にすると判断手順が崩れます。',
        f'別分野の知識を混ぜると、本文で確認したい「{clean}」から外れます。まず本文内の根拠で判断します。',
        f'本文に書かれていない内容を断定すると、ノートから確認できる根拠を超えます。復習では根拠のある範囲に絞ります。',
    ]
    return {
        'question_type':'single',
        'question_text':f'ノートAI問題{index}: 次のメモの要点として最も適切なのはどれか。「{clean}」',
        'choices':choices,
        'correct_code':'1',
        'choice_explanations':explanations,
        'explanation':f'この問題で学ぶことは、ノートの重要文「{clean}」を根拠に、正答と誤答のずれを説明できるようにすることです。既存の国家試験問題ではなく、復習用のオリジナル問題です。',
        'topic_code':topic_code,
    }

def _note_answer_statistics(question_id:int,db_path:Path|str=DB_PATH):
    r=fetch_one('SELECT COUNT(*) total,COALESCE(SUM(is_correct),0) correct FROM note_question_answers WHERE note_question_id=?',(question_id,),db_path)
    total=int(r['total'] or 0);correct=int(r['correct'] or 0)
    rate=round(correct/total*100,1) if total else None
    label=f'ノート問題の正答率 {rate}%（{total}件）' if total else 'ノート問題の正答率はまだ集計中'
    return {'total_answers':total,'correct_answers':correct,'correct_rate':rate,'label':label}

def _note_visual_aid(q:dict)->dict[str,Any]:
    topic=(q.get('topic_code') or '').upper()
    if topic in {'SUP-RESP','MED-ANAT'}:
        return _visual_aid('ノートから作った呼吸・生理マップ','exchange',['ノート本文','重要文','体内で起きる変化','正答根拠','誤答との差分'],'メモの一文を、体内の変化や因果関係へつなげて理解します。')
    if topic=='SUP-HD':
        return _visual_aid('ノートから作った透析マップ','exchange',['ノート本文','血液側','透析膜','透析液側','移動の理由'],'透析のメモは、どちら側からどちら側へ何が動くかを図で分けます。')
    return _visual_aid('ノート重要文マップ','map',['ノート本文','AIが選んだ重要文','正答根拠','誤答との差分'],'ノートの重要文を出発点に、正答と誤答の違いを短い流れで確認します。')

def generate_note_questions(user_id:int,note_id:int,count:int=5,db_path:Path|str=DB_PATH):
    note=fetch_one('SELECT * FROM student_notes WHERE id=? AND user_id=?',(note_id,user_id),db_path)
    if not note:raise ValueError('ノートが見つかりません。')
    count=max(1,min(int(count or 5),10))
    topic=_note_topic(note['content'])
    sentences=_important_sentences(note['content'],count)
    created=[]
    with connect(db_path) as conn:
        for i,sentence in enumerate(sentences,1):
            draft=_note_question(sentence,topic,i)
            exists=conn.execute('SELECT id FROM note_generated_questions WHERE note_id=? AND question_text=?',(note_id,draft['question_text'])).fetchone()
            if exists:
                created.append(dict(conn.execute('SELECT * FROM note_generated_questions WHERE id=?',(exists['id'],)).fetchone()))
                continue
            qid=conn.execute('''INSERT INTO note_generated_questions(note_id,user_id,question_type,question_text,choices,correct_code,choice_explanations,explanation,topic_code,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,'active',?)''',(note_id,user_id,draft['question_type'],draft['question_text'],json.dumps(draft['choices'],ensure_ascii=False),draft['correct_code'],json.dumps(draft['choice_explanations'],ensure_ascii=False),draft['explanation'],draft['topic_code'],utc_now())).lastrowid
            created.append(dict(conn.execute('SELECT * FROM note_generated_questions WHERE id=?',(qid,)).fetchone()))
    return {'note_id':note_id,'generated_count':len(created),'questions':[format_note_question(q,answered=False,db_path=db_path) for q in created]}

def format_note_question(row:dict|Any,answered:bool=False,include_answer:bool=False,db_path:Path|str=DB_PATH):
    q=dict(row)
    choices=json.loads(q.pop('choices'))
    explanations=json.loads(q.pop('choice_explanations'))
    q['choices']=[{'choice_code':str(i+1),'choice_text':text,'display_order':i+1} for i,text in enumerate(choices)]
    q['answered']=answered
    if include_answer:
        q['correct_code']=q.get('correct_code','1')
        q['choice_feedback']=[{**choice,'is_correct':choice['choice_code']==q['correct_code'],'explanation':explanations[i] if i<len(explanations) else ''} for i,choice in enumerate(q['choices'])]
        q['learning_point']='ノート本文の重要文を根拠に、正答と誤答のどこがずれているかを説明できるようにします。'
        q['answer_statistics']=_note_answer_statistics(q['id'],db_path)
        q['visual_aid']=_note_visual_aid(q)
    else:
        q.pop('correct_code',None);q.pop('explanation',None)
    return q

def list_note_questions(user_id:int,note_id:int,db_path:Path|str=DB_PATH):
    note=fetch_one('SELECT id FROM student_notes WHERE id=? AND user_id=?',(note_id,user_id),db_path)
    if not note:raise ValueError('ノートが見つかりません。')
    rows=fetch_all('''SELECT q.*,EXISTS(SELECT 1 FROM note_question_answers a WHERE a.user_id=? AND a.note_question_id=q.id) answered FROM note_generated_questions q WHERE q.user_id=? AND q.note_id=? AND q.status='active' ORDER BY q.id''',(user_id,user_id,note_id),db_path)
    return [format_note_question(r,answered=bool(r['answered']),db_path=db_path) for r in rows]

def get_note_question(user_id:int,question_id:int,db_path:Path|str=DB_PATH):
    row=fetch_one("SELECT * FROM note_generated_questions WHERE id=? AND user_id=? AND status='active'",(question_id,user_id),db_path)
    if not row:raise ValueError('ノート問題が見つかりません。')
    return format_note_question(row,db_path=db_path)

def answer_note_question(user_id:int,question_id:int,selected_code:str,confidence:str,seconds:int,db_path:Path|str=DB_PATH):
    row=fetch_one("SELECT * FROM note_generated_questions WHERE id=? AND user_id=? AND status='active'",(question_id,user_id),db_path)
    if not row:raise ValueError('ノート問題が見つかりません。')
    selected=(selected_code or '').strip()
    if not selected:raise ValueError('選択肢を選んでください。')
    correct=selected==row['correct_code']
    execute('INSERT INTO note_question_answers(user_id,note_question_id,selected_code,is_correct,confidence_level,response_time_seconds,answered_at) VALUES(?,?,?,?,?,?,?)',(user_id,question_id,selected,int(correct),confidence,max(0,int(seconds)),utc_now()),db_path)
    q=format_note_question(row,include_answer=True,db_path=db_path)
    for choice in q['choice_feedback']:choice['selected']=choice['choice_code']==selected
    return {'is_correct':correct,'question':q}

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
