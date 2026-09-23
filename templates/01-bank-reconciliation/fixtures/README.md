# テンプレ01 fixtures — 一覧と期待結果 / Template 01 fixtures — inventory and expected outcomes

すべて架空データ（実在の企業・個人・銀行・メールアドレスは含まない。ドメインは `example.jp` / `example.com`、銀行名は「サンプル銀行」「Sample Bank」）。
期待値は `DESIGN.md` §4 の Config 既定値と §6 の疑似コードから求めた（末尾「前提と注意」参照）。P3 はこの表に対して `tests/CASES.md` の手順で判定する。

All data is fictional (no real companies, people, banks or addresses; domains are `example.jp` / `example.com`, banks are "サンプル銀行" / "Sample Bank").
Expected values are derived from the Config defaults in `DESIGN.md` §4 and the pseudocode in §6 (see "Assumptions" at the end). P3 asserts against these tables following `tests/CASES.md`.

---

## 1. ファイル一覧 / Files

| ファイル / File | 文字コード・形式 / Encoding, format | 用途 / Purpose |
|---|---|---|
| `invoices.seed.csv` | UTF-8（BOM なし）、LF、§5 `invoices` の列順 | `invoices` シートの初期状態（20 件）/ initial `invoices` sheet (20 rows) |
| `transactions.seed.csv` | UTF-8（BOM なし）、LF、§5 `transactions` の列順、`imported_at` は ISO 8601 `+09:00` | `transactions` シートの初期状態（消込済み 1 件）/ initial `transactions` sheet (1 matched row) |
| `bank_A_sjis.csv` | **Shift_JIS（cp932）**、CRLF、見出し `日付,摘要,入金額,出金額,残高`、金額は `"33,000"` 形式（引用符＋桁区切り）| 銀行 A 形式。R01〜R09 / bank format A, cases R01–R09 |
| `bank_A_sjis_skip1.csv` | Shift_JIS（cp932）、CRLF。A と同じ 15 行の**前に**説明行 1 行（`サンプル銀行 入出金明細 …`）| `CSV_MAPPING.skip_rows=1` の実証（R15）。`skip_rows=0` では `CSV column not found` で明示的に失敗 / proves `skip_rows` (R15) |
| `bank_B_utf8bom.csv` | **UTF-8 with BOM**、CRLF、見出し `取引日,内容,お預入,お引出`、日付 `yyyyMMdd`、金額は桁区切りなし | 銀行 B 形式。R13 / bank format B, case R13 |
| `mail_bankX.eml` | RFC 822、件名は UTF-8 base64 の encoded-word、本文 text/plain UTF-8 base64 | 入金通知メール X（ラベル行形式）/ notification X (labeled lines) — R10 |
| `mail_bankY.eml` | RFC 822、本文 text/plain UTF-8 8bit | 入金通知メール Y（表形式）/ notification Y (table layout) — R10 |
| `mail_parsers.example.json` | JSON | 上記 2 通に対応する Config `MAIL_PARSERS` の値（正規表現はキャプチャ 1 つ）。**`DESIGN.md` §4 の既定値の正本** / `MAIL_PARSERS` for the two mails (one capture group each); **source of truth for the defaults in `DESIGN.md` §4** |
| `mail_pinned.example.json` | JSON | `Watch Gmail Inbox` の pinned data 例（Simplify OFF の形、`text` は .eml 本文のデコード結果）/ pinned-data example for the Gmail Trigger |
| `csv_mapping.examples.json` | JSON | 銀行 A・B それぞれの Config `CSV_MAPPING` / `CSV_MAPPING` for formats A and B |

---

## 2. `invoices.seed.csv`（20 件）

列は `shared/invoices.template.csv` と同一。`remind_stage=0`、`do_not_remind=FALSE`、`promised_date` 空。`INV-2026-010` は入金済み、`INV-2026-011` は取消で、この 2 件は突合対象外でなければならない。
Columns are identical to `shared/invoices.template.csv`. `remind_stage=0`, `do_not_remind=FALSE`, `promised_date` blank. `INV-2026-010` is already paid and `INV-2026-011` is cancelled; both must be ignored by matching.

