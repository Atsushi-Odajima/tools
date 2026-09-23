<!--
BOOTH 商品ページ（日本語）の原稿。根拠は README.ja.md / SETUP.ja.md / LICENSE.md / CHANGELOG.md / tests/RESULTS.md / BLOCKERS.md。
BOOTH の商品説明欄は Markdown を解釈しないため、貼り付け時は見出し記号と表を整形し直す。画像は末尾「掲載画像」の順で登録する。
配布 zip の `shared/` は本文の「同梱物」に書いた 5 ファイル（`sheets-schema.md`、`invoices.template.csv`、`transactions.template.csv`、`messages.ja.json`、`messages.en.json`）だけを入れる（リポジトリの `shared/` には他製品用の雛形 CSV もある）。
-->

# 入金消込 — Bank Deposit Reconciliation（n8n 2.x ワークフローテンプレート）

ワークフロー名：`[Odaji] 01 Bank Deposit Reconciliation v1.0.0`（本体）／`[Odaji] 01 Error Handler v1.0.0`（Error Workflow）

銀行の入出金 CSV と入金通知メールを Google Sheets の請求一覧と自動で突き合わせ、「誰から・どの請求の入金か」を判定し、確認が必要な分だけ通知します。

## こんな方向け

- 請求書払い（銀行振込）で売上を回収しているフリーランス、小規模 EC、BtoB の小規模事業者。
- 月に数十〜数百件の入金を、通帳（入出金明細）と請求一覧を見比べて手で消し込んでいる方。
- 請求一覧を Google Sheets で管理できる方（既存の一覧は所定の列名に合わせれば使えます）。

## Before / After

**Before**
- 入出金明細と請求一覧を並べ、1 件ずつ金額と振込名義を目で照合している。
- 振込手数料を差し引いた入金や、2〜3 件まとめて振り込まれた入金は、差額や合計を確かめてから該当する請求を探している。
- 請求の登録が間に合わなかった入金は保留にし、後日もう一度明細を見返している。

**After**
- 銀行 CSV を Google Drive の監視フォルダに置く（または入金通知メールが Gmail に届く）と、`invoices` シートの `status` / `paid_amount` / `paid_date` が更新され、入金は `transactions` シートに記録される。
- 手数料差引（既定 110〜880 円）、2〜3 件の合算、一部入金は規則で判定し、確定した内容を通知に理由付きで列挙する（「（手数料 ¥220 差引）」「（合算）」「（一部入金・残 ¥150,000）」）。
- 消し込めなかった入金は毎朝 09:00（JST、変更可）に再突合され、請求を登録すれば翌朝に消し込まれる。人が見るのは通知の「要確認」「候補複数」「未消込」と「警告」だけ。

## できること

### 処理の流れ（5 ステップ）

1. **取込**：3 系統のトリガー。Google Drive の監視フォルダに置かれた銀行 CSV（Shift_JIS／UTF-8 BOM、列の対応は `CSV_MAPPING`）、Gmail の入金通知メール（`MAIL_PARSERS` の正規表現で金額・名義・日付を抽出）、毎朝の再突合。系統ごとに `Config` の `TRIGGERS_ENABLED` で ON／OFF。出金行は無視。
2. **正規化**：振込名義を NFKC 正規化 → ひらがな→カタカナ → 法人格（`カ)` `株式会社` など）除去 → 空白・記号除去 → 先頭の数字列除去。入金ごとに `txn_id`（`日付|金額|正規化名義|正規化メモ`）を決める。
3. **突合**：`invoices` の `status` が `unpaid` / `partial` で通貨が JPY の請求を対象に、下表の規則 1〜5 で判定。`transactions` に既にある `txn_id` は skip（同じ CSV を 2 回置いても二重消込しない）。
4. **シート更新**：`invoices` を `invoice_id`、`transactions` を `txn_id` で Append or Update。通知より先に書く。
5. **通知**：1 行のサマリ（処理 N 件｜自動消込 A｜要確認 B｜未消込 C）と 4 区分の明細（自動消込／要確認／候補複数／未消込）、取込の警告を、設定したチャネルへ送る。

