# CLAUDE.md — 決済業務 n8n テンプレート4本（販売用プロダクト）

> **使い方**：このファイルをリポジトリ直下に `CLAUDE.md` として置き、`claude` を起動して「CLAUDE.md を読んで P0 から開始」と指示する。長いと感じたら「テンプレ01〜04」の各節を `specs/0X-*.md` に切り出し、本文に `@specs/01-reconciliation.md` の参照を残してよい。
> **Codex を使う場合**：このファイルを `AGENTS.md` としてコピーし、§2.3 の MCP 設定は Codex 側の設定方法に読み替える（n8n-mcp は Claude Code 以外のクライアントでも動く）。
> **凡例**：`[HUMAN]` = 人間が事前に行う作業（OAuth 同意、API キー発行など）。エージェントは代替できないので、未完了なら `BLOCKERS.md` に記録して先へ進む。

---

## 0. 役割とゴール

あなたは n8n ワークフローの専門ビルダー兼テクニカルライターである。決済代行会社で10年、銀行振込・クレジット・コンビニ・QR決済の管理画面と加盟店サポートを担当したオーナーの実務知識を、**買い手が30分以内に自分の環境へ導入できる有料テンプレート**に落とし込む。

成果物は4本。**build 順は 01 → 03 → 04 → 02 を推奨**（02 は freee のテスト事業所と OAuth が必要で、人間待ちが発生しやすいため最後）。

| # | 製品名 | 一言 | 想定価格（JA / EN） |
|---|---|---|---|
| 01 | Bank Deposit Reconciliation／入金消込 | 銀行CSV・入金通知メール → 請求一覧と自動突合 → 通知 | ¥4,980 / $39 |
| 02 | Payment Webhook → Accounting／決済Webhook会計連携 | Stripe・PayPal の決済を freee／MF／CSV に自動記帳。返金・チャージバックはアラート | ¥7,980 / $69 |
| 03 | Unpaid Invoice Reminder／未入金リマインド | 期日超過で段階的に督促（下書き→承認→送信）。入金で自動停止 | ¥3,980 / $29 |
| 04 | Refund & Chargeback Tracker／返金・チャージバック管理 | 発生検知 → 台帳 → 証拠期限リマインド → 月次CB率 | ¥4,980 / $39 |

01 と 03 は同じ Google Sheet（`invoices`）を共有する。02 と 04 は同じ Stripe／PayPal イベントを共有する。**共通スキーマ（§5）を先に確定してから**個別実装に入ること。

---

## 1. 絶対ルール

1. **組み込みノードのみ。** コミュニティノード禁止（n8n Cloud の買い手が導入できない）。`Read/Write Files from Disk` も禁止（Cloud で使えない）。
2. **シークレット・ID を JSON に残さない。** Credential は「名前参照」のみ。Sheet ID、Slack channel ID、メールアドレス等は Config ノードのプレースホルダに置く。export 前に `grep -E "sk_(live|test)|whsec_|xoxb-|Bearer [A-Za-z0-9]|@gmail\.com"` を通し、0件を確認して記録する。
3. **調整値は Config ノードに集約。** 他ノードでの直書き禁止。
4. **推測で API を書かない。** freee／Stripe／PayPal／LINE／Chatwork／n8n のエンドポイント・フィールド名は、実装前に公式ドキュメントを WebFetch で取得して確認し、URL と確認日を `ASSUMPTIONS.md` に記録する。
5. **テストは実行して通す。** `validate_workflow` の成功は「テスト通過」ではない。ローカル n8n で fixture を流し、実行 ID と結果を `tests/RESULTS.md` に残す。通らない限りフェーズをコミットしない。
6. **冪等。** 同じ入力を2回流しても状態が変わらない（二重消込・二重記帳・二重督促を起こさない）。
7. **買い手の環境を壊さない安全側の既定値。** 督促は「下書き作成」が既定、会計連携は「dry-run（シートのみ）」が既定。実送信・実記帳は Config で明示的に ON にする。
8. **バイリンガル。** ノード名は英語（式で参照するため ASCII 固定）。Sticky Note は日英併記。通知・メール文面は Config の `LANG`（`ja`／`en`）で切替。README／SETUP／リスティングは日英別ファイル。
9. **人間を待たない。** `[HUMAN]` 未完了で進めない箇所は、モック／フィクスチャで代替して先に進み、`BLOCKERS.md` に「何が必要か・どう確認するか」を書く。
10. **オーナーの勤務先固有の仕様・画面・API を再現しない。** 業界の一般知識の範囲に留める。

---

## 2. 環境構築（P0：最初の1回）

