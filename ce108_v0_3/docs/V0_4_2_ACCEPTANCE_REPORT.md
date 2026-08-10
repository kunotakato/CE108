# CE108 v0.4.2 Acceptance Report

## Release Name

CE108 v0.4.2 Tester Readiness

## Purpose

最初の外部テスター1人にCE108を渡し、スマートフォンで毎日学習を続けられるかを検証するための固定版です。新しい大規模機能ではなく、外部テスター運用の再現性と安全性を整えます。

## Implemented Scope

- 管理者APIによる外部βテスター学生作成。
- `scripts/create_tester_account.py`によるテスター学生作成。
- モバイルログイン画面のv0.4.2表示。
- 公開環境ではデモ入力を既定で出さない設定。
- ノートAI画面の個人情報・患者情報入力禁止文言。
- ノートAI生成内容が誤る可能性の明示。
- 外部βガイドと最初のテスターRunbook。

## Acceptance Criteria

- `/health` returns `0.4.2`.
- Demo login still works locally.
- Admin can create a tester student account.
- A created tester student can log in.
- Student cannot access tester-account admin API.
- Mobile typecheck passes.
- Mobile unit tests pass.
- Mobile production build passes.
- Python unit tests pass.
- `scripts/create_tester_account.py` works against a fresh SQLite DB.

## Test Result

- Python 3.12: `.venv312/bin/python -m unittest discover -s tests -v` passed, 43 tests.
- Mobile typecheck: `tsc --noEmit` passed.
- Mobile unit tests: `vitest run` passed, 6 tests.
- Mobile production build: `next build` passed.
- Compileall: `.venv312/bin/python -m compileall ce108 api.py app.py scripts` passed.
- Database init: `.venv312/bin/python scripts/init_db.py` passed.
- Tester script: `scripts/create_tester_account.py` created a student account against a fresh SQLite DB.

## Startup Result

- FastAPI started on `127.0.0.1:8012`.
- `/health` returned `{"status":"ok","version":"0.4.2"}`.
- Demo student login API succeeded.
- `/api/users/me` returned the student user.
- `/api/study/today` returned 5 items.
- Admin tester-student creation API created a student account.
- Mobile Next.js dev server started on `127.0.0.1:3012`.

## Manual Review Result

- Mobile login screen showed `Tester Readiness v0.4.2`.
- Public-default login screen did not show demo autofill.
- Login screen showed sample-content, non-prediction, and privacy warnings.
- Demo student login reached onboarding and home.
- Home showed today's learning status and note AI link.
- Note AI page showed privacy and generated-content warning text.
- Note AI generated review questions from a non-private sample note.

## Remaining Limitations

- 収録問題はCE108オリジナルサンプルで、公式過去問ではありません。
- ノートAIは外部AI APIを使わない簡易生成で、内容が誤る可能性があります。
- LINE本番接続は未完了です。
- 決済、招待メール自動送信、利用規約同意管理は未実装です。
- SQLite運用のため、大人数同時利用はv0.5以降で再評価が必要です。

## v0.3/v0.4 Compatibility

- React移行、PostgreSQL移行、国家試験過去問追加は行っていません。
- DBスキーマは変更していません。
- 既存のStreamlit教員・管理者画面は維持しています。
