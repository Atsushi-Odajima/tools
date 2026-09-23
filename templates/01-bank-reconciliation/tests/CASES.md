# テンプレ01 受け入れテスト / Template 01 acceptance tests — CASES

| 項目 | 値 |
|---|---|
| 対象 | `[Odaji] 01 Bank Deposit Reconciliation v1.0.0`（`workflow.json`）＋ `error-handler.json` |
| 版 | P1 版（2026-09-23、P1 レビュー反映済み）。P3 で実行 ID・合否を `tests/RESULTS.md` に記録する |
| 出典 | `CLAUDE.md` テンプレ01「受け入れテスト」R01〜R11、`DESIGN.md` §7・§8.4、`fixtures/README.md` の期待値表 |
| 前提 | fixture は `fixtures/`。期待値の細部（`txn_id`、`payer_name_norm`、候補）は `fixtures/README.md` §2〜§6 の表が正 |

日本語（§0〜§4）→ English（§5〜§8）の順。

---

## 0. 共通の実行方法

### 0.1 検証区分（各ケースに付ける）

| 区分 | 意味 | 必要なもの |
|---|---|---|
| **PIN** | pinned data だけで完結。Google／通知の Credential 不要。判定は `Match Invoices` の出力（`_kind` 付きアイテム）と `Build Notification` の出力で行う | ローカル n8n のみ |
| **LIVE-G** | Google Credential（BLOCKERS H1）が必要。Drive の実アップロード、Gmail の実ポーリング、`Update Invoices`／`Upsert Transactions` の**実際のセル**、2 回実行後の**シート差分ゼロ**はここでしか確認できない | Google OAuth2（Sheets / Drive / Gmail） |
| **LIVE-N** | 通知の実到達（Slack / Gmail 送信 / LINE / Chatwork）。BLOCKERS H2・H6・H7 | 各サービスの Credential |

**PIN で確認できること**：パース・正規化・突合・通知文面・冪等判定・ルーティング（どの出力にアイテムが流れたか）。
**PIN で確認できないこと**：シートの実セル値、`Append or Update` の一致キー動作と「未指定列が上書きされないこと」、トリガーの実発火、通知の実到達。PIN で PASS したケースは `RESULTS.md` に「ライブ未検証」と明記する（BLOCKERS 備考）。

### 0.2 pinned data の作り方（ASSUMPTIONS A5／A11）

1. 各ノードの pinned data をワークフローに**保存**する：`PATCH /rest/workflows/{id}` の `pinData`（`{ "<ノード名>": [ { "json": {...}, "binary": {...} } ] }`）。実行ボディ内だけの pinData は無視される（A11 実測）。UI の pin でもよいが、バイナリは UI では pin できないため API で入れる。
2. `POST /rest/workflows/{id}/run` に `triggerToStartFrom: { name: "<トリガー名>" }` を付けて手動実行する。
3. pinned にしたノードは実行されず、pinned data がそのまま出力になる。**Google ノードはすべて pinned** にすれば Credential 不要で末端まで流れる。
4. 実行結果は `GET /rest/executions/{id}` で取得し、`Normalize Payer`／`Match Invoices`／`Build Notification`／`Route Match Results`／`Check Notification Results` の各出力を判定する。

ノード別の pinned data（Drive 経路）：

| ノード | pinned data |
|---|---|
| `Watch Drive Folder` | `[{ "json": { "id": "fixture-bank-A", "name": "bank_A_sjis.csv", "mimeType": "text/csv" } }]` |
| `Download File` | `[{ "json": { "id": "fixture-bank-A", "name": "bank_A_sjis.csv", "mimeType": "text/csv" }, "binary": { "data": { "mimeType": "text/csv", "fileName": "bank_A_sjis.csv", "data": "<bank_A_sjis.csv の base64>" } } }]`（`base64 -w0 fixtures/bank_A_sjis.csv`） |
| `Read Invoices` | `fixtures/invoices.seed.csv` の各行を `{ "json": {...} }` にしたもの（キーは列名そのまま。数値は数値でも文字列でもよい：Code 側で `num()` する） |
| `Read Transactions` | `fixtures/transactions.seed.csv` の各行。空シートを試すときは `[{ "json": {} }]`（Always Output Data の挙動） |
| `Update Invoices` / `Upsert Transactions` | `[{ "json": { "pinned": true } }]`（実行させないためのダミー。判定は `Match Invoices` 出力で行う） |
| `Notify Slack` 等 | R11 以外は `NOTIFY_CHANNELS: []` にして IF で止める（pinned 不要） |

Gmail 経路：`Watch Gmail Inbox` に `fixtures/mail_pinned.example.json` の `items` を pin し、`triggerToStartFrom` を `Watch Gmail Inbox` にする。Schedule 経路：`Run Daily Rematch` に `[{ "json": { "timestamp": "2026-09-24T09:00:00.000+09:00" } }]` を pin。

**Config の差し替え**：`CSV_MAPPING`（A／B）、`MAIL_PARSERS`、`NOTIFY_CHANNELS`、`NOTIFY_MAX_LINES`、`TRIGGERS_ENABLED` はケースごとに `Config` ノードの JSON を書き換える（`PATCH /rest/workflows/{id}` の `nodes`）。既定値は `DESIGN.md` §4（`MAIL_PARSERS` の正本は `fixtures/mail_parsers.example.json`）。

### 0.3 シートの初期化（LIVE-G）

各ケース群の前に `invoices` を `fixtures/invoices.seed.csv`、`transactions` を `fixtures/transactions.seed.csv` の内容に戻す（シートを全消去してから貼り付け、または `shared/sheets-schema.md` の手順で再インポート）。判定は Google Sheets を CSV でエクスポートして fixture の期待値と diff する。

### 0.4 n8n 外での先行確認（任意）

`tests/unit/run-code-node.mjs` で `Match Invoices` 等の Code ノードを fixture に対して直接実行できる（ASSUMPTIONS A15）。これは P3 の代替にはならない（§1-5）。ローカル n8n の実行 ID を必ず残す。

---

## 1. ケース一覧

| ID | 内容 | fixture | 区分 | 期待の要点 |
|---|---|---|---|---|
| R01 | 名義・金額一致 | `bank_A_sjis.csv` No.1, 4, 13（＋B No.1, 3, 4, 6） | PIN（実セルは LIVE-G） | `auto`, `paid` |
| R02 | 金額のみ一致・候補 1 | A No.5 | PIN | `amount_only`, `paid`, 通知「要確認」 |
| R03 | 手数料 220 差引 | A No.3 | PIN | `fee_deducted=220`, `paid`, `paid_amount=54780` |
| R04 | 2 請求の合算 | A No.6 | PIN | `combined`, 2 件 `paid` |
| R05 | 一部入金 | A No.8 | PIN | `partial`, `paid_amount=100000` |
| R06 | 同額請求 2 件・名義不一致 | A No.9 | PIN | `ambiguous`, 自動確定なし, 候補 2 件 |
| R07 | 出金行 | A No.2, 7, 10, 15／B No.2, 5, 8 | PIN | txn を生成しない, `ignored_withdraw` |
| R08 | Shift_JIS／UTF-8 BOM | A 全行, B 見出し | PIN | 文字化けなし, BOM が見出しに残らない |
| R09 | 同一 CSV を 2 回投入 | A ×2 | PIN（差分ゼロは LIVE-G） | 2 回目は全件 skip, 書込みなし |
| R10 | Gmail 通知 | `mail_bankX.eml` / `mail_bankY.eml` | PIN（実ポーリングは LIVE-G） | 抽出値一致, R01 と同じ経路で `auto` |
| R11 | 全チャネル通知 | A + `NOTIFY_CHANNELS` 各値 | PIN（ルーティング）＋ LIVE-N（到達） | 設定分のノードだけ実行 |
| R12 | 入金と出金が同一行 | （N/A） | — | 銀行 CSV に存在しない。設計上の扱いのみ記述 |
| R13 | bank_B（BOM + yyyyMMdd + 先頭番号 + ひらがな） | `bank_B_utf8bom.csv` | PIN | 5 txn, 4 `auto`, 1 `unmatched` |
| R14 | 空シート（Always Output Data） | A + `Read Transactions`=`[{}]`／両方 `[{}]` | PIN | 後段が止まらない |
| R15 | `skip_rows=1` | `bank_A_sjis_skip1.csv` | PIN | A と同一の txn。`skip_rows=0` は明示エラー |
| R16 | 非 CSV ファイル | Drive pinned（`memo.pdf`） | PIN | `Skip Non-CSV File` で正常終了, 通知なし |
| R17 | パーサ不一致メール | 本文に記載の 2 通 | PIN | warning が通知に出る, txn なし |
| R18 | Schedule 再突合で matched になる | A の後に INV-2026-021 を登録 | PIN | A-11 が `matched`, `rematched=1` |
| R19 | Schedule で変化なし → 通知なし | A の直後に Schedule | PIN | `Build Notification` が `[]`, 書込みなし |
| R20 | `NOTIFY_MAX_LINES` 超過 | A + `NOTIFY_MAX_LINES=2` | PIN | 「…他 N 件」 |
| R21 | Error Workflow | 使い捨てワークフロー | PIN 相当（自動実行）／通知は LIVE-N | `error-handler` が起動し文面を組み立てる |
| R22 | `TRIGGERS_ENABLED` でトリガーを OFF | Gmail pinned ＋ `TRIGGERS_ENABLED.gmail=false` | PIN | `Skip Disabled Trigger` で終了, `Parse Mail` 不実行, 通知なし |
| R23 | 非 JPY の請求 | A ＋ `Read Invoices` に USD 行 1 件 | PIN | USD 行は突合されず `non_jpy_invoice` 警告 |

