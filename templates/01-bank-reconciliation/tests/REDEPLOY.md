# tests/REDEPLOY.md — 新規 n8n への再導入確認 / Re-deployment check on a fresh n8n (2026-09-23)

## JA

DoD（CLAUDE.md §7）の「新規の n8n（Cloud 想定）に import して赤ノード無し」と、ユーザー指示「SETUP どおりに自分で導入し直せるか確認」の証跡。SETUP.ja.md §4（取込）〜§4.4（Error Workflow 設定）を、UI 操作の代わりに同等の API 呼び出しで実施した。

| 項目 | 結果 |
|---|---|
| インスタンス | まっさらなデータディレクトリ（`n8n-data-redeploy`）で n8n 2.40.5 を別ポート（5680、タスクブローカー 5681。ASSUMPTIONS A39）に起動し、オーナー作成・API キー発行を行った。既存の検証用インスタンス（5678）とはデータを共有しない |
| 取込 | `error-handler.json` → id `NUbFyuo6mqFAoj1H`（15 ノード）、`workflow.json` → id `uA4qr3RhyjXZo4bJ`（38 ノード）。名前・ノード数は同梱ファイルどおり |
| 取込後の内容 | 取込後に取得した本体 JSON は `workflow.json` とノード名・型・typeVersion・パラメータ・接続が完全一致（Config キー 25 / Error Handler 9） |
| 赤ノード | 両ワークフローの全ノード型・typeVersion がこのインスタンスの `/types/nodes.json` に存在（未知の型 0）。組み込みノード以外 0、`credentials` ブロック 0（Credential は買い手が SETUP §4.3 で選ぶ） |
| Error Workflow | 本体の Settings → Error Workflow に Error Handler の id を設定できた（API の `settings.errorWorkflow`） |
| 有効化 | Credential 未設定のまま Publish を試すと「Cannot publish workflow: 9 nodes have configuration issues … Missing required credential」で拒否される（期待どおり。SETUP §4.3 の手順で Credential を選ぶか未使用の通知ノードを無効化してから Publish する） |
| 検証 | n8n-mcp `n8n_validate_workflow`: Error Handler valid・エラー 0・警告 0。本体は n8n-mcp プロセスが better-sqlite3 の終了時アサーションで落ちる（ツール側の既知の不具合、3 回再試行）ため、取込後に API で取得した本体 JSON をファイル検証 `validate_workflow`（runtime）にかけた: valid=True errors=0 warnings=4（警告は P2 と同じ「コメント内の require」2 件と「executeOnce」2 件） |
| 後片付け | 新規インスタンスを停止し、データディレクトリと API キーを削除 |

ライブ未検証（BLOCKERS H1/H2）: Google／Slack の実 Credential を使った有効化と実行。

## EN

Evidence for the DoD item "imports into a fresh n8n with no red nodes" and for the owner's request to re-deploy following SETUP. SETUP.en.md §4–§4.4 were performed with the equivalent API calls instead of UI clicks: a fresh n8n 2.40.5 (empty data directory, port 5680 / task broker 5681, see ASSUMPTIONS A39) with a new owner and API key; `error-handler.json` imported as `NUbFyuo6mqFAoj1H` (15 nodes) and `workflow.json` as `uA4qr3RhyjXZo4bJ` (38 nodes); the stored main workflow equals `workflow.json` (names, types, typeVersions, parameters, connections); every node type/version exists in the instance's node registry (no unknown nodes), no community nodes, no credentials blocks; the Error Workflow setting was set; Publish without credentials is refused with "Missing required credential" (expected; SETUP §4.3 explains assigning credentials or disabling unused Notify nodes); n8n-mcp validation: Error Handler valid / 0 errors / 0 warnings, main validated file-level from the imported JSON: valid=True errors=0 warnings=4 (the instance-level call crashes inside n8n-mcp's better-sqlite3 at exit — a tool defect, retried 3 times). The fresh instance was stopped and its data deleted afterwards. Live activation with real Google/Slack credentials remains unverified (BLOCKERS H1/H2).
