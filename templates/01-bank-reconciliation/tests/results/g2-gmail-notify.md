# P3 結果 — g2-gmail-notify（R10 / R10-idempotent / R11 / R13 / R17 / R23 / 通知失敗）

EN summary: All 14 executions of this batch behaved as `tests/CASES.md` §2 expects. R10 (Gmail path: both fixture mails → `auto`, INV-2026-018 / 019), R10-idempotent (same two mails twice → `skipped_existing=2`, no `invoice_update` / `txn_row`, two consecutive runs produced byte-identical node outputs), R11 (`["line","chatwork"]` → both local sinks received `line_text` / `chatwork_text`; `["slack"]` / `["email"]` → only the pinned Slack / Gmail node is reached and LINE / Chatwork never execute; all four → 4/4; `[]` → no Notify / Merge / Check node runs and the execution still succeeds), R13 (bank_B: BOM stripped, `yyyyMMdd` normalised, leading digits and hiragana handled → 4 `auto` + 1 `unmatched`, `ignored_withdraw=3`), R17 (`no_parser_matched` + `parser_no_capture bankX` warnings in the `■ 警告` section, no transactions, no writes), R23 (USD invoice ignored by the matcher, reconciliation identical to the bank_A baseline, `non_jpy_invoice INV-2026-022 USD` warning at the end of the body; R23-b Schedule → `Build Notification` returns `[]`), and the notification-failure behaviour (one channel down → success with `channels_failed=1`; all channels down → the execution ends in error at `Check Notification Results`). Verdict: every case **PASS** (PIN class; the Google writes and Slack / Gmail delivery remain pending H1 / H2). One documentation nit for the orchestrator: CASES R17 shows two spaces in `・no_parser_matched  会議のご案内`, the implemented `lineWarning` joins with one space (`・no_parser_matched 会議のご案内`).

| 項目 | 値 |
|---|---|
| 実行日 | 2026-09-23（ローカル n8n 2.40.5、`http://localhost:5678`） |
| ワークフロー複製 | 本体 `f7eKdb3gMdu91n9h`（`[P3-g2-gmail-notify] 01 Bank Deposit Reconciliation`、`settings.errorWorkflow` = `5th1GIVLYBd23Ds9`）／Error Workflow `5th1GIVLYBd23Ds9`（`[P3-g2-gmail-notify] 01 Error Handler`）。`workflow.json` / `error-handler.json` から `POST /api/v1/workflows` で作成し、終了時に両方 `DELETE` 済み（`GET` は `Not Found`） |
| シンク | LINE: `p0-sink`（`VDtPVF2gV4fnId1X`、`POST http://localhost:5678/webhook/p0-sink`）／Chatwork: 自前の `[P3-g2-gmail-notify] Chatwork sink`（`faxFLoRCvBA27Npy`、Webhook v2 `webhookId = p3-g2-gmail-notify`、path `rooms/:roomId/messages` → URL `http://localhost:5678/webhook/p3-g2-gmail-notify/rooms/<roomId>/messages`）。終了時に無効化して削除 |
| Credential | HTTP Request（Header Auth）は Credential 必須（A28。Credential 無しの試走 = 実行 87 は `Notify LINE` / `Notify Chatwork` が `Credentials not found` → `Check Notification Results` が throw）。ダミー Header Auth `[P3-g2-gmail-notify] LINE Messaging API`（`eed6hX7Tyi5mauAs`）／`[P3-g2-gmail-notify] Chatwork API`（`weLpAyNTCC6Itj52`）を `POST /api/v1/credentials` で作成し、自分の複製の `Notify LINE` / `Notify Chatwork` にだけ設定。終了時に削除 |
| 実行方法 | `tests/pins/README.md` の手順。各実行の前後に `PATCH /rest/workflows/{id}` で `pinData = {}` にリセットしてから pin を保存し、`POST /rest/workflows/{id}/run` に `triggerToStartFrom` を付けて実行（ハーネス `n8n-run2.py` の複製。A11） |
| 実行時の差し替え | pin ファイルは README のシンク URL（`p2-chatwork`）のまま保存。実行直前にメモリ上で `CHATWORK_API_BASE_URL` → `http://localhost:5678/webhook/p3-g2-gmail-notify`、`LINE_TO_USER_ID` `Utest` → `Ug2gmailnotify`、`CHATWORK_ROOM_ID` `1` → `g2` に置き換えた（並列実行中の他エージェントと共用の `p0-sink` で自分の受信を識別するため）。それ以外は pin どおり |
| 保存した実行 JSON | `<scratchpad>/p3-scratch/g2-gmail-notify/exec-<id>.json`（`GET /api/v1/executions/{id}?includeData=true`、削除前に取得）、シンク側は `sink-exec-<id>.json` |
| 新規 pin | `tests/pins/make_pins_g2_gmail_notify.py` が `drive.pin.json` / `gmail.pin.json` / `schedule.pin.json`（無変更）と `build/build_workflow.py` の既定値・`fixtures/` から生成。既存 pin と `make_pins.py` は変更していない（README に追記） |
| 区分 | すべて **PIN**。`Update Invoices` / `Upsert Transactions` / `Notify Slack` / `Notify Email` は pinned（`[{ok:true}]`）で、それらに**入力されたアイテム**（`Route Match Results` 出力 0/1、`Check … Enabled` の true 出力）を判定した。実セル・実到達は LIVE-G（H1）／LIVE-N（H2）待ち |

