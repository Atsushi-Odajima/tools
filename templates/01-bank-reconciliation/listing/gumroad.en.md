# Bank Deposit Reconciliation for n8n — `[Odaji] 01` v1.0.0

Workflow names: `[Odaji] 01 Bank Deposit Reconciliation v1.0.0` (main) / `[Odaji] 01 Error Handler v1.0.0` (Error Workflow)

Matches bank transaction CSVs and deposit-notification emails against an invoice list in Google Sheets, decides who paid which invoice, and notifies you only about the cases that need a human decision.

## Who it is for

- Freelancers, small e-commerce shops and small B2B businesses that collect revenue by invoice (bank transfer).
- Anyone who reconciles tens to hundreds of deposits a month by hand, comparing the bank statement with an invoice list.
- Anyone who can keep the invoice list in Google Sheets (an existing list works once its columns are renamed to the required names).

## Before / After

**Before**
- You tick off tens to hundreds of deposits a month against the invoice list by eye.
- A transfer ¥220 short, one transfer covering two invoices, or a half payment means a manual note or a guess.
- A deposit for an invoice you have not registered yet stays unmatched until someone remembers it.

**After**
- Drop the CSV into a watched Drive folder, or let the bank's email arrive in Gmail; the `invoices` sheet is updated and a summary arrives in Slack, email, LINE or Chatwork.
- Fee deductions and combined payments of 2–3 invoices are settled by rule and listed under "Needs review" with the reason; partial payments are settled and listed under "Auto-matched" with the remaining amount.
- Ambiguous or unmatched deposits are listed with up to 3 candidates; a daily re-match picks up invoices registered later.

## What it does

1. **Trigger.** A CSV lands in the watched Drive folder (polled every minute), an email matches the Gmail search (every 5 minutes), or the daily 09:00 JST re-match runs.
2. **Intake.** The CSV is decoded (Shift_JIS or UTF-8 BOM) and deposit rows extracted through the `CSV_MAPPING` column map; emails are parsed with the `MAIL_PARSERS` regular expressions.
3. **Normalize.** Remitter names are normalized (NFKC, hiragana to katakana, legal-entity tokens such as `カ)` / `株式会社` removed) and a deterministic `txn_id` is built.
4. **Match.** Open invoices (`unpaid` / `partial`, JPY) are matched with the rules below; a `txn_id` already in `transactions` is skipped.
5. **Write, then notify.** `invoices` and `transactions` are updated first, then the summary goes to every configured channel. A bundled Error Workflow reports failed runs.

Name match = normalized remitter equals, or contains with 3+ characters, `customer_name` or `payer_name_alias`. Remaining = `amount − paid_amount`.

| Rule | Condition | Result | Auto-confirmed |
|---|---|---|---|
| 1 | One invoice matches by name and remaining = deposit | `paid`, `auto` | **Yes** |
| 2 | One invoice with remaining = deposit, no name match | `paid`, `amount_only` | **Yes** (listed under Needs review) |
| 3a | One name match, remaining − deposit is in `FEE_SET` (default ¥110–880) | `paid`, fee written to `fee_deducted` | **Yes** (Needs review) |
| 3b | 2–3 name-matched invoices add up to the deposit, only one combination | all `paid`, `combined` | **Yes** (Needs review) |
| 3c | One name match, deposit < remaining | `partial`, `paid_amount` increased | **Yes** |
| 3d | One name match, deposit > remaining | unchanged; `transactions` row `ambiguous` (overpaid) | No |
| 4 | Several candidates, no way to decide | unchanged; `ambiguous`, top 3 candidates | No |
| 5 | None of the above | unchanged; `unmatched`, top 3 similar invoices | No |

An amount match is always required; a name alone never settles an invoice.

Channels: Slack (Block Kit), email (Gmail), LINE (Messaging API push), Chatwork — any combination via `NOTIFY_CHANNELS`, Japanese or English copy via `LANG`. Every channel is attempted; the run fails only when all fail. An empty `NOTIFY_CHANNELS` (no notification) also works.

## What's included

| File | Content |
|---|---|
| `workflow.json` | Main workflow: 30 nodes + 8 sticky notes (JA/EN) |
| `error-handler.json` | Error Workflow: 11 nodes + 4 sticky notes (JA/EN) |
| `README.ja.md` / `README.en.md` | Product description: rules, FAQ, limitations, verification status |
| `SETUP.ja.md` / `SETUP.en.md` | Step-by-step setup guide (written for about 30 min) |
| `DESIGN.md` | Node diagram, data shapes, reasoning, Code node pseudocode (for modifying) |
| `LICENSE.md` / `CHANGELOG.md` | Single-business license (JA/EN); Keep a Changelog history |
| `code/` | Source of the 8 Code nodes (embedded verbatim in `workflow.json` and `error-handler.json`) |
| `build/build_workflow.py` | Regenerates the JSON from `code/` (for modifying) |
| `fixtures/` | Fictional trial data: 3 bank CSVs, 2 `.eml` emails, 20-invoice seed, example `CSV_MAPPING` / `MAIL_PARSERS`, expected results |
| `tests/` | Acceptance cases, unit tests, pinned data and run records |
| `docs/` | Canvas images and how they were captured |
| `shared/` | Sheet schema (JA/EN), empty sheet templates, notification copy (`messages.ja.json` / `messages.en.json`) |

