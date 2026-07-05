from __future__ import annotations
import time
from datetime import date,datetime,timedelta
import pandas as pd
import streamlit as st
from ce108.admin_service import approve_question,create_question,import_questions_csv,unpublish_question
from ce108.config import DATA_DIR
from ce108.database import fetch_all,fetch_one
from ce108.seed import export_question_template,seed_database
from ce108.services import *

st.set_page_config(page_title='CE108｜臨床工学技士国試AI',page_icon='🫀',layout='wide')
st.markdown('''<style>.block-container{padding-top:1.2rem}.hero{padding:22px;border-radius:18px;background:linear-gradient(120deg,#092b55,#1268b3,#27a4a1);color:#fff;margin-bottom:18px}.hero h1{margin:0}.badge{display:inline-block;padding:3px 9px;border-radius:99px;background:#e7f2ff;color:#075aa7;font-weight:700}[data-testid="stMetric"]{border:1px solid #dbe7f3;padding:12px;border-radius:14px;background:white}</style>''',unsafe_allow_html=True)
seed_database();export_question_template()
for k,v in {'user_id':None,'daily_reveal':False,'daily_result':None,'daily_started':None,'diag_reveal':False,'diag_result':None,'diag_started':None}.items():st.session_state.setdefault(k,v)

def hero(t,s):st.markdown(f'<div class="hero"><h1>{t}</h1><p>{s}</p></div>',unsafe_allow_html=True)
def logout():
    for k in list(st.session_state):del st.session_state[k]
    st.rerun()
def render_question(q,key):
    st.markdown(f'<span class="badge">{q.get("subject_name") or "未分類"}｜{q.get("topic_name") or "未分類"}</span>',unsafe_allow_html=True);st.markdown('### '+q['question_text']);selected=[];num=None
    if q['question_type']=='numeric':num=st.number_input(f'数値を入力（単位：{q.get("unit") or "指定なし"}）',value=None,key=key+'n')
    elif q['question_type']=='multiple':
        ops={f"{c['choice_code']}. {c['choice_text']}":c['choice_code'] for c in q['choices']};labels=st.multiselect('正しいものを選択',list(ops),key=key+'m');selected=[ops[x] for x in labels]
    else:
        ops={f"{c['choice_code']}. {c['choice_text']}":c['choice_code'] for c in q['choices']};label=st.radio('回答を選択',list(ops),index=None,key=key+'s');selected=[ops[label]] if label else []
    conf=st.radio('自信度',['確実に分かる','たぶん分かる','迷った','勘で答えた'],horizontal=True,index=1,key=key+'c');return selected,num,conf
def explain(r):
    q=r['question']
    st.markdown(f'<span class="badge">{q.get("subject_name") or "未分類"}｜{q.get("topic_name") or "未分類"}</span>',unsafe_allow_html=True);st.markdown('### '+q['question_text'])
    if r['is_correct']:st.success('正解です。')
    else:st.error('不正解です。')
    if q['question_type']=='numeric':st.markdown(f"**正答：{q['numeric_answer']} {q.get('unit') or ''}**")
    else:st.markdown('**正答：** '+ '、'.join(f"{c['choice_code']}. {c['choice_text']}" for c in q['choices'] if c['is_correct']))
    st.write('**要点：** '+q['explanation_short']);
    with st.expander('標準解説',expanded=True):st.write(q['explanation_standard'])
    with st.expander('基礎から詳しく'):st.write(q['explanation_detailed'])
    st.caption('次回復習予定：'+r['review_date'])

def login():
    hero('CE108','AIが、今やるべき国試問題を選ぶ。');st.info('収録問題はCE108オリジナルサンプルです。過去問原文は権利確認後に登録してください。')
    a,b=st.columns(2)
    with a:
        e=st.text_input('メールアドレス',value='student@ce108.local');p=st.text_input('パスワード',value='demo1234',type='password')
        if st.button('ログイン',type='primary',width='stretch'):
            u=authenticate_user(e,p)
            if u:st.session_state.user_id=u['id'];st.rerun()
            st.error('ログイン情報が違います。')
    with b:st.code('学生: student@ce108.local\n教員: teacher@ce108.local\n管理者: admin@ce108.local\n共通: demo1234')