---

## 2. 各ケースの詳細

記法：`inv[INV-…]` = `invoices` の該当行、`txn[<txn_id>]` = `transactions` の該当行。`Match Invoices` の出力では前者が `_kind=invoice_update`、後者が `_kind=txn_row`。通知文面は `LANG=ja` の期待値（EN は §7）。`（手数料 ¥220 差引）` 等の理由句・見出し・「…他 N 件」は `shared/messages.ja.json` の `recon_summary`（`reasons.*` / `auto_heading` / `warnings_heading` / `more_items` / `skipped_note`）の値そのもの。

### R01 名義・金額一致 → auto, paid

- **入力**：`bank_A_sjis.csv` No.1 `2026/09/01, 振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ, "33,000"`。同型：No.4（全角名義 `フリコミ　ヤマダ　タロウ`）、No.13（包含一致 `ｶ)ｻﾝﾌﾟﾙﾌｰｽﾞﾄｳｷﾖｳ` ⊃ alias `サンプルフーズ`）
- **経路**：`Parse Bank CSV` → `Match Invoices` 規則 1（`both.length === 1`）
- **期待 invoices**：`inv[INV-2026-001] = status paid, paid_amount 33000, paid_date 2026-09-01, matched_txn_ids 2026-09-01|33000|サンプルシヨウジ|, match_confidence auto, fee_deducted 0`。No.4 → `inv[INV-2026-003]`（9800）、No.13 → `inv[INV-2026-012]`（27500）も同様
- **期待 transactions**：`txn[2026-09-01|33000|サンプルシヨウジ|] = source bank_csv, txn_date 2026-09-01, payer_name_raw 振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ, payer_name_norm サンプルシヨウジ, amount 33000, memo "", matched_invoice_ids INV-2026-001, status matched, suggested_invoice_ids ""`
- **補足**：INV-2026-001 と INV-2026-017 は同じ顧客（名義一致 2 件）だが、金額一致は INV-001 のみなので規則 1 で一意に決まる（INV-017 は変更なし）
- **期待通知**：`■ 自動消込` に `・2026-09-01 振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ ¥33,000 → INV-2026-001`。要確認・候補複数・未消込には出ない
- **実行**：§0.2 の Drive 経路 pinned で A を流す。`Route Match Results` 出力 0 に上記 `invoice_update`、出力 1 に `txn_row` が流れることを確認
- **区分**：PIN。実セル値・`Append or Update` の列挙動は LIVE-G

### R02 金額のみ一致・候補 1 → amount_only, paid, 通知に要確認

- **入力**：A No.5 `2026/09/04, 振込 ｻﾄｳ ｹｲｺ, "128,000"`（INV-2026-004 は 128,000・alias `ミホンデザイン`。名義は別人）
- **経路**：規則 2（`byAmt.length === 1 && byName.length === 0`）
- **期待 invoices**：`inv[INV-2026-004] = paid, paid_amount 128000, paid_date 2026-09-04, matched_txn_ids 2026-09-04|128000|サトウケイコ|, match_confidence amount_only, fee_deducted 0`
- **期待 transactions**：`txn[2026-09-04|128000|サトウケイコ|] = matched, matched_invoice_ids INV-2026-004, payer_name_norm サトウケイコ`
- **期待通知**：`■ 要確認（…）` に `・2026-09-04 振込 ｻﾄｳ ｹｲｺ ¥128,000 → INV-2026-004 （金額のみ一致・要確認）`。summary `b` に計上（`a` ではない）
- **区分**：PIN

### R03 手数料 220 差引 → fee_deducted=220, paid

- **入力**：A No.3 `2026/09/02, 振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ, "54,780"`（INV-2026-002 = 55,000）
- **経路**：規則 3a（`byAmt` 0 件、`byName` 1 件、`55000 − 54780 = 220 ∈ FEE_SET`）。名義は後株 `(ﾕ` → NFKC `(ユ` → 末尾トークン除去 → `テストコウギヨウ`（alias 1 番目と完全一致）
- **期待 invoices**：`inv[INV-2026-002] = paid, paid_amount 54780, paid_date 2026-09-02, matched_txn_ids 2026-09-02|54780|テストコウギヨウ|, match_confidence fee_deducted, fee_deducted 220`
- **期待 transactions**：`txn[2026-09-02|54780|テストコウギヨウ|] = matched, matched_invoice_ids INV-2026-002`
- **期待通知**：`■ 要確認` に `・2026-09-02 振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ ¥54,780 → INV-2026-002 （手数料 ¥220 差引）`
- **区分**：PIN

### R04 2 請求の合算 → combined, 2 件 paid

- **入力**：A No.6 `2026/09/05, 振込 ｶ)ﾃｽﾄﾌﾞﾂｻﾝ, "1,234,567"`（INV-2026-005 = 700,000 ＋ INV-2026-006 = 534,567、同一顧客 C-005）
- **経路**：規則 3b（`byAmt` 0 件、`byName` 2 件、2〜3 件の部分和が一意に一致）
- **期待 invoices**：`inv[INV-2026-005] = paid, paid_amount 700000, paid_date 2026-09-05, matched_txn_ids 2026-09-05|1234567|テストブツサン|, match_confidence combined, fee 0`；`inv[INV-2026-006] = paid, paid_amount 534567, 同じ paid_date・matched_txn_ids・combined`
- **期待 transactions**：`txn[2026-09-05|1234567|テストブツサン|] = matched, matched_invoice_ids INV-2026-005,INV-2026-006`（1 行。2 件の ID をカンマ区切り）
- **期待通知**：`■ 要確認` に `・2026-09-05 振込 ｶ)ﾃｽﾄﾌﾞﾂｻﾝ ¥1,234,567 → INV-2026-005, INV-2026-006 （合算）`
- **判定の要点**：`paid_amount` は各請求の**残額**（入金額ではない）。`invoice_update` が 2 アイテム出る
- **区分**：PIN

### R05 一部入金 → partial, paid_amount 加算

- **入力**：A No.8 `2026/09/08, 振込 ｻﾝﾌﾟﾙｼｽﾃﾑ(ｶ, "100,000"`（INV-2026-007 = 250,000）
- **経路**：規則 3c（`byName` 1 件、差 150,000 ∉ FEE_SET、`amount < remaining`）
- **期待 invoices**：`inv[INV-2026-007] = status partial, paid_amount 100000, paid_date 2026-09-08, matched_txn_ids 2026-09-08|100000|サンプルシステム|, match_confidence auto, fee_deducted 0`
- **期待 transactions**：`txn[2026-09-08|100000|サンプルシステム|] = matched, matched_invoice_ids INV-2026-007`
- **期待通知**：`■ 自動消込` に `・2026-09-08 振込 ｻﾝﾌﾟﾙｼｽﾃﾑ(ｶ ¥100,000 → INV-2026-007 （一部入金・残 ¥150,000）`。summary `a` に計上
- **区分**：PIN

### R06 同額請求 2 件・名義不一致 → ambiguous, 自動確定なし

