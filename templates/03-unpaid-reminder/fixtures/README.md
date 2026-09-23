# テンプレ03 fixtures — 一覧と期待結果 / Template 03 fixtures — inventory and expected outcomes

すべて架空データ（実在の企業・個人・メールアドレス・Gmail ID・カレンダー ID は含まない。ドメインは `example.jp` / `example.com`、社名は「サンプル」「テスト」「見本」「ダミー」）。**例外は `holidays.example.json` だけで、これは内閣府の実データ**（架空の祝日リストでは祝日に督促を送ってしまうため）。
期待値は `DESIGN.md` §4 の Config 既定値と §6 の疑似コードから求め、`make_fixtures.py --expected`（§6 の Python 移植）で機械的に再計算した（末尾「前提と注意」）。P3 はこの表に対して `tests/CASES.md` の手順で判定する。**件数の正本はこのファイル**（`DESIGN.md` §7 の記述）。

All data is fictional (no real companies, people, addresses, Gmail ids or calendar ids; domains are `example.jp` / `example.com`, company names use サンプル / テスト / 見本 / ダミー). **The one exception is `holidays.example.json`, which is real Cabinet Office data** (a fictional holiday list would send reminders on public holidays).
Expected values are derived from the Config defaults in `DESIGN.md` §4 and the pseudocode in §6, recomputed mechanically by `make_fixtures.py --expected` (a Python port of §6; see "Assumptions and notes"). P3 asserts against these tables following `tests/CASES.md`. **This file is the source of truth for the counts** (as `DESIGN.md` §7 states).

---

## 1. ファイル一覧 / Files

| ファイル / File | 形式 / Format | 用途 / Purpose |
|---|---|---|
| `invoices.seed.csv` | UTF-8（BOM なし）、LF、`shared/invoices.template.csv` と同じ 20 列・同じ順 | `invoices` シートの初期状態（17 件、`INV-2026-101`〜`117`。テンプレ01 の seed `001`〜`020` と重ならない）/ initial `invoices` sheet (17 rows) |
| `reminders_log.seed.csv` | UTF-8、LF、`shared/reminders_log.template.csv` と同じ 8 列 | 実行前に存在する督促ログ（12 行、9 請求）。「送付済み」「ログだけある」ケースの前提 / pre-existing reminder log (12 rows) |
| `make_fixtures.py` | Python 3 標準ライブラリのみ | 上の 2 CSV を基準日相対で再生成（`--today`）、決定的ビルドの確認（`--check`）、期待結果の再計算（`--expected`、`--run-date`、`--config`）。§2 / generator, determinism check, expectation calculator |
| `holidays.example.json` | JSON | Config `HOLIDAYS` の既定値（2026 年の日本の祝日 18 日、**内閣府 CSV と照合済み**）。§6 / default `HOLIDAYS` (real 2026 public holidays, verified) |
| `calendar_events.example.json` | JSON | `Fetch Holidays`（Google Calendar ノード）の pinned data：当日祝日あり（2 例）／なし `{}`／API 失敗 `{ error }`。§7 / pinned data for the Calendar node |
| `gmail_pinned.example.json` | JSON | `Create Draft`／`Send Reminder` の pinned data（成功 8 件、3 件目だけ失敗の 7 件）。§7 / pinned Gmail results |
| `config.examples.json` | JSON | P3 で `Config` に重ねる値：全ケース共通の `test_common`（試験用の社名・署名・振込先・`TODAY_OVERRIDE`）とケース別の差分。§7 / Config overrides per case |

`DESIGN.md` §7 が仮に挙げた `holidays_pinned.example.json` は `calendar_events.example.json` に名称を変えた（Config の静的リスト `holidays.example.json` と取り違えないため）。`gmail_pinned.example.json` は追加。
`holidays_pinned.example.json` named provisionally in `DESIGN.md` §7 became `calendar_events.example.json` (to avoid confusion with the static list `holidays.example.json`); `gmail_pinned.example.json` is an addition.

---

## 2. 基準日と再生成 / Reference date and regeneration

- **基準日 `TODAY = 2026-10-01`（木曜・祝日でない）**。seed の `due_date` は `TODAY − offset`、`reminders_log.seed.csv` の `sent_at` と `invoices` の `last_reminded_at` / `promised_date` もこの日付から逆算して埋めてある。P3 は Config `TODAY_OVERRIDE = "2026-10-01"` で流すか（`config.examples.json` `test_common`）、`make_fixtures.py --today <実行日>` で当日相対の seed を作り直して `TODAY_OVERRIDE` 無しで流す。
- 依頼時の参照日 2026-09-23 を基準日にしなかった理由：**2026-09-23 は秋分の日**（§6 の内閣府 CSV、`HOLIDAYS` 既定値に含まれる）で、既定 Config では `Check Business Day` が `holiday` を返し `Skip Non-Business Day` で終わる（CASES U21 がまさにこの日を使う）。督促ケースの基準日には使えない。`make_fixtures.py --today 2026-09-23` は動くが、その旨を stderr に警告する。
- 再生成すると `new_deadline` / `final_deadline`（実行日 + 7 日）、`sent_at`、日数、通知の日付が変わる。**判定は `make_fixtures.py --today <日付> --expected` の出力（§6 の Python 移植）と突き合わせる**。基準日を変えても各行の役割・ステージ・件数は変わらない（offset が同じため）。
- `--check` は生成結果とディスク上のファイルをバイト比較する（P2 の `build_workflow.py --check` と同じ考え方）。コミット前に `PYTHONDONTWRITEBYTECODE=1 python3 fixtures/make_fixtures.py --check` を通す。

