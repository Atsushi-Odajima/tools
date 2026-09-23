# テンプレ01 P3 テスト結果 / Template 01 — P3 test results (RESULTS.md)

`CLAUDE.md` §6 P3 ゲート（CASES を全て実行し実行 ID／入出力／合否を記録、2 回連続実行で状態不変）と §7 DoD（`tests/CASES.md` 全 PASS、`RESULTS.md` に証拠）のための唯一の証拠ファイル。各ケースの入出力全文は付録の担当グループ別ファイル（`tests/results/`）にあり、本書はそれを集約・再確認したもの。

| 項目 | 値 |
|---|---|
| 実行日 | 2026-09-23 |
| 対象 | `workflow.json`（`[Odaji] 01 Bank Deposit Reconciliation v1.0.0`、36 ノード）＋ `error-handler.json`（`[Odaji] 01 Error Handler v1.0.0`、14 ノード）。g1〜g3 は P2 終了時点（git HEAD `93a0975`）の内容を実行した。**P3 の 3 グループは製品ファイルを変更していない**が、本書の初版確定（09:02 UTC）後に別エージェント（p3f）が `code/check_notification_results.js` / `workflow.json` / `error-handler.json` / `build/build_workflow.py` / `tests/unit/*` を D34（無効化した Notify ノードの素通りを失敗に数える）で更新した。その作業ツリー版は **fix グループが再実行**した（下の「検証した版」行、§0、付録 `results/fix.md`） |
| 検証した版 | **g1 / g2 / g3**：git HEAD `93a0975ff096824af51151b32f93b2b42239842f` の `workflow.json` / `error-handler.json`（保存済み全実行 JSON の `workflowData` が HEAD の 7 Code ノード（Parse Bank CSV / Parse Mail / Collect Transactions / Normalize Payer / Match Invoices / Build Notification / Check Notification Results）と Build Error Message の jsCode に一致。`Check Notification Results` jsCode md5 = `e1da220f27…`）。**fix**：作業ツリー版（`workflow.json` sha256 `19d84ba99fc047c2e40888ac46f55ec83fd212164f3733de07998fb618f63fc1`、`error-handler.json` sha256 `f4c884aa958b52bd7d8a1a183c2a830fdfb82cc014c833f883a613113c954112`。jsCode md5：Parse Bank CSV `83c68d9b29…` / Parse Mail `9a6b9f2404…` / Collect Transactions `6da42b8747…` / Normalize Payer `7742d5abcc…` / Match Invoices `6ecfe309d3…` / Build Notification `8633097a78…` / **Check Notification Results `69be2a4c36…`** / Build Error Message `999a206481…`。HEAD との差は `Check Notification Results` と付箋 3 枚の高さのみ。`build/build_workflow.py --check` → `OK (unchanged)`）。fix の保存済み 19 実行の `workflowData` はすべてこの md5 に一致 |
| 環境 | ローカル n8n **2.40.5**（`http://localhost:5678`、SQLite、`Asia/Tokyo`、Node 24。BLOCKERS H8 のとおり npm 起動） |
| ケース定義 | `tests/CASES.md`（P1 版）§1 の R01〜R23、§2 の期待値、§3 の通知全文 |
| 実行体制 | 3 グループが並列に実行。各グループは製品ワークフローの登録本体（`EMlrzFHwUpu7xvZx` / `S9vwW2D7jBCIvCQn`）には触れず、`workflow.json` / `error-handler.json` から `POST /api/v1/workflows` で**自分の複製**を作って実行し、終了時に複製・シンク・ダミー Credential をすべて削除した（下表） |
| 判定方法 | 各ケースの CASES §2 の期待値を、`GET /api/v1/executions/{id}?includeData=true` で取得した実行 JSON の各ノード出力（`Parse Bank CSV` / `Parse Mail` / `Normalize Payer` / `Match Invoices` / `Route Match Results` / `Build Notification` / `Check Notification Results` 等）と照合。通知の実到達はローカルの受信 Webhook（LINE → `p0-sink`、Chatwork → 各グループ自作のシンク）で確認 |
| 集約時の再確認 | 本書の作成時に、保存済み実行 JSON（92 / 95 / 96 / 101 / 104 / 107 / 108 / 111 / 114 / 115 / 118 / 121 / 124 / 125 / 126 / 129 / 130 / 133 / 136 / 139 / 140 / 142 / 146 / 149 / 150 / 151 / 154〜158 / 161 / 164 / 167 / 168 / 172 / 173）から、通知全文・冪等性・実行順・R11 ルーティング・R21 文面・各 summary をスクリプト（作業領域 `p3-scratch/results-md/verify.py`）で再抽出し、グループ報告と一致することを確認した。作業中断（5 時間制限）後の再開時に同じスクリプトを再実行し、結果が変わらないことを再確認した。**監査後（fix、09:16〜09:18 UTC）**：作業ツリー版の複製で R11 全 6 通り（`["line"]` 185 / `["chatwork"]` 214 を新規に含む）＋ `["line","chatwork"]` 206、R11-b 193 / 195、フルパス 200（CASES §3 全文一致）と R09 2 回目 203、D34 素通り 196 / 198 を再実行し、`p3-scratch/fix/verify.py` の 59 判定すべて PASS |
| 実行 JSON の保存先 | 作業領域（リポジトリ外）`<scratchpad>/p3-scratch/<group>/exec-<id>.json` と `sink-exec-<id>.json`（fix は `p3-scratch/fix/`）。**複製ワークフローの実行は n8n 上から消えている（2026-09-23 09:20 UTC、n8n 稼働中に `GET /api/v1/executions` で確認：87〜173 のうち複製のものは無く、fix の 179〜214 も削除後 404）。** 現存するのは p0-sink（`VDtPVF2gV4fnId1X`）の実行 90 / 93 / 97 / 98 / 102 / 105 / 109 / 112 / 116 / 119 / 122 / 127 / 131 / 134 / 137 / 141 / 145 / 147 / 152 / 159 / 162 / 165 / 171 / 174（＋p3f 177、fix 180 / 182 / 184 / 186 / 191 / 194 / 197 / 201 / 204 / 207 / 212）で、保存済み `sink-exec-<id>.json` 29 件すべてと JSON として同一。**保存済み exec-<id>.json が証拠の原本**であり、全 113 ファイルの SHA-256 を `tests/results/evidence-sha256.md` に記録した |

### 複製ワークフローと後片付け / Copies used and cleanup

| グループ | 本体複製 | Error Workflow 複製 | Chatwork シンク | ダミー Header Auth（LINE / Chatwork） | その他 | 状態 |
|---|---|---|---|---|---|---|
| g1-drive | `6Y99TvLuHXtWgPXs` | `3acOl4yifpnXTVzw` | `ygfRR4YUXBptN6hK` | `c8agMqYZnQv3GZ3M` / `1zwAokCYaGHyMSdY` | — | 全削除 |
| g2-gmail-notify | `f7eKdb3gMdu91n9h` | `5th1GIVLYBd23Ds9` | `faxFLoRCvBA27Npy` | `eed6hX7Tyi5mauAs` / `weLpAyNTCC6Itj52` | — | 全削除 |
| g3-schedule-error | `m3C9NLhdSCUbSQEe` | `H8dkT8fJ4oOAJcqG` | `BktwWtxQHItWC1NB` | `aAybXoTbiQ66w55s` / `0h1Jyw27kF5coNNJ` | 使い捨て `zrFdEKFsbuBJAnmK`（R21 用） | 全削除 |
| fix（監査後の再実行、作業ツリー版） | `7iZwuEN7GUeToE8H` | `ZzZMfALj5IzDn4wL` | `RCP5XmAH8kHhv4rC` | `6rXur3JBdtzQlzBu` / `TA42bSPDjCtxxdcg` | 本体複製 `SrdBBEoGnI15qIo2`（`Notify Email` を disabled にした R11-c 用） | 全削除（`GET` → 404、`/rest/credentials` → 空を確認） |

