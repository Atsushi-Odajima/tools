# CLAUDE.md — Four Sellable n8n Templates for Payment Operations

> **How to use**: Place this file at the repository root as `CLAUDE.md`, start `claude`, and say "Read CLAUDE.md and start from P0". If it feels too long, split the "Template 01–04" sections into `specs/0X-*.md` and leave `@specs/01-reconciliation.md` references in the body.
> **Using Codex**: Copy this file as `AGENTS.md` and translate §2.3 (MCP setup) into Codex's configuration method (n8n-mcp works with clients other than Claude Code).
> **Legend**: `[HUMAN]` = a step only a human can do (OAuth consent, API key issuance, etc.). The agent cannot substitute for it; if incomplete, log it in `BLOCKERS.md` and move on.

---

## 0. Role and Goal

You are an expert n8n workflow builder and technical writer. Your job is to turn the owner's domain knowledge — ten years at a payment service provider running admin consoles and merchant support for bank transfer, credit card, convenience-store and QR-code payments — into **paid templates a buyer can deploy in their own environment in under 30 minutes**.

Four deliverables. **Recommended build order: 01 → 03 → 04 → 02** (02 needs a freee test company plus OAuth, which is the most likely to stall on a human step, so it goes last).

| # | Product | One-liner | Suggested price (JA / EN) |
|---|---|---|---|
| 01 | Bank Deposit Reconciliation | Bank CSV / deposit-notification email → auto-match against invoice sheet → notify | ¥4,980 / $39 |
| 02 | Payment Webhook → Accounting | Stripe / PayPal events auto-booked into freee / Money Forward / generic CSV; refunds & chargebacks raise alerts instead | ¥7,980 / $69 |
| 03 | Unpaid Invoice Reminder | Staged reminders after due date (draft → approve → send); stops automatically on payment | ¥3,980 / $29 |
| 04 | Refund & Chargeback Tracker | Detect → ledger → evidence-deadline reminders → monthly chargeback rate | ¥4,980 / $39 |

01 and 03 share one Google Sheet (`invoices`). 02 and 04 share the same Stripe / PayPal events. **Finalize the shared schema (§5) before starting any individual template.**

---

## 1. Hard Rules

1. **Built-in nodes only.** No community nodes (n8n Cloud buyers cannot install them). No `Read/Write Files from Disk` either (unavailable on Cloud).
2. **No secrets or IDs in the JSON.** Credentials are referenced by name only. Sheet IDs, Slack channel IDs, email addresses, etc. live as placeholders in the Config node. Before export, run `grep -E "sk_(live|test)|whsec_|xoxb-|Bearer [A-Za-z0-9]|@gmail\.com"` and record that it returns zero hits.
3. **Every tunable lives in the Config node.** No hard-coded values in other nodes.
4. **Never write an API call from memory.** For freee / Stripe / PayPal / LINE / Chatwork / n8n, fetch the official docs with WebFetch before implementing, and record the URL and the date checked in `ASSUMPTIONS.md`.
5. **Tests must actually run and pass.** A passing `validate_workflow` is not a passing test. Push fixtures through the local n8n instance and record execution IDs and results in `tests/RESULTS.md`. Do not commit a phase until it passes.
6. **Idempotent.** Running the same input twice must not change state (no double reconciliation, double booking, or double reminders).
7. **Safe defaults that cannot damage the buyer's environment.** Reminders default to "create draft"; accounting defaults to "dry-run (sheet only)". Real sending / real booking must be explicitly enabled in Config.
8. **Bilingual.** Node names in English (ASCII, because expressions reference them). Sticky Notes in both JA and EN. Notification and email copy switch on Config `LANG` (`ja` / `en`). README / SETUP / listings are separate JA and EN files.
9. **Never wait on a human.** Where a `[HUMAN]` prerequisite is missing, substitute mocks / fixtures, keep going, and write "what is needed and how to verify it" in `BLOCKERS.md`.
10. **Do not reproduce the owner's employer-specific specs, screens, or APIs.** Stay within general industry knowledge.

---

## 2. Environment Setup (P0, once)

### 2.1 [HUMAN] Prerequisites
- Windows with Docker Desktop (WSL2), Node.js 20+, Git, Claude Code installed
- Google Cloud OAuth client (Web) with Sheets / Drive / Gmail / Calendar APIs enabled. Register "Google Sheets OAuth2", "Gmail OAuth2", "Google Drive OAuth2", "Google Calendar OAuth2" credentials in n8n
- A Slack test channel `#n8n-test` and a Slack credential in n8n
- Stripe test-mode API key and Stripe CLI (`stripe login`)
- PayPal Developer Sandbox app (client id / secret) and a Sandbox webhook ID
- freee: a developer test company and a registered OAuth app (02 only)
- LINE Developers: a Messaging API channel (channel access token, your own userId) (optional)
- Chatwork API token (optional)

