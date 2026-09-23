# P3 結果 — g3-schedule-error（R18 / R19 / R19-twice / R21 / R22 / R12 / DESIGN §8.4 実行順）

EN summary: All executions of this batch behaved as `tests/CASES.md` §2 expects, on private copies of `workflow.json` / `error-handler.json` in the local n8n 2.40.5 (copies, sink, throwaway and dummy credentials deleted afterwards). R18 (Schedule re-match after bank_A: the ledger row `2026-09-11|66000|ミホンシヨウカイ|` goes `unmatched` → `matched INV-2026-021`, `invoice_update INV-2026-021 paid/auto/66000`, `rematched=1, n=0`, only that one `txn_row`, notification `■ 自動消込 ・2026-09-11 振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ ¥66,000 → INV-2026-021` reached both sinks), R19 (Schedule with no change → `Match Invoices` = summary only, `Route Match Results [0,0,1]`, `Update Invoices` / `Upsert Transactions` not executed, `Build Notification` returned `[]`, nothing after it ran, no sink delivery), R19-twice (two consecutive Schedule runs → identical node set and byte-identical node outputs, no writes), R21 (Error Workflow: the pinned execution-error and trigger-error shapes both produce the expected title / body; in addition a REAL production failure of a throwaway workflow invoked the error copy in `mode: error` (execution 173) and both sinks received `【n8n エラー】…` with workflow name / failed node / message / execution URL), R22 (`TRIGGERS_ENABLED.drive|gmail|schedule = false` one at a time and `SOURCE = "Manual"` → `Route by Source` fallback → `Skip Disabled Trigger`, nothing else executed, success, no notification; `gmail = true` restores the R10 result), R12 (N/A, documented). Execution-order evidence (DESIGN §8.4): `Update Invoices` → `Upsert Transactions` → `Build Notification` in runData order and by `startTime` in every run that wrote (146 / 151 / 158). Verdict: every case **PASS** (PIN class; sheet writes pending H1). **Two n8n 2.40.5 findings for the orchestrator (not workflow.json defects, but SETUP must say so): (1) an Error Workflow is only invoked when it is itself ACTIVE (`workflow-execution.service.js loadErrorWorkflowData` → log `Calling Error Workflow for "…". Workflow "…" is not active and cannot be executed`, observed for executions 167 / 168); (2) activation validates credentials of every enabled, connected node, so `error-handler.json` cannot be activated while `Notify Slack` / `Notify Email` have no credential (`Cannot publish workflow: … Missing required credential: slackApi / gmailOAuth2`) — the buyer must assign the credentials or disable the unused Notify nodes (disabled nodes are skipped by the validation). The same applies to the main workflow.**

