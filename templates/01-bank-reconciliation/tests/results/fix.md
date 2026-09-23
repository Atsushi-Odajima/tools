# P3 結果 — fix（監査指摘の再実行：R11 単独チャネル、R11-b、D34 素通り検知、フルパス、現行作業ツリー版での再検証）

EN summary: Audit follow-up run on the **current working-tree** `workflow.json` / `error-handler.json` (git HEAD `93a0975` plus the post-P3 D34 change to `Check Notification Results`; `build/build_workflow.py --check` reports both files unchanged, i.e. the on-disk JSON is the deterministic build output). 13 executions on my own copies (`[P3-fix] …`, deleted afterwards): the full Drive path (200) reproduces CASES §3 byte-for-byte and R09's second run (203) skips all 11 rows without touching the write nodes; all six R11 `NOTIFY_CHANNELS` variants now have their own execution — `["line"]` 185, `["chatwork"]` 214, `["slack"]` 188, `["email"]` 189, all four 211, `[]` 192, plus `["line","chatwork"]` 206 — with the expected IF routing, executed Notify nodes, `Check Notification Results` counters and sink receipts; R11-b partial failure 193 (`{2,1,0→1}` success) and all-fail 195 (throw, status error); and the new D34 pass-through logic was exercised for the first time in n8n: with `Notify Email` disabled on the copy, `["email","line"]` → 196 success `{attempted 2, ok 1, failed 1, errors ["notify node disabled or not executed (payload passed through)"]}` and `["email"]` → 198 error `All notification channels failed (1): notify node disabled …` (the HEAD logic would have reported 198 as a success — that is the defect D34 fixes). 0 FAIL. Every saved execution's `workflowData` carries the working-tree jsCode of all 7 Code nodes (md5 below). All copies, the Chatwork sink and the two dummy Header Auth credentials were deleted; the copies' executions are gone from n8n, the saved `exec-<id>.json` files (hashes in `evidence-sha256.md`) are the evidence.