---

## R10 Gmail 通知 → 抽出値一致、R01 と同じ経路で `auto`

- **区分**：PIN（実ポーリングと実出力形状は LIVE-G）
- **ワークフロー**：`f7eKdb3gMdu91n9h` ／ **実行 ID**：**96**（success、最終ノード `Check Notification Results`）／シンク：p0-sink 98、Chatwork sink 100
- **pin**：`tests/pins/gmail.pin.json`（`Watch Gmail Inbox` = `fixtures/mail_pinned.example.json` の 2 通、`Config` 2 件、`Read Invoices` = seed 20 件、`Read Transactions` = `[{}]`）
- **入力**：X `【サンプル銀行】ご入金のお知らせ`（`お振込人：ｶ)ﾀﾞﾐｰﾃﾞﾝｷ／金額：１０４，５００円／日付：２０２６年９月１７日`）、Y `Deposit Notification - Sample Bank`（Date ヘッダ 09-19、本文 `Transaction Date 2026-09-18 / Amount JPY 19,800 / Remitter ササキ ハナコ`）
- **観測**：
  - 実行順 `Watch Gmail Inbox [2] → Config [2] → Route by Source [0,2,0,0]`（gmail 出力）`→ Parse Mail [2] → Collect Transactions [1] → Read Invoices [20] → Read Transactions [1] → Normalize Payer [1] → Match Invoices [5] → Route Match Results [2,2,1] → Update Invoices → Upsert Transactions → Build Notification → … → Check Notification Results`
  - `Parse Mail`：`{_kind: txn, source: gmail, txn_date: "2026-09-17", payer_name_raw: "カ)ダミーデンキ", amount: 104500, memo: "【サンプル銀行】ご入金のお知らせ (gmail:18f3aabb00000001)", _parser: "bankX"}`、`{txn_date: "2026-09-18", payer_name_raw: "ササキ ハナコ", amount: 19800, memo: "Deposit Notification - Sample Bank (gmail:18f3aabb00000002)", _parser: "bankY"}`（Y は Date ヘッダではなく本文日付）
  - `Route Match Results` 出力 0（→ `Update Invoices` の入力）：`{invoice_id: INV-2026-018, status: paid, paid_amount: 104500, paid_date: 2026-09-17, matched_txn_ids: "2026-09-17|104500|ダミーデンキ|【サンプル銀行】ご入金のお知らせ(gmail:18f3aabb00000001)", match_confidence: auto, fee_deducted: 0}`、`{invoice_id: INV-2026-019, status: paid, paid_amount: 19800, paid_date: 2026-09-18, matched_txn_ids: "2026-09-18|19800|ササキハナコ|depositnotification-samplebank(gmail:18f3aabb00000002)", match_confidence: auto, fee_deducted: 0}`
  - 出力 1（→ `Upsert Transactions` の入力）：2 行、`source gmail`、`payer_name_norm ダミーデンキ / ササキハナコ`、`memo` 上記、`matched_invoice_ids INV-2026-018 / INV-2026-019`、`status matched`、`suggested_invoice_ids ""`、`imported_at 2026-09-23T17:16:22+09:00`
  - summary：`n=2, a=2, b=0, c=0, warnings=[]`
  - `Build Notification`：title `【入金消込 2026-09-23】処理 2件｜自動消込 2｜要確認 0｜未消込 0`、body `■ 自動消込\n・2026-09-17 カ)ダミーデンキ ¥104,500 → INV-2026-018\n・2026-09-18 ササキ ハナコ ¥19,800 → INV-2026-019`
  - シンク：p0-sink 98 の `body.messages[0].text` と Chatwork sink 100 の `body.body` が上記本文と一致、`Check Notification Results` `{attempted 2, ok 2, failed 0}`