各本体複製の `settings.errorWorkflow` は同グループの Error Workflow 複製 ID に設定した。LINE の受信先は P0 の共用シンク `p0-sink`（`VDtPVF2gV4fnId1X`、削除していない）。

---

## 0. 結論と要注意事項 / Verdict and call-outs

- **FAIL：0 件。製品側の欠陥は見つからなかった。** CASES §1 の R01〜R23 のうち **22 ケース PASS**、R12 は CASES の定義どおり **N/A**（実行なし）。
- PASS のうち Google ノード（`Watch Drive Folder` / `Download File` / `Watch Gmail Inbox` / `Read Invoices` / `Read Transactions` / `Update Invoices` / `Upsert Transactions`）を pinned にして通したケースは **「PASS（pinned; ライブ未検証）」** であり、実セル値・シート差分ゼロ・実ポーリングは BLOCKERS **H1** 待ち。Slack / Gmail 送信の実到達は **H2**、LINE / Chatwork の実到達は **H6 / H7** 待ち（ローカルシンクで代替）。
- **未実行・部分実行の項目（オーケストレーターの判断が必要）**：
  1. ~~**R11 の `["line"]` 単独・`["chatwork"]` 単独**：別々の実行としては未実行~~ → **解消（fix）**：`["line"]` = 実行 185（`Notify LINE` のみ、p0-sink 186）、`["chatwork"]` = 実行 214（`Notify Chatwork` のみ、シンク 215）。他 4 通りも作業ツリー版で再実行（188 / 189 / 211 / 192）。初版では `["line","chatwork"]`（121）で両 IF と両シンクを同時に確認していた。
  1-b. **製品ファイルの P3 後の変更（監査 blocker）**：本書初版の確定後に p3f が D34（`Check Notification Results` の素通り検知）を作業ツリーに入れた。fix グループが作業ツリー版で R11 / R11-b / フルパス / R09 2 回目 / D34 素通り（R11-c）を再実行し全 PASS（付録 `results/fix.md`）。**作業ツリー版を採用するか HEAD に戻すかはオーケストレーターの判断**（採用なら本書の R11 行と fix.md がその版の証拠。戻すなら g1〜g3 の証拠がそのまま有効で、R11-c だけ該当しなくなる）。監査時に実在しないとされた参照は p3f が解消済み：`P3 finding F2` は `tests/SMOKE-p3-followup.md`（F1 / F2 の定義、p3f 自身の実機確認 176 / 178）、D34 は DESIGN.md、A35〜A38 は ASSUMPTIONS.md にある。fix の 196 / 198 は p3f の 176 / 178 を別複製で独立に再現したもの。
  2. **R11-b「全滅 → `error-handler` が起動する」の後半**：本体複製の手動実行では Error Trigger が発火しない（n8n 公式仕様）ため、実行 142 は「`Check Notification Results` が throw して実行失敗」までを確認。Error Workflow の起動自体は R21-c（使い捨てワークフローの本番実行 172 → Error Workflow 実行 173）で確認した。本体そのものの失敗から `error-handler` が起動する経路は本番実行（有効化 + 実 Credential）でしか確認できず、**未実行**。
  3. **R21「LIVE-G の本命」（本体を有効化し `SHEET_ID` を壊して `Read Invoices` で失敗させる）**：H1 待ちで**未実行**。
  4. **R09 / R10-idempotent / R19-b の「シート差分ゼロ」**：pinned の範囲では「2 回目に書込みアイテムが 1 つも生成されず書込みノードが実行されない」ことで成立。実シートの diff は H1 待ち。
  5. **R14 LIVE-G（見出し行だけの実シート）、R22 注意（OFF でもトリガーのポーリングが続く）**：H1 待ちで未実行。
- **文言の差（仕様書側の修正候補、実装は変更不要）**：
  - CASES R17 の期待 `・no_parser_matched  会議のご案内`（空白 2 つ）に対し、実装は `・no_parser_matched 会議のご案内`（空白 1 つ。`build_notification.js` の `join(' ')`）。
  - CASES R21 の期待タイトル `【n8n エラー】[P3] Throw for error-handler` は使い捨てワークフロー名に依存する。実際は `[P3-g3-schedule-error] Throw for error-handler` という名前で作ったため、タイトルは `【n8n エラー】[P3-g3-schedule-error] Throw for error-handler`。`エラー：` の値は Code ノードが付ける ` [line 1]` 付き。起動は Schedule 毎分ではなく Webhook の本番実行で代替した。
- **n8n 2.40.5 の所見（SETUP / DESIGN §2.2 に反映が必要。詳細は §6）**：(1) Error Workflow は**自身が有効化（Active）されていないと呼ばれない**、(2) 有効化時に接続済み・有効な全ノードの Credential が検証されるため、`Notify Slack` / `Notify Email` に Credential を割り当てるかノードを無効化しないと `error-handler` も本体も有効化できない。

---

## 1. pinned data の仕組みと、pinned にしたノード / How pins work and which nodes were pinned

- 方法（ASSUMPTIONS A5 / A11、`tests/pins/README.md`）：pinned data は**ワークフローに保存**する（`PATCH /rest/workflows/{id}` の `pinData`。実行ボディ内だけの pinData は無視される）。その後 `POST /rest/workflows/{id}/run` に `triggerToStartFrom: { name: "<トリガー名>" }` を付けて手動実行する。pinned にしたノードは実行されず、保存した pinned data がそのまま出力になる。バイナリ（base64 の `binary.data.data`）も保存済み pinData から読める（A11、A22）。各実行の前後に `pinData` を `{}` に戻した。
- 本体ワークフローで pinned にしたノード（＝**ライブ未検証**、BLOCKERS H1）：
  - トリガー：`Watch Drive Folder`（Drive 経路）、`Watch Gmail Inbox`（Gmail 経路）、`Run Daily Rematch`（Schedule 経路）。実発火・実ポーリング・Simplify OFF の実出力形状は未検証。
  - Google Drive：`Download File`（fixture CSV の base64 バイナリ）。実ダウンロードは未検証。
  - Google Sheets 読取：`Read Invoices`（`fixtures/invoices.seed.csv` 20 行、ケースにより行追加）、`Read Transactions`（`[{}]` = 空シート、または `transactions.seed.csv` ＋ 前回実行の `txn_row`）。
  - Google Sheets 書込：`Update Invoices` / `Upsert Transactions`（`[{ok:true}]`）。**判定はこれらのノードに入力されたアイテム**（`Route Match Results` の出力 0 / 1）で行った。実セル値、`Append or Update` の一致キー動作、未指定列が上書きされないことは未検証。
  - `Config`（Set）：ケースごとの値を pin（`NOTIFY_CHANNELS: ["line","chatwork"]`、`LINE_API_URL` = `p0-sink`、`CHATWORK_API_BASE_URL` = 各グループのシンク、ダミーの `LINE_TO_USER_ID` / `CHATWORK_ROOM_ID` / `SHEET_ID`）。Set ノード自体の実動作は P2 の `*-realconfig` スモーク（`tests/SMOKE.md` 実行 60 / 73）で確認済み。
  - 通知：`Notify Slack` / `Notify Email` は R11 の該当ケースでのみ pinned（`[{ok:true}]`、BLOCKERS H2）。`Notify LINE` / `Notify Chatwork` は pinned にせず、ダミーの Header Auth Credential（A28）を複製にだけ割り当てて**実際に HTTP を送り**、ローカルシンクで受信を確認した（実サービスへの到達は H6 / H7）。