| 項目 | 値 |
|---|---|
| 実行日 | 2026-09-23（ローカル n8n 2.40.5、`http://localhost:5678`） |
| ワークフロー複製 | 本体 `m3C9NLhdSCUbSQEe`（`[P3-g3-schedule-error] [Odaji] 01 Bank Deposit Reconciliation v1.0.0`、`settings.errorWorkflow` = `H8dkT8fJ4oOAJcqG`、`GET /api/v1/workflows/m3C9NLhdSCUbSQEe` の `settings` で確認）／Error Workflow `H8dkT8fJ4oOAJcqG`（`[P3-g3-schedule-error] [Odaji] 01 Error Handler v1.0.0`）。`workflow.json` / `error-handler.json` から `POST /api/v1/workflows` で作成し、終了時に両方 `DELETE`（`GET` は `Not Found`） |
| 使い捨て | `zrFdEKFsbuBJAnmK`（`[P3-g3-schedule-error] Throw for error-handler`：Webhook v2 `POST p3-g3-schedule-error/throw` → Code `throw new Error('P3 error-handler check')`、`settings.errorWorkflow` = `H8dkT8fJ4oOAJcqG`）。CASES R21 の Schedule 毎分の代わりに Webhook の本番実行（`mode: webhook`）で失敗させた。終了時に無効化して削除 |
| シンク | LINE: `p0-sink`（`VDtPVF2gV4fnId1X`）／Chatwork: 自前 `[P3-g3-schedule-error] Chatwork sink`（`BktwWtxQHItWC1NB`、Webhook v2 `webhookId = p3-g3-schedule-error`、path `p3-g3-schedule-error/rooms/:roomId/messages`。動的パスの本番 URL は `http://localhost:5678/webhook/p3-g3-schedule-error/p3-g3-schedule-error/rooms/<roomId>/messages`（`/webhook/<webhookId>/<path>`。`/webhook/<path>` だけでは 404：実行 144 の `Notify Chatwork` エラー出力で確認し、以後は `CHATWORK_API_BASE_URL = http://localhost:5678/webhook/p3-g3-schedule-error/p3-g3-schedule-error` に置換）。終了時に無効化して削除 |
| Credential | ダミー Header Auth `[P3-g3-schedule-error] LINE Messaging API`（`aAybXoTbiQ66w55s`）／`[P3-g3-schedule-error] Chatwork API`（`0h1Jyw27kF5coNNJ`）を `POST /api/v1/credentials` で作成し、自分の複製（本体・Error Workflow）の `Notify LINE` / `Notify Chatwork` にだけ設定（A28）。終了時に削除 |
| Error Workflow 複製への変更 | 本番実行（pinned 不使用）で通知先をローカルにするため、複製の `Config` ノードの JSON を `NOTIFY_CHANNELS ["line","chatwork"]`、`LINE_API_URL` = p0-sink、`CHATWORK_API_BASE_URL` = 上記、`LINE_TO_USER_ID Ug3scheduleerror`、`CHATWORK_ROOM_ID g3` に変更。さらに有効化のため `Notify Slack` / `Notify Email` を `disabled: true` にした（後述の所見 2）。`error-handler.json` 自体は変更していない |
| 実行方法 | `tests/pins/README.md` の手順（A11）。各実行の前後に `PATCH /rest/workflows/{id}` で `pinData = {}` にリセット → pin を保存 → `POST /rest/workflows/{id}/run` に `triggerToStartFrom` を付けて実行。pin ファイルは README のシンク URL のまま保存し、実行直前にメモリ上で `CHATWORK_API_BASE_URL` → 自分のシンク、`LINE_TO_USER_ID` `Utest` → `Ug3scheduleerror`、`CHATWORK_ROOM_ID` `1` → `g3` に置換（共用 `p0-sink` で自分の受信を識別するため） |
| 保存した実行 JSON | `<scratchpad>/p3-scratch/g3-schedule-error/exec-<id>.json`（`GET /api/v1/executions/{id}?includeData=true`、削除前に取得）：144, 146, 149, 150, 151, 154, 155, 156, 157, 158, 161, 164, 167, 168, 169, 170, 172, 173。シンク側は `sink-exec-<id>.json`：145, 147, 148, 152, 153, 159, 160, 162, 163, 165, 166, 171, 174, 175 |
| 新規 pin | `tests/pins/make_pins_g3_schedule_error.py` が既存 pin（`drive` / `schedule` / `schedule-rematch` / `error-handler`、無変更）と `tests/pins/R18-bank-A-invoice-updates.json`（実行 146 の `invoice_update` 8 件）から `R18-schedule-rematch-after-A` / `R19-schedule-no-change` / `R22-drive-disabled` / `R22-schedule-disabled` / `R21-trigger-error` を生成。`make_pins.py` と既存 pin は変更していない（README に追記） |
| 区分 | すべて **PIN**（R21 は本番実行の Error Trigger も確認）。`Update Invoices` / `Upsert Transactions` は pinned（`[{ok:true}]`）で、それらに**入力されたアイテム**（`Route Match Results` 出力 0/1）を判定した。実セル・シート差分ゼロは LIVE-G（H1）待ち |

---

## 前提：bank_A を 1 回流した状態（実行 146）

- **実行 ID**：**146**（success、`Watch Drive Folder` から `tests/pins/drive.pin.json`）。実行 144 は同じ pin の初回（Chatwork シンク URL 誤りで `Notify Chatwork` が 404 のエラー出力 → `Check Notification Results {attempted 2, ok 1, failed 1}` で success。ハーネス側の設定ミスで、ケース判定には使わない）
- `Match Invoices [20]` = `invoice_update` 8（INV-001 paid/auto 33000、INV-002 paid/fee_deducted 54780、INV-003 paid/auto 9800、INV-004 paid/amount_only 128000、INV-005 + INV-006 paid/combined、INV-007 partial/auto 100000、INV-012 paid/auto 27500）＋ `txn_row` 11 ＋ summary `{n:11, a:4, b:3, c:4, rematched:0, skipped_existing:0, warnings:[]}`。`txn_row` 11 件は `schedule-rematch.pin.json` の台帳行（SMOKE 実行 57 由来）と `imported_at` 以外すべて一致
- この 8 件を seed に適用した `invoices`（20 行）と、seed ＋ 11 行の `transactions`（12 行）を R18 / R19 の pinned data にした（`R18-bank-A-invoice-updates.json`）