### 2.1 [HUMAN] 事前準備
- Windows に Docker Desktop（WSL2）、Node.js 20+、Git、Claude Code を導入済み
- Google Cloud で OAuth クライアント（Web）を作成し、Sheets／Drive／Gmail／Calendar API を有効化。n8n の Credentials に「Google Sheets OAuth2」「Gmail OAuth2」「Google Drive OAuth2」「Google Calendar OAuth2」を登録
- Slack ワークスペースにテスト用チャンネル `#n8n-test` を作成し、n8n に Slack Credential を登録
- Stripe テストモードの API キー、Stripe CLI を導入（`stripe login`）
- PayPal Developer の Sandbox アプリ（client id／secret）と Sandbox の Webhook ID
- freee：開発者向けテスト事業所を作成し、OAuth アプリ登録（02 のみ）
- LINE Developers：Messaging API チャネル（channel access token、自分の userId）（任意）
- Chatwork API トークン（任意）

### 2.2 ローカル n8n（`infra/docker-compose.yml`）
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
起動後 `http://localhost:5678` で初期ユーザーを作成し、Settings → n8n API から API キーを発行（[HUMAN]）。n8n のバージョン（Settings に表示）を `ASSUMPTIONS.md` に記録し、README の「対応バージョン」に記載する。

### 2.3 Claude Code の MCP（`.mcp.json` をリポジトリ直下に置く）
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
`N8N_API_KEY` は環境変数で渡す（ファイルにキーを書かない）。Claude Code は `${VAR}` の環境変数展開に対応するが、未設定で既定値も無いと設定ファイル全体の読み込みに失敗するため、`${N8N_API_KEY:-}` のように既定値を付ける。

CLI で登録する場合：
```
claude mcp add --transport stdio --scope project --env MCP_MODE=stdio --env N8N_API_URL=http://localhost:5678 --env N8N_API_KEY=$N8N_API_KEY n8n-mcp -- npx -y n8n-mcp
```

加えて czlonkowski/n8n-skills（n8n 式の書き方・ノード設定・検証ループ回避のスキル集）を、同リポジトリの README の手順どおり導入する。導入手順は記憶で書かず README を取得して従う。

### 2.4 動作確認（これが P0 のゲート）
- `claude mcp list` で n8n-mcp が Connected
- Claude Code 内 `/mcp` でツール一覧に `n8n_create_workflow` が出る（API 接続済みの証拠）
- 最小ワークフロー（Manual Trigger → Set → Slack `#n8n-test`）を作成・実行し、Slack に届いたら P0 完了。このワークフローは削除してよい

### 2.5 Webhook を外から受ける（02・04）
- Stripe：`stripe listen --forward-to localhost:5678/webhook/<path>`。イベント発火は `stripe trigger charge.succeeded` 等
- PayPal：Sandbox からローカルへ届けるため `cloudflared tunnel --url http://localhost:5678` で一時 URL を作り、Sandbox Webhook に登録（[HUMAN]）

---

## 3. リポジトリ構成
```
/CLAUDE.md
/.mcp.json
/PROGRESS.md            # フェーズ進捗（セッション開始時に必読）
/BLOCKERS.md            # [HUMAN] 待ち事項
/ASSUMPTIONS.md         # 仕様判断・確認した公式ドキュメント URL と日付・n8n バージョン
/infra/docker-compose.yml
/shared/
  sheets-schema.md      # §5 のスキーマ（買い手向け説明含む、日英）
  invoices.template.csv # 買い手がインポートする空テンプレ（ヘッダー＋架空サンプル3行）
  transactions.template.csv
  reminders_log.template.csv
  events_ledger.template.csv
  disputes.template.csv
  messages.ja.json      # 通知・メール文面の原本（Config に埋め込む）
  messages.en.json
/templates/01-bank-reconciliation/
  workflow.json         # 販売物本体（Cloud 互換・秘密なし）
  error-handler.json    # 共通エラー通知ワークフロー（各テンプレに同梱）
  DESIGN.md             # ノード構成図（Mermaid）・データフロー・判断理由・疑似コード
  README.ja.md / README.en.md
  SETUP.ja.md / SETUP.en.md
  fixtures/             # 架空データ（実在の個人名・企業名を使わない）
  tests/CASES.md        # 受け入れテスト一覧
  tests/RESULTS.md      # 実行 ID・入出力・合否・日付
  listing/gumroad.en.md / listing/booth.ja.md / listing/note.ja.md
  LICENSE.md / CHANGELOG.md
  make/blueprint.json   # P6（任意）
/templates/02-payment-webhook-accounting/   （同構成）
/templates/03-unpaid-reminder/              （同構成）
/templates/04-refund-chargeback/            （同構成）
```

---

## 4. 共通設計規約

### 4.1 Config ノード
各ワークフローの先頭（トリガー直後）に Set ノード `Config` を置く。全ての調整値（Sheet ID、シート名、通知チャネル、しきい値、`LANG`、モード、文面）をここに集約する。買い手は Config だけ触れば動く状態にする。Sticky Note で各キーの意味を日英で説明する。

### 4.2 命名
- ノード名：英語・動詞始まり（`Parse Bank CSV`, `Match Invoices`, `Notify Slack`）
- ワークフロー名：`[Odaji] 01 Bank Deposit Reconciliation v1.0.0`
- Sticky Note：`## JA` → `## EN` の順で併記。色は 入力＝青、判定＝黄、出力＝緑、注意＝赤 に統一

