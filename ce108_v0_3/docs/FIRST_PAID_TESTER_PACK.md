# CE108 First Paid Tester Pack

## Purpose

最初の有料候補テスターに見せるための30問パックです。

このパックは、問題数を多く見せることではなく、CE108の有料価値を短時間で確認してもらうことを目的にします。

## Positioning

この30問は、次の価値を確認するためのものです。

- 元文系でも理解しやすいか
- 医学と工学をつなげて理解できるか
- 誤答選択肢の理由が復習に役立つか
- 図解が文字だけの理解不足を補えるか
- 月額1,480円の候補価値があるか

## Composition

- 医学・病態・生理: 15問
- 工学・装置・安全・計算: 15問
- 合計: 30問

## Included Themes

医学側:

- 血圧、前負荷、心拍出量
- 酸塩基
- 低酸素と換気
- ショック
- 心不全
- 腎不全
- 心電図

工学・装置側:

- 人工呼吸器
- 透析
- 電気安全
- 交流回路
- 流体
- パルスオキシメータ
- 除細動
- サンプリング

## Mobile Route

学生画面では次から開始できます。

```text
/study?mode=first_paid
```

ホームと戦略画面にも「有料候補30問」への導線を追加しています。

## API

30問パック全体を確認するAPI:

```text
GET /api/study/first-paid-pack
```

学習画面用の出題API:

```text
GET /api/study/focus?mode=first_paid&count=30
```

## Review CSV

一次監修・学習者目線レビュー用CSV:

```bash
cd /Users/taka.k/Documents/AIシステム/ce108_v0_3
.venv312/bin/python scripts/export_first_paid_tester_pack.py --output data/first_paid_tester_pack.csv
```

CSVでは次を確認します。

- `primary_review`: 内容確認済みか
- `learner_comment`: 元文系・苦手学習者目線で分かりやすいか
- `needs_fix`: 修正が必要か
- `fix_comment`: 修正内容

## Acceptance Criteria

- 30問すべてが取得できる
- 回答前に正答・解説が露出しない
- 回答後に解説、誤答理由、図解、復習日が出る
- 医学と工学のバランスが崩れていない
- 公式過去問と誤解されない
- テスターが「これなら続けたいか」を判断できる

## Current Decision

このパックは、正式販売用ではなく、有料候補テスター向けの検証パックです。

あなた自身のME経験、元文系から国試164点まで伸ばした学習設計、医学高得点の強みを一次監修と解説設計に反映します。必要に応じて、工学・装置・安全の第三者確認を追加します。