| 項目 | 値 |
|---|---|
| 実行日 | 2026-09-23 09:16〜09:18 UTC（ローカル n8n 2.40.5、`http://localhost:5678`） |
| 対象の版 | git HEAD `93a0975ff096824af51151b32f93b2b42239842f` ＋ 作業ツリーの未コミット変更（`Check Notification Results` の D34 素通り検知、付箋 S5 / S6 / E1 の高さ）。`workflow.json` sha256 `19d84ba99fc047c2e40888ac46f55ec83fd212164f3733de07998fb618f63fc1`、`error-handler.json` sha256 `f4c884aa958b52bd7d8a1a183c2a830fdfb82cc014c833f883a613113c954112`。`PYTHONDONTWRITEBYTECODE=1 python3 build/build_workflow.py --check` → `OK (unchanged)` 両ファイル（作業ツリーの JSON は `build/` と `code/` からの決定的ビルド出力そのもの。製品ファイルは本作業では変更していない） |
| Code ノードの jsCode md5（`workflow.json`） | Parse Bank CSV `83c68d9b29751a61d7799fdc404f3965` / Parse Mail `9a6b9f24044ee55707cfcc3496b3600d` / Collect Transactions `6da42b87471d5d4dac290882ccebccf3` / Normalize Payer `7742d5abcc2fa3f74821c5b393695cc7` / Match Invoices `6ecfe309d39b8815c77b79af01680457` / Build Notification `8633097a7836915415f337cfd734c301` / **Check Notification Results `69be2a4c361070317ef97380ecf292b0`**（HEAD 版は `e1da220f27…`。他 6 ノードは HEAD と同一）。`error-handler.json` Build Error Message `999a206481e0175b7eed6efc4a85e29e`（HEAD と同一）。保存した 19 実行すべての `workflowData` がこの md5 と一致（`verify.py` の `rev` 判定） |
| ワークフロー複製 | 本体 `7iZwuEN7GUeToE8H`（`[P3-fix] [Odaji] 01 Bank Deposit Reconciliation v1.0.0`、`settings.errorWorkflow` = `ZzZMfALj5IzDn4wL`）／本体（`Notify Email` を `disabled: true` にした複製）`SrdBBEoGnI15qIo2`（R11-c 用）／Error Workflow `ZzZMfALj5IzDn4wL`。いずれも作業ツリーの JSON から `POST /api/v1/workflows` で作成し、終了時に `DELETE`（`GET` → 404 を確認）。製品の登録本体（`EMlrzFHwUpu7xvZx` / `S9vwW2D7jBCIvCQn`）は未使用 |
| シンク | LINE: `p0-sink`（`VDtPVF2gV4fnId1X`）／Chatwork: 自作 `[P3-fix] Chatwork sink`（`RCP5XmAH8kHhv4rC`、Webhook v2 POST、path `p3-fix/rooms/:roomId/messages`、`webhookId = p3-fix` → URL は `http://localhost:5678/webhook/p3-fix/p3-fix/rooms/<roomId>/messages`）。終了時に無効化して削除 |
| Credential | ダミー Header Auth `[P3-fix] LINE Messaging API`（`6rXur3JBdtzQlzBu`）／`[P3-fix] Chatwork API`（`TA42bSPDjCtxxdcg`）を複製の `Notify LINE` / `Notify Chatwork` にだけ設定（A28）。終了時に削除（`/rest/credentials` → `[]`） |
| 実行方法 | `n8n-run2.py <copy> "Watch Drive Folder" --pin <run pin> --out <file>`（A11：`PATCH /rest/workflows/{id}` で `pinData` 保存 → `POST /rest/workflows/{id}/run` に `triggerToStartFrom`）。各実行の前後に `pinData = {}` に戻した（削除前に両複製とも `{}` を確認） |
| 実行時の差し替え | pin ファイルは他の pin と同じ `p2-chatwork` の URL のまま。実行直前にメモリ上で `CHATWORK_API_BASE_URL` → `http://localhost:5678/webhook/p3-fix/p3-fix`、`LINE_TO_USER_ID` → `Ufix`、`CHATWORK_ROOM_ID` → `fix` に置換（共用 `p0-sink` で自分の受信を識別するため）。それ以外は pin どおり |
| 保存した実行 JSON | `<scratchpad>/p3-scratch/fix/exec-<id>.json`（19 件：179 / 181 / 183 / 185 / 187 / 188 / 189 / 190 / 192 / 193 / 195 / 196 / 198 / 200 / 203 / 206 / 209 / 211 / 214）と `sink-exec-<id>.json`（p0-sink 180 / 182 / 184 / 186 / 191 / 194 / 197 / 201 / 204 / 207 / 212、Chatwork シンク 199（疎通 probe）/ 202 / 205 / 208 / 210 / 213 / 215）。SHA-256 は `tests/results/evidence-sha256.md`（p3f の 176 / 178 / 177 を含む 113 ファイル）。複製の実行は削除後 n8n から消えている（`GET /api/v1/executions/200` → 404 を確認） |
| 判定スクリプト | `<scratchpad>/p3-scratch/fix/verify.py`（判定 59 件、FAIL 0。CASES §3 の全文は CASES.md のコードブロックから読み込み、日付だけ実行日に置換） |
| 新規 pin | `tests/pins/R11-line.pin.json`、`R11-chatwork.pin.json`、`R11-c-passthrough-email-line.pin.json`、`R11-c-passthrough-email.pin.json`（すべて `drive.pin.json` の `Config.NOTIFY_CHANNELS` だけを変えた単体 JSON。`make_pins.py` と既存 pin は無変更。README に追記） |

---

## 監査指摘との対応 / Audit findings → what was done

| 指摘 | 対応 |
|---|---|
| (blocker) P3 の証拠が HEAD 版 `Check Notification Results` のもので、作業ツリー（D34 素通り検知）を検証していない | **fixed（再実行）**。作業ツリー版で複製を作り直し、R11 全 6 通り＋`["line","chatwork"]`、R11-b（一部失敗・全滅）、フルパス（bank_A → CASES §3 全文一致、R09 2 回目）、D34 素通り（R11-c ×2）を再実行。`build_workflow.py --check` で作業ツリーの JSON がビルド出力と一致することを確認（再ビルドで差分は出ない）。製品ファイルの採否（revert か accept か）はオーケストレーターの判断のまま。監査時に「実在しない」とされた参照は、並行エージェント p3f が本作業中に解消した：DESIGN D34（09:11 UTC）、ASSUMPTIONS A35〜A38（09:12 UTC）、`tests/SMOKE-p3-followup.md`（09:13 UTC。F1 / F2 の定義と p3f 自身の実機確認 176 / 178 の記録） |
| (major) 検証した版（コミット・jsCode ハッシュ）が RESULTS.md に無い | **fixed**。本書の表と RESULTS.md の表に、g1〜g3 が実行した版（HEAD `93a0975`、`Check Notification Results` md5 `e1da220f27bc…`）と fix が実行した版（作業ツリー、同 `69be2a4c36…`）を併記 |
| (minor) 複製の実行の n8n 上の有無が「未確認」 | **fixed**。n8n 稼働中に確認：複製の実行は消えている。p0-sink の実行 28 件（90〜174 と fix の 11 件）は現存し、保存 JSON と JSON 同一。`tests/results/evidence-sha256.md` に全 110 ファイルの SHA-256 を記録 |
| (minor) R11 の `["line"]` / `["chatwork"]` 単独が未実行 | **fixed**。185（line）/ 214（chatwork）を追加。§2 の R11 行に反映 |

