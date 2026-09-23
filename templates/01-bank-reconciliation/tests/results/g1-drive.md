# P3 結果 — g1-drive（Drive 経路：R01〜R09, R14, R15, R16, R20）/ P3 results — g1-drive

実行日 2026-09-23、ローカル n8n 2.40.5、`tests/CASES.md`（P1 版）に対する判定。Google ノードはすべて pinned（LIVE-G 未検証、BLOCKERS H1）。実行 ID はローカル n8n のもの。
Run on 2026-09-23 against local n8n 2.40.5 following `tests/CASES.md`. Every Google node is pinned (not verified live, BLOCKERS H1). Execution ids refer to the local n8n.

## 共通 / Common

| 項目 | 値 |
|---|---|
| ワークフロー複製（本体） | `6Y99TvLuHXtWgPXs`（`[P3-g1-drive] [Odaji] 01 Bank Deposit Reconciliation v1.0.0`、`workflow.json` から `POST /api/v1/workflows` で作成。`settings.errorWorkflow` = `3acOl4yifpnXTVzw`。終了後に削除） |
| ワークフロー複製（Error Workflow） | `3acOl4yifpnXTVzw`（`[P3-g1-drive] [Odaji] 01 Error Handler v1.0.0`、`error-handler.json` から作成。終了後に削除。本セッションで起動なし：手動実行では Error Trigger は発火しない） |
| 通知シンク | LINE → 既存 `p0-sink`（`VDtPVF2gV4fnId1X`、`POST http://localhost:5678/webhook/p0-sink`）。Chatwork → 自作 `[P3-g1-drive] Chatwork sink`（`ygfRR4YUXBptN6hK`、Webhook v2、path `p3-g1-drive/rooms/:roomId/messages`、webhookId `p3-g1-drive`。動的パスは `/webhook/<webhookId>/<path>` で登録されるため `CHATWORK_API_BASE_URL = http://localhost:5678/webhook/p3-g1-drive/p3-g1-drive`。終了後に削除） |
| Credential | `LINE Messaging API`（`c8agMqYZnQv3GZ3M`）／`Chatwork API`（`1zwAokCYaGHyMSdY`）を `POST /api/v1/credentials`（httpHeaderAuth、`Authorization: Bearer <dummy>`）で作成し、複製の `Notify LINE`／`Notify Chatwork` にのみ割当。終了後に削除（A28） |
| pin の使い方 | 各実行前に複製の `pinData` を `{}` に戻し、`p2-scratch/n8n-run2.py <id> "Watch Drive Folder" --pin <run copy>` で保存→実行。run copy は下記 pin ファイルの `Config.CHATWORK_API_BASE_URL` だけを上記シンクに置換したもの（`p3-scratch/g1-drive/run-*.pin.json`。リポジトリの pin は既定の `p2-chatwork` URL のまま） |
| 実行 JSON の保存先 | `scratchpad/p3-scratch/g1-drive/exec-<id>.json`（`GET /api/v1/executions/<id>?includeData=true`、複製削除前に保存）。シンク側実行は `sink-executions.json`、対応表は `sink-mapping.json` |
| 判定スクリプト | `scratchpad/p3-scratch/g1-drive/assert.py`（103 判定すべて PASS、出力 `assert-out.txt`） |
| 新規 pin | `tests/pins/r08-bank-b.pin.json`、`r15-skip-rows-1.pin.json`、`r15-skip-rows-0-fails.pin.json`、`r14b-empty-sheets.pin.json`、`r20-notify-max-lines-2.pin.json`（`drive.pin.json` から派生した単体 JSON。`make_pins.py` は並行作業中のため未変更。生成スクリプトは `p3-scratch/g1-drive/make_case_pins.py`、README に注記） |
| 実行 89 | 最初の bank_A 実行。Chatwork シンクのパス登録ミス（自作 Webhook の動的パス URL に webhookId が前置されることを見落とし）で `Notify Chatwork` が 404 → `channels_failed 1`。突合結果は 92 と同一。シンク修正後に 92 で再実行し、92 を正とする |

## 一覧 / Summary

| Case | 区分 / Class | 実行 ID / Execution | 判定 / Verdict |
|---|---|---|---|
| R01 | PIN（実セルは LIVE-G） | 92 | **PASS**（pinned; live write pending H1） |
| R02 | PIN | 92 | **PASS** |
| R03 | PIN | 92 | **PASS** |
| R04 | PIN | 92 | **PASS** |
| R05 | PIN | 92 | **PASS** |
| R06 | PIN | 92 | **PASS** |
| R07 | PIN | 92（A）, 101（B） | **PASS** |
| R08 | PIN | 92（A）, 101（B） | **PASS** |
| R09 | PIN（差分ゼロは LIVE-G） | 92 → 95 | **PASS**（pinned; live sheet diff pending H1） |
| R14 | PIN | 92（R14-a）, 108（R14-b） | **PASS** |
| R15 | PIN | 104（skip_rows=1）, 107（skip_rows=0 → 意図どおり失敗） | **PASS** |
| R16 | PIN | 114 | **PASS** |
| R20 | PIN | 111 | **PASS** |

---

## R01 名義・金額一致 → auto, paid

