# Changelog — [Odaji] 01 Bank Deposit Reconciliation

All notable changes to this template are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the template uses [Semantic Versioning](https://semver.org/).
このファイルは Keep a Changelog 形式です。バージョンはセマンティック バージョニングに従います。

## [Unreleased]

## [1.0.0] - 2026-09-23

### Added
- Bank deposit reconciliation workflow (`workflow.json`, 30 nodes + 6 bilingual sticky notes) with three triggers: Google Drive folder (bank CSV), Gmail (deposit-notification emails, regex parsers) and a daily schedule (re-match of unmatched deposits).
- Matching rules 1–5 (exact name+amount, amount-only, transfer-fee deduction, combined payment of 2–3 invoices, partial payment, overpaid, ambiguous, unmatched) with idempotent `txn_id` handling and a shared `invoices` / `transactions` Google Sheet.
- Notifications to Slack (Block Kit), Gmail, LINE Messaging API push and Chatwork, selectable in Config; error handler workflow (`error-handler.json`).
- Config node with every tunable (sheet ids, CSV column mapping incl. Shift_JIS / UTF-8 BOM, mail parsers, legal-entity tokens, fee set, channels, copy in JA/EN).
- Fictional fixtures, unit and integration tests, pinned-data smoke runs (local n8n 2.40.5), README / SETUP in Japanese and English.
- 入金消込ワークフロー本体、Error Workflow、Config 集約、日英ドキュメント、fixtures とテスト一式（初版）。
