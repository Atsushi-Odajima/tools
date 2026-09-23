# tests/SMOKE.md — P2 smoke runs of the registered workflows (local n8n 2.40.5, 2026-09-23, after the P2 review fixes)

JA: `build/build_workflow.py` が生成した `workflow.json` / `error-handler.json` をローカル n8n に登録し、`tests/pins/*.pin.json` で実行した結果（P2 レビュー反映後の再実行。DESIGN D31〜D33、`ASSUMPTIONS.md` A29〜A34）。Google／Slack／Gmail ノードは pinned（ライブ未検証）。実行 ID はローカル n8n のもの。
EN: Results of running the generated `workflow.json` / `error-handler.json` registered in the local n8n with `tests/pins/*.pin.json`, re-run after the P2 review fixes (DESIGN D31–D33, `ASSUMPTIONS.md` A29–A34). Google / Slack / Gmail nodes are pinned (not verified live). Execution ids refer to the local n8n.

| Item | Value |
|---|---|
| main workflow id | `EMlrzFHwUpu7xvZx` (`[Odaji] 01 Bank Deposit Reconciliation v1.0.0`), updated with `PUT /api/v1/workflows/{id}` (name / nodes / connections / settings, `settings.errorWorkflow` = error workflow id) |
| error workflow id | `S9vwW2D7jBCIvCQn` (`[Odaji] 01 Error Handler v1.0.0`), same PUT |
| sinks | `p0-sink` (`VDtPVF2gV4fnId1X`, LINE target) and `p2-chatwork` (`YF7YdSa8P6bqGgtp`, Webhook v2 path `rooms/:roomId/messages`, Chatwork target; created for these runs and deleted afterwards) |
| credentials | two dummy Header Auth credentials `LINE Messaging API` / `Chatwork API` created only in the local n8n and referenced by `Notify LINE` / `Notify Chatwork` during the runs (A28); removed afterwards, the stored workflows were PUT again from the repo files |
| validation | `validate_workflow` (profile runtime): `workflow.json` valid, 0 errors, 4 warnings ("Dynamic require() not supported" ×2 — the word only appears in comments of `parse_bank_csv.js` / `parse_mail.js`; "executeOnce is enabled" ×2 — by design, DESIGN §2.5); `error-handler.json` valid, 0 errors, 0 warnings. `validate_node` (full / runtime) on `Notify Slack` with `otherOptions.includeLinkToWorkflow = false`: valid, 0 errors, 0 warnings |
| secret grep | CLAUDE.md §1-2 pattern → 0 matches in `workflow.json` and `error-handler.json` (also asserted by the build script); repo-wide (text + binary, excluding `.git`) the only hits are the rule text in `CLAUDE.md` / `CLAUDE.en.md`; no `__pycache__` / `*.pyc` left (now ignored by `.gitignore`, A34) |
| unit suites | `tests/unit/run-all.sh` on `code/*.js` → 10/10 suites PASS (incl. the new scenarios `parse_bank_csv/two_files_A_and_edge_in_one_run`, `parse_bank_csv/sheets_export_utf8_nobom_default_shift_jis`, `parse_bank_csv/plain_utf8_nobom_default_shift_jis_fails`, `collect_transactions/drive_two_files`, `match_invoices/bank_A_rerun_after_invoice_write_only`); `tests/unit/run-all.sh workflow.json` (embedded jsCode) → 10/10 PASS |
| build | `python3 build/build_workflow.py` then `--check`: both files unchanged / deterministic (workflow.json 108,236 bytes, 36 nodes; error-handler.json 19,004 bytes, 14 nodes) |
| result | **all 15 smoke runs behave as expected** (table below); `pinData` reset to `{}` before and after every run |

## Runs

### drive — execution 57, status `success`, last node `Check Notification Results`