- **期待（CASES R10）**：抽出値 X `104500 / カ)ダミーデンキ / 2026-09-17`、Y `19800 / ササキ ハナコ / 2026-09-18`；`inv[018] / inv[019]` paid・auto・上記 `matched_txn_ids`；transactions 2 行 `source gmail`・`memo`・`matched`；タイトル `処理 2件｜自動消込 2｜要確認 0｜未消込 0`；`Route by Source` gmail 出力 → `Parse Mail` → `Collect Transactions`
- **判定**：**PASS**（pinned; live Gmail polling / sheet write pending H1）

## R10-idempotent 同じ 2 通を 2 回投入 → 2 回目は全件 skip、書込みなし（2 回連続でも同一）

- **区分**：PIN（シート差分ゼロの実証は LIVE-G）
- **実行 ID**：**115**（1 回目の再投入）と **118**（2 回連続の 2 回目）。いずれも success／シンク 116・117、119・120
- **pin**：`tests/pins/R10-idempotent-gmail-second-run.pin.json`（`gmail.pin.json` の `Read Transactions` を `transactions.seed.csv` 1 行 ＋ 実行 96 の `txn_row` 2 件（`_kind` 除去）にしたもの。`--txn-rows` で生成）
- **入力**：R10 と同じ 2 通。台帳 `Read Transactions` 3 件（`2026-08-28|66000|ミホンシヨウカイ|`, `2026-09-17|104500|ダミーデンキ|…(gmail:18f3aabb00000001)`, `2026-09-18|19800|ササキハナコ|…(gmail:18f3aabb00000002)`）
- **観測（115）**：`Parse Mail [2]`（同じ 2 txn）→ `Normalize Payer` の `existing` 3 件 → `Match Invoices [1]` = summary のみ `{n:0, a:0, b:0, c:0, rematched:0, skipped_existing:2, skipped_duplicate_in_batch:0, warnings:[]}` → `Route Match Results [0,0,1]`（`Update Invoices` / `Upsert Transactions` は runData に無し＝未実行）→ `Build Notification` title `【入金消込 2026-09-23】新規の入金はありませんでした`、body `…\n\n（処理済みのため skip：2 件）` → 両シンク受信、`Check Notification Results {attempted 2, ok 2, failed 0}`
- **観測（118）**：全ノードの出力 JSON が 115 と完全一致（`imported_at` を含む txn_row が無いため差分ゼロ。ノード集合・各出力を機械比較して差分 0 ノード）
- **期待（CASES R09-b / §6 P3 ゲート）**：2 回目は `skipped_existing=2`、`invoice_update` 0・`txn_row` 0、書込みノード未実行、`新規の入金はありませんでした` ＋ `（処理済みのため skip：2 件）`；2 回連続で状態が変わらない
- **判定**：**PASS**（pinned; sheet diff = 0 pending H1）

## R11 全チャネル通知 → 設定分のノードだけ実行