### 突合ルールと自動確定の範囲

「残額」は `amount − paid_amount`。「名義一致」は正規化した振込名義が `customer_name` または `payer_name_alias` の正規化値と完全一致、または 3 文字以上の包含一致。

| 規則 | 条件 | `invoices` の更新 | 自動確定 | 通知の区分 |
|---|---|---|---|---|
| 1 | 名義一致 かつ 残額＝入金額 の請求が 1 件 | `paid`、`auto` | する | 自動消込 |
| 2 | 残額＝入金額 が 1 件、名義一致が 0 件 | `paid`、`amount_only` | する | 要確認 |
| 3a | 名義一致 1 件で、残額−入金額 が `FEE_SET`（既定 110〜880 円）にある | `paid`、`fee_deducted`、差額を `fee_deducted` 列に記録 | する | 要確認 |
| 3b | 名義一致 2〜3 件の残額合計が入金額と一致し、組合せが 1 通り | 該当全件 `paid`、`combined` | する | 要確認 |
| 3c | 名義一致 1 件で、入金額 < 残額 | `partial`、`paid_amount` に加算 | する | 自動消込（残額を明記） |
| 3d | 名義一致 1 件で、入金額 > 残額 | 変更しない。`transactions` は `ambiguous` | しない | 候補複数 |
| 4 | 候補が複数あり決めきれない（同額の請求が複数 など） | 変更しない。`transactions` は `ambiguous`、候補上位 3 件を `suggested_invoice_ids` に | しない | 候補複数 |
| 5 | いずれにも当たらない | 変更しない。`transactions` は `unmatched`、類似候補上位 3 件を `suggested_invoice_ids` に | しない | 未消込 |

- 自動で確定するのは規則 1・2・3a・3b・3c だけです。2・3a・3b は確定しますが「要確認」として通知に列挙します。
- 金額一致を必須にしているのは、振込名義がカナで届き、個人名では同姓同名が起きるためです。名義だけでは確定しません。
- 候補複数・未消込・超過入金は人が `invoices` と `transactions` を直して確定します。

### 通知先

- Slack（Block Kit）、メール（Gmail）、LINE（Messaging API push）、Chatwork。`Config` の `NOTIFY_CHANNELS` に配列で列挙し、複数可。通知先なし（空配列）でも動きます。
- 設定した全チャネルへ送り、一部が失敗しても残りには届きます。全チャネルが失敗したときだけ実行が失敗し、同梱の Error Workflow に通知されます。
- 通知文面は `Config` の `LANG`（`ja` / `en`）で切替。文面自体は `Config` の `MESSAGES` で編集できます。
- 毎朝の再突合では、状態の変化か取込の警告があるときだけ通知します。

## 同梱物

| ファイル / フォルダ | 内容 |
|---|---|
| `workflow.json` | 本体ワークフロー（30 ノード＋日英併記の付箋 8 枚）。n8n に取り込むファイル |
| `error-handler.json` | Error Workflow（11 ノード＋日英併記の付箋 4 枚）。本体の失敗を通知する |
| `README.ja.md` / `README.en.md` | 製品説明（何ができるか・どう動くか）。日本語／英語 |
| `SETUP.ja.md` / `SETUP.en.md` | 導入手順。日本語／英語 |
| `DESIGN.md` | 設計書（ノード構成図、データの形、判断理由、Code ノードの疑似コード）。改変するときに読む |
| `LICENSE.md` | ライセンス（単一事業者、日英） |
| `CHANGELOG.md` | 更新履歴（Keep a Changelog 形式） |
| `code/` | Code ノード 8 本の JavaScript 原本（`workflow.json` / `error-handler.json` に同じ内容が埋め込まれている。動作には不要） |
| `build/build_workflow.py` | `code/` と設定から `workflow.json` / `error-handler.json` を再生成するスクリプト（改変者向け。動作には不要） |
| `fixtures/` | 試運転用の架空データ：銀行 CSV 3 本（Shift_JIS、Shift_JIS＋説明行、UTF-8 BOM）、入金通知メール 2 通（`.eml`）、請求 20 件・取引 1 件の seed、`CSV_MAPPING` / `MAIL_PARSERS` の設定例。`fixtures/README.md` に期待結果の表 |
| `tests/` | 受け入れテスト一覧（`CASES.md`）、実行記録（`RESULTS.md`、`SMOKE.md`、`results/`）、Code ノードの単体テストと固定データ（改変者向け） |
| `docs/` | キャンバス画像 6 枚（本体・Error Workflow の全体図、Config 付箋、Config キー一覧 2 枚、サムネイル）と撮影条件 |
| `shared/` | `sheets-schema.md`（スプレッドシートの作り方と列の定義、日英）、`invoices.template.csv` / `transactions.template.csv`（シートに取り込む空テンプレ）、`messages.ja.json` / `messages.en.json`（通知文面の原本） |