- pin: `tests/pins/drive.pin.json` (workflow `EMlrzFHwUpu7xvZx`)
- expected / observed: success; summary n=11 a=4 b=3 c=4 ignored_withdraw=4 skipped 0/0 warnings=[]; invoice_updates INV-001 paid/auto 33000, INV-002 paid/fee_deducted 54780, INV-003 paid/auto 9800, INV-004 paid/amount_only 128000, INV-005 + INV-006 paid/combined, INV-007 partial/auto 100000, INV-012 paid/auto 27500; Route Match Results 8/11/1; title `【入金消込 2026-09-23】処理 11件｜自動消込 4｜要確認 3｜未消込 4`; Check Notification Results {attempted 2, ok 2, failed 0}; sink p0-sink received the LINE JSON (`to:"Utest"`, sink execution 58), sink p2-chatwork received the `body=` form data (sink execution 59, `params.roomId = "1"`)
- items per node (per output; nodes not listed did not execute): `Watch Drive Folder` [1], `Config` [1], `Route by Source` [1, 0, 0, 0], `Check File Is CSV` [1, 0], `Download File` [1], `Parse Bank CSV` [12], `Collect Transactions` [1], `Read Invoices` [20], `Read Transactions` [1], `Normalize Payer` [1], `Match Invoices` [20], `Route Match Results` [8, 11, 1], `Update Invoices` [1], `Upsert Transactions` [1], `Build Notification` [1], `Check Slack Enabled` [0, 1], `Check Email Enabled` [0, 1], `Check LINE Enabled` [1, 0], `Notify LINE` [1, 0], `Check Chatwork Enabled` [1, 0], `Notify Chatwork` [1, 0], `Merge Notification Results` [2], `Check Notification Results` [1]

### drive-realconfig — execution 60, status `success`, last node `Check Notification Results`

- pin: `tests/pins/drive-realconfig.pin.json` (workflow `EMlrzFHwUpu7xvZx`)
- expected / observed: success; real `Config` (Set v3.5 JSON output) emitted `SOURCE = "Watch Drive Folder"`, trigger fields `id`/`name`/`mimeType` passed through, regexes intact (`Amount\s+(?:JPY|¥)?\s*([0-9,]+)`); same reconciliation as `drive`; `Notify Slack` pinned (default `NOTIFY_CHANNELS = ["slack"]`), Merge ran with only input 1 populated, Check Notification Results {attempted 1, ok 1, failed 0}
- items per node (per output; nodes not listed did not execute): `Watch Drive Folder` [1], `Config` [1], `Route by Source` [1, 0, 0, 0], `Check File Is CSV` [1, 0], `Download File` [1], `Parse Bank CSV` [12], `Collect Transactions` [1], `Read Invoices` [20], `Read Transactions` [1], `Normalize Payer` [1], `Match Invoices` [20], `Route Match Results` [8, 11, 1], `Update Invoices` [1], `Upsert Transactions` [1], `Build Notification` [1], `Check Slack Enabled` [1, 0], `Notify Slack` [1], `Check Email Enabled` [0, 1], `Check LINE Enabled` [0, 1], `Check Chatwork Enabled` [0, 1], `Merge Notification Results` [1], `Check Notification Results` [1]

### drive-second-run — execution 61, status `success`, last node `Check Notification Results`

- pin: `tests/pins/drive-second-run.pin.json` (workflow `EMlrzFHwUpu7xvZx`)
- expected / observed: success; summary n=0 a=0 b=0 c=0 skipped_existing=11; Route Match Results 0/0/1 → Update / Upsert not executed; title `【入金消込 2026-09-23】新規の入金はありませんでした` + `（処理済みのため skip：11 件）` (R09); both sinks received it (sink executions 62 / 63)
- items per node (per output; nodes not listed did not execute): `Watch Drive Folder` [1], `Config` [1], `Route by Source` [1, 0, 0, 0], `Check File Is CSV` [1, 0], `Download File` [1], `Parse Bank CSV` [12], `Collect Transactions` [1], `Read Invoices` [20], `Read Transactions` [12], `Normalize Payer` [1], `Match Invoices` [1], `Route Match Results` [0, 0, 1], `Build Notification` [1], `Check Slack Enabled` [0, 1], `Check Email Enabled` [0, 1], `Check LINE Enabled` [1, 0], `Notify LINE` [1, 0], `Check Chatwork Enabled` [1, 0], `Notify Chatwork` [1, 0], `Merge Notification Results` [2], `Check Notification Results` [1]