- **区分**：PIN（`Update Invoices` の実セルは LIVE-G）
- **複製 ID**：`6Y99TvLuHXtWgPXs`　**実行 ID**：92（status `success`、last node `Check Notification Results`）
- **pin**：`tests/pins/drive.pin.json`（run copy `run-drive.pin.json`。trigger `{id:file_test_001, name:bank_A_sjis.csv, mimeType:text/csv}`、`Download File` = `bank_A_sjis.csv` の cp932 バイナリ、`Read Invoices` = seed 20 件、`Read Transactions` = `[{}]`、`Update Invoices`／`Upsert Transactions` = `[{ok:true}]`）
- **入力**：A No.1 `2026/09/01, 振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ, "33,000"`、No.4 `フリコミ　ヤマダ　タロウ 9,800`、No.13 `振込 ｶ)ｻﾝﾌﾟﾙﾌｰｽﾞﾄｳｷﾖｳ 27,500`
- **観測（`Match Invoices` 出力、`Route Match Results` 出力 0 に流れた `invoice_update`）**：
  - `{"_kind": "invoice_update", "invoice_id": "INV-2026-001", "status": "paid", "paid_amount": 33000, "paid_date": "2026-09-01", "matched_txn_ids": "2026-09-01|33000|サンプルシヨウジ|", "match_confidence": "auto", "fee_deducted": 0}`
  - `{"_kind": "invoice_update", "invoice_id": "INV-2026-003", "status": "paid", "paid_amount": 9800, "paid_date": "2026-09-03", "matched_txn_ids": "2026-09-03|9800|ヤマダタロウ|", "match_confidence": "auto", "fee_deducted": 0}`
  - `{"_kind": "invoice_update", "invoice_id": "INV-2026-012", "status": "paid", "paid_amount": 27500, "paid_date": "2026-09-14", "matched_txn_ids": "2026-09-14|27500|サンプルフーズトウキヨウ|", "match_confidence": "auto", "fee_deducted": 0}`
  - INV-2026-017 は `invoice_update` に無し（同一顧客だが金額不一致 → 変更なし）
- **観測（出力 1 の `txn_row`）**：
  - `{"_kind": "txn_row", "txn_id": "2026-09-01|33000|サンプルシヨウジ|", "source": "bank_csv", "txn_date": "2026-09-01", "payer_name_raw": "振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ", "payer_name_norm": "サンプルシヨウジ", "amount": 33000, "memo": "", "imported_at": "2026-09-23T17:16:21+09:00", "matched_invoice_ids": "INV-2026-001", "status": "matched", "suggested_invoice_ids": ""}`
  - `{"_kind": "txn_row", "txn_id": "2026-09-03|9800|ヤマダタロウ|", "source": "bank_csv", "txn_date": "2026-09-03", "payer_name_raw": "フリコミ　ヤマダ　タロウ", "payer_name_norm": "ヤマダタロウ", "amount": 9800, "memo": "", "imported_at": "2026-09-23T17:16:21+09:00", "matched_invoice_ids": "INV-2026-003", "status": "matched", "suggested_invoice_ids": ""}`
  - `{"_kind": "txn_row", "txn_id": "2026-09-14|27500|サンプルフーズトウキヨウ|", "source": "bank_csv", "txn_date": "2026-09-14", "payer_name_raw": "振込 ｶ)ｻﾝﾌﾟﾙﾌｰｽﾞﾄｳｷﾖｳ", "payer_name_norm": "サンプルフーズトウキヨウ", "amount": 27500, "memo": "", "imported_at": "2026-09-23T17:16:21+09:00", "matched_invoice_ids": "INV-2026-012", "status": "matched", "suggested_invoice_ids": ""}`
- **観測（`Route Match Results`）**：出力 `[8, 11, 1]`（0 = `invoice_update` 8 件、1 = `txn_row` 11 件、2 = `summary` 1 件）。`Update Invoices`（1）→ `Upsert Transactions`（1）→ `Build Notification`（1）の順に実行（`startTime` 昇順を確認）
- **観測（通知）**：`■ 自動消込` に `・2026-09-01 振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ ¥33,000 → INV-2026-001`（要確認・候補複数・未消込には無し）。summary `auto` に `2026-09-01 → [INV-2026-001]`
- **期待（CASES §2 R01）**：上記と同一（`paid, 33000, 2026-09-01, matched_txn_ids 2026-09-01|33000|サンプルシヨウジ|, auto, fee 0`、txn `source bank_csv … status matched, suggested ""`、INV-017 変更なし、通知は自動消込のみ）
- **判定**：**PASS**（pinned; live write pending H1）
- **備考**：LINE sink（p0-sink `VDtPVF2gV4fnId1X`）実行 ['93']、Chatwork sink（`ygfRR4YUXBptN6hK`）実行 ['94']（`params.roomId` = `1`、`Authorization: Bearer <dummy>`）。`Check Notification Results` = `{"channels_attempted": 2, "channels_ok": 2, "channels_failed": 0, "errors": []}`。`imported_at` は `2026-09-23T17:16:21+09:00`（ISO 8601 +09:00、形式のみ判定）

## R02 金額のみ一致・候補 1 → amount_only, paid, 通知に要確認