- Error Workflow：R21-a / R21-b では `Catch Workflow Error`（Error Trigger）と `Config` を pinned。R21-c は pinned を使わず、使い捨てワークフローの本番実行（`mode: webhook`）の失敗から Error Workflow 複製を実際に起動させた（`mode: error`）。
- 実行ノード：`Route by Source` / `Check File Is CSV` / `Parse Bank CSV` / `Parse Mail` / `Collect Transactions` / `Normalize Payer` / `Match Invoices` / `Route Match Results` / `Build Notification` / `Check … Enabled` ×4 / `Notify LINE` / `Notify Chatwork` / `Merge Notification Results` / `Check Notification Results` / `Skip Non-CSV File` / `Skip Disabled Trigger` / `Build Error Message` は全ケースで実際に実行された。

---

## 2. ケース一覧 / Summary table (R01–R23)

区分は CASES §0.1（PIN / LIVE-G / LIVE-N）。実行 ID はローカル n8n のもの（各グループの複製ワークフロー上）。「担当」は付録の詳細ファイル。

| ID | 内容 | 区分 | 実行 ID | 判定 | 証拠（要点） | 担当 |
|---|---|---|---|---|---|---|
| R01 | 名義・金額一致 → `auto`, `paid` | PIN（実セルは LIVE-G） | 92（A）、101 / 130（B） | **PASS**（pinned; live write pending H1） | `invoice_update` INV-2026-001 paid/auto/33000/2026-09-01/`2026-09-01\|33000\|サンプルシヨウジ\|`、INV-003 paid/auto/9800、INV-012 paid/auto/27500。`txn_row` は `source bank_csv, status matched, suggested ""`。INV-017 は変更なし。`Route Match Results` [8, 11, 1]。B：INV-013/014/015/016 paid/auto。通知 `■ 自動消込` に `・2026-09-01 振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ ¥33,000 → INV-2026-001` | g1 / g2 |
| R02 | 金額のみ一致・候補 1 → `amount_only` | PIN | 92 | **PASS** | INV-2026-004 paid/amount_only/128000/2026-09-04；txn matched；通知 `■ 要確認` に `…¥128,000 → INV-2026-004 （金額のみ一致・要確認）`；summary `b` に計上（b=3） | g1 |
| R03 | 手数料 220 差引 → `fee_deducted` | PIN | 92 | **PASS** | INV-2026-002 paid/fee_deducted/paid_amount 54780/fee_deducted 220、`payer_name_norm テストコウギヨウ`；通知 `（手数料 ¥220 差引）` | g1 |
| R04 | 2 請求の合算 → `combined` | PIN | 92 | **PASS** | INV-2026-005 paid 700000 ＋ INV-2026-006 paid 534567、両方 `combined`・同じ `matched_txn_ids`；`txn_row` は 1 行で `matched_invoice_ids "INV-2026-005,INV-2026-006"`；通知 `（合算）` | g1 |
| R05 | 一部入金 → `partial` | PIN | 92 | **PASS** | INV-2026-007 partial/auto/paid_amount 100000；通知 `■ 自動消込` に `（一部入金・残 ¥150,000）`；summary `a` に計上（a=4） | g1 |
| R06 | 同額請求 2 件・名義不一致 → `ambiguous` | PIN | 92 | **PASS** | INV-008/009 は `invoice_update` に無し；txn `status ambiguous, suggested_invoice_ids "INV-2026-008,INV-2026-009"`；通知 `■ 候補複数` に `候補: INV-2026-008(¥44,000), INV-2026-009(¥44,000)` | g1 |
| R07 | 出金行 → 無視 | PIN | 92（A）、101（B） | **PASS** | A：`Parse Bank CSV` 12 件 = txn 11 ＋ `file_stats {ignored_withdraw: 4, rows_total: 15}`、`_row` に 3/8/11/16 無し；B：txn 5 ＋ `ignored_withdraw: 3`。summary も同値 | g1 |
| R08 | Shift_JIS／UTF-8 BOM → 文字化けなし | PIN | 92（A）、101（B） | **PASS** | A（cp932）：`payer_name_raw` / `payer_name_norm` / `txn_id` 11 件が `fixtures/README.md` §4 と一致、U+FFFD なし；B（EF BB BF）：`取引日` が見つかり raw が §5 と一致、`yyyyMMdd → yyyy-MM-dd`、U+FEFF なし；`workflow.json` に `extractFromFile` 無し（`TextDecoder` 経路、A6） | g1 |
| R09 | 同一 CSV を 2 回投入 → 全件 skip | PIN（差分ゼロは LIVE-G） | 92 → 95 | **PASS**（pinned; sheet diff pending H1） | 2 回目：`Match Invoices` は summary 1 件のみ `{n:0, a:0, b:0, c:0, skipped_existing:11, skipped_duplicate_in_batch:0, ignored_withdraw:4}`、`Route Match Results` [0, 0, 1]、`Update Invoices` / `Upsert Transactions` 未実行、タイトル `【入金消込 2026-09-23】新規の入金はありませんでした`、本文 `（処理済みのため skip：11 件）`。§3 参照 | g1 |
| R10 | Gmail 通知 → 抽出値一致、`auto` | PIN（実ポーリングは LIVE-G） | 96 | **PASS**（pinned; live Gmail polling / sheet write pending H1） | `Parse Mail`：X `104500 / カ)ダミーデンキ / 2026-09-17`（bankX）、Y `19800 / ササキ ハナコ / 2026-09-18`（bankY、本文日付）；INV-2026-018 / 019 paid/auto、`matched_txn_ids` が CASES と一致；`txn_row` 2 行 `source gmail, status matched`；タイトル `処理 2件｜自動消込 2｜要確認 0｜未消込 0`；経路 `Route by Source [0,2,0,0] → Parse Mail → Collect Transactions` | g2 |
| R09-b（R10-idempotent） | 同じ 2 通を 2 回投入 | PIN（差分ゼロは LIVE-G） | 115、118 | **PASS**（pinned; sheet diff pending H1） | `skipped_existing 2`、`invoice_update` 0、`txn_row` 0、書込みノード未実行、`（処理済みのため skip：2 件）`；115 と 118 は全ノード出力が同一。§3 参照 | g2 |
| R11 | 全チャネル通知 → 設定分のみ | PIN（ルーティング）＋ LIVE-N（到達） | HEAD 版（g2）：121、124、125、126、129；R11-b：140、142。**作業ツリー版（fix）：`["line"]` 185、`["chatwork"]` 214、`["slack"]` 188、`["email"]` 189、4 チャネル 211、`[]` 192、`["line","chatwork"]` 206；R11-b：193、195；R11-c（D34 素通り）：196、198** | **PASS**（pinned; Slack / Gmail delivery pending H2。6 通りすべて個別実行済み） | `["line","chatwork"]` 121 / 206：IF [0,1]/[0,1]/[1,0]/[1,0]、`Notify LINE` / `Notify Chatwork` 実行、両シンク受信（LINE `messages[0].text` == `line_text`、Chatwork `body` == `chatwork_text`）、`{attempted 2, ok 2}`；`["line"]` 185：IF [0,1]/[0,1]/[1,0]/[0,1]、`Notify LINE` のみ、p0-sink 186 受信、Chatwork 受信なし、`{1, 1, 0}`；`["chatwork"]` 214：IF [0,1]/[0,1]/[0,1]/[1,0]、`Notify Chatwork` のみ、シンク 215 受信、LINE 受信なし、`{1, 1, 0}`；`["slack"]` 124 / 188、`["email"]` 125 / 189：pinned の Notify 1 つだけ到達、`{attempted 1, ok 1}`；4 チャネル 126 / 211：`{attempted 4, ok 4}`；`[]` 129 / 192：4 IF すべて false、Notify / Merge / Check 未実行、最終ノード `Check Chatwork Enabled`、status success。`Build Notification` の出力キー `title / body_text / slack_blocks / line_text / chatwork_text`。R11-b：一部失敗 140 / 193 = success `{attempted 2, ok 1, failed 1, errors ["connect ECONNREFUSED 127.0.0.1:9"]}`；全滅 142 / 195 = status error、`All notification channels failed (2): …`。R11-c（作業ツリー版のみ）：`Notify Email` を disabled にした複製で `["email","line"]` 196 = success `{2, 1, 1, errors ["notify node disabled or not executed (payload passed through)"]}`、`["email"]` 198 = error `All notification channels failed (1): notify node disabled …` | g2 / fix |
| R12 | 入金と出金が同一行 | — | — | **N/A** | CASES T11 のとおり銀行 CSV に該当行が無く、`parse_bank_csv.js` は `deposit_col` だけで判定（記録のみ） | g3 |
| R13 | bank_B（BOM + yyyyMMdd + 先頭番号 + ひらがな） | PIN | 130（同結果：101） | **PASS**（pinned; live write pending H1） | 5 txn、`payer_name_norm` = ダミーカコウ / スズキイチロウ / ミホンプランニング / タカハシミキ / ワタナベケン；INV-013/014/015/016 paid/auto；`2026-09-22\|7700\|ワタナベケン\|` unmatched・suggested ""；summary `n=5 a=4 b=0 c=1 ignored_withdraw=3`；通知 `■ 未消込` 1 行 ＋ `■ 自動消込` 4 行 | g2 / g1 |
| R14 | 空シート（Always Output Data） | PIN | 92（a）、108（b） | **PASS** | a：`Read Transactions = [{}]` → `existing []`、`skipped_existing 0`、結果は R01〜R06 と同一；b：両方 `[{}]` → 11 件 unmatched・suggested ""、`invoice_update` 0、`c=11`、`Route Match Results` [0, 11, 1]、`■ 未消込` 11 行、最終ノードまで到達 | g1 |
| R15 | `skip_rows=1` | PIN | 104（=1）、107（=0） | **PASS** | =1：`txn_id` 11 件が A と完全一致、`_row` が A の各値 +1（[3,5,6,7,8,10,11,13,14,15,16]）、`ignored_withdraw 4`；=0：`Parse Bank CSV` で失敗 `CSV column not found: "日付". header = サンプル銀行 入出金明細 …`、後段未実行 | g1 |
| R16 | 非 CSV ファイル → NoOp | PIN | 114 | **PASS** | `Check File Is CSV` [0, 1] → `Skip Non-CSV File`；`Download File` 以降は runData に無し；status success、通知なし | g1 |
| R17 | パーサ不一致メール → warning | PIN | 133 | **PASS**（表記差あり、§0） | `Parse Mail`：`{_kind: warning, type: no_parser_matched}`、`{type: parser_no_capture, parser: bankX}`；`txns []`、summary `n=0`、書込みなし；タイトル `新規の入金はありませんでした`、本文 `■ 警告\n・no_parser_matched 会議のご案内\n・parser_no_capture bankX 【サンプル銀行】ご入金のお知らせ` | g2 |
| R18 | Schedule 再突合で matched | PIN（実セルは LIVE-G） | 151（前提の bank_A：146） | **PASS**（pinned; live write pending H1） | `Update Invoices` 入力 = `{INV-2026-021, paid, 66000, 2026-09-11, matched_txn_ids 2026-09-11\|66000\|ミホンシヨウカイ\|, auto}` 1 件；`Upsert Transactions` 入力 = その txn 1 行のみ（`matched, INV-2026-021, suggested "", imported_at 2026-09-23T16:24:12+09:00` を保持）；summary `rematched 1, n 0`；タイトル `処理 0件｜自動消込 0｜要確認 0｜未消込 0`（A27）＋ `■ 自動消込 ・2026-09-11 振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ ¥66,000 → INV-2026-021`；両シンク受信 | g3 |
| R19 | Schedule で変化なし → 通知なし | PIN | 149（R19-b：150） | **PASS** | 実行ノードは 10 個のみ；`Match Invoices` = summary `{rematched 0, n 0, warnings []}`；`Route Match Results` [0, 0, 1]；`Build Notification` 出力 `[]`；`Check … Enabled` 以降・書込みノード未実行；シンク受信なし。§3 参照 | g3 |
| R20 | `NOTIFY_MAX_LINES=2` → `…他 N 件` | PIN | 111 | **PASS** | `■ 要確認` 2 行＋`…他 1 件`、`■ 候補複数` 1 行、`■ 未消込` 2 行＋`…他 1 件`、`■ 自動消込` 2 行＋`…他 2 件`；`slack_blocks` の各 text 長 [42, 161, 109, 146, 111]（< 3,000） | g1 |
| R21 | Error Workflow が起動する | PIN 相当（pinned 2 形状）＋ 本番実行／通知は LIVE-N | 161（execution error 形状）、164（trigger error 形状）、172 → 173（本番実行） | **PASS**（Slack / Gmail は H2；LIVE-G 本命は未実行、§0） | 173：`mode: error`、`Catch Workflow Error` に実行 172 の `{execution: {id, url, error, lastNodeExecuted}, workflow: {id, name}}`；`Build Error Message` title `【n8n エラー】[P3-g3-schedule-error] Throw for error-handler`、body に `失敗したノード：Throw P3 Error` / `エラー：P3 error-handler check [line 1]` / `実行ログ：http://localhost:5678/workflow/zrFdEKFsbuBJAnmK/executions/172`；LINE / Chatwork シンク 174 / 175 が同文を受信。161 / 164 は DESIGN §6.9 のフォールバック（`(not saved)` 等）を確認 | g3 |
| R22 | `TRIGGERS_ENABLED` OFF → `Skip Disabled Trigger` | PIN | 157（gmail=false）、158（R22-b）、156（R22-c）、155（drive=false）、154（schedule=false） | **PASS**（ポーリング継続の確認は H1） | OFF の 4 実行：`Route by Source` [0,0,0,n]（fallback）→ `Skip Disabled Trigger` のみ実行、`Parse Mail` 等未実行、success、通知・書込みなし；R22-b（gmail=true）158 は R10 と同一結果（INV-018/019 paid/auto） | g3 |
| R23 | 非 JPY の請求 → 警告 | PIN | 136（R23-b：139） | **PASS**（pinned; live write pending H1） | `Read Invoices` 21 件（USD 行）→ `invoice_update` 8 / `txn_row` 11 が bank_A 基準（121）と `imported_at` 以外一致、INV-2026-022 はどこにも出ない、A-5 は引き続き INV-004 `amount_only`；summary `warnings [{type: non_jpy_invoice, invoice_id: INV-2026-022, currency: USD}]`；本文末尾 `■ 警告\n・non_jpy_invoice INV-2026-022 USD`；R23-b 139：`Match Invoices` summary のみ → `Build Notification` `[]`、通知なし | g2 |