「期待結果」は各入力（A = `bank_A_sjis.csv`、B = `bank_B_utf8bom.csv`、M = 2 通のメール）を**初期状態のシートに対して**流した後の `invoices` 行。列は `status / match_confidence / paid_amount / fee_deducted / paid_date / matched_txn_ids`。「—」は変更なし。
"Expected" is the `invoices` row after running each input (A = `bank_A_sjis.csv`, B = `bank_B_utf8bom.csv`, M = the two mails) **against the seed state**: `status / match_confidence / paid_amount / fee_deducted / paid_date / matched_txn_ids`. "—" = unchanged.

| invoice_id | customer_name | payer_name_alias | amount | due_date | 初期 status / seed | 役割 / Role | 期待結果 / Expected |
|---|---|---|---|---|---|---|---|
| INV-2026-001 | 株式会社サンプル商事 | `カ)サンプルシヨウジ,サンプルシヨウジ` | 33000 | 2026-09-30 | unpaid | R01（A-1） | A: `paid / auto / 33000 / 0 / 2026-09-01 / 2026-09-01\|33000\|サンプルシヨウジ\|` |
| INV-2026-002 | テスト工業有限会社 | `テストコウギヨウ,テストコウギョウ`（2 表記 / two spellings） | 55000 | 2026-09-30 | unpaid | R03（A-3） | A: `paid / fee_deducted / 54780 / 220 / 2026-09-02 / 2026-09-02\|54780\|テストコウギヨウ\|` |
| INV-2026-003 | 山田 太郎 | `ヤマダタロウ` | 9800 | 2026-09-30 | unpaid | R01 全角名義 / full-width（A-4） | A: `paid / auto / 9800 / 0 / 2026-09-03 / 2026-09-03\|9800\|ヤマダタロウ\|` |
| INV-2026-004 | 合同会社ミホンデザイン | `ミホンデザイン` | 128000 | 2026-09-30 | unpaid | R02（A-5、名義は別人 / remitter differs） | A: `paid / amount_only / 128000 / 0 / 2026-09-04 / 2026-09-04\|128000\|サトウケイコ\|` |
| INV-2026-005 | 株式会社テスト物産 | `カ)テストブツサン,テストブツサン` | 700000 | 2026-09-10 | unpaid | R04 合算 1/2（A-6） | A: `paid / combined / 700000 / 0 / 2026-09-05 / 2026-09-05\|1234567\|テストブツサン\|` |
| INV-2026-006 | 株式会社テスト物産 | `カ)テストブツサン,テストブツサン` | 534567 | 2026-09-30 | unpaid | R04 合算 2/2（A-6） | A: `paid / combined / 534567 / 0 / 2026-09-05 / 2026-09-05\|1234567\|テストブツサン\|` |
| INV-2026-007 | サンプルシステム株式会社 | `サンプルシステム` | 250000 | 2026-09-30 | unpaid | R05 一部入金 / partial（A-8） | A: `partial / auto / 100000 / 0 / 2026-09-08 / 2026-09-08\|100000\|サンプルシステム\|` |
| INV-2026-008 | 有限会社見本印刷 | （なし / none） | 44000 | 2026-09-30 | unpaid | R06 同額ペア A / ambiguous pair A（A-9） | — （変更なし。`suggested` に載るだけ / unchanged, suggested only） |
| INV-2026-009 | モデル企画株式会社 | （なし / none） | 44000 | 2026-10-05 | unpaid | R06 同額ペア B / ambiguous pair B（A-9） | — |
| INV-2026-010 | 株式会社見本商会 | `カ)ミホンシヨウカイ,ミホンシヨウカイ` | 66000 | 2026-09-01 | **paid**（2026-08-28 入金、`matched_txn_ids=2026-08-28\|66000\|ミホンシヨウカイ\|`） | 入金済みは対象外 / paid must be ignored（A-11 は一致させない） | — |
| INV-2026-011 | テスト建設株式会社 | `テストケンセツ` | 88000 | 2026-09-15 | **cancelled** | 取消は対象外 / cancelled must be ignored（A-12 は一致させない） | — |
| INV-2026-012 | 株式会社サンプルフーズ | `サンプルフーズ` | 27500 | 2026-09-30 | unpaid | R01 包含一致 / containment（A-13） | A: `paid / auto / 27500 / 0 / 2026-09-14 / 2026-09-14\|27500\|サンプルフーズトウキヨウ\|` |
| INV-2026-013 | 株式会社ダミー加工 | `ダミーカコウ` | 41800 | 2026-09-30 | unpaid | R13 先頭番号 / leading digits（B-1） | B: `paid / auto / 41800 / 0 / 2026-09-17 / 2026-09-17\|41800\|ダミーカコウ\|` |
| INV-2026-014 | 鈴木 一郎 | `スズキイチロウ` | 15400 | 2026-09-30 | unpaid | R13 ひらがな / hiragana（B-3） | B: `paid / auto / 15400 / 0 / 2026-09-18 / 2026-09-18\|15400\|スズキイチロウ\|` |
| INV-2026-015 | 有限会社見本プランニング | `ミホンプランニング` | 57200 | 2026-10-05 | unpaid | R13（B-4） | B: `paid / auto / 57200 / 0 / 2026-09-19 / 2026-09-19\|57200\|ミホンプランニング\|` |
| INV-2026-016 | 高橋 美紀 | `タカハシミキ` | 12100 | 2026-10-10 | unpaid | R13 先頭番号・個人 / leading digits, individual（B-6） | B: `paid / auto / 12100 / 0 / 2026-09-21 / 2026-09-21\|12100\|タカハシミキ\|` |
| INV-2026-017 | 株式会社サンプル商事 | `カ)サンプルシヨウジ,サンプルシヨウジ` | 49500 | 2026-10-15 | unpaid | 同一顧客の 2 件目。A-1 は金額で INV-001 に決まる / 2nd open invoice of C-001; A-1 resolves to INV-001 by amount | — （A-11 の候補に載る / listed as a candidate of A-11） |
| INV-2026-018 | ダミー電機株式会社 | `カ)ダミーデンキ,ダミーデンキ` | 104500 | 2026-10-10 | unpaid | R10 メール X / mail X | M: `paid / auto / 104500 / 0 / 2026-09-17 / 2026-09-17\|104500\|ダミーデンキ\|【サンプル銀行】ご入金のお知らせ(gmail:18f3aabb00000001)` |
| INV-2026-019 | 佐々木 花子 | `ササキハナコ` | 19800 | 2026-10-12 | unpaid | R10 メール Y / mail Y | M: `paid / auto / 19800 / 0 / 2026-09-18 / 2026-09-18\|19800\|ササキハナコ\|depositnotification-samplebank(gmail:18f3aabb00000002)` |
| INV-2026-020 | 株式会社サンプル運輸 | `サンプルウンユ` | 38500 | 2026-10-20 | unpaid | 未入金のまま / stays unpaid | — |