- **Reference date `TODAY = 2026-10-01`** (Thursday, not a public holiday). Every `due_date` is `TODAY − offset`; `sent_at`, `last_reminded_at` and `promised_date` are derived from the same date. P3 either runs with Config `TODAY_OVERRIDE = "2026-10-01"` (`config.examples.json` `test_common`) or regenerates the seed for the actual run day with `make_fixtures.py --today <date>` and runs without `TODAY_OVERRIDE`.
- 2026-09-23, the reference date named in the task, was not used because **it is Autumnal Equinox Day** (in the Cabinet Office list and in the default `HOLIDAYS`); with the default Config `Check Business Day` returns `holiday` and the run ends in `Skip Non-Business Day` (CASES U21 uses exactly that day). `make_fixtures.py --today 2026-09-23` works but prints a warning to stderr.
- Regenerating shifts `new_deadline` / `final_deadline` (run date + 7), `sent_at`, day counts and notice dates. **Compare against `make_fixtures.py --today <date> --expected`**; roles, stages and counts per row stay the same because the offsets do.
- `--check` byte-compares the generated CSVs with the files on disk (same idea as `build_workflow.py --check`). Run `PYTHONDONTWRITEBYTECODE=1 python3 fixtures/make_fixtures.py --check` before committing.

```
python3 fixtures/make_fixtures.py                                   # rewrite both CSVs for 2026-10-01
python3 fixtures/make_fixtures.py --check                           # OK / DIFF per file, exit 1 on diff
python3 fixtures/make_fixtures.py --check --expected                # expected outcome JSON for 2026-10-01 (default Config + test_common)
python3 fixtures/make_fixtures.py --check --expected --config '{"LANG":"en"}'          # other Config (U28)
python3 fixtures/make_fixtures.py --check --expected --run-date 2026-10-15             # committed seed, run on another day (U15)
python3 fixtures/make_fixtures.py --today 2026-11-04 --out-dir /tmp/seed-1104         # seed for another run day, elsewhere
```

---

## 3. `invoices.seed.csv`（17 件）

列は `shared/invoices.template.csv` と同一。`payer_name_alias` はテンプレ01 用（03 は読まない）。`do_not_remind` は文字列 `TRUE`/`FALSE`（チェックボックス列の boolean でも同じ判定、U07-b）。`notes` に役割を日英で書いてある。「offset」は `TODAY − due_date`（日）。
Columns are identical to `shared/invoices.template.csv`. `payer_name_alias` is for Template 01 (03 never reads it). `do_not_remind` is the string `TRUE`/`FALSE` (a boolean checkbox column behaves the same, U07-b). `notes` carries the role in JA / EN. "offset" = `TODAY − due_date` in days.

「期待」は既定 Config（`SEND_MODE=draft`、stage 0 OFF、`GROUP_BY_CUSTOMER=true`）・`TODAY_OVERRIDE=2026-10-01` で 1 回流したときの結果。`remaining` は文面の `¥{remaining}`。`log_row` / `invoice_update` は `Collect Send Results` の出力（= `Record Reminder Log` / `Update Invoice Stage` に書かれる行）。
"Expected" is the outcome of one run with the default Config (`SEND_MODE=draft`, stage 0 off, `GROUP_BY_CUSTOMER=true`) and `TODAY_OVERRIDE=2026-10-01`. `remaining` is the `¥{remaining}` in the copy; `log_row` / `invoice_update` are the `Collect Send Results` items (= the rows written by `Record Reminder Log` / `Update Invoice Stage`).

