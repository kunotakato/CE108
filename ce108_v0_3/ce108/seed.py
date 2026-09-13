from __future__ import annotations
import csv
from pathlib import Path
from .config import DATA_DIR, DB_PATH
from .database import connect, initialize_database, utc_now
from .first_paid_pack import FIRST_PAID_TESTER_PACK_CHOICE_UPDATES
from .original_question_bank import EXPANDED_ORIGINAL_QUESTIONS
from .security import hash_password

SUBJECTS=[('MED','医学概論・基礎医学'),('EEE','医用電気電子工学'),('MECH','医用機械工学・物理数学'),('MAT','生体物性材料工学'),('SUP','生体機能代行装置学'),('THER','医用治療機器学'),('MEAS','生体計測装置学'),('SAFE','医用機器安全管理学'),('CLIN','臨床医学総論')]
TOPICS=[('MED','MED-ANAT','解剖・生理'),('MED','MED-BIO','生化学・代謝'),('EEE','EEE-CIR','電気回路'),('EEE','EEE-SIG','交流・信号'),('MECH','MECH-MATH','数学・単位変換'),('MECH','MECH-FLUID','圧力・流体'),('MAT','MAT-BIO','生体物性'),('SUP','SUP-HD','血液浄化'),('SUP','SUP-RESP','呼吸療法'),('SUP','SUP-ECC','体外循環'),('THER','THER-DEF','除細動・治療機器'),('MEAS','MEAS-SPO2','生体計測・SpO2'),('SAFE','SAFE-ELEC','電気安全'),('CLIN','CLIN-PATH','病態・臨床')]