- **区分**：PIN（ルーティング）。到達は LINE / Chatwork のローカルシンクで確認、Slack / Gmail は pinned（LIVE-N H2）
- **pin**：`tests/pins/drive.pin.json`（`["line","chatwork"]`）、`tests/pins/R11-slack.pin.json`（`["slack"]` + `Notify Slack` pinned）、`tests/pins/R11-email.pin.json`（`["email"]` + `Notify Email` pinned）、`tests/pins/R11-all-four.pin.json`（4 チャネル + Slack / Email pinned）、`tests/pins/R11-none.pin.json`（`[]`）。すべて bank_A（R01〜R08 と同じ消込：`Match Invoices [20]`、`Route Match Results [8,11,1]`、summary `n=11 a=4 b=3 c=4`）
- **観測**：

| NOTIFY_CHANNELS | 実行 ID | Check Slack / Email / LINE / Chatwork Enabled（true, false） | 実行された Notify ノード | Merge → Check Notification Results | シンク |
|---|---|---|---|---|---|
| `["line","chatwork"]` | **121** | [0,1] / [0,1] / [1,0] / [1,0] | `Notify LINE` [1,0]、`Notify Chatwork` [1,0]（Slack / Email は runData 無し） | Merge [2] → `{attempted 2, ok 2, failed 0}` | p0-sink 122（`to: Ug2gmailnotify`、`messages[0].text` == `line_text`、`Authorization` ヘッダにダミー値、JSON）、Chatwork sink 123（`params.roomId = g2`、form-urlencoded `body` == `chatwork_text`） |
| `["slack"]` | **124** | [1,0] / [0,1] / [0,1] / [0,1] | `Notify Slack` のみ（pinned `{ok:true}`、入力 = `Check Slack Enabled` true 出力 1 件、title `【入金消込 2026-09-23】処理 11件｜…`）。LINE / Chatwork / Email は runData 無し | Merge [1] → `{attempted 1, ok 1, failed 0}` | 受信なし |
| `["email"]` | **125** | [0,1] / [1,0] / [0,1] / [0,1] | `Notify Email` のみ（pinned、入力 1 件） | Merge [1] → `{attempted 1, ok 1, failed 0}` | 受信なし |
| `["slack","email","line","chatwork"]` | **126** | [1,0] / [1,0] / [1,0] / [1,0] | 4 ノードすべて（Slack / Email pinned、LINE / Chatwork は実 HTTP） | Merge [4] → `{attempted 4, ok 4, failed 0}` | 127 / 128 |
| `[]` | **129** | [0,1] / [0,1] / [0,1] / [0,1] | なし。最終ノード `Check Chatwork Enabled`、`Merge Notification Results` / `Check Notification Results` も未実行、status **success** | — | 受信なし |

  - `Build Notification` 出力キー：`title / body_text / slack_blocks / line_text / chatwork_text` が揃い、`line_text == chatwork_text == body_text`。`slack_blocks` は header 1 + section 4（最長 section 228 文字）
  - `Notify LINE` の `jsonBody` は `messages[0].text = $json.line_text`、`Notify Chatwork` の `body = $json.chatwork_text`（`workflow.json` の式。シンク受信値がそれぞれ `line_text` / `chatwork_text` と一致することで実証）。`Notify Slack` は `blocksUi = JSON.stringify({blocks: $json.slack_blocks})`・`text = $json.title`、`Notify Email` は `subject = $json.title`・`message = $json.body_text`（pinned のため式は静的確認のみ）
  - body 全文は CASES §3 と一致（実行 121 の `body_text`。日付 `2026-09-23`）
- **期待（CASES R11）**：設定したチャネルの IF だけ true；`[]` では 4 IF が false で Notify も Merge / Check も未実行；出力キー 5 種；LINE は `line_text`、Chatwork は `chatwork_text`
- **判定**：**PASS**（pinned; Slack / Gmail delivery pending H2）
- **監査後の補足（fix）**：CASES が求める 6 通りのうち `["line"]` 単独・`["chatwork"]` 単独はこの表には無い（121 で両方同時に確認）。監査指摘により fix グループが作業ツリー版の複製で `["line"]` = 実行 185、`["chatwork"]` = 実行 214 を追加し、他 4 通り（188 / 189 / 211 / 192）と `["line","chatwork"]`（206）も再実行した。本表の実行 121〜129 は HEAD（`93a0975`）版 `Check Notification Results` のもの。詳細は `tests/results/fix.md`

