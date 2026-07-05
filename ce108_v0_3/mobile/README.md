# CE108 Mobile Alpha v0.3.5

学生がスマートフォンで毎日5問を解くための Next.js/TypeScript フロントエンドです。教員・管理者画面は従来どおり Streamlit を利用します。

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

## デモログイン

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

## v0.3.5 の範囲

- 学生用モバイル画面のみを対象にします。
- LINE 本番接続、AI出題、React 以外への置換、PostgreSQL 化、国家試験過去問の追加は行いません。
- 回答前の問題詳細では、正解コード、数値正解、選択肢解説、解説本文を表示しません。