README, SETUP, LICENSE, the sheet schema and every canvas sticky note are in Japanese and English. DESIGN.md and the test records are single-language (mostly Japanese) with a summary in the other language.

## Requirements

- **n8n 2.x**, self-hosted or n8n Cloud. Built and tested on 2.40.5 self-hosted; **not yet tested on Cloud**. Built-in nodes only; self-hosted instances need task runners for the Code nodes.
- **Google account**: Sheets (ledger), Drive (watched folder), Gmail (email intake and/or notifications; can be skipped). Three OAuth2 credentials from one Google Cloud OAuth client, or "Sign in with Google" on Cloud.
- One spreadsheet with the sheets `invoices` and `transactions` (`shared/sheets-schema.md`).
- A bank CSV export or deposit-notification emails; either is enough.
- Optional: Slack (bot token, `chat:write`), LINE Messaging API channel token, Chatwork API token.

## Not supported / limitations

- **JPY only.** Non-JPY invoices are skipped and reported as a warning.
- **No compatibility guarantee with any specific bank.** The CSV layout is set in `CSV_MAPPING` and email parsing in regular expressions you adapt; two fictional email samples and two CSV layouts are included.
- **Google Sheets is the ledger**; nothing is written elsewhere.
- **No accounting-software booking**, no reminder emails, no foreign currency, no tax decisions.
- Ambiguous, unmatched and overpaid deposits are never auto-confirmed. One email = one deposit. No passbook images or PDFs.
- Every run reads both sheets in full; split `transactions` by year beyond roughly 10,000 rows.
- The original CSV and email are not stored in the sheet (n8n's execution log keeps node inputs and outputs as usual).

## Setup time

`SETUP.en.md` is written so that a first-time n8n user can finish in about 30 minutes (target); the Google Cloud OAuth step (10–15 min) is the one most likely to run over.

## FAQ

**Does it run on n8n Cloud?** Expected to (built-in nodes only), but verified only on self-hosted 2.40.5. Not tested on Cloud.

**Will it work with my bank's CSV?** Adjust `CSV_MAPPING` (headers, `skip_rows`, date format, encoding). Compatibility with any specific bank is not guaranteed. A missing column fails the run rather than producing 0 rows.

**What about deposit emails?** `MAIL_PARSERS` holds sender/subject matches and regular expressions for amount, remitter and date. Two fictional samples are included; adapt them to your bank's email.

**Transfer-fee deductions?** A shortfall in `FEE_SET` (default ¥110–880) with one name match is marked `paid`, the fee goes to `fee_deducted`, and it is listed under "Needs review". Other shortfalls are partial payments.

**Partial payments?** One name match and deposit < remaining: `status=partial`, `paid_amount` increased, remaining amount shown. The invoice becomes `paid` when the rest arrives.

**Two invoices with the same amount?** If the remitter name narrows it to one, rule 1 settles it. Otherwise the candidates are listed and a person picks one in the sheet. `payer_name_alias` reduces these cases.

**Re-importing the same CSV?** Existing `txn_id`s are skipped, the sheets do not change, and the notification reads "No new transactions (skipped as already processed: N)". Verified with the fixtures on all three trigger paths (Google nodes on pinned data; see "What was tested?").

**Multiple channels?** Yes, via `NOTIFY_CHANNELS`; if some fail the rest still deliver. Deactivate unused `Notify …` nodes (n8n will not publish an active node without a credential).

**English notifications?** Set `LANG` to `"en"` in `Config` of both workflows; edit `MESSAGES` to change the wording.

**What was tested?** Self-hosted n8n 2.40.5, 2026-09-23: 10 unit/integration suites for the 8 Code nodes, 15 smoke-run paths, acceptance cases R01–R23 (22 pass, 1 not applicable) including idempotency. The Error Workflow was verified as invoked by a production failure of a throwaway workflow; invocation by a live failure of the main workflow itself is not yet verified (needs Google credentials). Google nodes ran on pinned data: real Sheets/Drive/Gmail calls, real Slack/Gmail delivery and n8n Cloud were **not** verified; LINE and Chatwork were verified up to the HTTP call to a local receiver. Fixtures are fictional. Details: `README.en.md` §10, `tests/RESULTS.md`.

## License and support

- **Single-business license** (`LICENSE.md`): one sole proprietor or one legal entity, any number of n8n instances, modification allowed. No resale, redistribution, or inclusion in other templates or client deliverables (one license per client). Provided as is; no accounting or tax determinations. The author is not liable for damages arising from use, including reconciliation errors, undelivered notifications or third-party service charges; test with the bundled fixtures and the trial-run procedure (`SETUP.en.md` §7) before production use.
- **Support**: email, 30 days from purchase, for deploying as described in `SETUP.en.md`. Modified workflows, bank-specific formats and defects in n8n itself are out of scope.

## Price

$39, one-time.

## Changelog

`CHANGELOG.md` (Keep a Changelog). Current version 1.0.0 (2026-09-23).

## Screenshots

Upload in this order (all in `docs/`):

1. `thumbnail.png` — cover (1200×630)
2. `canvas-main.png` — main workflow
3. `canvas-error-handler.png` — Error Workflow
4. `canvas-config-sticky.png` — Config note
5. `canvas-config-keys-1.png` / `canvas-config-keys-2.png` — Config key tables