def student_home(u):
    hero(f"{u['display_name']}さんの学習ホーム",'毎日続けるための今日の状態、復習、理解度を確認します。');s=get_learning_summary(u['id']);d=get_daily_status(u['id']);c=st.columns(4);c[0].metric('連続学習',f"{d['streak_days']}日");c[1].metric('正答率',f"{s['accuracy']}%");c[2].metric('復習待ち',f"{d['due_reviews']}問");c[3].metric('平均回答時間',f"{s['avg_seconds']}秒")
    p=generate_daily_plan(u['id']);done=sum(int(x['completed']) for x in p['items']);st.subheader('今日の学習');st.progress(done/max(1,len(p['items'])));st.write(f"{done}/{len(p['items'])}問完了｜目安{p['estimated_minutes']}分｜次：{d['next_action']}");st.caption(d['tomorrow_preview']['message'])
    for x in p['items']:st.write(('✅' if x['completed'] else '⬜')+f" **{x['item_type']}**｜{x['subject_name']}｜{x['reason']}")

def student_daily(u):
    hero('今日の問題','復習・必達・苦手・新規問題を組み合わせます。');p=generate_daily_plan(u['id']);pending=[x for x in p['items'] if not x['completed']]
    if st.session_state.daily_reveal and st.session_state.daily_result:
        explain(st.session_state.daily_result)
        if st.button('次の問題へ',type='primary'):st.session_state.daily_reveal=False;st.session_state.daily_result=None;st.session_state.daily_started=time.time();st.rerun()
        return
    if not pending:st.success('今日の問題は完了しました。');return
    item=pending[0];q=get_question(item['question_id']);st.caption(f"{item['item_type']}｜{item['reason']}");st.session_state.daily_started=st.session_state.daily_started or time.time();sel,num,conf=render_question(q,'d'+str(q['id']))
    if st.button('回答を確定',type='primary'):
        if (q['question_type']=='numeric' and num is None) or (q['question_type']!='numeric' and not sel):st.warning('回答を入力してください。')
        else:st.session_state.daily_result=record_answer(u['id'],q['id'],sel,num,conf,round(time.time()-st.session_state.daily_started),'daily');st.session_state.daily_reveal=True;st.rerun()

def student_diag(u):
    hero('初回30問診断','基礎医学・工学・主要領域を横断して現在地を推定します。');s=get_diagnostic_state(u['id'])
    if not s:
        st.write('目安20〜30分。回答済みデータは保存されます。')
        if st.button('診断を開始',type='primary'):start_diagnostic(u['id']);st.session_state.diag_started=time.time();st.rerun()
        return
    if s['status']=='completed':
        r=diagnostic_result(u['id'],s['id']);c=st.columns(3);c[0].metric('正答率',f"{r['accuracy']}%");c[1].metric('参考換算点',f"{r['estimated_score']}/180");c[2].metric('正解数',f"{r['correct']}/{r['total']}");st.caption('参考換算点はサンプル30問の単純換算で、実際の合格予測ではありません。');df=pd.DataFrame(r['subjects'])
        if not df.empty:st.bar_chart(df.set_index('subject_name')['accuracy'])
        for x in r['weak_subjects']:st.warning(f"{x['subject_name']}：{x['accuracy']}%")
        return
    if st.session_state.diag_reveal and st.session_state.diag_result:
        explain(st.session_state.diag_result)
        if st.button('次へ',type='primary'):st.session_state.diag_reveal=False;st.session_state.diag_result=None;st.session_state.diag_started=time.time();st.rerun()
        return
    pending=[x for x in s['items'] if not x['answered']];q=get_question(pending[0]['question_id']);answered=len(s['items'])-len(pending);st.progress(answered/len(s['items']));st.caption(f"{answered+1}/{len(s['items'])}");st.session_state.diag_started=st.session_state.diag_started or time.time();sel,num,conf=render_question(q,'g'+str(q['id']))
    if st.button('診断回答を確定',type='primary'):
        if (q['question_type']=='numeric' and num is None) or (q['question_type']!='numeric' and not sel):st.warning('回答を入力してください。')
        else:st.session_state.diag_result=answer_diagnostic(u['id'],s['id'],q['id'],sel,num,conf,round(time.time()-st.session_state.diag_started));st.session_state.diag_reveal=True;st.rerun()