- **区分**：PIN　**複製 ID**：`6Y99TvLuHXtWgPXs`　**実行 ID**：92　**pin**：`tests/pins/drive.pin.json`
- **入力**：A No.5 `2026/09/04, 振込 ｻﾄｳ ｹｲｺ, "128,000"`
- **観測**：`{"_kind": "invoice_update", "invoice_id": "INV-2026-004", "status": "paid", "paid_amount": 128000, "paid_date": "2026-09-04", "matched_txn_ids": "2026-09-04|128000|サトウケイコ|", "match_confidence": "amount_only", "fee_deducted": 0}`；`{"_kind": "txn_row", "txn_id": "2026-09-04|128000|サトウケイコ|", "source": "bank_csv", "txn_date": "2026-09-04", "payer_name_raw": "振込 ｻﾄｳ ｹｲｺ", "payer_name_norm": "サトウケイコ", "amount": 128000, "memo": "", "imported_at": "2026-09-23T17:16:21+09:00", "matched_invoice_ids": "INV-2026-004", "status": "matched", "suggested_invoice_ids": ""}`；通知 `■ 要確認（…）` に `・2026-09-04 振込 ｻﾄｳ ｹｲｺ ¥128,000 → INV-2026-004 （金額のみ一致・要確認）`；summary `needs_review` に計上、`auto` には無し（`b=3`）
- **期待**：同上（`amount_only`, `paid`, 128000, 2026-09-04, 通知は要確認、summary `b`）
- **判定**：**PASS**

## R03 手数料 220 差引 → fee_deducted=220, paid

- **区分**：PIN　**複製 ID**：`6Y99TvLuHXtWgPXs`　**実行 ID**：92　**pin**：`tests/pins/drive.pin.json`
- **入力**：A No.3 `2026/09/02, 振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ, "54,780"`（INV-2026-002 = 55,000）
- **観測**：`{"_kind": "invoice_update", "invoice_id": "INV-2026-002", "status": "paid", "paid_amount": 54780, "paid_date": "2026-09-02", "matched_txn_ids": "2026-09-02|54780|テストコウギヨウ|", "match_confidence": "fee_deducted", "fee_deducted": 220}`；`{"_kind": "txn_row", "txn_id": "2026-09-02|54780|テストコウギヨウ|", "source": "bank_csv", "txn_date": "2026-09-02", "payer_name_raw": "振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ", "payer_name_norm": "テストコウギヨウ", "amount": 54780, "memo": "", "imported_at": "2026-09-23T17:16:21+09:00", "matched_invoice_ids": "INV-2026-002", "status": "matched", "suggested_invoice_ids": ""}`；通知 `■ 要確認` に `・2026-09-02 振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ ¥54,780 → INV-2026-002 （手数料 ¥220 差引）`
- **期待**：同上（`paid_amount 54780, fee_deducted 220, match_confidence fee_deducted`、名義 `(ﾕ` → `テストコウギヨウ`）
- **判定**：**PASS**

## R04 2 請求の合算 → combined, 2 件 paid

- **区分**：PIN　**複製 ID**：`6Y99TvLuHXtWgPXs`　**実行 ID**：92　**pin**：`tests/pins/drive.pin.json`
- **入力**：A No.6 `2026/09/05, 振込 ｶ)ﾃｽﾄﾌﾞﾂｻﾝ, "1,234,567"`（INV-005 700,000 ＋ INV-006 534,567）
- **観測**：`invoice_update` 2 件 `{"_kind": "invoice_update", "invoice_id": "INV-2026-005", "status": "paid", "paid_amount": 700000, "paid_date": "2026-09-05", "matched_txn_ids": "2026-09-05|1234567|テストブツサン|", "match_confidence": "combined", "fee_deducted": 0}` と `{"_kind": "invoice_update", "invoice_id": "INV-2026-006", "status": "paid", "paid_amount": 534567, "paid_date": "2026-09-05", "matched_txn_ids": "2026-09-05|1234567|テストブツサン|", "match_confidence": "combined", "fee_deducted": 0}`（`paid_amount` は各請求の残額）；`txn_row` は 1 行 `{"_kind": "txn_row", "txn_id": "2026-09-05|1234567|テストブツサン|", "source": "bank_csv", "txn_date": "2026-09-05", "payer_name_raw": "振込 ｶ)ﾃｽﾄﾌﾞﾂｻﾝ", "payer_name_norm": "テストブツサン", "amount": 1234567, "memo": "", "imported_at": "2026-09-23T17:16:21+09:00", "matched_invoice_ids": "INV-2026-005,INV-2026-006", "status": "matched", "suggested_invoice_ids": ""}`；通知 `■ 要確認` に `・2026-09-05 振込 ｶ)ﾃｽﾄﾌﾞﾂｻﾝ ¥1,234,567 → INV-2026-005, INV-2026-006 （合算）`
- **期待**：同上
- **判定**：**PASS**

## R05 一部入金 → partial, paid_amount 加算