- **入力**：A No.9 `2026/09/09, 振込 ｵｵﾊﾞ ﾏｻｵ, "44,000"`（INV-2026-008 見本印刷と INV-2026-009 モデル企画が共に 44,000。どちらも alias なし、漢字名は名義と一致しない）
- **経路**：規則 4（`byAmt.length >= 2 && byName.length === 0` → `ambiguous('same_amount_multiple')`）
- **期待 invoices**：**変更なし**（`invoice_update` に INV-008／009 が出ない。両方 `unpaid, paid_amount 0` のまま）
- **期待 transactions**：`txn[2026-09-09|44000|オオバマサオ|] = status ambiguous, matched_invoice_ids "", suggested_invoice_ids INV-2026-008,INV-2026-009`（順序：スコア同点 → due_date 昇順）
- **期待通知**：`■ 候補複数（自動確定せず。候補から選んでください）` に `・2026-09-09 振込 ｵｵﾊﾞ ﾏｻｵ ¥44,000 → 候補: INV-2026-008(¥44,000), INV-2026-009(¥44,000)`。summary `c` に計上
- **区分**：PIN

### R07 出金行 → 無視

- **入力**：A No.2（`ｶｰﾄﾞ ｻﾝﾌﾟﾙｶｰﾄﾞ` 出金 12,800）、No.7（8,450）、No.10（ATM 30,000）、No.15（手数料 440）。B No.2, 5, 8
- **経路**：`parseBankCsv` の `!(deposit > 0)` → `ignored_withdraw++`
- **期待**：これらの行から txn が**生成されない**（`Parse Bank CSV` の出力に無い、`transactions` に行が増えない）。A の `file_stats.ignored_withdraw = 4`、summary `ignored_withdraw = 4`。B は 3
- **区分**：PIN

### R08 Shift_JIS／UTF-8 BOM → 文字化けなく名義が読める

- **入力**：`bank_A_sjis.csv`（cp932、UTF-8 として不正なバイト列を含むことを Python で確認済み）、`bank_B_utf8bom.csv`（先頭 `EF BB BF`）
- **期待（A）**：`Parse Bank CSV` の各 `payer_name_raw` が `fixtures/README.md` §4 の raw 列と一致（例 `振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ`、`フリコミ　ヤマダ　タロウ`）。`U+FFFD` を含まない。`payer_name_norm` が同表と一致（半角カナ→全角カナ、濁点合成、`ｰ`→`ー`）
- **期待（B）**：`CSV column not found: "取引日"` にならない（BOM が 1 列目見出しに残らない）。`payer_name_raw` が `0123 カ)ダミーカコウ` 等と一致
- **復号経路**：Code ノード（`TextDecoder`）で確定済み（`ASSUMPTIONS.md` A6、`DESIGN.md` §3.8）。`Extract From File` は `workflow.json` に含まれないことも確認する。結果は `RESULTS.md` に記録
- **区分**：PIN

### R09 同一 CSV を 2 回投入 → 2 回目は全件 skip、シート差分なし

- **入力**：A を 1 回流したあと、`Read Transactions` の pinned data を「`transactions.seed` ＋ 1 回目の `txn_row` 11 件（`_kind` を除く）」に差し替えて、同じ A をもう一度流す
- **期待（2 回目）**：`Match Invoices` の出力は `summary` 1 件のみ（`n=0, a=0, b=0, c=0, skipped_existing=11, skipped_duplicate_in_batch=0`）。`invoice_update` 0 件、`txn_row` 0 件。`Route Match Results` 出力 0・1 が空で `Update Invoices`／`Upsert Transactions` が実行されない
- **期待通知**：タイトル `【入金消込 {date}】新規の入金はありませんでした`、本文に `（処理済みのため skip：11 件）`（D16 `skipped_note`）
- **R09-b（Gmail）**：`mail_pinned.example.json` の 2 通を 2 回流す。2 回目は `skipped_existing=2`
- **LIVE-G**：実シートで 2 回目実行後に `invoices`／`transactions` を CSV エクスポートし、1 回目の結果と全セル一致
- **区分**：PIN（差分ゼロの実証は LIVE-G）

### R10 Gmail 通知 → amount／payer／date 抽出、R01 と同じ経路で消込

- **入力**：`Watch Gmail Inbox` に `fixtures/mail_pinned.example.json` の 2 アイテム（`text` は `.eml` の本文をデコードしたもの）。`MAIL_PARSERS` = `fixtures/mail_parsers.example.json`
- **期待抽出**：X → `amount 104500, payer_name_raw カ)ダミーデンキ（NFKC 後）, txn_date 2026-09-17`；Y → `amount 19800, payer_name_raw ササキ ハナコ, txn_date 2026-09-18`（Date ヘッダ 09-19 ではなく本文の日付）
- **期待 invoices**：`inv[INV-2026-018] = paid, auto, 104500, paid_date 2026-09-17, matched_txn_ids 2026-09-17|104500|ダミーデンキ|【サンプル銀行】ご入金のお知らせ(gmail:18f3aabb00000001)`；`inv[INV-2026-019] = paid, auto, 19800, paid_date 2026-09-18, matched_txn_ids 2026-09-18|19800|ササキハナコ|depositnotification-samplebank(gmail:18f3aabb00000002)`
- **期待 transactions**：2 行、`source gmail`、`memo` は `【サンプル銀行】ご入金のお知らせ (gmail:18f3aabb00000001)`／`Deposit Notification - Sample Bank (gmail:18f3aabb00000002)`、`status matched`
- **期待通知**：タイトル `処理 2件｜自動消込 2｜要確認 0｜未消込 0`、`■ 自動消込` に `・2026-09-17 カ)ダミーデンキ ¥104,500 → INV-2026-018` と `・2026-09-18 ササキ ハナコ ¥19,800 → INV-2026-019`
- **実行**：`triggerToStartFrom = Watch Gmail Inbox`。`Route by Source` の `gmail` 出力 → `Parse Mail` → `Collect Transactions` を通ることを確認
- **LIVE-G**：Gmail に 2 通を実際に送り（自分宛て）、既定の `GMAIL_QUERY`（`subject:(入金 OR Deposit) newer_than:1d`。X・Y 両方の件名に一致する）でポーリングされて `Simplify OFF` の実出力が §3.1 の想定どおりか確認（差分があれば `DESIGN.md` §3.1 と pinned 例を更新）
- **区分**：PIN（実ポーリングと実出力形状は LIVE-G）

### R11 全チャネル通知 → 設定分のみ到達

- **入力**：A を `NOTIFY_CHANNELS` = `["slack"]`、`["email"]`、`["line"]`、`["chatwork"]`、`["slack","email","line","chatwork"]`、`[]` の 6 通りで実行
- **期待（PIN）**：`Check Slack/Email/LINE/Chatwork Enabled` の true 出力に流れるのは設定したチャネルだけ。`[]` では 4 つの IF がすべて false で通知ノードが 1 つも実行されず、`Merge Notification Results`／`Check Notification Results` も実行されない。`Build Notification` の出力に `title / body_text / slack_blocks / line_text / chatwork_text` が揃い、`Notify LINE` の `text` は `line_text`、`Notify Chatwork` の `body` は `chatwork_text` を参照している
- **期待（LIVE-N）**：Slack にヘッダー＋セクション、Email に件名＝title・本文＝body_text、LINE に line_text、Chatwork に chatwork_text が届く。Credential 未登録のチャネルは「HTTP 呼び出しを試みた」ことを実行ログで確認し、BLOCKERS H2/H6/H7 として未到達を記録
- **R11-b（一部失敗・全滅）**：`["slack","email"]` で `SLACK_CHANNEL` を存在しない値にして実行 → `Notify Slack` は error 出力、`Notify Email` は送信され、`Check Notification Results` が `channels_attempted 2, channels_ok 1, channels_failed 1` を出して実行は**成功**（Error Workflow は起動しない）。次に `["slack"]` で同じ不正値 → `Check Notification Results` が `throw`、実行は失敗し `error-handler` が起動する（`DESIGN.md` D17）。Slack Credential が無い間は LINE／Chatwork の HTTP Request（到達不能 URL）で代替できる
- **区分**：PIN（ルーティング）＋ LIVE-N（到達）

### R12 入金と出金が同一行 → N/A