---

## fix-1 フルパス（bank_A 初期状態、`["line","chatwork"]`）→ R01〜R08 基準・CASES §3 全文一致

- **区分**：PIN（`Update Invoices` / `Upsert Transactions` は pinned。実セルは LIVE-G H1）＋ LIVE-N（LINE / Chatwork はローカルシンク）
- **複製**：`7iZwuEN7GUeToE8H`　**実行 ID**：**200**（success、最終ノード `Check Notification Results`）　**pin**：`tests/pins/drive.pin.json`（差し替えは上表）
- **入力**：`Watch Drive Folder` / `Download File` = `bank_A_sjis.csv`（Shift_JIS バイナリ）、`Read Invoices` = seed 20 行、`Read Transactions` = `[{}]`、`Config` = 既定＋`NOTIFY_CHANNELS ["line","chatwork"]`
- **観測**：`Parse Bank CSV` 12 件（txn 11 ＋ file_stats）；`Match Invoices` summary `{n 11, a 4, b 3, c 4, rematched 0, skipped_existing 0, skipped_duplicate_in_batch 0, ignored_withdraw 4}`；`Route Match Results` [8, 11, 1]；`Update Invoices`（index 12, startTime 1790155026604）→ `Upsert Transactions`（13, …613）→ `Build Notification`（14, …621）の順；`Build Notification` の `body_text` が **CASES §3 のコードブロックと完全一致**（日付 `2026-09-23`）、`line_text == chatwork_text == body_text`、キー `title / body_text / slack_blocks / line_text / chatwork_text`；IF [0,1] / [0,1] / [1,0] / [1,0]；`Notify LINE` [1,0]、`Notify Chatwork` [1,0]；`Check Notification Results` `{channels_attempted 2, channels_ok 2, channels_failed 0, errors []}`
- **シンク**：p0-sink **201**（`to: Ufix`、`messages[0].text` == `line_text`、`Authorization: Bearer dummy`、`application/json`）、Chatwork sink **202**（`params.roomId = fix`、`application/x-www-form-urlencoded`、`body` == `chatwork_text`）
- **期待（CASES R01〜R08、§3）**：上記のとおり
- **判定**：**PASS**（pinned; live write pending H1）

## fix-2 R09 同一 CSV の 2 回目 → 全件 skip、書込みノード未実行

- **複製**：`7iZwuEN7GUeToE8H`　**実行 ID**：**203**（success）　**pin**：`tests/pins/drive-second-run.pin.json`（`Read Transactions` = seed 1 行 ＋ 1 回目の `txn_row` 11 件 = 12 行）
- **観測**：`Match Invoices` は summary 1 件のみ `{n 0, a 0, b 0, c 0, rematched 0, skipped_existing 11, skipped_duplicate_in_batch 0, ignored_withdraw 4}`；`Route Match Results` [0, 0, 1]；`Update Invoices` / `Upsert Transactions` は runData に無し；タイトル `【入金消込 2026-09-23】新規の入金はありませんでした`、本文に `（処理済みのため skip：11 件）`；`Check Notification Results` `{2, 2, 0}`；シンク 204（LINE）/ 205（Chatwork）受信
- **期待（CASES R09）**：2 回目は skip のみ、書込みなし。**2 回連続実行で状態不変**（1 回目 200 の出力を入力にした 2 回目が書込みアイテムを生成しない）
- **判定**：**PASS**（pinned; sheet diff pending H1）

## fix-3 R11 全チャネル通知 → 設定分のノードだけ実行（6 通り＋`["line","chatwork"]`）

- **区分**：PIN（ルーティング）＋ LIVE-N（LINE / Chatwork はシンク、Slack / Gmail は pinned `[{ok:true}]`、H2）
- **複製**：`7iZwuEN7GUeToE8H`（すべて）
- **観測**（すべて success、bank_A の消込は fix-1 と同一、`body_text` は全実行で CASES §3 と一致）：