### 4.3 通知チャネル（Config `NOTIFY_CHANNELS` 配列で複数可）
- `slack`：Slack ノード（Block Kit で見出し＋箇条書き）
- `email`：Gmail ノード
- `line`：HTTP Request → LINE Messaging API push（`https://api.line.me/v2/bot/message/push`、Bearer channel access token、`to` = userId）。**LINE Notify は 2025 年 3 月に終了しているので使わない。**
- `chatwork`：HTTP Request → `https://api.chatwork.com/v2/rooms/{room_id}/messages`（ヘッダ `X-ChatWorkToken`）
- 未設定チャネルはスキップ。全チャネル失敗時は Error Workflow へ

### 4.4 エラー処理・冪等性
- 各テンプレに `error-handler.json`（Error Trigger → 通知）を同梱し、ワークフロー Settings の Error Workflow に指定する手順を SETUP に書く
- HTTP Request は Retry On Fail（3回・待機 2s）。`Continue On Fail` はシート書込み等の副作用が無い箇所だけ
- 冪等性キーを必ず持つ：01 = `txn_id`、02 = `event_id`、03 = `(invoice_id, stage)`、04 = `(source, object_id, event_type)`。処理前に台帳シートを読み、既存なら skip

### 4.5 タイムゾーン・日付・金額
- ワークフロー Settings の Timezone を `Asia/Tokyo` に固定（Config でも `TZ` を持ち、式は `$now.setZone($('Config').item.json.TZ)`）
- 日付は Luxon で扱い、シートへは `yyyy-MM-dd` 文字列で書く
- 金額は整数（円）。全角数字・カンマ・`¥`・`円` を除去して `parseInt`。JPY 以外はテンプレ02 の通貨ルール

### 4.6 Code ノード
- JavaScript のみ。`require` 禁止（Cloud で動かない）。Node.js 20 の組み込みグローバルは可（`TextDecoder`, `Intl`, `Buffer` など）。ハッシュが必要なら Crypto ノード
- 1 Code ノード＝1責務。ロジックは `DESIGN.md` に疑似コードで併記する

### 4.7 セキュリティ
- Webhook は必ず署名検証（Stripe Trigger ノードは自動、PayPal は verify-webhook-signature API を呼ぶ）
- シートには必要最小限の個人情報のみ。SETUP に「顧客メール・氏名を扱う場合の注意」を明記

---

## 5. 共有 Google Sheets スキーマ

1つのスプレッドシートに以下のシートを作る（`shared/*.template.csv` を買い手がインポート）。列名は英語固定（式参照のため）、1行目ヘッダー、2行目以降データ。

### invoices（01・03 が共有）
| 列 | 型 | 説明 |
|---|---|---|
| invoice_id | text, unique | 請求番号 |
| customer_id | text | 任意 |
| customer_name | text | 請求先名（漢字可） |
| payer_name_alias | text | **振込名義（カナ）をカンマ区切りで。** 銀行の振込名義はカタカナで届くため、漢字の請求先名だけでは照合できない。SETUP で「必須級」として案内する |
| customer_email | text | 03 の送信先 |
| amount | int | 税込請求額（円） |
| currency | text | 既定 `JPY` |
| issue_date / due_date | date | `yyyy-MM-dd` |
| status | enum | `unpaid` / `partial` / `paid` / `overpaid` / `cancelled` / `escalated` |
| paid_amount | int | 累計入金額 |
| paid_date | date | 最終入金日 |
| matched_txn_ids | text | カンマ区切り |
| match_confidence | enum | `auto` / `amount_only` / `fee_deducted` / `combined` / `manual` |
| fee_deducted | int | 先方負担の振込手数料差額 |
| remind_stage | int | 0〜3（03 が更新） |
| last_reminded_at | datetime | |
| promised_date | date | 入金予定を聞き取ったら記入。未来日なら督促を止める |
| do_not_remind | bool | TRUE で督促対象外 |
| notes | text | |

### transactions（01）
`txn_id`（`date|amount|payer_norm|memo_norm` の連結文字列）, `source`(`bank_csv`/`gmail`/`manual`), `txn_date`, `payer_name_raw`, `payer_name_norm`, `amount`, `memo`, `matched_invoice_ids`, `status`(`matched`/`unmatched`/`ambiguous`/`ignored`), `suggested_invoice_ids`, `imported_at`

### reminders_log（03）
`invoice_id`, `stage`, `mode`(`draft`/`sent`), `channel`, `to`, `subject`, `sent_at`, `gmail_message_id`

### events_ledger（02）
`event_id`, `source`(`stripe`/`paypal`), `event_type`, `object_id`, `occurred_at`, `currency`, `gross`, `fee`, `net`, `gross_jpy`, `fee_jpy`, `net_jpy`, `fx_rate`, `customer_ref`, `booking_status`(`dry_run`/`booked`/`skipped`/`error`), `accounting_ref`（freee の取引 ID 等）, `error_message`