- 銀行の入出金明細では 1 行に入金と出金が同時に入ることはない（どちらか一方の列だけが埋まる）ため、fixture には含めず **N/A** とする。
- 設計上の扱い（記録のみ）：`parseBankCsv` は `deposit_col` だけで判定する（`deposit > 0` なら取引、それ以外は無視）。仮に両方が埋まった行が来ても入金として扱われ、`withdraw_col` は参照されない（`DESIGN.md` §4 `CSV_MAPPING.withdraw_col` は説明用）。SETUP に「集計行・小計行が `入金額` を持つ CSV は `skip_rows` か事前の除去で対応」と書く。

### R13 bank_B（BOM + yyyyMMdd + 先頭番号 + ひらがな）→ 正しくパース

- **入力**：`bank_B_utf8bom.csv`、`CSV_MAPPING` を `csv_mapping.examples.json` の `bank_B_utf8bom.csv` に差し替え（`date_format=yyyyMMdd`。`auto` でも同結果）
- **期待 txn**（`fixtures/README.md` §5）：
  - No.1 `0123 カ)ダミーカコウ` → `payer_name_norm ダミーカコウ`（`カ)` は先頭の数字列を許容して除去 → `STRIP_LEADING_DIGITS` で `0123` 除去）、`txn_id 2026-09-17|41800|ダミーカコウ|` → `inv[INV-2026-013] = paid, auto, 41800`
  - No.3 `ふりこみ　すずき　いちろう` → `スズキイチロウ`（ひらがな→カタカナ、`フリコミ` 除去）→ `inv[INV-2026-014] = paid, auto, 15400`
  - No.4 `ユ)ミホンプランニング` → `ミホンプランニング` → `inv[INV-2026-015] = paid, auto, 57200`
  - No.6 `0045 タカハシ ミキ` → `タカハシミキ` → `inv[INV-2026-016] = paid, auto, 12100`
  - No.7 `フリコミ ワタナベ ケン` → `ワタナベケン` → `txn status unmatched, suggested ""`
  - No.2, 5, 8 は出金（R07）
- **期待 summary**：`n=5, a=4, b=0, c=1, ignored_withdraw=3`。日付が `2026-09-17` 等 `yyyy-MM-dd` に正規化されている
- **期待通知**：`■ 未消込` に `・2026-09-22 フリコミ ワタナベ ケン ¥7,700 → 候補: —`、`■ 自動消込` に 4 行
- **区分**：PIN

### R14 空シート（Always Output Data）→ 後段が止まらない

- **R14-a**：`Read Transactions` を `[{ "json": {} }]` に、`Read Invoices` は seed のまま A を流す → 結果は R01〜R06 と同一（`skipped_existing=0`）。`{}` 行が txn として数えられない
- **R14-b**：`Read Invoices` も `[{ "json": {} }]` にして A を流す → 11 件すべて `unmatched`、`suggested_invoice_ids ""`、`invoice_update` 0 件、`c=11`。通知の `■ 未消込` に 11 行
- **区分**：PIN。LIVE-G ではヘッダーだけのシートで同じことを確認

### R15 `skip_rows=1` → 見出し前の行を捨てる

- **入力**：`bank_A_sjis_skip1.csv`（A と同内容。見出しの前に `サンプル銀行 入出金明細 …` の 1 行がある）
- **期待**：`CSV_MAPPING.skip_rows=1` で A と**同一**の 11 txn（`txn_id` 完全一致、`_row` は A より 1 大きい）、`ignored_withdraw=4`。`skip_rows=0` のままだと `Parse Bank CSV` が `CSV column not found: "日付"` で失敗する（黙って 0 件にしない）
- **区分**：PIN

### R16 非 CSV ファイル → NoOp

- **入力**：`Watch Drive Folder` を `[{ "json": { "id": "fixture-pdf", "name": "memo.pdf", "mimeType": "application/pdf" } }]` に pin
- **期待**：`Check File Is CSV` が false → `Skip Non-CSV File` が実行され、`Download File` 以降は実行されない。実行は成功終了。通知なし
- **区分**：PIN

### R17 パーサ不一致メール → warning が通知に出る

- **入力（a: no_parser_matched）**：`Watch Gmail Inbox` に `{ "json": { "id": "18f3aabb00000009", "date": "2026-09-20T10:00:00+09:00", "from": { "text": "someone@example.org" }, "subject": "会議のご案内", "text": "来週の会議についてご連絡します。" } }`
- **入力（b: parser_no_capture）**：`{ "json": { "id": "18f3aabb00000010", "date": "2026-09-20T10:05:00+09:00", "from": { "text": "サンプル銀行 <notice@example.jp>" }, "subject": "【サンプル銀行】ご入金のお知らせ", "text": "本日の入金はありません。" } }`（bankX に一致するが金額・名義が取れない）
- **期待**：`Parse Mail` が (a) `{_kind: warning, type: no_parser_matched}`、(b) `{_kind: warning, type: parser_no_capture, parser: bankX}` を出す。`Collect Transactions` の `txns=[]`、`warnings` 2 件。`Match Invoices` は `summary` のみ（`n=0`）。書込みなし
- **期待通知**：タイトル `新規の入金はありませんでした`、`■ 警告`（D16 `warnings_heading`）に `・no_parser_matched  会議のご案内` と `・parser_no_capture bankX 【サンプル銀行】ご入金のお知らせ`
- **区分**：PIN

### R18 Schedule 再突合で前日 unmatched が matched になる

- **前提**：A を流した状態（`transactions` = seed ＋ A の 11 行。A-11 `2026-09-11|66000|ミホンシヨウカイ|` は `unmatched`）
- **入力**：`Read Invoices` に seed ＋ A の更新を反映し、さらに買い手が登録した `INV-2026-021, C-009, 株式会社見本商会, カ)ミホンシヨウカイ,ミホンシヨウカイ, shokai@example.jp, 66000, JPY, 2026-09-15, 2026-10-15, unpaid, 0, …` を追加。`Run Daily Rematch` から実行
- **期待 invoices**：`inv[INV-2026-021] = paid, auto, paid_amount 66000, paid_date 2026-09-11, matched_txn_ids 2026-09-11|66000|ミホンシヨウカイ|`
- **期待 transactions**：`txn[2026-09-11|66000|ミホンシヨウカイ|]` が `matched, matched_invoice_ids INV-2026-021, suggested ""` に更新（`imported_at` は元の値を保持）。A-9（ambiguous）・A-12・A-14（unmatched）は候補に変化がないので**書き戻さない**（`txn_row` はこの 1 件のみ）
- **期待 summary**：`rematched=1, n=0`。通知は出る（D12：状態が変わった）。`■ 自動消込` に `・2026-09-11 振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ ¥66,000 → INV-2026-021`
- **注意（P2 へ）**：疑似コードのままだと再突合で評価した既存行も `a`/`c` に数えられ、タイトルが `処理 0件｜自動消込 1｜要確認 0｜未消込 3` となる（D11 の「n = A + B + C（新規のみ）」と一致しない）。P2 で「既存行は `rematched` にだけ数える」か「タイトルに `再突合 {rematched}` を足す」かを決めて `ASSUMPTIONS.md` に記録する。RESULTS では明細行の内容を正とし、タイトルの数字は P2 の決定に従う
- **区分**：PIN

### R19 Schedule で変化なし → 通知なし・書込みなし

- **入力**：R18 の「INV-2026-021 を登録する前」の状態で `Run Daily Rematch` から実行
- **期待**：`Match Invoices` は `summary` のみ（`rematched=0, n=0, warnings=[]`）。`txn_row` 0 件（変化のない unmatched／ambiguous は書き戻さない）。`Build Notification` が `[]` を返し、`Check … Enabled` 以降が実行されない
- **R19-b**：同じ状態で Schedule を 2 回連続実行しても結果が同一（冪等）
- **区分**：PIN

### R20 `NOTIFY_MAX_LINES` 超過 → 「…他 N 件」

- **入力**：A を `NOTIFY_MAX_LINES=2` で実行
- **期待通知**：`■ 要確認` 2 行＋`…他 1 件`、`■ 候補複数` 1 行、`■ 未消込` 2 行＋`…他 1 件`、`■ 自動消込` 2 行＋`…他 2 件`（D16 `more_items`）。`slack_blocks` の各 section text が 3,000 文字未満
- **区分**：PIN

### R21 Error Workflow が起動する