### drive-two-files — execution 64, status `success`, last node `Check Notification Results`

- pin: `tests/pins/drive-two-files.pin.json` (workflow `EMlrzFHwUpu7xvZx`)
- expected / observed: success (D31 / ASSUMPTIONS A29); trigger, Config, Check File Is CSV and Download File all carried 2 items; `Parse Bank CSV` emitted 14 items = 11 A txns + `file_stats` (bank_A_sjis.csv, ignored 4, rows 15) + 1 txn + `file_stats` (bank_A_second.csv, ignored 1, rows 2), `_file` set = both names, `pairedItem.item` ∈ {0, 1}; `Collect Transactions` ignored_withdraw=5, file_name `bank_A_sjis.csv, bank_A_second.csv`, 12 txns; summary n=12 a=4 b=3 c=5 (the 1,000 JPY `振込 ﾆﾏｲﾒ ﾃｽﾄ` is unmatched with no candidate); Route Match Results 8/12/1; title `処理 12件｜自動消込 4｜要確認 3｜未消込 5`; sinks 65 / 66
- items per node (per output; nodes not listed did not execute): `Watch Drive Folder` [2], `Config` [2], `Route by Source` [2, 0, 0, 0], `Check File Is CSV` [2, 0], `Download File` [2], `Parse Bank CSV` [14], `Collect Transactions` [1], `Read Invoices` [20], `Read Transactions` [1], `Normalize Payer` [1], `Match Invoices` [21], `Route Match Results` [8, 12, 1], `Update Invoices` [1], `Upsert Transactions` [1], `Build Notification` [1], `Check Slack Enabled` [0, 1], `Check Email Enabled` [0, 1], `Check LINE Enabled` [1, 0], `Notify LINE` [1, 0], `Check Chatwork Enabled` [1, 0], `Notify Chatwork` [1, 0], `Merge Notification Results` [2], `Check Notification Results` [1]

### drive-sheet-export — execution 67, status `success`, last node `Check Notification Results`

- pin: `tests/pins/drive-sheet-export.pin.json` (workflow `EMlrzFHwUpu7xvZx`)
- expected / observed: success (D22 / A30); trigger `mimeType = application/vnd.google-apps.spreadsheet`, name `bank_A_sjis` (no extension) → `Check File Is CSV` true on the third condition; `Download File` pinned with the trigger json + bank_A re-encoded as UTF-8 without BOM; with the DEFAULT `CSV_MAPPING.encoding = shift_jis` the node decoded it as UTF-8: 12 items, first remitter `振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ`, `_file` / `file_name` = `bank_A_sjis`; same summary as `drive` (n=11 a=4 b=3 c=4); sinks 68 / 69
- items per node (per output; nodes not listed did not execute): `Watch Drive Folder` [1], `Config` [1], `Route by Source` [1, 0, 0, 0], `Check File Is CSV` [1, 0], `Download File` [1], `Parse Bank CSV` [12], `Collect Transactions` [1], `Read Invoices` [20], `Read Transactions` [1], `Normalize Payer` [1], `Match Invoices` [20], `Route Match Results` [8, 11, 1], `Update Invoices` [1], `Upsert Transactions` [1], `Build Notification` [1], `Check Slack Enabled` [0, 1], `Check Email Enabled` [0, 1], `Check LINE Enabled` [1, 0], `Notify LINE` [1, 0], `Check Chatwork Enabled` [1, 0], `Notify Chatwork` [1, 0], `Merge Notification Results` [2], `Check Notification Results` [1]