### disputes（04）
`record_id`(`source|object_id`), `source`, `type`(`refund`/`dispute`/`early_fraud_warning`/`manual`), `status`, `amount`, `currency`, `customer_ref`, `reason`, `opened_at`, `evidence_due_by`, `last_alert_stage`, `outcome`, `closed_at`, `notes`

---

## 6. フェーズとコミットゲート（各テンプレ共通）

| Phase | 内容 | ゲート（満たすまでコミット禁止） |
|---|---|---|
| P0 | §2 環境構築（初回のみ） | §2.4 の Slack 疎通 |
| P1 | 仕様確定：`DESIGN.md`（Mermaid ノード図・データフロー・判断理由・疑似コード）、`tests/CASES.md`、`fixtures/` | CASES が仕様の全分岐を網羅 |
| P2 | 実装：n8n-mcp で作成 → `validate_workflow` 合格 → ローカル n8n に登録 → `workflow.json` export | 秘密検出 grep 0件、組み込みノードのみ |
| P3 | テスト：CASES を全て実行、`RESULTS.md` に実行 ID／入出力／合否。2回連続実行で状態不変（冪等） | 全ケース PASS |
| P4 | ドキュメント：README／SETUP 日英、Sticky Note 日英、（任意）Playwright でキャンバスのスクリーンショット | 第三者が SETUP だけで30分以内に導入できる粒度 |
| P5 | 販売パッケージ：listing 日英・LICENSE・CHANGELOG・価格・FAQ・サポート方針。`git tag 0X-v1.0.0` | §7 全項目 ✅ |
| P6（任意） | Make ブループリント版（Make MCP または手組み）。[HUMAN] が Make 無料枠で import 確認 | import 成功 |

コミット規約：`feat(01): ...` / `test(01): ...` / `docs(01): ...` / `chore: ...`。1フェーズ1コミット以上。

---

## 7. Definition of Done（テンプレごと）
- [ ] 新規の n8n（Cloud 想定）に import して赤ノード無し
- [ ] 秘密・個人 ID ゼロ（grep 記録あり）
- [ ] Config だけで設定完了。SETUP どおりに Credential を選び直せば動く
- [ ] `tests/CASES.md` 全 PASS、`RESULTS.md` に証拠
- [ ] 冪等（同一入力2回で差分なし）
- [ ] Error Workflow 同梱・設定手順あり
- [ ] Sticky Note 日英／README・SETUP 日英／listing 日英
- [ ] 対応 n8n バージョンを明記
- [ ] fixtures は全て架空データ

---

## 8. 販売パッケージの中身
- `listing/gumroad.en.md`：タイトル、1行の価値提案、Before／After、含まれるもの、必要なもの（n8n 版・Google・Slack 等）、非対応事項、FAQ（Cloud で動く？／自分の銀行は OK？）、ライセンス、サポート（メール30日）、価格
- `listing/booth.ja.md`／`listing/note.ja.md`：同内容の日本語版。note は「導入記事」として書き、購入導線を末尾に
- `LICENSE.md`：単一事業者ライセンス。再販・再配布・テンプレ販売への転用禁止。改変は自由
- `CHANGELOG.md`：Keep a Changelog 形式
- 価格は §0 の表を既定とし、根拠を `ASSUMPTIONS.md` に書く

---

## 9. セッション運用
1. 開始時：`CLAUDE.md` → `PROGRESS.md` → `BLOCKERS.md` → `ASSUMPTIONS.md` の順に読む
2. `PROGRESS.md` の未完了フェーズから再開。人間に質問しない。判断が必要なら決めて `ASSUMPTIONS.md` に理由を書く
3. `[HUMAN]` 待ちで詰まったら、そのテンプレの別フェーズか、別テンプレの独立作業へ切替
4. 終了時：`PROGRESS.md` に「完了フェーズ／次の一手／未解決」を更新してコミット

---
---

# テンプレ01：入金消込（Bank Deposit Reconciliation）

## 目的と買い手
請求書払い（銀行振込）のフリーランス・小規模 EC・BtoB 小規模事業者。月に数十〜数百件の入金を、通帳と請求一覧を目視で突き合わせている人。**「誰から・どの請求の入金か」を自動判定し、確認が必要な分だけ人に渡す。**

## トリガー（3系統、Config で ON／OFF）
1. `Google Drive Trigger`：Config `DRIVE_FOLDER_ID` の監視フォルダに CSV が置かれたら実行
2. `Gmail Trigger`（polling）：Config `GMAIL_QUERY`（例：`subject:(入金) newer_than:1d`）に一致するメール
3. `Schedule Trigger`：毎日 Config `RUN_AT`（既定 09:00 JST）に、未処理 transactions を再突合（前日 unmatched だったものが、請求登録後に一致するケースを拾う）