def mastery(u):
    hero('苦手・得意分析','正誤、自信度、回答時間から理解度を更新します。');df=pd.DataFrame(get_mastery_report(u['id']));
    if df.empty:st.info('データがありません。');return
    df['正答率']=df.apply(lambda r:round(r.correct_answers/r.total_answers*100,1) if r.total_answers else 0,axis=1);st.dataframe(df[['subject_name','topic_name','mastery_score','retention_score','total_answers','正答率']].rename(columns={'subject_name':'科目','topic_name':'分野','mastery_score':'理解度','retention_score':'定着度','total_answers':'回答数'}),width='stretch',hide_index=True);st.bar_chart(df.set_index('topic_name')['mastery_score'])
def reviews(u):
    hero('復習予定','今日・期限超過・今後の復習を確認します。');q=get_review_queue(u['id'])
    if q['items']:st.dataframe(pd.DataFrame(q['items']),width='stretch',hide_index=True)
    else:st.info('復習予定はありません。')
def history(u):
    hero('学習履歴','日別の回答数と正答率です。');r=fetch_all("SELECT date(answered_at) day,COUNT(*) answers,ROUND(AVG(is_correct)*100,1) accuracy FROM answer_history WHERE user_id=? GROUP BY date(answered_at) ORDER BY day DESC",(u['id'],))
    if r:st.dataframe(pd.DataFrame([dict(x) for x in r]),width='stretch',hide_index=True)
    else:st.info('履歴がありません。')
def assignments(u):
    hero('教員からの課題','配信された課題を確認します。');r=list_assignments_for_student(u['id'])
    if r:st.dataframe(pd.DataFrame(r),width='stretch',hide_index=True)
    else:st.info('課題はありません。')

def teacher_dash(u):
    hero('教員ダッシュボード','担当学生の継続状況と要注意度を確認します。');r=get_teacher_support_summary(u['id'])
    if r:
        df=pd.DataFrame([{k:v for k,v in x.items() if k!='weak_topics'} for x in r]);st.dataframe(df,width='stretch',hide_index=True)
    else:st.info('担当学生がいません。')
def teacher_task(u):
    hero('課題作成','既存問題から課題を配信します。');ss=list_students_for_teacher(u['id']);qs=list_questions(limit=200);so={f"{x['display_name']}（{x['grade']}）":x['id'] for x in ss};qo={f"Q{x['id']}｜{x['subject_name']}｜{x['question_text'][:35]}":x['id'] for x in qs}
    with st.form('task'):title=st.text_input('課題名',value='今週の確認問題');desc=st.text_area('説明');targets=st.multiselect('対象学生',list(so));problems=st.multiselect('問題',list(qo));due=st.date_input('締切',value=date.today()+timedelta(days=7));ok=st.form_submit_button('配信',type='primary')
    if ok:
        if not targets or not problems:st.error('学生と問題を選択してください。')
        else:aid=create_assignment(u['id'],title,desc,[qo[x] for x in problems],[so[x] for x in targets],datetime.combine(due,datetime.max.time()).isoformat());st.success(f'課題ID {aid}を作成しました。')

def teacher_results(u):
    hero('課題結果','配信済み課題の回答数と正答率を確認します。');rows=fetch_all('SELECT id,title,due_at FROM assignments WHERE teacher_id=? ORDER BY created_at DESC',(u['id'],))
    if not rows:st.info('課題がありません。');return
    opts={f"#{r['id']} {r['title']}｜締切 {r['due_at']}":r['id'] for r in rows};label=st.selectbox('課題',list(opts));aid=opts[label];res=list_assignment_results(u['id'],aid);df=pd.DataFrame(res);st.dataframe(df,width='stretch',hide_index=True)
    st.download_button('CSV出力',assignment_results_csv(u['id'],aid).encode('utf-8-sig'),f'assignment_{aid}_results.csv','text/csv',width='stretch')

def admin_dash(u):
    hero('管理者ダッシュボード','問題・権利・公開状態・品質状態を管理します。');q=get_admin_quality_summary();df=pd.DataFrame(q['items']);c=st.columns(4);c[0].metric('登録問題数',len(df));c[1].metric('公開可能',q['counts']['ready']);c[2].metric('要確認',q['counts']['needs_review']);c[3].metric('公開不可',q['counts']['blocked']);st.dataframe(df,width='stretch',hide_index=True)