## R18 Schedule 再突合で前日 unmatched が matched になる

- **区分**：PIN（実セルは LIVE-G）
- **ワークフロー**：`m3C9NLhdSCUbSQEe` ／ **実行 ID**：**151**（success、最終ノード `Check Notification Results`）／シンク：p0-sink 152、Chatwork sink 153
- **pin**：`tests/pins/R18-schedule-rematch-after-A.pin.json`（`Run Daily Rematch` `{timestamp: 2026-09-24T09:00:00.000+09:00}`、`Config`、`Read Invoices` = seed に A の更新 8 件を反映した 20 行 ＋ `INV-2026-021`（C-009、株式会社見本商会、alias `カ)ミホンシヨウカイ,ミホンシヨウカイ`、66000 JPY、2026-09-15 / 2026-10-15、unpaid）、`Read Transactions` = seed ＋ A の 11 行（A-11 `2026-09-11|66000|ミホンシヨウカイ|` は `unmatched`、`suggested_invoice_ids INV-2026-015,INV-2026-017`、`imported_at 2026-09-23T16:24:12+09:00`））
- **観測**：
  - 実行順 `Run Daily Rematch [1] → Config [1] → Route by Source [0,0,1,0]`（schedule 出力）`→ Collect Transactions [1] → Read Invoices [21] → Read Transactions [12] → Normalize Payer [1] → Match Invoices [3] → Route Match Results [1,1,1] → Update Invoices → Upsert Transactions → Build Notification → … → Check Notification Results`
  - `Update Invoices` の入力（`Route Match Results` 出力 0）：`{invoice_id: INV-2026-021, status: paid, paid_amount: 66000, paid_date: 2026-09-11, matched_txn_ids: "2026-09-11|66000|ミホンシヨウカイ|", match_confidence: auto, fee_deducted: 0}` の 1 件
  - `Upsert Transactions` の入力（出力 1）：`{txn_id: "2026-09-11|66000|ミホンシヨウカイ|", source: bank_csv, txn_date: 2026-09-11, payer_name_raw: "振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ", payer_name_norm: ミホンシヨウカイ, amount: 66000, memo: "", imported_at: "2026-09-23T16:24:12+09:00", matched_invoice_ids: INV-2026-021, status: matched, suggested_invoice_ids: ""}` の 1 件のみ。`imported_at` は台帳の元の値を保持。A-9（ambiguous）・A-12・A-14（unmatched）の `txn_row` は出ていない（候補に変化なし）
  - summary：`{n:0, a:0, b:0, c:0, rematched:1, skipped_existing:0, warnings:[], auto:[{txn_date: 2026-09-11, payer_raw: "振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ", amount: 66000, invoice_ids: [INV-2026-021], reason: auto, remaining_after: 0}], needs_review:[], ambiguous:[], unmatched:[]}`
  - `Build Notification`：title `【入金消込 2026-09-23】処理 0件｜自動消込 0｜要確認 0｜未消込 0`、body_text `…\n\n■ 自動消込\n・2026-09-11 振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ ¥66,000 → INV-2026-021`。p0-sink 152 の `messages[0].text` と Chatwork sink 153 の `body`（`params.roomId = g3`）が同文。`Check Notification Results {attempted 2, ok 2, failed 0}`
- **期待（CASES R18 / A27）**：`inv[INV-2026-021] = paid, auto, 66000, paid_date 2026-09-11, matched_txn_ids 2026-09-11|66000|ミホンシヨウカイ|`；`txn[2026-09-11|66000|ミホンシヨウカイ|]` が `matched, INV-2026-021, suggested ""`、`imported_at` 保持、`txn_row` はこの 1 件のみ；`rematched=1, n=0`；通知あり、`■ 自動消込` に上記 1 行；タイトルは A27 のとおり `処理 0件｜自動消込 0｜要確認 0｜未消込 0`
- **判定**：**PASS**（pinned; live write pending H1）

## R19 Schedule で変化なし → 通知なし・書込みなし

