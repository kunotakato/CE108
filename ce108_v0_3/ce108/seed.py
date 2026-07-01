from __future__ import annotations
import csv
from pathlib import Path
from .config import DATA_DIR, DB_PATH
from .database import connect, initialize_database, utc_now
from .security import hash_password

SUBJECTS=[('MED','医学概論・基礎医学'),('EEE','医用電気電子工学'),('MECH','医用機械工学・物理数学'),('MAT','生体物性材料工学'),('SUP','生体機能代行装置学'),('THER','医用治療機器学'),('MEAS','生体計測装置学'),('SAFE','医用機器安全管理学'),('CLIN','臨床医学総論')]
TOPICS=[('MED','MED-ANAT','解剖・生理'),('MED','MED-BIO','生化学・代謝'),('EEE','EEE-CIR','電気回路'),('EEE','EEE-SIG','交流・信号'),('MECH','MECH-MATH','数学・単位変換'),('MECH','MECH-FLUID','圧力・流体'),('MAT','MAT-BIO','生体物性'),('SUP','SUP-HD','血液浄化'),('SUP','SUP-RESP','呼吸療法'),('SUP','SUP-ECC','体外循環'),('THER','THER-DEF','除細動・治療機器'),('MEAS','MEAS-SPO2','生体計測・SpO2'),('SAFE','SAFE-ELEC','電気安全'),('CLIN','CLIN-PATH','病態・臨床')]

def C(topic,text,choices,correct,short,importance=4,frequency=2.0,qtype='single'):
    return {'type':qtype,'topic':topic,'text':text,'choices':choices,'correct':[str(x) for x in correct],'short':short,'standard':short,'detailed':short+' 関連する基礎原理と臨床的な意味を合わせて確認してください。','importance':importance,'frequency':frequency}
def N(topic,text,answer,unit,short,importance=5,frequency=3.0,tol=.01):
    return {'type':'numeric','topic':topic,'text':text,'numeric_answer':answer,'unit':unit,'short':short,'standard':short,'detailed':short+' 使用公式、単位変換、代入、検算の順に確認してください。','importance':importance,'frequency':frequency,'tolerance':tol}

