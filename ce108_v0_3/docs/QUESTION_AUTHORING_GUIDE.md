# CE108 Question Authoring Guide

## Purpose

CE108に追加する問題は、臨床工学技士国家試験対策として使える「国試風オリジナル問題」に限定します。国家試験過去問の原文、解説文、選択肢の丸写しは収録しません。

## Required Fields

- `question_type`: `single`、`truefalse`、`numeric`
- `topic_code`: 既存の出題基準コード
- `question_text`: オリジナルの問題文
- `choices`: 選択問題では2から5個
- `correct_codes`: 選択問題の正答
- `numeric_answer`: 数値問題の正答
- `numeric_tolerance`: 許容誤差
- `explanation_short`: 1行の正答根拠
- `explanation_standard`: 学生が読む標準解説
- `explanation_detailed`: 誤答との違いまで含む詳細解説
- `choice_explanations`: 各選択肢が正しい理由、または誤りの理由
- `importance`: 1から5
- `frequency_score`: 1.0から3.0目安
- `source_type`: `sample_original`
- `permission_status`: `internal_sample`

## Authoring Rules

- 問題文は「用語暗記」だけでなく、条件から判断する形にする。
- 選択肢は正答と同じ分野の紛らわしい語を含める。
- 誤答選択肢には「なぜ違うか」を必ず書く。
- 医学では、解剖、生理、循環、呼吸、腎、酸塩基、ショック、検査値を優先する。
- 工学では、電気回路、交流、信号、圧力、流量、透析、人工呼吸、人工心肺、安全を優先する。
- 数値問題では、公式、単位変換、代入、答えを解説に含める。
- 回答前APIに正答、正答選択肢、選択肢解説を返さない。
- 回答後は、正答根拠、誤答理由、復習日、関連問題を返す。

## Prohibited Content

- 国家試験過去問の原文
- 外部サイトの解説文の転載
- 出典不明の図表
- 実在患者情報
- 公式問題と誤認される表記

## Review Checklist

- [ ] 問題文がオリジナルである
- [ ] 正答が一意に決まる
- [ ] すべての誤答選択肢に理由がある
- [ ] 出題基準コードと対応している
- [ ] 図解生成の対象になりやすいキーワードを含む
- [ ] 医学・工学の専門監修前であることを明示できる
- [ ] `permission_status=internal_sample`または`permission_confirmed`である
