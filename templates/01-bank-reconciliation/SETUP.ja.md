# テンプレ01 入金消込 — 導入手順（SETUP）

対象：`[Odaji] 01 Bank Deposit Reconciliation v1.0.0`（`workflow.json`）と `[Odaji] 01 Error Handler v1.0.0`（`error-handler.json`）。
この手順だけで、n8n を初めて使う人が約 30 分で自分の環境に導入できることを目標にしています。上から順に進めてください。最も時間がかかりやすいのは §2（Google Cloud）です。n8n Cloud で **Sign in with Google** が使える場合は §2.1〜2.3 を省略できます。

| 節 | 内容 | 目安 |
|---|---|---|
| 0 | 所要時間と前提 | 2 分 |
| 1 | スプレッドシート作成 | 5 分 |
| 2 | Google 側の準備（Cloud プロジェクト・OAuth・n8n Credential） | 10〜15 分（Google Cloud を初めて使う場合は 15 分） |
| 3 | 通知先の準備（Slack／メール／LINE／Chatwork） | 3〜10 分（使う分だけ） |
| 4 | ワークフローの取込と Credential の割当 | 5 分 |
| 5 | `Config` の編集 | 3〜5 分 |
| 6 | トリガーノードに入れる値 | 2 分 |
| 7 | 動作確認 | 5 分 |
| 8 | 本番化 | 3 分 |
| 9 | トラブルシューティング | 必要時 |
| 10 | チェックリスト | 1 分 |

---

## 0. 所要時間と前提（2 分）

### 対応する n8n
- 開発・テストは **n8n 2.40.5（セルフホスト、Node.js 24）** で行いました。
- **n8n Cloud は 2.x 系であれば動く前提**ですが、Cloud での動作確認は行っていません。使用ノードはすべて n8n 組み込みノードのみで、コミュニティノードや `Read/Write Files from Disk` は使っていないため、Cloud でも取り込めます。
- 1.x 系では画面の表記（`Publish` が `Activate` など）が異なります。本書は 2.x の表記で書いています。

### 必要なもの
| 項目 | 必須 | 用途 |
|---|---|---|
| n8n 2.x（Cloud またはセルフホスト）にログインできる管理者アカウント | 必須 | ワークフローの取込・Credential 登録 |
| Google アカウント | 必須 | スプレッドシート、監視フォルダ。Gmail は入金通知メールの取込かメール通知を使う場合のみ（§2、§6.4） |
| Google Cloud Console にプロジェクトを作れる権限 | セルフホストでは必須（Cloud は「Sign in with Google」で省略可、§2.4） | OAuth クライアントの発行 |
| Slack ワークスペース（アプリをインストールできる権限） | 任意 | Slack 通知 |
| LINE 公式アカウント＋LINE Developers（Messaging API チャネル） | 任意 | LINE 通知 |
| Chatwork アカウント（API 利用が許可されているもの） | 任意 | Chatwork 通知 |
| 銀行の入出金明細 CSV、または銀行からの入金通知メール | 運用時に必須 | 入力データ |

### このテンプレが「しないこと」
- 特定の銀行との互換は保証しません。CSV の列名と文字コードは `CSV_MAPPING`、メールの解析は `MAIL_PARSERS` で**正規表現を自分で合わせる方式**です。架空の銀行 2 行分のサンプル（`fixtures/`）を同梱しています。
- 通貨は JPY のみです。
- 曖昧な入金（候補が複数）や該当請求がない入金は自動確定しません。通知を見て人がシートを直します。

---

## 1. スプレッドシート作成（5 分）

`shared/invoices.template.csv` と `shared/transactions.template.csv` から、1 冊のスプレッドシートに `invoices` と `transactions` の 2 シートを作ります（詳細は `shared/sheets-schema.md`）。

1. Google ドライブで **スプレッドシートを新規作成** します。名前は自由です（例：`payment-ops`）。
2. メニュー **ファイル → インポート → アップロード** で `shared/invoices.template.csv` を選びます。
3. インポート設定を次のようにします。
   - インポート場所：**新しいシートを挿入する**
   - 区切り文字の種類：**自動的に検出する**
   - **「テキストを数値、日付、数式に変換する」のチェックを外す**
4. 追加されたシートのタブ名を **`invoices`** に変更します（半角小文字、空白なし）。
5. 同じ手順で `shared/transactions.template.csv` を取り込み、タブ名を **`transactions`** にします。
6. 各シートで **全選択（Ctrl+A）→ 表示形式 → 数字 → 書式なしテキスト** を設定します（Google 側の自動書式で `2026-09-10` が `2026/09/10` に変わるのを防ぐため。テンプレは数値も日付も文字列として読み書きします）。
7. **1 行目（列名）は変更・削除・並び替えをしないでください。** 列名が 1 文字でも違うと動きません。右側に独自の列を追加するのは構いません。
8. サンプル行（2〜4 行目）はそのまま残しておき、§7 の動作確認のあとで削除します。
9. ブラウザーのアドレスバー `https://docs.google.com/spreadsheets/d/<ここが ID>/edit` の **ID** をメモします。§5 で `Config` の `SHEET_ID` に貼ります。
10. 監視フォルダを作ります。Google ドライブで **新規 → 新しいフォルダ** を作成し（例：`bank-csv`）、開いたときの URL `https://drive.google.com/drive/folders/<ここが ID>` の **ID** をメモします。§5・§6 で使います。
11. Google ドライブの設定（`drive.google.com/drive/settings`）で **「アップロードしたファイルを Google ドキュメント エディタ形式に変換する」のチェックを外します。** ON のままだと CSV がスプレッドシートに変換され、Shift_JIS の名義が壊れることがあります（Google ドライブ ヘルプ「ファイルをアップロードする」参照）。

`invoices` の列で最初に埋めるべきもの：

| 列 | 内容 |
|---|---|
| `invoice_id` | 請求番号（一意） |
| `customer_name` | 請求先名（漢字可） |
| `payer_name_alias` | **振込名義（カナ）をカンマ区切りで。** 銀行の振込名義はカタカナで届くため、漢字の `customer_name` だけでは一致しません。ここが空だと自動消込率が大きく落ちます（§8） |
| `amount` | 税込請求額（円、整数） |
| `currency` | `JPY` |
| `due_date` | `yyyy-MM-dd` |
| `status` | `unpaid` |
| `paid_amount` | `0` |

---

## 2. Google 側の準備（10 分）

このテンプレは Google の 3 サービスを使います。n8n の Credential は **サービスごとに 1 つ**、最大 3 つ作ります（**Gmail OAuth2 API** は入金通知メールの取込かメール通知を使う場合のみ。使わない場合は §6.4 のとおり `Watch Gmail Inbox` と `Notify Email` を無効化します）。

| n8n の Credential 種別（画面表記） | 使うノード |
|---|---|
| **Google Drive OAuth2 API** | `Watch Drive Folder`、`Download File` |
| **Google Sheets OAuth2 API** | `Read Invoices`、`Read Transactions`、`Update Invoices`、`Upsert Transactions` |
| **Gmail OAuth2 API** | `Watch Gmail Inbox`、`Notify Email`（Error Handler の `Notify Email` も同じ） |

手順は n8n 公式「Google OAuth2 single service」に従います（参考 [1]）。以下はその要約です。