補助実行（ケース判定には使わない）：89（g1、Chatwork シンクの URL 誤りで `Notify Chatwork` 404、以後 92 で置換）、87（g2、Credential 無しの試走 → `Credentials not found`、A28 の確認）、144（g3、同じく URL 誤り）、167 / 168 / 169 / 170（g3、Error Workflow が有効化されていない／URL 誤りの先行試行。§6 の所見の根拠）。

---

## 3. 冪等性 / Idempotency (CLAUDE.md §6 P3, DESIGN §8.4)

三つの経路すべてで「同じ入力の 2 回目は書込みアイテムを生成せず、書込みノードが実行されない」ことを確認した。実シートの差分ゼロは H1 待ち。

### 3.1 R09 Drive：同一 CSV を 2 回投入（実行 92 → 95、g1）

| | 1 回目（92） | 2 回目（95） |
|---|---|---|
| `Read Transactions`（pinned） | `[{}]`（空シート） | `transactions.seed.csv` 1 行 ＋ 92 の `txn_row` 11 件（`imported_at` 以外完全一致を事前確認） |
| `Parse Bank CSV` | 12 件（txn 11 ＋ file_stats） | 12 件（同じ） |
| `Match Invoices` summary | `n 11, a 4, b 3, c 4, skipped_existing 0` | `n 0, a 0, b 0, c 0, skipped_existing 11, skipped_duplicate_in_batch 0, ignored_withdraw 4` |
| `Route Match Results` | [8, 11, 1] | [0, 0, 1] |
| `Update Invoices` / `Upsert Transactions` | 実行（入力 8 件 / 11 件） | **未実行**（runData に無し） |
| 通知 | §4 の全文 | `【入金消込 2026-09-23】新規の入金はありませんでした` ＋ `（処理済みのため skip：11 件）`（両シンク 97 / 99 受信） |