## 入力パース
**CSV**（`Extract from File` → 不可なら Code ノード）
- 文字コード：Shift_JIS が既定。組み込みノードの encoding オプションが使えるか実測し、使えなければ Code ノードで `new TextDecoder('shift_jis').decode(buffer)`。UTF-8 BOM も除去。両方の fixture で実証すること
- 列の対応は Config `CSV_MAPPING`：`{date_col, payer_col, deposit_col, withdraw_col, memo_col, skip_rows, date_format}`。fixture は2形式（A：`日付,摘要,入金額,出金額,残高`／B：`取引日,内容,お預入,お引出`）
- 出金行は無視。日付は `yyyy/MM/dd`・`yyyyMMdd`・`yyyy-MM-dd` を受ける
- 金額：全角→半角、`,`・`¥`・`円` 除去

**Gmail**
- Config `MAIL_PARSERS`：`[{name, from_match, subject_match, amount_regex, payer_regex, date_regex}]`。**特定銀行との互換を断言しない。** fixture は「実在の通知形式を模した架空メール」2種を用意し、README では「正規表現設定式・サンプル2種同梱・自行の通知に合わせて調整可」と書く
- 本文は HTML／テキスト両対応（`text` を優先）

**txn_id**：`${yyyy-MM-dd}|${amount}|${payer_norm}|${memo_norm}`。`transactions` に既存なら skip。

## 名義正規化（`Normalize Payer` Code ノード）
1. Unicode NFKC（全角英数→半角、半角カナ→全角カナ）
2. ひらがな→カタカナ
3. 法人格の略記・正式名称を除去：`ｶ) (ｶ カ） （カ ユ) (ユ ド) (ド シヤ) ザイ) ガク) イ) ホ) 株式会社 有限会社 合同会社 一般社団法人 医療法人` など（Config `LEGAL_ENTITY_TOKENS` で追加可）
4. 空白・`・`・記号除去。長音 `ー` は保持
5. 先頭の振込人番号・支店コード（数字のみの連続）を除去（Config で ON／OFF）

比較対象は `customer_name` の正規化値と `payer_name_alias` 各要素の正規化値。

## 突合アルゴリズム（`Match Invoices` Code ノード、疑似コード）
```
remaining(inv) = inv.amount - inv.paid_amount
open = invoices where status in [unpaid, partial]
for txn in txns（未処理）:
  byAmt  = open where remaining == txn.amount
  byName = open where nameMatch(txn.payer_norm, inv)   # 完全一致 or alias 一致 or 3文字以上の包含
  1. |byAmt ∩ byName| == 1            → matched, confidence=auto
  2. |byAmt| == 1 and |byName| == 0   → matched, confidence=amount_only（要確認フラグ）
  3. |byAmt| == 0:
     a. fee = remaining - txn.amount ∈ FEE_SET かつ name 一致1件 → matched, fee_deducted=fee
        FEE_SET 既定 [110,165,220,275,330,440,550,660,770,880]（Config）
     b. byName の 2〜3件の合計 == txn.amount          → matched(combined)、全件 paid
     c. |byName| == 1 and txn.amount < remaining      → partial（paid_amount 加算、status=partial）
     d. |byName| == 1 and txn.amount > remaining      → overpaid（要確認）
  4. 候補複数で決めきれない → ambiguous（自動確定しない。候補上位3件を suggested へ）
  5. それ以外 → unmatched（名前類似・金額近似の上位3件を suggested へ）
```
自動確定するのは 1・2・3a・3b・3c のみ。2 と 3a・3b は通知に「要確認」として列挙する。

## 出力
- `invoices`：status／paid_amount／paid_date／matched_txn_ids／match_confidence／fee_deducted を「Append or Update（invoice_id で一致）」
- `transactions`：全 txn を追記（matched／unmatched／ambiguous）
- 通知（§4.3）：サマリ（処理 N 件／自動消込 A／要確認 B／未消込 C）＋ 要確認・未消込の明細（日付・名義・金額・候補）。文面は `shared/messages.*.json` の `recon_summary`

## fixtures
- `bank_A_sjis.csv`（Shift_JIS、15行：出金混在、カンマ入り金額、全角名義、手数料差引1件、合算1件、一部入金1件）
- `bank_B_utf8bom.csv`
- `mail_bankX.eml`／`mail_bankY.eml`（架空）
- `invoices.seed.csv`（20件：alias あり／なし、同額の請求2件で ambiguous を作る）

