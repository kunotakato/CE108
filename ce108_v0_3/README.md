# CE108 v0.4.1 Web Deployment Preparation

臨床工学技士国家試験対策のローカル実動プロトタイプです。v0.4では、学生が毎日使い続けるための日次学習体験、復習キュー、教員支援、管理者品質チェックを追加しています。v0.4.1では、外部URLで小規模β検証を行うためのWeb公開準備を追加しています。

## 実装済み

### 学生機能
- メールログイン
- 30問の初回診断
- 今日の推奨問題
- 五肢択一・正誤・数値入力問題
- 回答時の自信度入力
- 正誤判定と3段階解説
- 正誤・自信度・回答時間による理解度更新
- 1日後・3日後・7日後・14日後の復習登録
- 苦手・得意分析
- 学習履歴
- 教員課題一覧

### 教員機能
- 担当学生一覧
- 学生の回答数・正答率確認
- 公開済み問題から課題作成
- 対象学生・締切設定
- 課題結果確認
- 課題結果CSV出力

### 管理者機能
- 問題一覧
- 問題の手動登録
- CSV一括登録
- 出題基準コードとの紐付け
- 権利状態の管理
- 権利確認済み問題のみ承認・公開
- 問題の非公開化
- 管理者操作の監査ログ保存

### API・LINE接続口
- FastAPI
- 署名付きアクセストークン
- ロール別アクセス制御
- 問題取得・回答API
- 今日の問題API
- 診断API
- 教員向け担当学生・課題結果API
- 管理者向け問題管理API
- LINE Webhook受信口
- 「テスター希望」の保存
- LIFF接続用HTML雛形

### Mobile Alpha v0.3.5
- 学生向けNext.jsモバイル画面
- ログイン、オンボーディング、ホーム、今日の5問、回答後解説、完了結果、理解度画面
- PWA manifest
- 320px幅を含むスマートフォン表示の横スクロール抑制
- 回答前の正解情報露出ガード

### Daily Learning Beta v0.4
- 今日の学習状態
- 連続学習日数
- 7日間の学習サマリー
- 未完了日次セッションの再開導線
- 復習キュー
- 復習予定の「今日・期限超過・今後」表示
- 教員向け要注意学生サマリーAPI
- 管理者向け問題品質チェックAPI

### Web Deployment Preparation v0.4.1
- FastAPIのCORS許可オリジンを`CE108_CORS_ORIGINS`で設定可能
- `/health`とモバイルパッケージのバージョンを`0.4.1`へ更新
- デプロイ用環境変数サンプルを整理
- `docs/DEPLOYMENT_PLAN.md`にWeb公開準備手順を追加
- `docs/EXTERNAL_BETA_GUIDE.md`に外部βテスターへ共有する前の準備事項を追加
- 学生モバイル画面からβフィードバックを送信可能
- 同時アクセス時の日次プラン生成競合を修正

## 重要事項

収録されている問題は、動作確認用のCE108オリジナルサンプルです。30問診断はこのサンプル問題群から重複なく生成します。国家試験過去問の原文は収録していません。

過去問を公開する場合は、権利者、利用条件、出典、加工の有無を確認し、`question_sources.permission_status`を更新してください。

医学・工学解説はMVP用サンプルです。正式公開前に、臨床工学技士・養成校教員等による監修が必要です。

## 起動方法

Python 3.11または3.12を推奨します。v0.3内部α版はPython 3.12.13で検証済みです。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate

pip install -r requirements.txt
python scripts/init_db.py
streamlit run app.py
```

通常は次のURLで開きます。

```text
http://localhost:8501
```

8501が使用中の場合は、任意の空きポートを指定してください。

```bash
streamlit run app.py --server.port 8503
```

## デモアカウント

```text
学生: student@ce108.local
教員: teacher@ce108.local
管理者: admin@ce108.local
共通パスワード: demo1234
```

## FastAPI

```bash
uvicorn api:app --host 127.0.0.1 --port 8000
```

APIドキュメント:

```text
http://localhost:8000/docs
```

ログイン例:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=student@ce108.local&password=demo1234"
```