### 3.2 R09-b Gmail：同じ 2 通を 2 回投入し、さらに 2 回連続（実行 96 → 115 → 118、g2）

| | 1 回目（96） | 2 回目（115） | 3 回目（118） |
|---|---|---|---|
| `Read Transactions`（pinned） | `[{}]` | seed 1 行 ＋ 96 の `txn_row` 2 件 | 115 と同じ |
| `Match Invoices` | 5 件（update 2 ＋ txn 2 ＋ summary） | summary のみ `{n 0, skipped_existing 2}` | 同じ |
| `Route Match Results` | [2, 2, 1] | [0, 0, 1] | [0, 0, 1] |
| 書込みノード | 実行 | 未実行 | 未実行 |
| 通知 | `処理 2件｜自動消込 2…` | `新規の入金はありませんでした` ＋ `（処理済みのため skip：2 件）` | 同じ |
| 115 と 118 の比較 | — | ノード集合同一、全ノードの出力 JSON を機械比較して**差分 0**（集約時に再確認） | |

### 3.3 R19-b Schedule：変化のない状態で 2 回連続（実行 149 → 150、g3）

- 入力：bank_A 反映後の `invoices` 20 行（実行 146 の `invoice_update` 8 件を seed に適用）と `transactions` 12 行（seed ＋ 146 の 11 行）。
- 149 / 150 とも実行ノードは `Run Daily Rematch, Config, Route by Source [0,0,1,0], Collect Transactions, Read Invoices [20], Read Transactions [12], Normalize Payer, Match Invoices [1], Route Match Results [0,0,1], Build Notification [[]]` の 10 個のみ。`Match Invoices` = summary `{n 0, rematched 0, skipped_existing 0, warnings []}`、`invoice_update` 0、`txn_row` 0、`Build Notification` 出力 `[]`、以降未実行、シンク受信なし。
- 149 と 150 の全ノード出力 JSON を機械比較して**差分 0**（集約時に再確認）。

---

## 4. 実行順 / Execution order (DESIGN §8.4: Update Invoices → Upsert Transactions → Build Notification)

書込みが発生した全実行で、`runData` の順序と各ノードの `startTime`（ms）が `Update Invoices` → `Upsert Transactions` → `Build Notification` の順で単調増加した（集約時に保存済み JSON から再抽出）。`Route Match Results` の出力 0 → 1 → 2 の順に `executionOrder: v1` で実行され、通知は 2 つの書込みノードの後（D17）。pinned のため書込みノードの `executionTime` は 0 ms だが、順序自体はエンジンが決めるため本番でも同じ。

| 実行 | 経路 | `Update Invoices`（index, startTime） | `Upsert Transactions` | `Build Notification` |
|---|---|---|---|---|
| 92 | Drive bank_A（g1） | 12, 1790151381310 | 13, 1790151381318 | 14, 1790151381326 |
| 101 | Drive bank_B（g1） | 12, 1790151383661 | 13, 1790151383669 | 14, 1790151383676 |
| 104 | Drive skip_rows=1（g1） | 12, 1790151384593 | 13, 1790151384602 | 14, 1790151384618 |
| 108 | Drive R14-b（g1、`Update Invoices` は入力 0 件で未実行） | — | 12, 1790151386303 | 13, 1790151386311 |
| 111 | Drive R20（g1） | 12, 1790151387184 | 13, 1790151387193 | 14, 1790151387202 |
| 96 | Gmail R10（g2） | 10, 1790151382399 | 11, 1790151382422 | 12, 1790151382442 |
| 121 | Drive R11（g2） | 12, 1790151423632 | 13, 1790151423640 | 14, 1790151423650 |
| 130 | Drive R13（g2） | 12, 1790151436656 | 13, 1790151436665 | 14, 1790151436674 |
| 136 | Drive R23（g2） | 12, 1790151441800 | 13, 1790151441812 | 14, 1790151441824 |
| 146 | Drive bank_A（g3） | 12, 1790151955435 | 13, 1790151955444 | 14, 1790151955454 |
| 151 | Schedule R18（g3） | 9, 1790152031122 | 10, 1790152031131 | 11, 1790152031143 |
| 158 | Gmail R22-b（g3） | 10, 1790152043727 | 11, 1790152043735 | 12, 1790152043744 |

---

## 5. 観測した通知文面 / Notification texts observed

### 5.1 基準実行（bank_A を初期状態に流したとき）と CASES §3 の比較

実行 92（g1）の `Build Notification.body_text` は、**CASES §3 の全文と空行を含めて完全一致**した（日付は実行日 `2026-09-23`）。実行 121（g2）と 146（g3）の `body_text` も 92 と同一。`line_text` と `chatwork_text` は `body_text` と同一で、LINE シンク（`messages[0].text`）と Chatwork シンク（form の `body`）が同文を受信した。`slack_blocks` は header 1 ＋ section 4。

