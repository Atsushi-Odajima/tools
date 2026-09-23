# 共有 Google Sheets スキーマ / Shared Google Sheets Schema

> JA: 決済業務 n8n テンプレート 01〜04 が読み書きする Google スプレッドシートの定義です。仕様書 `CLAUDE.md` §5 を原本とし、買い手向けの作成手順と、テンプレ実装者向けの型・書式・冪等キーをまとめています。列名は英語固定（n8n の式が列名で参照するため）。
> EN: Definition of the Google Spreadsheet that payment-ops n8n templates 01–04 read and write. `CLAUDE.md` §5 is the source of truth; this file adds buyer-facing creation steps and the types, formats and idempotency keys template builders must follow. Column names are fixed English identifiers (n8n expressions reference them by name).

| ファイル / File | 用途 / Purpose | 使うテンプレ / Used by |
|---|---|---|
| `shared/invoices.template.csv` | 請求一覧 / Invoice list | 01, 03 |
| `shared/transactions.template.csv` | 入金明細（消込台帳）/ Deposit ledger | 01 |
| `shared/reminders_log.template.csv` | 督促送信ログ / Reminder log | 03 |
| `shared/events_ledger.template.csv` | 決済イベント記帳台帳 / Payment-event booking ledger | 02 |
| `shared/disputes.template.csv` | 返金・チャージバック台帳 / Refund & dispute ledger | 04 |

各 CSV は UTF-8（BOM なし）、1 行目がヘッダー、2〜4 行目が架空のサンプルです。サンプルは互いに整合しています（例：`transactions` の 1 行目は `invoices` の INV-2026-0001 を消し込んだ明細）。
Each CSV is UTF-8 without BOM, row 1 is the header, rows 2–4 are fictional samples. The samples are mutually consistent (e.g. row 1 of `transactions` is the deposit that settled INV-2026-0001 in `invoices`).

---

# スプレッドシートの作り方 / How to create the spreadsheet

## JA

**所要時間の目安：5 分。** 4 本のテンプレは同じ 1 冊のスプレッドシートを使います（使わないテンプレのシートも作っておいて構いません）。

1. Google ドライブで **スプレッドシートを新規作成** します。名前は自由です（例：`payment-ops`）。
2. メニュー **ファイル → インポート → アップロード** で `invoices.template.csv` を選びます。インポート設定は次のとおりにします。
   - インポート場所：**新しいシートを挿入する**
   - 区切り文字の種類：**自動的に検出する**（カンマ）
   - **「テキストを数値、日付、数式に変換する」のチェックを外す**（日付や請求番号が勝手に変換されるのを防ぎます）
3. 追加されたシートのタブ名（`invoices.template` などになっています）を **`invoices`** に変更します。半角小文字・空白なし・完全一致で入力してください。
4. 残りの 4 ファイルも同じ手順で取り込み、タブ名をそれぞれ **`transactions`／`reminders_log`／`events_ledger`／`disputes`** にします。
5. 各シートで **全選択（Ctrl+A）→ 表示形式 → 数字 → 書式なしテキスト** を設定します。テンプレは数値・日付を文字列として読み書きするため、この設定にしておくと Google 側の自動書式で `2026-09-10` が `2026/09/10` に化けるといった事故を防げます。
6. **1 行目（列名）は変更・削除・並び替えをしないでください。** 列名が 1 文字でも違うとテンプレは動きません。右側に独自の列を追加するのは構いません。
7. 各シートのサンプル 3 行（2〜4 行目）は、最初の動作確認に使ったあと **本番運用前に削除** してください。
8. ブラウザーのアドレスバー `https://docs.google.com/spreadsheets/d/<ここが ID>/edit` の **ID** をコピーし、各ワークフローの `Config` ノードの `SHEET_ID` に貼ります。シート名は既定でこの文書と同じ値が `Config` に入っています（`SHEET_INVOICES` など。変えた場合はここを直します）。
9. n8n の Google Sheets Credential に使う Google アカウントに、このスプレッドシートの **編集権限** を付けます。
10. 最初からある空の「シート1」は削除して構いません。

**個人情報について**：`customer_name`／`customer_email`／`payer_name_alias` は氏名・メールアドレスです。共有範囲を最小限にし、不要になった行は削除してください。テンプレは元の銀行 CSV や通知メールをシートに保存しません。

## EN

**Time required: about 5 minutes.** All four templates share one spreadsheet (creating the sheets for templates you do not use is harmless).

1. In Google Drive, **create a new Google Spreadsheet**. Any name is fine (e.g. `payment-ops`).
2. **File → Import → Upload** and choose `invoices.template.csv`. Use these import settings:
   - Import location: **Insert new sheet(s)**
   - Separator type: **Detect automatically** (comma)
   - **Uncheck "Convert text to numbers, dates, and formulas"** (prevents dates and invoice numbers from being silently converted)
3. Rename the new sheet tab (it will be called something like `invoices.template`) to exactly **`invoices`** — lowercase, no spaces, exact match.
4. Import the other four files the same way and name the tabs **`transactions` / `reminders_log` / `events_ledger` / `disputes`**.
5. On every sheet, **Select all (Ctrl+A) → Format → Number → Plain text**. The templates read and write numbers and dates as strings; plain-text formatting stops Google's automatic formatting from turning `2026-09-10` into `2026/09/10` or similar.
6. **Never rename, delete or reorder row 1 (the column names).** A single-character difference breaks the templates. Adding your own columns to the right is fine.
7. The three sample rows (rows 2–4) on each sheet are for your first test run; **delete them before going live**.
8. Copy the **ID** from the browser address bar `https://docs.google.com/spreadsheets/d/<this is the ID>/edit` and paste it into `SHEET_ID` in each workflow's `Config` node. The sheet names in `Config` (`SHEET_INVOICES` etc.) already default to the names above; change them only if you renamed a tab.
9. Give the Google account used by your n8n Google Sheets credential **edit access** to the spreadsheet.
10. The empty default "Sheet1" can be deleted.