## 受け入れテスト（`tests/CASES.md` に転記し全て PASS）
| ID | 入力 | 期待 |
|---|---|---|
| R01 | 名義・金額一致 | auto, paid |
| R02 | 金額のみ一致・候補1 | amount_only, paid, 通知に要確認 |
| R03 | 手数料 220 差引 | fee_deducted=220, paid |
| R04 | 2請求の合算 | combined, 2件 paid |
| R05 | 一部入金 | partial, paid_amount 加算 |
| R06 | 同額請求2件・名義不一致 | ambiguous, 自動確定なし |
| R07 | 出金行 | 無視 |
| R08 | Shift_JIS | 文字化けなく名義が読める |
| R09 | 同一 CSV を2回投入 | 2回目は全件 skip、シート差分なし |
| R10 | Gmail 通知 | amount／payer／date 抽出、R01 と同じ経路で消込 |
| R11 | 全チャネル通知 | slack／email／line／chatwork それぞれ到達（設定分のみ） |

## 既知の落とし穴（SETUP に必ず書く）
- 振込名義はカナ。`payer_name_alias` を埋めないと自動消込率が大きく落ちる
- 個人名の名義は同姓同名が起きる → 金額一致を必須にしている理由
- 銀行 CSV は月をまたぐと形式が変わることがある（見出し行の有無）→ `skip_rows`

---

# テンプレ02：決済 Webhook → 会計連携（Payment Webhook → Accounting）

## 目的と買い手
Stripe／PayPal でオンライン販売している個人〜小規模事業者。決済ごとの売上・手数料・入金を freee／マネーフォワード／汎用 CSV に自動で起票し、返金・チャージバックは記帳せずアラートで人に渡す。

## 対象イベント
**Stripe（`Stripe Trigger` ノード：署名検証込み。有効化時に Webhook を自動作成する挙動を公式ドキュメントで確認）**
- `charge.succeeded` → 売上計上（`balance_transaction` を `GET /v1/balance_transactions/{id}` で取得し fee／net／exchange_rate を得る）
- `charge.refunded` → 返金計上（Config `BOOK_REFUNDS`、既定 OFF＝アラートのみ）
- `charge.dispute.created`／`charge.dispute.closed` → アラート（`closed` かつ `lost` の時のみ、Config ON で計上）
- `payout.paid` → 未収入金 → 普通預金 の振替（Config `BOOK_PAYOUTS`、既定 ON）

**PayPal（`Webhook` ノード＋署名検証 `POST /v1/notifications/verify-webhook-signature`）**
- `PAYMENT.CAPTURE.COMPLETED`（fee は `seller_receivable_breakdown.paypal_fee`）
- `PAYMENT.CAPTURE.REFUNDED`
- `CUSTOMER.DISPUTE.CREATED`／`CUSTOMER.DISPUTE.RESOLVED`

署名検証に失敗した Webhook は 400 を返して破棄し、Error Workflow へ。

## 通貨・金額
- Stripe は最小単位。**ゼロ小数通貨**（JPY, KRW, VND など。公式一覧を取得して Config `ZERO_DECIMAL_CURRENCIES` に持つ）はそのまま、他は ÷100
- 外貨は `balance_transaction.exchange_rate` で円換算し `*_jpy` 列へ。換算レートも保存
- 消費税：Config `TAX_MODE`（`inclusive_10` 既定／`inclusive_8`／`exempt`／`none`）。**カード決済手数料は非課税として扱うのが一般的**だが、既定は Config で明示し、README に「税理士に確認」を必ず書く

## 記帳モード（Config `ACCOUNTING_MODE`）
1. `dry_run`（既定）：`events_ledger` に書くだけ。買い手が数日ログを見て納得してから切替
2. `freee`：OAuth2（Authorization Code）Credential。会社 ID（Config）。実装前に公式ドキュメントで確認：取引作成 API、口座振替 API、勘定科目一覧 API、税区分一覧 API。勘定科目名（`売上高`／`支払手数料`／`未収入金`／`普通預金`）は Config に持ち、初回実行時に一覧 API で ID を解決してキャッシュ
3. `mf`：マネーフォワード クラウド会計 API の利用可否・仕訳作成の可否を確認。API で仕訳が作れない／パートナー登録が要る場合は、**`csv` モードで MF 取込形式の仕訳 CSV を日次生成**する代替を正式に提供し、README に理由を書く
4. `csv`：汎用の仕訳 CSV（日付・借方科目・借方金額・貸方科目・貸方金額・税区分・摘要）を Google Drive の Config フォルダに日次出力（freee／MF／弥生の取込に流用可能）

仕訳の既定（JPY, `charge.succeeded`）：
- 借方 未収入金（Stripe） net／借方 支払手数料 fee／貸方 売上高 gross
- `payout.paid`：借方 普通預金 amount／貸方 未収入金（Stripe） amount
- 摘要：`Stripe {charge_id} {customer_email or description}`

## 冪等・信頼性
- `event_id` を `events_ledger` で先に検索し、既存なら 200 で終了（Stripe／PayPal は再送する）
- 会計 API 失敗時は `booking_status=error` を記録し、Schedule Trigger（毎時）で `error` を再試行（最大5回）
- 1イベント＝1トランザクション。部分成功を残さない（freee 作成成功 → シート更新失敗 を防ぐため `accounting_ref` を先に書いてから次へ）