---

## 3. `transactions.seed.csv`（1 件）

| txn_id | source | txn_date | payer_name_raw | payer_name_norm | amount | matched_invoice_ids | status |
|---|---|---|---|---|---|---|---|
| `2026-08-28\|66000\|ミホンシヨウカイ\|` | bank_csv | 2026-08-28 | `振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ` | ミホンシヨウカイ | 66000 | INV-2026-010 | matched |

`INV-2026-010` を消し込んだ過去の入金。`Read Transactions` が空でない状態を作るためのもの（空シートは R14 で別に試す）。`matched` なので再突合の対象にならない。
The deposit that settled `INV-2026-010`. Provides a non-empty `Read Transactions` (the empty-sheet case is R14). Being `matched`, it is never re-matched.

---

## 4. `bank_A_sjis.csv`（Shift_JIS、15 行）

Config は既定値のまま（`CSV_MAPPING` = `csv_mapping.examples.json` の `bank_A_sjis.csv`）。`No.` はデータ行番号、`_row` は物理行番号（見出し = 1）。`txn_id` は `日付|金額|payer_name_norm|`（memo 列なし → 末尾 `|`）。
Config defaults apply (`CSV_MAPPING` = `bank_A_sjis.csv` entry in `csv_mapping.examples.json`). `No.` = data row, `_row` = physical line (header = 1). `txn_id` = `date|amount|payer_name_norm|` (no memo column → trailing `|`).