- **区分**：PIN　**複製 ID**：`6Y99TvLuHXtWgPXs`　**実行 ID**：92　**pin**：`tests/pins/drive.pin.json`
- **入力**：A No.8 `2026/09/08, 振込 ｻﾝﾌﾟﾙｼｽﾃﾑ(ｶ, "100,000"`（INV-2026-007 = 250,000）
- **観測**：`{"_kind": "invoice_update", "invoice_id": "INV-2026-007", "status": "partial", "paid_amount": 100000, "paid_date": "2026-09-08", "matched_txn_ids": "2026-09-08|100000|サンプルシステム|", "match_confidence": "auto", "fee_deducted": 0}`；`{"_kind": "txn_row", "txn_id": "2026-09-08|100000|サンプルシステム|", "source": "bank_csv", "txn_date": "2026-09-08", "payer_name_raw": "振込 ｻﾝﾌﾟﾙｼｽﾃﾑ(ｶ", "payer_name_norm": "サンプルシステム", "amount": 100000, "memo": "", "imported_at": "2026-09-23T17:16:21+09:00", "matched_invoice_ids": "INV-2026-007", "status": "matched", "suggested_invoice_ids": ""}`；通知 `■ 自動消込` に `・2026-09-08 振込 ｻﾝﾌﾟﾙｼｽﾃﾑ(ｶ ¥100,000 → INV-2026-007 （一部入金・残 ¥150,000）`；summary `auto` に計上（`a=4`）
- **期待**：同上（`status partial, paid_amount 100000, auto, fee 0`、通知は自動消込に残額付き、summary `a`）
- **判定**：**PASS**

## R06 同額請求 2 件・名義不一致 → ambiguous, 自動確定なし

- **区分**：PIN　**複製 ID**：`6Y99TvLuHXtWgPXs`　**実行 ID**：92　**pin**：`tests/pins/drive.pin.json`
- **入力**：A No.9 `2026/09/09, 振込 ｵｵﾊﾞ ﾏｻｵ, "44,000"`（INV-008／INV-009 が共に 44,000）
- **観測**：`invoice_update` の invoice_id 集合 = `['INV-2026-001', 'INV-2026-002', 'INV-2026-003', 'INV-2026-004', 'INV-2026-005', 'INV-2026-006', 'INV-2026-007', 'INV-2026-012']`（INV-008／009 無し）；`{"_kind": "txn_row", "txn_id": "2026-09-09|44000|オオバマサオ|", "source": "bank_csv", "txn_date": "2026-09-09", "payer_name_raw": "振込 ｵｵﾊﾞ ﾏｻｵ", "payer_name_norm": "オオバマサオ", "amount": 44000, "memo": "", "imported_at": "2026-09-23T17:16:21+09:00", "matched_invoice_ids": "", "status": "ambiguous", "suggested_invoice_ids": "INV-2026-008,INV-2026-009"}`；summary `ambiguous` = `[{"txn_date": "2026-09-09", "payer_raw": "振込 ｵｵﾊﾞ ﾏｻｵ", "amount": 44000, "source": "bank_csv", "reason": "same_amount_multiple", "candidates": [{"invoice_id": "INV-2026-008", "remaining": 44000}, {"invoice_id": "INV-2026-009", "remaining": 44000}]}]`；通知 `■ 候補複数（自動確定せず。候補から選んでください）` に `・2026-09-09 振込 ｵｵﾊﾞ ﾏｻｵ ¥44,000 → 候補: INV-2026-008(¥44,000), INV-2026-009(¥44,000)`；`c=4` に計上
- **期待**：同上（invoices 変更なし、txn `ambiguous`, `suggested INV-2026-008,INV-2026-009`（due_date 昇順）、通知は候補複数、summary `c`）
- **判定**：**PASS**

## R07 出金行 → 無視

- **区分**：PIN　**複製 ID**：`6Y99TvLuHXtWgPXs`　**実行 ID**：92（A）、101（B）　**pin**：`tests/pins/drive.pin.json`（A）、`tests/pins/r08-bank-b.pin.json`（B）
- **入力**：A No.2, 7, 10, 15（`ｶｰﾄﾞ ｻﾝﾌﾟﾙｶｰﾄﾞ` 12,800／`ﾃﾞﾝｷﾘﾖｳｷﾝ ｻﾝﾌﾟﾙﾃﾞﾝﾘﾖｸ` 8,450／`ATM ﾋｷﾀﾞｼ` 30,000／`ﾃｽｳﾘﾖｳ` 440）、B No.2, 5, 8
- **観測（A）**：`Parse Bank CSV` 出力 12 件 = txn 11 ＋ `file_stats` `{"_kind": "file_stats", "file_name": "bank_A_sjis.csv", "ignored_withdraw": 4, "rows_total": 15}`。txn の `payer_name_raw` に上記 4 名義は無く、`_row` = `[2, 4, 5, 6, 7, 9, 10, 12, 13, 14, 15]`（物理行 3, 8, 11, 16 が無い）。`txn_row` にも無し。summary `ignored_withdraw = 4`
- **観測（B）**：`Parse Bank CSV` 出力 6 件 = txn 5 ＋ `{"_kind": "file_stats", "file_name": "bank_B_utf8bom.csv", "ignored_withdraw": 3, "rows_total": 8}`。`デンワリヨウキン サンプルツウシン`／`ATMヒキダシ`／`フリカエ サンプルセイメイ` から txn は生成されず、summary `ignored_withdraw = 3`
- **期待**：出金行から txn を生成しない、A の `file_stats.ignored_withdraw = 4`／summary 4、B は 3
- **判定**：**PASS**