## R13 bank_B（BOM + yyyyMMdd + 先頭番号 + ひらがな）→ 正しくパース

- **区分**：PIN ／ **実行 ID**：**130**（success）／シンク 131・132
- **pin**：`tests/pins/R13-bank-B.pin.json`（`drive.pin.json` からトリガー `{name: bank_B_utf8bom.csv, mimeType: text/csv}`、`Download File` = `fixtures/bank_B_utf8bom.csv` の base64、`Config.CSV_MAPPING` = `csv_mapping.examples.json` の `bank_B_utf8bom.csv`（`取引日 / 内容 / お預入 / お引出`, `date_format yyyyMMdd`, `encoding utf-8`）に差し替え）
- **観測**：
  - `Parse Bank CSV [6]` = 5 txn + `file_stats {file_name: bank_B_utf8bom.csv, ignored_withdraw: 3, rows_total: 8}`。`CSV column not found` にならず、出力に U+FFFD / U+FEFF なし
  - txn（`txn_date` / `payer_name_raw` / `amount` / `_row`）：`2026-09-17 / 0123 カ)ダミーカコウ / 41800 / 2`、`2026-09-18 / ふりこみ　すずき　いちろう / 15400 / 4`、`2026-09-19 / ユ)ミホンプランニング / 57200 / 5`、`2026-09-21 / 0045 タカハシ ミキ / 12100 / 7`、`2026-09-22 / フリコミ ワタナベ ケン / 7700 / 8`（日付は `yyyyMMdd` → `yyyy-MM-dd`）
  - `Match Invoices [10]` → `Route Match Results [4,5,1]`：`invoice_update` = `INV-2026-013 paid auto 41800 (2026-09-17|41800|ダミーカコウ|)`、`INV-2026-014 paid auto 15400 (2026-09-18|15400|スズキイチロウ|)`、`INV-2026-015 paid auto 57200 (2026-09-19|57200|ミホンプランニング|)`、`INV-2026-016 paid auto 12100 (2026-09-21|12100|タカハシミキ|)`；`txn_row` 5 行、`payer_name_norm` = `ダミーカコウ / スズキイチロウ / ミホンプランニング / タカハシミキ / ワタナベケン`、最後の 1 行 `2026-09-22|7700|ワタナベケン| status unmatched, matched_invoice_ids "", suggested_invoice_ids ""`
  - summary `{n:5, a:4, b:0, c:1, ignored_withdraw:3, warnings:[]}`
  - 通知：title `処理 5件｜自動消込 4｜要確認 0｜未消込 1`、`■ 未消込（該当請求なし）\n・2026-09-22 フリコミ ワタナベ ケン ¥7,700 → 候補: —`、`■ 自動消込` に `・2026-09-17 0123 カ)ダミーカコウ ¥41,800 → INV-2026-013` 他 4 行。両シンク受信、`{attempted 2, ok 2}`
- **期待（CASES R13 / fixtures README §5）**：5 txn、`payer_name_norm` と `txn_id` 上記、INV-013〜016 paid・auto、No.7 unmatched・suggested ""、`n=5 a=4 b=0 c=1 ignored_withdraw=3`、通知の未消込 1 行＋自動消込 4 行
- **判定**：**PASS**（pinned; live write pending H1）

## R17 パーサ不一致メール → warning が通知に出る、txn なし