- **前提**：Error Trigger は手動実行では発火しない（公式ドキュメント）。pinned data も本番実行では使われない。よって Google 不要の方法として使い捨てワークフローを使う
- **入力**：使い捨てワークフロー `[P3] Throw for error-handler`（Schedule Trigger 毎分 → Code `throw new Error('P3 error-handler check')`）の Settings → Error workflow に `error-handler` を指定して有効化。`error-handler` の `Config` は `NOTIFY_CHANNELS: []`（到達は LIVE-N）
- **期待**：1 分以内に `error-handler` の実行が生まれ、`Build Error Message` の出力 `title` が `【n8n エラー】[P3] Throw for error-handler`、`body_text` に `失敗したノード：<Code ノード名>`・`エラー：P3 error-handler check` を含む。確認後に使い捨てワークフローを無効化・削除
- **LIVE-G の本命**：本体を有効化し `SHEET_ID` を壊して Drive に CSV を置く → `Read Invoices` で失敗 → `error-handler` が通知（`DESIGN.md` §2.2）
- **区分**：PIN 相当（自動実行だが Credential 不要）。通知の到達は LIVE-N

### R22 `TRIGGERS_ENABLED` で OFF にした系統は `Skip Disabled Trigger` で終わる

- **入力**：R10 と同じ Gmail pinned（2 通）。`Config` の `TRIGGERS_ENABLED` を `{ "drive": true, "gmail": false, "schedule": true }` にして `triggerToStartFrom = Watch Gmail Inbox`
- **期待**：`Route by Source` の `gmail` 出力にアイテムが流れず、Fallback（Extra Output）→ `Skip Disabled Trigger` が実行される。`Parse Mail`／`Collect Transactions`／`Read Invoices` 以降は実行されない。実行は成功終了、通知なし、書込みなし
- **R22-b**：`gmail: true` に戻すと R10 と同じ結果になる（`TRIGGERS_ENABLED` 以外は変えない）
- **R22-c**：`SOURCE` に未知の値（`Config` の `SOURCE` を `"Manual"` に固定）でも同じく `Skip Disabled Trigger` で終わる
- **注意**：OFF にしてもトリガーノード自身のポーリング（API 呼出し）は続く（`DESIGN.md` D26、Sticky S1）。LIVE-G ではこの点を実行ログで確認する
- **区分**：PIN

### R23 非 JPY の請求は突合されず警告になる

- **入力**：A を流す。`Read Invoices` の pinned data を seed ＋ 1 行 `INV-2026-022, C-019, Sample Overseas LLC, サンプルオーバーシーズ, overseas@example.com, 128000, USD, 2026-09-01, 2026-09-30, unpaid, 0, …` にする（金額は A-5 の 128,000 と同じにして、通貨を見なければ規則 2／4 の候補に入ることを確かめる）
- **期待**：結果は R01〜R06 と同一（A-5 は引き続き INV-2026-004 に `amount_only` で一致し、INV-2026-022 は `byAmt` にも候補にも入らない）。`inv[INV-2026-022]` は `invoice_update` に出ない。summary `warnings` に `{ type: non_jpy_invoice, invoice_id: INV-2026-022, currency: USD }` が 1 件
- **期待通知**：本文末尾に `■ 警告` と `・non_jpy_invoice INV-2026-022 USD`
- **R23-b（Schedule）**：同じ pinned で `Run Daily Rematch` から実行 → `rematched=0` かつ取込警告なしなので `Build Notification` は `[]`（`non_jpy_invoice` だけでは毎朝通知しない。`DESIGN.md` D12／D28）
- **区分**：PIN

---

## 3. 期待通知の全文（`LANG=ja`、A を初期状態に流したとき）

見出し・理由句は `shared/messages.ja.json` の `recon_summary` の値。空行の数は実装（`join`）に依存するため判定対象外。

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

日付 `2026-09-23` は実行日に読み替える。未消込の候補は残っている請求に依存する（`fixtures/README.md` §7）。

---

## 4. 仕様判断 / Decisions（`ASSUMPTIONS.md` へ転記）

- **T01 fixture の追加**：仕様の 4 種（A・B・メール 2 通・seed）に加えて `transactions.seed.csv`（消込済み 1 件。`Read Transactions` が空でない状態を作る）、`bank_A_sjis_skip1.csv`（`skip_rows` の実証）、`mail_parsers.example.json`／`mail_pinned.example.json`／`csv_mapping.examples.json`（P3 の pinned data と Config 差し替えをそのまま使えるようにする）を同梱する。理由：P3 の再現性と速度。販売物に含めても買い手の設定例として役立つ。
- **T02 期待値の前提は「初期状態から各入力を 1 回」**：A・B・メールの対象請求は互いに素にしたので消込結果は順序に依存しないが、`suggested_invoice_ids` は残請求に依存する。P3 は各ファイルの前にシートを seed に戻す。
- **T03 名義正規化のトークン順**：`DESIGN.md` §6.6 を「どこでも除去するトークン → 前株 `X)`／後株 `(X`」の 2 段階に修正済み（2026-09-23、`ASSUMPTIONS.md` A16）。期待する `payer_name_norm`（`fixtures/README.md` §4〜§6）は修正後の関数で全 14 名義を Node で検証した値。1 回走査だと `振込 ｶ)…` が `カ…` になり `txn_id` が変わる。
- **T04 メールの `payer_name_raw` は NFKC 後**：疑似コード（本文を NFKC してから正規表現）に従い、`ｶ)ﾀﾞﾐｰﾃﾞﾝｷ` は `カ)ダミーデンキ` として保存される。CSV 経路との不揃いは許容し、SETUP に書く。
- **T05 メール Y のパーサは表形式用に変更**：fixture Y の表形式に合わせて `Amount\s+…`／`Remitter\s+…`／`Transaction Date\s+…` に最終化し、`DESIGN.md` §4 の既定値も同じ値に更新済み（正本は `fixtures/mail_parsers.example.json`、`ASSUMPTIONS.md` A17）。旧 `Amount[：:]` 形式では Y が `parser_no_capture` になることを Node で確認。bankX は `日付` ラベルを要求する `date_regex` にして誤キャプチャ（口座番号等）を防ぐ。
- **T06 入金済み・取消請求の罠行**：A-11（INV-010 と同名義・同額）と A-12（INV-011 と同名義・同額）を入れ、`status ∉ {unpaid, partial}` の請求が候補にも一致にも出ないことを明示的に検証する。
- **T07 再突合時のタイトル件数**：疑似コードでは再突合で評価した既存行も `a`/`c` に数える（R18 注意）。P2 で決めて記録する。
- **T08 通知本文の空行**：`DESIGN.md` §6.8 を `[title, ...sections].join('\n\n')` に直し、タイトルと各セクションの間は空行 1 つになった（§3 の全文と一致）。空行の数は引き続き判定対象外。
- **T09 `imported_at` の書式**：ISO 8601 + JST オフセット（`yyyy-MM-ddTHH:mm:ss+09:00`、`shared/sheets-schema.md` の datetime）に統一済み。`DESIGN.md` §6.7 の `nowStr` と `fixtures/transactions.seed.csv` を修正（`DESIGN.md` D30）。本 CASES は形式のみ判定。
- **T10 `memo_norm` の定義差**：`shared/sheets-schema.md` を `DESIGN.md` の定義（NFKC → 空白除去 → `|`→`/` → 小文字化、記号は残す）に合わせて統一済み（`DESIGN.md` D30）。期待値どおりメールの `txn_id` に `【】()` が残る。
- **T11 R12 は N/A**：入金と出金が同一行になる銀行 CSV は無く、パーサは `deposit_col` だけで判定する。
- **T12 非 JPY**：`DESIGN.md` §6.7 に `currency ≠ JPY` の除外と `non_jpy_invoice` 警告を実装し、R23 を追加した。seed は全件 JPY のまま（USD 行を seed に入れると A・B・M の `warnings=[]` の期待値が全て変わるため、R23 では pinned data にだけ 1 行加える）。
- **T13 `TRIGGERS_ENABLED`（R22）**：仕様「トリガー（3系統、Config で ON／OFF）」に対応する Config キーが `DESIGN.md` に無かったため D26 として追加し、R22 で `gmail=false` の経路と未知の `SOURCE` を検証する。OFF でもトリガーのポーリングは続く点は LIVE-G で確認する。
- **T14 通知の一部失敗（R11-b）**：Notify ノードを Continue (using error output) にし、全チャネル失敗のときだけ `Check Notification Results` が `throw` する設計（`DESIGN.md` D17）に合わせ、R11 に一部失敗・全滅の副ケースを追加した。