| invoice_id | customer_id / name | customer_email | amount / paid_amount | due_date（offset） | status | remind_stage / last_reminded_at | promised_date / do_not_remind | reminders_log seed | ケース / Case | 期待 / Expected |
|---|---|---|---|---|---|---|---|---|---|---|
| INV-2026-101 | C-101 株式会社サンプル商事 | keiri@example.jp | 33000 / 0 | 2026-10-04（−3） | unpaid | 0 / — | — / FALSE | — | U17（stage 0） | 既定では対象外 `no_stage_due`。stage 0 ON（U17）なら件名 `お支払期限のご案内（請求書番号 INV-2026-101）`、残額 ¥33,000、`log_row stage 0`、`invoice_update remind_stage 0`（変わらない）・`last_reminded_at` 更新 |
| INV-2026-102 | C-102 テスト工業有限会社 | ap@example.com | 55000 / 0 | 2026-09-30（+1） | unpaid | 0 / — | — / FALSE | — | **U01** | **stage 1**：件名 `お支払いのご確認のお願い（請求書番号 INV-2026-102）`、¥55,000。`log_row (102, 1, draft)`、`invoice_update { status unpaid, remind_stage 1 }` |
| INV-2026-103 | C-103 見本デザイン合同会社 | info@example.jp | 128000 / 0 | 2026-09-24（+7） | unpaid | 1 / 2026-09-25T10:00:05+09:00 | — / FALSE | (103, 1) | **U03** | **stage 2**：件名 `【再送】お支払いのお願い（請求書番号 INV-2026-103）`、¥128,000、`new_deadline 2026-10-08`、`（超過）`、お振込先あり。`log_row (103, 2)`、`remind_stage 2` |
| INV-2026-104 | C-104 株式会社ダミー製作所 | billing@example.com | 44000 / 0 | 2026-09-17（+14） | unpaid | 2 / 2026-09-24T10:00:06+09:00 | — / FALSE | (104, 1) (104, 2) | **U04** | **stage 3 → escalated**：件名 `【重要】お支払いに関する最終のご連絡（請求書番号 INV-2026-104）`、¥44,000、`final_deadline 2026-10-08`。`log_row (104, 3)`、`invoice_update { status escalated, remind_stage 3 }`、`escalated` 通知（`14日超過`） |
| INV-2026-105 | C-105 サンプルシステム株式会社 | ap@example.jp | 250000 / 100000 | 2026-09-30（+1） | partial（paid_date 2026-09-26、auto） | 0 / — | — / FALSE | — | **U08** | **stage 1、残額 ¥150,000**（`amount` の 250,000 ではない）。`log_row (105, 1)`、`invoice_update { status partial, remind_stage 1 }` |
| INV-2026-106 | C-106 有限会社サンプル印刷 | paid@example.com | 66000 / 66000 | 2026-09-01（+30） | paid（paid_date 2026-08-30） | 0 / — | — / FALSE | — | **U05** | 対象外 `not_open`。メール・ログ・更新・通知のどこにも出ない |
| INV-2026-107 | C-107 テスト商事株式会社 | keiri2@example.jp | 88000 / 0 | 2026-09-24（+7） | unpaid | 1 / 2026-09-25T10:00:07+09:00 | **2026-10-15** / FALSE | (107, 1) | **U06** | 対象外 `promised_future`（promised_date ≥ today）。U06-b（`TODAY_OVERRIDE=2026-10-16`）では対象になり、22 日超過なので **stage 3**（`DESIGN.md` §7 の「stage 2」は誤り。§8） |
| INV-2026-108 | C-108 株式会社テスト物産 | keiri@example.com | 700000 / 0 | 2026-09-24（+7） | unpaid | 1 / 2026-09-25T10:00:09+09:00 | — / FALSE | (108, 1)（109 と同じ ID） | **U11** | **stage 2、109 と 1 通**：件名 `【再送】お支払いのお願い（請求書番号 INV-2026-108、INV-2026-109）`、明細ブロック 2 回（¥700,000 / ¥534,567）＋お振込先 1 回。`log_row (108, 2)` と `(109, 2)` は同じ `gmail_message_id`・同じ件名 |
| INV-2026-109 | C-108 株式会社テスト物産 | keiri@example.com | 534567 / 0 | 2026-09-24（+7） | unpaid | 1 / 2026-09-25T10:00:09+09:00 | — / FALSE | (109, 1) | **U11** | 同上。`invoice_update` は 108・109 に 1 件ずつ（`remind_stage 2`） |
| INV-2026-110 | C-110 ダミー企画有限会社 | stop@example.jp | 27500 / 0 | 2026-09-24（+7） | unpaid | 1 / 2026-09-25T10:00:10+09:00 | — / **TRUE** | (110, 1) | **U07** | 対象外 `do_not_remind`（stage 1 送付後に TRUE にした想定） |
| INV-2026-111 | C-111 Sample Overseas LLC | overseas@example.com | 128000 / 0 | 2026-09-30（+1）、**USD** | unpaid | 0 / — | — / FALSE | — | **U14** | 対象外 `non_jpy`。警告 `{ type: non_jpy_invoice, invoice_id: INV-2026-111, currency: USD }` → 通知 `・non_jpy_invoice INV-2026-111 USD` |
| INV-2026-112 | C-112 見本 一郎 | **（空）** | 41800 / 0 | 2026-09-30（+1） | unpaid | 0 / — | — / FALSE | — | **U18** | 対象外 `missing_email`。警告 `{ type: missing_email, invoice_id: INV-2026-112 }` → 通知 `・missing_email INV-2026-112` |
| INV-2026-113 | C-113 サンプル物流株式会社 | ap3@example.jp | 15400 / 0 | 2026-09-24（+7） | unpaid | 1 / 2026-09-25T10:00:11+09:00 | **2026-09-20（過去）** / FALSE | (113, 1) | **U13** | **stage 2**（過去の promised_date は無視）：件名 `【再送】お支払いのお願い（請求書番号 INV-2026-113）`、¥15,400。`log_row (113, 2)`、`remind_stage 2` |
| INV-2026-114 | C-114 テスト建材株式会社 | late@example.com | 57200 / 0 | 2026-09-01（+30） | unpaid | 0 / — | — / FALSE | — | **U19** | **stage 3（1・2 を飛ばす）→ escalated**：件名 `【重要】…（請求書番号 INV-2026-114）`、¥57,200。`log_row (114, 3)`、`invoice_update { escalated, 3 }`、`escalated` 通知（`30日超過`） |
| INV-2026-115 | C-115 ダミー出版株式会社 | cancel@example.jp | 12100 / 0 | 2026-09-24（+7） | **cancelled** | 0 / — | — / FALSE | — | （取消） | 対象外 `not_open` |
| INV-2026-116 | C-116 有限会社見本エンジニアリング | esc@example.com | 49500 / 0 | 2026-09-10（+21） | **escalated** | 3 / 2026-09-24T10:00:12+09:00 | — / FALSE | (116, 1) (116, 2) (116, 3) | （最終済み） | 対象外 `not_open`。以後の自動督促なし（+30 でも同じ。U15 で確認） |
| INV-2026-117 | C-117 サンプル食品株式会社 | retry@example.jp | 38500 / 0 | 2026-09-30（+1） | unpaid | **0** / — | — / FALSE | **(117, 1)**（今日 10:00:08） | **U20** / U16 | 対象外 `already_logged`（`invoices` 側の更新が失敗した状態の再現。ログだけで止まる） |