### gmail — execution 70, status `success`, last node `Check Notification Results`

- pin: `tests/pins/gmail.pin.json` (workflow `EMlrzFHwUpu7xvZx`)
- expected / observed: success; Parse Mail 2 txns; INV-2026-018 paid/auto/104500 and INV-2026-019 paid/auto/19800; title `処理 2件｜自動消込 2｜要確認 0｜未消込 0`; both sinks received the body (71 / 72)
- items per node (per output; nodes not listed did not execute): `Watch Gmail Inbox` [2], `Config` [2], `Route by Source` [0, 2, 0, 0], `Parse Mail` [2], `Collect Transactions` [1], `Read Invoices` [20], `Read Transactions` [1], `Normalize Payer` [1], `Match Invoices` [5], `Route Match Results` [2, 2, 1], `Update Invoices` [1], `Upsert Transactions` [1], `Build Notification` [1], `Check Slack Enabled` [0, 1], `Check Email Enabled` [0, 1], `Check LINE Enabled` [1, 0], `Notify LINE` [1, 0], `Check Chatwork Enabled` [1, 0], `Notify Chatwork` [1, 0], `Merge Notification Results` [2], `Check Notification Results` [1]

### gmail-realconfig — execution 73, status `success`, last node `Check Notification Results`

- pin: `tests/pins/gmail-realconfig.pin.json` (workflow `EMlrzFHwUpu7xvZx`)
- expected / observed: success; real `Config` produced 2 items (one per mail) with `SOURCE = "Watch Gmail Inbox"`; same reconciliation as `gmail`; `Notify Slack` pinned, Check Notification Results {attempted 1, ok 1}
- items per node (per output; nodes not listed did not execute): `Watch Gmail Inbox` [2], `Config` [2], `Route by Source` [0, 2, 0, 0], `Parse Mail` [2], `Collect Transactions` [1], `Read Invoices` [20], `Read Transactions` [1], `Normalize Payer` [1], `Match Invoices` [5], `Route Match Results` [2, 2, 1], `Update Invoices` [1], `Upsert Transactions` [1], `Build Notification` [1], `Check Slack Enabled` [1, 0], `Notify Slack` [1], `Check Email Enabled` [0, 1], `Check LINE Enabled` [0, 1], `Check Chatwork Enabled` [0, 1], `Merge Notification Results` [1], `Check Notification Results` [1]

### gmail-disabled — execution 74, status `success`, last node `Skip Disabled Trigger`

- pin: `tests/pins/gmail-disabled.pin.json` (workflow `EMlrzFHwUpu7xvZx`)
- expected / observed: success; `Route by Source` outputs [0,0,0,2] → fallback output 3 → `Skip Disabled Trigger` (2 items); `Parse Mail` and later nodes not executed; no notification (R22)
- items per node (per output; nodes not listed did not execute): `Watch Gmail Inbox` [2], `Config` [2], `Route by Source` [0, 0, 0, 2], `Skip Disabled Trigger` [2]

### unknown-source — execution 75, status `success`, last node `Skip Disabled Trigger`

- pin: `tests/pins/unknown-source.pin.json` (workflow `EMlrzFHwUpu7xvZx`)
- expected / observed: success; `SOURCE = "Manual"` → fallback → `Skip Disabled Trigger`; nothing else executed (R22-c)
- items per node (per output; nodes not listed did not execute): `Watch Drive Folder` [1], `Config` [1], `Route by Source` [0, 0, 0, 1], `Skip Disabled Trigger` [1]

### schedule — execution 76, status `success`, last node `Build Notification`