QUESTIONS=[
C('MED-ANAT','心臓の正常な刺激伝導系で、通常ペースメーカーとして最初に興奮する部位はどれか。',['洞房結節','房室結節','His束','右脚','Purkinje線維'],[1],'正常心では洞房結節が最初に自発興奮します。',5,3),
C('MED-ANAT','肺胞で酸素と二酸化炭素が移動する主な機序はどれか。',['能動輸送','単純拡散','濾過','浸透','貪食'],[2],'肺胞気と血液の分圧差により、ガスは単純拡散します。',5,3),
C('MED-ANAT','腎小体で血液から原尿が濾過される主な部位はどれか。',['糸球体','近位尿細管','Henle係蹄','遠位尿細管','集合管'],[1],'原尿は糸球体毛細血管からBowman嚢へ濾過されます。',5,3),
C('MED-BIO','血糖値を低下させる作用を持つホルモンはどれか。',['グルカゴン','アドレナリン','コルチゾール','インスリン','成長ホルモン'],[4],'インスリンは細胞への糖取り込みなどを促進し、血糖を低下させます。'),
C('MED-ANAT','血液中で酸素の大部分を運搬する物質はどれか。',['アルブミン','ヘモグロビン','フィブリノゲン','重炭酸イオン','グロブリン'],[2],'酸素の大部分は赤血球内のヘモグロビンと結合して運ばれます。',5,3),
C('MED-ANAT','副交感神経の刺激は、一般に心拍数を増加させる。',['正しい','誤り'],[2],'副交感神経刺激は一般に心拍数を低下させます。',4,2,'truefalse'),
N('EEE-CIR','抵抗6 Ωに12 Vの電圧を加えた。流れる電流は何Aか。',2,'A','オームの法則 I＝V/R より2 Aです。'),
N('EEE-CIR','100 Vで2 Aの電流が流れる機器の消費電力は何Wか。',200,'W','電力P＝VIより200 Wです。'),
N('MECH-FLUID','100 Nの力が0.02 m²の面積に均等に加わる。圧力は何Paか。',5000,'Pa','圧力P＝F/Aより5,000 Paです。'),
N('MECH-MATH','流量1 L/minは、およそ何mL/sか。小数第1位まで答えよ。',16.7,'mL/s','1,000 mL÷60 s＝約16.7 mL/sです。',5,3,.02),
C('MECH-MATH','初期値100が2回の半減期を経た値はどれか。',['12.5','25','50','75','200'],[2],'100→50→25となります。',3,1.5),
N('EEE-CIR','2 Ωと3 Ωの抵抗を直列接続した。合成抵抗は何Ωか。',5,'Ω','直列抵抗は加算するため5 Ωです。'),
N('EEE-CIR','6 Ωと3 Ωの抵抗を並列接続した。合成抵抗は何Ωか。',2,'Ω','1/R＝1/6＋1/3＝1/2より2 Ωです。'),
C('EEE-CIR','コンデンサの基本的な働きとして最も適切なのはどれか。',['電荷を蓄える','直流電圧を必ず増幅する','磁束を発生しない','抵抗値を一定に保つ','交流を直流へ必ず変換する'],[1],'コンデンサは電荷を蓄える素子です。'),
N('EEE-SIG','周波数50 Hzの正弦波の周期は何秒か。',0.02,'s','周期T＝1/fより0.02秒です。',5,3,.001),
C('SUP-HD','血液透析で小分子溶質が濃度の高い側から低い側へ移動する機序はどれか。',['拡散','能動輸送','貪食','沈殿','電気泳動のみ'],[1],'尿素などの小分子除去の中心は拡散です。',5,3),
C('SUP-HD','血液透析で限外濾過の主な駆動力となるものはどれか。',['膜間圧力差','酸素分圧差','温度差のみ','電位差のみ','赤血球数'],[1],'限外濾過は膜間圧力差を主な駆動力とします。',5,3),
C('SUP-HD','血液透析では一般に、血液と透析液を同じ方向に流す方が向流より濃度勾配を保ちやすい。',['正しい','誤り'],[2],'一般に向流の方が膜全体で濃度勾配を保ちやすくなります。',4,2,'truefalse'),
C('SUP-HD','維持血液透析の長期的な血管アクセスとして一般に用いられるものはどれか。',['自己血管内シャント','末梢静脈留置針','肺動脈カテーテル','動脈ライン','中心静脈圧ライン'],[1],'自己血管内シャントは長期透析の代表的な血管アクセスです。',5,3),
C('SUP-RESP','室内気の吸入酸素濃度（FiO2）に最も近い値はどれか。',['0.10','0.21','0.40','0.60','1.00'],[2],'室内気の酸素濃度は約21％です。',5,3),
C('SUP-RESP','人工呼吸管理でPEEPを設定する主な目的として適切なのはどれか。',['呼気終末の肺胞虚脱を抑える','必ず心拍数を増やす','気道抵抗をゼロにする','吸気時間を必ず短縮する','二酸化炭素産生を停止する'],[1],'PEEPは呼気終末に陽圧を保ち、肺胞虚脱を抑えます。',5,3),
N('SUP-RESP','一回換気量500 mL、呼吸数12回/minのとき、分時換気量は何L/minか。',6,'L/min','500 mL×12＝6,000 mL/min＝6 L/minです。'),
C('MEAS-SPO2','SpO2は、動脈血酸素飽和度を非侵襲的に推定する指標である。',['正しい','誤り'],[1],'SpO2は脈動成分を利用して酸素飽和度を推定します。',5,3,'truefalse'),
C('SUP-ECC','人工心肺回路の人工肺が担う主な機能はどれか。',['酸素付加と二酸化炭素除去','血糖測定','神経刺激','尿生成','骨髄造血'],[1],'人工肺は肺のガス交換機能を代行します。',5,3),
C('SUP-ECC','体外循環中の抗凝固状態の確認に一般に用いられる検査はどれか。',['ACT','HbA1c','尿比重','赤沈','肺活量'],[1],'ACTは体外循環中のヘパリン抗凝固管理に用いられます。',5,3),
C('SUP-ECC','低体温は一般に組織の代謝・酸素消費を低下させる方向に働く。',['正しい','誤り'],[1],'体温低下は代謝率と酸素消費を低下させます。',4,2,'truefalse'),
C('SUP-ECC','遠心ポンプの特性として適切なのはどれか。',['流量は前負荷・後負荷の影響を受ける','回転数に関係なく流量が一定','血液と接触しない','逆流が絶対に起こらない','電源が不要'],[1],'遠心ポンプ流量は回転数だけでなく前負荷・後負荷にも依存します。'),
C('SAFE-ELEC','医用電気機器の患者漏れ電流を管理する主な目的はどれか。',['患者への電撃リスクを低減する','機器の重量を増やす','画面を明るくする','酸素濃度を上げる','薬剤量を測定する'],[1],'漏れ電流管理は患者・使用者の電撃防止に重要です。',5,3),
C('THER-DEF','除細動器で電気エネルギーを蓄える主要部品はどれか。',['コンデンサ','抵抗器のみ','温度計','人工肺','圧力計'],[1],'除細動器はコンデンサに電気エネルギーを蓄えます。',5,3),
C('MEAS-SPO2','パルスオキシメータが酸化ヘモグロビンと還元ヘモグロビンを識別するために利用するものはどれか。',['赤色光と赤外光の吸光度の違い','X線吸収のみ','超音波反射のみ','体温差のみ','磁場強度のみ'],[1],'赤色光と赤外光に対する吸光特性の差を利用します。',5,3),
C('CLIN-PATH','左心不全で生じやすい所見はどれか。',['肺うっ血','脾摘後変化','胆汁うっ滞のみ','多尿のみ','骨折'],[1],'左心系の拍出障害は肺静脈圧上昇と肺うっ血につながります。'),
]

