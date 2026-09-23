# ASSUMPTIONS（仕様判断・確認済み公式ドキュメント・バージョン）

## 環境・バージョン
| 項目 | 値 | 確認日 | 根拠 |
|---|---|---|---|
| n8n | 2.40.5（npm `latest`／`stable`） | 2026-09-23 | https://registry.npmjs.org/n8n/latest（engines: node >= 24） |
| Node.js（n8n 実行用） | 24.21.0（LTS Krypton） | 2026-09-23 | https://nodejs.org/dist/index.json |
| n8n-mcp | 2.87.0 | 2026-09-23 | https://registry.npmjs.org/n8n-mcp/latest |
| 作業環境 | Linux コンテナ、Docker CLI あり・デーモン無し | 2026-09-23 | `docker ps` が接続エラー |

## 確認した公式ドキュメント
| 目的 | URL | 確認日 |
|---|---|---|
| n8n-mcp 導入（README） | https://github.com/czlonkowski/n8n-mcp/blob/main/README.md | 2026-09-23 |
| n8n-mcp Claude Code 設定 | https://github.com/czlonkowski/n8n-mcp/blob/main/docs/CLAUDE_CODE_SETUP.md | 2026-09-23 |
| n8n-skills 導入 | https://github.com/czlonkowski/n8n-skills/blob/main/README.md | 2026-09-23 |
| n8n 公開 API 認証（`X-N8N-API-KEY`、`/api/v1`） | https://docs.n8n.io/connect/n8n-api/authentication.md | 2026-09-23 |
| n8n 公開 API エンドポイント | https://docs.n8n.io/connect/n8n-api/api-reference.md | 2026-09-23 |
| 環境変数（deployment） | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/deployment.md | 2026-09-23 |
| 環境変数（endpoints: `WEBHOOK_URL` は 2.35 で `N8N_WEBHOOK_URL` の別名に） | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/endpoints.md | 2026-09-23 |
| 環境変数（task runners） | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/task-runners.md | 2026-09-23 |
| タスクランナー設定 | https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-task-runners.md | 2026-09-23 |
| タイムゾーン | https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/timezone-and-localization.md | 2026-09-23 |
| Pin / mock data | https://docs.n8n.io/build/work-with-data/pin-and-mock-data.md | 2026-09-23 |
| Extract From File ノード | https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.extractfromfile.md | 2026-09-23 |
| Google Sheets ノード | https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.googlesheets.md 、 .../sheet-operations.md | 2026-09-23 |
| Google Drive Trigger | https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.googledrivetrigger.md | 2026-09-23 |
| Gmail Trigger | https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.gmailtrigger.md 、 .../poll-mode-options.md | 2026-09-23 |
| Gmail ノード（message / draft） | https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.gmail/message-operations.md 、 .../draft-operations.md | 2026-09-23 |
| Schedule Trigger | https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger.md | 2026-09-23 |
| Slack ノード | https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.slack.md | 2026-09-23 |
| Code ノード | https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.code.md | 2026-09-23 |
| Error Trigger | https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.errortrigger.md | 2026-09-23 |
| Edit Fields (Set) | https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.set.md | 2026-09-23 |
| HTTP Request | https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest.md | 2026-09-23 |
| Sticky Note | https://docs.n8n.io/build/understand-workflows/workflow-components/add-notes-and-documentation.md | 2026-09-23 |