| NOTIFY_CHANNELS | 実行 ID | pin | Check Slack / Email / LINE / Chatwork Enabled（true, false） | 実行された Notify ノード | Check Notification Results | シンク受信 |
|---|---|---|---|---|---|---|
| `["line"]` | **185** | `R11-line.pin.json`（新規） | [0,1] / [0,1] / [1,0] / [0,1] | `Notify LINE` [1,0] のみ | `{1, 1, 0}` | p0-sink 186（`messages[0].text` == `line_text`）。Chatwork シンク受信なし |
| `["chatwork"]` | **214** | `R11-chatwork.pin.json`（新規） | [0,1] / [0,1] / [0,1] / [1,0] | `Notify Chatwork` [1,0] のみ | `{1, 1, 0}` | Chatwork sink 215（`roomId fix`、`body` == `chatwork_text`）。p0-sink 受信なし |
| `["slack"]` | **188** | `R11-slack.pin.json` | [1,0] / [0,1] / [0,1] / [0,1] | `Notify Slack` のみ（pinned 出力 `[{ok:true}]`） | `{1, 1, 0}` | 受信なし |
| `["email"]` | **189** | `R11-email.pin.json` | [0,1] / [1,0] / [0,1] / [0,1] | `Notify Email` のみ（pinned） | `{1, 1, 0}` | 受信なし |
| `["slack","email","line","chatwork"]` | **211** | `R11-all-four.pin.json` | [1,0] / [1,0] / [1,0] / [1,0] | 4 ノードすべて（Slack / Email pinned、LINE / Chatwork 実 HTTP） | `{4, 4, 0}` | p0-sink 212、Chatwork sink 213（各本文一致） |
| `[]` | **192** | `R11-none.pin.json` | [0,1] / [0,1] / [0,1] / [0,1] | なし。`Merge Notification Results` / `Check Notification Results` も未実行、最終ノード `Check Chatwork Enabled` | — | 受信なし |
| `["line","chatwork"]` | **206** | `drive.pin.json` | [0,1] / [0,1] / [1,0] / [1,0] | `Notify LINE` [1,0]、`Notify Chatwork` [1,0] | `{2, 2, 0}` | p0-sink 207、Chatwork sink 208 |

- **期待（CASES R11）**：設定したチャネルの IF だけ true；`[]` では Notify も Merge / Check も未実行；出力キー 5 種；LINE は `line_text`、Chatwork は `chatwork_text`
- **判定**：**PASS**（pinned; Slack / Gmail delivery pending H2）。監査指摘の `["line"]` / `["chatwork"]` 単独実行を含め 6 通りすべて個別の実行 ID を持つ

## fix-4 R11-b 一部失敗 → 成功・`failed 1`／全滅 → throw

- **複製**：`7iZwuEN7GUeToE8H`　**pin**：`tests/pins/notify-partial-fail.pin.json`（Chatwork = `http://127.0.0.1:9`）、`tests/pins/notify-all-fail.pin.json`（LINE / Chatwork とも到達不能）
- **観測（一部失敗、実行 193、success）**：`Notify LINE` [1,0]（p0-sink 194 受信）、`Notify Chatwork` [0,1]（error 出力 `error: {message "connect ECONNREFUSED 127.0.0.1:9", name "Error", stack …}`）→ `Merge` [2] → `Check Notification Results` `{channels_attempted 2, channels_ok 1, channels_failed 1, errors ["connect ECONNREFUSED 127.0.0.1:9"]}`
- **観測（全滅、実行 195、error）**：`Notify LINE` [0,1]、`Notify Chatwork` [0,1] → `Merge` [2] → `Check Notification Results` が throw `All notification channels failed (2): connect ECONNREFUSED 127.0.0.1:9 / connect ECONNREFUSED 127.0.0.1:9 [line 56]`、`status error`、最終ノード `Check Notification Results`。Error Workflow 複製 `ZzZMfALj5IzDn4wL` の実行 0 件（手動実行では Error Trigger は発火しない。起動自体は R21-c 172 → 173 で確認済み）
- **期待（CASES R11-b / DESIGN D17）**：一部失敗は実行成功、全滅は throw
- **判定**：**PASS**

## fix-5 R11-c（新規、D34）無効化した Notify ノードの素通りを失敗に数える