- pin: `tests/pins/schedule.pin.json` (workflow `EMlrzFHwUpu7xvZx`)
- expected / observed: success; summary source=schedule n=0 rematched=0 warnings=[] (the seed ledger has only a matched row) → `Build Notification` returned [] and nothing after it ran (R19)
- items per node (per output; nodes not listed did not execute): `Run Daily Rematch` [1], `Config` [1], `Route by Source` [0, 0, 1, 0], `Collect Transactions` [1], `Read Invoices` [20], `Read Transactions` [1], `Normalize Payer` [1], `Match Invoices` [1], `Route Match Results` [0, 0, 1], `Build Notification` [0]

### schedule-rematch — execution 77, status `success`, last node `Check Notification Results`

- pin: `tests/pins/schedule-rematch.pin.json` (workflow `EMlrzFHwUpu7xvZx`)
- expected / observed: success; INV-2026-021 paid/auto/66000 with matched_txn_ids `2026-09-11|66000|ミホンシヨウカイ|`; that txn row → matched; summary rematched=1 n=0; title `処理 0件｜自動消込 0｜要確認 0｜未消込 0`; notification sent to both sinks (78 / 79). As before, `Read Invoices` = seed + INV-021 without A's updates, so two other unmatched rows were written back because their candidates changed (D10); R18 with the fully updated sheet is P3 scope
- items per node (per output; nodes not listed did not execute): `Run Daily Rematch` [1], `Config` [1], `Route by Source` [0, 0, 1, 0], `Collect Transactions` [1], `Read Invoices` [21], `Read Transactions` [12], `Normalize Payer` [1], `Match Invoices` [5], `Route Match Results` [1, 3, 1], `Update Invoices` [1], `Upsert Transactions` [1], `Build Notification` [1], `Check Slack Enabled` [0, 1], `Check Email Enabled` [0, 1], `Check LINE Enabled` [1, 0], `Notify LINE` [1, 0], `Check Chatwork Enabled` [1, 0], `Notify Chatwork` [1, 0], `Merge Notification Results` [2], `Check Notification Results` [1]

### drive-nonecsv — execution 80, status `success`, last node `Skip Non-CSV File`

- pin: `tests/pins/drive-nonecsv.pin.json` (workflow `EMlrzFHwUpu7xvZx`)
- expected / observed: success; `Check File Is CSV` outputs [0,1] → `Skip Non-CSV File`; `Download File` and later nodes not executed (R16)
- items per node (per output; nodes not listed did not execute): `Watch Drive Folder` [1], `Config` [1], `Route by Source` [1, 0, 0, 0], `Check File Is CSV` [0, 1], `Skip Non-CSV File` [1]

### notify-partial-fail — execution 81, status `success`, last node `Check Notification Results`

- pin: `tests/pins/notify-partial-fail.pin.json` (workflow `EMlrzFHwUpu7xvZx`)
- expected / observed: success; `Notify Chatwork` error-output item = input json + `error: { message: "connect ECONNREFUSED 127.0.0.1:9", name, stack }` + `details` (error is an object, A21); Merge received 2 of 8 inputs; Check Notification Results {attempted 2, ok 1, failed 1, errors ["connect ECONNREFUSED 127.0.0.1:9"]}; execution succeeded (no Error Workflow); LINE sink 82
- items per node (per output; nodes not listed did not execute): `Watch Drive Folder` [1], `Config` [1], `Route by Source` [1, 0, 0, 0], `Check File Is CSV` [1, 0], `Download File` [1], `Parse Bank CSV` [12], `Collect Transactions` [1], `Read Invoices` [20], `Read Transactions` [1], `Normalize Payer` [1], `Match Invoices` [20], `Route Match Results` [8, 11, 1], `Update Invoices` [1], `Upsert Transactions` [1], `Build Notification` [1], `Check Slack Enabled` [0, 1], `Check Email Enabled` [0, 1], `Check LINE Enabled` [1, 0], `Notify LINE` [1, 0], `Check Chatwork Enabled` [1, 0], `Notify Chatwork` [0, 1], `Merge Notification Results` [2], `Check Notification Results` [1]