**Personal data**: `customer_name`, `customer_email` and `payer_name_alias` contain names and email addresses. Keep sharing minimal and delete rows you no longer need. The templates never store the original bank CSV or notification email in the sheet.

---

# 共通ルール / Common rules

## JA

### 型と書式
| 型 | 書き方 | 例 |
|---|---|---|
| text | 文字列。前後の空白は無視される | `INV-2026-0001` |
| int | 整数（円）。カンマ・`¥`・`円`・全角数字は書かない。テンプレは読み取り時に除去して `parseInt` する | `33000` |
| number | 小数を含みうる数値（JPY 以外の通貨、為替レート） | `49.99`, `150.12` |
| date | `yyyy-MM-dd`（JST の暦日） | `2026-09-10` |
| datetime | ISO 8601、秒まで、JST オフセット付き `yyyy-MM-ddTHH:mm:ss+09:00` | `2026-09-16T10:00:08+09:00` |
| bool | `TRUE` / `FALSE`（大文字）。空欄は `FALSE` 扱い | `TRUE` |
| enum | 定義された小文字の値のみ | `unpaid` |

- 空欄は「未設定」。テンプレは空欄と `0` を区別する列（`paid_date` と `paid_amount` など）を持つため、数値列で「なし」を表すときは `0`、日付・文字列列では空欄にする。
- カンマ区切り列（`payer_name_alias`, `matched_txn_ids`, `matched_invoice_ids`, `suggested_invoice_ids`）は半角カンマ `,` で区切り、要素の前後の空白は無視する。
- ワークフローがシートへ書く際は Google Sheets ノードの **Cell Format = Let n8n format** を使い、文字列を文字列のまま保存する。読む際は **Output Formatting = Values (unformatted)** を既定とし、数値・日付は必ず文字列から自前でパースする（買い手が書式設定を変えても壊れないようにするため）。

### 冪等キー（§4.4）
| テンプレ | 台帳シート | キー | 処理前の確認 |
|---|---|---|---|
| 01 入金消込 | `transactions` | `txn_id` | `txn_id` が既にあれば skip |
| 02 Webhook 会計 | `events_ledger` | `event_id` | `event_id` が既にあれば 200 を返して終了 |
| 03 未入金リマインド | `reminders_log` | `(invoice_id, stage)` | 同じ組が既にあれば送らない |
| 04 返金・CB | `disputes` | `(source, object_id, event_type)` | `record_id = source\|object_id` の行を読み、`notes` に同じ `event_type` の処理記録が既にあれば skip |

同じ入力を 2 回流しても、これらの台帳と `invoices` に差分が出ないことを各テンプレの受け入れテストで確認する。

### `txn_id` の形式（テンプレ 01）
```
${yyyy-MM-dd}|${amount}|${payer_norm}|${memo_norm}
例: 2026-09-10|32780|サンプルシヨウジ|振込
```
- `yyyy-MM-dd`：入金日（JST）
- `amount`：整数円（カンマ・記号なし）
- `payer_norm`：`Normalize Payer` の出力（NFKC → ひらがな→カタカナ → 法人格トークン除去 → 空白・記号除去 → 先頭の数字列除去）
- `memo_norm`：摘要を NFKC 正規化し、空白と記号を除いたもの。摘要が無い場合は空文字（末尾の `|` は残す）
- 区切りは半角 `|`。名義・摘要に `|` が含まれる場合は正規化で除去される

### Config で持つシート設定
`SHEET_ID`（スプレッドシート ID）、`SHEET_INVOICES`、`SHEET_TRANSACTIONS`、`SHEET_REMINDERS_LOG`、`SHEET_EVENTS_LEDGER`、`SHEET_DISPUTES`（各シート名、既定はこの文書の値）。Google Sheets ノードの Sheet は **By Name** でこれらを参照する。

## EN

### Types and formats
| Type | How to write it | Example |
|---|---|---|
| text | String; surrounding whitespace is ignored | `INV-2026-0001` |
| int | Integer yen. No commas, `¥`, `円` or full-width digits; the templates strip them and `parseInt` on read anyway | `33000` |
| number | Numeric value that may have decimals (non-JPY currencies, FX rates) | `49.99`, `150.12` |
| date | `yyyy-MM-dd` (calendar date in JST) | `2026-09-10` |
| datetime | ISO 8601 to the second with the JST offset: `yyyy-MM-ddTHH:mm:ss+09:00` | `2026-09-16T10:00:08+09:00` |
| bool | `TRUE` / `FALSE` (uppercase); blank is treated as `FALSE` | `TRUE` |
| enum | Only the listed lowercase values | `unpaid` |

- Blank means "not set". Some column pairs distinguish blank from `0` (e.g. `paid_date` vs `paid_amount`), so write `0` for "none" in numeric columns and leave date/text columns blank.
- Comma-separated columns (`payer_name_alias`, `matched_txn_ids`, `matched_invoice_ids`, `suggested_invoice_ids`) use a half-width comma `,`; whitespace around elements is ignored.
- When a workflow writes to a sheet it uses the Google Sheets node option **Cell Format = Let n8n format** so strings stay strings. When reading, the default is **Output Formatting = Values (unformatted)** and numbers/dates are always parsed from strings by the workflow itself, so a buyer changing cell formatting cannot break the templates.

### Idempotency keys (§4.4)
| Template | Ledger sheet | Key | Check before processing |
|---|---|---|---|
| 01 Bank Reconciliation | `transactions` | `txn_id` | Skip if `txn_id` already exists |
| 02 Webhook → Accounting | `events_ledger` | `event_id` | If `event_id` exists, respond 200 and stop |
| 03 Unpaid Reminder | `reminders_log` | `(invoice_id, stage)` | Do not send if the pair exists |
| 04 Refund & Chargeback | `disputes` | `(source, object_id, event_type)` | Read the row `record_id = source\|object_id`; skip if `notes` already records the same `event_type` |