```
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
```

### 5.2 その他の観測文面と CASES との差

| ケース／実行 | 観測した文面 | CASES の期待との差 |
|---|---|---|
| R09（95） | `【入金消込 2026-09-23】新規の入金はありませんでした\n\n（処理済みのため skip：11 件）` | 一致 |
| R09-b（115 / 118） | 同上、`skip：2 件` | 一致 |
| R10（96）/ R22-b（158） | `【入金消込 2026-09-23】処理 2件｜自動消込 2｜要確認 0｜未消込 0\n\n■ 自動消込\n・2026-09-17 カ)ダミーデンキ ¥104,500 → INV-2026-018\n・2026-09-18 ササキ ハナコ ¥19,800 → INV-2026-019` | 一致 |
| R13（130 / 101） | `処理 5件｜自動消込 4｜要確認 0｜未消込 1`、`■ 未消込（該当請求なし）\n・2026-09-22 フリコミ ワタナベ ケン ¥7,700 → 候補: —`、`■ 自動消込` に `・2026-09-17 0123 カ)ダミーカコウ ¥41,800 → INV-2026-013` ほか計 4 行 | 一致 |
| R14-b（108） | `処理 11件｜自動消込 0｜要確認 0｜未消込 11`、`■ 未消込` 11 行（すべて `候補: —`） | 一致 |
| R17（133） | `【入金消込 2026-09-23】新規の入金はありませんでした\n\n■ 警告\n・no_parser_matched 会議のご案内\n・parser_no_capture bankX 【サンプル銀行】ご入金のお知らせ` | **表記差**：CASES は `・no_parser_matched  会議のご案内`（空白 2 つ）。実装は `[type, parser, subject, invoice_id, currency].filter(Boolean).join(' ')` で空白 1 つ。内容は同一。CASES 側の修正を提案 |
| R18（151） | `【入金消込 2026-09-23】処理 0件｜自動消込 0｜要確認 0｜未消込 0\n\n■ 自動消込\n・2026-09-11 振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ ¥66,000 → INV-2026-021` | 明細行は一致。タイトルの件数は CASES の注記どおり P2 の決定（A27：既存行の再突合は `rematched` にだけ数える）に従う |
| R20（111） | §2 の R20 行のとおり、各セクション 2 行＋`…他 N 件`（`messages.ja.json` `more_items`） | 一致 |
| R23（136） | 5.1 の全文の末尾に `\n\n■ 警告\n・non_jpy_invoice INV-2026-022 USD` | 一致 |
| R21-a（161、docs 例の execution error） | title `【n8n エラー】Example Workflow`、body `ワークフロー：Example Workflow\n失敗したノード：Node With Error\nエラー：Example Error Message\n実行ログ：https://n8n.example.com/execution/231\n\n実行ログで原因を確認し、修正後に再実行してください。シート書込みやメール送信が途中まで進んでいる可能性があるため、再実行前に台帳シートを確認してください。` | DESIGN §6.9 どおり |
| R21-b（164、trigger error 形状） | title `【n8n エラー】Example Trigger Workflow`、`失敗したノード：Watch Drive Folder`、`エラー：Poll failed: invalid_grant`、`実行ログ：(not saved)` | DESIGN §6.9 のフォールバックどおり |
| R21-c（173、本番実行） | title `【n8n エラー】[P3-g3-schedule-error] Throw for error-handler`、`失敗したノード：Throw P3 Error`、`エラー：P3 error-handler check [line 1]`、`実行ログ：http://localhost:5678/workflow/zrFdEKFsbuBJAnmK/executions/172` | CASES は `[P3] Throw for error-handler` という名前を想定（使い捨てワークフロー名の違いのみ）。`エラー：` に Code ノード由来の ` [line 1]` が付く |
| R11-b 全滅（142） | 実行エラー `All notification channels failed (2): connect ECONNREFUSED 127.0.0.1:9 / connect ECONNREFUSED 127.0.0.1:9`（`Check Notification Results`） | DESIGN D17 どおり |

---

## 6. 既知の制約・未検証事項 / Known limitations

1. **手動実行では Error Workflow が起動しない**（n8n 公式仕様、CASES R21 前提）。本体複製を失敗させた実行（107、142）で Error Workflow 複製の実行は生まれていない。Error Workflow の起動は使い捨てワークフローの本番実行（Webhook、172 → 173）で確認した。本体そのものの失敗（`Read Invoices` の失敗など）からの起動は本番実行が必要で、H1 待ち。
2. **n8n 2.40.5 では Error Workflow 自身が有効化（Active）されていないと呼ばれない**：実行 167 / 168 では Error Workflow の実行が生まれず、n8n ログに `Calling Error Workflow for "zrFdEKFsbuBJAnmK". Workflow "H8dkT8fJ4oOAJcqG" is not active and cannot be executed`（`workflow-execution.service.js` `loadErrorWorkflowData`）。`settings.errorWorkflow` の設定だけでは不十分。**DESIGN §2.2 と SETUP（P4）に「Error Workflow を有効化する」を追記する必要がある**（`error-handler.json` の変更は不要）。
3. **有効化時の Credential 検証**：`POST /api/v1/workflows/{id}/activate` は接続済み・有効な全ノードの Credential を要求し（`Cannot publish workflow: 2 nodes have configuration issues: Node "Notify Slack": Missing required credential: slackApi / Node "Notify Email": Missing required credential: gmailOAuth2`）、`disabled` なノードだけ除外する。R21-c では複製の `Notify Slack` / `Notify Email` を `disabled: true` にして有効化した。買い手は `NOTIFY_CHANNELS` で使わないチャネルの Notify ノードにも Credential を割り当てるか、ノードを無効化する必要がある（本体も同じ検証を受ける）。SETUP に手順を追記、または既定の設計（Slack / Email ノードを既定で disabled にする等）の変更はオーケストレーターの判断。
4. **ライブ未検証（BLOCKERS H1）**：Google ノードはすべて pinned。実セル値、`Append or Update` の一致キー動作と未指定列の非上書き、2 回実行後の実シート差分ゼロ、Drive の実アップロード／実ダウンロード、Gmail の実ポーリングと Simplify OFF の実出力形状、見出し行だけの実シート（R14）、OFF にしたトリガーのポーリング継続（R22）、Google 由来の実失敗からの Error Workflow 起動（R21 本命）。
5. **ライブ未検証（BLOCKERS H2 / H6 / H7）**：Slack（Block Kit）と Gmail 送信は pinned（`[{ok:true}]`）で、Notify ノードへの入力アイテムまでを確認。LINE / Chatwork は実際に HTTP を送ったが、宛先はローカルの受信 Webhook。
6. **Header Auth のダミー Credential が必要（A28）**：HTTP Request（Header Auth）は Credential 未設定だと `Credentials not found` で失敗する（実行 87）。テストでは複製にだけダミーを割り当てて終了後に削除した。販売物の JSON には credentials ブロックを置かない。
7. **Error Trigger の実出力**は docs 例より `execution.error` のキーが多い（`level / shouldReport / description / tags / name / lineNumber`）。`Build Error Message` が参照するキーはすべて存在し、DESIGN §3 / §6.9 の変更は不要（記録のみ）。
8. **試験環境の運用上の注意**：動的パス `rooms/:roomId/messages` を持つ Webhook v2 ノードは (path, method) がインスタンス内で一意で、URL は `/webhook/<webhookId>/<path>`。並列実行ではエージェントごとに path の接頭辞を分ける（`tests/pins/README.md` の注記）。製品の動作とは無関係。
9. **実行 JSON はリポジトリ外**：複製ワークフローの削除により n8n 上の実行は**消えている（確認済み。2026-09-23 09:20 UTC、`GET /api/v1/executions` に複製の実行は無く、fix の実行も削除後 404）**。p0-sink の実行（90〜174 の 24 件、p3f 177、fix 11 件）は現存し、保存済み `sink-exec-<id>.json` と JSON 同一。証拠の原本は作業領域の `p3-scratch/<group>/exec-<id>.json`（`fix/`・p3f を含む 113 ファイル）で、その SHA-256 を `tests/results/evidence-sha256.md` に残した。リポジトリに残る証拠は本書・付録の引用値・このハッシュ一覧。
10. **P3 後の製品変更（D34）は fix で再検証済み、採否は未決**：作業ツリーの `Check Notification Results` は無効化した Notify ノードの素通り（`json.error` 無し・応答マーカー無しのペイロード）を失敗に数える。fix の 196 / 198 で n8n 上の挙動を確認（HEAD 版なら 198 相当は「成功」と報告される = 無通知の見逃し）。`build/build_workflow.py --check` は作業ツリーで OK。revert / accept はオーケストレーターの判断（§0 1-b）。