| No. | _row | 日付 | 摘要（raw） | 入金額 | 出金額 | ケース / Case | payer_name_norm | txn_id | transactions.status | matched_invoice_ids | suggested_invoice_ids | invoices への効果 / Effect on invoices |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2 | 2026/09/01 | `振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ` | "33,000" | | **R01** 名義・金額一致 | サンプルシヨウジ | `2026-09-01\|33000\|サンプルシヨウジ\|` | matched | INV-2026-001 | | INV-001 → paid, auto, 33000, fee 0 |
| 2 | 3 | 2026/09/01 | `ｶｰﾄﾞ ｻﾝﾌﾟﾙｶｰﾄﾞ` | | "12,800" | **R07** 出金 | — | （生成しない / not generated） | — | — | — | なし。`ignored_withdraw` +1 |
| 3 | 4 | 2026/09/02 | `振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ` | "54,780" | | **R03** 手数料 220 差引 | テストコウギヨウ | `2026-09-02\|54780\|テストコウギヨウ\|` | matched | INV-2026-002 | | INV-002 → paid, fee_deducted, paid_amount 54780, fee 220。通知「要確認」 |
| 4 | 5 | 2026/09/03 | `フリコミ　ヤマダ　タロウ`（全角カナ・全角空白 / full-width） | "9,800" | | **R01** 全角名義 | ヤマダタロウ | `2026-09-03\|9800\|ヤマダタロウ\|` | matched | INV-2026-003 | | INV-003 → paid, auto, 9800 |
| 5 | 6 | 2026/09/04 | `振込 ｻﾄｳ ｹｲｺ` | "128,000" | | **R02** 金額のみ一致 | サトウケイコ | `2026-09-04\|128000\|サトウケイコ\|` | matched | INV-2026-004 | | INV-004 → paid, amount_only, 128000。通知「要確認」 |
| 6 | 7 | 2026/09/05 | `振込 ｶ)ﾃｽﾄﾌﾞﾂｻﾝ` | "1,234,567" | | **R04** 2 請求の合算 | テストブツサン | `2026-09-05\|1234567\|テストブツサン\|` | matched | INV-2026-005,INV-2026-006 | | INV-005 → paid, combined, 700000；INV-006 → paid, combined, 534567。両方の `matched_txn_ids` に同じ txn_id。通知「要確認」 |
| 7 | 8 | 2026/09/05 | `ﾃﾞﾝｷﾘﾖｳｷﾝ ｻﾝﾌﾟﾙﾃﾞﾝﾘﾖｸ` | | "8,450" | **R07** 出金 | — | — | — | — | — | `ignored_withdraw` +1 |
| 8 | 9 | 2026/09/08 | `振込 ｻﾝﾌﾟﾙｼｽﾃﾑ(ｶ` | "100,000" | | **R05** 一部入金 | サンプルシステム | `2026-09-08\|100000\|サンプルシステム\|` | matched | INV-2026-007 | | INV-007 → partial, auto, paid_amount 100000（残 150000）。通知「自動消込」に残額表示 |
| 9 | 10 | 2026/09/09 | `振込 ｵｵﾊﾞ ﾏｻｵ` | "44,000" | | **R06** 同額請求 2 件・名義不一致 | オオバマサオ | `2026-09-09\|44000\|オオバマサオ\|` | **ambiguous** | | INV-2026-008,INV-2026-009 | なし（自動確定しない）。通知「候補複数」 |
| 10 | 11 | 2026/09/10 | `ATM ﾋｷﾀﾞｼ` | | "30,000" | **R07** 出金 | — | — | — | — | — | `ignored_withdraw` +1 |
| 11 | 12 | 2026/09/11 | `振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ` | "66,000" | | 入金済み請求の罠 / paid-invoice trap（規則 5） | ミホンシヨウカイ | `2026-09-11\|66000\|ミホンシヨウカイ\|` | **unmatched** | | INV-2026-015,INV-2026-017 | なし。INV-010（paid）に一致させてはならない。候補は弱い名義類似（`nameRank=1`）による |
| 12 | 13 | 2026/09/12 | `振込 ﾃｽﾄｹﾝｾﾂ(ｶ` | "88,000" | | 取消請求の罠 / cancelled-invoice trap（規則 5） | テストケンセツ | `2026-09-12\|88000\|テストケンセツ\|` | **unmatched** | | （空 / empty） | なし。INV-011（cancelled）に一致させてはならない |
| 13 | 14 | 2026/09/14 | `振込 ｶ)ｻﾝﾌﾟﾙﾌｰｽﾞﾄｳｷﾖｳ` | "27,500" | | **R01** 包含一致（名義 ⊃ alias） | サンプルフーズトウキヨウ | `2026-09-14\|27500\|サンプルフーズトウキヨウ\|` | matched | INV-2026-012 | | INV-012 → paid, auto, 27500 |
| 14 | 15 | 2026/09/15 | `振込 ﾅｶﾑﾗ ｼﾞﾛｳ` | "5,500" | | 該当なし / no invoice（規則 5） | ナカムラジロウ | `2026-09-15\|5500\|ナカムラジロウ\|` | **unmatched** | | INV-2026-014 | なし。候補は「ロウ」の弱い類似（`nameRank=1`）による |
| 15 | 16 | 2026/09/16 | `ﾃｽｳﾘﾖｳ` | | "440" | **R07** 出金（手数料） | — | — | — | — | — | `ignored_withdraw` +1 |