**既定 Config・`TODAY_OVERRIDE=2026-10-01` の合計 / Totals for the default run**

| 項目 / Item | 期待 / Expected |
|---|---|
| `Select Due Invoices.candidates` | 8 件：102(1) 103(2) 104(3) 105(1) 108(2) 109(2) 113(2) 114(3)（括弧は `target_stage`） |
| `skipped` | `{ not_open: 3, do_not_remind: 1, promised_future: 1, no_stage_due: 1, already_at_stage: 0, already_logged: 1, non_jpy: 1, missing_email: 1, bad_due_date: 0 }`（合計 9 ＋ candidates 8 = 17） |
| `warnings` | 2 件：`non_jpy_invoice INV-2026-111 USD`、`missing_email INV-2026-112`（この順） |
| `Group By Customer.groups` → `Build Reminder Emails` | **7 通**（§6.5 の並び：stage 昇順 → `customer_name` の `localeCompare`）：`C-105\|1` 105 → `C-102\|1` 102 → `C-113\|2` 113 → `C-108\|2` 108+109 → `C-103\|2` 103 → `C-114\|3` 114 → `C-104\|3` 104 |
| `log_row` | **8 行**（108・109 は同じ `gmail_message_id`）、`mode draft`、`channel gmail`、`sent_at` = 実行時刻 `2026-10-01THH:mm:ss+09:00` |
| `invoice_update` | **8 行**：105 `partial/1`、102 `unpaid/1`、113・108・109・103 `unpaid/2`、114・104 **`escalated/3`**。`last_reminded_at` = `sent_at` と同じ値 |
| `summary` | `n 7, emails_ok 7, emails_failed 0, escalated [114, 104]` |
| オーナー通知 / owner notices | 3 アイテム：`【未入金リマインド 2026-10-01】本日の下書き 7 件`（明細 8 行 ＋ `■ warnings` 2 行、先頭に `TODAY_OVERRIDE=2026-10-01`）、`【未入金リマインド】請求書 INV-2026-114 が最終段階（stage 3）に到達しました`、同 `INV-2026-104`。全文は `tests/CASES.md` §3 |

Config を変えたときの件数（`make_fixtures.py --expected --config …` で再計算。詳細は `tests/CASES.md`）/ Counts under other Config values:

| 変更 / Change | メール / Emails | log_row | invoice_update | 差分 / Difference |
|---|---|---|---|---|
| `STAGES[0].enabled = true`（U17） | 8 | 9 | 9 | 101 が stage 0（先頭）。`invoice_update.remind_stage 0`、`no_stage_due 0` |
| `GROUP_BY_CUSTOMER = false`（U11-b） | 8 | 8 | 8 | 108 と 109 が別の通（件名は原本と同一形）。`gmail_message_id` は別 |
| `SEND_MODE = send`（U10） | 7 | 8（`mode sent`） | 8 | 通知先頭に `SEND_MODE=send` |
| `SEND_MODE = owner_only`（U23） | 7（一覧のみ） | **0** | **0** | 通知先頭に `SEND_MODE=owner_only`、`n 7` |
| `LANG = en`（U28） | 7 | 8 | 8 | 件名 `Payment reminder — Invoice INV-2026-102` 等、通知 `[Unpaid Reminder 2026-10-01] 7 drafts created today` |
| `TODAY_OVERRIDE = 2026-10-15`（U15） | 9 | 10 | 10 | 101 → stage 2（11 日）、102・105・117 → stage 3（15 日、117 はログが stage 1 のみ）、他はすべて stage 3。`escalated` 9 件 |
| `TODAY_OVERRIDE = 2026-10-16`（U06-b） | 10 | 11 | 11 | 上に加え 107 が対象（promised_date 経過、22 日 → stage 3） |
| `TODAY_OVERRIDE = 2026-10-03` ＋ `SKIP_WEEKENDS=false`（U09-c） | 7 | 8 | 8 | 既定と同じ 7 通（日数が +2） |

