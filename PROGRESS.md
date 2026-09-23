# PROGRESS

セッション開始時に必ず読む。最終更新は末尾の履歴を参照。

## 置き場所について
- 2026-09-23 ユーザー指示により、このプロジェクトの正式な置き場所は https://github.com/Atsushi-Odajima/tools のリポジトリ直下（`main`）。§3 の `/` はリポジトリ直下を指す。
- それ以前は `4S-search` リポジトリの `n8n-payment-templates/` 配下（ブランチ `claude/english-claude-md-p46sf4`）で作業していた。履歴はそちらのコミットに残る。
- 仕様書は `CLAUDE.md`（日本語）と `CLAUDE.en.md`（英語）。Codex を使う場合は `CLAUDE.md` を `AGENTS.md` にコピーする。

## フェーズ状況

| テンプレ | P0 | P1 | P2 | P3 | P4 | P5 | P6 |
|---|---|---|---|---|---|---|---|
| 共通 | 完了（2026-09-23） | - | - | - | - | - | - |
| 01 入金消込 | - | 完了（2026-09-23） | 進行中 | 未着手 | 未着手 | 未着手 | 任意 |
| 03 未入金リマインド | - | 未着手 | 未着手 | 未着手 | 未着手 | 未着手 | 任意 |
| 04 返金・CB | - | 未着手 | 未着手 | 未着手 | 未着手 | 未着手 | 任意 |
| 02 Webhook会計 | - | 未着手 | 未着手 | 未着手 | 未着手 | 未着手 | 任意 |

## 次の一手
- 01 P2: `code/*.js`（8 ノード）→ 単体・結合テスト → `build/build_workflow.py` で `workflow.json` / `error-handler.json` 生成 → n8n-mcp 検証 → ローカル n8n 登録 → pinned data で 6 経路のスモーク実行 → 敵対的レビュー → 修正（Workflow で実行中）。

## P1 の証跡（2026-09-23）
- `templates/01-bank-reconciliation/DESIGN.md`（約 1,100 行）: Mermaid ノード図（本体 30 ノード＋付箋 6、Error Workflow）、データフロー、Config キー 40 項目、判断理由、全 Code ノードの疑似コード、R01〜R13 との対応、P2/P3 で実測する事項。
- fixtures 10 件（Shift_JIS 実バイトの CSV、UTF-8 BOM の CSV、架空メール 2 通、請求 20 件・取引の seed、MAIL_PARSERS / CSV_MAPPING の例）と `tests/CASES.md`。
- 敵対的レビュー 3 名（整合性・仕様準拠・実在性）の指摘 20 件を反映（DESIGN.md 422 行差分、fixtures/README・CASES・shared の同期）。

## P0 の証跡（2026-09-23）
- n8n 2.40.5 を Node 24.21.0 で起動（`infra/run-n8n-local.sh`、SQLite、`Asia/Tokyo`）。`/healthz` 200。
- オーナー `owner@example.com` を作成、API キー（106 スコープ）を発行。公開 API `GET /api/v1/workflows` 200。キーは作業領域の `secrets/` のみに保存（リポジトリ外）。
- n8n-mcp 2.87.0: `n8n_health_check` → `status: ok`、ツール 28 個（`n8n_create_workflow` を含む）。`.mcp.json` に `WEBHOOK_SECURITY_MODE=moderate` が必要（ASSUMPTIONS A10）。
- n8n-skills（14 スキル＋ルーター）を README の Method 3 で `~/.claude/skills/` に導入。
- 最小ワークフロー `[P0] Manual → Set → Notify (Slack substitute)`: 実行 ID 1 成功（`Notify Sink` まで到達）。受信側 `[P0] Local Notification Sink` の実行 ID 2 で本文 `P0 疎通確認 / P0 connectivity check from n8n` を受信。Slack 実投稿は BLOCKERS H2。

## 未解決
- `BLOCKERS.md` を参照。

## 履歴
- 2026-09-23: プロジェクト開始。仕様書を配置。P0 完了（Slack は代替）。01 P1 完了。リポジトリを tools に移設。01 P2 着手。