- **区分**：PIN ／ **実行 ID**：**149**（success、最終ノード `Build Notification`）
- **pin**：`tests/pins/R19-schedule-no-change.pin.json`（R18 の pin から `INV-2026-021` を除いたもの＝A 直後の状態。`Read Invoices` 20、`Read Transactions` 12）
- **観測**：実行されたノードは `Run Daily Rematch, Config, Route by Source [0,0,1,0], Collect Transactions, Read Invoices [20], Read Transactions [12], Normalize Payer（existing 12 件）, Match Invoices [1], Route Match Results [0,0,1], Build Notification [[]]` の 10 個のみ。`Match Invoices` の出力は summary 1 件 `{n:0, a:0, b:0, c:0, rematched:0, skipped_existing:0, skipped_duplicate_in_batch:0, warnings:[], auto:[], needs_review:[], ambiguous:[], unmatched:[]}`。`invoice_update` 0、`txn_row` 0。`Update Invoices` / `Upsert Transactions` / `Check Slack Enabled` 以降は runData に無い（未実行）。`Build Notification` の出力 `[[]]`（空）。両シンクとも新規受信なし
- **期待（CASES R19）**：summary のみ（`rematched=0, n=0, warnings=[]`）、`txn_row` 0、`Build Notification` が `[]`、`Check … Enabled` 以降が未実行
- **判定**：**PASS**

## R19-twice（R19-b）Schedule を 2 回連続実行 → 同一・書込みなし

- **区分**：PIN（シート差分ゼロは LIVE-G）／ **実行 ID**：**149** と **150**（同じ pin を続けて実行。どちらも success、最終ノード `Build Notification`）
- **観測**：実行ノード集合が同一（上記 10 ノード）、全ノードの出力 JSON を機械比較して差分 0 ノード。150 も `Build Notification` `[[]]`、書込みノード未実行、シンク受信なし
- **期待（CASES R19-b / CLAUDE.md §6 P3 ゲート / DESIGN §8.4）**：2 回連続で結果同一、2 回目もシート差分ゼロ・通知なし
- **判定**：**PASS**（pinned; sheet diff = 0 pending H1）

## R21 Error Workflow が起動する

- **区分**：PIN 相当（pinned の Error Trigger 2 形状）＋ 本番実行の Error Trigger（Credential 不要）。通知の実到達は LIVE-N（Slack / Gmail は H2）。LINE / Chatwork はローカルシンクで確認
- **前提の確認**：本体複製 `m3C9NLhdSCUbSQEe` の `settings.errorWorkflow` = `H8dkT8fJ4oOAJcqG`（`POST /api/v1/workflows` の応答と `GET` で確認）。手動実行（`POST /rest/workflows/{id}/run`）では Error Trigger が発火しないため、本体複製の失敗（例：notify-all-fail 相当）では Error Workflow を検証できない（公式ドキュメントどおり。CASES R21 前提）。よって (a) Error Trigger を pin した手動実行と (b) 使い捨てワークフローの本番実行（Webhook）で確認した

### R21-a Error Trigger pinned：execution error 形状 — 実行 **161**

- **pin**：`tests/pins/error-handler.pin.json`（`Catch Workflow Error` = n8n ドキュメントの例 `{execution: {id: 231, url: https://n8n.example.com/execution/231, retryOf: 34, error: {message: Example Error Message, stack}, lastNodeExecuted: Node With Error, mode: manual}, workflow: {id: 1, name: Example Workflow}}`、`Config` pinned）。ワークフロー `H8dkT8fJ4oOAJcqG`、`triggerToStartFrom = Catch Workflow Error`
- **観測**：success。`Build Error Message` の title `【n8n エラー】Example Workflow`、body_text `ワークフロー：Example Workflow\n失敗したノード：Node With Error\nエラー：Example Error Message\n実行ログ：https://n8n.example.com/execution/231\n\n実行ログで原因を確認し、修正後に再実行してください。シート書込みやメール送信が途中まで進んでいる可能性があるため、再実行前に台帳シートを確認してください。`。`slack_blocks[0]`（header）= title、`line_text == chatwork_text == body_text`。`Check Slack/Email Enabled [0,1]`、`Check LINE/Chatwork Enabled [1,0]` → `Notify LINE` / `Notify Chatwork` 実行。p0-sink 162 の `messages[0].text` と Chatwork sink 163 の `body` が body_text と一致

### R21-b Error Trigger pinned：trigger error 形状 — 実行 **164**

