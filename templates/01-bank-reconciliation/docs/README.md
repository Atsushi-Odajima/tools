# docs/ — キャンバス画像 / Canvas images

## JA

- `canvas-main.png`（3200×2000）：本体ワークフロー `[Odaji] 01 Bank Deposit Reconciliation v1.0.0` の全体。1600×1000 の表示領域で「Zoom to fit」（キーボードの `1` と同じ）を押した状態を 2 倍解像度で保存（表示倍率 21.9%）。上段の 5 枚の付箋はそれぞれ本文がノード列の上にあり、ノードは付箋の下側に入る。下段は赤い注意（S6）と黄色い「Config キー一覧（1/2）（2/2）」。
- `canvas-error-handler.png`（3200×2000）：`[Odaji] 01 Error Handler v1.0.0` の全体。同じ手順（表示倍率 33.0%）。
- `canvas-config-sticky.png`（1568×2272）：本体の `Config` / `Route by Source` / `Skip Disabled Trigger` を囲む Config 用付箋（784×1136）を 100% 表示で要素ごと撮影。本文は概要と `TRIGGERS_ENABLED` の説明のみで、キーの表は下の 2 枚に分けた。
- `canvas-config-keys-1.png`（3008×2944）／`canvas-config-keys-2.png`（3008×3040）：「Config キー一覧（1/2）」（`TZ` 〜 `MAIL_PARSERS`、1504×1472）と「（2/2）」（`LEGAL_ENTITY_TOKENS` 〜 `SOURCE`、1504×1520）を 100% 表示で要素ごと撮影。3 列とも切れずに読める。
- `thumbnail.png`（1200×630）：本体キャンバスの取込グループ（`Check File Is CSV` 〜 `Collect Transactions`）を 58% 表示で切り出し（600×315 の 2 倍）。付箋は隠していない（本文はノード列の上にあるため切り出し範囲に入らない）。「Credential 未設定」の赤い警告バッジだけをブラウザー側の CSS で非表示にしており、ワークフロー本体は変更していない。背景は不透明なので明暗どちらの掲載ページでも使える。
- 配置の根拠：付箋の本文の高さは Playwright で実測し（`build/build_workflow.py` の `TEXT_SIZE`）、本文の下端と最初のノード列の間を 48 px 以上、最後のノード列（ラベル込み）の下を 40 px 以上あける。実測では、どのノードも付箋の本文領域（本文＋40 px）と重ならず、本文の切れ（縦・横）と付箋どうしの重なりは 0 件（変更前は本体で本文とノードの重なり 33 件・切れ 2 枚、Error Handler で 6 件・1 枚）。
- 作成環境：ローカル n8n 2.40.5（`ASSUMPTIONS.md`）、Playwright 1.63.0 + Chromium 141.0.7390.37（`/opt/pw-browsers/chromium-1194`）、ヘッドレス、`deviceScaleFactor: 2`、2026-09-23。オーナーでサインインし、閲覧のみ（ノードを開かず、保存・実行・pin なし）。撮影は同じ JSON を API で登録した一時コピーで行い、撮影後に削除した。
- スクリプト：`/tmp/claude-0/-home-user-4S-search/3170e1bf-16ee-57f4-89e0-ecee08729771/scratchpad/p4c-scratch/shots-p4c.js`（共通処理は `p4-scratch/shots/lib.js`、計測は `measure.js` + `analyze.py`）。サインイン処理を含むためリポジトリには置かない。パスワードは scratch の秘密ファイルから読み、出力しない。
- 再作成：付箋の本文を変えたら `measure.js` で本文の高さを実測して `TEXT_SIZE` を更新し、ビルド後に `node shots-p4c.js` を再実行して `out/` の 6 ファイルをここへコピーする。

## EN

- `canvas-main.png` (3200×2000): whole canvas of `[Odaji] 01 Bank Deposit Reconciliation v1.0.0`, 1600×1000 viewport after "Zoom to fit" (same as key `1`), saved at 2× resolution (zoom 21.9%). In each of the five upper notes the text sits above the node rows and the nodes sit in the lower part of the note; the lower row holds the red Caution note (S6) and the yellow "Config keys (1/2)" / "(2/2)" tables.
- `canvas-error-handler.png` (3200×2000): whole canvas of `[Odaji] 01 Error Handler v1.0.0`, same procedure (zoom 33.0%).
- `canvas-config-sticky.png` (1568×2272): element screenshot at 100% zoom of the Config note (784×1136) that covers `Config` / `Route by Source` / `Skip Disabled Trigger`. Its text is the overview plus the `TRIGGERS_ENABLED` explanation; the key table moved into the two notes below.
- `canvas-config-keys-1.png` (3008×2944) / `canvas-config-keys-2.png` (3008×3040): element screenshots at 100% zoom of "Config keys (1/2)" (`TZ` … `MAIL_PARSERS`, 1504×1472) and "(2/2)" (`LEGAL_ENTITY_TOKENS` … `SOURCE`, 1504×1520). All three columns are fully visible.
- `thumbnail.png` (1200×630): crop of the Intake group of the main canvas (`Check File Is CSV` … `Collect Transactions`) at 58% zoom (600×315 CSS px at 2×). Sticky notes are not hidden (their text sits above the node rows, outside the crop); only the red "no credential selected" badges were hidden with browser-side CSS. The workflow itself is unchanged. Opaque background, so it works on light or dark listing pages.
- Layout rule: the rendered height of every note's text was measured with Playwright (`TEXT_SIZE` in `build/build_workflow.py`); the build keeps at least 48 px between the bottom of the text and the first node row and at least 40 px below the last node row (labels included). Measured result: no node intersects any note's text area (text + 40 px), no note is clipped vertically or horizontally, and no notes overlap (before: 33 text/node intersections and 2 clipped notes in the main workflow, 6 and 1 in the Error Handler).
- Environment: local n8n 2.40.5 (see `ASSUMPTIONS.md`), Playwright 1.63.0 + Chromium 141.0.7390.37 (`/opt/pw-browsers/chromium-1194`), headless, `deviceScaleFactor: 2`, 2026-09-23. Signed in as the owner, view only (no node opened, nothing saved, run or pinned). The shots were taken on temporary copies of the same JSON registered through the API and deleted afterwards.
- Script: `/tmp/claude-0/-home-user-4S-search/3170e1bf-16ee-57f4-89e0-ecee08729771/scratchpad/p4c-scratch/shots-p4c.js` (helpers in `p4-scratch/shots/lib.js`, measurement in `measure.js` + `analyze.py`). Kept out of the repo because it contains the sign-in flow; the password is read from a scratch secrets file and never printed.
- Regenerate: after editing a note's text, re-measure its height with `measure.js`, update `TEXT_SIZE`, rebuild, run `node shots-p4c.js` again and copy the six files from `out/` here.

## 参考 / References（2026-09-23 取得）

- n8n Docs, Keyboard shortcuts（Canvas zoom: `1` = zoom to fit, `0` = reset, Ctrl/Cmd + mouse wheel）: https://docs.n8n.io/build/keyboard-shortcuts.md