ワークフローのノード名は英語、キャンバスの付箋は日英併記です。README・SETUP・LICENSE・シート定義は日本語版と英語版を同梱しています。DESIGN.md とテスト記録は主に日本語で、英語の要約を付けています（一部のテスト記録は英語）。

## 必要なもの

| 項目 | 必須 | 備考 |
|---|---|---|
| n8n 2.x | 必須 | 2.40.5（セルフホスト）で構築・検証。セルフホスト／n8n Cloud のどちらでも取り込めます（組み込みノードのみ。コミュニティノード、`Read/Write Files from Disk` は不使用）。**n8n Cloud での実機検証は行っていません。** Code ノードを使うため、セルフホストではタスクランナーが動く標準構成であること |
| Google アカウント | 必須 | Google Sheets（台帳）、Google Drive（CSV の監視フォルダ）。Gmail は入金通知メールの取込かメール通知を使う場合のみ。n8n の Credential は Google Sheets OAuth2 / Google Drive OAuth2 / Gmail OAuth2 |
| Google スプレッドシート 1 冊 | 必須 | `invoices` と `transactions` の 2 シート。`shared/sheets-schema.md` の手順で作成 |
| 銀行の入出金明細 CSV、または入金通知メール | 運用時に必須 | どちらか一方でも可 |
| Slack / LINE / Chatwork | 任意 | Slack は Bot User OAuth Token（`chat:write`）、LINE は Messaging API のチャネルアクセストークン、Chatwork は API トークン |

外部サービスの料金は各社の契約によります。本テンプレは Google Sheets / Drive / Gmail の API を通常の範囲で呼び出します（シート読み込みは 1 実行につき 2 回、ポーリングは Drive 毎分・Gmail 5 分ごと）。

## 非対応・制限

- 通貨は JPY のみ。`invoices.currency` が JPY 以外の行は突合せず、通知の「警告」に出します。
- 特定の銀行との互換は保証しません。CSV は `CSV_MAPPING`（列見出し、見出し前に捨てる行数、日付形式、文字コード）で自行の形式に合わせます。同梱の架空 CSV は 2 形式（`日付,摘要,入金額,出金額,残高` と `取引日,内容,お預入,お引出`）です。
- 入金通知メールは正規表現の設定式です。架空のサンプル 2 通（ラベル行形式、表形式）を同梱しており、自行の通知に合わせて `MAIL_PARSERS` を調整します。1 通＝1 入金として扱い、1 通に複数の入金が並ぶ形式には対応しません。
- 台帳は Google Sheets（`invoices`、`transactions`）です。他のデータベースには書きません。
- 会計ソフトへの記帳は行いません。督促メール、外貨、消費税の判定も行いません。
- 通帳画像や PDF の読み取り、特定の Web バンキング画面との互換保証は対象外です。
- 候補複数・未消込・超過入金は自動確定しません。人がシートを直します。
- `invoices` と `transactions` は実行のたびに全行読みます。`transactions` が 1 万行程度を超えたら年次でシートを分けることを推奨します。
- 元の CSV やメールは保存しません（n8n の実行ログには通常どおりノードの入出力が残ります）。

## 導入時間