---

## 7. 再現手順 / How to reproduce

前提：`tests/pins/README.md` の「実行手順」と `tests/SMOKE.md` の手順（ASSUMPTIONS A5 / A11 / A28）。

1. `workflow.json` と `error-handler.json` から `POST /api/v1/workflows` で複製を作る（`name` / `nodes` / `connections` / `settings`）。本体複製の `settings.errorWorkflow` に Error Workflow 複製の ID を入れる。製品の登録本体は使わない。
2. シンク：LINE は `p0-sink`（Webhook v2、POST、path `p0-sink`）。Chatwork は Webhook v2、POST、path `<prefix>/rooms/:roomId/messages`（`webhookId` を付ける）を作り有効化。URL は `http://localhost:5678/webhook/<webhookId>/<prefix>`（README の注記）。
3. ダミー Header Auth Credential を `POST /api/v1/credentials {name, type: "httpHeaderAuth", data: {name: "Authorization", value: "Bearer <任意のダミー値>"}}` で 2 つ作り、複製の `Notify LINE` / `Notify Chatwork` にだけ設定する（A28）。
4. pin を生成する（すべて決定的、`fixtures/` と `build/build_workflow.py` の既定値から）：
   - `PYTHONDONTWRITEBYTECODE=1 python3 tests/pins/make_pins.py`（P2 の 15 本。`--txn-rows <1 回目の txn_row JSON>` で `drive-second-run` / `schedule-rematch`）
   - `PYTHONDONTWRITEBYTECODE=1 python3 tests/pins/make_pins_g2_gmail_notify.py`（R10-idempotent / R11-* / R13 / R17 / R23 / R23-b）
   - `PYTHONDONTWRITEBYTECODE=1 python3 tests/pins/make_pins_g3_schedule_error.py`（R18 / R19 / R21-trigger-error / R22-*。入力 `R18-bank-A-invoice-updates.json`）
   - g1 の単体 pin（`r08-bank-b` / `r15-skip-rows-1` / `r15-skip-rows-0-fails` / `r14b-empty-sheets` / `r20-notify-max-lines-2`）は `drive.pin.json` から派生した JSON としてそのまま置いてある。
   - 各 pin の `Config.CHATWORK_API_BASE_URL` は既定の `p2-chatwork` URL なので、実行前に手順 2 のシンク URL に置き換える（並列実行なら `LINE_TO_USER_ID` / `CHATWORK_ROOM_ID` も自分用に変えて共用 `p0-sink` の受信を識別する）。
5. ケースと pin・トリガーの対応（§2 の表と `tests/pins/README.md`）：

   | ケース | pin | Trigger to start from |
   |---|---|---|
   | R01〜R08（A）、R14-a、R11（`["line","chatwork"]`） | `drive.pin.json` | `Watch Drive Folder` |
   | R07 / R08（B）、R13 | `r08-bank-b.pin.json` または `R13-bank-B.pin.json` | `Watch Drive Folder` |
   | R09 | `drive.pin.json` → `drive-second-run.pin.json`（`Read Transactions` = seed ＋ 1 回目の `txn_row`） | `Watch Drive Folder` |
   | R10 / R22-b | `gmail.pin.json` | `Watch Gmail Inbox` |
   | R09-b | `gmail.pin.json` → `R10-idempotent-gmail-second-run.pin.json` ×2 | `Watch Gmail Inbox` |
   | R11 | `R11-slack` / `R11-email` / `R11-line` / `R11-chatwork` / `R11-all-four` / `R11-none` `.pin.json`；R11-b は `notify-partial-fail` / `notify-all-fail`；R11-c（D34）は `R11-c-passthrough-email-line` / `R11-c-passthrough-email`（複製の `Notify Email` を `disabled: true` にして実行） | `Watch Drive Folder` |
   | R14-b | `r14b-empty-sheets.pin.json` | `Watch Drive Folder` |
   | R15 | `r15-skip-rows-1.pin.json` / `r15-skip-rows-0-fails.pin.json` | `Watch Drive Folder` |
   | R16 | `drive-nonecsv.pin.json` | `Watch Drive Folder` |
   | R17 | `R17-parser-mismatch.pin.json` | `Watch Gmail Inbox` |
   | R18 | `R18-schedule-rematch-after-A.pin.json` | `Run Daily Rematch` |
   | R19 / R19-b | `R19-schedule-no-change.pin.json` ×2 | `Run Daily Rematch` |
   | R20 | `r20-notify-max-lines-2.pin.json` | `Watch Drive Folder` |
   | R21-a / R21-b | `error-handler.pin.json` / `R21-trigger-error.pin.json`（Error Workflow 複製） | `Catch Workflow Error` |
   | R21-c | pin なし。使い捨てワークフロー（Webhook → Code `throw new Error('P3 error-handler check')`、`settings.errorWorkflow` = Error Workflow 複製）を有効化して Webhook を叩く。**Error Workflow 複製も有効化が必要**（§6-2/3：`Notify Slack` / `Notify Email` を disabled にするか Credential を付ける） | — |
   | R22 | `gmail-disabled.pin.json`（gmail=false）、`R22-drive-disabled.pin.json`、`R22-schedule-disabled.pin.json`、`unknown-source.pin.json`（R22-c） | 各トリガー |
   | R23 / R23-b | `R23-non-jpy.pin.json` / `R23-b-non-jpy-schedule.pin.json` | `Watch Drive Folder` / `Run Daily Rematch` |

6. 実行：各 pin について `PATCH /rest/workflows/{id}` で `pinData` を `{}` に戻し、pin を `pinData` として保存し、`POST /rest/workflows/{id}/run` に `triggerToStartFrom: { name: "<Trigger to start from>" }` を付けて実行する（本体は `curl -d @file`。pinned バイナリでコマンドライン長を超えるため）。作業領域のハーネス `n8n-run2.py <workflowId> "<Trigger>" --pin <pin.json> --out <file>` はこの手順をそのまま自動化したもの（保存 → 実行 → `GET /api/v1/executions/{id}?includeData=true` でノード別件数を表示）。
7. 判定：`GET /api/v1/executions/{id}?includeData=true` の `data.resultData.runData` から、§2 の各行に書いた値を照合する。シンク側は各シンクの実行 JSON の `body` / `params.roomId` を見る。
8. 後片付け：`pinData` を `{}` に戻し、複製 2 本・シンク・使い捨て・ダミー Credential を `DELETE` する。実行 JSON は削除前に保存する。