### 2.2 Local n8n (`infra/docker-compose.yml`)
```yaml
services:
  n8n:
    image: docker.n8n.io/n8nio/n8n
    ports:
      - "5678:5678"
    environment:
      - GENERIC_TIMEZONE=Asia/Tokyo
      - TZ=Asia/Tokyo
      - WEBHOOK_URL=http://localhost:5678/
      - N8N_PUBLIC_API_DISABLED=false
    volumes:
      - n8n_data:/home/node/.n8n
volumes:
  n8n_data:
```
After start-up, create the initial user at `http://localhost:5678` and issue an API key under Settings → n8n API ([HUMAN]). Record the n8n version (shown in Settings) in `ASSUMPTIONS.md` and in the README's "Supported version".

### 2.3 Claude Code MCP (`.mcp.json` at the repo root)
```json
{
  "mcpServers": {
    "n8n-mcp": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "n8n-mcp"],
      "env": {
        "MCP_MODE": "stdio",
        "LOG_LEVEL": "error",
        "DISABLE_CONSOLE_OUTPUT": "true",
        "N8N_API_URL": "http://localhost:5678",
        "N8N_API_KEY": "${N8N_API_KEY:-}"
      }
    }
  }
}
```
Pass `N8N_API_KEY` as an environment variable (never write the key into the file). Claude Code expands `${VAR}`; if the variable is unset and has no default, the whole config fails to parse, so keep the `${N8N_API_KEY:-}` default.

CLI alternative:
```
claude mcp add --transport stdio --scope project --env MCP_MODE=stdio --env N8N_API_URL=http://localhost:5678 --env N8N_API_KEY=$N8N_API_KEY n8n-mcp -- npx -y n8n-mcp
```

Also install czlonkowski/n8n-skills (Claude Code skills for n8n expression syntax, node configuration and avoiding validation loops) exactly as that repository's README describes. Fetch the README; do not write the steps from memory.

### 2.4 Verification (this is the P0 gate)
- `claude mcp list` shows n8n-mcp as Connected
- `/mcp` inside Claude Code lists `n8n_create_workflow` (proof the API connection works)
- Build and run a minimal workflow (Manual Trigger → Set → Slack `#n8n-test`). When the message lands in Slack, P0 is done. This workflow may be deleted.

### 2.5 Receiving webhooks from outside (02, 04)
- Stripe: `stripe listen --forward-to localhost:5678/webhook/<path>`; fire events with `stripe trigger charge.succeeded` etc.
- PayPal: expose local n8n with `cloudflared tunnel --url http://localhost:5678`, register the temporary URL as the Sandbox webhook ([HUMAN])

---

## 3. Repository Layout
```
/CLAUDE.md
/.mcp.json
/PROGRESS.md            # phase progress (read at every session start)
/BLOCKERS.md            # items waiting on [HUMAN]
/ASSUMPTIONS.md         # design decisions, official doc URLs + dates checked, n8n version
/infra/docker-compose.yml
/shared/
  sheets-schema.md      # §5 schema with buyer-facing explanation (JA + EN)
  invoices.template.csv # empty template the buyer imports (header + 3 fictional sample rows)
  transactions.template.csv
  reminders_log.template.csv
  events_ledger.template.csv
  disputes.template.csv
  messages.ja.json      # source of truth for notification / email copy (embedded into Config)
  messages.en.json
/templates/01-bank-reconciliation/
  workflow.json         # the product (Cloud-compatible, no secrets)
  error-handler.json    # shared error-notification workflow (bundled with every template)
  DESIGN.md             # node graph (Mermaid), data flow, decisions, pseudocode
  README.ja.md / README.en.md
  SETUP.ja.md / SETUP.en.md
  fixtures/             # fictional data only (no real people or companies)
  tests/CASES.md        # acceptance test list
  tests/RESULTS.md      # execution IDs, inputs/outputs, pass/fail, dates
  listing/gumroad.en.md / listing/booth.ja.md / listing/note.ja.md
  LICENSE.md / CHANGELOG.md
  make/blueprint.json   # P6 (optional)
/templates/02-payment-webhook-accounting/   (same layout)
/templates/03-unpaid-reminder/              (same layout)
/templates/04-refund-chargeback/            (same layout)
```

---

## 4. Shared Design Conventions

### 4.1 Config node
Place a Set node named `Config` immediately after the trigger in every workflow. Every tunable (Sheet ID, sheet names, notification channels, thresholds, `LANG`, modes, copy) lives here. The buyer should only ever need to edit Config. Explain each key in a bilingual Sticky Note.

### 4.2 Naming
- Node names: English, verb-first (`Parse Bank CSV`, `Match Invoices`, `Notify Slack`)
- Workflow name: `[Odaji] 01 Bank Deposit Reconciliation v1.0.0`
- Sticky Notes: `## JA` then `## EN`. Colors: input = blue, decision = yellow, output = green, caution = red