残高列は先頭 1,200,000 円からの通算で整合している（パーサは使わない）。
The balance column is a consistent running balance from 1,200,000 yen (not used by the parser).

**A の summary 期待値 / Expected summary for A**：`n=11, a=4, b=3, c=4, ignored_withdraw=4, skipped_existing=0, skipped_duplicate_in_batch=0, warnings=[]`
（A = No.1, 4, 8, 13　B = No.3, 5, 6　C = No.9, 11, 12, 14）

**A を 2 回目に流したとき（R09）/ Second run of A (R09)**：`n=0, skipped_existing=11`、`invoice_update` 0 件、`txn_row` 0 件、通知は `no_transactions`（skip 11 件）。

---

## 5. `bank_B_utf8bom.csv`（UTF-8 BOM、8 行）

Config `CSV_MAPPING` を `csv_mapping.examples.json` の `bank_B_utf8bom.csv` に差し替える（`date_col=取引日, payer_col=内容, deposit_col=お預入, withdraw_col=お引出, date_format=yyyyMMdd, encoding=utf-8`）。BOM があるため `encoding` の値に関わらず UTF-8 として読まれる。`date_format=auto` でも同じ結果になる。
Switch `CSV_MAPPING` to the `bank_B_utf8bom.csv` entry. The BOM forces UTF-8 regardless of `encoding`; `date_format=auto` yields the same result.