- **pin**：`tests/pins/R21-trigger-error.pin.json`（新規。`{trigger: {error: {name: WorkflowActivationError, message: "Poll failed: invalid_grant", cause: {…}, timestamp, node: {name: Watch Drive Folder, type: n8n-nodes-base.googleDriveTrigger, …}}, mode: trigger}, workflow: {id: 1, name: Example Trigger Workflow}}`。`execution` キー無し）
- **観測**：success。title `【n8n エラー】Example Trigger Workflow`、body_text `ワークフロー：Example Trigger Workflow\n失敗したノード：Watch Drive Folder\nエラー：Poll failed: invalid_grant\n実行ログ：(not saved)\n\n…`（`last_node` は `trigger.error.node.name`、`message` は `trigger.error.message`、`execution_url` は `(not saved)` にフォールバック：DESIGN §6.9）。p0-sink 165 / Chatwork sink 166 が同文を受信

### R21-c 本番実行（使い捨てワークフローの失敗 → Error Workflow 起動）— 実行 **172**（失敗側）／**173**（Error Workflow）

- **手順**：使い捨て `zrFdEKFsbuBJAnmK` を有効化し `POST http://localhost:5678/webhook/p3-g3-schedule-error/throw` → `Throw P3 Error`（Code）が `throw new Error('P3 error-handler check')`
- **観測（172）**：`mode: webhook`、status `error`、`lastNodeExecuted Throw P3 Error`、error `P3 error-handler check [line 1]`
- **観測（173）**：Error Workflow 複製 `H8dkT8fJ4oOAJcqG` の実行、**`mode: error`**、success、開始 `2026-09-23T08:29:56.644Z`（172 の停止 `08:29:56.587Z` の 57 ms 後）。`Catch Workflow Error` の出力 = `{execution: {id: "172", url: "http://localhost:5678/workflow/zrFdEKFsbuBJAnmK/executions/172", error: {name: WrappedExecutionError, message: "P3 error-handler check [line 1]", stack, lineNumber: 1, …}, lastNodeExecuted: "Throw P3 Error", mode: "webhook", executionContext: {…}}, workflow: {id: zrFdEKFsbuBJAnmK, name: "[P3-g3-schedule-error] Throw for error-handler"}}`（実出力は docs 例より `error` のキーが多い：`level / shouldReport / description / tags / name / lineNumber`、および `execution.executionContext`。`Build Error Message` が使う `workflow.name / execution.error.message / lastNodeExecuted / execution.url` はすべて存在）
  - `Build Error Message`：title `【n8n エラー】[P3-g3-schedule-error] Throw for error-handler`、body_text `ワークフロー：[P3-g3-schedule-error] Throw for error-handler\n失敗したノード：Throw P3 Error\nエラー：P3 error-handler check [line 1]\n実行ログ：http://localhost:5678/workflow/zrFdEKFsbuBJAnmK/executions/172\n\n実行ログで原因を確認し、…`
  - `Notify LINE [1]` → p0-sink **174**（`to: Ug3scheduleerror`、`messages[0].text` = body_text）、`Notify Chatwork [1]` → Chatwork sink **175**（`params.roomId = g3`、`body` = body_text）
- **先行試行の記録（所見の根拠）**：
  - 実行 **167**・**168**（使い捨ての失敗）では Error Workflow の実行が生まれず、n8n ログに `Calling Error Workflow for "zrFdEKFsbuBJAnmK". Workflow "H8dkT8fJ4oOAJcqG" is not active and cannot be executed`。→ **所見 1**：n8n 2.40.5 は Error Workflow 自身が有効化（published）されていないと呼び出さない（`n8n/dist/workflows/workflow-execution.service.js` `loadErrorWorkflowData`：published data が無ければ `logger.error` して `null`）
  - Error Workflow 複製の有効化は `POST /api/v1/workflows/{id}/activate` が `Cannot publish workflow: 2 nodes have configuration issues: Node "Notify Slack": Missing required credential: slackApi / Node "Notify Email": Missing required credential: gmailOAuth2` で拒否。→ **所見 2**：有効化時の検証（`workflow-validation.service.js` `validateNodeConfiguration`）は接続済みの有効ノード全部の Credential を要求し、`disabled` なノードだけ除外する。複製の `Notify Slack` / `Notify Email` を `disabled: true` にすると有効化でき、実行 **169**（失敗側）→ **170**（Error Workflow、`mode: error`）が生まれた。170 は `Notify Chatwork` が 404（複製 `Config` の Chatwork URL が `/webhook/<webhookId>/<path>` 形式でなかった自分の設定ミス）で status `error` になったが `Build Error Message` の出力と p0-sink **171** の受信は 173 と同じ。URL を直して再実行したのが 172 / 173