---

## 8. 付録 / Appendices (per-group detail files)

各ケースの入力・観測した全アイテム・期待値・判定の全文はこちら。本書はこれらを集約したもの。

- [tests/results/g1-drive.md](results/g1-drive.md) — Drive 経路：R01〜R09、R14、R15、R16、R20（実行 89、92、95、101、104、107、108、111、114。`assert.py` 103 判定）
- [tests/results/g2-gmail-notify.md](results/g2-gmail-notify.md) — Gmail 経路と通知：R10、R09-b（R10-idempotent）、R11（＋R11-b）、R13、R17、R23（＋R23-b）（実行 87、96、115、118、121、124、125、126、129、130、133、136、139、140、142）
- [tests/results/g3-schedule-error.md](results/g3-schedule-error.md) — Schedule 経路と Error Workflow：R18、R19（＋R19-b）、R21、R22、R12、DESIGN §8.4 実行順（実行 144、146、149、150、151、154〜158、161、164、167〜170、172、173）
- [tests/results/fix.md](results/fix.md) — 監査後の再実行（作業ツリー版）：フルパス 200、R09 2 回目 203、R11 全 6 通り（185 / 214 / 188 / 189 / 211 / 192）＋206、R11-b 193 / 195、R11-c（D34 素通り）196 / 198。補助 179 / 181 / 183 / 187 / 190 / 209
- [tests/results/evidence-sha256.md](results/evidence-sha256.md) — 保存済み実行 JSON 113 ファイルの SHA-256 と、p0-sink 実行の現存・同一性の確認結果

関連：`tests/CASES.md`（期待値）、`tests/SMOKE.md`（P2 スモーク、実行 57〜86）、`tests/pins/README.md`（pin の一覧と手順）、`BLOCKERS.md`（H1 / H2 / H6 / H7）、`ASSUMPTIONS.md`（A5 / A11 / A27 / A28）。

---

## EN summary

P3 acceptance run of template 01 (`workflow.json` 36 nodes + `error-handler.json` 14 nodes, unchanged during P3) on a local n8n **2.40.5** on 2026-09-23. Three groups ran the cases in parallel on their own copies of both workflows (created from the JSON files via `POST /api/v1/workflows`, `settings.errorWorkflow` set to the copy of the error handler; all copies, sinks, a throwaway workflow and dummy Header Auth credentials were deleted afterwards; the registered product workflows were not touched). Every expectation in `tests/CASES.md` §2 was checked against the actual execution output (`GET /api/v1/executions/{id}?includeData=true`), and while writing this file the key values (notification texts, idempotency diffs, execution order, R11 routing, R21 messages, summaries) were re-extracted from the saved execution JSON and matched the group reports.

**Result: 22 of the 23 cases in CASES §1 PASS, R12 is N/A by definition, 0 FAIL, no product defect found.** Pinned data (ASSUMPTIONS A5 / A11) replaced every Google node — `Watch Drive Folder`, `Download File`, `Watch Gmail Inbox`, `Run Daily Rematch`, `Read Invoices`, `Read Transactions`, `Update Invoices`, `Upsert Transactions` — plus `Config` and, in the R11 variants, `Notify Slack` / `Notify Email`. Writes were judged by the items that reached the pinned write nodes (`Route Match Results` outputs 0 / 1). Therefore R01, R09, R09-b, R10, R13, R18, R19-b and R23 are "PASS (pinned; live write / sheet diff / polling pending BLOCKERS H1)", R11 and R21 are "pending H2" for Slack / Gmail delivery; LINE / Chatwork were sent over real HTTP to local webhook sinks (H6 / H7 for the real services).

Key evidence: the reference bank_A run (execution 92, also 121 / 146) produced a `body_text` identical to CASES §3 including blank lines; idempotency held on all three paths (Drive 92 → 95: `skipped_existing 11`, Gmail 96 → 115 → 118: `skipped_existing 2` with 115 ≡ 118, Schedule 149 ≡ 150: summary only, `Build Notification []`), with the write nodes not executed on the repeat runs; `Update Invoices → Upsert Transactions → Build Notification` ran in that order with monotonic `startTime` in all 12 writing executions; the Error Workflow was invoked for real (`mode: error`, execution 173) by a production failure of a throwaway workflow (172) and delivered the expected message to both sinks.

**Audit follow-up (fix group, after this file was first finalized).** A concurrent agent changed `Check Notification Results` in the working tree after P3 (D34: a disabled Notify node passes its payload through and must count as a failed channel). The fix group therefore re-ran, on fresh copies of the **working-tree** `workflow.json` / `error-handler.json` (git HEAD `93a0975` + that change; `build_workflow.py --check` OK; every saved execution's `workflowData` carries the working-tree jsCode, md5 in the header table), the full Drive path (200, `body_text` identical to CASES §3) and R09's second run (203), all six R11 variants as separate executions (`["line"]` 185, `["chatwork"]` 214, `["slack"]` 188, `["email"]` 189, all four 211, `[]` 192, plus `["line","chatwork"]` 206), R11-b (193 partial → success, 195 all-fail → throw) and the new D34 pass-through behaviour (196: `["email","line"]` with `Notify Email` disabled → `{attempted 2, ok 1, failed 1}`; 198: `["email"]` only → `All notification channels failed (1): notify node disabled …`; the HEAD logic would have reported 198 as a success). All 59 checks passed. The copies' executions are confirmed gone from n8n; the p0-sink executions still exist and are identical to the saved JSON; SHA-256 of all 113 saved files is in `results/evidence-sha256.md`. Whether to keep or revert the post-P3 product change remains the orchestrator's call; the references the audit flagged as dangling (`P3 finding F2`, `tests/SMOKE-p3-followup.md`, D34, A35–A38) have since been created by the p3f agent (`tests/SMOKE-p3-followup.md` defines F1 / F2 and records its own executions 176 / 178, which the fix group's 196 / 198 reproduce independently).

Not executed (orchestrator to decide): ~~R11 `["line"]` and `["chatwork"]` as separate runs~~ (done in the fix group: 185 / 214); R11-b's "all channels fail → error-handler starts" for the main workflow itself (manual runs never invoke the Error Workflow; the invocation was proven by R21-c instead); R21's LIVE-G variant (break `SHEET_ID`); every LIVE-G / LIVE-N item (real cells, real sheet diff, real triggers, real Slack / Gmail / LINE / Chatwork delivery). Two n8n 2.40.5 findings must go into DESIGN §2.2 / SETUP: an Error Workflow is only invoked when it is itself active, and activation refuses any workflow whose enabled connected nodes lack credentials (`Notify Slack` / `Notify Email` must get credentials or be disabled). Two wording nits in CASES: R17 expects two spaces in `・no_parser_matched  会議のご案内` (implementation joins with one), and R21's expected title depends on the throwaway workflow's name (observed `【n8n エラー】[P3-g3-schedule-error] Throw for error-handler`, error text carries ` [line 1]`).