## 仕様判断
| # | 判断 | 理由 | 日付 |
|---|---|---|---|
| A1 | （更新）成果物は専用リポジトリ https://github.com/Atsushi-Odajima/tools の直下に置く（2026-09-23 ユーザー指示）。当初は `4S-search/n8n-payment-templates/` 配下で作業した | 専用リポジトリの指定があったため。`4S-search` 側の複製は移設後に削除した | 2026-09-23 |
| A2 | 作業環境では Docker の代わりに npm 版 n8n 2.40.5 を Node 24 で起動する | Docker デーモン無し。n8n 2.40.5 は Node >= 24 必須（npm engines）。バージョンは Docker イメージ `latest` と同じ系列 | 2026-09-23 |
| A3 | `WEBHOOK_URL` は compose では `N8N_WEBHOOK_URL` を使う | 2.35.0 で `WEBHOOK_URL` は非推奨の別名になった（endpoints ドキュメント） | 2026-09-23 |
| A4 | 開発用 n8n は `N8N_RUNNERS_MODE=internal`（既定） | 単一プロセスで完結させるため。README では本番は external 推奨と注記 | 2026-09-23 |
| A5 | Google／Slack Credential が無い間は pinned data で Google ノードを固定し、Code ノードのロジックを実行検証する | [HUMAN] H1/H2 未完了。pinned data は公式機能（Pin and mock data） | 2026-09-23 |
| A6 | 銀行 CSV の Shift_JIS 復号は Code ノード（`new TextDecoder('shift_jis')`）で行い、`Extract From File` は使わない | n8n 2.40.5 の `Extract From File`（CSV）の `options.encoding` 選択肢は ascii / latin1 / ucs-2 / ucs2 / utf-8 / utf16le / utf8 のみで Shift_JIS が無い（n8n-mcp `get_node nodes-base.extractFromFile search_properties encoding` と `n8n-nodes-base/dist/nodes/SpreadsheetFile/v2` の実装で確認）。UTF-8 BOM 除去・`skip_rows` も同じ Code ノードで処理し、経路を1本にする | 2026-09-23 |
| A7 | ローカル起動スクリプトは `N8N_LISTEN_ADDRESS=127.0.0.1` を既定にする | IPv6 が無いコンテナでは n8n 既定の `::` にバインドできず起動に失敗した（実測） | 2026-09-23 |
| A8 | n8n のオーナー作成・API キー発行は UI と同じ内部 REST（`POST /rest/owner/setup`、`POST /rest/login`、`GET /rest/api-keys/scopes`、`POST /rest/api-keys`）で自動化した。キーはリポジトリ外の作業領域にのみ保存 | [HUMAN] 作業の代替。公開 API（`/api/v1`、`X-N8N-API-KEY`）で疎通確認済み | 2026-09-23 |
| A9 | P0 の Slack 疎通は、Slack Credential が無いため「Manual Trigger → Set → HTTP Request → 同一 n8n の Webhook（受信シンク）」で代替し、通知ノードの実行成功をもって P0 ゲートとする。Slack 実投稿は BLOCKERS H2 | Slack ワークスペースと App 作成は人間のみ可能 | 2026-09-23 |
| A10 | `.mcp.json` に `WEBHOOK_SECURITY_MODE=moderate` と `N8N_MCP_TELEMETRY_DISABLED=true` を追加 | n8n-mcp 2.87.0 は既定 `strict` で `http://localhost:5678` への API 接続を SSRF 保護で拒否する（実測、公式 docs/SECURITY_HARDENING.md に `moderate` が localhost を許可すると明記）。テレメトリは初回起動時の案内に従い無効化 | 2026-09-23 |
| A11 | P3 のテストは pinned data を「ワークフローに保存」して手動実行する（`PATCH /rest/workflows/{id}` の `pinData` → `POST /rest/workflows/{id}/run` with `triggerToStartFrom`）。実行ボディ内だけの pinData は無視される（実測）。バイナリ（base64 の `binary.data.data`）も pinned data として実行に使える（実測、実行 ID 6） | UI は「バイナリは pin 不可」だが、保存済み pinData に含めれば実行エンジンは受け付ける。Google Drive のダウンロード結果（CSV バイナリ）をこれで固定して Code ノードを実機検証できる | 2026-09-23 |
| A12 | Code ノード（タスクランナー内部モード、n8n 2.40.5）で `TextDecoder('shift_jis')`・`Buffer`・`String.normalize('NFKC')`・`DateTime`（Luxon）・`$now.setZone()`・`$('Config').first().json`・`this.helpers.getBinaryDataBuffer(0,'data')` が動作することを実行 ID 5/6 で確認。`process` は未定義 | テンプレ01 の CSV 復号・正規化・日付処理を Code ノードで実装できる根拠 | 2026-09-23 |
| A13 | Set ノード（v3.4/3.5）で `includeOtherFields: true` とし、`SOURCE = {{ $prevNode.name }}` を持たせると、複数トリガーが1つの Config に合流しても発火元を判別できる（実行 ID 5 で `SOURCE: "Manual"` を確認） | Config を1つに保つ設計（§4.1）を満たすため | 2026-09-23 |