`SETUP.ja.md` の手順で約 30 分を目標にしています（n8n を初めて使う方を想定）。内訳：スプレッドシート作成 5 分、Google 側の準備 10〜15 分、通知先の準備 3〜10 分（使う分だけ）、ワークフローの取込と Credential 割当 5 分、`Config` の編集 3〜5 分、トリガーノードの値 2 分、同梱データでの動作確認 5 分、本番化 3 分。最も時間がかかるのは Google Cloud の OAuth 設定で、n8n Cloud で「Sign in with Google」が使える場合はその部分を省略できます。

## よくある質問

**n8n Cloud で動きますか？**
組み込みノードだけで作り、Cloud で使えないノードは使っていないため、2.x 系の Cloud で動く想定です。ただし作者が検証したのはセルフホストの n8n 2.40.5 だけで、Cloud での実機検証はしていません。Cloud では Google の Credential に「Sign in with Google」が使えます。

**自分の銀行の CSV で動きますか？**
`CSV_MAPPING` で列見出し・見出し前の説明行数（`skip_rows`）・日付形式（`yyyy/MM/dd`、`yyyyMMdd`、`yyyy-MM-dd`）・文字コード（Shift_JIS 既定、UTF-8 BOM は自動判定）を合わせれば多くの入出金明細に対応できますが、特定銀行との互換は保証しません。金額のカンマ・`¥`・`円` は自動で除去します。設定例は `fixtures/csv_mapping.examples.json` にあります。

**入金通知メールはどう扱いますか？**
`Config` の `MAIL_PARSERS` に差出人・件名の部分一致と、金額・名義・日付の正規表現を設定します。本文はテキストを優先し、HTML でも動きます。架空のサンプル 2 通と対応する設定例を同梱しています。どのパーサにも一致しないメールは警告として通知します。Gmail の検索式（既定 `subject:(入金 OR Deposit) newer_than:1d`）は自行の件名に合わせて変えてください。

**手数料を差し引いて振り込まれた場合は？**
残額との差が `FEE_SET`（既定 `[110,165,220,275,330,440,550,660,770,880]` 円）のいずれかで、名義が一致する請求が 1 件あれば `paid` にし、差額を `fee_deducted` 列に書き、通知の「要確認」に「（手数料 ¥220 差引）」のように出します。`FEE_SET` は編集できます。差額が `FEE_SET` にない場合は一部入金として扱います。

**一部入金があった場合は？**
名義が一致する請求が 1 件で、入金額が残額より少なければ `status=partial`、`paid_amount` に加算し、通知の「自動消込」に残額を出します。残りが後日振り込まれれば、そのときの残額と一致して `paid` になります。同じ日に同じ請求へ 2 回に分けて振り込まれた場合、2 回目は翌朝の再突合で消し込まれます。

**同額の請求が複数あるときは？**
名義で 1 件に絞れれば規則 1 で確定します。絞れないときは自動確定せず「候補複数」として候補を通知し、`transactions.status=ambiguous`、`suggested_invoice_ids` に候補を書きます。人が `invoices` の `status` / `paid_amount` と `transactions.status` を直します。`payer_name_alias` に振込名義（カナ）を登録しておくと、この状況を減らせます。

**同じ CSV を再投入したら？**
`txn_id`（`日付|金額|正規化名義|正規化メモ`）が `transactions` に既にあれば skip し、通知は「新規の入金はありませんでした（処理済みのため skip：N 件）」になります。シートに差分は出ません。同じメールが再配信された場合も同様です。`invoices.matched_txn_ids` に記録済みの入金も再適用しません。

**通知先を複数にできますか？**
できます。`NOTIFY_CHANNELS` に `slack` / `email` / `line` / `chatwork` を配列で列挙します（例：`["slack","email"]`）。一部が失敗しても残りには届き、全チャネルが失敗したときだけ実行が失敗して Error Workflow に回ります。Error Workflow 側の `Config` にも同じ通知設定を入れます。使わないチャネルの `Notify …` ノードは無効化します（Credential 未設定のノードが有効のままだと Publish できません）。

**英語の通知にできますか？**
`Config` の `LANG` を `"en"` にすると通知文面が英語になります（`shared/messages.en.json` と同じ内容）。Error Workflow の `Config` の `LANG` も合わせます。