## R08 Shift_JIS／UTF-8 BOM → 文字化けなく名義が読める

- **区分**：PIN　**複製 ID**：`6Y99TvLuHXtWgPXs`　**実行 ID**：92（A: `bank_A_sjis.csv`）、101（B: `bank_B_utf8bom.csv`）
- **pin**：A = `tests/pins/drive.pin.json`；B = `tests/pins/r08-bank-b.pin.json`（新規。`drive.pin.json` から派生：trigger／Download の name を `bank_B_utf8bom.csv`、binary = `fixtures/bank_B_utf8bom.csv` の base64（先頭 3 バイト `efbbbf` を確認）、`Config.CSV_MAPPING` = `csv_mapping.examples.json` の `bank_B_utf8bom.csv`（`date_format yyyyMMdd, encoding utf-8`））
- **入力の性質**：A の pinned バイナリは UTF-8 として復号不可（`UnicodeDecodeError`）で cp932 として `日付,…` で始まる。B は BOM 付き UTF-8
- **観測（A、`Parse Bank CSV` → `Normalize Payer`）**：`payer_name_raw` 11 件 = `["振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ", "振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ", "フリコミ　ヤマダ　タロウ", "振込 ｻﾄｳ ｹｲｺ", "振込 ｶ)ﾃｽﾄﾌﾞﾂｻﾝ", "振込 ｻﾝﾌﾟﾙｼｽﾃﾑ(ｶ", "振込 ｵｵﾊﾞ ﾏｻｵ", "振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ", "振込 ﾃｽﾄｹﾝｾﾂ(ｶ", "振込 ｶ)ｻﾝﾌﾟﾙﾌｰｽﾞﾄｳｷﾖｳ", "振込 ﾅｶﾑﾗ ｼﾞﾛｳ"]`（`fixtures/README.md` §4 raw 列と文字単位で一致、U+FFFD なし）。`payer_name_norm` = `["サンプルシヨウジ", "テストコウギヨウ", "ヤマダタロウ", "サトウケイコ", "テストブツサン", "サンプルシステム", "オオバマサオ", "ミホンシヨウカイ", "テストケンセツ", "サンプルフーズトウキヨウ", "ナカムラジロウ"]`（半角カナ→全角、濁点合成、`ｰ`→`ー`、§4 と一致）。`txn_id` 11 件も §4 と一致
- **観測（B）**：実行成功（`CSV column not found: "取引日"` にならない＝BOM が 1 列目見出しに残らない）。`payer_name_raw` = `["0123 カ)ダミーカコウ", "ふりこみ　すずき　いちろう", "ユ)ミホンプランニング", "0045 タカハシ ミキ", "フリコミ ワタナベ ケン"]`（§5 raw 列と一致、U+FEFF／U+FFFD なし）、`txn_date` = `["2026-09-17", "2026-09-18", "2026-09-19", "2026-09-21", "2026-09-22"]`（`yyyyMMdd` → `yyyy-MM-dd`）、`payer_name_norm` = `["ダミーカコウ", "スズキイチロウ", "ミホンプランニング", "タカハシミキ", "ワタナベケン"]`。invoice_update = INV-013/014/015/016 すべて `paid / auto`、summary `{"date": "2026-09-23", "source": "drive", "n": 5, "a": 4, "b": 0, "c": 1, "rematched": 0, "skipped_existing": 0, "skipped_duplicate_in_batch": 0, "ignored_withdraw": 3, "warnings": []}`
- **復号経路**：`workflow.json` に `n8n-nodes-base.extractFromFile` ノード無し（36 ノードの型を確認）。`Parse Bank CSV` の jsCode は `TextDecoder`（BOM → UTF-8、それ以外は `CSV_MAPPING.encoding`、`code/parse_bank_csv.js` L49–56）で復号（A6／DESIGN §3.8）
- **期待**：A の raw／norm が §4 と一致し U+FFFD を含まない。B で `取引日` が見つかり raw が `0123 カ)ダミーカコウ` 等と一致。Extract From File 不使用
- **判定**：**PASS**
- **備考**：B の実行は R13 の期待（5 txn, 4 auto, 1 unmatched, `n=5 a=4 b=0 c=1 ignored_withdraw=3`）とも一致した。通知 `LINE sink（p0-sink `VDtPVF2gV4fnId1X`）実行 ['102']、Chatwork sink（`ygfRR4YUXBptN6hK`）実行 ['103']（`params.roomId` = `1`、`Authorization: Bearer <dummy>`）`

## R09 同一 CSV を 2 回投入 → 2 回目は全件 skip、書込みなし