Each template's acceptance tests prove that running the same input twice leaves these ledgers and `invoices` unchanged.

### `txn_id` format (Template 01)
```
${yyyy-MM-dd}|${amount}|${payer_norm}|${memo_norm}
e.g. 2026-09-10|32780|サンプルシヨウジ|振込
```
- `yyyy-MM-dd`: deposit date (JST)
- `amount`: integer yen, no commas or symbols
- `payer_norm`: output of `Normalize Payer` (NFKC → hiragana→katakana → strip legal-entity tokens → strip spaces/punctuation → strip leading digit run)
- `memo_norm`: the memo after NFKC normalization with whitespace and punctuation removed; empty string when there is no memo (the trailing `|` stays)
- Separator is a half-width `|`; any `|` inside a name or memo is removed by normalization

### Sheet settings held in Config
`SHEET_ID` (spreadsheet ID), `SHEET_INVOICES`, `SHEET_TRANSACTIONS`, `SHEET_REMINDERS_LOG`, `SHEET_EVENTS_LEDGER`, `SHEET_DISPUTES` (sheet names, defaulting to the values in this document). The Google Sheets node selects the sheet **By Name** from these.

---

# invoices

## JA

請求一覧。**買い手が請求を登録し、01 が入金状況を、03 が督促状況を更新する。** 01 と 03 が共有する。

| 列 | 型 | 必須 | 説明 | 読み書き |
|---|---|---|---|---|
| invoice_id | text（一意） | 必須 | 請求番号。`Append or Update` の一致キー。重複不可 | 買い手 W／01 R／03 R |
| customer_id | text | 任意 | 顧客 ID。03 が同一顧客の複数請求を 1 通にまとめる際のグループキー（空なら `customer_email`） | 買い手 W／03 R |
| customer_name | text | 必須 | 請求先名（漢字可）。01 の名義照合と 03 の宛名に使う | 買い手 W／01 R／03 R |
| payer_name_alias | text（カンマ区切り） | **必須級** | **振込名義（カナ）をカンマ区切りで。** 銀行の振込名義はカタカナで届くため、漢字の請求先名だけでは照合できない。例：`カ）サンプルシヨウジ,サンプルシヨウジ`。空だと自動消込率が大きく落ちる | 買い手 W／01 R |
| customer_email | text | 03 で必須 | 督促メールの送信先 | 買い手 W／03 R |
| amount | int | 必須 | 税込請求額（円） | 買い手 W／01 R／03 R |
| currency | text | 必須 | 既定 `JPY`。01・03 は JPY のみ対象。JPY 以外の行は処理せず通知で警告する | 買い手 W／01 R／03 R |
| issue_date | date | 任意 | 請求日 `yyyy-MM-dd` | 買い手 W／03 R |
| due_date | date | 必須 | 支払期限 `yyyy-MM-dd`。03 のステージ判定基準 | 買い手 W／03 R |
| status | enum | 必須 | `unpaid`／`partial`／`paid`／`overpaid`／`cancelled`／`escalated`。買い手は新規登録時に `unpaid` を入れる。01 が `partial`／`paid`／`overpaid` に、03 が stage 3 送付後に `escalated` に更新。`cancelled` は買い手が手動で入れると 01・03 の対象外になる | 買い手 W／01 R W／03 R W |
| paid_amount | int | 必須（既定 `0`） | 累計入金額（実際に着金した額）。残額 = `amount − paid_amount` | 01 W／03 R |
| paid_date | date | 任意 | 最終入金日 | 01 W |
| matched_txn_ids | text（カンマ区切り） | 任意 | 消し込んだ `transactions.txn_id` | 01 W |
| match_confidence | enum | 任意 | `auto`／`amount_only`／`fee_deducted`／`combined`／`manual`。01 が判定根拠を書く。買い手が手で消し込んだときは `manual` | 01 W／買い手 W |
| fee_deducted | int | 任意（既定 `0`） | 先方負担の振込手数料差額。`paid_amount + fee_deducted = amount` で `paid` になる | 01 W |
| remind_stage | int | 必須（既定 `0`） | 送付済みの最終ステージ 0〜3。03 が更新 | 03 W／03 R |
| last_reminded_at | datetime | 任意 | 最終督促日時 | 03 W |
| promised_date | date | 任意 | 顧客から聞き取った入金予定日。**未来日の間は督促を止める** | 買い手 W／03 R |
| do_not_remind | bool | 任意（既定 `FALSE`） | `TRUE` で督促対象外 | 買い手 W／03 R |
| notes | text | 任意 | 自由記入。テンプレは書き換えない | 買い手 W |

**enum**
- `status`: `unpaid` 未入金 / `partial` 一部入金 / `paid` 入金済 / `overpaid` 過入金（要確認） / `cancelled` 取消 / `escalated` 最終督促済み（以後は自動送信しない）
- `match_confidence`: `auto` 名義と金額が一致 / `amount_only` 金額のみ一致（要確認） / `fee_deducted` 手数料差引で一致 / `combined` 複数請求の合算で一致 / `manual` 人が消し込んだ

## EN

Invoice list. **The buyer registers invoices; 01 updates payment state, 03 updates reminder state.** Shared by 01 and 03.