### notify-all-fail — execution 83, status `error`, last node `Check Notification Results`

- pin: `tests/pins/notify-all-fail.pin.json` (workflow `EMlrzFHwUpu7xvZx`)
- error: `All notification channels failed (2): connect ECONNREFUSED 127.0.0.1:9 / connect ECONNREFUSED 127.0.0.1:9 [line 38]`
- expected / observed: error at `Check Notification Results`: `All notification channels failed (2): connect ECONNREFUSED 127.0.0.1:9 / connect ECONNREFUSED 127.0.0.1:9`; both Notify nodes emitted on their error output; Merge 2 items; sheets were "written" (pinned) before the notification (D17)
- items per node (per output; nodes not listed did not execute): `Watch Drive Folder` [1], `Config` [1], `Route by Source` [1, 0, 0, 0], `Check File Is CSV` [1, 0], `Download File` [1], `Parse Bank CSV` [12], `Collect Transactions` [1], `Read Invoices` [20], `Read Transactions` [1], `Normalize Payer` [1], `Match Invoices` [20], `Route Match Results` [8, 11, 1], `Update Invoices` [1], `Upsert Transactions` [1], `Build Notification` [1], `Check Slack Enabled` [0, 1], `Check Email Enabled` [0, 1], `Check LINE Enabled` [1, 0], `Notify LINE` [0, 1], `Check Chatwork Enabled` [1, 0], `Notify Chatwork` [0, 1], `Merge Notification Results` [2], `Check Notification Results` []

### error-handler — execution 84, status `success`, last node `Notify Chatwork`

- pin: `tests/pins/error-handler.pin.json` (workflow `S9vwW2D7jBCIvCQn`)
- expected / observed: success; `Build Error Message` title `【n8n エラー】Example Workflow`, body `ワークフロー：Example Workflow / 失敗したノード：Node With Error / エラー：Example Error Message / 実行ログ：https://n8n.example.com/execution/231`; sink p0-sink received the LINE JSON (sink execution 85), sink p2-chatwork the form body (86). `Build Error Message` now sits at x=900 inside the green E3 sticky. (Execution 54 was a first attempt of this pin with the command-line harness; identical result.)
- items per node (per output; nodes not listed did not execute): `Catch Workflow Error` [1], `Config` [1], `Build Error Message` [1], `Check Slack Enabled` [0, 1], `Check Email Enabled` [0, 1], `Check LINE Enabled` [1, 0], `Notify LINE` [1], `Check Chatwork Enabled` [1, 0], `Notify Chatwork` [1]

## Findings recorded in ASSUMPTIONS.md (A29–A34)

- Drive Trigger emits every new file of one poll as separate items of one execution; `Parse Bank CSV` now parses all of them and `Collect Transactions` aggregates the per-file `file_stats` (execution 64; A29 / D31).
- `Download File` passes the trigger json through, and a Google-Sheet export is UTF-8 without BOM; items whose source mimeType is a Google Sheet are decoded as UTF-8 regardless of `CSV_MAPPING.encoding` (execution 67; A30 / D22).
- Idempotency also keys on the invoices' `matched_txn_ids` so a re-run after a failed `Upsert Transactions` cannot re-apply a deposit (unit scenario; A31 / D32).
- Slack v2.7 `otherOptions.includeLinkToWorkflow` defaults to true and appends a block with the instance URL + workflow id; both workflows now set it to false (A32 / D33). Not exercised end-to-end (Notify Slack is pinned in the `*-realconfig` runs).
- `PUT /api/v1/workflows/{id}` returns the Slack / Gmail nodes with an added `webhookId`; parameters and connections are otherwise identical to the repo files (A33).
- The stored workflows were reset afterwards (`pinData = {}`, credential references removed by a final PUT from `workflow.json` / `error-handler.json`); the dummy credentials and the `p2-chatwork` sink were deleted.
