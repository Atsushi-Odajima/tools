# BLOCKERS（[HUMAN] 待ち事項）

エージェントが代替できない作業。各項目に「何が必要か」「どう確認するか」「エージェント側の暫定対応」を書く。

## 一覧

| # | 項目 | 必要なもの | 確認方法 | 暫定対応 |
|---|---|---|---|---|
| H1 | Google OAuth クライアント（Sheets / Drive / Gmail / Calendar） | Google Cloud でプロジェクト作成、OAuth 同意画面、Web クライアント ID/Secret、n8n に 4 種の Google OAuth2 Credential を登録 | n8n の Credentials 画面で各 Credential が「Connected」 | Google 系ノードは pinned data（固定出力）で実行し、Code ノードのロジックを検証。ライブ検証は SETUP の手順で買い手／オーナーが実施 |
| H2 | Slack テストチャンネル `#n8n-test` と Slack Credential | Slack ワークスペースで App 作成、`chat:write` スコープ、Bot をチャンネルに招待、n8n に Slack Credential 登録 | Manual Trigger → Slack の最小ワークフローで投稿が届く | P0 ゲートはローカルの Webhook 受信（HTTP Request → 同一 n8n の Webhook ノード）で「通知ノードまで到達し送信を試みた」ことを実行ログで確認する。Slack への実投稿は未確認 |
| H3 | Stripe テストモード API キー・Stripe CLI ログイン | Stripe アカウント、`stripe login` | `stripe listen` が接続 | 02・04 着手時に fixtures（Stripe 公式ドキュメントのイベント例）で代替 |
| H4 | PayPal Sandbox アプリ・Webhook ID | PayPal Developer アカウント | Sandbox Webhook Simulator から到達 | 02・04 着手時に fixtures で代替 |
| H5 | freee テスト事業所・OAuth アプリ | freee 開発者アカウント | OAuth 認可が通る | 02 は `dry_run` / `csv` モードで検証し freee モードは未検証と明記 |
| H6 | LINE Messaging API チャネル（任意） | channel access token、userId | push が届く | HTTP Request ノードの設定のみ用意し未送信 |
| H7 | Chatwork API トークン（任意） | トークン、room_id | 投稿が届く | 同上 |
| H8 | Docker Desktop | この作業環境には Docker デーモンが無い | `docker ps` | npm でインストールした同一バージョンの n8n を `infra/run-n8n-local.sh` で起動（DB は SQLite、設定は compose と同じ） |

## 備考
- H1 と H2 が無い間、テンプレ01 の P3 は「Google ノードの pinned data ＋ Code ノードの単体実行」で行い、`tests/RESULTS.md` にどのケースがライブ未検証かを明記する。