---

## 4. `reminders_log.seed.csv`（12 行、`sent_at` 昇順）

すべて `mode draft`・`channel gmail`。件名は `shared/messages.ja.json` の `reminder.stage<n>.subject` そのもの（108・109 はまとめて送った stage 1 の件名 `…（請求書番号 INV-2026-108、INV-2026-109）` を 2 行が共有し、`gmail_message_id` も同じ。`shared/sheets-schema.md` の約束）。`gmail_message_id` は架空の 16 桁 hex。
All rows are `mode draft` / `channel gmail`. Subjects are the literal `reminder.stage<n>.subject` of `shared/messages.ja.json`; 108 / 109 were sent as one grouped stage-1 email, so both rows share the grouped subject and the same `gmail_message_id` (`shared/sheets-schema.md`). Gmail ids are fictional 16-hex strings.

| invoice_id | stage | to | subject | sent_at | gmail_message_id | 役割 / Role |
|---|---|---|---|---|---|---|
| INV-2026-116 | 1 | esc@example.com | お支払いのご確認のお願い（請求書番号 INV-2026-116） | 2026-09-11T10:00:12+09:00 | 18f60a1b2c3d4e01 | escalated 済みの履歴 / history of the escalated invoice |
| INV-2026-116 | 2 | esc@example.com | 【再送】お支払いのお願い（請求書番号 INV-2026-116） | 2026-09-17T10:00:12+09:00 | 18f60a1b2c3d4e02 | 同上 |
| INV-2026-104 | 1 | billing@example.com | お支払いのご確認のお願い（請求書番号 INV-2026-104） | 2026-09-18T10:00:06+09:00 | 18f60a1b2c3d4e03 | U04 の前提 |
| INV-2026-104 | 2 | billing@example.com | 【再送】お支払いのお願い（請求書番号 INV-2026-104） | 2026-09-24T10:00:06+09:00 | 18f60a1b2c3d4e04 | U04 の前提（`remind_stage 2` と一致） |
| INV-2026-116 | 3 | esc@example.com | 【重要】お支払いに関する最終のご連絡（請求書番号 INV-2026-116） | 2026-09-24T10:00:12+09:00 | 18f60a1b2c3d4e05 | 同上（`remind_stage 3` と一致） |
| INV-2026-103 | 1 | info@example.jp | お支払いのご確認のお願い（請求書番号 INV-2026-103） | 2026-09-25T10:00:05+09:00 | 18f60a1b2c3d4e06 | U03 の前提 |
| INV-2026-107 | 1 | keiri2@example.jp | お支払いのご確認のお願い（請求書番号 INV-2026-107） | 2026-09-25T10:00:07+09:00 | 18f60a1b2c3d4e07 | U06 の前提 |
| INV-2026-108 | 1 | keiri@example.com | お支払いのご確認のお願い（請求書番号 INV-2026-108、INV-2026-109） | 2026-09-25T10:00:09+09:00 | 18f60a1b2c3d4e08 | U11 の前提（グループ送付の 1/2） |
| INV-2026-109 | 1 | keiri@example.com | 同上 | 2026-09-25T10:00:09+09:00 | 18f60a1b2c3d4e08 | U11 の前提（2/2、同じ ID） |
| INV-2026-110 | 1 | stop@example.jp | お支払いのご確認のお願い（請求書番号 INV-2026-110） | 2026-09-25T10:00:10+09:00 | 18f60a1b2c3d4e09 | U07 の前提 |
| INV-2026-113 | 1 | ap3@example.jp | お支払いのご確認のお願い（請求書番号 INV-2026-113） | 2026-09-25T10:00:11+09:00 | 18f60a1b2c3d4e0a | U13 の前提 |
| INV-2026-117 | 1 | retry@example.jp | お支払いのご確認のお願い（請求書番号 INV-2026-117） | **2026-10-01T10:00:08+09:00** | 18f60a1b2c3d4e0b | **U20 / U16**：当日の先行実行で `Record Reminder Log` は成功したが `Update Invoice Stage` が失敗した状態（`remind_stage` は 0 のまま）。ログだけで再送を止める二重防御の実証 |

整合性（`make_fixtures.py` が保証し、P1 で Python 検証済み）：全行の `invoice_id` は `invoices.seed.csv` に存在、`to` は当該請求の `customer_email` と一致、`(invoice_id, stage)` は重複なし、`remind_stage = n` の請求は stage 1〜n のログを全て持つ（117 だけが例外で、それが U20 の意図）。
Consistency (guaranteed by `make_fixtures.py`, verified in Python in P1): every `invoice_id` exists in `invoices.seed.csv`, `to` equals that invoice's `customer_email`, `(invoice_id, stage)` is unique, and every invoice with `remind_stage = n` has log rows for stages 1..n (117 is the deliberate exception, which is the point of U20).

