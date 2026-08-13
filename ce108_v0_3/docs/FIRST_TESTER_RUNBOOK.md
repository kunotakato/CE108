# CE108 First Tester Runbook

## Goal

v0.4.3の目的は、最初の外部テスター1人がスマートフォンでCE108を触り、学習導線、ログイン活動、フィードバック導線を確認できる状態にすることです。

最初の1人へ何をどう渡すかの設計は、`docs/FIRST_TESTER_DELIVERY_DESIGN.md`を参照してください。

## Before Inviting

- FastAPIとmobileの公開URLがHTTPSで開ける。
- `/health`が`0.4.3`を返す。
- `CE108_APP_SECRET`をデモ値から変更している。
- `CE108_CORS_ORIGINS`にmobile公開URLだけを設定している。
- `NEXT_PUBLIC_API_BASE_URL`にFastAPI公開URLを設定している。
- SQLite DBがRender Diskなどの永続領域にある。
- `NEXT_PUBLIC_ENABLE_DEMO_LOGIN`は公開環境で未設定または`false`にしている。

## Create Tester Account

Render Shellまたはローカルで実行します。

```bash
cd ce108_v0_3
python scripts/create_tester_account.py \
  --email beta1@example.com \
  --password replace-with-8-or-more-chars \
  --display-name 外部β1
```

管理者APIで作る場合:

```bash
curl -X POST "$API_URL/api/admin/tester-students" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"beta1@example.com","password":"replace-with-8-or-more-chars","display_name":"外部β1"}'
```

## Tester Script

テスターには次の順番で触ってもらいます。

1. mobile公開URLを開く。
2. 発行されたメールアドレスとパスワードでログインする。
3. ホームで今日の状態を確認する。
4. 今日の5問を1問以上回答する。
5. 回答後に正誤、解説、選択肢ごとの解説、復習日が出ることを確認する。
6. 復習画面を開く。
7. 理解度画面を開く。
8. ノートAI画面で、個人情報を含まない短い学習メモから問題を作る。
9. フィードバック画面で感想と不具合を送る。

## Message To Tester

```text
CE108は外部β版です。
問題は操作検証用のオリジナルサンプルで、公式過去問ではありません。
参考換算点や学習提案は合格予測ではありません。
ノートAIには個人情報、患者情報、学校の非公開資料、支払い情報を入力しないでください。
使って迷った点、続けたい/続けにくい点をフィードバック画面から送ってください。
```

## Pass Criteria

- ログインできる。
- 今日の5問が表示される。
- 回答を保存できる。
- 回答前に正解情報が表示されない。
- 回答後に解説と選択肢ごとの解説が表示される。
- 復習日が登録される。
- ノートAIの注意文言が見える。
- フィードバックが保存される。
- 管理者画面の「βフィードバック分析」で一覧、カテゴリ別件数、優先度別件数を確認できる。

## Stop Criteria

- ログインできない。
- `Failed to fetch`が解消できない。
- 回答前に正答や選択肢解説が見える。
- テスターがサンプル問題を公式問題だと誤解する。
- テスターがノートAIへ個人情報や患者情報を入力しそうになる。
- 再起動でデータが消える。

## Reviewing Feedback

管理者アカウントでStreamlit管理画面にログインし、メニューから「βフィードバック分析」を開きます。

確認する項目:

- 総件数
- 平均評価
- 早急対応件数
- カテゴリ別の集中箇所
- 優先度「高」の意見
- 画面、日時、ユーザー、本文

優先度「高」は、不具合、低評価、ログイン不可、Failed to fetch、保存不可などの文言から自動判定します。

Render上でStreamlit管理画面を公開していない場合は、管理者トークンでFastAPIから確認します。

```text
GET /api/admin/tester-students/activity
GET /api/admin/beta-feedback/summary
GET /api/admin/beta-feedback
```