### 2.1 Google Cloud プロジェクトの作成
1. [Google Cloud Console](https://console.cloud.google.com) に Google アカウントでログインします。
2. 上部のプロジェクト選択から **New project**（新しいプロジェクト）を選びます。
3. **Project name**（プロジェクト名）を入力し、**Create**（作成）を押します。
4. 上部のプロジェクト選択が作成したプロジェクトになっていることを確認します。

### 2.2 API の有効化
1. 左メニュー **APIs & Services > Library**（API とサービス > ライブラリ）を開きます。
2. 次の 3 つを検索し、それぞれ **ENABLE**（有効にする）を押します。
   - **Google Sheets API**
   - **Google Drive API**（Google Sheets ノードにも必要と公式ドキュメントに明記されています）
   - **Gmail API**（Gmail の Credential を作る場合）
3. Google Calendar API は本テンプレでは不要です。

### 2.3 OAuth 同意画面
1. **APIs & Services > OAuth consent screen**（OAuth 同意画面）を開きます。Google Auth Platform の Overview に移動します。
2. **Get started** を押します。
3. **App name**（アプリ名。例：`n8n`）と **User support email** を入力し **Next**。
4. **Audience**（対象ユーザー）は、Google Workspace 組織内で使うなら **Internal**、個人の Gmail アカウントなら **External** を選び **Next**。
5. 連絡先メールを入力し **Next** → ポリシーに同意して **Continue** → **Create**。
6. 左メニュー **Branding** を開き、**Authorized domains** で **Add domain**：
   - n8n Cloud の場合：`n8n.cloud`
   - セルフホストの場合：自分の n8n のドメイン
7. **Save** を押します。
8. **External** を選んだ場合、アプリは **Testing**（テスト）状態です。左メニュー **Audience** の **Test users** に、n8n で接続する Google アカウントのメールアドレスを追加します。追加しないと接続時に「アクセスをブロック」されます。
   - 注意：**Testing かつ External** のアプリは、公式ドキュメントによると **同意とトークンが 7 日で失効** します。失効したら n8n の Credential 画面で再接続してください。長期運用では Google 側でアプリを公開（Publishing status を In production に）することを検討してください。

### 2.4 OAuth クライアントの作成（Google 側）と n8n Credential の作成
Credential 1 つにつき、次の手順を繰り返します（最大 3 回）。**Google 側の OAuth クライアントは 1 つを 3 つの Credential で使い回して構いません**（Client ID と Client Secret は同じ、Redirect URI は 1 つ）。

**n8n Cloud の場合**：Google Drive／Google Sheets／Gmail（Trigger 含む）は **Managed OAuth2** に対応しており、Credential 画面の **Sign in with Google** だけで接続できます（Google Cloud Console の作業は不要）。公式ドキュメントにこの一覧があります（参考 [1]）。この場合は §2.1〜2.3 を飛ばせます。

1. n8n の左メニュー **Create**（作成ボタン）→ **Credential** を選びます。
2. 検索欄に `Google Sheets` と入力し **Google Sheets OAuth2 API** を選びます（2 回目は **Google Drive OAuth2 API**、3 回目は **Gmail OAuth2 API**）。
3. Credential 画面に表示される **OAuth Redirect URL** をコピーします（セルフホストのローカル環境なら `http://localhost:5678/rest/oauth2-credential/callback` のような形）。
4. Google Cloud Console の **APIs & Services > Credentials**（認証情報）で **+ Create credentials > OAuth client ID** を選びます。
5. **Application type** は **Web application**。
6. **Name** を分かる名前に変え、**Authorized redirect URIs** に手順 3 の URL を **プロトコルとポート番号まで一字違わず** 貼り、**Create**。
7. 表示された **Client ID** と **Client Secret** を n8n の Credential 画面の同名欄に貼ります（前後の空白に注意）。
8. **Sign in with Google** を押し、手順 2.3 で登録した Google アカウントで許可します。
9. Credential 名を分かる名前に変えて **Save**。名前は自由です（例：`Google Sheets (payment-ops)`）。ワークフローは Credential を**名前ではなく、§4.3 で各ノードに割り当てたもの**で参照します。
10. スコープ（権限）は n8n の Credential が既定で設定します。**Custom Scopes** は OFF のままにします（ON にすると Scope 欄と注意書き「The default scopes needed for the node to work are already set」が現れますが、既定のスコープで十分です）。
11. 2 回目・3 回目は手順 1〜2 と 7〜9 だけで済みます（OAuth クライアントは同じものを使う）。
12. Google Sheets Credential に使った Google アカウントに、§1 のスプレッドシートの **編集権限** があることを確認します（自分で作ったなら不要）。

---

## 3. 通知先の準備（使うものだけ、各 3〜10 分）

通知は `Config` の `NOTIFY_CHANNELS` で選びます（既定 `["slack"]`）。使わないチャネルの準備は不要です。**トークン類は Config に書かず、必ず n8n の Credential に入れます。**

### 3.1 Slack（5 分）
`Notify Slack` ノードは **Access Token**（Bot User OAuth Token）方式で組んであります。n8n 公式「Slack credentials」の手順に従います（参考 [4]）。

1. [Slack API Apps](https://api.slack.com/apps) を開き **Create New App > From a manifest** を選びます。
2. 投稿先のワークスペースを選び **Next**。
3. **JSON** タブを選び、既定のマニフェストを n8n 公式ページ掲載の「API access token 用マニフェスト」に置き換えます。最低限必要なスコープは `chat:write` です（公式マニフェストは他のスコープも含みます。減らしても構いません）。
4. **Next** → 内容を確認して **Create**。
5. 左メニュー **OAuth & Permissions** → **OAuth Tokens** の **Install to Workspace** → **Allow**（ワークスペース管理者権限が必要）。
6. 表示された **Bot User OAuth Token**（先頭が `xoxb` で始まるトークン）をコピーします。
7. n8n で **Create → Credential** → `Slack` を検索 → **Slack API** を選び、**Access Token** に貼って **Save**。Credential 名は自由です。
8. **Token rotation（トークンローテーション）は OFF のままにします。** ON だと 12 時間で失効し n8n から使えなくなり、あとから OFF に戻せません（公式ドキュメント「Common issues」）。
9. 投稿先のチャンネルを決め、**そのチャンネルにアプリ（ボット）を追加します。** Slack API の仕様上、アプリがチャンネルのメンバーでないと投稿が `not_in_channel` で失敗します（参考 [5]）。チャンネルへのアプリ追加手順を記載した Slack ヘルプページは本書作成時に取得できなかったため、Slack のヘルプセンターで「チャンネルにアプリを追加」を参照してください。
10. `Config` の `SLACK_CHANNEL` に入れる値をメモします。`#チャンネル名`（例：`#入金消込`）でも、チャンネル ID（`C` で始まる文字列）でも構いません。チャンネル ID は、ブラウザーでそのチャンネルを開いたときの URL `https://app.slack.com/client/T…/C…` の `C…` の部分です（参考 [6]）。

### 3.2 メール通知（0 分）
`Notify Email` は §2 で作った **Gmail OAuth2 API** の Credential をそのまま使います。宛先は `Config` の `NOTIFY_EMAIL_TO` です。

### 3.3 LINE（10 分）
`Notify LINE` は HTTP Request ノードで LINE Messaging API の push（`POST https://api.line.me/v2/bot/message/push`）を呼びます。認証は **Header Auth** Credential です。LINE Notify は 2025 年 3 月に終了しているため使いません。

1. Messaging API チャネルを用意します。2024 年 9 月 4 日以降、LINE Developers Console から直接は作成できず、**LINE 公式アカウントを作成 → LINE Official Account Manager で Messaging API を有効化 → LINE Developers Console にログイン** の順になります（参考 [7]）。
2. LINE Developers Console で該当チャネルを開き、チャネルアクセストークンを発行します。公式ドキュメントは有効期限を指定する **Channel access token v2.1（最長 30 日）** を推奨しています。無人運用で更新の手間を避けたい場合は **Long-lived channel access token（無期限、Messaging API チャネルのみ）** を使えます。どちらを使うかは自分で決め、失効時は再発行して Credential を更新してください（参考 [8][9]）。
3. 通知の宛先となる自分の userId（`U` の後に 16 進数 32 文字が続く文字列。形式 `U[0-9a-f]{32}`）を、チャネルの **Basic settings** タブの **Your user ID** で確認します。表示されない場合は Business ID と LINE アカウントの連携が必要です（参考 [10]）。
4. LINE アプリで、その公式アカウントを **友だち追加** しておきます（参考 [9]）。
5. n8n で **Create → Credential** → `Header Auth` を検索 → **Header Auth** を選びます。
6. **Name**（ヘッダ名）に `Authorization`、**Value** に `Bearer` ＋ 半角スペース 1 つ ＋ チャネルアクセストークン を 1 つの文字列として入れます（`Bearer` の直後に半角スペースが 1 つだけあること。トークンをそのまま貼るだけでは認証されません）。
7. Credential 名を **`LINE Messaging API`** にして **Save**。
8. `Config` の `LINE_TO_USER_ID` に手順 3 の userId を入れます（§5）。

### 3.4 Chatwork（5 分）
`Notify Chatwork` は HTTP Request ノードで `POST https://api.chatwork.com/v2/rooms/{room_id}/messages` を呼びます。認証はヘッダ `X-ChatWorkToken` の **Header Auth** Credential です（参考 [11][12]）。

1. Chatwork の画面右上の **利用者名 → サービス連携 → API トークン** で API トークンを発行します。パーソナルプラン以外では **組織管理者への利用申請** が必要です（参考 [11]）。
2. 投稿先のルーム ID（数字）を確認します。ルーム ID の確認方法を記載した Chatwork ヘルプページは本書作成時に取得できませんでした。公式 API リファレンスの `GET https://api.chatwork.com/v2/rooms`（チャット一覧を取得する）は各ルームの `room_id` を返すので、これを使って確認できます（参考 [13]）。
3. n8n で **Create → Credential** → **Header Auth** を選びます。
4. **Name** に `X-ChatWorkToken`、**Value** に API トークンを入れます。
5. Credential 名を **`Chatwork API`** にして **Save**。
6. `Config` の `CHATWORK_ROOM_ID` にルーム ID を入れます（§5）。

---

## 4. ワークフローの取込（5 分）

### 4.1 取込の順序
Error Handler を先に取り込みます（本体の Settings で選択するため）。n8n 公式「Export and import」の **Import from File** を使います（参考 [14]）。

1. n8n の左メニュー **Create → Workflow** で空のワークフローを開きます。
2. 右上の **三点メニュー（…）→ Import from File** を選び、`error-handler.json` を選びます。
3. ワークフロー名が `[Odaji] 01 Error Handler v1.0.0` になっていることを確認します。**この名前は変えないでください。**
4. もう一度 **Create → Workflow** で空のワークフローを開き、同じ操作で `workflow.json` を取り込みます。名前は `[Odaji] 01 Bank Deposit Reconciliation v1.0.0` です。
5. 2.x では編集内容は自動保存されます。1.x の場合は **Save** を押します。

### 4.2 取込直後の確認
1. キャンバスに 30 ノードと付箋（Sticky Note）8 枚（Error Handler は 11 ノードと付箋 4 枚）が表示され、**赤い（エラー表示の）ノードが無い** ことを確認します。「Unknown node」「Node type not found」が出た場合は n8n のバージョンが古いか、組み込みノードが無効化されています。
2. Credential 未設定のノードには警告アイコンが出ます。これは §4.3 で解消します。
3. 付箋の内容は日本語（`## JA`）→ 英語（`## EN`）の順で、本書と同じ内容の要約です。

### 4.3 Credential を各ノードで選ぶ
ノードをダブルクリックして開き、上部の Credential 欄で選びます。**次のすべてのノードで選択が必要です。**

本体 `[Odaji] 01 Bank Deposit Reconciliation v1.0.0`：

| ノード名 | 選ぶ Credential | 備考 |
|---|---|---|
| `Watch Drive Folder` | Google Drive OAuth2 API | |
| `Watch Gmail Inbox` | Gmail OAuth2 API | |
| `Download File` | Google Drive OAuth2 API | |
| `Read Invoices` | Google Sheets OAuth2 API | |
| `Read Transactions` | Google Sheets OAuth2 API | |
| `Update Invoices` | Google Sheets OAuth2 API | |
| `Upsert Transactions` | Google Sheets OAuth2 API | |
| `Notify Slack` | Slack API（Access Token） | `NOTIFY_CHANNELS` に `slack` を入れる場合 |
| `Notify Email` | Gmail OAuth2 API | `email` を入れる場合 |
| `Notify LINE` | Header Auth `LINE Messaging API` | `line` を入れる場合。Authentication は **Generic Credential Type → Header Auth** のまま |
| `Notify Chatwork` | Header Auth `Chatwork API` | `chatwork` を入れる場合。同上 |

Error Handler `[Odaji] 01 Error Handler v1.0.0`：

| ノード名 | 選ぶ Credential |
|---|---|
| `Notify Slack` | Slack API（本体と同じ） |
| `Notify Email` | Gmail OAuth2 API（本体と同じ） |
| `Notify LINE` | Header Auth `LINE Messaging API` |
| `Notify Chatwork` | Header Auth `Chatwork API` |

- **使わないチャネルの `Notify …` ノードは、本体・Error Handler の両方で無効化します**（ノードを右クリック → **Deactivate**。無効化したノードは灰色になります）。n8n は Publish（有効化）のときに有効な全ノードの Credential を検証するため、Credential 未設定のノードが 1 つでも有効のままだと **`Cannot publish workflow: … Missing required credential: slackApi`（または `gmailOAuth2`）** で Publish できません（作者の n8n 2.40.5 で確認）。無効化したノードは検証されません。
- 無効化したチャネルは `NOTIFY_CHANNELS`（§5）にも入れないでください。無効化したノードは入力をそのまま次へ通すため、`NOTIFY_CHANNELS` に残すと `Check Notification Results` がそのチャネルを「失敗」（`errors` に `notify node disabled or not executed (payload passed through)`）として数えます。それが唯一のチャネルだと実行は `All notification channels failed (1): …` で失敗します。通知が黙って届かない状態にはなりません。
- `Notify LINE`／`Notify Chatwork`（HTTP Request）は Credential 未設定のまま実行されると「Node does not have any credentials set」で失敗します。使うチャネルでは必ず Header Auth Credential を選んでください。
- `Notify Slack` の Authentication を OAuth2 に変えることもできますが、その場合は Slack OAuth2 API の Credential を別途作り直す必要があります。本書は Access Token 方式で説明しています。

### 4.4 ワークフロー Settings
本体ワークフローで設定します（参考 [15][16]）。

1. 右上の **三点メニュー（…）→ Settings** を開きます。
2. **Error Workflow (to notify when this one errors)** で **`[Odaji] 01 Error Handler v1.0.0`** を選びます。
3. **Timezone** が **Asia/Tokyo** になっていることを確認します（`workflow.json` に含めてあります。違っていれば選び直します）。
4. **Save** を押します。
5. Error Handler 側の Settings の Error Workflow は **空のまま** にします（無限ループ防止）。
6. **Error Handler を Publish します**（Error Handler を開き、§4.3 で Credential を選ぶか使わないチャネルのノードを無効化し、§5.3 の Error Handler `Config` も編集したあと、右上の **Publish** → ダイアログ内の **Publish**。§7.2 手順 2 参照）。作者の n8n 2.40.5 では、**Publish されていない Error Workflow は本体が失敗しても呼び出されません**（n8n のログに `Calling Error Workflow for "…". Workflow "…" is not active and cannot be executed` と出るだけです）。公式ドキュメント（参考 [20]）は公開不要としていますが、実測では必要でした。Publish が `Missing required credential` で拒否される場合は §4.3 の無効化を見直します。

---

## 5. `Config` の編集（3〜5 分）

本体の `Config` ノード（Edit Fields (Set)、Mode: JSON）を開き、JSON を直接編集します。**`REPLACE_ME_` で始まる値と `replace-me@example.com` をすべて置き換えてください。** JSON の構文（引用符・カンマ）を崩さないよう注意します。

JSON 欄は **Expression** モードのまま編集します（末尾の `SOURCE` に `{{ $prevNode.name }}` が入っているため）。**Fixed に切り替えないでください**（切り替えると `SOURCE` が文字列になり、`Route by Source` が正しく分岐しません）。JSON は約 160 行あります。`SHEET_ID` と `DRIVE_FOLDER_ID` は先頭付近、`SLACK_CHANNEL`／`NOTIFY_EMAIL_TO`／`LINE_TO_USER_ID`／`CHATWORK_ROOM_ID` は `NOTIFY_CHANNELS` の直後にあります。

| キー | 必須 | 既定値 | 入れるもの |
|---|---|---|---|
| `TZ` | — | `"Asia/Tokyo"` | 日付判定のタイムゾーン。ワークフロー Settings の Timezone と同じにする |
| `LANG` | — | `"ja"` | 通知文面の言語。`ja` または `en` |
| `SHEET_ID` | **必須** | `"REPLACE_ME_SHEET_ID"` | §1 手順 9 のスプレッドシート ID |
| `SHEET_INVOICES` | — | `"invoices"` | 請求一覧のシート名。タブ名を変えていなければそのまま |
| `SHEET_TRANSACTIONS` | — | `"transactions"` | 取引台帳のシート名 |
| `DRIVE_FOLDER_ID` | **必須** | `"REPLACE_ME_DRIVE_FOLDER_ID"` | §1 手順 10 の監視フォルダ ID。**参照用。実際に効くのは `Watch Drive Folder` ノードの値（§6）**。同じ値にする |
| `GMAIL_QUERY` | — | `"subject:(入金 OR Deposit) newer_than:1d"` | Gmail 検索式。**参照用。実際に効くのは `Watch Gmail Inbox` の Search（§6）**。同じ値にする |
| `RUN_AT` | — | `"09:00"` | 毎日の再突合時刻（JST）。**参照用。実際に効くのは `Run Daily Rematch`（§6）** |
| `TRIGGERS_ENABLED.drive` | — | `true` | 監視フォルダの CSV 取込を使うか |
| `TRIGGERS_ENABLED.gmail` | — | `true` | 入金通知メールの取込を使うか。使わないなら `false` |
| `TRIGGERS_ENABLED.schedule` | — | `true` | 毎日の再突合を使うか |
| `CSV_MAPPING.date_col` | 銀行 CSV を使うなら必須 | `"日付"` | 取引日の列見出し（CSV の 1 行目の文字列と完全一致） |
| `CSV_MAPPING.payer_col` | 同上 | `"摘要"` | 振込名義（摘要）の列見出し |
| `CSV_MAPPING.deposit_col` | 同上 | `"入金額"` | 入金額の列見出し。空または 0 の行（出金行）は無視 |
| `CSV_MAPPING.withdraw_col` | — | `"出金額"` | 出金額の列見出し（説明用。無ければ `""`） |
| `CSV_MAPPING.memo_col` | — | `""` | 摘要とは別にメモ列があるときだけ |
| `CSV_MAPPING.skip_rows` | — | `0` | 見出し行より前に捨てる行数（説明行がある CSV は `1` など） |
| `CSV_MAPPING.date_format` | — | `"auto"` | `auto` / `yyyy/MM/dd` / `yyyyMMdd` / `yyyy-MM-dd` |
| `CSV_MAPPING.encoding` | — | `"shift_jis"` | `shift_jis` / `utf-8` / `auto`。UTF-8 BOM 付きファイルは設定に関わらず UTF-8 として読む |
| `MAIL_PARSERS` | メール取込を使うなら必須 | 2 件（bankX / bankY） | 入金通知メールの解析ルール（下記 5.2） |
| `LEGAL_ENTITY_TOKENS` | — | `["カ)", "(カ", …, "株式会社", …]` | 名義から除去する法人格等。追加は全角でも可 |
| `STRIP_LEADING_DIGITS` | — | `true` | 名義先頭の数字列（振込人番号・支店コード）を除去 |
| `FEE_SET` | — | `[110,165,220,275,330,440,550,660,770,880]` | 先方負担の振込手数料として許容する差額（円） |
| `NAME_MIN_CONTAINS` | — | `3` | 名義の包含一致に必要な最小文字数 |
| `NOTIFY_CHANNELS` | — | `["slack"]` | `slack` / `email` / `line` / `chatwork` の組合せ（配列）。空 `[]` なら通知しない |
| `SLACK_CHANNEL` | `slack` を使うなら必須 | `"REPLACE_ME_SLACK_CHANNEL_ID"` | `#チャンネル名` または `C…` の ID（§3.1） |
| `NOTIFY_EMAIL_TO` | `email` を使うなら必須 | `"replace-me@example.com"` | 通知メールの宛先 |
| `LINE_TO_USER_ID` | `line` を使うなら必須 | `"REPLACE_ME_LINE_USER_ID"` | LINE の userId（§3.3） |
| `CHATWORK_ROOM_ID` | `chatwork` を使うなら必須 | `"REPLACE_ME_CHATWORK_ROOM_ID"` | Chatwork のルーム ID（§3.4） |
| `LINE_API_URL` | — | `"https://api.line.me/v2/bot/message/push"` | LINE push の URL。**変更しない**（プロキシ経由にする場合のみ） |
| `CHATWORK_API_BASE_URL` | — | `"https://api.chatwork.com/v2"` | Chatwork API のベース URL。**変更しない** |
| `NOTIFY_MAX_LINES` | — | `40` | 通知の各セクションに載せる明細の上限行数。超過分は「…他 N 件」 |
| `MESSAGES` | — | `shared/messages.ja.json` / `messages.en.json` の内容 | 通知文面（`ja` / `en`）。文言を変えたいときだけ編集 |
| `SOURCE` | — | `{{ $prevNode.name }}` | 自動設定。**変更しない** |

使わない通知先の `REPLACE_ME_…` は残っていても動作に影響しません（そのチャネルは実行されません）。ただし混乱を避けるため、空文字 `""` にしておくことを勧めます。

### 5.1 `CSV_MAPPING` の合わせ方
1. 銀行からダウンロードした CSV をテキストエディタで開き、**1 行目の列見出し**を確認します。
2. `date_col` / `payer_col` / `deposit_col` にその見出しを**そのまま**書きます。
3. 見出しの前に説明行があれば、その行数を `skip_rows` に入れます。
4. 日付が `20260917` 形式なら `date_format` を `"yyyyMMdd"` にします（`auto` でも読めますが明示すると安全です）。
5. 文字コードが UTF-8（BOM なし）なら `encoding` を `"utf-8"` にします。
6. 例は `fixtures/csv_mapping.examples.json` にあります。`bank_A_sjis.csv`（`日付,摘要,入金額,出金額,残高`、Shift_JIS）は既定値そのまま、`bank_B_utf8bom.csv`（`取引日,内容,お預入,お引出`、UTF-8 BOM、`yyyyMMdd`）は次の値です。

```json
"CSV_MAPPING": {
  "date_col": "取引日", "payer_col": "内容", "deposit_col": "お預入", "withdraw_col": "お引出",
  "memo_col": "", "skip_rows": 0, "date_format": "yyyyMMdd", "encoding": "utf-8"
}
```

### 5.2 `MAIL_PARSERS` の合わせ方
`MAIL_PARSERS` は配列で、先頭から順に試し**最初に一致したルール**を使います。正本の例は `fixtures/mail_parsers.example.json`（同梱の架空メール `mail_bankX.eml`／`mail_bankY.eml` に対応）です。

| 項目 | 意味 |
|---|---|
| `name` | 通知に出す識別名 |
| `from_match` | 差出人に含まれる文字列（大文字小文字無視の部分一致）。例：`"@example.jp"` |
| `subject_match` | 件名に含まれる文字列。例：`"入金"` |
| `amount_regex` | 本文に対する正規表現。**1 つ目のかっこ `( )` が金額** |
| `payer_regex` | 同じく 1 つ目のかっこが振込名義 |
| `date_regex` | 同じく 1 つ目のかっこが日付。無ければメールの受信日を使う |

正規表現の調整手順：
1. 自行の入金通知メールを 1 通開き、金額・名義・日付が書かれている行を確認します。
2. 本文は解析前に **NFKC 正規化**されます（全角英数字→半角、全角コロン `：` も `:` として扱えるよう、既定の正規表現は `[：:]` を使っています）。
3. ラベル付き 1 行形式（`入金額：33,000円`）なら bankX の形 `(?:入金額|お振込金額|金額)[：:]\\s*([0-9,]+)` を、ラベル名だけ自行のものに書き換えます。
4. 表形式（`Amount             JPY 19,800`）なら bankY の形 `Amount\\s+(?:JPY|¥)?\\s*([0-9,]+)` を参考にします。
5. JSON の中では `\` を `\\` と 2 つ書きます（`\\s`、`\\d`）。
6. かっこ `( )` は **値を取り出す 1 か所だけ**にし、他のかっこは `(?: )` にします。
7. 名義の正規表現は行末まで取る `([^\\n]+)` が安全です。
8. 一致しないメールは実行を止めず、通知の「警告」に `no_parser_matched`（ルール不一致）または `parser_no_capture`（正規表現が値を取れない）として出ます。これを見て調整します。
9. 正規表現が文法的に誤っている場合は実行が失敗します（Config の誤りを隠さないため）。

### 5.3 Error Handler の `Config`
Error Handler `[Odaji] 01 Error Handler v1.0.0` にも `Config` ノードがあり、通知に必要な 9 キーだけを持ちます：`LANG`、`NOTIFY_CHANNELS`、`SLACK_CHANNEL`、`NOTIFY_EMAIL_TO`、`LINE_TO_USER_ID`、`CHATWORK_ROOM_ID`、`LINE_API_URL`、`CHATWORK_API_BASE_URL`、`MESSAGES`。本体と同じ値を入れ、`REPLACE_ME_…` と `replace-me@example.com` を置き換えます（Error Handler は本体の `Config` を参照できません）。JSON 欄のモードは変えずにそのまま編集します。§4.4 手順 6 の Publish より前に済ませてください。

---

## 6. トリガーノードに入れる値（2 分）

トリガーノードは `Config` より先に動くため、`Config` の値を参照できません。**次の 3 ノードには実値を直接入れます。** `Config` の `DRIVE_FOLDER_ID` / `GMAIL_QUERY` / `RUN_AT` は「何を設定したか」の記録用なので、同じ値にしておきます。

### 6.1 `Watch Drive Folder`（Google Drive Trigger）
1. ノードを開きます。
2. **Trigger On** は「特定のフォルダ」（`Changes Involving a Specific Folder`）のままにします。
3. **Folder** 欄左側のモードが **ID** になっていることを確認し（取込直後は ID）、値 `REPLACE_ME_DRIVE_FOLDER_ID` を §1 手順 10 のフォルダ ID に置き換えます（**Link** に切り替えてフォルダの URL を貼っても構いません。**Folder** はリストから選ぶモードで、Credential 接続後に使えます）。
4. **Watch For** は `File Created` のまま。ポーリングは毎分（`Poll Times: Every Minute`）のままで構いません。

### 6.2 `Watch Gmail Inbox`（Gmail Trigger）
1. ノードを開きます。
2. **Simplify** は **OFF のまま**にします（本文が必要なため。ON にすると本文が取れず解析できません）。
3. **Filters → Search** に検索式を入れます。既定は `subject:(入金 OR Deposit) newer_than:1d` で、同梱サンプル 2 通の件名に一致します。自行の通知に合わせて `subject:` の語や `from:` を変えます。Gmail の `subject:` は本文を検索しません（参考 [17]）。
4. **Read Status** は `Unread and read emails`、**Max Emails per Poll** は `10`、ポーリングは 5 分ごとのままで構いません。
5. `Config` の `GMAIL_QUERY` を同じ値にします。

### 6.3 `Run Daily Rematch`（Schedule Trigger）
1. ノードを開きます。
2. **Trigger Interval** `Days`、**Days Between Triggers** `1`、**Trigger at Hour** `9am`、**Trigger at Minute** `0` が既定です。変える場合は `Config` の `RUN_AT` も同じ値にします。
3. 時刻はワークフロー Settings の Timezone（Asia/Tokyo）で解釈されます（参考 [18]）。

### 6.4 使わない系統の止め方
- `Config` の `TRIGGERS_ENABLED` を `false` にすると、その系統は `Route by Source` で `Skip Disabled Trigger` に落ちて正常終了します。**ただしトリガーノード自体のポーリング（Drive／Gmail API の呼出し）は続きます。**
- API 呼出しも止めたいときは、そのトリガーノードを無効化します（ノードのメニューの **Deactivate**）。無効化したノードは `Publish` 後も動きません。
- Gmail を使わない場合（入金通知メールもメール通知も使わない）は、`TRIGGERS_ENABLED.gmail` を `false` にしたうえで、`Watch Gmail Inbox` と `Notify Email`（本体・Error Handler の両方）を無効化します。Gmail OAuth2 API の Credential を作らずにこれらのノードを有効のまま残すと、Publish が `Missing required credential: gmailOAuth2` で拒否されます（§4.3）。
- トリガーノードの**名前は変えないでください**。`Route by Source` がノード名（`Watch Drive Folder` / `Watch Gmail Inbox` / `Run Daily Rematch`）で分岐しています。

---

## 7. 動作確認（5 分）

同梱の架空データで、取込 → 突合 → シート更新 → 通知の一連を確認します。**本番の請求データを入れる前に行ってください。**

### 7.1 シートに試運転データを入れる
1. `invoices` シートのサンプル行（2〜4 行目）を削除し、`fixtures/invoices.seed.csv` の 20 行をインポートします（§1 と同じ手順で **現在のシートに追加する** か、内容をコピーして 2 行目から貼り付け）。1 行目の列名は同じなので、貼り付ける場合は見出し行を含めないでください。
2. `transactions` シートも同様にサンプル行を消し、`fixtures/transactions.seed.csv` の 1 行を入れます。
3. 貼り付け後も列が「書式なしテキスト」のままであることを確認します。

### 7.2 CSV を監視フォルダに置く
1. `Config` の `CSV_MAPPING` が既定値（`日付` / `摘要` / `入金額` / `出金額`、`shift_jis`）であることを確認します。
2. 本体ワークフローを公開します。右上の **Publish**（または Shift+P）を押すと公開ダイアログが開きます（Version name は既定で UUID。変更不要）。ダイアログ内の **Publish** を押して公開します。公開しないとトリガーは動きません（参考 [19]）。
3. `fixtures/bank_A_sjis.csv` を §1 手順 10 の監視フォルダにアップロードします（ドライブの「変換」設定が OFF であることを再確認）。
4. 1〜2 分待ち、ワークフローの **Executions** タブで実行が 1 件増え、ステータスが成功（緑）になっていることを確認します。
   - 補足：Google Drive Trigger を **Execute workflow** で手動実行すると、条件に合う直近のイベントを 1 件返します。該当が無い場合はエラーになります（公式ドキュメントの注記）。手動で確認したい場合はファイルを置いたあとに実行してください。

### 7.3 期待される結果
通知（`LANG=ja`）は次の内容になります（日付は実行日。`tests/CASES.md` §3 より）。

```
【入金消込 2026-09-23】処理 11件｜自動消込 4｜要確認 3｜未消込 4

■ 要確認（金額のみ一致・手数料差引・合算で自動消込した分）
・2026-09-02 振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ ¥54,780 → INV-2026-002 （手数料 ¥220 差引）
・2026-09-04 振込 ｻﾄｳ ｹｲｺ ¥128,000 → INV-2026-004 （金額のみ一致・要確認）
・2026-09-05 振込 ｶ)ﾃｽﾄﾌﾞﾂｻﾝ ¥1,234,567 → INV-2026-005, INV-2026-006 （合算）

■ 候補複数（自動確定せず。候補から選んでください）
・2026-09-09 振込 ｵｵﾊﾞ ﾏｻｵ ¥44,000 → 候補: INV-2026-008(¥44,000), INV-2026-009(¥44,000)

■ 未消込（該当請求なし）
・2026-09-11 振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ ¥66,000 → 候補: INV-2026-015(¥57,200), INV-2026-017(¥49,500)
・2026-09-12 振込 ﾃｽﾄｹﾝｾﾂ(ｶ ¥88,000 → 候補: —
・2026-09-15 振込 ﾅｶﾑﾗ ｼﾞﾛｳ ¥5,500 → 候補: INV-2026-014(¥15,400)

■ 自動消込
・2026-09-01 振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ ¥33,000 → INV-2026-001
・2026-09-03 フリコミ　ヤマダ　タロウ ¥9,800 → INV-2026-003
・2026-09-08 振込 ｻﾝﾌﾟﾙｼｽﾃﾑ(ｶ ¥100,000 → INV-2026-007 （一部入金・残 ¥150,000）
・2026-09-14 振込 ｶ)ｻﾝﾌﾟﾙﾌｰｽﾞﾄｳｷﾖｳ ¥27,500 → INV-2026-012
```

`invoices` シートの変化（`fixtures/README.md` §2 より）：

| invoice_id | status | match_confidence | paid_amount | fee_deducted |
|---|---|---|---|---|
| INV-2026-001 | paid | auto | 33000 | 0 |
| INV-2026-002 | paid | fee_deducted | 54780 | 220 |
| INV-2026-003 | paid | auto | 9800 | 0 |
| INV-2026-004 | paid | amount_only | 128000 | 0 |
| INV-2026-005 / 006 | paid | combined | 700000 / 534567 | 0 |
| INV-2026-007 | partial | auto | 100000 | 0 |
| INV-2026-012 | paid | auto | 27500 | 0 |
| INV-2026-008 / 009（同額 2 件） | unpaid のまま | — | 0 | — |

`transactions` シートには 11 行が追加されます（出金行 4 件は無視）。`status` は `matched` / `unmatched` / `ambiguous` のいずれかです。

### 7.4 冪等性の確認（任意）
同じ `bank_A_sjis.csv` をもう一度（別名でも可）監視フォルダに置くと、通知は `【入金消込 …】新規の入金はありませんでした（処理済みのため skip：11 件）` となり、シートは変わりません。

### 7.5 メール経路の確認（任意）
`fixtures/mail_bankX.eml` / `mail_bankY.eml` を自分の Gmail 宛てに送る（メールソフトで .eml を開いて転送するなど）と、`Watch Gmail Inbox` の Search に一致した場合に `INV-2026-018`（104,500 円）と `INV-2026-019`（19,800 円）が `paid` になります。差出人が `example.jp` / `example.com` ではないため、確認時は `MAIL_PARSERS` の `from_match` を自分の送信元に一時的に変えてください。

### 7.6 試運転データの削除
1. `invoices` シートから `INV-2026-001`〜`INV-2026-020` の行を**すべて削除**します。
2. `transactions` シートから試運転で追加された行（seed の 1 行を含む）を**すべて削除**します。残っていると、同じ `txn_id` の本番入金が「処理済み」として skip されることはありませんが、台帳に架空データが混ざります。
3. Error Handler の動作確認は手動ではできません（Error Trigger は自動実行の失敗時にだけ発火します。参考 [20]）。§8 で公開したあと、`Check Notification Results` が全チャネル失敗時に実行を失敗させる設計になっているため、通知先を一時的に誤った値にして確認できます。

---

## 8. 本番化（3 分）

1. `invoices` シートに本番の請求を入れます。**`payer_name_alias` を必ず埋めてください。** 振込名義はカタカナ（半角カナや `ｶ)` などの法人格略記を含む）で届きます。過去の通帳から実際の振込名義を写し、複数ある場合はカンマ区切りで入れます（例：`カ)サンプルシヨウジ,サンプルシヨウジ`）。ここが空だと、名義一致が働かず「金額のみ一致（要確認）」か「未消込」が増えます。
2. `Config` の通知先（`SLACK_CHANNEL` / `NOTIFY_EMAIL_TO` など）を本番用にし、Error Handler の `Config` にも**同じ通知設定**を入れます（Error Handler は本体の `Config` を参照できません）。
3. 本体ワークフローが **Publish** されていることを確認します（§7.2 で公開済みなら、`Config` を変えたあとに再度 **Publish**（§7.2 手順 2 のダイアログ）が必要です。2.x では編集内容は公開するまで本番に反映されません）。**Error Handler も Publish されていることを確認します**（§4.4 手順 6。Publish されていないと呼び出されません。Error Handler の `Config` を変えたあとも再度 Publish が必要です）。
4. 運用上の注意：
   - **同姓同名**：個人名の名義は同姓同名が起きます。このテンプレが金額一致を必須にしているのはそのためで、名義が違って金額だけ一致した入金は「要確認」として通知に出ます。必ず目視してください。
   - **月をまたいで CSV 形式が変わる**：銀行によっては見出し行の有無や説明行の追加が起きます。「`CSV column not found`」で失敗したら `CSV_MAPPING.skip_rows` と列見出しを見直します（§9）。
   - **曖昧・未消込は人が確定**：`invoices.status` / `paid_amount` / `paid_date` を手で直し、`transactions.status` を `matched`（消込済み）か `ignored`（対象外）にします。`unmatched` / `ambiguous` のままの行は毎朝の再突合で再評価されます。
   - **台帳の大きさ**：`transactions` は毎回全件読みます。1 万行を超えたら年次でシートを分けてください。
5. **個人情報の扱い**：`customer_name` / `customer_email` / `payer_name_alias` は氏名・メールアドレスです。スプレッドシートの共有範囲を最小限にし、不要になった行は削除してください。通知（Slack／メール／LINE／Chatwork）には振込名義と金額が含まれるため、通知先のチャンネルやルームの参加者も必要最小限にします。テンプレは元の銀行 CSV や通知メールをシートに保存せず、Config にもトークンを置きません。n8n の実行ログ（Executions）にはノードの入出力が残るので、ワークフロー Settings の保存設定や保持期間も確認してください。

---

## 9. トラブルシューティング（必要時）

| 症状 | 原因と対処 |
|---|---|
| 名義が文字化けする（`�` や意味不明な文字） | `CSV_MAPPING.encoding` が実際の文字コードと違う。Shift_JIS なら `shift_jis`、UTF-8 なら `utf-8`。Google ドライブの「変換」が ON で CSV がスプレッドシートに変換されている場合は、変換時点で壊れているため設定を OFF にして置き直す（§1 手順 11） |
| 実行が `CSV column not found: "日付"` で失敗する | CSV の見出しと `CSV_MAPPING` の `date_col` / `payer_col` / `deposit_col` が一致していない。エラー文の `header = …` に実際の見出しが出るので、その文字列を入れる。見出しの前に説明行がある場合は `skip_rows` を増やす |
| 実行が `CSV has no header row after skip_rows=…` で失敗する | `skip_rows` が大きすぎる |
| 通知が来ない（実行は成功） | (1) `NOTIFY_CHANNELS` にそのチャネル名（`slack` / `email` / `line` / `chatwork`）が入っているか。(2) そのチャネルの `Notify …` ノードに Credential を選んだか。(3) Executions で該当実行を開き、`Check Notification Results` の出力を見る。`channels_failed` が 1 以上なら `errors` に失敗理由（`not_in_channel`、401 など）が出る。一部のチャネルが失敗しても実行は成功扱いで、シートは更新済み |
| 実行が `All notification channels failed …` で失敗する | 設定した全チャネルが失敗。上と同じ手順で `errors` を確認。シートは通知より先に更新されているので、原因を直したあとの再実行は全件 skip で安全 |
| `Notify LINE` / `Notify Chatwork` が `Node does not have any credentials set` | HTTP Request ノードに Header Auth Credential を選んでいない（§4.3） |
| Slack で `not_in_channel` | ボットが投稿先チャンネルのメンバーではない。チャンネルにアプリを追加する（§3.1） |
| Slack が `invalid_auth` / `token_revoked` | トークンローテーションが ON になっているか、アプリを再インストールした。OFF のアプリを作り直し、Credential を更新する |
| Google ノードが `401 unauthorized_client` | Google Cloud で該当 API（Sheets / Drive / Gmail）が有効化されていない（参考 [21][22]） |
| Google 接続時に「Google hasn't verified this app」「アクセスをブロック」 | 同意画面が External の Testing 状態で、接続するアカウントが Test users に無い（§2.3 手順 8） |
| 数日後に Google ノードが失敗し始めた | External + Testing のアプリは 7 日で失効する。Credential 画面で再接続するか、アプリを公開する（§2.3） |
| `redirect_uri_mismatch` | n8n の OAuth Redirect URL と Google 側の Authorized redirect URIs が一字でも違う（§2.4） |
| `Watch Gmail Inbox` が反応しない | Search の条件に一致していない（`subject:` は本文を見ない）。既読メールも対象にするには Read Status を `Unread and read emails` にする。**Simplify を ON にしていると本文が取れず解析できない** |
| 同じ CSV を 2 回入れたのに二重に消し込まれない（正常） | `txn_id`（日付｜金額｜正規化名義｜正規化メモ）が `transactions` に既にある取引、または請求の `matched_txn_ids` に記録済みの取引は skip する設計。同日・同額・同名義・同メモの実在する 2 重入金は 2 件目が skip されるので、通知の「処理済みのため skip」件数を見て人が `manual` で処理する |
| Error Handler が動かない（本体の実行は失敗している） | (1) **Error Handler 自身が Publish されているか**（§4.4 手順 6。未公開だと n8n のログに `Workflow "…" is not active and cannot be executed` と出て呼び出されない）。(2) 本体の Settings → Error Workflow で選んでいるか。(3) Error Trigger は **公開後の自動実行が失敗したとき**だけ発火し、手動実行では発火しない。(4) 通知ノードの一部失敗は「処理済み」扱いなので発火しない（全チャネル失敗時のみ `Check Notification Results` が失敗させる）。(5) Error Handler の `Config` に通知先を入れたか。(6) Error Handler 側の使うチャネルの `Notify …` に Credential を選んだか |
| Publish が `Cannot publish workflow: … Missing required credential: slackApi` / `gmailOAuth2` などで拒否される（本体・Error Handler とも） | Credential 未設定のノードが有効のまま残っている（`Notify …` ノードのほか、Gmail の Credential を作っていない場合は `Watch Gmail Inbox` も該当）。使わないチャネルのノードを右クリック → **Deactivate** で無効化するか、Credential を選ぶ（§4.3、§6.4）。無効化したチャネルは `NOTIFY_CHANNELS` からも外す |
| `Check Notification Results` の `errors` に `notify node disabled or not executed (payload passed through)` が出る | `NOTIFY_CHANNELS` に入っているチャネルの `Notify …` ノードが無効化されている。そのチャネルを使うならノードを有効化（Activate）して Credential を選ぶ。使わないなら `NOTIFY_CHANNELS` から外す（§4.3） |
| ノードの出力に「This data is pinned」と出る | 開発用に固定された出力が残っている。バナーの **Unpin** を押す。販売物の JSON には固定データを含めていないが、自分で固定した場合は本番実行では無視される（参考 [23]） |
| 請求が突合されず「警告」に `non_jpy_invoice` と出る | `invoices.currency` が `JPY` 以外。JPY のみ対応 |
| 空のシートで止まる | `Read Invoices` / `Read Transactions` は Always Output Data ON で空でも進む設計。止まる場合は列名（1 行目）が無いか変更されている |

---

## 10. チェックリスト（1 分）

導入完了の確認：

- [ ] スプレッドシートに `invoices` / `transactions` があり、列名はテンプレのまま、全セルが「書式なしテキスト」
- [ ] Google ドライブの「アップロードしたファイルを Google ドキュメント エディタ形式に変換する」が OFF
- [ ] Google Cloud で Google Sheets API / Google Drive API / Gmail API を有効化し、同意画面（Test users または公開）と OAuth クライアント（Redirect URI）を設定した
- [ ] n8n に Google Sheets OAuth2 API / Google Drive OAuth2 API / Gmail OAuth2 API の Credential を作り、接続済み（Gmail は使う場合のみ。使わないなら `Watch Gmail Inbox` と `Notify Email` を無効化）
- [ ] 使う通知先の Credential を作った（Slack API、Header Auth `LINE Messaging API`、Header Auth `Chatwork API`）
- [ ] `error-handler.json` → `workflow.json` の順に取り込み、赤いノードが無い
- [ ] 本体の 11 ノード、Error Handler の 4 ノードで Credential を選んだ。使わないチャネルの `Notify …` ノードは本体・Error Handler の両方で無効化（Deactivate）し、`NOTIFY_CHANNELS` からも外した
- [ ] 本体の Settings で Error Workflow に `[Odaji] 01 Error Handler v1.0.0`、Timezone に `Asia/Tokyo`
- [ ] `Config` の `REPLACE_ME_…` と `replace-me@example.com` をすべて置き換えた（本体・Error Handler の両方）
- [ ] `CSV_MAPPING` を自行の CSV の見出しに合わせた／`MAIL_PARSERS` を自行の通知メールに合わせた（使う経路のみ）
- [ ] `Watch Drive Folder` の Folder、`Watch Gmail Inbox` の Search、`Run Daily Rematch` の時刻を入れ、`Config` の `DRIVE_FOLDER_ID` / `GMAIL_QUERY` / `RUN_AT` と揃えた
- [ ] `fixtures/bank_A_sjis.csv` で通知とシート更新を確認し、試運転データを削除した
- [ ] `invoices.payer_name_alias` を本番の請求で埋めた
- [ ] 本体を **Publish** した
- [ ] Error Handler を **Publish** した（Publish されていないと呼び出されない）

---

## 参考 / References

すべて 2026-09-23 に取得・確認。n8n の画面表記（Google Drive Trigger の Folder のモード名 Folder／Link／ID、Google 系 Credential の Custom Scopes、公開ダイアログを含む）はセルフホストの n8n 2.40.5 で確認したものです。

1. n8n Docs — Google OAuth2 single service（Google Cloud プロジェクト・API 有効化・同意画面・OAuth クライアント・Managed OAuth2・トラブルシューティング）: https://docs.n8n.io/integrations/builtin/credentials/google/oauth-single-service.md
2. n8n Docs — Google credentials（Managed OAuth2 対応ノード一覧・OAuth2 と Service Account）: https://docs.n8n.io/integrations/builtin/credentials/google.md
3. n8n Docs — Create and edit credentials（Credential の作成・命名）: https://docs.n8n.io/build/understand-workflows/create-and-edit-credentials.md
4. n8n Docs — Slack credentials（マニフェストからのアプリ作成、Bot User OAuth Token、スコープ、トークンローテーション）: https://docs.n8n.io/integrations/builtin/credentials/slack.md
5. Slack API — chat.postMessage（`not_in_channel`：アプリが会話のメンバーである必要）: https://docs.slack.dev/reference/methods/chat.postMessage
6. Slack Help — Locate your Slack URL or ID（URL 形式 `https://app.slack.com/client/T…/C…`）: https://slack.com/help/articles/221769328
7. LINE Developers — Get started with the Messaging API（チャネル作成は LINE 公式アカウント経由）: https://developers.line.biz/en/docs/messaging-api/getting-started/
8. LINE Developers — Channel access token（種類と有効期限）: https://developers.line.biz/en/docs/basics/channel-access-token/
9. LINE Developers — Build a bot（チャネルアクセストークンの発行、友だち追加）: https://developers.line.biz/en/docs/messaging-api/building-bot/
10. LINE Developers — Get user IDs（Basic settings の Your user ID）: https://developers.line.biz/en/docs/messaging-api/getting-user-ids/
11. Chatwork API — Chatwork API へようこそ（API トークンの発行場所、利用申請）: https://developer.chatwork.com/docs/getting-started
12. Chatwork API — チャットにメッセージを投稿する（`POST /rooms/{room_id}/messages`、ヘッダ `x-chatworktoken`）: https://developer.chatwork.com/reference/post-rooms-room_id-messages
13. Chatwork API — チャット一覧を取得する（`GET /rooms` が `room_id` を返す）: https://developer.chatwork.com/reference/get-rooms
14. n8n Docs — Export and import（三点メニュー → Import from File）: https://docs.n8n.io/build/manage-workflows/export-and-import.md
15. n8n Docs — Configure workflow settings（Error Workflow、Timezone）: https://docs.n8n.io/build/manage-workflows/configure-workflow-settings.md
16. n8n Docs — Handle errors gracefully（Error Workflow の設定手順）: https://docs.n8n.io/build/flow-logic/handle-errors-gracefully.md
17. n8n Docs — Gmail Trigger（Simplify、Search、Read Status、Max Emails per Poll）: https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.gmailtrigger.md ／ Gmail ヘルプ — Gmail で使用できる検索演算子: https://support.google.com/mail/answer/7190?hl=ja
18. n8n Docs — Schedule Trigger（公開が必要、Timezone の扱い、Days 間隔の項目名）: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger.md
19. n8n Docs — Save and publish workflows／Create and run workflows／Types of executions（Publish、手動実行と本番実行の違い）: https://docs.n8n.io/build/understand-workflows/save-and-publish-workflows.md ／ https://docs.n8n.io/build/understand-workflows/create-and-run-workflows.md ／ https://docs.n8n.io/build/understand-workflows/understand-executions/types-of-executions.md
20. n8n Docs — Error Trigger（手動実行では発火しない。ドキュメントは「Error Workflow は公開不要」と読めるが、作者のセルフホスト n8n 2.40.5 では **Publish されていない Error Workflow は呼び出されなかった**ため、本書は Publish を必須としている。§4.4 手順 6）: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.errortrigger.md
21. n8n Docs — Google Drive Trigger と Common issues（手動実行時の挙動、401、複数ファイル）: https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.googledrivetrigger.md ／ https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.googledrivetrigger/common-issues.md
22. n8n Docs — Gmail Trigger Common issues（401）: https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.gmailtrigger/common-issues.md
23. n8n Docs — Pin and mock data（Unpin、本番実行では無視）: https://docs.n8n.io/build/work-with-data/pin-and-mock-data.md
24. n8n Docs — HTTP Request credentials（Header Auth の Name / Value）: https://docs.n8n.io/integrations/builtin/credentials/httprequest.md
25. Google ドライブ ヘルプ — Google ドライブにファイルやフォルダをアップロードする（「アップロードしたファイルを Google ドキュメント エディタ形式に変換する」の設定場所）: https://support.google.com/drive/answer/2424368?hl=ja
26. Google ドキュメント エディタ ヘルプ — スプレッドシートで数値の表示形式を設定する（表示形式 → 数字）: https://support.google.com/docs/answer/56470?hl=ja
27. n8n Docs — Work with nodes（ノードのコンテキストメニューの Deactivate）: https://docs.n8n.io/build/understand-workflows/workflow-components/work-with-nodes.md

取得できなかったページ：Slack ヘルプ「チャンネルにアプリを追加する」、Chatwork ヘルプ「ルーム ID の確認方法」（いずれも本文中に明記し、代替の公式資料を示しています）。LINE／Chatwork の API 仕様（URL・ヘッダ名・本文形式）の確認記録は `ASSUMPTIONS.md` の「外部 API」表にもあります。

本テンプレの設計と判断理由は `DESIGN.md`、受け入れテストは `tests/CASES.md`、同梱データの期待値は `fixtures/README.md` にあります。