- **区分**：PIN。CASES には無い副ケース。作業ツリーで変わった `Check Notification Results` の新ロジック（DESIGN D34、A38：無効化ノードは入力をそのまま通す）を n8n 上で初めて実行したもの
- **複製**：`SrdBBEoGnI15qIo2`（作業ツリーの `workflow.json` から作成し、`Notify Email` だけ `disabled: true`。実行 JSON の `workflowData` で確認）　**pin**：`tests/pins/R11-c-passthrough-email-line.pin.json`（`["email","line"]`）、`R11-c-passthrough-email.pin.json`（`["email"]`）。`Notify Email` は pin しない（無効化ノードとして素通りさせる）
- **観測（実行 196、success）**：`Check Email Enabled` [1,0]、`Check LINE Enabled` [1,0]；`Notify Email` は runData に [1,0]（`executionStatus success`、出力 = 入力そのまま：キー `title / body_text / slack_blocks / line_text / chatwork_text`、`error` 無し、応答マーカー無し）；`Notify LINE` [1,0]（出力 `{message: "Workflow was started"}`、p0-sink 197 受信）→ `Merge` [2] → `Check Notification Results` **`{channels_attempted 2, channels_ok 1, channels_failed 1, errors ["notify node disabled or not executed (payload passed through)"]}`**
- **観測（実行 198、error）**：`["email"]` のみ → `Merge` [1]（素通りペイロードだけ）→ throw **`All notification channels failed (1): notify node disabled or not executed (payload passed through) [line 56]`**。`verify.py` で HEAD 版の判定（`json.error` の有無だけ）を同じ Merge 出力に当てると「失敗 0 → 成功」になる（= D34 が直した無通知の見逃し）
- **期待（DESIGN D34 / `tests/unit` C-4・C-5、`pass_through_one_ok` / `pass_through_only_throws`）**：素通りは失敗に数え、他に成功があれば実行成功、素通りだけなら throw
- **判定**：**PASS**

## 補助実行（判定には使わない）

- **179 / 181 / 183 / 187 / 190**：最初の一巡。Chatwork シンクの URL を `http://localhost:5678/webhook/p3-fix`（`webhookId` のみ）にしていたため `Notify Chatwork` が 404（`The requested webhook "POST p3-fix/rooms/fix/messages" is not registered`）。179 / 181 / 183 / 190 は LINE 成功・Chatwork 失敗の「一部失敗」で success、187（`["chatwork"]` 単独）は全滅で error。動的パス付き Webhook の URL は `/webhook/<webhookId>/<path>` という README の注記どおりで、`http://localhost:5678/webhook/p3-fix/p3-fix` に直して 200 / 203 / 206 / 214 / 211 で置換。製品の欠陥ではない（p0-sink 180 / 182 / 184 / 191 は受信済み）
- **209**：`["chatwork"]` を誤って `Notify Email` 無効化複製 `SrdBBEoGnI15qIo2` で実行したもの（結果は 214 と同一：Chatwork のみ実行、`{1,1,0}`、シンク 210 受信）。通常複製での 214 で置換
- **199**：Chatwork シンクへの疎通 probe（`roomId probe`）

## オーケストレーターへの申し送り / For the orchestrator

1. **製品ファイルの採否**：作業ツリーの `workflow.json` / `error-handler.json` / `code/check_notification_results.js` / `build/build_workflow.py` / `tests/unit/*`（並行エージェント p3f による D34 変更）は本作業では触れていない。accept する場合、本書の再実行で R11 / R11-b / R11-c / フルパス / R09 が作業ツリー版で PASS しており、`build_workflow.py --check` も OK。revert する場合は g1〜g3 の HEAD 版証拠がそのまま有効で、fix-5（R11-c）だけが該当しなくなる（HEAD 版では 198 相当が success になる = 無通知の見逃し）。
2. **監査の「存在しない参照」は解消済み**：`P3 finding F2` は `tests/SMOKE-p3-followup.md`（p3f、09:13 UTC）の F2、D34 は DESIGN.md §2.2 / §8、A35〜A38 は ASSUMPTIONS.md に存在する。本作業の R11-c（196 / 198）は p3f の 176 / 178（別複製 `jrlJtOg97BAJBHGb`、同じ pin 構成）と同じ結果で、独立に再現した。
3. **並行編集**：本作業中（09:11〜09:13 UTC）に `DESIGN.md` / `ASSUMPTIONS.md` が別エージェントに更新されていたため、本作業の編集は `tests/RESULTS.md`、`tests/results/`、`tests/pins/`（新規 4 本＋README 追記）、`PROGRESS.md` の 1 行に限定した。
4. n8n の残存物：`[P2 smoke] Collect Transactions + Normalize Payer`（`9N4xqof1hoAYsMZV`）と `[EXP] runtime probe`（`KRsP0xVLaqYwpOdw`）は P2 以前のもので監査の指摘対象ではないため削除していない。P3 各グループ・p3f・本作業の複製・シンク・Credential は残っていない（ワークフロー一覧は製品 2 本＋P0 2 本＋上記 2 本、`/rest/credentials` は空）。