---

## 5. 行 → ケース対応の早見表 / Row-to-case map

依頼の要件（`due −3 / +1 / +7 / +14 / +30`、partial、promised_date 未来、do_not_remind、paid、cancelled、非 JPY、同一顧客 2 件、ログ済み）と `DESIGN.md` §7 の追加ケースを、どの行が担うか。
Which row serves which requirement (the task's list and the `DESIGN.md` §7 extras).

| 要件 / Requirement | 行 / Row | ケース / Case |
|---|---|---|
| due −3、stage 0 候補（既定 OFF） / stage-0 candidate | 101 | U17（既定では `no_stage_due`） |
| +1 → stage 1 | 102 | U01、U02、U16 |
| +7 → stage 2 | 103 | U03 |
| +14 → stage 3 → escalated | 104 | U04、U04-b |
| +30、既に stage 3 / escalated（再送なし）/ already escalated | 116（+21、`status escalated`、`remind_stage 3`、ログ 1〜3） | not_open（U15 の +14 日でも対象外） |
| +30、未送付のまま大幅超過 / long overdue, nothing sent | 114 | U19 |
| partial（残額表示）/ remaining shown | 105（+1） | U08 |
| promised_date 未来 / future → skip | 107（+7、2026-10-15） | U06、U06-b |
| promised_date 過去 / past → continue | 113（+7、2026-09-20） | U13 |
| do_not_remind TRUE | 110（+7） | U07、U07-b |
| paid → 対象外 | 106（+30） | U05 |
| cancelled → 対象外 | 115（+7） | （not_open） |
| 非 JPY → 警告 / non-JPY warning | 111（+1、USD） | U14 |
| customer_email 空 → 警告 | 112（+1） | U18 |
| 同一顧客 2 件 → 1 通 / grouping | 108 + 109（+7、C-108） | U11、U11-b |
| ログ済み (invoice_id, stage 1) → skip | 117（+1、ログのみ） | U20、U16 |

---

## 6. `holidays.example.json`（Config `HOLIDAYS` の既定値）

- 出典：内閣府「国民の祝日について」の CSV `https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv`（Shift_JIS、見出し `国民の祝日・休日月日,国民の祝日・休日名称`）。**2026-09-23 に取得**（HTTP 200、21,538 バイト、1,068 行）。`2026/` で始まる 18 行を `yyyy-MM-dd` に変換したものが `HOLIDAYS`。名称は `names_from_source` に併記。
- `DESIGN.md` §4 の既定値 18 日と 1 日ずつ一致することを Python で確認した（P1）。P2 は `build_workflow.py` のアサートで `workflow.json` の埋め込み値がこのファイルと一致することを確認する（`DESIGN.md` §8.3-2）。
- 2026-09-21（敬老の日）・09-22（国民の休日）・09-23（秋分の日）が連続するため、CASES U09 / U12 / U21 はこの 3 日を使う。年末年始は祝日ではないので含めない（自社休業日として買い手が追記）。
- Source: the Cabinet Office CSV above (Shift_JIS), **fetched 2026-09-23** (HTTP 200, 21,538 bytes, 1,068 lines). The 18 rows starting with `2026/` converted to `yyyy-MM-dd` form `HOLIDAYS`; names are kept in `names_from_source`. Verified in Python against `DESIGN.md` §4 (P1); P2 asserts the value embedded in `workflow.json` against this file (`DESIGN.md` §8.3-2). CASES U09 / U12 / U21 use the three consecutive holidays 09-21 / 09-22 / 09-23. Year-end is not a public holiday and is left to the buyer.

---

## 7. pinned data・Config の例 / Pinned data and Config examples

### 7.1 `calendar_events.example.json`（`Fetch Holidays`）

| キー / Key | 中身 / Content | 使うケース / Cases |
|---|---|---|
| `holiday_2026-09-21` | 終日イベント 1 件：`summary 敬老の日`、`start.date 2026-09-21`、`end.date 2026-09-22`（end は排他）、`status confirmed`、`transparency transparent`、`creator/organizer` = 祝日カレンダー自身 | U09（`TODAY_OVERRIDE=2026-09-21`）→ `Check Business Day { reason holiday, holiday_name 敬老の日, holiday_source calendar }` |
| `holiday_2026-10-12` | 同形（スポーツの日、月曜） | 2 例目 |
| `none` | `[{ "json": {} }]`（Always Output Data が API の `items: []` から作る形） | 営業日のケース全部（U01 …） |
| `error` | `[{ "json": { "error": "Forbidden - perhaps check your credentials?" } }]`（On Error = Continue (regular output) の形） | U12 / U12-b → `holiday_calendar_unavailable` 警告 ＋ `HOLIDAYS` フォールバック |

形の出典：n8n Google Calendar ノード Event operations「Get Many」（https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.googlecalendar/event-operations.md）が参照する Google Calendar API Events リソース（https://developers.google.com/calendar/api/v3/reference/events：`kind, etag, id, status, htmlLink, created, updated, summary, description, creator{email, displayName, self}, organizer{…}, start{date|dateTime}, end{…}, transparency, visibility, iCalUID, sequence, eventType`）、および n8n-nodes-base 2.40.2 `GoogleCalendar.node.js`（`getAll` は `items` を 1 イベント 1 アイテムで返し、v1.3 は `sortItemKeysByPriorityList(['id','summary','start','end','attendees','creator','organizer','description','location','created','updated'])` でキー順を並べ替える。失敗時は `{ error: error.message }`）。いずれも 2026-09-23 取得。**値（id / etag / htmlLink / 日時）は例示**。P2 で実出力を 1 回取得し、形が違えばこのファイルと `DESIGN.md` §3.2 を更新する（`DESIGN.md` §8.3-1）。
Shape sources: the n8n Google Calendar Event operations page (Get Many), the Google Calendar API Events resource it points to, and `GoogleCalendar.node.js` of n8n-nodes-base 2.40.2 (`getAll` returns one item per event, v1.3 re-orders keys by the priority list above, failures become `{ error }`), all read 2026-09-23. **Values are illustrative**; P2 captures one real output and updates this file and `DESIGN.md` §3.2 if the shape differs.

`Fetch Holidays` を**無効化**するケース（U22）は pin しない：無効化ノードは入力（`Resolve Run Date` のアイテム）をそのまま通す（ASSUMPTIONS A36）。`USE_HOLIDAY_CALENDAR=false`（U21）では IF が迂回するので pin は不要。
U22 (node deactivated) must not pin the node: a deactivated node passes its input through (ASSUMPTIONS A36). With `USE_HOLIDAY_CALENDAR=false` (U21) the IF bypasses it and no pin is needed.

### 7.2 `gmail_pinned.example.json`（`Create Draft` / `Send Reminder`）

| キー / Key | 中身 / Content | 使うケース / Cases |
|---|---|---|
| `Create Draft.draft_ok` | 8 件 `{ id: "r-1000…", message: { id: "18f7000000000001"…"…08", threadId, labelIds: ["DRAFT"] } }`（Draft リソース） | draft のケース。**期待メール数ぶんに切る**（既定 7 → `[0:7]`、U11-b / U17 は 8） |
| `Create Draft.draft_7_third_error` | 7 件、3 件目だけ `{ error: "Invalid email address (item 2)" }` | U25 |
| `Send Reminder.send_ok` | 8 件 `{ id: "18f7000000000001"…, threadId, labelIds: ["SENT"] }`（Message リソース） | U10（`[0:7]`） |

`gmail_message_id` に記録されるのは draft では `message.id`、send では `id`（`DESIGN.md` §3.7）。両方とも `18f7000000000001`〜 なので、U01 と U10 の期待 `log_row` は `mode` 以外同じ。**pin の件数がメール数と違うと `Collect Send Results` が台帳を書かずに throw する**（D08）。形の出典は Gmail Draft operations / Message operations の公式ページと n8n-nodes-base 2.40.2 `GmailV2.node.js`（`POST /gmail/v1/users/me/drafts` / `…/messages/send` の応答をそのまま返す。Continue On Fail の失敗アイテムは `{ error: "<message> (item <i>)" }`、`@` の無い宛先は `prepareEmailsInput` が `Invalid email address` を投げる）。
`gmail_message_id` is `message.id` for drafts and `id` for sends (`DESIGN.md` §3.7); both use `18f7000000000001`… so the expected `log_row`s of U01 and U10 differ only in `mode`. **A pin whose length differs from the number of emails makes `Collect Send Results` throw without writing** (D08). Shapes: the Gmail Draft / Message operations pages and `GmailV2.node.js` (responses of `POST …/drafts` and `…/messages/send` returned as-is; Continue On Fail yields `{ error: "<message> (item <i>)" }`; an address without `@` raises `Invalid email address` in `prepareEmailsInput`).

### 7.3 `config.examples.json`

`test_common`（全ケース）：`SHEET_ID TEST_SHEET`、`TODAY_OVERRIDE 2026-10-01`、`NOTIFY_CHANNELS []`（U26 以外は通知ノードを IF で止める）、`COMPANY サンプル株式会社`、`SENDER_NAME 見本 太郎`、`SIGNATURE サンプル株式会社 経理部 見本 太郎\nTEL 00-0000-0000 / keiri@example.jp`、`BANK_DETAILS サンプル銀行 本店 普通 1234567 カ）サンプル`、`CC` / `BCC` 空。本文の期待値（`tests/CASES.md` §3）はこの値で埋めてある。`cases` はケースごとの差分（`SEND_MODE`、`STAGES`、`GROUP_BY_CUSTOMER`、`USE_HOLIDAY_CALENDAR`、`TODAY_OVERRIDE`、`LANG`、`NOTIFY_CHANNELS`）。
`test_common` applies to every case; the expected bodies in `tests/CASES.md` §3 are filled with these values. `cases` holds the per-case differences.

---

## 8. 前提と注意 / Assumptions and notes

- **初期状態**：期待値は「`invoices` = seed、`reminders_log` = seed」に対する 1 回目の実行。2 回目以降（U02 / U04-b / U16 / U17-b）は 1 回目の `invoice_update` / `log_row` を pinned data に反映してから流す。
- **順序**：メール・`log_row`・`invoice_update`・通知明細の並びは `DESIGN.md` §6.5 の並び（stage 昇順 → `customer_name` の `localeCompare` → `group_key`）。JS の `localeCompare` と Python の既定比較はこの seed の名前では一致するが、判定は**内容で行い、位置で行わない**（Gmail pin との添字突合だけが順序に依存し、U25 の「3 件目」は実行結果の `Build Reminder Emails` の順で確認する）。
- **時刻**：`sent_at` / `last_reminded_at` は実行開始時刻（`Resolve Run Date.now_iso`、`yyyy-MM-ddTHH:mm:ss+09:00`）。`--expected` は `10:00:03` を仮置きする。判定は日付部分（`TODAY_OVERRIDE` の日付）と形式で行う。
- **`--expected` は Python 移植**：`DESIGN.md` §6.4〜§6.8 を構造をそろえて移植したもので、`toInt` の全角・カンマ・`¥` 除去、`normalizeDate` の表記ゆれ、`localeCompare`、Slack Blocks 分割は簡略化している（seed には全角数字も表記ゆれも無い）。P2 で `code/*.js` ができたら `tests/unit/run-code-node.mjs` 相当で同じ seed を流し、差があれば JS を正とする。
- **通貨**：111 だけ USD。テンプレ01 の seed と違い USD 行を seed 本体に入れているのは、03 の既定通知に警告が 2 件常に出ることを期待値に含めるため（U02 で「警告があるので通知は出る」を確かめられる）。
- **105 の `paid_date`**：一部入金は期限前（2026-09-26）。テンプレ01 が書く `matched_txn_ids` / `match_confidence auto` の形にしてある（03 は読まない）。
- **117 のログ**：`sent_at` が当日 10:00:08 なのは「当日の先行実行で `Update Invoice Stage` だけ失敗した」状態の再現（U16 の 2 回目相当）。`TODAY_OVERRIDE` を別日にすると「過去の実行」の意味になるが判定（`already_logged`）は変わらない。
- **名前**：テンプレ01 の seed と一部同じ社名（株式会社サンプル商事、テスト工業有限会社、株式会社テスト物産、サンプルシステム株式会社）を `DESIGN.md` §3 の例に合わせて使うが、`customer_id`（`C-1xx`）と `invoice_id` は別。両テンプレを同じシートで試すときは ID が衝突しない。
- **2026-09-23**：秋分の日。`--today 2026-09-23` で seed は作れるが既定 Config では非営業日として終わる（§2）。

- **Seed state**: expectations are for the first run against `invoices` = seed and `reminders_log` = seed. Later runs (U02 / U04-b / U16 / U17-b) apply the first run's `invoice_update` / `log_row` items to the pinned data first.
- **Order**: emails, `log_row`s, `invoice_update`s and notice lines follow `DESIGN.md` §6.5 (stage ascending → `customer_name` via `localeCompare` → `group_key`). JS `localeCompare` and Python's default comparison agree for these names, but assert **by content, not position**; only the index pairing with the Gmail pin depends on order (U25's "third item" is read from the actual `Build Reminder Emails` output).
- **Times**: `sent_at` / `last_reminded_at` are the run start (`Resolve Run Date.now_iso`, `yyyy-MM-ddTHH:mm:ss+09:00`); `--expected` uses a placeholder `10:00:03`. Assert the date part (the `TODAY_OVERRIDE` date) and the format.
- **`--expected` is a Python port** of `DESIGN.md` §6.4–§6.8 with the same structure; `toInt`'s full-width / comma / `¥` stripping, `normalizeDate` variants, `localeCompare` and Slack block chunking are simplified (the seed contains none of those variants). Once `code/*.js` exists (P2), run the same seed through a `tests/unit/run-code-node.mjs` equivalent; the JS wins on any difference.
- **Currency**: only 111 is USD. Unlike Template 01's seed, the USD row lives in the seed itself so that the default notice always carries two warnings (U02 can then show that warnings alone still produce a notice).
- **105 `paid_date`**: the partial payment is before the due date (2026-09-26) in the `matched_txn_ids` / `auto` shape Template 01 writes (03 never reads it).
- **117's log row** is dated today 10:00:08 to reproduce "an earlier run today where only `Update Invoice Stage` failed" (the second run of U16). Another `TODAY_OVERRIDE` turns it into a past run; the verdict (`already_logged`) does not change.
- **Names**: a few company names are shared with Template 01's seed to match the examples in `DESIGN.md` §3, but `customer_id` (`C-1xx`) and `invoice_id` ranges are distinct, so both templates can be tried on one sheet without collisions.
- **2026-09-23** is Autumnal Equinox Day; `--today 2026-09-23` builds a seed but the default Config ends the run as a non-business day (§2).