- **区分**：PIN（シート差分ゼロの実証は LIVE-G）　**複製 ID**：`6Y99TvLuHXtWgPXs`　**実行 ID**：1 回目 92 → 2 回目 95（status `success`）
- **pin**：`tests/pins/drive-second-run.pin.json`（`Read Transactions` = `transactions.seed.csv` 1 行 ＋ 1 回目の `txn_row` 11 件）。実行前に、この pin の 11 行が **実行 92 の `Route Match Results` 出力 1（`txn_row`）と `imported_at` を除き完全一致**することを確認した（`p3-scratch/g1-drive/run1-txn-rows.json`）
- **入力**：同じ `bank_A_sjis.csv`（`Parse Bank CSV` は 1 回目と同じ 12 件を出力）、`Read Transactions` 12 件
- **観測**：`Match Invoices` 出力は 1 件のみ（`summary` `{"date": "2026-09-23", "source": "drive", "n": 0, "a": 0, "b": 0, "c": 0, "rematched": 0, "skipped_existing": 11, "skipped_duplicate_in_batch": 0, "ignored_withdraw": 4, "warnings": []}`）。`invoice_update` 0 件、`txn_row` 0 件。`Route Match Results` 出力 `[0, 0, 1]`。`Update Invoices`／`Upsert Transactions` は runData に無し（未実行）。通知タイトル `【入金消込 2026-09-23】新規の入金はありませんでした`、本文：
    【入金消込 2026-09-23】新規の入金はありませんでした
    
    （処理済みのため skip：11 件）
- **期待**：summary `n=0, a=0, b=0, c=0, skipped_existing=11, skipped_duplicate_in_batch=0`、`invoice_update` 0、`txn_row` 0、出力 0・1 が空で書込みノード未実行、タイトル `【入金消込 {date}】新規の入金はありませんでした`、本文に `（処理済みのため skip：11 件）`
- **判定**：**PASS**（pinned; live sheet diff pending H1）。§6 ゲート「2 回連続実行で状態不変」は、2 回目に書込みアイテムが 1 つも生成されないことで pinned 範囲では成立
- **備考**：LINE sink（p0-sink `VDtPVF2gV4fnId1X`）実行 ['97']、Chatwork sink（`ygfRR4YUXBptN6hK`）実行 ['99']（`params.roomId` = `1`、`Authorization: Bearer <dummy>`）。ノード別件数：`Watch Drive Folder` [1], `Config` [1], `Route by Source` [1, 0, 0, 0], `Check File Is CSV` [1, 0], `Download File` [1], `Parse Bank CSV` [12], `Collect Transactions` [1], `Read Invoices` [20], `Read Transactions` [12], `Normalize Payer` [1], `Match Invoices` [1], `Route Match Results` [0, 0, 1], `Build Notification` [1], `Check Slack Enabled` [0, 1], `Check Email Enabled` [0, 1], `Check LINE Enabled` [1, 0], `Notify LINE` [1, 0], `Check Chatwork Enabled` [1, 0], `Notify Chatwork` [1, 0], `Merge Notification Results` [2], `Check Notification Results` [1]

## R14 空シート（Always Output Data）→ 後段が止まらない

- **区分**：PIN　**複製 ID**：`6Y99TvLuHXtWgPXs`
- **R14-a**：実行 92（`tests/pins/drive.pin.json` は `Read Transactions = [{}]` を pin している）。観測：`Normalize Payer` の `existing = []`（`{}` 行を txn として数えない）、summary `skipped_existing = 0`、突合結果は R01〜R06 と同一（`n=11 a=4 b=3 c=4`）
- **R14-b**：実行 108（status `success`、last node `Check Notification Results`）。pin `tests/pins/r14b-empty-sheets.pin.json`（新規：`Read Invoices` と `Read Transactions` を共に `[{}]`）。観測：`Match Invoices` 出力 12 件 = `txn_row` 11 ＋ `summary`。11 件すべて `status unmatched`, `matched_invoice_ids ""`, `suggested_invoice_ids ""`。`invoice_update` 0 件。summary `{"date": "2026-09-23", "source": "drive", "n": 11, "a": 0, "b": 0, "c": 11, "rematched": 0, "skipped_existing": 0, "skipped_duplicate_in_batch": 0, "ignored_withdraw": 4, "warnings": []}`。`Route Match Results` `[0, 11, 1]` → `Update Invoices` 未実行、`Upsert Transactions`（1）は実行。通知タイトル `【入金消込 2026-09-23】処理 11件｜自動消込 0｜要確認 0｜未消込 11`、`■ 未消込（該当請求なし）` に 11 行（すべて `候補: —`）
- **期待**：R14-a = R01〜R06 と同一で `skipped_existing=0`；R14-b = 11 件 `unmatched`、`suggested ""`、`invoice_update` 0、`c=11`、未消込 11 行、後段が止まらない
- **判定**：**PASS**
- **備考**：LINE sink（p0-sink `VDtPVF2gV4fnId1X`）実行 ['109']、Chatwork sink（`ygfRR4YUXBptN6hK`）実行 ['110']（`params.roomId` = `1`、`Authorization: Bearer <dummy>`）

## R15 `skip_rows=1` → 見出し前の行を捨てる