## fixtures／テスト
- `stripe trigger charge.succeeded`／`charge.refunded`／`charge.dispute.created`／`payout.paid`（テストモード）
- PayPal Sandbox の Webhook Simulator
- `tests/CASES.md`：A01 売上 JPY／A02 売上 USD 換算／A03 返金アラートのみ／A04 返金記帳 ON／A05 dispute created アラート／A06 dispute lost 記帳／A07 payout 振替／A08 同一 event_id 再送で skip／A09 署名不正で 400／A10 freee API 失敗→再試行／A11 dry_run で会計未書込／A12 csv 出力形式

## 既知の落とし穴
- Stripe の入金（payout）はチャージの数日後にまとまる。チャージ時に売上、入金時に振替の2段階にしている理由を README に図解
- 返金は元の売上を取り消すのではなく、返金日で計上するのが一般的。既定 OFF の理由も書く
- PayPal の保留（hold）や通貨換算手数料は別イベント。非対応と明記

---

# テンプレ03：未入金リマインド（Unpaid Invoice Reminder）

## 目的と買い手
01 と同じ層。**期日超過を毎朝チェックし、段階的に文面を強めた督促メールを「下書き」で用意する。** オーナーは Gmail の下書きを確認して送るだけ。慣れたら自動送信に切替。入金（01 が `paid` にする）で自動停止。

## トリガー
`Schedule Trigger` 毎日 Config `RUN_AT`（既定 10:00 JST）。営業日判定：土日は Config `SKIP_WEEKENDS`（既定 ON）、日本の祝日は Google Calendar ノードで `ja.japanese#holiday@group.v.calendar.google.com` を照会（既定 ON。失敗時は Config `HOLIDAYS` の静的リストにフォールバック）。非営業日は何もしない。

## ステージ（Config `STAGES`、日数は変更可）
| stage | 条件 | 件名（JA） | トーン |
|---|---|---|---|
| 0（既定 OFF） | due_date − 3日 | お支払期限のご案内 | 事前案内 |
| 1 | due_date ＋ 1日 | お支払いのご確認のお願い | 丁寧・行き違い配慮 |
| 2 | due_date ＋ 7日 | 【再送】お支払いのお願い | 明確・期限明記 |
| 3 | due_date ＋ 14日 | 【重要】お支払いに関する最終のご連絡 | 最終・以後の対応を予告 |

stage 3 送付後は `status=escalated`、オーナーに個別通知し、以後は自動送信しない。

## 判定ロジック
```
for inv in invoices where status in [unpaid, partial] and do_not_remind != TRUE:
  if promised_date and promised_date >= today: skip
  days = today - due_date（JST、日付単位）
  target_stage = 最大の stage where days >= STAGES[stage].offset
  if target_stage > inv.remind_stage and (invoice_id, target_stage) not in reminders_log:
     send/draft(target_stage); update remind_stage, last_reminded_at; append reminders_log
```
残額 = amount − paid_amount。partial の場合は文面で残額を明示。同一顧客に同日複数請求がある場合は1通にまとめる（Config `GROUP_BY_CUSTOMER` 既定 ON）。

## 送信モード（Config `SEND_MODE`）
- `draft`（既定）：Gmail ノードで下書き作成。オーナーに「本日の下書き N 件」を通知
- `send`：Gmail ノードで送信。送信後に `gmail_message_id` を記録
- `owner_only`：顧客には送らず、オーナーに一覧のみ（試運転用）
- 送信元名・署名・振込先は Config。CC／BCC 任意

## 文面
`shared/messages.ja.json`／`.en.json` の `reminder.stage1..3` を使用。プレースホルダ：`{customer_name} {invoice_id} {amount} {remaining} {due_date} {bank_details} {sender_name} {company} {signature}`。文面は付録B を原本とする。

## fixtures／テスト
`invoices.seed.csv`（due が −3／＋1／＋7／＋14／＋30、partial、promised_date 未来、do_not_remind、paid を含む）
- U01 stage1 下書き作成／U02 同日2回実行で二重作成なし／U03 stage2 到達で件名変化／U04 stage3 で escalated＆オーナー通知／U05 paid は対象外／U06 promised_date 未来で skip／U07 do_not_remind／U08 partial で残額表示／U09 祝日で全スキップ／U10 send モードで message_id 記録／U11 同一顧客2請求で1通

## 既知の落とし穴
- 督促はトーンを間違えると顧客を失う。既定を draft にした理由を README に明記
- 「お振込みが行き違いになっている場合は何卒ご容赦ください」を stage1・2 に必ず入れる
- 祝日カレンダーは Google の共有カレンダー。組織で無効化されている場合の手順も書く

---

# テンプレ04：返金・チャージバック管理（Refund & Chargeback Tracker）

## 目的と買い手
02 と同じ層＋複数 PSP を使う小規模 EC。**返金・チャージバック・不正警告を一つの台帳に集約し、証拠提出期限を逃さない。** チャージバックは期限内に証拠を出さなければ自動的に負ける。