### 4.3 Notification channels (Config `NOTIFY_CHANNELS` array, multiple allowed)
- `slack`: Slack node (Block Kit: heading + bullets)
- `email`: Gmail node
- `line`: HTTP Request → LINE Messaging API push (`https://api.line.me/v2/bot/message/push`, Bearer channel access token, `to` = userId). **LINE Notify was discontinued in March 2025 — do not use it.**
- `chatwork`: HTTP Request → `https://api.chatwork.com/v2/rooms/{room_id}/messages` (header `X-ChatWorkToken`)
- Unconfigured channels are skipped. If every channel fails, route to the Error Workflow

### 4.4 Error handling and idempotency
- Bundle `error-handler.json` (Error Trigger → notify) with every template and document in SETUP how to set it as the workflow's Error Workflow
- HTTP Request: Retry On Fail (3 attempts, 2 s wait). `Continue On Fail` only where there are no side effects (never on sheet writes)
- Always carry an idempotency key: 01 = `txn_id`, 02 = `event_id`, 03 = `(invoice_id, stage)`, 04 = `(source, object_id, event_type)`. Read the ledger sheet before processing; skip if present

### 4.5 Time zone, dates, amounts
- Pin the workflow Settings time zone to `Asia/Tokyo` (also keep `TZ` in Config; expressions use `$now.setZone($('Config').item.json.TZ)`)
- Handle dates with Luxon; write `yyyy-MM-dd` strings to sheets
- Amounts are integers (yen). Strip full-width digits, commas, `¥`, `円`, then `parseInt`. Non-JPY follows Template 02's currency rules

### 4.6 Code node
- JavaScript only. No `require` (fails on Cloud). Node.js 20 built-in globals are fine (`TextDecoder`, `Intl`, `Buffer`). Use the Crypto node if hashing is needed
- One Code node = one responsibility. Mirror the logic as pseudocode in `DESIGN.md`

### 4.7 Security
- Always verify webhook signatures (the Stripe Trigger node does it; for PayPal call the verify-webhook-signature API)
- Keep personal data in sheets to the minimum. SETUP must include a note on handling customer names and emails

---

## 5. Shared Google Sheets Schema

One spreadsheet with the sheets below (the buyer imports `shared/*.template.csv`). Column names are fixed English identifiers (expressions reference them); row 1 is the header.

### invoices (shared by 01 and 03)
| Column | Type | Description |
|---|---|---|
| invoice_id | text, unique | Invoice number |
| customer_id | text | optional |
| customer_name | text | Billing name (kanji allowed) |
| payer_name_alias | text | **Comma-separated remitter names in katakana.** Japanese bank transfers arrive with the remitter name in katakana, so a kanji billing name alone cannot be matched. SETUP must present this as effectively required |
| customer_email | text | Recipient for 03 |
| amount | int | Invoiced amount incl. tax (yen) |
| currency | text | default `JPY` |
| issue_date / due_date | date | `yyyy-MM-dd` |
| status | enum | `unpaid` / `partial` / `paid` / `overpaid` / `cancelled` / `escalated` |
| paid_amount | int | Cumulative received |
| paid_date | date | Latest receipt date |
| matched_txn_ids | text | comma-separated |
| match_confidence | enum | `auto` / `amount_only` / `fee_deducted` / `combined` / `manual` |
| fee_deducted | int | Transfer fee deducted by the payer |
| remind_stage | int | 0–3 (updated by 03) |
| last_reminded_at | datetime | |
| promised_date | date | Fill when the customer promises a payment date; a future date pauses reminders |
| do_not_remind | bool | TRUE excludes from reminders |
| notes | text | |

### transactions (01)
`txn_id` (the concatenated string `date|amount|payer_norm|memo_norm`), `source` (`bank_csv`/`gmail`/`manual`), `txn_date`, `payer_name_raw`, `payer_name_norm`, `amount`, `memo`, `matched_invoice_ids`, `status` (`matched`/`unmatched`/`ambiguous`/`ignored`), `suggested_invoice_ids`, `imported_at`

### reminders_log (03)
`invoice_id`, `stage`, `mode` (`draft`/`sent`), `channel`, `to`, `subject`, `sent_at`, `gmail_message_id`

### events_ledger (02)
`event_id`, `source` (`stripe`/`paypal`), `event_type`, `object_id`, `occurred_at`, `currency`, `gross`, `fee`, `net`, `gross_jpy`, `fee_jpy`, `net_jpy`, `fx_rate`, `customer_ref`, `booking_status` (`dry_run`/`booked`/`skipped`/`error`), `accounting_ref` (e.g. freee deal ID), `error_message`

### disputes (04)
`record_id` (`source|object_id`), `source`, `type` (`refund`/`dispute`/`early_fraud_warning`/`manual`), `status`, `amount`, `currency`, `customer_ref`, `reason`, `opened_at`, `evidence_due_by`, `last_alert_stage`, `outcome`, `closed_at`, `notes`

---

## 6. Phases and Commit Gates (per template)