def C(topic,text,choices,correct,short,importance=4,frequency=2.0,qtype='single',choice_explanations=None):
    return {'type':qtype,'topic':topic,'text':text,'choices':choices,'correct':[str(x) for x in correct],'short':short,'standard':short,'detailed':short+' 関連する基礎原理と臨床的な意味を合わせて確認してください。','importance':importance,'frequency':frequency,'choice_explanations':choice_explanations or []}
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
C('MED-ANAT','血圧を規定する要素として最も基本的な組合せはどれか。',['心拍出量と末梢血管抵抗','体温と尿量','血糖値と白血球数','肺活量と酸素濃度','骨密度と筋力'],[1],'血圧は大きく心拍出量と末梢血管抵抗により規定されます。',5,3,'single',['心拍出量と末梢血管抵抗は血圧理解の基本です。','体温や尿量は全身状態の指標ですが、血圧を直接規定する基本式ではありません。','血糖値と白血球数は代謝・炎症の評価であり、血圧の主因ではありません。','肺活量と酸素濃度は呼吸評価の項目です。循環の基本因子と混同しないようにします。','骨密度と筋力は運動器の評価で、血圧調節の主因ではありません。']),
C('MED-ANAT','静脈還流が低下したとき、まず低下しやすい循環指標はどれか。',['前負荷','後負荷','心筋収縮性','血液粘稠度のみ','体温'],[1],'静脈還流の低下は心室へ戻る血液量を減らし、前負荷低下につながります。',5,3,'single',['前負荷は心室拡張末期の充満を反映し、静脈還流の影響を受けます。','後負荷は心臓が血液を押し出す抵抗で、静脈還流そのものとは区別します。','心筋収縮性はポンプ機能の性質で、戻る血液量とは別概念です。','血液粘稠度は抵抗に関わりますが、静脈還流低下の最初の説明ではありません。','体温は循環に影響し得ますが、静脈還流低下を直接表す指標ではありません。']),
C('MED-BIO','代謝性アシドーシスで一次的に低下しているものはどれか。',['血中重炭酸イオン','PaCO2','血清Naのみ','ヘモグロビン濃度','体温'],[1],'代謝性アシドーシスでは一次性変化として重炭酸イオンが低下します。',5,3,'single',['重炭酸イオン低下が代謝性アシドーシスの一次性変化です。','PaCO2低下は呼吸性代償として起こり得ますが、一次性変化ではありません。','血清Naだけで酸塩基異常の型は決まりません。','ヘモグロビン濃度は酸素運搬能の指標で、酸塩基の一次変化ではありません。','体温は酸塩基平衡の分類項目ではありません。']),
C('MED-BIO','低酸素血症に対して末梢化学受容器が主に反応する部位はどれか。',['頸動脈小体','洞房結節','腎糸球体','膵ランゲルハンス島','脾臓'],[1],'頸動脈小体などの末梢化学受容器は低酸素に反応して換気調節に関わります。',5,3,'single',['頸動脈小体は低酸素への反応で重要です。','洞房結節は心拍のペースメーカーで、化学受容器ではありません。','腎糸球体は濾過に関わる構造です。酸素分圧を直接検出する主部位ではありません。','膵ランゲルハンス島は血糖調節に関わります。','脾臓は免疫・血液貯蔵に関わり、換気調節の主受容器ではありません。']),
C('CLIN-PATH','ショックで共通して問題となる病態として最も適切なのはどれか。',['組織灌流の不足','骨形成の亢進','胆汁分泌の増加のみ','視力の改善','皮膚角化の亢進'],[1],'ショックでは原因にかかわらず組織灌流不足が中心問題になります。',5,3,'single',['組織灌流不足がショックの中核です。循環血液量、ポンプ機能、血管抵抗のどこが崩れたかを次に考えます。','骨形成はショックの中心病態ではありません。','胆汁分泌だけでは全身性の循環不全を説明できません。','視力改善はショックの所見ではありません。','皮膚角化は慢性皮膚変化であり、急性循環不全の中心ではありません。']),
C('CLIN-PATH','心原性ショックの原因として最も考えやすいものはどれか。',['急性心筋梗塞によるポンプ機能低下','大量出血のみ','強いアナフィラキシーによる血管拡張','敗血症による末梢血管拡張','脱水による循環血液量低下'],[1],'心原性ショックは心臓のポンプ機能低下が主因です。',5,3,'single',['急性心筋梗塞では心筋収縮が障害され、ポンプ機能低下による心原性ショックにつながります。','大量出血は循環血液量減少性ショックとして整理します。','アナフィラキシーは血管拡張・血管透過性亢進による分布異常性ショックです。','敗血症性ショックは分布異常性ショックとして考えます。','脱水は循環血液量減少性ショックです。']),
C('CLIN-PATH','慢性腎不全で高くなりやすい検査値はどれか。',['血清クレアチニン','動脈血酸素分圧のみ','血小板数のみ','肺活量','視力'],[1],'腎機能低下ではクレアチニン排泄が低下し、血清クレアチニンが上昇しやすくなります。',5,3,'single',['血清クレアチニンは腎機能評価の代表的指標です。','酸素分圧は呼吸評価の指標で、腎不全の基本検査値としては中心ではありません。','血小板数だけでは腎機能低下を直接評価できません。','肺活量は換気機能の評価です。','視力は腎機能検査値ではありません。']),
C('SUP-RESP','人工呼吸器で一回換気量を大きくしすぎた場合に注意すべきリスクはどれか。',['肺の過伸展','必ず低血糖','除細動エネルギー不足','血液透析効率の低下のみ','電池容量の増加'],[1],'過大な一回換気量は肺胞過伸展や圧損傷のリスクになります。',5,3,'single',['一回換気量過大では肺の過伸展を考えます。','低血糖は換気量設定の直接的な代表リスクではありません。','除細動エネルギーは人工呼吸器の一回換気量とは別機器の概念です。','透析効率とは別の治療系です。装置名だけで結びつけないようにします。','電池容量は設定変更で増加しません。']),
C('SUP-RESP','呼吸不全でPaCO2が上昇しているとき、直接示唆される状態はどれか。',['肺胞換気の不足','酸素投与量が必ず過剰','血糖低下','腎濾過量の増加','骨髄機能亢進'],[1],'PaCO2上昇は二酸化炭素排出が不十分、すなわち肺胞換気不足を示唆します。',5,3,'single',['PaCO2上昇は換気不足をまず考えます。','酸素投与量だけではPaCO2上昇を直接説明できません。酸素化と換気を分けて考えます。','血糖はCO2排出の直接指標ではありません。','腎濾過量はPaCO2上昇の直接原因ではありません。','骨髄機能は血球産生の話で、換気評価とは別です。']),
C('SUP-HD','透析液流量を増やすことで主に改善しやすいものはどれか。',['拡散による溶質除去効率','血液凝固能そのもの','赤血球産生','除細動成功率','体温計の精度'],[1],'透析液側の濃度勾配を保ちやすくなり、拡散による小分子除去効率が改善しやすくなります。',5,3,'single',['透析液流量増加は濃度勾配維持に関わります。','血液凝固能は抗凝固薬や患者状態の問題で、透析液流量だけでは直接決まりません。','赤血球産生は腎性貧血や造血因子の問題です。','除細動は心臓治療機器の話で透析液流量とは別です。','体温計の精度は測定機器の性能です。']),
C('SUP-HD','透析中に除水量を過大に設定した場合に起こりやすいものはどれか。',['血圧低下','血糖上昇のみ','骨密度増加','肺活量増加','視力改善'],[1],'過大な除水は循環血液量を減らし、血圧低下を起こしやすくなります。',5,3,'single',['除水過多では循環血液量減少と血圧低下を考えます。','血糖上昇のみで除水過多は説明できません。','骨密度は急性の除水設定で増えません。','肺活量は除水量の直接結果ではありません。','視力改善は除水過多の代表所見ではありません。']),
C('SAFE-ELEC','ミクロショックのリスクが特に問題となる状況はどれか。',['心臓内に導電性カテーテルがある場合','皮膚が完全に乾燥している場合のみ','電源が完全に切れている場合','機器が未使用で保管中の場合','患者から離れた机上だけで測定する場合'],[1],'心臓内へ導電経路があると、微小な電流でも心筋へ直接影響し得ます。',5,3,'single',['心臓内導電経路がある場合はミクロショックに注意します。','皮膚状態はマクロショックに関わりますが、心内導電路の危険とは区別します。','電源が完全に切れていれば漏れ電流の問題は通常小さくなります。','保管中の未使用機器は患者接続時のリスクとは違います。','患者から離れた測定だけでは患者電撃リスクは中心になりません。']),
C('SAFE-ELEC','保護接地の主な目的はどれか。',['故障時に外装へ生じる危険電圧を低減する','装置の表示を大きくする','測定値を必ず高くする','バッテリー容量を増やす','消毒効果を高める'],[1],'保護接地は故障時の外装電位上昇を抑え、感電リスクを下げます。',5,3,'single',['保護接地は外装電位上昇と感電リスク低減が目的です。','表示サイズとは関係ありません。','測定値を高くする機能ではありません。','バッテリー容量は接地で増えません。','消毒効果は感染対策の領域です。']),
C('EEE-SIG','交流回路でコンデンサの容量リアクタンスは周波数が高くなるとどうなるか。',['小さくなる','大きくなる','必ずゼロになる','抵抗値と同じ意味になる','周波数と無関係'],[1],'容量リアクタンスは Xc＝1/(2πfC) で、周波数が高いほど小さくなります。',5,3,'single',['式 Xc＝1/(2πfC) から周波数上昇で小さくなります。','大きくなるのは誘導リアクタンスと混同しやすい誤りです。','高周波で小さくなりますが、理想式でも有限周波数で必ずゼロとは限りません。','リアクタンスと抵抗は単位は同じでも、エネルギー消費の意味が異なります。','容量リアクタンスは周波数に依存します。']),
C('EEE-SIG','誘導リアクタンスは周波数が高くなるとどうなるか。',['大きくなる','小さくなる','必ずゼロになる','容量リアクタンスと同じ式になる','電圧と無関係に常に一定'],[1],'誘導リアクタンスは XL＝2πfL で、周波数が高いほど大きくなります。',5,3,'single',['式 XL＝2πfL から周波数上昇で大きくなります。','小さくなるのは容量リアクタンスとの混同です。','周波数が高いほど増えるため、必ずゼロにはなりません。','容量リアクタンスは逆数の式です。式の形を区別します。','インダクタンスが一定なら周波数で変化します。']),
C('MECH-FLUID','流体抵抗が大きくなる条件として最も適切なのはどれか。',['管半径が小さい','管半径が大きい','粘度が低い','管長が短い','圧力差がゼロ'],[1],'管半径が小さくなると流体抵抗は大きくなります。',5,3,'single',['管半径低下は抵抗増大の重要因子です。半径の影響は非常に大きい点を押さえます。','管半径が大きいと抵抗は小さくなりやすいです。','粘度が低いと抵抗は小さくなりやすいです。','管長が短いと抵抗は小さくなりやすいです。','圧力差ゼロは流れを生みにくい条件ですが、抵抗そのものの説明とは分けます。']),
C('MEAS-SPO2','パルスオキシメータで測定値が不安定になりやすい状況はどれか。',['末梢循環不全','安静で十分な脈波がある状態','センサが適切に装着されている状態','体動が全くない状態','爪に何も塗布されていない状態'],[1],'末梢循環不全では脈波が小さくなり、SpO2測定が不安定になりやすくなります。',5,3,'single',['末梢循環不全では脈動成分が弱くなり、測定不良につながります。','十分な脈波があれば測定は安定しやすくなります。','適切な装着は測定安定に寄与します。','体動がないことは測定安定に寄与します。','爪の塗布物がないことは光学測定の妨げを減らします。']),
C('THER-DEF','同期カルディオバージョンで同期が必要な主な理由はどれか。',['脆弱期への通電を避けるため','充電時間を必ずゼロにするため','電極を不要にするため','血圧計として使うため','酸素濃度を測るため'],[1],'同期によりR波に合わせて通電し、心室細動を誘発しやすい時相を避けます。',5,3,'single',['同期はR波に合わせ、脆弱期通電を避けるために重要です。','充電時間をゼロにする機能ではありません。','電極は通電に必要です。','血圧測定機能ではありません。','酸素濃度測定はパルスオキシメータなどの役割です。']),
]
QUESTIONS.extend(EXPANDED_ORIGINAL_QUESTIONS)