- **区分**：PIN　**複製 ID**：`6Y99TvLuHXtWgPXs`　**実行 ID**：104（`skip_rows=1`、status `success`）、107（`skip_rows=0`、status `error`）
- **pin**：`tests/pins/r15-skip-rows-1.pin.json`／`tests/pins/r15-skip-rows-0-fails.pin.json`（新規：`bank_A_sjis_skip1.csv` の cp932 バイナリ、`CSV_MAPPING` は A の既定値に `skip_rows` 1／0）
- **観測（104）**：`Parse Bank CSV` 12 件、`txn_id` 11 件が実行 92 と完全一致、`_row` = `[3, 5, 6, 7, 8, 10, 11, 13, 14, 15, 16]`（A の `[2, 4, 5, 6, 7, 9, 10, 12, 13, 14, 15]` にそれぞれ +1）、summary `ignored_withdraw = 4`、`invoice_update` 8 件と `txn_row` 11 件（`imported_at` 除く）が実行 92 と同一。通知本文は 92 と同一
- **観測（107）**：`Parse Bank CSV` で失敗、エラー `CSV column not found: "日付". header = サンプル銀行 入出金明細 2026/09/01~2026/09/16 普通 1234567 [line 88]`。`Collect Transactions` 以降は未実行（黙って 0 件にならない）。Error Workflow 複製は起動せず（手動実行のため。期待どおり）
- **期待**：`skip_rows=1` で A と同一の 11 txn（`txn_id` 一致、`_row` は +1）、`ignored_withdraw=4`；`skip_rows=0` は `CSV column not found: "日付"` で失敗
- **判定**：**PASS**
- **備考**：LINE sink（p0-sink `VDtPVF2gV4fnId1X`）実行 ['105']、Chatwork sink（`ygfRR4YUXBptN6hK`）実行 ['106']（`params.roomId` = `1`、`Authorization: Bearer <dummy>`）

## R16 非 CSV ファイル → NoOp

- **区分**：PIN　**複製 ID**：`6Y99TvLuHXtWgPXs`　**実行 ID**：114（status `success`、last node `Skip Non-CSV File`）　**pin**：`tests/pins/drive-nonecsv.pin.json`（trigger `{"id": "file_test_002", "name": "memo.pdf", "mimeType": "application/pdf"}`）
- **観測**：ノード別件数 `Watch Drive Folder` [1], `Config` [1], `Route by Source` [1, 0, 0, 0], `Check File Is CSV` [0, 1], `Skip Non-CSV File` [1]。`Check File Is CSV` の false 出力に 1 件 → `Skip Non-CSV File` 実行。`Download File`／`Parse Bank CSV`／`Match Invoices`／`Build Notification`／`Notify *` は runData に無し。通知シンクへの送信なし
- **期待**：`Check File Is CSV` false → `Skip Non-CSV File`、`Download File` 以降未実行、成功終了、通知なし
- **判定**：**PASS**

## R20 `NOTIFY_MAX_LINES` 超過 → 「…他 N 件」