---
---

## 5. Common execution notes (EN)

### 5.1 Verification classes

| Class | Meaning | Needs |
|---|---|---|
| **PIN** | Fully verifiable with pinned data; no Google or notification credentials. Assert on the output items of `Match Invoices` (tagged `_kind`) and `Build Notification` | local n8n only |
| **LIVE-G** | Needs Google credentials (BLOCKERS H1): a real Drive upload, real Gmail polling, the **actual cells** written by `Update Invoices` / `Upsert Transactions`, and the **zero sheet diff** after a second run can only be checked live | Google OAuth2 (Sheets / Drive / Gmail) |
| **LIVE-N** | Actual delivery to Slack / Gmail send / LINE / Chatwork (BLOCKERS H2, H6, H7) | each service's credential |

Pinned data proves parsing, normalization, matching, notification text, idempotency logic and routing. It cannot prove real cell values, `Append or Update` key behaviour (including "unmapped columns are not blanked"), real trigger firing or real delivery. Cases passed with PIN only are marked "not verified live" in `RESULTS.md`.

### 5.2 Pinned-data mechanics (ASSUMPTIONS A5 / A11)

1. Save pinned data **into the workflow**: `PATCH /rest/workflows/{id}` with `pinData` = `{ "<Node name>": [ { "json": {...}, "binary": {...} } ] }`. Pin data passed only in the run body is ignored (measured). The UI pin works too, except for binary, which must go through the API.
2. Run manually with `POST /rest/workflows/{id}/run` and `triggerToStartFrom: { name: "<trigger name>" }`.
3. A pinned node is not executed; its pinned data becomes its output. Pin **every Google node** and the run reaches the end without credentials.
4. Fetch `GET /rest/executions/{id}` and assert on the outputs of `Match Invoices`, `Build Notification` and `Route Match Results`.

Per-node pinned data for the Drive path: `Watch Drive Folder` → one file item (`id`, `name`, `mimeType`); `Download File` → the same json plus `binary.data` = base64 of the CSV (`base64 -w0 fixtures/bank_A_sjis.csv`); `Read Invoices` → rows of `invoices.seed.csv` as `{ "json": {...} }` (numbers may be numbers or strings, the Code node coerces); `Read Transactions` → rows of `transactions.seed.csv` (or `[{ "json": {} }]` for the empty-sheet case); `Update Invoices` / `Upsert Transactions` → a dummy item so they do not execute. Gmail path: pin `Watch Gmail Inbox` with the `items` of `fixtures/mail_pinned.example.json` and start from that trigger. Schedule path: pin `Run Daily Rematch` with one `{ "timestamp": "2026-09-24T09:00:00.000+09:00" }` item.

Config values (`CSV_MAPPING`, `MAIL_PARSERS`, `NOTIFY_CHANNELS`, `NOTIFY_MAX_LINES`) are changed per case by editing the `Config` node JSON; defaults are in `DESIGN.md` §4.

### 5.3 Sheet reset (LIVE-G)

Before each group of cases, restore `invoices` from `fixtures/invoices.seed.csv` and `transactions` from `fixtures/transactions.seed.csv`. Assert by exporting the sheets to CSV and diffing against the expected values in `fixtures/README.md`.

---

## 6. Case list (EN)

| ID | Case | Fixture | Class | Expected in short |
|---|---|---|---|---|
| R01 | Name + amount match | `bank_A_sjis.csv` rows 1, 4, 13 (+ B rows 1, 3, 4, 6) | PIN (cells: LIVE-G) | `auto`, `paid` |
| R02 | Amount only, single candidate | A row 5 | PIN | `amount_only`, `paid`, listed under "needs review" |
| R03 | Fee 220 deducted | A row 3 | PIN | `fee_deducted=220`, `paid`, `paid_amount=54780` |
| R04 | Two invoices combined | A row 6 | PIN | `combined`, both `paid` |
| R05 | Partial payment | A row 8 | PIN | `partial`, `paid_amount=100000` |
| R06 | Two same-amount invoices, no name match | A row 9 | PIN | `ambiguous`, nothing auto-confirmed, 2 candidates |
| R07 | Withdrawal rows | A rows 2, 7, 10, 15 / B rows 2, 5, 8 | PIN | no txn, counted in `ignored_withdraw` |
| R08 | Shift_JIS / UTF-8 BOM | all of A, header of B | PIN | no mojibake, no BOM in the first header |
| R09 | Same CSV twice | A ×2 | PIN (zero diff: LIVE-G) | second run skips all, writes nothing |
| R10 | Gmail notification | `mail_bankX.eml` / `mail_bankY.eml` | PIN (real polling: LIVE-G) | extraction correct, `auto` via the same path as R01 |
| R11 | All channels | A + each `NOTIFY_CHANNELS` value | PIN (routing) + LIVE-N (delivery) | only configured channel nodes run |
| R12 | Deposit and withdrawal on one row | (N/A) | — | does not occur in bank CSVs; design note only |
| R13 | bank_B (BOM + yyyyMMdd + leading digits + hiragana) | `bank_B_utf8bom.csv` | PIN | 5 txns, 4 `auto`, 1 `unmatched` |
| R14 | Empty sheets (Always Output Data) | A + `Read Transactions`=`[{}]` / both `[{}]` | PIN | downstream keeps running |
| R15 | `skip_rows=1` | `bank_A_sjis_skip1.csv` | PIN | identical txns to A; `skip_rows=0` fails loudly |
| R16 | Non-CSV file | Drive pinned (`memo.pdf`) | PIN | ends in `Skip Non-CSV File`, no notification |
| R17 | Mail matched by no parser / no capture | two inline mails | PIN | warning appears in the notification, no txn |
| R18 | Schedule re-match resolves a prior unmatched row | register INV-2026-021 after A | PIN | A-11 becomes `matched`, `rematched=1` |
| R19 | Schedule run with no change → no notification | Schedule right after A | PIN | `Build Notification` returns `[]`, no writes |
| R20 | `NOTIFY_MAX_LINES` exceeded | A + `NOTIFY_MAX_LINES=2` | PIN | "… and N more" |
| R21 | Error Workflow | throwaway workflow | PIN-equivalent (automatic run) / delivery LIVE-N | `error-handler` runs and builds the message |
| R22 | Trigger disabled via `TRIGGERS_ENABLED` | Gmail pinned + `TRIGGERS_ENABLED.gmail=false` | PIN | ends in `Skip Disabled Trigger`, `Parse Mail` not executed, no notification |
| R23 | Non-JPY invoice | A + one USD row in `Read Invoices` | PIN | USD row never matched, `non_jpy_invoice` warning |

---

## 7. Case details (EN)

Notation: `inv[INV-…]` = the `invoices` row, `txn[<txn_id>]` = the `transactions` row; in the `Match Invoices` output these are `_kind=invoice_update` and `_kind=txn_row`. Full cell-level expectations (every `txn_id`, `payer_name_norm`, candidate list) are in `fixtures/README.md` §2–§6; this section states the assertion per case. Headings and reason phrases such as `(fee ¥220 deducted)` are the literal values of `recon_summary` in `shared/messages.en.json` (`reasons.*`, `auto_heading`, `warnings_heading`, `more_items`, `skipped_note`).