def seed_database(db_path:Path|str=DB_PATH):
    initialize_database(db_path)
    with connect(db_path) as conn:
        now=utc_now()
        if conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]==0:
            ids={}
            for email,role,name,grade,year in [('student@ce108.local','student','学生デモ','4年',2027),('teacher@ce108.local','teacher','教員デモ',None,None),('admin@ce108.local','admin','管理者デモ',None,None)]:
                uid=conn.execute("INSERT INTO users(email,password_hash,role,status,created_at,updated_at) VALUES(?,?,?,'active',?,?)",(email,hash_password('demo1234'),role,now,now)).lastrowid;ids[role]=uid
                conn.execute("INSERT INTO user_profiles(user_id,display_name,school_name,grade,target_exam_year,daily_study_minutes,target_score,notification_time) VALUES(?,?,'CE108デモ養成校',?,?,15,108,'20:00')",(uid,name,grade,year))
            org=conn.execute("INSERT INTO organizations(name,organization_type,status,created_at) VALUES('CE108デモ養成校','training_school','active',?)",(now,)).lastrowid
            conn.execute("INSERT INTO organization_memberships(organization_id,user_id,class_name,academic_year,membership_role) VALUES(?,?,'4年A組',2026,'student')",(org,ids['student']));conn.execute("INSERT INTO organization_memberships(organization_id,user_id,class_name,academic_year,membership_role) VALUES(?,?,'4年A組',2026,'teacher')",(org,ids['teacher']))
        if conn.execute('SELECT COUNT(*) FROM exam_standard_versions').fetchone()[0]==0:
            sid=conn.execute("INSERT INTO exam_standard_versions(version_name,effective_exam_from,source_url,status) VALUES('令和8年版',39,'https://www.jaame.or.jp/ce/criteria/R8kijun_all.pdf','active')").lastrowid;sm={}
            for i,(c,n) in enumerate(SUBJECTS,1):sm[c]=conn.execute('INSERT INTO subjects(standard_version_id,code,name,display_order) VALUES(?,?,?,?)',(sid,c,n,i)).lastrowid
            for i,(sc,c,n) in enumerate(TOPICS,1):conn.execute("INSERT INTO topics(subject_id,level,code,name,description,display_order) VALUES(?,'small',?,?,?,?)",(sm[sc],c,n,'MVP用代表項目。正式版で公式階層を拡張する。',i))
        if conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]==0:
            tm={r['code']:r['id'] for r in conn.execute('SELECT id,code FROM topics')};admin=conn.execute("SELECT id FROM users WHERE role='admin'").fetchone()['id']
            for q in QUESTIONS:
                qid=conn.execute("""INSERT INTO questions(question_type,question_text,numeric_answer,numeric_tolerance,unit,explanation_short,explanation_standard,explanation_detailed,difficulty,importance,frequency_score,source_type,status,created_by,approved_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,2,?,?,'sample_original','published',?,?,?,?)""",(q['type'],q['text'],q.get('numeric_answer'),q.get('tolerance',.01),q.get('unit'),q['short'],q['standard'],q['detailed'],q['importance'],q['frequency'],admin,admin,now,now)).lastrowid
                for i,ch in enumerate(q.get('choices',[]),1):conn.execute("INSERT INTO question_choices(question_id,choice_code,choice_text,is_correct,explanation,display_order) VALUES(?,?,?,?,?,?)",(qid,str(i),ch,int(str(i) in q.get('correct',[])),'',i))
                conn.execute("INSERT INTO question_topic_mappings(question_id,topic_id,mapping_type,weight) VALUES(?,?,'primary',1.0)",(qid,tm[q['topic']]))
                conn.execute("INSERT INTO question_sources(question_id,source_name,copyright_holder,permission_status,checked_at,checked_by) VALUES(?,'CE108オリジナルサンプル','CE108','internal_sample',?,?)",(qid,now,admin))

def export_question_template(path:Path|None=None)->Path:
    path=path or DATA_DIR/'question_import_template.csv';cols=['question_type','question_text','choice_1','choice_2','choice_3','choice_4','choice_5','correct_codes','numeric_answer','numeric_tolerance','unit','topic_code','explanation_short','explanation_standard','explanation_detailed','difficulty','importance','frequency_score','source_type','source_name','source_url','copyright_holder','permission_status','status']
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(cols);w.writerow(['single','サンプル問題文','選択肢1','選択肢2','選択肢3','選択肢4','選択肢5','1','','0.01','','MED-ANAT','一言解説','標準解説','詳細解説','2','3','1.0','original','作成者名','','権利者','permission_confirmed','draft'])
    return path