| Column | Type | Required | Description | Read/Write by |
|---|---|---|---|---|
| invoice_id | text (unique) | required | Invoice number. Match key for `Append or Update`. Must be unique | buyer W / 01 R / 03 R |
| customer_id | text | optional | Customer ID. 03 groups several invoices of one customer into one email by this key (falls back to `customer_email`) | buyer W / 03 R |
| customer_name | text | required | Billing name (kanji allowed). Used by 01 for name matching and by 03 for the salutation | buyer W / 01 R / 03 R |
| payer_name_alias | text (comma-separated) | **effectively required** | **Remitter names in katakana, comma-separated.** Japanese bank transfers arrive with the remitter name in katakana, so a kanji billing name alone cannot be matched. Example: `カ）サンプルシヨウジ,サンプルシヨウジ`. Leaving it blank sharply lowers the auto-match rate | buyer W / 01 R |
| customer_email | text | required for 03 | Recipient of reminder emails | buyer W / 03 R |
| amount | int | required | Invoiced amount incl. tax (yen) | buyer W / 01 R / 03 R |
| currency | text | required | Default `JPY`. 01 and 03 handle JPY only; non-JPY rows are skipped with a warning in the notification | buyer W / 01 R / 03 R |
| issue_date | date | optional | Issue date `yyyy-MM-dd` | buyer W / 03 R |
| due_date | date | required | Due date `yyyy-MM-dd`; basis of 03's stage logic | buyer W / 03 R |
| status | enum | required | `unpaid` / `partial` / `paid` / `overpaid` / `cancelled` / `escalated`. The buyer enters `unpaid` on registration. 01 sets `partial` / `paid` / `overpaid`; 03 sets `escalated` after stage 3. `cancelled` is set manually and removes the row from 01 and 03 | buyer W / 01 R W / 03 R W |
| paid_amount | int | required (default `0`) | Cumulative amount actually received. Remaining = `amount − paid_amount` | 01 W / 03 R |
| paid_date | date | optional | Latest receipt date | 01 W |
| matched_txn_ids | text (comma-separated) | optional | `transactions.txn_id` values settled against this invoice | 01 W |
| match_confidence | enum | optional | `auto` / `amount_only` / `fee_deducted` / `combined` / `manual`. 01 records why it matched; `manual` when a human reconciled it | 01 W / buyer W |
| fee_deducted | int | optional (default `0`) | Transfer fee deducted by the payer. The row becomes `paid` when `paid_amount + fee_deducted = amount` | 01 W |
| remind_stage | int | required (default `0`) | Highest reminder stage sent so far, 0–3. Updated by 03 | 03 W / 03 R |
| last_reminded_at | datetime | optional | Time of the last reminder | 03 W |
| promised_date | date | optional | Payment date promised by the customer. **Reminders pause while it is in the future** | buyer W / 03 R |
| do_not_remind | bool | optional (default `FALSE`) | `TRUE` excludes the invoice from reminders | buyer W / 03 R |
| notes | text | optional | Free text. Never modified by the templates | buyer W |

**Enums**
- `status`: `unpaid` / `partial` partially paid / `paid` / `overpaid` (needs review) / `cancelled` / `escalated` final reminder sent, no further automatic sending
- `match_confidence`: `auto` name and amount matched / `amount_only` amount matched only (needs review) / `fee_deducted` matched after a transfer-fee deduction / `combined` one deposit settled several invoices / `manual` reconciled by a human

---

# transactions

## JA

入金明細の台帳。**01 が銀行 CSV・入金通知メールから取り込んだ全ての入金を追記する。** 買い手は手入力（`source=manual`）以外は編集しない。`txn_id` の重複チェックで二重取込を防ぎ、`unmatched`／`ambiguous` の行は毎朝の再突合の対象になる。

| 列 | 型 | 必須 | 説明 | 読み書き |
|---|---|---|---|---|
| txn_id | text（一意） | 必須 | `${yyyy-MM-dd}\|${amount}\|${payer_norm}\|${memo_norm}`（「共通ルール」参照）。冪等キー | 01 W／01 R |
| source | enum | 必須 | `bank_csv`／`gmail`／`manual` | 01 W／買い手 W（manual） |
| txn_date | date | 必須 | 入金日 `yyyy-MM-dd` | 01 W |
| payer_name_raw | text | 必須 | 銀行から届いた名義そのまま（半角カナ・法人格記号を含む） | 01 W |
| payer_name_norm | text | 必須 | `Normalize Payer` の出力 | 01 W／01 R |
| amount | int | 必須 | 入金額（円）。出金行は取り込まない | 01 W／01 R |
| memo | text | 任意 | 摘要（銀行 CSV の備考、メールの件名など） | 01 W |
| matched_invoice_ids | text（カンマ区切り） | 任意 | 消し込んだ `invoices.invoice_id`。`combined` のとき複数 | 01 W |
| status | enum | 必須 | `matched`／`unmatched`／`ambiguous`／`ignored` | 01 W／01 R／買い手 W（ignored） |
| suggested_invoice_ids | text（カンマ区切り） | 任意 | `unmatched`／`ambiguous` のときの候補（上位 3 件）。人が確認する材料 | 01 W |
| imported_at | datetime | 必須 | 取込日時 | 01 W |

**enum**
- `source`: `bank_csv` 銀行 CSV / `gmail` 入金通知メール / `manual` 手入力
- `status`: `matched` 消込済 / `unmatched` 該当なし（再突合の対象） / `ambiguous` 候補が複数で自動確定しない（再突合の対象） / `ignored` 買い手が「対象外」と印を付けた行（再突合しない）

## EN

Deposit ledger. **01 appends every deposit imported from bank CSVs and payment-notification emails.** The buyer edits nothing except manual entries (`source=manual`). Duplicate `txn_id` values are rejected to prevent double import, and `unmatched` / `ambiguous` rows are re-matched every morning.

| Column | Type | Required | Description | Read/Write by |
|---|---|---|---|---|
| txn_id | text (unique) | required | `${yyyy-MM-dd}\|${amount}\|${payer_norm}\|${memo_norm}` (see "Common rules"). Idempotency key | 01 W / 01 R |
| source | enum | required | `bank_csv` / `gmail` / `manual` | 01 W / buyer W (manual) |
| txn_date | date | required | Deposit date `yyyy-MM-dd` | 01 W |
| payer_name_raw | text | required | Remitter name exactly as delivered by the bank (half-width katakana, entity abbreviations included) | 01 W |
| payer_name_norm | text | required | Output of `Normalize Payer` | 01 W / 01 R |
| amount | int | required | Deposit amount (yen). Withdrawal rows are never imported | 01 W / 01 R |
| memo | text | optional | Memo (bank CSV remark, email subject, etc.) | 01 W |
| matched_invoice_ids | text (comma-separated) | optional | `invoices.invoice_id` values settled by this deposit; several when `combined` | 01 W |
| status | enum | required | `matched` / `unmatched` / `ambiguous` / `ignored` | 01 W / 01 R / buyer W (ignored) |
| suggested_invoice_ids | text (comma-separated) | optional | Up to 3 candidate invoices for `unmatched` / `ambiguous` rows, for human review | 01 W |
| imported_at | datetime | required | Import time | 01 W |