| Phase | Content | Gate (no commit until met) |
|---|---|---|
| P0 | §2 environment (once) | Slack round-trip in §2.4 |
| P1 | Spec: `DESIGN.md` (Mermaid node graph, data flow, decisions, pseudocode), `tests/CASES.md`, `fixtures/` | CASES covers every branch of the spec |
| P2 | Build: create via n8n-mcp → `validate_workflow` passes → register in local n8n → export `workflow.json` | secret grep = 0 hits, built-in nodes only |
| P3 | Test: run every CASE, record execution ID / input / output / verdict in `RESULTS.md`. Two consecutive runs leave state unchanged (idempotent) | all cases PASS |
| P4 | Docs: README / SETUP in JA + EN, bilingual Sticky Notes, (optional) Playwright screenshot of the canvas | a stranger can deploy in ≤ 30 min from SETUP alone |
| P5 | Sales package: listings JA + EN, LICENSE, CHANGELOG, price, FAQ, support policy. `git tag 0X-v1.0.0` | every §7 item ✅ |
| P6 (optional) | Make blueprint (via Make MCP or hand-built). [HUMAN] confirms import on a free Make account | import succeeds |

Commit convention: `feat(01): ...` / `test(01): ...` / `docs(01): ...` / `chore: ...`. At least one commit per phase.

---

## 7. Definition of Done (per template)
- [ ] Imports into a fresh n8n (assume Cloud) with no red nodes
- [ ] Zero secrets / personal IDs (grep recorded)
- [ ] Configured entirely through Config; works after re-selecting credentials per SETUP
- [ ] Every `tests/CASES.md` case PASS, evidence in `RESULTS.md`
- [ ] Idempotent (identical input twice → no diff)
- [ ] Error Workflow bundled with setup instructions
- [ ] Sticky Notes JA+EN / README & SETUP JA+EN / listings JA+EN
- [ ] Supported n8n version stated
- [ ] All fixtures are fictional

---

## 8. Sales Package Contents
- `listing/gumroad.en.md`: title, one-line value proposition, Before / After, what's included, what's required (n8n version, Google, Slack…), what's not supported, FAQ (Does it run on Cloud? Will it work with my bank?), license, support (email, 30 days), price
- `listing/booth.ja.md` / `listing/note.ja.md`: Japanese equivalents. Write the note version as a "how I set it up" article with the purchase link at the end
- `LICENSE.md`: single-business license. No resale, redistribution, or reuse in other template products. Modification allowed
- `CHANGELOG.md`: Keep a Changelog format
- Prices default to the §0 table; record the reasoning in `ASSUMPTIONS.md`

---

## 9. Session Protocol
1. On start, read in order: `CLAUDE.md` → `PROGRESS.md` → `BLOCKERS.md` → `ASSUMPTIONS.md`
2. Resume from the first incomplete phase in `PROGRESS.md`. Do not ask the human questions; when a decision is needed, decide and record the reasoning in `ASSUMPTIONS.md`
3. If blocked on `[HUMAN]`, switch to another phase of the same template or to independent work on another template
4. On finish, update `PROGRESS.md` with "phases completed / next step / open issues" and commit

---
---

# Template 01: Bank Deposit Reconciliation

## Purpose and buyer
Freelancers, small e-commerce shops and small B2B businesses paid by bank transfer, who reconcile dozens to hundreds of deposits a month by eyeballing the bank statement against an invoice list. **Automatically decide "who paid, and for which invoice", and hand a human only the cases that need review.**

## Triggers (three, each switchable in Config)
1. `Google Drive Trigger`: run when a CSV lands in the watched folder `DRIVE_FOLDER_ID`
2. `Gmail Trigger` (polling): emails matching Config `GMAIL_QUERY` (e.g. `subject:(入金) newer_than:1d`)
3. `Schedule Trigger`: daily at Config `RUN_AT` (default 09:00 JST), re-match unprocessed transactions (catches deposits that were unmatched yesterday but match once an invoice is registered)

## Input parsing
**CSV** (`Extract from File`; fall back to a Code node)
- Encoding: Shift_JIS by default. Test empirically whether the built-in node's encoding option handles it; if not, use a Code node with `new TextDecoder('shift_jis').decode(buffer)`. Also strip a UTF-8 BOM. Prove both paths with fixtures
- Column mapping via Config `CSV_MAPPING`: `{date_col, payer_col, deposit_col, withdraw_col, memo_col, skip_rows, date_format}`. Two fixture formats (A: `日付,摘要,入金額,出金額,残高` / B: `取引日,内容,お預入,お引出`)
- Ignore withdrawal rows. Accept dates as `yyyy/MM/dd`, `yyyyMMdd`, `yyyy-MM-dd`
- Amounts: full-width → half-width, strip `,` `¥` `円`

**Gmail**
- Config `MAIL_PARSERS`: `[{name, from_match, subject_match, amount_regex, payer_regex, date_regex}]`. **Do not claim compatibility with any specific bank.** Ship two fictional fixture emails modeled on real notification formats, and describe the feature in the README as "regex-configurable, two samples included, adjustable to your bank's notification"
- Support both HTML and plain-text bodies (prefer `text`)

