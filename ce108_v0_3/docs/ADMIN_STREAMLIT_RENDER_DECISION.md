# CE108 Admin Streamlit Render Decision

## Decision

v0.4系では、管理者Streamlit画面をすぐにRenderで外部公開しません。

## Reason

現在の公開構成は次の2サービスです。

- `ce108-api`: FastAPI backend
- `ce108-mobile`: Next.js student mobile frontend

管理者Streamlit画面は、問題登録、問題承認、CSV登録、βフィードバック分析を扱います。外部公開すると、管理者ログイン画面、DB接続、Cookie/session、管理操作の誤操作、デモ管理者パスワード残存のリスクが増えます。

## Current Safe Operation

管理者フィードバック確認は、次のどちらかで行います。

- ローカルStreamlit管理画面
- FastAPIの管理者API

詳細手順は `docs/ADMIN_FEEDBACK_OPERATIONS.md` に固定しています。

## Conditions To Publish Admin Streamlit

Renderで管理者Streamlitを公開する場合、最低限以下を満たしてから実施します。

- [ ] `admin@ce108.local` の初期パスワードを強固なものへ変更
- [ ] 管理者URLを一般テスターへ共有しない
- [ ] `CE108_DB_PATH=/var/data/ce108.db` の共有方針を確認
- [ ] FastAPIとStreamlitが同じDBを安全に参照できることを確認
- [ ] Render Diskのバックアップ手順を用意
- [ ] 管理者操作の監査ログを確認
- [ ] 公開前に学生アカウントで管理者メニューへ入れないことを確認
- [ ] 費用増加を許容する

## Recommended Next Step

最初の外部テスター1人の段階では、管理者Streamlitはローカル運用のままにします。フィードバック確認はローカル管理画面で行い、必要時だけ管理者APIを使います。

外部テスターが3から5人に増え、毎日フィードバックを見る必要が出てから、管理者専用Renderサービスを追加する判断に進みます。
