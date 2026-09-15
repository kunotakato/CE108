# CE108 Past Exam Theme Index

## Purpose

過去問10年分をそのまま転載するのではなく、出題位置とテーマだけを整理し、CE108オリジナル問題・有料模試・学習戦略へつなげるためのメタデータ台帳です。

CE108では、公式問題文・選択肢・公式解説文を保存しません。扱うのは以下だけです。

- 第何回
- 年度
- 午前 / 午後
- 第何問
- CE108内の分野コード
- 頻出テーマ
- キーワード
- 参照元URL
- 対応するCE108オリジナル類題ID

## Why This Matters

ユーザーにとって価値が高いのは、「自分で10年分を見比べなくても、どのテーマがよく出るか分かる」ことです。

この台帳を増やすと、次の機能につながります。

- 年度別にどの分野が出たかを見る
- 午前/午後の出題傾向を見る
- 頻出テーマ順にCE108オリジナル類題を解く
- 苦手分野と頻出分野が重なる部分を優先表示する
- 有料模試の出題設計に使う

## CSV Columns

`scripts/import_past_exam_theme_refs.py` は以下のCSVを読み込みます。

```csv
exam_round,exam_year,session,question_number,topic_code,derived_theme,keywords,source_url,linked_question_id,note
39,2026,午前,1,MED-ANAT,刺激伝導系,"心臓,洞房結節,房室結節",https://example.com,1,公式本文は保存しない
```

## Import Command

```bash
cd /Users/taka.k/Documents/AIシステム/ce108_v0_3
python scripts/import_past_exam_theme_refs.py data/past_exam_theme_refs.csv
```

Render Shellで実行する場合も同じ考え方です。DBは環境変数 `CE108_DB_PATH` が指す `/var/data/ce108.db` を使います。

## Copyright Rule

安全運用のため、CSVやDBへ以下は入れません。

- 公式過去問の問題文全文
- 公式過去問の選択肢全文
- 公式解説文の転載
- 他サイトの解説文の転載

CE108で表示・販売する問題は、頻出テーマをもとに作ったオリジナル類題として作成します。

## Review Workflow

1. 過去問の出題位置を確認する
2. テーマだけをCSVへ記録する
3. CE108オリジナル類題へ紐づける
4. あなたがME視点で医学・工学の一次監修を行う
5. 有料提供前に誤りや表現の最終確認を行う

この流れなら、AIの強みである頻出分析と学習優先度付けを使いながら、公式問題の転載リスクを避けられます。
