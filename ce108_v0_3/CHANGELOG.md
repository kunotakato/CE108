# Changelog

## v0.4.1-web-deployment-prep - 2026-07-21

### Added
- 外部URLで小規模β検証を行うためのデプロイ計画を追加。
- `CE108_CORS_ORIGINS`でFastAPIのCORS許可オリジンを設定可能に変更。
- 外部βテスター向けガイドを追加。
- 学生モバイル画面にフィードバック送信画面を追加。
- `/api/beta/feedback`で学生のβフィードバックを保存。

### Fixed
- ホーム画面の同時API呼び出しで日次プラン生成が競合する問題を修正。

### Verified
- Python unittest 29件成功。
- `python -m compileall app.py api.py ce108 scripts tests`成功。
- Mobile unit test 6件成功。
- `npm run typecheck`、`npm run lint`、`npm run build`成功。

## v0.4.0-daily-learning-beta - 2026-07-02

### Added
- 学生が毎日開くためのホーム画面、連続学習、7日間の進捗、次アクション表示を追加。
- 復習キューAPIとモバイル復習画面を追加。
- 教員向けに担当学生の支援サマリー、リスク、未学習日数、復習待ち、苦手分野を追加。
- 管理者向けに問題品質チェック、公開準備状況、権利状態、解説 completeness の確認を追加。
- FastAPIに`/api/study/daily-status`、`/api/study/reviews`、`/api/teacher/support`、`/api/admin/quality`を追加。

### Verified
- Python unittest 26件成功。
- Mobile unit test 5件成功。
- Mobile E2E 7件成功。
- `npm run typecheck`、`npm run lint`、`npm run build`成功。
- FastAPIとモバイル主要画面をローカルで確認。

### Release Notes
- tag: `v0.4.0-daily-learning-beta`
- v0.4はローカルβ検証用リリース。
- LINE本番接続、国家試験過去問原文の追加、PostgreSQL移行、外部AI必須化は含まない。

## v0.3.0-internal-alpha - 2026-07-01

### Fixed
- Python 3.12.13の新規仮想環境で依存導入、DB初期化、テスト、起動確認を実施。
- `requirements.txt`にFastAPI TestClient実行に必要な`httpx2`を明示。
- 回答前の問題詳細APIから正答、数値正答、選択肢解説、問題解説本文が露出しないよう修正。
- `python scripts/init_db.py`がプロジェクトルート外のimport問題で失敗しないことを確認。
- Streamlitの学生、教員、管理者の主要画面をPython 3.12環境で確認。

### Release Notes
- DBファイルは再生成可能なローカル成果物として`data/*.db`でGit管理対象外。
- 収録問題はCE108オリジナルサンプル。国家試験過去問原文は含まない。
- LINE/LIFFは署名検証、テスター希望保存、HTML雛形まで。本番接続は未実施。