## 外部 API（テンプレ01 の通知で使用）
| API | 確認した事実 | 出典 | 確認日 |
|---|---|---|---|
| LINE Messaging API push | `POST https://api.line.me/v2/bot/message/push`、`Authorization: Bearer {channel access token}`、JSON `{ "to": "<userId>", "messages": [ { "type": "text", "text": "..." } ] }`（messages は 1〜5 件、`notificationDisabled` 任意） | 公式 OpenAPI 定義 https://github.com/line/line-openapi/blob/main/messaging-api.yml（`PushMessageRequest` / `TextMessage` / `securitySchemes.Bearer`）、参照ページ https://developers.line.biz/en/reference/messaging-api/#send-push-message | 2026-09-23 |
| Chatwork メッセージ投稿 | `POST https://api.chatwork.com/v2/rooms/{room_id}/messages`、ヘッダ `x-chatworktoken: {API トークン}`、`Content-Type: application/x-www-form-urlencoded`、パラメータ `body`（必須、1〜65,535 文字）・`self_unread`（任意 0/1）。成功時 `{ "message_id": "..." }`、429 でレート制限 | https://developer.chatwork.com/reference/post-rooms-room_id-messages | 2026-09-23 |
| Gmail Trigger の本文取得 | `simple: false` にすると raw メールを解析し `text` / `html` / `subject` / `from` / `to` / `date` / `headers` を返す（`simple: true` は id / threadId / labels / ヘッダのみで本文なし）。メモリ使用量が増える旨の公式注記あり | n8n 2.40.5 `GmailTrigger.node.js`（`format: 'metadata'` vs `parseRawEmail`） | 2026-09-23 |
| Google Sheets v4.7 upsert | `operation: appendOrUpdate`、`columns` は resourceMapper（`mappingMode: autoMapInputData` ＋ `matchingColumns: ["invoice_id"]`）、`documentId` / `sheetName` は resourceLocator（`mode: id` / `mode: name` で式指定可）、`authentication: oAuth2` | n8n-mcp `get_node nodes-base.googleSheets detail=full` | 2026-09-23 |
| A14 | Sticky Note の `color` 番号: 1=黄（判定）、3=赤（注意）、4=緑（出力）、5=青（入力）。2=橙、6=紫、7=灰は未使用 | n8n 2.40.5 エディタの CSS 変数 `--sticky--color--background--variant-N`（1: yellow, 2: gold, 3: red, 4: green, 5: blue, 6: purple, 7: neutral）で確認 | 2026-09-23 |
| A15 | Code ノードの原本を `templates/0X-*/code/*.js` に置き、`workflow.json` の `jsCode` に同一文字列を埋め込む。`tests/unit/run-code-node.mjs` で n8n 外でも同じコードを fixtures に対して実行できる | §4.6「ロジックは DESIGN.md に疑似コードで併記」に加え、実コードの単体実行を可能にして P3 の検証を速く・再現可能にするため。販売物は `workflow.json` 単体で完結する（`code/` は同梱するが必須ではない） | 2026-09-23 |
| A16 | テンプレ01 の名義正規化（`normalizePayer`）はトークン除去を 2 段階で行う：先に「どこでも除去」するトークン（`振込`／`フリコミ`／`株式会社` 等）を消し、その後に前株 `X)`（先頭のみ、先頭の数字列は許容）・後株 `(X`（末尾のみ）を当てる（`DESIGN.md` §6.6、CASES T03） | 長さ降順の 1 回走査だと `振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ` は `カ)` が先頭に来る前に試されて残り `カサンプルシヨウジ` になる（fixture A-1/A-6/A-11/A-13 で Node により確認）。`txn_id` が変わるため冪等性に影響する。fixture の期待値は 2 段階版で計算 | 2026-09-23 |
| A17 | テンプレ01 の `MAIL_PARSERS` 既定値の正本は `fixtures/mail_parsers.example.json`。bankY は表形式（コロン無し）に合わせ `Amount\s+…`／`Remitter\s+…`／`Transaction Date\s+…`、bankX の `date_regex` は `(?:日付|お取引日|取引日)[：:]` のラベル付き（CASES T05） | `DESIGN.md` §4 の暫定値（`Amount[：:]` 形式）は fixture Y で `parser_no_capture` になることを Node で確認。P2 は Config の既定値をこの JSON から埋め込む。bankX のラベル要求は口座番号等の誤キャプチャ防止 | 2026-09-23 |
