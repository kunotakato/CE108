# CE108 Mobile v0.4.2

学生がスマートフォンで毎日5問を解くための Next.js/TypeScript フロントエンドです。v0.4.2では最初の外部テスターに渡すため、発行アカウントでのログイン、安全文言、フィードバック導線、ノートAI復習を整理しています。教員・管理者画面は従来どおり Streamlit を利用します。

## 起動

```bash
cd /Users/taka.k/Documents/AIシステム/ce108_v0_3
.venv312/bin/uvicorn api:app --host 127.0.0.1 --port 8000
```

別ターミナルで:

```bash
cd /Users/taka.k/Documents/AIシステム/ce108_v0_3/mobile
npm install
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --hostname 127.0.0.1 --port 3000
```

ブラウザーで `http://127.0.0.1:3000/login` を開きます。

## Web公開時の設定

外部URLで使う場合は、デプロイ先の環境変数に公開済みFastAPI URLを設定します。

```text
NEXT_PUBLIC_API_BASE_URL=https://your-api.example.com
```

FastAPI側では、モバイルURLを`CE108_CORS_ORIGINS`に設定してください。

ローカル検証でデモログイン入力ボタンを表示する場合だけ、次を追加します。

```text
NEXT_PUBLIC_ENABLE_DEMO_LOGIN=true
```

## 外部βログイン

外部テスターには、管理者APIまたは`scripts/create_tester_account.py`で発行した学生アカウントを共有します。

ローカル検証用デモアカウント:

- メールアドレス: `student@ce108.local`
- パスワード: `demo1234`

## 検証

```bash
npm run typecheck
npm run lint
npm test
npm run build
npm run test:e2e
```

Playwright のブラウザーが未導入の場合は、次を一度だけ実行します。

```bash
npm run test:e2e:install
```

## v0.4.2 の範囲

- 学生用モバイル画面のみを対象にします。
- ホーム、今日の5問、復習、理解度、学習戦略、ノートAI復習、フィードバック送信を対象にします。
- ノートAI復習は外部AI APIを使わない簡易生成です。生成内容は誤る可能性があります。
- LINE 本番接続、React 以外への置換、PostgreSQL 化、国家試験過去問の追加は行いません。
- 回答前の問題詳細では、正解コード、数値正解、選択肢解説、解説本文を表示しません。