**Enums**
- `source`: `bank_csv` bank CSV / `gmail` payment-notification email / `manual` entered by hand
- `status`: `matched` reconciled / `unmatched` no candidate (re-matched daily) / `ambiguous` several candidates, not auto-confirmed (re-matched daily) / `ignored` marked by the buyer as out of scope (never re-matched)

---

# reminders_log

## JA

督促の送信ログ。**03 が下書き作成または送信のたびに 1 行追記する（追記のみ）。** `(invoice_id, stage)` の組が既にあれば同じステージは二度と送らない。同一顧客の複数請求を 1 通にまとめた場合は、請求ごとに 1 行ずつ書き、`gmail_message_id` を共有する。

| 列 | 型 | 必須 | 説明 | 読み書き |
|---|---|---|---|---|
| invoice_id | text | 必須 | 対象の `invoices.invoice_id` | 03 W／03 R |
| stage | int | 必須 | 0〜3（0 = 事前案内、1〜3 = 督促） | 03 W／03 R |
| mode | enum | 必須 | `draft`（Gmail 下書き作成）／`sent`（送信済み） | 03 W |
| channel | text | 必須 | v1 は `gmail` 固定（将来の拡張用） | 03 W |
| to | text | 必須 | 送信先メールアドレス | 03 W |
| subject | text | 必須 | 件名（付録 B の文面） | 03 W |
| sent_at | datetime | 必須 | 下書き作成または送信の日時 | 03 W |
| gmail_message_id | text | 任意 | Gmail のメッセージ ID（`draft` のときは下書きのメッセージ ID、`sent` のときは送信済みメッセージの ID）。`owner_only` モードでは空 | 03 W |

**enum**
- `mode`: `draft` 下書きを作成した / `sent` 顧客へ送信した

## EN

Reminder log. **03 appends one row every time it creates a draft or sends an email (append-only).** If the pair `(invoice_id, stage)` already exists, that stage is never sent again. When several invoices of one customer are combined into one email, one row is written per invoice and they share the same `gmail_message_id`.

| Column | Type | Required | Description | Read/Write by |
|---|---|---|---|---|
| invoice_id | text | required | The `invoices.invoice_id` concerned | 03 W / 03 R |
| stage | int | required | 0–3 (0 = advance notice, 1–3 = reminders) | 03 W / 03 R |
| mode | enum | required | `draft` (Gmail draft created) / `sent` (email sent) | 03 W |
| channel | text | required | Fixed to `gmail` in v1 (reserved for future channels) | 03 W |
| to | text | required | Recipient email address | 03 W |
| subject | text | required | Subject line (Appendix B wording) | 03 W |
| sent_at | datetime | required | Time the draft was created or the email sent | 03 W |
| gmail_message_id | text | optional | Gmail message ID (the draft's message ID for `draft`, the sent message's ID for `sent`). Blank in `owner_only` mode | 03 W |

**Enums**
- `mode`: `draft` a draft was created / `sent` the email was sent to the customer

---

# events_ledger

## JA

決済イベントの記帳台帳。**02 が Stripe／PayPal から受けたイベントを 1 行ずつ追記し、会計連携の結果を記録する。** `event_id` が既にあれば再送とみなして処理しない。`booking_status=error` の行は毎時の再試行対象。

| 列 | 型 | 必須 | 説明 | 読み書き |
|---|---|---|---|---|
| event_id | text（一意） | 必須 | PSP のイベント ID（Stripe `evt_…`、PayPal の Webhook イベント ID）。冪等キー | 02 W／02 R |
| source | enum | 必須 | `stripe`／`paypal` | 02 W |
| event_type | text | 必須 | PSP のイベント種別そのまま（`charge.succeeded`、`PAYMENT.CAPTURE.COMPLETED` など） | 02 W |
| object_id | text | 必須 | 対象オブジェクトの ID（charge／refund／dispute／payout／capture の ID） | 02 W |
| occurred_at | datetime | 必須 | イベント発生日時（PSP の UNIX 秒を JST に変換） | 02 W |
| currency | text | 必須 | ISO 4217（`JPY`, `USD` …） | 02 W |
| gross | number | 必須 | 決済総額（通貨の主単位。JPY は整数、USD は `49.99` のように小数） | 02 W |
| fee | number | 必須 | PSP 手数料（同上） | 02 W |
| net | number | 必須 | `gross − fee` | 02 W |
| gross_jpy | int | 必須 | 円換算の総額（JPY ならそのまま） | 02 W |
| fee_jpy | int | 必須 | 円換算の手数料 | 02 W |
| net_jpy | int | 必須 | `gross_jpy − fee_jpy`（換算後に差し引くので端数が合う） | 02 W |
| fx_rate | number | 必須 | 円換算レート。JPY は `1`。Stripe は `balance_transaction.exchange_rate` | 02 W |
| customer_ref | text | 任意 | 顧客参照（Stripe customer ID、メールアドレス、PayPal payer ID 等） | 02 W |
| booking_status | enum | 必須 | `dry_run`／`booked`／`skipped`／`error` | 02 W／02 R |
| accounting_ref | text | 任意 | 会計側の参照。`freee:deal:<ID>`、`csv:<ファイル名>` など | 02 W |
| error_message | text | 任意 | `error` のときの理由と再試行回数 | 02 W |

