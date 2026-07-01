# Changelog

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