def _apply_choice_updates(conn,updates:dict[str,list[tuple[str,bool,str]]]):
    for question_text, choices in updates.items():
        row=conn.execute('SELECT id FROM questions WHERE question_text=?',(question_text,)).fetchone()
        if not row:continue
        qid=row['id']
        for i,(choice_text,is_correct,explanation) in enumerate(choices,1):
            choice_code=str(i)
            exists=conn.execute('SELECT id FROM question_choices WHERE question_id=? AND choice_code=?',(qid,choice_code)).fetchone()
            if exists:
                conn.execute('''UPDATE question_choices
                    SET choice_text=?,is_correct=?,explanation=?,display_order=?
                    WHERE question_id=? AND choice_code=?''',(choice_text,int(is_correct),explanation,i,qid,choice_code))
            else:
                conn.execute('''INSERT INTO question_choices(question_id,choice_code,choice_text,is_correct,explanation,display_order)
                    VALUES(?,?,?,?,?,?)''',(qid,choice_code,choice_text,int(is_correct),explanation,i))

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
        tm={r['code']:r['id'] for r in conn.execute('SELECT id,code FROM topics')};admin=conn.execute("SELECT id FROM users WHERE role='admin'").fetchone()['id']
        existing={r['question_text'] for r in conn.execute('SELECT question_text FROM questions')}
        for q in QUESTIONS:
            if q['text'] in existing:continue
            qid=conn.execute("""INSERT INTO questions(question_type,question_text,numeric_answer,numeric_tolerance,unit,explanation_short,explanation_standard,explanation_detailed,difficulty,importance,frequency_score,source_type,status,created_by,approved_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,2,?,?,'sample_original','published',?,?,?,?)""",(q['type'],q['text'],q.get('numeric_answer'),q.get('tolerance',.01),q.get('unit'),q['short'],q['standard'],q['detailed'],q['importance'],q['frequency'],admin,admin,now,now)).lastrowid
            choice_explanations=q.get('choice_explanations') or []
            for i,ch in enumerate(q.get('choices',[]),1):
                is_correct=int(str(i) in q.get('correct',[]))
                explanation=choice_explanations[i-1] if i-1<len(choice_explanations) else (q['short'] if is_correct else f'{ch}は本問の正答ではありません。正答の根拠と比較し、どの条件が合わないかを確認してください。')
                conn.execute("INSERT INTO question_choices(question_id,choice_code,choice_text,is_correct,explanation,display_order) VALUES(?,?,?,?,?,?)",(qid,str(i),ch,is_correct,explanation,i))
            conn.execute("INSERT INTO question_topic_mappings(question_id,topic_id,mapping_type,weight) VALUES(?,?,'primary',1.0)",(qid,tm[q['topic']]))
            conn.execute("INSERT INTO question_sources(question_id,source_name,copyright_holder,permission_status,checked_at,checked_by) VALUES(?,'CE108オリジナルサンプル','CE108','internal_sample',?,?)",(qid,now,admin))
        for row in conn.execute("SELECT c.id,c.choice_text,c.is_correct,q.explanation_short FROM question_choices c JOIN questions q ON q.id=c.question_id WHERE TRIM(COALESCE(c.explanation,''))=''"):
            explanation=row['explanation_short'] if row['is_correct'] else f"{row['choice_text']}は本問の正答ではありません。正答の根拠と比較し、どの条件が合わないかを確認してください。"
            conn.execute('UPDATE question_choices SET explanation=? WHERE id=?',(explanation,row['id']))
        _apply_choice_updates(conn,FIRST_PAID_TESTER_PACK_CHOICE_UPDATES)

def export_question_template(path:Path|None=None)->Path:
    path=path or DATA_DIR/'question_import_template.csv';cols=['question_type','question_text','choice_1','choice_2','choice_3','choice_4','choice_5','choice_1_explanation','choice_2_explanation','choice_3_explanation','choice_4_explanation','choice_5_explanation','correct_codes','numeric_answer','numeric_tolerance','unit','topic_code','explanation_short','explanation_standard','explanation_detailed','difficulty','importance','frequency_score','source_type','source_name','source_url','copyright_holder','permission_status','status']
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(cols);w.writerow(['single','サンプル問題文','選択肢1','選択肢2','選択肢3','選択肢4','選択肢5','選択肢1が正しい理由','選択肢2が誤りの理由','選択肢3が誤りの理由','選択肢4が誤りの理由','選択肢5が誤りの理由','1','','0.01','','MED-ANAT','一言解説','標準解説','詳細解説','2','3','1.0','original','作成者名','','権利者','permission_confirmed','draft'])
    return path