**enum**
- `source`: `stripe` / `paypal`
- `booking_status`: `dry_run` シートに書いただけ（既定モード） / `booked` 会計へ記帳済み / `skipped` 記帳対象外（返金アラートのみ等） / `error` 会計 API 失敗（再試行対象、最大 5 回）

## EN

Payment-event booking ledger. **02 appends one row per event received from Stripe / PayPal and records the accounting result.** An existing `event_id` is treated as a redelivery and not processed. Rows with `booking_status=error` are retried hourly.

| Column | Type | Required | Description | Read/Write by |
|---|---|---|---|---|
| event_id | text (unique) | required | PSP event ID (Stripe `evt_…`, PayPal webhook event ID). Idempotency key | 02 W / 02 R |
| source | enum | required | `stripe` / `paypal` | 02 W |
| event_type | text | required | PSP event type verbatim (`charge.succeeded`, `PAYMENT.CAPTURE.COMPLETED`, …) | 02 W |
| object_id | text | required | ID of the object concerned (charge / refund / dispute / payout / capture) | 02 W |
| occurred_at | datetime | required | Event time (PSP UNIX seconds converted to JST) | 02 W |
| currency | text | required | ISO 4217 (`JPY`, `USD`, …) | 02 W |
| gross | number | required | Gross amount in major units (integer for JPY, decimals such as `49.99` for USD) | 02 W |
| fee | number | required | PSP fee (same unit) | 02 W |
| net | number | required | `gross − fee` | 02 W |
| gross_jpy | int | required | Gross converted to yen (unchanged for JPY) | 02 W |
| fee_jpy | int | required | Fee converted to yen | 02 W |
| net_jpy | int | required | `gross_jpy − fee_jpy` (subtracted after conversion so rounding always balances) | 02 W |
| fx_rate | number | required | Yen conversion rate; `1` for JPY. Stripe: `balance_transaction.exchange_rate` | 02 W |
| customer_ref | text | optional | Customer reference (Stripe customer ID, email address, PayPal payer ID, …) | 02 W |
| booking_status | enum | required | `dry_run` / `booked` / `skipped` / `error` | 02 W / 02 R |
| accounting_ref | text | optional | Reference on the accounting side, e.g. `freee:deal:<ID>`, `csv:<filename>` | 02 W |
| error_message | text | optional | Reason and retry count when `error` | 02 W |

**Enums**
- `source`: `stripe` / `paypal`
- `booking_status`: `dry_run` written to the sheet only (default mode) / `booked` posted to accounting / `skipped` not booked (e.g. refund alert only) / `error` accounting API failed (retried, max 5 times)

---

# disputes

## JA

返金・チャージバック・不正警告の台帳。**04 が Stripe／PayPal の Webhook と手入力フォームから 1 対象 1 行で作成・更新する（`record_id` で Append or Update）。** 状態が変わるたびに `notes` へ 1 行追記し、履歴と再送検知に使う。

| 列 | 型 | 必須 | 説明 | 読み書き |
|---|---|---|---|---|
| record_id | text（一意） | 必須 | `source\|object_id`。例 `stripe\|dp_sample0001`。手入力は `manual\|MAN-<yyyyMMdd>-<HHmmss>` を 04 が採番 | 04 W／04 R |
| source | enum | 必須 | `stripe`／`paypal`／`manual` | 04 W |
| type | enum | 必須 | `refund`／`dispute`／`early_fraud_warning`／`manual` | 04 W |
| status | enum | 必須 | 種別ごとの現在状態（下記） | 04 W／04 R |
| amount | number | 必須 | 金額（通貨の主単位。JPY は整数） | 04 W |
| currency | text | 必須 | ISO 4217 | 04 W |
| customer_ref | text | 任意 | 顧客参照（Stripe customer ID、メール、PayPal payer ID、手入力は `invoices.customer_id`） | 04 W |
| reason | text | 任意 | PSP の理由コードそのまま（`fraudulent`, `product_not_received` …）。手入力は自由記述 | 04 W |
| opened_at | datetime | 必須 | 発生日時（JST） | 04 W |
| evidence_due_by | datetime | dispute で必須 | 証拠提出期限。**PSP の UNIX 秒（UTC）を JST の実時刻に変換**して書く（当日 23:59 ではない）。期限リマインドの基準 | 04 W／04 R |
| last_alert_stage | int | 必須（既定 `0`） | 送付済みの期限リマインド数（`0` = 未送、`1` = 7 日前、`2` = 3 日前、`3` = 1 日前。Config `DEADLINE_ALERT_DAYS` の順）。重複防止 | 04 W／04 R |
| outcome | enum | 任意 | 終了結果 `won`／`lost`。未終了は空欄 | 04 W |
| closed_at | datetime | 任意 | 終了日時 | 04 W |
| notes | text | 任意 | 履歴ログ。`yyyy-MM-dd HH:mm <event_type>: <内容>` を `; ` 区切りで追記。例 `2026-09-14 03:12 charge.dispute.created: → needs_response` | 04 W／04 R／買い手 W |

**enum**
- `source`: `stripe` / `paypal` / `manual`（フォーム手入力：銀行振込・コンビニ等）
- `type`: `refund` 返金 / `dispute` チャージバック・異議 / `early_fraud_warning` 不正警告（Stripe Radar） / `manual` API の無いチャネルの返金・異議
- `status`（`type` ごと）:
  - `dispute`: `needs_response` 証拠提出待ち / `under_review` 審査中 / `closed` 終了（結果は `outcome`）
  - `refund`: `pending` 処理中 / `succeeded` 完了 / `failed` 失敗（即時アラート） / `canceled` 取消
  - `early_fraud_warning`／`manual`: `open` 対応中 / `closed` 終了
- `outcome`: `won` 勝訴 / `lost` 敗訴（空欄 = 未終了または結果なし）

## EN

Ledger of refunds, chargebacks and fraud warnings. **04 creates and updates one row per object from Stripe / PayPal webhooks and the manual-entry form (Append or Update on `record_id`).** Every state change appends one line to `notes`, which serves as history and redelivery detection.