- **R01** — Input A row 1 `2026/09/01, 振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ, "33,000"` (also row 4, full-width remitter; row 13, containment `サンプルフーズトウキヨウ` ⊃ alias `サンプルフーズ`). Path: rule 1. Expect `inv[INV-2026-001] = paid, paid_amount 33000, paid_date 2026-09-01, matched_txn_ids 2026-09-01|33000|サンプルシヨウジ|, match_confidence auto, fee_deducted 0`; `txn[2026-09-01|33000|サンプルシヨウジ|] = bank_csv, matched, matched_invoice_ids INV-2026-001, suggested ""`. INV-2026-017 (same customer, other amount) stays untouched. Notification: `■ Auto-matched` → `• 2026-09-01 振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ ¥33,000 → INV-2026-001`. Run: Drive path pinned; check `Route Match Results` outputs 0 and 1. PIN; real cells LIVE-G.
- **R02** — A row 5 `振込 ｻﾄｳ ｹｲｺ, 128,000` (INV-2026-004 has that amount, a different remitter). Rule 2. Expect `inv[INV-2026-004] = paid, 128000, 2026-09-04, amount_only, fee 0`; txn `matched`. Notification under `■ Needs review`: `• 2026-09-04 振込 ｻﾄｳ ｹｲｺ ¥128,000 → INV-2026-004 (amount only, needs review)`; counted in `b`. PIN.
- **R03** — A row 3 `振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ, 54,780` vs INV-2026-002 = 55,000. Rule 3a (difference 220 ∈ FEE_SET, exactly one name match; `(ﾕ` is the trailing-entity token). Expect `inv[INV-2026-002] = paid, paid_amount 54780, paid_date 2026-09-02, fee_deducted 220, match_confidence fee_deducted`; txn `matched`. Notification under Needs review: `… ¥54,780 → INV-2026-002 (fee ¥220 deducted)`. PIN.
- **R04** — A row 6 `振込 ｶ)ﾃｽﾄﾌﾞﾂｻﾝ, 1,234,567` = INV-2026-005 (700,000) + INV-2026-006 (534,567), same customer. Rule 3b with a unique subset sum. Expect two `invoice_update` items: `INV-2026-005 paid 700000` and `INV-2026-006 paid 534567`, both `combined`, both with `matched_txn_ids 2026-09-05|1234567|テストブツサン|`; one txn row `matched_invoice_ids INV-2026-005,INV-2026-006`. `paid_amount` is each invoice's remaining, not the deposit. Notification under Needs review `(combined)`. PIN.
- **R05** — A row 8 `振込 ｻﾝﾌﾟﾙｼｽﾃﾑ(ｶ, 100,000` vs INV-2026-007 = 250,000. Rule 3c. Expect `inv[INV-2026-007] = status partial, paid_amount 100000, paid_date 2026-09-08, auto, fee 0`; txn `matched`. Notification under `■ Auto-matched`: `… → INV-2026-007 (partial, remaining ¥150,000)`; counted in `a`. PIN.
- **R06** — A row 9 `振込 ｵｵﾊﾞ ﾏｻｵ, 44,000`; INV-2026-008 and INV-2026-009 are both 44,000, neither has an alias and neither kanji name matches. Rule 4 `same_amount_multiple`. Expect **no** `invoice_update` for 008/009; `txn[2026-09-09|44000|オオバマサオ|] = ambiguous, matched_invoice_ids "", suggested_invoice_ids INV-2026-008,INV-2026-009`. Notification under `■ Ambiguous`: `… → candidates: INV-2026-008(¥44,000), INV-2026-009(¥44,000)`; counted in `c`. PIN.
- **R07** — Withdrawal rows (A rows 2, 7, 10, 15; B rows 2, 5, 8) produce no txn; `ignored_withdraw` = 4 for A and 3 for B. PIN.
- **R08** — A is cp932 (contains bytes invalid as UTF-8, checked with Python); B starts with `EF BB BF`. Expect every `payer_name_raw` equal to the raw column in `fixtures/README.md` §4/§5 with no U+FFFD, `payer_name_norm` as listed, and no `CSV column not found: "取引日"` for B (BOM stripped from the first header). Decoding is done in the Code node (`TextDecoder`, decided per ASSUMPTIONS A6 / `DESIGN.md` §3.8); also confirm `Extract From File` is absent from `workflow.json`. PIN.
- **R09** — Run A once, then re-pin `Read Transactions` = seed + the 11 `txn_row` items from run 1 (without `_kind`) and run A again. Expect run 2: only the `summary` item (`n=0, skipped_existing=11`), zero `invoice_update`, zero `txn_row`, outputs 0/1 of `Route Match Results` empty, notification `no_transactions` with `(skipped as already processed: 11)`. R09-b: the two mails twice → `skipped_existing=2`. Zero sheet diff after a real second run: LIVE-G. PIN otherwise.
- **R10** — Pin `Watch Gmail Inbox` with `fixtures/mail_pinned.example.json`; `MAIL_PARSERS` = `fixtures/mail_parsers.example.json`. Expect X → `amount 104500, payer_name_raw カ)ダミーデンキ (post-NFKC), txn_date 2026-09-17`; Y → `19800, ササキ ハナコ, 2026-09-18` (body date, not the 09-19 header). Expect `inv[INV-2026-018] = paid, auto, 104500` with `matched_txn_ids 2026-09-17|104500|ダミーデンキ|【サンプル銀行】ご入金のお知らせ(gmail:18f3aabb00000001)` and `inv[INV-2026-019] = paid, auto, 19800` with `…|ササキハナコ|depositnotification-samplebank(gmail:18f3aabb00000002)`; two txn rows `source gmail`, memo = subject + ` (gmail:<id>)`. Notification title `Processed 2 | Auto-matched 2 | Needs review 0 | Unmatched 0`. Real polling and the real Simplify-OFF output shape: LIVE-G (update `DESIGN.md` §3.1 and the pinned example if they differ). PIN otherwise.
- **R11** — Run A with `NOTIFY_CHANNELS` = `["slack"]`, `["email"]`, `["line"]`, `["chatwork"]`, all four, `[]`. PIN: only the configured `Check … Enabled` nodes take the true branch; `[]` runs no notify node and neither `Merge Notification Results` nor `Check Notification Results`; `Build Notification` emits `title / body_text / slack_blocks / line_text / chatwork_text`, and `Notify LINE` / `Notify Chatwork` reference `line_text` / `chatwork_text`. LIVE-N: real delivery per channel; channels without credentials are recorded as attempted (BLOCKERS H2/H6/H7). **R11-b**: with `["slack","email"]` and an invalid `SLACK_CHANNEL`, Slack takes the error output, Email is still sent, `Check Notification Results` reports `channels_ok 1, channels_failed 1` and the run **succeeds** (no Error Workflow); with `["slack"]` and the same invalid value, `Check Notification Results` throws, the run fails and `error-handler` fires (`DESIGN.md` D17).
- **R12** — N/A: bank statements never fill both the deposit and the withdrawal column on one row. Design note: `parseBankCsv` decides on `deposit_col` only (`deposit > 0` → transaction, else ignored); `withdraw_col` is informational. SETUP tells buyers to use `skip_rows` or pre-clean CSVs whose subtotal rows carry a deposit value.
- **R13** — `bank_B_utf8bom.csv` with the B `CSV_MAPPING` (`date_format=yyyyMMdd`; `auto` gives the same). Expect row 1 `0123 カ)ダミーカコウ` → norm `ダミーカコウ` (entity token removed with the leading digits allowed, then `STRIP_LEADING_DIGITS`) → `inv[INV-2026-013] paid auto 41800`; row 3 hiragana `ふりこみ　すずき　いちろう` → `スズキイチロウ` → `INV-2026-014 paid 15400`; row 4 → `INV-2026-015 paid 57200`; row 6 `0045 タカハシ ミキ` → `INV-2026-016 paid 12100`; row 7 `ワタナベケン` → `unmatched`, no candidates; rows 2, 5, 8 ignored. Summary `n=5, a=4, b=0, c=1, ignored_withdraw=3`; dates normalized to `yyyy-MM-dd`. PIN.
- **R14** — (a) `Read Transactions` = `[{ "json": {} }]`, invoices seeded → same result as R01–R06, `skipped_existing=0`. (b) both sheets `[{ "json": {} }]` → all 11 txns `unmatched` with empty candidates, no `invoice_update`, `c=11`. PIN; header-only sheets LIVE-G.
- **R15** — `bank_A_sjis_skip1.csv` (A with one title line before the header). `skip_rows=1` → the same 11 `txn_id`s as A (`_row` one larger), `ignored_withdraw=4`. `skip_rows=0` → `Parse Bank CSV` fails with `CSV column not found: "日付"` instead of silently yielding zero rows. PIN.
- **R16** — Pin `Watch Drive Folder` with `{ "id": "fixture-pdf", "name": "memo.pdf", "mimeType": "application/pdf" }`. Expect `Check File Is CSV` false → `Skip Non-CSV File`, nothing downstream, successful execution, no notification. PIN.
- **R17** — (a) a mail from `someone@example.org` with subject `会議のご案内` → `no_parser_matched`; (b) a mail from `サンプル銀行 <notice@example.jp>` with subject `【サンプル銀行】ご入金のお知らせ` and body `本日の入金はありません。` → `parser_no_capture` (parser bankX). Expect `Collect Transactions` with `txns=[]` and 2 warnings, `Match Invoices` summary only (`n=0`), no writes, notification titled `No new transactions` with a `■ Warnings` section listing both. PIN.
- **R18** — State after A (A-11 `2026-09-11|66000|ミホンシヨウカイ|` is `unmatched`). Add `INV-2026-021` (株式会社見本商会, alias `カ)ミホンシヨウカイ,ミホンシヨウカイ`, 66000, due 2026-10-15, unpaid) to the pinned invoices and start from `Run Daily Rematch`. Expect `inv[INV-2026-021] = paid, auto, 66000, paid_date 2026-09-11, matched_txn_ids 2026-09-11|66000|ミホンシヨウカイ|`; the A-11 txn row rewritten as `matched, INV-2026-021` keeping its original `imported_at`; A-9/A-12/A-14 not rewritten (unchanged candidates); `rematched=1`; notification sent with `• 2026-09-11 振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ ¥66,000 → INV-2026-021` under Auto-matched. Note for P2: the pseudocode also counts re-evaluated existing rows in `a`/`c`, so the title reads `Processed 0 | Auto-matched 1 | Needs review 0 | Unmatched 3`; decide and record (see T07). PIN.
- **R19** — Same state as R18 but before registering INV-2026-021; start from `Run Daily Rematch`. Expect summary only (`rematched=0, n=0`), zero `txn_row`, `Build Notification` returns `[]`, no notify node runs. R19-b: two consecutive schedule runs give identical results. PIN.
- **R20** — A with `NOTIFY_MAX_LINES=2`. Expect Needs review 2 lines + `… and 1 more`, Ambiguous 1 line, Unmatched 2 + `… and 1 more`, Auto-matched 2 + `… and 2 more`; every Slack section text under 3,000 characters. PIN.
- **R21** — Error Trigger does not fire on manual runs and pinned data is ignored in production runs, so use a throwaway workflow `[P3] Throw for error-handler` (Schedule every minute → Code `throw new Error('P3 error-handler check')`) with its Error workflow set to `error-handler` (`NOTIFY_CHANNELS: []`). Expect an `error-handler` execution within a minute whose `Build Error Message` output has `title = [n8n error] [P3] Throw for error-handler` and `body_text` containing the failed node name and the message. Deactivate and delete the throwaway afterwards. The real scenario (activate the main workflow, break `SHEET_ID`, drop a CSV in Drive) is LIVE-G; delivery is LIVE-N.
- **R22** — Same Gmail pinned data as R10 with `TRIGGERS_ENABLED = { "drive": true, "gmail": false, "schedule": true }`, started from `Watch Gmail Inbox`. Expect nothing on the `gmail` output of `Route by Source`; the fallback (Extra Output) runs `Skip Disabled Trigger`; `Parse Mail` and everything after it do not execute; the run succeeds with no notification and no writes. R22-b: `gmail: true` restores the R10 result. R22-c: an unknown `SOURCE` (e.g. `"Manual"`) also ends in `Skip Disabled Trigger`. Note: the trigger node keeps polling even when disabled here (`DESIGN.md` D26); confirm in LIVE-G. PIN.
- **R23** — Run A with `Read Invoices` pinned to the seed plus one row `INV-2026-022, C-019, Sample Overseas LLC, サンプルオーバーシーズ, overseas@example.com, 128000, USD, 2026-09-01, 2026-09-30, unpaid, 0, …` (same amount as A-5 so that, without the currency check, it would enter rules 2/4). Expect the same result as R01–R06 (A-5 still matches INV-2026-004 as `amount_only`; INV-2026-022 appears neither in `byAmt` nor among candidates), no `invoice_update` for INV-2026-022, and one summary warning `{ type: non_jpy_invoice, invoice_id: INV-2026-022, currency: USD }` rendered as `■ Warnings` / `• non_jpy_invoice INV-2026-022 USD` at the end of the notification. R23-b: the same pinned data started from `Run Daily Rematch` yields `rematched=0` and `Build Notification` returns `[]` (a non-JPY warning alone never triggers the daily notification; `DESIGN.md` D12/D28). PIN.