| No. | _row | 取引日 | 内容（raw） | お預入 | お引出 | ケース / Case | payer_name_norm | txn_id | transactions.status | matched_invoice_ids | suggested_invoice_ids | invoices への効果 / Effect |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2 | 20260917 | `0123 カ)ダミーカコウ` | 41800 | | **R13** 先頭の振込人番号 → `STRIP_LEADING_DIGITS` | ダミーカコウ | `2026-09-17\|41800\|ダミーカコウ\|` | matched | INV-2026-013 | | INV-013 → paid, auto, 41800 |
| 2 | 3 | 20260917 | `デンワリヨウキン サンプルツウシン` | | 3300 | R07 出金 | — | — | — | — | — | `ignored_withdraw` +1 |
| 3 | 4 | 20260918 | `ふりこみ　すずき　いちろう`（ひらがな / hiragana） | 15400 | | **R13** ひらがな→カタカナ、`フリコミ` 除去 | スズキイチロウ | `2026-09-18\|15400\|スズキイチロウ\|` | matched | INV-2026-014 | | INV-014 → paid, auto, 15400 |
| 4 | 5 | 20260919 | `ユ)ミホンプランニング` | 57200 | | **R13** `ユ)` 除去 | ミホンプランニング | `2026-09-19\|57200\|ミホンプランニング\|` | matched | INV-2026-015 | | INV-015 → paid, auto, 57200 |
| 5 | 6 | 20260919 | `ATMヒキダシ` | | 20000 | R07 出金 | — | — | — | — | — | `ignored_withdraw` +1 |
| 6 | 7 | 20260921 | `0045 タカハシ ミキ` | 12100 | | **R13** 先頭番号・個人名 | タカハシミキ | `2026-09-21\|12100\|タカハシミキ\|` | matched | INV-2026-016 | | INV-016 → paid, auto, 12100 |
| 7 | 8 | 20260922 | `フリコミ ワタナベ ケン` | 7700 | | 該当なし / no invoice（規則 5） | ワタナベケン | `2026-09-22\|7700\|ワタナベケン\|` | **unmatched** | | （空 / empty） | なし |
| 8 | 9 | 20260922 | `フリカエ サンプルセイメイ` | | 15800 | R07 出金 | — | — | — | — | — | `ignored_withdraw` +1 |

**B の summary 期待値 / Expected summary for B**：`n=5, a=4, b=0, c=1, ignored_withdraw=3, warnings=[]`

**R08 の判定 / R08 assertion**：A・B とも `payer_name_raw` が上表の raw 列と文字単位で一致し（U+FFFD なし）、B の 1 列目見出しが BOM 込みでなく `取引日` と一致する（`CSV column not found` にならない）。

---

## 6. `mail_bankX.eml` / `mail_bankY.eml`（R10）

Config `MAIL_PARSERS` = `mail_parsers.example.json`。パーサは先頭から試し、最初に `from_match`（差出人の部分一致）と `subject_match`（件名の部分一致）を満たしたものだけを使う。X は bankX に、Y は bankY にだけ一致する（X の差出人は `@example.jp`、Y は `@example.com`）。本文は NFKC 正規化してから正規表現を当てるため、全角数字・全角コロン・半角カナは半角数字・半角コロン・全角カナに変換された状態でキャプチャされる。
`MAIL_PARSERS` = `mail_parsers.example.json`. Parsers are tried in order; the first whose `from_match` (substring of From) and `subject_match` (substring of Subject) both hold is used. X matches only bankX, Y only bankY. The body is NFKC-normalized before the regexes run, so full-width digits/colons and half-width katakana are captured in their normalized form.