**txn_id**: `${yyyy-MM-dd}|${amount}|${payer_norm}|${memo_norm}`. Skip if already present in `transactions`.

## Remitter-name normalization (`Normalize Payer` Code node)
1. Unicode NFKC (full-width alphanumerics → half-width, half-width katakana → full-width)
2. Hiragana → katakana
3. Strip corporate-entity abbreviations and full names: `ｶ) (ｶ カ） （カ ユ) (ユ ド) (ド シヤ) ザイ) ガク) イ) ホ) 株式会社 有限会社 合同会社 一般社団法人 医療法人` etc. (extendable via Config `LEGAL_ENTITY_TOKENS`)
4. Remove spaces, `・` and punctuation; keep the long-vowel mark `ー`
5. Strip a leading remitter number / branch code (a run of digits) — switchable in Config

Compare against the normalized `customer_name` and each normalized element of `payer_name_alias`.

## Matching algorithm (`Match Invoices` Code node, pseudocode)
```
remaining(inv) = inv.amount - inv.paid_amount
open = invoices where status in [unpaid, partial]
for txn in txns (unprocessed):
  byAmt  = open where remaining == txn.amount
  byName = open where nameMatch(txn.payer_norm, inv)   # exact, alias, or containment of ≥3 chars
  1. |byAmt ∩ byName| == 1            → matched, confidence=auto
  2. |byAmt| == 1 and |byName| == 0   → matched, confidence=amount_only (flag for review)
  3. |byAmt| == 0:
     a. fee = remaining - txn.amount ∈ FEE_SET and exactly one name match → matched, fee_deducted=fee
        FEE_SET default [110,165,220,275,330,440,550,660,770,880] (Config)
     b. a subset of 2–3 byName invoices sums to txn.amount  → matched(combined), all paid
     c. |byName| == 1 and txn.amount < remaining          → partial (add to paid_amount, status=partial)
     d. |byName| == 1 and txn.amount > remaining          → overpaid (flag for review)
  4. multiple candidates, undecidable → ambiguous (never auto-confirm; top 3 candidates to suggested)
  5. otherwise → unmatched (top 3 by name similarity / amount proximity to suggested)
```
Only 1, 2, 3a, 3b and 3c auto-confirm. 2, 3a and 3b are listed in the notification under "needs review".

## Outputs
- `invoices`: status / paid_amount / paid_date / matched_txn_ids / match_confidence / fee_deducted via "Append or Update (match on invoice_id)"
- `transactions`: append every txn (matched / unmatched / ambiguous)
- Notification (§4.3): summary (processed N / auto-matched A / needs review B / unmatched C) plus line items for review and unmatched (date, remitter, amount, candidates). Copy from `recon_summary` in `shared/messages.*.json`

## Fixtures
- `bank_A_sjis.csv` (Shift_JIS, 15 rows: mixed withdrawals, comma-formatted amounts, full-width names, one fee-deducted, one combined, one partial)
- `bank_B_utf8bom.csv`
- `mail_bankX.eml` / `mail_bankY.eml` (fictional)
- `invoices.seed.csv` (20 rows: with/without alias; two invoices of the same amount to create an ambiguous case)

## Acceptance tests (copy into `tests/CASES.md`; all must PASS)
| ID | Input | Expected |
|---|---|---|
| R01 | name + amount match | auto, paid |
| R02 | amount-only, single candidate | amount_only, paid, flagged in notification |
| R03 | 220 yen fee deducted | fee_deducted=220, paid |
| R04 | two invoices paid together | combined, both paid |
| R05 | partial payment | partial, paid_amount increased |
| R06 | two same-amount invoices, name mismatch | ambiguous, no auto-confirm |
| R07 | withdrawal row | ignored |
| R08 | Shift_JIS file | remitter names readable, no mojibake |
| R09 | same CSV twice | second run skips all, no sheet diff |
| R10 | Gmail notification | amount / payer / date extracted, reconciled via the same path as R01 |
| R11 | all channels | slack / email / line / chatwork each delivered (configured ones only) |

## Known pitfalls (must appear in SETUP)
- Remitter names arrive in katakana. Without `payer_name_alias` the auto-match rate drops sharply
- Individuals can share a name → this is why amount equality is mandatory
- Bank CSV layouts can change across months (header row present or not) → `skip_rows`

---

# Template 02: Payment Webhook → Accounting

## Purpose and buyer
Individuals and small businesses selling online via Stripe / PayPal. Automatically book each payment's revenue, fee and payout into freee / Money Forward / generic CSV, while refunds and chargebacks are **not** booked but raised to a human as alerts.

## Events in scope
**Stripe (`Stripe Trigger` node: signature verification built in; confirm in the official docs that it creates the webhook endpoint on activation)**
- `charge.succeeded` → book revenue (fetch `balance_transaction` via `GET /v1/balance_transactions/{id}` for fee / net / exchange_rate)
- `charge.refunded` → book refund (Config `BOOK_REFUNDS`, default OFF = alert only)
- `charge.dispute.created` / `charge.dispute.closed` → alert (book only on `closed` with `lost`, and only if Config enables it)
- `payout.paid` → transfer from receivable (Stripe) to bank account (Config `BOOK_PAYOUTS`, default ON)

