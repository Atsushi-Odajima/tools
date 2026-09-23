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
| 01 入金消込 | - | 完了（2026-09-23） | 完了（2026-09-23） | 完了（2026-09-23） | 完了（2026-09-23） | 完了（2026-09-23、tag `01-v1.0.0`） | 未着手（任意） |
| 03 未入金リマインド | - | 中断（DESIGN.md・fixtures 下書きあり、CASES.md とレビュー未実施） | 未着手 | 未着手 | 未着手 | 未着手 | 任意 |
| 04 返金・CB | - | 未着手 | 未着手 | 未着手 | 未着手 | 未着手 | 任意 |
| 02 Webhook会計 | - | 未着手 | 未着手 | 未着手 | 未着手 | 未着手 | 任意 |

## 次の一手
- **2026-09-23 ユーザー指示により作業を停止中（使用量の都合）。再開の指示があるまで着手しない。**
- 再開時: テンプレ03 の P1 は `templates/03-unpaid-reminder/DESIGN.md` と `fixtures/` の下書きが未レビューのまま残っている。`tests/CASES.md` の作成 → 3 名の敵対的レビュー → 修正から再開し、その後 P2 → P5、続いて 04、02。
- ユーザー側 [HUMAN]（BLOCKERS H1/H2）が済んだら、01 のライブ検証（Google 実読み書き、Slack/Gmail 実送信、本番実行からの Error Workflow 起動）を `tests/RESULTS.md` §6 の手順で行う。

## P5 と DoD（2026-09-23）
- `listing/gumroad.en.md` / `booth.ja.md` / `note.ja.md`、価格根拠は `ASSUMPTIONS.md` の「価格・販売方針（テンプレ01）」。正確性・販売コンプライアンスのレビュー 26 件を反映（部分入金の区分、候補複数・未消込の台帳書込み、日英ドキュメント範囲の過大表現、未発売製品名の削除、購入導線の置き場 等）。
- `tests/REDEPLOY.md`: 新規 n8n（別データディレクトリ）に同梱 JSON を取り込み、赤ノード無し・Config のみで設定・Error Workflow 設定・Credential 未設定時の Publish 拒否を確認。

| DoD（CLAUDE.md §7） | 状態 | 証跡 |
|---|---|---|
| 新規の n8n に import して赤ノード無し | ✅ | `tests/REDEPLOY.md`（38/15 ノード、未知の型 0） |
| 秘密・個人 ID ゼロ（grep 記録） | ✅ | `build/build_workflow.py` のアサート、`tests/RESULTS.md`、リポジトリ全体 grep 0 件（仕様書の規則文を除く） |
| Config だけで設定完了 | ✅ | `SETUP.*.md` §5–§6、第三者導入レビュー（P4） |
| `tests/CASES.md` 全 PASS、`RESULTS.md` に証拠 | ✅ | R01〜R23: 22 PASS / R12 N/A / FAIL 0 |
| 冪等 | ✅ | `RESULTS.md` §3（R09 / R09-b / R19-b） |
| Error Workflow 同梱・設定手順 | ✅ | `error-handler.json`、`SETUP.*.md` §4.4（Publish 必須を明記） |
| 付箋・README・SETUP・listing の日英 | ✅ | 付箋 8＋4 枚すべて JA/EN、README/SETUP 各 2 言語、listing EN 1・JA 2 |
| 対応 n8n バージョン明記 | ✅ | README/SETUP に 2.40.5（Cloud 未検証） |
| fixtures は架空データ | ✅ | P1 実在性レビュー（`fixtures/README.md`） |
| ライブ検証 | ⏳ | Google/Slack の実 Credential が無いため未実施（BLOCKERS H1/H2）。手順は `RESULTS.md` §6 |

## P4 の証跡（2026-09-23）
- `README.ja.md` / `README.en.md`、`SETUP.ja.md` / `SETUP.en.md`（0〜10 章＋参考 26 件、公式ページを取得して引用）、`docs/`（Playwright で撮影したキャンバス画像 6 枚、付箋の重なり 0・切れ 0 を実測）。
- 第三者レビュー: SETUP だけを読んでポート 5679 の新規 n8n に導入（API で import 相当）。指摘 9 件（Drive Trigger のフォルダ指定モード、Config JSON が Expression である旨、Error Handler 側 Config の 9 キー、Publish ダイアログ、UI 表記 等）と正確性レビュー 12 件（日英パリティ、画像参照、参考文献、seed 行番号 等）を反映。
- 付箋は本体 8 枚・Error Handler 4 枚（Config キー表を 2 枚に分割）。日英併記。