| ファイル / File | From | Subject | Date ヘッダ | 本文の抽出元 / Body fields | パーサ / Parser | 抽出値 / Extracted (`amount / payer_raw / date`) | txn_id | 効果 / Effect |
|---|---|---|---|---|---|---|---|---|
| `mail_bankX.eml` | `サンプル銀行 <notice@example.jp>` | `【サンプル銀行】ご入金のお知らせ` | 2026-09-17 09:12 +09:00 | `お振込人：ｶ)ﾀﾞﾐｰﾃﾞﾝｷ` / `金額：１０４，５００円` / `日付：２０２６年９月１７日` | bankX | `104500` / `カ)ダミーデンキ`（NFKC 後）/ `2026-09-17` | `2026-09-17\|104500\|ダミーデンキ\|【サンプル銀行】ご入金のお知らせ(gmail:18f3aabb00000001)` | INV-018 → paid, auto, 104500。transactions: `source=gmail`, `memo=【サンプル銀行】ご入金のお知らせ (gmail:18f3aabb00000001)` |
| `mail_bankY.eml` | `Sample Bank Online <alerts@example.com>` | `Deposit Notification - Sample Bank` | 2026-09-19 08:30 +09:00（本文の取引日は前日 / body date is the previous day） | `Transaction Date   2026-09-18` / `Amount             JPY 19,800` / `Remitter           ササキ ハナコ` | bankY | `19800` / `ササキ ハナコ` / `2026-09-18`（Date ヘッダではなく本文の日付 / from the body, not the header） | `2026-09-18\|19800\|ササキハナコ\|depositnotification-samplebank(gmail:18f3aabb00000002)` | INV-019 → paid, auto, 19800。transactions: `source=gmail`, `memo=Deposit Notification - Sample Bank (gmail:18f3aabb00000002)` |

Gmail の message id（`18f3aabb00000001` / `18f3aabb00000002`）は `mail_pinned.example.json` の `id` で与える架空の値。`txn_id` の `memo_norm` は「件名 + ` (gmail:<id>)`」を NFKC → 空白除去 → `|`→`/` → 小文字化したもの（`DESIGN.md` §6.6 `normalizeMemo`、`shared/sheets-schema.md` と同一定義）。Config 既定の `GMAIL_QUERY`（`subject:(入金 OR Deposit) newer_than:1d`）は X・Y 両方の件名に一致する（Gmail の `subject:` は本文を見ないため、Y の本文にある `入金通知` では拾えない）。
The Gmail message ids are fictional values from `mail_pinned.example.json`. `memo_norm` = subject + ` (gmail:<id>)` after NFKC, whitespace removal, `|`→`/`, lowercase (`DESIGN.md` §6.6 `normalizeMemo`, same definition as `shared/sheets-schema.md`). The default `GMAIL_QUERY` (`subject:(入金 OR Deposit) newer_than:1d`) matches both subjects; Gmail `subject:` does not search the body, so the `入金通知` inside Y's body would not be enough.

**M の summary 期待値 / Expected summary for the two mails in one run**：`n=2, a=2, b=0, c=0, warnings=[]`

`mail_parsers.example.json` の正規表現（Python `re` と Node `RegExp(…, 'u')` で .eml 本文に対し検証済み、2026-09-23。`DESIGN.md` §4 の既定値と同一）/ Regexes (verified with Python `re` and Node `RegExp(…, 'u')` against the decoded .eml bodies, 2026-09-23; identical to the defaults in `DESIGN.md` §4):

| parser | amount_regex | payer_regex | date_regex |
|---|---|---|---|
| bankX | `(?:入金額\|お振込金額\|金額)[：:]\s*([0-9,]+)` → `104,500` | `(?:お振込人\|振込人\|振込名義\|ご依頼人)[：:]\s*([^\n]+)` → `カ)ダミーデンキ` | `(?:日付\|お取引日\|取引日)[：:]\s*(\d{4}[/\-年]\d{1,2}[/\-月]\d{1,2})` → `2026年9月17` |
| bankY | `Amount\s+(?:JPY\|¥)?\s*([0-9,]+)` → `19,800` | `Remitter\s+([^\n]+)` → `ササキ ハナコ` | `Transaction Date\s+(\d{4}-\d{2}-\d{2})` → `2026-09-18` |

---

## 7. 前提と注意 / Assumptions and notes