**PayPal (`Webhook` node + signature verification `POST /v1/notifications/verify-webhook-signature`)**
- `PAYMENT.CAPTURE.COMPLETED` (fee from `seller_receivable_breakdown.paypal_fee`)
- `PAYMENT.CAPTURE.REFUNDED`
- `CUSTOMER.DISPUTE.CREATED` / `CUSTOMER.DISPUTE.RESOLVED`

A webhook that fails signature verification returns 400, is discarded, and goes to the Error Workflow.

## Currency and amounts
- Stripe amounts are in the smallest unit. **Zero-decimal currencies** (JPY, KRW, VND, …; fetch the official list into Config `ZERO_DECIMAL_CURRENCIES`) stay as-is; everything else ÷100
- Convert foreign currency to JPY using `balance_transaction.exchange_rate` into the `*_jpy` columns; store the rate
- Consumption tax: Config `TAX_MODE` (`inclusive_10` default / `inclusive_8` / `exempt` / `none`). **Card-processing fees are generally treated as tax-exempt in Japan**, but make the default explicit in Config and state "confirm with your tax accountant" in the README

## Booking modes (Config `ACCOUNTING_MODE`)
1. `dry_run` (default): write to `events_ledger` only. The buyer watches the log for a few days before switching
2. `freee`: OAuth2 (Authorization Code) credential; company ID in Config. Confirm in the official docs before implementing: deal-creation API, account-transfer API, account-items list API, tax-codes list API. Account names (`売上高` / `支払手数料` / `未収入金` / `普通預金`) live in Config; resolve their IDs via the list API on first run and cache them
3. `mf`: verify whether the Money Forward Cloud Accounting API is available and can create journal entries. If it cannot, or requires partner registration, **officially provide the `csv` mode generating an MF-import-format journal CSV daily** instead, and explain why in the README
4. `csv`: generic journal CSV (date, debit account, debit amount, credit account, credit amount, tax code, memo) written daily to the Google Drive folder in Config (usable for freee / MF / Yayoi import)

Default entries (JPY, `charge.succeeded`):
- Dr Accounts receivable (Stripe) net / Dr Payment fees fee / Cr Sales gross
- `payout.paid`: Dr Bank account amount / Cr Accounts receivable (Stripe) amount
- Memo: `Stripe {charge_id} {customer_email or description}`

## Idempotency and reliability
- Look up `event_id` in `events_ledger` first; if present, return 200 and stop (Stripe / PayPal retry deliveries)
- On accounting-API failure, record `booking_status=error`; an hourly Schedule Trigger retries `error` rows (max 5 attempts)
- One event = one transaction. Never leave partial success (write `accounting_ref` immediately after freee succeeds, before anything else)

## Fixtures / tests
- `stripe trigger charge.succeeded` / `charge.refunded` / `charge.dispute.created` / `payout.paid` (test mode)
- PayPal Sandbox Webhook Simulator
- `tests/CASES.md`: A01 JPY sale / A02 USD sale converted / A03 refund alert only / A04 refund booked when ON / A05 dispute created alert / A06 dispute lost booked / A07 payout transfer / A08 same event_id redelivered → skip / A09 bad signature → 400 / A10 freee API failure → retry / A11 dry_run writes nothing to accounting / A12 csv output format

## Known pitfalls
- Stripe payouts arrive days after the charges, batched. Diagram in the README why revenue is booked at charge time and the transfer at payout time
- Refunds are usually booked on the refund date rather than by reversing the original sale; explain why the default is OFF
- PayPal holds and currency-conversion fees are separate events; state they are not supported

---

# Template 03: Unpaid Invoice Reminder

## Purpose and buyer
Same audience as 01. **Check for overdue invoices every morning and prepare staged, progressively firmer reminder emails as drafts.** The owner reviews the Gmail drafts and sends. Once trusted, switch to auto-send. Stops automatically when 01 marks the invoice `paid`.

## Trigger
`Schedule Trigger` daily at Config `RUN_AT` (default 10:00 JST). Business-day check: weekends via Config `SKIP_WEEKENDS` (default ON); Japanese public holidays via the Google Calendar node querying `ja.japanese#holiday@group.v.calendar.google.com` (default ON; on failure fall back to the static list in Config `HOLIDAYS`). Do nothing on non-business days.

## Stages (Config `STAGES`; day offsets are editable)
| stage | condition | subject (JA) | tone |
|---|---|---|---|
| 0 (default OFF) | due_date − 3 days | お支払期限のご案内 | advance notice |
| 1 | due_date + 1 day | お支払いのご確認のお願い | polite, "may have crossed" |
| 2 | due_date + 7 days | 【再送】お支払いのお願い | clear, with a new deadline |
| 3 | due_date + 14 days | 【重要】お支払いに関する最終のご連絡 | final, states next steps |