- **区分**：PIN ／ **実行 ID**：**133**（success）／シンク 134・135
- **pin**：`tests/pins/R17-parser-mismatch.pin.json`（`gmail.pin.json` のトリガーを CASES R17 の 2 通 `{id 18f3aabb00000009, from someone@example.org, subject 会議のご案内, text 来週の会議についてご連絡します。}` / `{id 18f3aabb00000010, from サンプル銀行 <notice@example.jp>, subject 【サンプル銀行】ご入金のお知らせ, text 本日の入金はありません。}` に、`Config` も 2 件に差し替え）
- **観測**：
  - `Parse Mail [2]`：`{_kind: warning, type: no_parser_matched, message_id: 18f3aabb00000009, from: someone@example.org, subject: 会議のご案内}`、`{_kind: warning, type: parser_no_capture, parser: bankX, message_id: 18f3aabb00000010, subject: 【サンプル銀行】ご入金のお知らせ}`
  - `Collect Transactions`：`txns: []`, `warnings` 2 件 → `Match Invoices [1]` = summary `{n:0, a:0, b:0, c:0, skipped_existing:0, warnings: [上記 2 件]}` → `Route Match Results [0,0,1]`（`Update Invoices` / `Upsert Transactions` 未実行）
  - `Build Notification`：title `【入金消込 2026-09-23】新規の入金はありませんでした`、body `…\n\n■ 警告\n・no_parser_matched 会議のご案内\n・parser_no_capture bankX 【サンプル銀行】ご入金のお知らせ`。両シンク受信、`{attempted 2, ok 2}`
- **期待（CASES R17）**：warning 2 種、`txns=[]`、summary のみ `n=0`、書込みなし、タイトル `新規の入金はありませんでした`、`■ 警告` に 2 行
- **判定**：**PASS**。注記：CASES の期待文 `・no_parser_matched  会議のご案内` は空白 2 つ、実装（`build_notification.js` `lineWarning` = `[type, parser, subject, invoice_id, currency].filter(Boolean).join(' ')`）は空白 1 つ。内容は同一なので実装側を正とし、CASES の表記を 1 空白に直すことを提案（オーケストレーター判断）

## R23 非 JPY の請求は突合されず警告になる（＋ R23-b Schedule）

- **区分**：PIN ／ **実行 ID**：**136**（R23、success、シンク 137・138）、**139**（R23-b、success、最終ノード `Build Notification`）
- **pin**：`tests/pins/R23-non-jpy.pin.json`（`drive.pin.json` の `Read Invoices` に `INV-2026-022, C-019, Sample Overseas LLC, サンプルオーバーシーズ, overseas@example.com, 128000, USD, 2026-09-01, 2026-09-30, unpaid, 0, …` を追加。21 件）、`tests/pins/R23-b-non-jpy-schedule.pin.json`（`schedule.pin.json` の `Read Invoices` を同じ 21 件に。`Read Transactions` = seed 1 行）
- **観測（136）**：
  - `Read Invoices [21]`（最終行 `INV-2026-022 / USD`）→ `Normalize Payer` の `invoices` 21 件 → `Match Invoices [20]` → `Route Match Results [8,11,1]`
  - `invoice_update` 8 件・`txn_row` 11 件が、同じ pin の USD 行なし（実行 121）と `imported_at` を除いて**完全一致**（機械比較）。更新対象 `INV-2026-001, 002, 003, 004, 005, 006, 007, 012`。A-5 は引き続き `INV-2026-004 paid amount_only 128000`（`txn 2026-09-04|128000|サトウケイコ| matched INV-2026-004`）。`INV-2026-022` は `invoice_update`・`suggested_invoice_ids`・candidates のどこにも出ない
  - summary `{n:11, a:4, b:3, c:4, warnings: [{type: non_jpy_invoice, invoice_id: INV-2026-022, currency: USD}]}`
  - `Build Notification` body 末尾 `…INV-2026-012\n\n■ 警告\n・non_jpy_invoice INV-2026-022 USD`（それ以外は CASES §3 の全文と一致）。両シンク受信、`{attempted 2, ok 2}`