def admin_add(u):
    hero('問題登録','オリジナル問題または権利確認済み問題を登録します。');topics=list_topics();to={f"{x['code']}｜{x['name']}":x['code'] for x in topics}
    with st.form('addq2'):
        qt=st.selectbox('問題形式',['single','multiple','truefalse','numeric']);text=st.text_area('問題文');choices=[st.text_input(f'選択肢{i}') for i in range(1,6)] if qt!='numeric' else [];correct=st.text_input('正答コード（例 1 または 1,3）') if qt!='numeric' else '';num=st.number_input('正答数値',value=0.0) if qt=='numeric' else None;unit=st.text_input('単位') if qt=='numeric' else None;topic=st.selectbox('出題基準',list(to));short=st.text_area('一言解説');standard=st.text_area('標準解説');detailed=st.text_area('詳細解説');imp=st.slider('重要度',1,5,3);diff=st.slider('難易度',1,5,2);perm=st.selectbox('権利状態',['internal_sample','permission_confirmed','checking','not_allowed']);status=st.selectbox('公開状態',['draft','published']);ok=st.form_submit_button('登録',type='primary')
    if ok:
        try:qid=create_question(u['id'],qt,text,to[topic],choices,[x.strip() for x in correct.split(',') if x.strip()],num,unit,short,standard,detailed,imp,diff,perm,status);st.success(f'問題ID {qid}を登録しました。')
        except Exception as e:st.error(str(e))
def admin_csv(u):
    hero('CSV一括登録','テンプレートを使って問題を登録します。');p=DATA_DIR/'question_import_template.csv';st.download_button('テンプレートをダウンロード',p.read_bytes(),'ce108_question_import_template.csv','text/csv');f=st.file_uploader('問題CSV',type=['csv'])
    if f and st.button('取り込む',type='primary'):
        try:
            r=import_questions_csv(f.getvalue(),u['id']);st.success(f"{r['inserted']}問登録")
            if r['errors']:st.warning('\n'.join(r['errors']))
        except Exception as e:st.error(str(e))
def admin_approve(u):
    hero('問題承認','権利確認済みの問題だけを公開します。');rows=fetch_all("SELECT q.id,q.question_text,q.status,qs.permission_status FROM questions q LEFT JOIN question_sources qs ON qs.question_id=q.id WHERE q.status!='published' ORDER BY q.id DESC")
    if not rows:st.info('承認待ちはありません。');return
    for r in rows:
        with st.container(border=True):st.write(f"**Q{r['id']}** {r['question_text']}");st.caption(f"権利:{r['permission_status']} 状態:{r['status']}");
        if st.button('承認して公開',key='a'+str(r['id'])):
            try:approve_question(r['id'],u['id']);st.rerun()
            except Exception as e:st.error(str(e))

def admin_unpublish(u):
    hero('問題非公開化','公開済み問題を必要に応じて非公開にします。');rows=fetch_all("SELECT q.id,q.question_text,qs.permission_status FROM questions q LEFT JOIN question_sources qs ON qs.question_id=q.id WHERE q.status='published' ORDER BY q.id DESC")
    if not rows:st.info('公開中の問題はありません。');return
    for r in rows:
        with st.container(border=True):
            st.write(f"**Q{r['id']}** {r['question_text']}");st.caption(f"権利:{r['permission_status']}")
            if st.button('非公開にする',key='u'+str(r['id'])):
                try:unpublish_question(r['id'],u['id']);st.rerun()
                except Exception as e:st.error(str(e))

if st.session_state.user_id is None:login();st.stop()
u=get_user(st.session_state.user_id)
with st.sidebar:
    st.markdown('## CE108');st.write('**'+u['display_name']+'**');st.caption('権限：'+u['role'])
    if st.button('ログアウト',width='stretch'):logout()
    menus={'student':['ホーム','初回30問診断','今日の問題','苦手・得意分析','復習予定','学習履歴','教員からの課題'],'teacher':['教員ダッシュボード','課題作成','課題結果'],'admin':['管理者ダッシュボード','問題登録','CSV一括登録','問題承認','問題非公開化']};page=st.radio('メニュー',menus[u['role']])
funcs={'ホーム':student_home,'初回30問診断':student_diag,'今日の問題':student_daily,'苦手・得意分析':mastery,'復習予定':reviews,'学習履歴':history,'教員からの課題':assignments,'教員ダッシュボード':teacher_dash,'課題作成':teacher_task,'課題結果':teacher_results,'管理者ダッシュボード':admin_dash,'問題登録':admin_add,'CSV一括登録':admin_csv,'問題承認':admin_approve,'問題非公開化':admin_unpublish};funcs[page](u)