## P3 の証跡（2026-09-23）
- `tests/RESULTS.md`（唯一の証拠ファイル、検証した版のコミット・ファイル sha256・Code ノード jsCode md5 を記録）＋ `tests/results/g1-drive.md` / `g2-gmail-notify.md` / `g3-schedule-error.md`。
- R01〜R23: 22 ケース PASS、R12 は定義どおり N/A、FAIL 0。冪等性は R09（同一 CSV 2 回）、R09-b（同じメール 2 回＋2 回連続）、R19-b（Schedule 2 回連続）で出力同一・書込みゼロを確認。実行順 Update Invoices → Upsert Transactions → Build Notification を runData の順序と startTime で確認。
- 3 グループが並列に自分の複製ワークフローで実行し、後片付け（複製・シンク・ダミー Credential 削除）を監査で確認。監査指摘 4 件（検証版の不一致・版の記録・n8n 上の実行の有無・R11 単独チャネル未実行）は再実行と RESULTS 改訂で解消。
- P3 で見つかった製品上の事実 2 点を反映（D34 / ASSUMPTIONS A35〜A38）: (1) n8n は有効化（Publish）済みの Error Workflow しか呼ばない → SETUP §4 に「Error Handler を Publish」を追加。(2) 有効化時に有効な全ノードの Credential が検証され、未使用の通知ノードは無効化が必要。無効化ノードは入力を素通しするため、`Check Notification Results` を「素通りした通知は失敗として数える」よう修正（単体 11/11、結合 121/121、実行 176/178・196/198 で確認）。
- ライブ未検証（BLOCKERS H1/H2）: Google Sheets/Drive/Gmail の実読み書き、Slack/Gmail の実送信、本体の本番実行からの Error Workflow 起動。
- 01 P3 監査対応（2026-09-23）：RESULTS.md 初版確定後に作業ツリーへ入った D34（`Check Notification Results` の素通り検知）を fix グループが作業ツリー版で再実行（R11 全 6 通り・R11-b・R11-c・フルパス・R09 2 回目、全 PASS。`tests/results/fix.md`）。検証した版（コミット・jsCode md5）と保存済み実行 JSON の SHA-256（`tests/results/evidence-sha256.md`）を記録。**製品ファイルの D34 変更を採用するか HEAD に戻すかは未決（オーケストレーター判断）。**

## P2 の証跡（2026-09-23）
- `code/*.js` 8 本（Parse Bank CSV / Parse Mail / Collect Transactions / Normalize Payer / Match Invoices / Build Notification / Build Error Message / Check Notification Results）。`tests/unit/run-all.sh` 10 スイート合格（結合 119 アサーション）。`workflow.json` 埋め込み版でも同結果。
- `build/build_workflow.py` → `workflow.json`（36 ノード、付箋 6）/ `error-handler.json`（14 ノード）。決定的ビルド（`--check`）。秘密 grep 0、組み込みノードのみ、credentials ブロック無し。
- n8n-mcp `validate_workflow`（runtime）: 両ファイル valid・エラー 0（警告はコメント内の require 誤検知 2、executeOnce 設計どおり 2）。
- ローカル n8n 2.40.5 に登録（本体 `EMlrzFHwUpu7xvZx`、Error Workflow `S9vwW2D7jBCIvCQn`、`settings.errorWorkflow` 設定済み）。pinned data による 15 経路のスモーク実行すべて期待どおり（`tests/SMOKE.md`、実行 57〜86）。
- 敵対的レビュー 3 名の指摘 10 件（複数ファイル取込の欠落、Sheets 変換 CSV の文字コード、Slack のリンク既定、冪等性の二重防御 等）を修正し再検証。

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

## タグについて
- `01-v1.0.0` はローカルで `7f24b9a` に作成済み。このセッションの GitHub 接続はブランチの push のみ許可されており、タグの push は 403 で拒否された（`git push origin 01-v1.0.0`）。お手元の PC で次を実行すると同じタグを公開できる:

```
git fetch origin main
git tag -a 01-v1.0.0 7f24b9a -m "Template 01 Bank Deposit Reconciliation v1.0.0 (n8n 2.40.5)"
git push origin 01-v1.0.0
```

## 履歴
- 2026-09-23: プロジェクト開始。仕様書を配置。P0 完了（Slack は代替）。01 P1 完了。リポジトリを tools に移設。01 P2 完了。01 P3 完了（22 PASS / FAIL 0、製品修正 D34）。01 P4 完了。01 P5 完了・DoD 確認・`01-v1.0.0` タグ。テンプレ03 の P1 に着手したが、ユーザー指示で停止（下書きを WIP コミット）。