## トリガー
1. `Stripe Trigger`：`charge.refunded`, `refund.updated`（失敗検知）, `charge.dispute.created`, `charge.dispute.updated`, `charge.dispute.closed`, `radar.early_fraud_warning.created`
2. `Webhook`（PayPal、署名検証）：`PAYMENT.CAPTURE.REFUNDED`, `CUSTOMER.DISPUTE.CREATED`, `CUSTOMER.DISPUTE.UPDATED`, `CUSTOMER.DISPUTE.RESOLVED`
3. `n8n Form Trigger`：銀行振込・コンビニ等、API の無いチャネルの返金・異議を手入力（種別・金額・顧客・理由・期限）
4. `Schedule Trigger` 毎日 09:00 JST：期限リマインドと日次ダイジェスト。月初に月次 CB 率

## 台帳（`disputes`、§5）
`record_id = source|object_id`。`Append or Update`。状態遷移を `notes` に追記（例：`2026-09-23 needs_response → under_review`）。

## アラート
- dispute created：即時。金額・顧客・理由・**期限（`evidence_due_by` を JST 表示）**・証拠チェックリスト（付録C）・Stripe／PayPal ダッシュボードの URL
- early_fraud_warning：即時。「チャージバック化する前の自主返金を検討」を提案文に含める（実務で有効な対処）
- 期限リマインド：`evidence_due_by` の 7日前・3日前・1日前（Config `DEADLINE_ALERT_DAYS`）。`last_alert_stage` で重複防止。`status` が `needs_response` の間だけ
- 返金：`refund.updated` で `failed` → 即時。`pending` が営業日 Config `REFUND_STALE_DAYS`（既定5）超 → 日次ダイジェストで列挙
- 日次ダイジェスト：未対応 dispute（期限順）／停滞返金／本日の新規
- 月次：`disputes ÷ 当月成功決済数`（成功決済数は Stripe API で当月の charge を数える。PayPal は取得可否を確認し、不可なら Config の手入力値）。Config `CB_RATE_WARN`（既定 0.75%）／`CB_RATE_CRIT`（既定 0.9%）超で警告。カードブランドの基準は変わるため、README で「各ブランドの最新基準を確認」と書き、数値を断定しない

## fixtures／テスト
- `stripe trigger charge.dispute.created` 等、PayPal Simulator、Form 手入力
- D01 dispute created → 台帳＋即時通知＋期限表示／D02 期限 T-3 で通知、翌日再実行で重複なし／D03 dispute closed won／lost で outcome／D04 EFW 通知／D05 refund failed 即時／D06 refund pending 6営業日で列挙／D07 Form 入力が台帳に入る／D08 月次 CB 率 warn／D09 同一 event 再送 skip／D10 署名不正 400

## 既知の落とし穴
- `evidence_due_by` は UNIX 秒（UTC）。JST 変換と「当日 23:59 ではなく実時刻」を明記
- チャージバック率はブランドごとに分母・分子の定義が違う。テンプレの値は目安
- 証拠は「配送証明・注文確認・顧客とのやり取り・AVS／CVC 結果・IP／端末情報」を日頃から取れる状態にしておくこと自体が最大の対策（README に書く）

---

## 付録A 通知文（`shared/messages.*.json` に格納。ここは要約）
`recon_summary`
- JA：`【入金消込 {date}】処理 {n}件｜自動消込 {a}｜要確認 {b}｜未消込 {c}` ＋ 明細行 `・{txn_date} {payer_raw} ¥{amount} → {invoice_id or 候補: ...}`
- EN：`[Reconciliation {date}] Processed {n} | Auto-matched {a} | Needs review {b} | Unmatched {c}` ＋ `• {txn_date} {payer_raw} ¥{amount} → {invoice_id or candidates: ...}`

`dispute_created`／`deadline_reminder`／`daily_digest`／`cb_rate_alert`／`draft_summary` も同様に日英対で作る。

## 付録B 督促メール文面（原本）

### JA
**stage1**
件名：お支払いのご確認のお願い（請求書番号 {invoice_id}）
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
件名：【再送】お支払いのお願い（請求書番号 {invoice_id}）
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
件名：【重要】お支払いに関する最終のご連絡（請求書番号 {invoice_id}）
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
（stage3 でも「法的措置を取る」など具体的な法的手段を断言する文言は入れない）

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

## 付録C 証拠チェックリスト（dispute 通知に同梱）
- 注文確認メール／請求書（顧客名・金額・日付）
- 配送証明（追跡番号・配達完了・受領サイン）。デジタル商品はアクセスログ・ダウンロード記録
- 利用規約・返金ポリシーへの同意記録（チェックボックス・タイムスタンプ）
- 顧客とのやり取り（メール・チャット履歴）
- 決済時の AVS／CVC 結果、3D セキュア認証の有無
- IP アドレス・端末・過去の正常取引履歴
- 提出は期限の24時間前までに（審査側の処理時間を考慮）