---

## 8. Decisions (EN mirror of §4, for `ASSUMPTIONS.md`)

- **T01 Extra fixtures**: besides the four required ones, ship `transactions.seed.csv` (one matched row, so `Read Transactions` is non-empty), `bank_A_sjis_skip1.csv` (proves `skip_rows`), and `mail_parsers.example.json` / `mail_pinned.example.json` / `csv_mapping.examples.json` (drop-in pinned data and Config values for P3). Reason: reproducible, fast P3; also useful to buyers as configuration examples.
- **T02 Expectations assume "seed state, one input"**: target invoices of A, B and the mails are disjoint so match results are order-independent, but `suggested_invoice_ids` depends on what is still open; P3 resets the sheets before each file.
- **T03 Token order in name normalization**: `DESIGN.md` §6.6 is now two passes ("anywhere" tokens first, then the anchored `X)` / `(X` tokens; 2026-09-23, `ASSUMPTIONS.md` A16). The expected `payer_name_norm` values in `fixtures/README.md` §4–§6 were verified in Node with the fixed function for all 14 names; a single pass would turn `振込 ｶ)…` into `カ…` and change `txn_id`.
- **T04 Mail `payer_name_raw` is post-NFKC** as the pseudocode dictates (`ｶ)ﾀﾞﾐｰﾃﾞﾝｷ` → `カ)ダミーデンキ`); the mismatch with the CSV path is accepted and documented in SETUP.
- **T05 Parser Y finalized for a table layout**: bankY uses `Amount\s+…` / `Remitter\s+…` / `Transaction Date\s+…` to match fixture Y and `DESIGN.md` §4 now carries the same values (source of truth: `fixtures/mail_parsers.example.json`, `ASSUMPTIONS.md` A17); the old `Amount[：:]` form was verified in Node to yield `parser_no_capture` for Y. bankX's `date_regex` requires a `日付` label to avoid capturing account numbers.
- **T06 Trap rows for paid and cancelled invoices**: A-11 and A-12 carry the exact name and amount of INV-2026-010 (paid) and INV-2026-011 (cancelled) and must end `unmatched`, proving that non-open invoices are excluded from matching and candidates.
- **T07 Schedule-run title counters**: the pseudocode counts re-evaluated existing rows in `a`/`c`; P2 decides whether to count them only in `rematched` or to add a `再突合 / re-matched {rematched}` figure to the title.
- **T08 Blank lines in the notification body**: `DESIGN.md` §6.8 now uses `[title, ...sections].join('\n\n')`, giving one blank line between the title and each section (matches §3); the number of blank lines is still not asserted.
- **T09 `imported_at` format**: unified on ISO 8601 with the JST offset (`yyyy-MM-ddTHH:mm:ss+09:00`, the shared schema's `datetime`); `DESIGN.md` §6.7 `nowStr` and `fixtures/transactions.seed.csv` were changed accordingly (`DESIGN.md` D30). CASES asserts the format only.
- **T10 `memo_norm` definition**: `shared/sheets-schema.md` was aligned to the `DESIGN.md` definition (NFKC → whitespace removed → `|`→`/` → lowercased, punctuation kept; `DESIGN.md` D30), so the mail `txn_id`s keep `【】()` as expected.
- **T11 R12 is N/A**: no bank CSV fills both columns on one row; the parser decides on `deposit_col` only.
- **T12 Non-JPY invoices**: `DESIGN.md` §6.7 now excludes `currency ≠ JPY` rows with a `non_jpy_invoice` warning and R23 covers it. The seed stays all-JPY (a USD row in the seed would change every `warnings=[]` expectation for A, B and M), so R23 adds the row to the pinned data only.
- **T13 `TRIGGERS_ENABLED` (R22)**: the spec's "three triggers, on/off in Config" had no Config key in `DESIGN.md`; D26 adds it and R22 verifies the `gmail=false` path and an unknown `SOURCE`. Polling continues for a disabled trigger; confirmed in LIVE-G.
- **T14 Partial notification failure (R11-b)**: notify nodes use Continue (using error output) and only `Check Notification Results` throws when every attempted channel failed (`DESIGN.md` D17); R11 gained the partial-failure and all-failed sub-cases.