| Column | Type | Required | Description | Read/Write by |
|---|---|---|---|---|
| record_id | text (unique) | required | `source\|object_id`, e.g. `stripe\|dp_sample0001`. Manual entries get `manual\|MAN-<yyyyMMdd>-<HHmmss>` assigned by 04 | 04 W / 04 R |
| source | enum | required | `stripe` / `paypal` / `manual` | 04 W |
| type | enum | required | `refund` / `dispute` / `early_fraud_warning` / `manual` | 04 W |
| status | enum | required | Current state per type (see below) | 04 W / 04 R |
| amount | number | required | Amount in major units (integer for JPY) | 04 W |
| currency | text | required | ISO 4217 | 04 W |
| customer_ref | text | optional | Customer reference (Stripe customer ID, email, PayPal payer ID; `invoices.customer_id` for manual entries) | 04 W |
| reason | text | optional | PSP reason code verbatim (`fraudulent`, `product_not_received`, …); free text for manual entries | 04 W |
| opened_at | datetime | required | Time opened (JST) | 04 W |
| evidence_due_by | datetime | required for disputes | Evidence deadline. **Convert the PSP's UNIX seconds (UTC) to the actual JST instant** (it is not 23:59 local). Basis for deadline reminders | 04 W / 04 R |
| last_alert_stage | int | required (default `0`) | Number of deadline reminders already sent (`0` none, `1` = 7 days before, `2` = 3 days, `3` = 1 day, in the order of Config `DEADLINE_ALERT_DAYS`). Prevents duplicates | 04 W / 04 R |
| outcome | enum | optional | Final result `won` / `lost`; blank while open | 04 W |
| closed_at | datetime | optional | Time closed | 04 W |
| notes | text | optional | History log. Append `yyyy-MM-dd HH:mm <event_type>: <detail>` entries separated by `; `, e.g. `2026-09-14 03:12 charge.dispute.created: → needs_response` | 04 W / 04 R / buyer W |

**Enums**
- `source`: `stripe` / `paypal` / `manual` (form entry: bank transfer, convenience-store payment, …)
- `type`: `refund` / `dispute` chargeback or inquiry / `early_fraud_warning` (Stripe Radar) / `manual` refund or dispute on a channel without an API
- `status` (per `type`):
  - `dispute`: `needs_response` evidence required / `under_review` / `closed` (result in `outcome`)
  - `refund`: `pending` / `succeeded` / `failed` (immediate alert) / `canceled`
  - `early_fraud_warning` / `manual`: `open` / `closed`
- `outcome`: `won` / `lost` (blank = still open or not applicable)

---

## 仕様判断 / Decisions

以下は仕様書（`CLAUDE.md`）と公式ドキュメントに無かった点をこの文書で決めたもの。`ASSUMPTIONS.md` に転記する。
The following points were not fixed by the spec (`CLAUDE.md`) or the official docs and were decided here; copy them into `ASSUMPTIONS.md`.

