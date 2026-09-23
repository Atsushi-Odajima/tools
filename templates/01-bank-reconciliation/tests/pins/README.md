# tests/pins — smoke-test pinned data / スモークテスト用 pinned data

JA: `workflow.json` / `error-handler.json` をローカル n8n に登録し、Google／Slack／Gmail の Credential 無しで末端まで実行するための pinned data。`make_pins.py` が `build/build_workflow.py` の Config 既定値と `fixtures/` から生成する（手で編集しない）。結果は `tests/SMOKE.md`。
EN: Pinned data that lets the registered `workflow.json` / `error-handler.json` run end-to-end in a local n8n without Google / Slack / Gmail credentials. `make_pins.py` generates every file from the Config defaults in `build/build_workflow.py` and `fixtures/` (do not edit by hand). Results: `tests/SMOKE.md`.

## 共通の差し替え / Common overrides (every `Config` pin)

| Key | Value | Why |
|---|---|---|
| `NOTIFY_CHANNELS` | `["line","chatwork"]` | 両チャネルとも HTTP Request なので Credential 無しの n8n でも「実際に HTTP を送る」経路を通せる（ヘッダ用に空の Header Auth Credential を割り当てる） / both are HTTP Request nodes, so the real HTTP path runs (assign any Header Auth credential for the header) |
| `LINE_API_URL` | `http://localhost:5678/webhook/p0-sink` | ローカルの受信 Webhook（P0 のシンク）/ local webhook sink |
| `CHATWORK_API_BASE_URL` | `http://localhost:5678/webhook/p2-chatwork` | パス `rooms/:roomId/messages` を持つ受信 Webhook（`webhookId = p2-chatwork`）。ノードは `<base>/rooms/<CHATWORK_ROOM_ID>/messages` に POST する / a webhook whose path is `rooms/:roomId/messages` |
| `LINE_TO_USER_ID` / `CHATWORK_ROOM_ID` / `SHEET_ID` | `Utest` / `1` / `TEST_SHEET` | ダミー / dummies |
| 到達不能 URL / unreachable URL | `http://127.0.0.1:9` | 失敗させたいチャネルに使う / used for channels that must fail |

`Config` 自体を pin するので、その実行では `Config`（Set）ノードは動かない。Set ノードの実動作は `*-realconfig` で確認する（`Config` を pin せず、`Notify Slack` を pin して既定の `NOTIFY_CHANNELS = ["slack"]` を吸収する）。
Because `Config` is pinned, the Set node does not run in those executions; the real Set node is exercised by the `*-realconfig` pins (Config not pinned, `Notify Slack` pinned to absorb the default `NOTIFY_CHANNELS = ["slack"]`).

## ファイル一覧 / Files