主要API:

```text
GET  /health
POST /api/auth/login
GET  /api/users/me
GET  /api/questions
GET  /api/questions/{qid}
POST /api/questions/{qid}/answer
GET  /api/study/today
GET  /api/study/daily-status
GET  /api/study/reviews
GET  /api/study/summary
GET  /api/study/mastery
POST /api/diagnostics/start
POST /api/diagnostics/{sid}/answer
GET  /api/diagnostics/{sid}/result
GET  /api/teacher/students
GET  /api/teacher/support
GET  /api/teacher/assignments/{assignment_id}/results.csv
GET  /api/admin/questions
GET  /api/admin/quality
POST /api/admin/questions
POST /api/admin/questions/{qid}/approve
POST /api/admin/questions/{qid}/unpublish
```

学生向けの問題詳細APIは、回答前に正答コード、数値正答、選択肢ごとの正誤を返しません。

### Web公開準備

外部URLでスマホ版を使うには、Next.jsだけでなくFastAPIも公開する必要があります。

FastAPI側の主な環境変数:

```text
CE108_APP_SECRET=replace-with-a-long-random-secret
CE108_DB_PATH=/path/to/persistent/ce108.db
CE108_CORS_ORIGINS=https://your-mobile-app.example.com
PUBLIC_BASE_URL=https://your-api.example.com
```

モバイル側の主な環境変数:

```text
NEXT_PUBLIC_API_BASE_URL=https://your-api.example.com
```

詳細は次を参照してください。

```text
docs/DEPLOYMENT_PLAN.md
docs/EXTERNAL_BETA_GUIDE.md
```

## Mobile Alpha v0.3.5

学生がスマートフォンで毎日5問を解くためのNext.jsフロントエンドを`mobile/`に追加しています。教員・管理者画面は従来どおりStreamlitを利用します。

FastAPIを起動した状態で、別ターミナルから起動します。

```bash
cd mobile
npm install
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --hostname 127.0.0.1 --port 3000
```

通常は次のURLで開きます。

```text
http://127.0.0.1:3000/login
```

モバイル側の検証:

```bash
cd mobile
npm run typecheck
npm run lint
npm test
npm run build
npm run test:e2e
```

## CSV問題登録

管理者でログインし、「CSV一括登録」からテンプレートをダウンロードします。

公開可能な権利状態:
- `permission_confirmed`
- `internal_sample`
- `public_domain`

それ以外の問題は、CSVで`published`を指定しても`draft`になります。

## LINE・LIFF

`.env.example`を`.env`にコピーし、LINE Developersで取得した認証情報を設定します。

```text
LINE_CHANNEL_SECRET
LINE_CHANNEL_ACCESS_TOKEN
LIFF_ID
PUBLIC_BASE_URL
```

Webhook URL:

```text
https://YOUR_DOMAIN/api/line/webhook
```

`liff/index.html`内の`YOUR_LIFF_ID`を置き換えてください。

v0.3ではWebhook署名検証、Webhook受信、「テスター希望」の保存、LIFF HTML雛形までを実装しています。本番接続は未完了です。Push配信、LINEログインの本番検証、LIFFアクセストークン検証は、実アカウントとデプロイ環境が必要です。

## テスト

```bash
python -m unittest discover -s tests -v
```

## 構成

```text
ce108_v0_3/
├── app.py
├── api.py
├── ce108/
│   ├── admin_service.py
│   ├── config.py
│   ├── database.py
│   ├── security.py
│   ├── seed.py
│   └── services.py
├── data/
├── liff/index.html
├── mobile/
├── scripts/init_db.py
├── tests/test_core.py
├── Dockerfile
├── requirements.txt
└── .env.example
```

## v0.3で外部設定が必要な部分

- LINEログイン
- LINE Push Message
- LIFFの本番配信
- 本番ドメインでのWebhook疎通確認
- PostgreSQL本番移行
- OpenAI APIによる類題生成
- 国家試験過去問の正式収録
- 学校ごとの本番アクセス制御