- **datetime 列の書式は ISO 8601 + JST オフセット（`yyyy-MM-ddTHH:mm:ss+09:00`）** — §4.5 は date の `yyyy-MM-dd` のみ規定。Luxon の `toISO()` でそのまま出せ、文字列ソートで時系列順になり、`evidence_due_by` の「実時刻」を曖昧さなく表せるため。/ **Datetime columns use ISO 8601 with the JST offset** — §4.5 only fixes the date format; Luxon `toISO()` emits it directly, string sort equals chronological order, and it expresses `evidence_due_by` as an unambiguous instant.
- **bool は `TRUE`/`FALSE` の大文字文字列、空欄は `FALSE` 扱い** — §5 が `do_not_remind` に `TRUE` と書いており、Google Sheets のブール表記と一致するため。/ **Booleans are uppercase `TRUE`/`FALSE`, blank = `FALSE`** — matches §5's `TRUE` and Google Sheets' own literal.
- **`issue_date / due_date` は 2 列に分割し、この順で並べる** — §5 は 1 行にまとめて書いているが、式参照のため別列が必要。/ **`issue_date / due_date` are two separate columns in that order** — §5 lists them on one line, but expressions need distinct columns.
- **買い手には全シートを「書式なしテキスト」に設定させ、ワークフローは Cell Format = Let n8n format で書き、読み取り値は必ず自前でパースする** — Google Sheets の自動書式で `yyyy-MM-dd` がロケール表示に変わると n8n の既定「Formatted Text」読み取りが壊れるため（Google Sheets ノード公式ドキュメントの Output Formatting／Cell Format の記述に基づく）。/ **Buyers set every sheet to Plain text; workflows write with Cell Format = Let n8n format and always parse what they read** — Google's automatic formatting turns `yyyy-MM-dd` into locale text and n8n's default "Formatted Text" read would then break (per the Google Sheets node docs on Output Formatting / Cell Format).
- **Config のシート設定キーは `SHEET_ID`, `SHEET_INVOICES`, `SHEET_TRANSACTIONS`, `SHEET_REMINDERS_LOG`, `SHEET_EVENTS_LEDGER`, `SHEET_DISPUTES`** — §4.1 は「Sheet ID・シート名を Config に」とだけ規定。各テンプレは同じキー名を使う。/ **Config keys for sheet settings are named as above** — §4.1 only says the IDs and names live in Config; every template uses the same key names.
- **`memo_norm` は摘要を NFKC 正規化し空白・記号を除いたもの。摘要が無ければ空文字で末尾の `|` は残す** — §5 の `txn_id` 形式に `memo_norm` の定義が無い。名義正規化と違い法人格除去・カナ変換はしない（摘要は名義ではない）。最終定義は 01 の `DESIGN.md` に置く。/ **`memo_norm` = memo after NFKC with whitespace/punctuation removed; empty string (trailing `|` kept) when there is no memo** — §5 does not define it; unlike payer normalization it does not strip legal-entity tokens or convert kana. Final definition lives in 01's `DESIGN.md`.
- **`paid_amount` は実際に着金した額。手数料差引のときは `paid_amount + fee_deducted = amount` で `paid`** — §5 は `paid_amount`「累計入金額」と `fee_deducted` の関係を明示していない。着金額をそのまま持てば通帳と一致し、差額は `fee_deducted` で説明できる。/ **`paid_amount` is the cash actually received; with a fee deduction the row is `paid` when `paid_amount + fee_deducted = amount`** — §5 does not state the relation; keeping the cash figure matches the bank statement and `fee_deducted` explains the gap.
- **一部入金（突合ルール 3c）の `match_confidence` は `auto`** — enum に一部入金専用の値が無く、名義一致で自動確定する経路のため。/ **Partial payments (matching rule 3c) record `match_confidence=auto`** — the enum has no partial-specific value and the path auto-confirms on a name match.
- **01・03 は `currency=JPY` の請求のみ処理し、JPY 以外の行は通知で警告して対象外にする** — §4.5「JPY 以外はテンプレ02 の通貨ルール」は 02 向けで、01・03 の扱いが未定義。銀行振込の円建て突合が製品範囲。/ **01 and 03 process only `currency=JPY` invoices and warn about others** — §4.5 defers non-JPY to Template 02; yen bank transfers are the product scope of 01/03.
- **03 の顧客グループ化キーは `customer_id`、空なら `customer_email`** — §5 は `customer_id` を「任意」としか書いていない。ID があればそれを、無ければ送信先で束ねる。/ **03 groups invoices by `customer_id`, falling back to `customer_email`** — §5 only marks `customer_id` optional.
- **`reminders_log.channel` は v1 では `gmail` 固定の text 列** — 03 は Gmail ノードでのみ送るため enum を増やさない。/ **`reminders_log.channel` is a text column fixed to `gmail` in v1** — 03 sends via the Gmail node only.
- **`gmail_message_id` は `draft` のとき下書きのメッセージ ID、`sent` のとき送信メッセージ ID、`owner_only` では空。顧客単位で 1 通にまとめた場合は請求ごとに 1 行を書き ID を共有** — §5 は列名のみ。冪等キー `(invoice_id, stage)` を請求単位で保つため。/ **`gmail_message_id` holds the draft's message ID for `draft`, the sent message ID for `sent`, blank for `owner_only`; grouped emails write one row per invoice sharing the ID** — keeps the `(invoice_id, stage)` key per invoice.
- **`events_ledger` の `gross`/`fee`/`net` は通貨の主単位の number（USD は小数）、`*_jpy` は int、`net_jpy = gross_jpy − fee_jpy`** — テンプレ02「最小単位→÷100」に従い、円換算は gross と fee を個別に四捨五入してから net を差で出すと端数が常に合う。サンプル CSV は指示どおり整数（JPY）のみ。/ **`gross`/`fee`/`net` are numbers in major units (decimals for USD), `*_jpy` are ints, `net_jpy = gross_jpy − fee_jpy`** — follows Template 02's minor-unit rule; rounding gross and fee separately and deriving net keeps the ledger balanced. Sample CSVs use JPY integers only, as instructed.
- **`accounting_ref` の形式は `freee:deal:<ID>` / `mf:<ID>` / `csv:<ファイル名>`** — §5 は「freee の取引 ID 等」のみ。モードが分かる接頭辞を付ける。/ **`accounting_ref` format is `freee:deal:<ID>` / `mf:<ID>` / `csv:<filename>`** — §5 only says "e.g. freee deal ID"; the prefix identifies the mode.
- **`disputes.status` は `type` ごとの enum（dispute: `needs_response`/`under_review`/`closed`、refund: `pending`/`succeeded`/`failed`/`canceled`、EFW・manual: `open`/`closed`）、`outcome` は `won`/`lost`** — §5 は列名のみ。テンプレ04 の本文が使う語（`needs_response`、`under_review`、`failed`、`pending`、`won`/`lost`）に合わせ、PSP の生の状態は `notes` に残す。/ **`disputes.status` is an enum per `type` and `outcome` is `won`/`lost`** — §5 names the columns only; values follow the words Template 04 uses, with raw PSP states kept in `notes`.
- **`disputes.notes` は `yyyy-MM-dd HH:mm <event_type>: <内容>` を `; ` 区切りで追記し、04 の冪等キー `(source, object_id, event_type)` の `event_type` 既出チェックに使う** — §5 の `disputes` に `event_type` 列が無く、テンプレ04 は「状態遷移を notes に追記」とだけ規定。列を増やさずに再送検知を可能にする。04 の `DESIGN.md` で最終確認する。/ **`disputes.notes` appends `yyyy-MM-dd HH:mm <event_type>: <detail>` entries separated by `; ` and is where 04 checks the `event_type` part of its idempotency key** — `disputes` has no `event_type` column and Template 04 only says to append transitions to `notes`; this enables redelivery detection without a new column. To be confirmed in 04's `DESIGN.md`.
- **手入力の `object_id` は `MAN-<yyyyMMdd>-<HHmmss>` を 04 が採番** — `record_id = source|object_id` の `manual` に ID の規定が無い。/ **Manual entries get `object_id = MAN-<yyyyMMdd>-<HHmmss>` assigned by 04** — the spec gives no ID rule for `manual`.
- **`last_alert_stage` は送付済みリマインド数（0〜3、`DEADLINE_ALERT_DAYS` の順）** — §5 は列名のみ。/ **`last_alert_stage` = number of deadline reminders sent (0–3, in `DEADLINE_ALERT_DAYS` order)** — §5 names the column only.
- **CSV の改行は LF、UTF-8 BOM なし。サンプルはすべて架空（`example.com`／`example.jp`、「サンプル」「テスト」「見本」を含む名称、`*_sample0001` 形式の ID）** — タスク指示どおり。/ **CSV line ending is LF, UTF-8 without BOM; all samples fictional** — as instructed.