- **初期状態**：各入力（A、B、M）は「`invoices` = seed、`transactions` = transactions.seed」の状態に対して流したときの期待値である。A → B → M と連続して流しても消込結果は同じ（対象請求が互いに素）だが、`suggested_invoice_ids` は残っている請求に依存するため、A-11 の候補（INV-015）は B を先に流すと消える。P3 では各ファイルの前にシートを seed に戻す。
- **実行日**：`summary.date` と通知の日付は実行日（JST）。`imported_at` は実行時刻。どちらも値の一致ではなく形式（`yyyy-MM-dd` / ISO 8601 `yyyy-MM-ddTHH:mm:ss+09:00`、`shared/sheets-schema.md` の datetime）で判定する。
- **名義正規化の順序**：期待する `payer_name_norm` は `DESIGN.md` §6.6 `normalizePayer`（2 段階：どこでも除去するトークン `振込`／`フリコミ`／`株式会社` 等を先に消し、その後に前株 `X)`／後株 `(X` を当てる）で計算した値。1 回の走査で長さ順に混ぜると `振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ` が `カサンプルシヨウジ` になる（A-1, A-6, A-11, A-13）ため、§6.6 は 2 段階で確定済み（2026-09-23、Node で全 14 名義を検証）。
- **半角カナと小書き**：銀行は `ｼﾖｳ` のように大書きで届ける。alias も `サンプルシヨウジ`（大書き）で登録している。`INV-2026-002` は `テストコウギヨウ,テストコウギョウ` の 2 表記を持ち、どちらの表記で振り込まれても完全一致する例。
- **メールの `payer_name_raw`**：本文を NFKC 正規化してから抽出するため、`ｶ)ﾀﾞﾐｰﾃﾞﾝｷ` は `カ)ダミーデンキ` として保存される（CSV 経路の raw は変換しない）。
- **通貨**：seed は全件 `JPY`。`shared/sheets-schema.md` の「JPY 以外は警告して対象外」は `tests/CASES.md` R23 で、`Read Invoices` の pinned data に USD の請求 1 行（`INV-2026-022`）を加えて試す（seed 本体には入れない。入れると A・B・M の `warnings=[]` の期待値が全て変わるため）。

- **Seed state**: every expectation assumes the run starts from `invoices` = seed and `transactions` = transactions.seed. Running A → B → M consecutively gives the same matches (target invoices are disjoint), but `suggested_invoice_ids` depends on what is still open (A-11 loses INV-015 as a candidate if B runs first). P3 resets the sheets to the seed before each file.
- **Run date**: `summary.date` and the notification date are the run date (JST); `imported_at` is the run time in ISO 8601 with the JST offset (`yyyy-MM-ddTHH:mm:ss+09:00`, the `datetime` type of `shared/sheets-schema.md`). Assert the format, not the value.
- **Token order in name normalization**: expected `payer_name_norm` is computed by `DESIGN.md` §6.6 `normalizePayer` (two passes: "anywhere" tokens such as `振込` / `フリコミ` / `株式会社` first, then the anchored `X)` / `(X` tokens). A single pass in descending token length would turn `振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ` into `カサンプルシヨウジ` (rows A-1, A-6, A-11, A-13), so §6.6 is fixed as two passes (2026-09-23, all 14 names verified in Node).
- **Half-width kana and small kana**: banks deliver large kana (`ｼﾖｳ`), and the aliases are registered the same way (`サンプルシヨウジ`). `INV-2026-002` carries both spellings `テストコウギヨウ,テストコウギョウ` as an example of a customer with two remitter spellings.
- **Mail `payer_name_raw`** is captured from the NFKC-normalized body, so `ｶ)ﾀﾞﾐｰﾃﾞﾝｷ` is stored as `カ)ダミーデンキ` (the CSV path keeps the raw text).
- **Currency**: the seed is all `JPY`. The non-JPY warning described in `shared/sheets-schema.md` is exercised by `tests/CASES.md` R23, which adds one USD invoice (`INV-2026-022`) to the pinned `Read Invoices` data (not to the seed, which would change every `warnings=[]` expectation for A, B and M).