| File | Trigger to start from | Pinned nodes | Purpose (CASES) |
|---|---|---|---|
| `drive.pin.json` | `Watch Drive Folder` | trigger `{id:"file_test_001", name:"bank_A_sjis.csv", mimeType:"text/csv"}`, `Download File` (binary = base64 of `fixtures/bank_A_sjis.csv`), `Config`, `Read Invoices` = `invoices.seed.csv`, `Read Transactions` = `[{}]` (empty sheet), `Update Invoices` / `Upsert Transactions` = `[{ok:true}]` | R01–R08, R14-a; sink receives one LINE and one Chatwork body |
| `drive-realconfig.pin.json` | `Watch Drive Folder` | as above without `Config`; `Notify Slack` = `[{ok:true}]` | Set JSON-output mode: `SOURCE = $prevNode.name`, trigger fields pass through, regexes intact (DESIGN §8.3-5) |
| `drive-second-run.pin.json` | `Watch Drive Folder` | as `drive` but `Read Transactions` = `transactions.seed.csv` + the 11 `txn_row` items of the first run (written by `make_pins.py --txn-rows <json>`) | R09: all 11 skipped, no writes, `no_transactions` notice |
| `gmail.pin.json` | `Watch Gmail Inbox` | trigger = `fixtures/mail_pinned.example.json` items (Simplify OFF shape), `Config` (2 items, one per mail), Google nodes as above | R10 |
| `gmail-realconfig.pin.json` | `Watch Gmail Inbox` | as above without `Config`; `Notify Slack` = `[{ok:true}]` | Set node with 2 input items |
| `gmail-disabled.pin.json` | `Watch Gmail Inbox` | as `gmail` with `TRIGGERS_ENABLED.gmail = false` | R22: `Route by Source` fallback → `Skip Disabled Trigger` |
| `unknown-source.pin.json` | `Watch Drive Folder` | as `drive` with `SOURCE = "Manual"` | R22-c: unknown source → `Skip Disabled Trigger` |
| `drive-two-files.pin.json` | `Watch Drive Folder` | trigger 2 items (`bank_A_sjis.csv`, `bank_A_second.csv`), `Config` 2 items, `Download File` 2 items (A + a derived second CSV: one 1,000 JPY deposit + one withdrawal) | D31: both files parsed (`Parse Bank CSV` 14 items, `file_stats` ×2), `ignored_withdraw` 4+1, `file_name` joined, summary n=12 |
| `drive-sheet-export.pin.json` | `Watch Drive Folder` | trigger `{name:"bank_A_sjis", mimeType:"application/vnd.google-apps.spreadsheet"}`, `Download File` = that json + binary = bank_A re-encoded as UTF-8 without BOM | D22: `Check File Is CSV` passes on the mimeType, the export is decoded as UTF-8 although `CSV_MAPPING.encoding` is `shift_jis` → same 11 txns as `drive` |
| `schedule.pin.json` | `Run Daily Rematch` | trigger `{timestamp}`, `Config`, `Read Transactions` = `transactions.seed.csv` (1 matched row) | R19: nothing to re-match → `Build Notification` returns `[]` |
| `schedule-rematch.pin.json` | `Run Daily Rematch` | `Read Transactions` = seed + the 11 first-run rows, `Read Invoices` = seed + `INV-2026-021` | R18: `2026-09-11\|66000\|ミホンシヨウカイ\|` becomes `matched`, `rematched = 1` |
| `drive-nonecsv.pin.json` | `Watch Drive Folder` | trigger `{name:"memo.pdf", mimeType:"application/pdf"}` | R16: IF false → `Skip Non-CSV File` |
| `notify-partial-fail.pin.json` | `Watch Drive Folder` | as `drive`, `CHATWORK_API_BASE_URL = http://127.0.0.1:9` | R11-b: one channel fails, run succeeds, `channels_failed = 1` |
| `notify-all-fail.pin.json` | `Watch Drive Folder` | as `drive`, both URLs unreachable | R11-b: `Check Notification Results` throws, execution ends in error |
| `error-handler.pin.json` | `Catch Workflow Error` (error-handler.json) | trigger = the example item of the n8n Error Trigger docs, own `Config` | R21 (message assembly + delivery to the sinks) |

## 実行手順 / How to run

1. Register both workflows (`POST /api/v1/workflows` with `name` / `nodes` / `connections` / `settings` of the JSON files). Set the main workflow's `settings.errorWorkflow` to the error handler's id.
2. Create the two local webhook sinks (`p0-sink`: Webhook v2, POST, path `p0-sink`; `p2-chatwork`: Webhook v2, POST, path `rooms/:roomId/messages`, `webhookId` `p2-chatwork`) and activate them. Create two Header Auth credentials named `LINE Messaging API` / `Chatwork API` with any dummy value and select them in `Notify LINE` / `Notify Chatwork` (HTTP Request refuses to run without a credential when Header Auth is selected).
3. `PYTHONDONTWRITEBYTECODE=1 python3 tests/pins/make_pins.py` (no `__pycache__/` under `build/`; add `--txn-rows <file>` with the `txn_row` items of a first Drive run to produce `drive-second-run` / `schedule-rematch`).
4. For each pin: `PATCH /rest/workflows/{id}` `{ "pinData": {}, "versionId": … }` (reset), then `{ "pinData": <file>, "versionId": … }`, then `POST /rest/workflows/{id}/run` with `triggerToStartFrom: { name: "<Trigger to start from>" }` (ASSUMPTIONS A11: pinned data must be stored on the workflow; binary is accepted there).
5. Read `GET /api/v1/executions/{id}?includeData=true` and compare the per-node item counts with `tests/SMOKE.md`. Reset `pinData` to `{}` before every run (the harness merges the pin over whatever is stored, so a `Config` pin would leak into a `*-realconfig` run). The run body must be sent from a file (`curl -d @file`): with the pinned binaries it exceeds the command-line length.
6. Afterwards reset `pinData` to `{}` and remove the credential references again so the stored workflow equals `workflow.json`; delete the dummy credentials and the extra sink.

Pins are development aids; they are not part of the buyer's setup and contain no real IDs or tokens.
