# CE108 Admin Feedback Operations

## Purpose

外部βテスターの意見を確認し、どの不満が集中しているか、どれを早急に直すべきかを判断するための運用手順です。

## Streamlit管理画面で見る

ローカルで管理画面を起動します。

```bash
cd /Users/taka.k/Documents/AIシステム/ce108_v0_3
.venv312/bin/streamlit run app.py --server.port 8504
```

ブラウザで開きます。

```text
http://localhost:8504/
```

管理者でログインします。

```text
admin@ce108.local
demo1234
```

左メニューで次を選びます。

```text
βフィードバック分析
```

## 画面で確認する項目

- テスター活動状況
- 総フィードバック件数
- 平均評価
- 早急対応件数
- カテゴリ別件数
- 対応優先度
- 集中している論点
- 画面別の集中箇所
- フィードバック一覧
- CSV出力

## APIで見る

管理者トークンを取得します。

```bash
curl -X POST https://ce108-api.onrender.com/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@ce108.local&password=YOUR_ADMIN_PASSWORD"
```

フィードバック集計を確認します。

```bash
curl https://ce108-api.onrender.com/api/admin/beta-feedback/summary \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

一覧を確認します。

```bash
curl https://ce108-api.onrender.com/api/admin/beta-feedback \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

テスター活動状況を確認します。

```bash
curl https://ce108-api.onrender.com/api/admin/tester-students/activity \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## Priority Rules

- `高`: 不具合、低評価、ログイン不可、通信エラー、回答保存不可、画面が開けない
- `中`: 問題・解説の改善、要望、評価3
- `低`: 高評価の感想、緊急性の低いコメント

## Current Limitation

v0.4系では、外部公開済みの管理者用Web画面はFastAPI管理APIとローカルStreamlit管理画面です。Streamlit管理画面をRender上で公開する場合は、管理者専用URL、強い管理者パスワード、CORS、DB Disk共有、アクセス制限を確認してから別サービスとして作成します。