- **期待（CASES R21）**：`error-handler` の実行が生まれ、`Build Error Message` の `title` が `【n8n エラー】<失敗したワークフロー名>`、`body_text` に `失敗したノード：<Code ノード名>`・`エラー：P3 error-handler check` を含む。（CASES は `[P3] Throw for error-handler` という名前と Schedule 毎分を想定。名前は自分のラベル付き、起動は Webhook の本番実行に置き換えた。`エラー：` の値は Code ノードが付ける ` [line 1]` 付き）
- **判定**：**PASS**（pinned 2 形状 ＋ 本番実行で Error Workflow 起動・文面・LINE / Chatwork 到達を確認。Slack / Gmail の到達は LIVE-N H2）。**ただし所見 1・2 は SETUP に必須の記述**（下記「オーケストレーターへ」）

## R22 `TRIGGERS_ENABLED` で OFF にした系統は `Skip Disabled Trigger` で終わる

- **区分**：PIN（OFF でもトリガーのポーリングが続く点は LIVE-G）
- **観測**：

| ケース | 実行 ID | pin | Config | `Route by Source` 出力（drive, gmail, schedule, fallback） | 実行ノード | status ／ 通知 |
|---|---|---|---|---|---|---|
| R22 drive=false | **155** | `tests/pins/R22-drive-disabled.pin.json`（`drive.pin.json` ＋ `TRIGGERS_ENABLED {drive:false, gmail:true, schedule:true}`）、`Watch Drive Folder` から | `SOURCE Watch Drive Folder` | `[0,0,0,1]` | `Watch Drive Folder [1], Config [1], Route by Source, Skip Disabled Trigger [1]` のみ。`Check File Is CSV` / `Download File` / `Parse Bank CSV` 以降なし | success ／ なし |
| R22 gmail=false | **157** | `tests/pins/gmail-disabled.pin.json`（既存）、`Watch Gmail Inbox` から | `SOURCE Watch Gmail Inbox`、`gmail:false` | `[0,0,0,2]` | `Watch Gmail Inbox [2], Config [2], Route by Source, Skip Disabled Trigger [2]` のみ。`Parse Mail` / `Collect Transactions` / `Read Invoices` 以降なし | success ／ なし |
| R22 schedule=false | **154** | `tests/pins/R22-schedule-disabled.pin.json`（`schedule.pin.json` ＋ `schedule:false`）、`Run Daily Rematch` から | `SOURCE Run Daily Rematch`、`schedule:false` | `[0,0,0,1]` | `Run Daily Rematch [1], Config [1], Route by Source, Skip Disabled Trigger [1]` のみ | success ／ なし |
| R22-c SOURCE 未知 | **156** | `tests/pins/unknown-source.pin.json`（既存、`SOURCE = "Manual"`、`TRIGGERS_ENABLED` すべて true）、`Watch Drive Folder` から | `SOURCE Manual` | `[0,0,0,1]` | `Watch Drive Folder [1], Config [1], Route by Source, Skip Disabled Trigger [1]` のみ | success ／ なし |
| R22-b gmail=true に戻す | **158** | `tests/pins/gmail.pin.json`（既存、`TRIGGERS_ENABLED` 以外は 157 と同一） | `gmail:true` | `[0,2,0,0]` | R10 と同じ全経路：`Parse Mail [2] → … → Match Invoices [5] → Route Match Results [2,2,1]`、`invoice_update` INV-2026-018 paid/auto/104500・INV-2026-019 paid/auto/19800、`txn_row` 2 件 matched、title `処理 2件｜自動消込 2｜要確認 0｜未消込 0` | success ／ p0-sink 159・Chatwork sink 160 |

  - 4 つの OFF ケースで両シンクとも新規受信なし。`Update Invoices` / `Upsert Transactions` / `Build Notification` は runData に無い（書込みなし・通知なし）
- **期待（CASES R22）**：`Route by Source` の該当出力にアイテムが流れず Fallback → `Skip Disabled Trigger`；`Parse Mail` 等以降が未実行；成功終了、通知なし、書込みなし；R22-b は R10 と同じ；R22-c も `Skip Disabled Trigger`
- **判定**：**PASS**（トリガー自身のポーリング継続の確認は LIVE-G H1）