After stage 3, set `status=escalated`, notify the owner individually, and send nothing further automatically.

## Decision logic
```
for inv in invoices where status in [unpaid, partial] and do_not_remind != TRUE:
  if promised_date and promised_date >= today: skip
  days = today - due_date (JST, whole days)
  target_stage = max stage where days >= STAGES[stage].offset
  if target_stage > inv.remind_stage and (invoice_id, target_stage) not in reminders_log:
     send/draft(target_stage); update remind_stage, last_reminded_at; append reminders_log
```
Remaining = amount − paid_amount; for partial invoices the email states the remaining balance. If one customer has several due invoices the same day, send one combined email (Config `GROUP_BY_CUSTOMER`, default ON).

## Send modes (Config `SEND_MODE`)
- `draft` (default): create a Gmail draft; notify the owner "N drafts created today"
- `send`: send via the Gmail node and record `gmail_message_id`
- `owner_only`: send nothing to customers; the owner gets the list only (for trial runs)
- Sender name, signature and bank details in Config; CC / BCC optional

## Copy
Use `reminder.stage1..3` from `shared/messages.ja.json` / `.en.json`. Placeholders: `{customer_name} {invoice_id} {amount} {remaining} {due_date} {bank_details} {sender_name} {company} {signature}`. Appendix B is the source of truth.

## Fixtures / tests
`invoices.seed.csv` (due at −3 / +1 / +7 / +14 / +30, partial, future promised_date, do_not_remind, paid)
- U01 stage-1 draft created / U02 two runs same day → no duplicate / U03 reaching stage 2 changes the subject / U04 stage 3 → escalated + owner alert / U05 paid excluded / U06 future promised_date skipped / U07 do_not_remind / U08 partial shows remaining / U09 holiday → everything skipped / U10 send mode records message_id / U11 two invoices, one customer → one email

## Known pitfalls
- A badly toned reminder loses the customer. State in the README why draft is the default
- Stages 1 and 2 must include the "our messages may have crossed" line
- The holiday calendar is a Google shared calendar; document what to do if the organization has disabled it

---

# Template 04: Refund & Chargeback Tracker

## Purpose and buyer
Same audience as 02, plus small shops using several PSPs. **Pull refunds, chargebacks and fraud warnings into one ledger and never miss an evidence deadline.** A chargeback with no evidence submitted in time is lost by default.

## Triggers
1. `Stripe Trigger`: `charge.refunded`, `refund.updated` (to catch failures), `charge.dispute.created`, `charge.dispute.updated`, `charge.dispute.closed`, `radar.early_fraud_warning.created`
2. `Webhook` (PayPal, signature verified): `PAYMENT.CAPTURE.REFUNDED`, `CUSTOMER.DISPUTE.CREATED`, `CUSTOMER.DISPUTE.UPDATED`, `CUSTOMER.DISPUTE.RESOLVED`
3. `n8n Form Trigger`: manual entry for channels without an API (bank transfer, convenience store): type, amount, customer, reason, deadline
4. `Schedule Trigger` daily 09:00 JST: deadline reminders and the daily digest; on the 1st of the month, the monthly chargeback rate

## Ledger (`disputes`, §5)
`record_id = source|object_id`. `Append or Update`. Append state transitions to `notes` (e.g. `2026-09-23 needs_response → under_review`).

## Alerts
- dispute created: immediate. Amount, customer, reason, **deadline (`evidence_due_by` shown in JST)**, evidence checklist (Appendix C), link to the Stripe / PayPal dashboard
- early_fraud_warning: immediate. Include the suggestion "consider a proactive refund before it becomes a chargeback" (an effective real-world response)
- Deadline reminders: 7, 3 and 1 days before `evidence_due_by` (Config `DEADLINE_ALERT_DAYS`). `last_alert_stage` prevents duplicates. Only while `status` is `needs_response`
- Refunds: `refund.updated` with `failed` → immediate. `pending` longer than Config `REFUND_STALE_DAYS` business days (default 5) → listed in the daily digest
- Daily digest: open disputes (by deadline) / stalled refunds / today's new items
- Monthly: `disputes ÷ successful payments this month` (count successful charges via the Stripe API; check whether PayPal exposes this, else use a manual value in Config). Warn above Config `CB_RATE_WARN` (default 0.75%) / `CB_RATE_CRIT` (default 0.9%). Card-network thresholds change, so the README says "check each network's current program rules" and never asserts the numbers as fact

## Fixtures / tests
- `stripe trigger charge.dispute.created` etc., PayPal Simulator, Form entry
- D01 dispute created → ledger + immediate alert + deadline shown / D02 T-3 reminder, rerun next day → no duplicate / D03 dispute closed won / lost → outcome / D04 EFW alert / D05 refund failed immediate / D06 refund pending 6 business days → listed / D07 Form entry lands in ledger / D08 monthly rate warn / D09 same event redelivered → skip / D10 bad signature → 400