- **観測（139）**：`Run Daily Rematch → Config → Route by Source [0,0,1,0] → Collect Transactions → Read Invoices [21] → Read Transactions [1] → Normalize Payer → Match Invoices [1]`（summary `{source: schedule, n:0, rematched:0, warnings: [non_jpy_invoice INV-2026-022 USD]}`）`→ Route Match Results [0,0,1] → Build Notification [0]`。以降のノード未実行、通知なし、status success
- **期待（CASES R23）**：R01〜R06 と同一の結果、INV-022 が候補に入らない、`warnings` に `non_jpy_invoice` 1 件、本文末尾に `■ 警告 ・non_jpy_invoice INV-2026-022 USD`；R23-b は `Build Notification` が `[]`
- **判定**：**PASS**（pinned; live write pending H1）

## 通知失敗（R11-b 相当）：1 チャネル失敗 → 成功・`failed=1`／全滅 → `Check Notification Results` で実行エラー

- **区分**：PIN（到達不能 URL `http://127.0.0.1:9` で代替。Slack Credential 無し）
- **pin**：`tests/pins/notify-partial-fail.pin.json`（`CHATWORK_API_BASE_URL` = 到達不能、LINE はシンク）、`tests/pins/notify-all-fail.pin.json`（両方到達不能）
- **観測（一部失敗、実行 ID 140、success）**：`Notify LINE [1,0]`（p0-sink 141 受信）、`Notify Chatwork [0,1]`（error 出力：入力 json ＋ `error: {message: "connect ECONNREFUSED 127.0.0.1:9", name, stack, code: ECONNREFUSED}`）→ `Merge Notification Results [2]` → `Check Notification Results {channels_attempted: 2, channels_ok: 1, channels_failed: 1, errors: ["connect ECONNREFUSED 127.0.0.1:9"]}`。最終ノード `Check Notification Results`、status success。シートへの書込み（pinned）は通知の前に完了
- **観測（全滅、実行 ID 142、error）**：`Notify LINE [0,1]`、`Notify Chatwork [0,1]`（両方 error 出力）→ `Merge [2]` → `Check Notification Results` が throw：`All notification channels failed (2): connect ECONNREFUSED 127.0.0.1:9 / connect ECONNREFUSED 127.0.0.1:9`。`status = error`、`lastNodeExecuted = Check Notification Results`。Error Workflow 複製（`5th1GIVLYBd23Ds9`）の実行は 0 件 — 手動実行では Error Trigger が発火しない（CASES R21 前提、公式仕様）ため想定どおり。自動実行での起動は R21 担当ケースで確認
- **期待（CASES R11-b / DESIGN D17）**：一部失敗は `attempted 2, ok 1, failed 1` で実行成功（Error Workflow 起動なし）、全滅は throw して実行失敗
- **判定**：**PASS**

---

## オーケストレーターへの申し送り / For the orchestrator

1. **全ケース PASS**。FAIL・製品側の欠陥なし（`workflow.json` / `error-handler.json` / `code/` / `build/` / `fixtures/` は無変更）。
2. **CASES.md R17 の表記ゆれ**：`・no_parser_matched  会議のご案内`（空白 2 つ）→ 実装は空白 1 つ。CASES を `・no_parser_matched 会議のご案内` に直すか判断が必要（実装変更は不要）。
3. **追加ファイル**：`tests/pins/make_pins_g2_gmail_notify.py` と生成物 `R10-idempotent-gmail-second-run` / `R11-slack` / `R11-email` / `R11-all-four` / `R11-none` / `R13-bank-B` / `R17-parser-mismatch` / `R23-non-jpy` / `R23-b-non-jpy-schedule` `.pin.json`（`tests/pins/README.md` に節を追記）。`make_pins.py` と既存 pin は無変更。
4. **ライブ未検証**（BLOCKERS H1 / H2）：`Update Invoices` / `Upsert Transactions` の実セル、Gmail 実ポーリング（R10 LIVE-G）、Slack / Gmail 送信の実到達（R11 LIVE-N）。
5. 実行 ID の一覧：87（Credential 無しの試走、error）、96、115、118、121、124、125、126、129、130、133、136、139、140、142。複製ワークフローは削除済みのため、n8n 上の実行は消えている可能性がある。全 JSON は `<scratchpad>/p3-scratch/g2-gmail-notify/exec-<id>.json`。