- **区分**：PIN　**複製 ID**：`6Y99TvLuHXtWgPXs`　**実行 ID**：111（status `success`）　**pin**：`tests/pins/r20-notify-max-lines-2.pin.json`（新規：`drive.pin.json` の `Config` に `NOTIFY_MAX_LINES: 2`）
- **観測**：`Config.NOTIFY_MAX_LINES = 2`、突合は A と同一（`n=11 a=4 b=3 c=4`）。`body_text`：
    【入金消込 2026-09-23】処理 11件｜自動消込 4｜要確認 3｜未消込 4
    
    ■ 要確認（金額のみ一致・手数料差引・合算で自動消込した分）
    ・2026-09-02 振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ ¥54,780 → INV-2026-002 （手数料 ¥220 差引）
    ・2026-09-04 振込 ｻﾄｳ ｹｲｺ ¥128,000 → INV-2026-004 （金額のみ一致・要確認）
    …他 1 件
    
    ■ 候補複数（自動確定せず。候補から選んでください）
    ・2026-09-09 振込 ｵｵﾊﾞ ﾏｻｵ ¥44,000 → 候補: INV-2026-008(¥44,000), INV-2026-009(¥44,000)
    
    ■ 未消込（該当請求なし）
    ・2026-09-11 振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ ¥66,000 → 候補: INV-2026-015(¥57,200), INV-2026-017(¥49,500)
    ・2026-09-12 振込 ﾃｽﾄｹﾝｾﾂ(ｶ ¥88,000 → 候補: —
    …他 1 件
    
    ■ 自動消込
    ・2026-09-01 振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ ¥33,000 → INV-2026-001
    ・2026-09-03 フリコミ　ヤマダ　タロウ ¥9,800 → INV-2026-003
    …他 2 件
  各セクション：要確認 2 行＋`…他 1 件`、候補複数 1 行（省略なし）、未消込 2 行＋`…他 1 件`、自動消込 2 行＋`…他 2 件`（`messages.ja.json` `more_items` = `…他 {n} 件`）。`line_text`／`chatwork_text` も同じ 3 箇所で省略。`slack_blocks` の各 text 長 = `[42, 161, 109, 146, 111]`（すべて 3,000 未満）
- **期待**：`■ 要確認` 2 行＋`…他 1 件`、`■ 候補複数` 1 行、`■ 未消込` 2 行＋`…他 1 件`、`■ 自動消込` 2 行＋`…他 2 件`、slack section text < 3,000 文字
- **判定**：**PASS**
- **備考**：LINE sink（p0-sink `VDtPVF2gV4fnId1X`）実行 ['112']、Chatwork sink（`ygfRR4YUXBptN6hK`）実行 ['113']（`params.roomId` = `1`、`Authorization: Bearer <dummy>`）

---

## 付記：実行 92 の通知全文（CASES §3 との比較）

`Build Notification.body_text` は空行を除いて CASES §3 の全文と完全一致（日付は実行日 `2026-09-23`）：

    【入金消込 2026-09-23】処理 11件｜自動消込 4｜要確認 3｜未消込 4
    
    ■ 要確認（金額のみ一致・手数料差引・合算で自動消込した分）
    ・2026-09-02 振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ ¥54,780 → INV-2026-002 （手数料 ¥220 差引）
    ・2026-09-04 振込 ｻﾄｳ ｹｲｺ ¥128,000 → INV-2026-004 （金額のみ一致・要確認）
    ・2026-09-05 振込 ｶ)ﾃｽﾄﾌﾞﾂｻﾝ ¥1,234,567 → INV-2026-005, INV-2026-006 （合算）
    
    ■ 候補複数（自動確定せず。候補から選んでください）
    ・2026-09-09 振込 ｵｵﾊﾞ ﾏｻｵ ¥44,000 → 候補: INV-2026-008(¥44,000), INV-2026-009(¥44,000)
    
    ■ 未消込（該当請求なし）
    ・2026-09-11 振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ ¥66,000 → 候補: INV-2026-015(¥57,200), INV-2026-017(¥49,500)
    ・2026-09-12 振込 ﾃｽﾄｹﾝｾﾂ(ｶ ¥88,000 → 候補: —
    ・2026-09-15 振込 ﾅｶﾑﾗ ｼﾞﾛｳ ¥5,500 → 候補: INV-2026-014(¥15,400)
    
    ■ 自動消込
    ・2026-09-01 振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ ¥33,000 → INV-2026-001
    ・2026-09-03 フリコミ　ヤマダ　タロウ ¥9,800 → INV-2026-003
    ・2026-09-08 振込 ｻﾝﾌﾟﾙｼｽﾃﾑ(ｶ ¥100,000 → INV-2026-007 （一部入金・残 ¥150,000）
    ・2026-09-14 振込 ｶ)ｻﾝﾌﾟﾙﾌｰｽﾞﾄｳｷﾖｳ ¥27,500 → INV-2026-012

## オーケストレーターへ / For the orchestrator

- 欠陥なし。担当 13 ケースすべて PASS（R01・R09 は pinned 範囲。実セル／シート差分ゼロは H1 待ち）。
- Chatwork シンクの動的パス：Webhook v2 で `:roomId` を含む path は `webhook_entity` に `webhookPath = <path>` で登録され URL は `/webhook/<webhookId>/<path>` になる。`rooms/:roomId/messages` は (webhookPath, method) の UNIQUE 制約で **1 ワークフローしか登録できない**（並行エージェントの `p3-g2-gmail-notify` と衝突して自分の sink が「active」表示のまま未登録になった）。並行実行時はエージェントごとに path を `p3-<label>/rooms/:roomId/messages` にし、`CHATWORK_API_BASE_URL` を `http://localhost:5678/webhook/<webhookId>/p3-<label>` にする必要がある。SMOKE.md／pins README の手順（path `rooms/:roomId/messages`）は単独実行前提であることを注記すると良い。
- 新規 pin 5 件は `make_pins.py` に入れていない（並行編集を避けた）。取り込むなら `make_case_pins.py` の `variant()` 相当を `pins` dict に追加すれば既存 pin の内容は変わらない。

## EN summary

All 13 assigned cases PASS on a private copy of the workflow (`6Y99TvLuHXtWgPXs`, error copy `3acOl4yifpnXTVzw`, both deleted afterwards together with the `[P3-g1-drive] Chatwork sink` `ygfRR4YUXBptN6hK` and the two dummy Header Auth credentials). Executions: 92 (bank_A: R01–R08, R14-a; body_text equals CASES §3 verbatim apart from blank lines), 95 (R09 second run: summary only, `skipped_existing=11`, no `invoice_update` / `txn_row`, Update/Upsert not executed, "新規の入金はありませんでした" + "（処理済みのため skip：11 件）"), 101 (bank_B: BOM stripped, `取引日` found, raw names intact, 5 txns / 4 auto / 1 unmatched, ignored_withdraw 3), 104 (skip_rows=1: same 11 txn_ids as A, `_row` +1), 107 (skip_rows=0: fails at Parse Bank CSV with `CSV column not found: "日付"`), 108 (R14-b: 11 unmatched, no invoice_update, 11 lines under 未消込), 111 (R20: 2 lines + `…他 N 件` per section, slack sections < 3,000 chars), 114 (R16: `Skip Non-CSV File`, nothing downstream). Execution 89 is an earlier bank_A attempt with a mis-registered Chatwork sink (Notify Chatwork 404, otherwise identical) and is superseded by 92. Every expectation of CASES.md §2 was asserted programmatically against the saved execution JSON (`assert.py`, 103 checks, 0 failures). R01 / R09 are PASS (pinned; live write / zero sheet diff pending H1). No defects found. One operational note: the dynamic Chatwork sink path must be unique per parallel agent (UNIQUE on webhook path + method), and its URL is `/webhook/<webhookId>/<path>`.