## R12 入金と出金が同一行 → N/A

- **区分**：—（実行なし）
- **理由（CASES R12 / T11）**：銀行の入出金明細は 1 行に入金と出金が同時に入らない（どちらか一方の列だけが埋まる）ため fixture に該当行が無く、ケースとして実行できない。`code/parse_bank_csv.js`（`workflow.json` の `Parse Bank CSV`）は `deposit_col` だけで判定し（`deposit > 0` なら取引、それ以外は `ignored_withdraw`）、`withdraw_col` は参照しない。仮に両列が埋まった行が来ても入金として扱われる。集計行・小計行が `入金額` を持つ CSV は `skip_rows` か事前除去で対応する旨を SETUP（P4）に書く
- **判定**：**N/A**（記録のみ）

## DESIGN §8.4 実行順：`Update Invoices` → `Upsert Transactions` → `Build Notification`

- 書込みが発生した 3 実行の `runData` の順序と各ノードの `startTime`（ms）：

| 実行 | 経路 | `Update Invoices` | `Upsert Transactions` | `Build Notification` | 単調増加 |
|---|---|---|---|---|---|
| 146 | Drive（bank_A） | index 12, `1790151955435` | index 13, `1790151955444` | index 14, `1790151955454` | はい |
| 151 | Schedule（R18） | index 9, `1790152031122` | index 10, `1790152031131` | index 11, `1790152031143` | はい |
| 158 | Gmail（R22-b） | index 10, `1790152043727` | index 11, `1790152043735` | index 12, `1790152043744` | はい |

- `Route Match Results` の出力 0 → `Update Invoices`、出力 1 → `Upsert Transactions`、出力 2 → `Build Notification` の順で実行され、通知は 2 つの書込みノードの後（`executionOrder: v1`、DESIGN D17「シート書込み後に通知」）。pinned のため書込みノードの `executionTime` は 0 ms だが、実行順自体はエンジンが決めるので本番でも同じ
- **判定**：**PASS**

---

## オーケストレーターへ / For the orchestrator

1. **Error Workflow は有効化が必要（n8n 2.40.5）**：`settings.errorWorkflow` を設定しただけでは呼ばれず、`error-handler` 自身を Active にする必要がある（実行 167 / 168 のログ、`workflow-execution.service.js` `loadErrorWorkflowData`）。DESIGN §2.2 と SETUP（P4）に「Error Workflow を有効化する」を追記すべき。`error-handler.json` の変更は不要
2. **有効化時の Credential 検証**：接続済みの有効ノードは到達しない経路でも Credential が必須（`Notify Slack: slackApi`、`Notify Email: gmailOAuth2`）。`NOTIFY_CHANNELS` で使わないチャネルの Notify ノードは、買い手が Credential を割り当てるか **ノードを無効化（disabled）** しないと `error-handler` も本体も有効化できない。SETUP に手順を追記すべき（本体も `Notify Slack` / `Notify Email` / Google ノードで同じ検証を受ける）。設計変更の要否（例：既定で Slack / Email ノードを disabled にする、または Config の `NOTIFY_CHANNELS` 既定を空にする）はオーケストレーターの判断
3. **Error Trigger の実出力**：`execution.error` に docs 例より多いキー（`level / shouldReport / description / tags / name / lineNumber`）と `execution.executionContext` がある。`Build Error Message` が参照するキーはすべて存在し、DESIGN §3 / §6.9 の変更は不要（記録のみ）
4. **CASES R21 の手順差**：Schedule 毎分ではなく Webhook の本番実行で失敗させた（待ち時間と繰り返し発火を避けるため）。結果は同等（`mode: error` の Error Workflow 実行）。CASES を書き換えるなら「本番実行（Webhook でも可）」とする
5. **動的パス Webhook の URL**：`rooms/:roomId/messages` 形式のシンクは `/webhook/<webhookId>/<path>`（README の注記どおり）。`make_pins.py` 既定の `http://localhost:5678/webhook/p2-chatwork` は SMOKE 時の `webhookId = p2-chatwork` と path `rooms/:roomId/messages` の組合せに対応しており、別 path を使う場合はベース URL に `<webhookId>/<path 先頭>` を含める（実行 144 の 404 で確認）