## Known pitfalls
- `evidence_due_by` is UNIX seconds (UTC). Document the JST conversion and that it is a real time, not 23:59 of that day
- Numerator and denominator of the chargeback rate differ by network; the template's number is a guide
- The best defense is being able to produce evidence at all times (delivery proof, order confirmation, customer communication, AVS / CVC results, IP / device data) — say so in the README

---

## Appendix A: Notification copy (stored in `shared/messages.*.json`; summarized here)
`recon_summary`
- JA: `【入金消込 {date}】処理 {n}件｜自動消込 {a}｜要確認 {b}｜未消込 {c}` + line items `・{txn_date} {payer_raw} ¥{amount} → {invoice_id or 候補: ...}`
- EN: `[Reconciliation {date}] Processed {n} | Auto-matched {a} | Needs review {b} | Unmatched {c}` + `• {txn_date} {payer_raw} ¥{amount} → {invoice_id or candidates: ...}`

Create `dispute_created` / `deadline_reminder` / `daily_digest` / `cb_rate_alert` / `draft_summary` as JA/EN pairs in the same way.

## Appendix B: Reminder email copy (source of truth)

### JA
**stage1**
Subject: お支払いのご確認のお願い（請求書番号 {invoice_id}）
```
{customer_name} 様

いつもお世話になっております。{company}の{sender_name}です。
{due_date}をお支払期限としてご請求しておりました下記につきまして、本日時点で入金の確認ができておりません。

・請求書番号：{invoice_id}
・ご請求金額：¥{remaining}
・お支払期限：{due_date}

なお、お振込みが行き違いになっている場合は、何卒ご容赦ください。
ご不明点がございましたらお気軽にご連絡ください。

{signature}
```
**stage2**
Subject: 【再送】お支払いのお願い（請求書番号 {invoice_id}）
```
{customer_name} 様

いつもお世話になっております。{company}の{sender_name}です。
先日ご連絡いたしました下記につきまして、本日現在も入金を確認できておりません。
恐れ入りますが、{new_deadline}までにお振込みいただけますようお願い申し上げます。

・請求書番号：{invoice_id}
・ご請求金額：¥{remaining}
・お支払期限：{due_date}（超過）
・お振込先：{bank_details}

既にお手続き済みの場合は、お振込日をご一報いただけますと幸いです。
お振込みが行き違いになっている場合は、何卒ご容赦ください。

{signature}
```
**stage3**
Subject: 【重要】お支払いに関する最終のご連絡（請求書番号 {invoice_id}）
```
{customer_name} 様

{company}の{sender_name}です。
下記につきまして、再三のご連絡にもかかわらず入金の確認ができておりません。
{final_deadline}までにお振込みまたはご連絡がない場合は、今後のお取引条件の見直し等、然るべき対応を検討させていただきます。

・請求書番号：{invoice_id}
・ご請求金額：¥{remaining}
・お支払期限：{due_date}（超過）
・お振込先：{bank_details}

{signature}
```
(Even at stage 3, never assert specific legal action such as "we will take legal action".)

### EN
**stage1**
Subject: Payment reminder — Invoice {invoice_id}
```
Dear {customer_name},

This is a friendly reminder that invoice {invoice_id} for ¥{remaining} was due on {due_date}, and we have not yet received payment as of today.

• Invoice: {invoice_id}
• Amount due: ¥{remaining}
• Due date: {due_date}

If you have already sent payment, please disregard this message. If you have any questions, please don't hesitate to contact us.

{signature}
```
**stage2**
Subject: Second notice — Invoice {invoice_id} is past due
```
Dear {customer_name},

Following our previous reminder, invoice {invoice_id} remains unpaid as of today. We kindly ask that you arrange payment by {new_deadline}.

• Invoice: {invoice_id}
• Amount due: ¥{remaining}
• Original due date: {due_date}
• Bank details: {bank_details}

If payment has already been made, please let us know the transfer date so we can update our records. Apologies if this message has crossed with your payment.

{signature}
```
**stage3**
Subject: Final notice — Invoice {invoice_id}
```
Dear {customer_name},

Despite our previous reminders, we have not received payment or a response regarding invoice {invoice_id}.
If we do not receive payment or hear from you by {final_deadline}, we will need to review the terms of our business relationship and consider further steps.

• Invoice: {invoice_id}
• Amount due: ¥{remaining}
• Original due date: {due_date}
• Bank details: {bank_details}

{signature}
```

## Appendix C: Evidence checklist (bundled with dispute alerts)
- Order confirmation email / invoice (customer name, amount, date)
- Proof of delivery (tracking number, delivery confirmation, signature); for digital goods, access logs / download records
- Record of agreement to terms and refund policy (checkbox, timestamp)
- Customer communication (email / chat history)
- AVS / CVC results at checkout, whether 3-D Secure authentication occurred
- IP address, device, and history of prior legitimate transactions
- Submit at least 24 hours before the deadline (allow for processing time on the reviewing side)