**何を検証しましたか？**
確認済み（2026-09-23、セルフホスト n8n 2.40.5）：Code ノード 8 本の単体テスト 10 スイート合格。ローカル n8n での 15 経路のスモーク実行と、受け入れテスト R01〜R23（22 ケース PASS、1 ケースは定義上対象なし、FAIL 0）。同一 CSV の 2 回投入・同じメールの 2 回投入・再突合の 2 回連続で書込みが発生しないこと（冪等）。Shift_JIS の CSV が文字化けせず読めること、UTF-8 BOM が見出しに残らないこと。n8n-mcp の `validate_workflow` で両ファイルともエラー 0。秘密検出 grep 0 件。
未検証（作者の環境に Credential が無いため）：Google Sheets / Drive / Gmail の実 API（Google ノードは固定データで代替）、Slack / Gmail 送信 / LINE / Chatwork への実到達（LINE と Chatwork はローカルの受信先で本文を確認、Slack と Gmail 送信はノード設定のみ）、n8n Cloud での動作、実在の銀行の CSV や通知メール（fixtures はすべて架空）。詳細は同梱の `tests/RESULTS.md` と `README.ja.md` §10 にあります。同梱の試運転手順で自分の環境で確認してから本番運用に入ってください。

## ライセンス・サポート

**ライセンス（`LICENSE.md`、単一事業者ライセンス）**
- 購入者 1 事業者（個人事業主 1 名、または 1 法人）が自らの業務のために利用できます。n8n のインスタンス数に制限はなく、セルフホスト・n8n Cloud のどちらでも使えます。
- 購入者の業務に合わせた改変は自由です（ノードの追加・削除、文面や `Config` の変更、Code ノードの修正を含む）。購入者の従業員・業務委託先が購入者の業務のために操作できます。
- 再販・再配布・転売・貸与・公開（無償を含む）はできません。他のテンプレート製品・有料コンテンツ・受託納品物の一部として第三者に提供することもできません（顧客ごとに購入すれば可）。同梱ドキュメント・文面・付箋の内容を別製品の販売物に転用することもできません。
- 本製品は現状有姿で提供されます。銀行 CSV や入金通知メールの形式は金融機関ごとに異なり、すべての形式との互換を保証しません。消込の誤り、通知の不達、外部サービスの課金を含む損害について作者は責任を負いません。本番運用の前に同梱の fixtures と試運転手順で確認してください。会計・税務上の取扱いについて本製品は判断しません。
- n8n は n8n GmbH の製品であり、本製品は n8n 公式・関連会社の製品ではありません。

**サポート**
- 購入日から 30 日間、メールで導入サポートを提供します（`SETUP.ja.md` どおりに導入できない場合の質問対応）。
- 改変後の動作、金融機関固有の形式への対応、n8n 自体の不具合はサポート対象外です。

## 価格

¥4,980（買い切り）。n8n・Google・Slack などの外部サービスの料金は各社の契約によります。

## 更新履歴

- v1.0.0（2026-09-23）：初版。入金消込ワークフロー本体、Error Workflow、`Config` 集約、日英ドキュメント、fixtures とテスト一式。以降の変更は同梱の `CHANGELOG.md` に記載します。

## 掲載画像

登録順に記載します。すべて `docs/` に同梱（作者の n8n 2.40.5 で撮影、2026-09-23）。

1. `docs/thumbnail.png`（1200×630）：本体キャンバスの取込部分（`Check File Is CSV` 〜 `Collect Transactions`）。サムネイル用。
2. `docs/canvas-main.png`（3200×2000）：本体ワークフロー `[Odaji] 01 Bank Deposit Reconciliation v1.0.0` の全体。
3. `docs/canvas-error-handler.png`（3200×2000）：Error Workflow `[Odaji] 01 Error Handler v1.0.0` の全体。
4. `docs/canvas-config-sticky.png`（1568×2272）：`Config` を説明する付箋（日英併記）。
5. `docs/canvas-config-keys-1.png`（3008×2944）：Config キー一覧（1/2）。
6. `docs/canvas-config-keys-2.png`（3008×3040）：Config キー一覧（2/2）。
