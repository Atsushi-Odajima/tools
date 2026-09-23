# Template 01 Bank Deposit Reconciliation — Setup Guide (SETUP)

Applies to: `[Odaji] 01 Bank Deposit Reconciliation v1.0.0` (`workflow.json`) and `[Odaji] 01 Error Handler v1.0.0` (`error-handler.json`).
The goal of this guide is that someone new to n8n can deploy the template in their own environment in about 30 minutes using nothing but this document. Work through it from top to bottom. Section 2 (Google Cloud) is the one most likely to take longer than planned. If you can use **Sign in with Google** on n8n Cloud, you can skip §2.1–2.3.

| Section | Contents | Time |
|---|---|---|
| 0 | Time required and prerequisites | 2 min |
| 1 | Create the spreadsheet | 5 min |
| 2 | Google setup (Cloud project, OAuth, n8n credentials) | 10–15 min (15 min if you are new to Google Cloud) |
| 3 | Notification targets (Slack / email / LINE / Chatwork) | 3–10 min (only the channels you use) |
| 4 | Import the workflows and assign credentials | 5 min |
| 5 | Edit `Config` | 3–5 min |
| 6 | Values that go into the trigger nodes | 2 min |
| 7 | Test run | 5 min |
| 8 | Going live | 3 min |
| 9 | Troubleshooting | as needed |
| 10 | Checklist | 1 min |

---

## 0. Time required and prerequisites (2 min)

### Supported n8n versions
- Built and tested on **n8n 2.40.5 (self-hosted, Node.js 24)**.
- **n8n Cloud is assumed to work on any 2.x version**, but the template has not been tested on Cloud. Every node is a built-in n8n node; no community nodes and no `Read/Write Files from Disk` node are used, so the workflows can be imported on Cloud.
- On 1.x the UI labels differ (for example `Activate` instead of `Publish`). This guide uses the 2.x labels.

### What you need
| Item | Required | Used for |
|---|---|---|
| An admin account on n8n 2.x (Cloud or self-hosted) | Required | Importing the workflows, registering credentials |
| A Google account | Required | Spreadsheet, watched folder. Gmail only if you use email intake or email notifications (§2, §6.4) |
| Permission to create a project in Google Cloud Console | Required for self-hosted (Cloud can skip it with "Sign in with Google", §2.4) | Issuing the OAuth client |
| A Slack workspace (with permission to install apps) | Optional | Slack notifications |
| A LINE Official Account plus LINE Developers (Messaging API channel) | Optional | LINE notifications |
| A Chatwork account (with API use approved) | Optional | Chatwork notifications |
| Your bank's transaction CSV export, or the bank's deposit notification emails | Required in operation | Input data |

### What this template does not do
- It does not promise compatibility with any specific bank. CSV column names and encoding are set in `CSV_MAPPING`, email parsing in `MAIL_PARSERS`; **you adapt the regular expressions yourself**. Samples for two fictional banks are included (`fixtures/`).
- JPY only.
- Ambiguous deposits (several candidate invoices) and deposits with no matching invoice are never confirmed automatically. A person reads the notification and corrects the sheet.

---

## 1. Create the spreadsheet (5 min)

Create one spreadsheet with two sheets, `invoices` and `transactions`, from `shared/invoices.template.csv` and `shared/transactions.template.csv` (details in `shared/sheets-schema.md`).

1. In Google Drive, **create a new Google Sheets spreadsheet**. Any name is fine (e.g. `payment-ops`).
2. Choose **File → Import → Upload** and select `shared/invoices.template.csv`.
3. Use these import settings:
   - Import location: **Insert new sheet(s)**
   - Separator type: **Detect automatically**
   - **Uncheck "Convert text to numbers, dates, and formulas"**
4. Rename the new sheet tab to **`invoices`** (lowercase ASCII, no spaces).
5. Import `shared/transactions.template.csv` the same way and name the tab **`transactions`**.
6. On each sheet, **select all (Ctrl+A) → Format → Number → Plain text**. This stops Google's automatic formatting from turning `2026-09-10` into `2026/09/10`; the template reads and writes both numbers and dates as strings.
7. **Do not rename, delete or reorder row 1 (the column names).** A single-character difference breaks the workflow. Adding your own columns to the right is fine.
8. Leave the sample rows (rows 2–4) in place; you will delete them after the test run in §7.
9. Note the **ID** from the browser address bar, `https://docs.google.com/spreadsheets/d/<this is the ID>/edit`. You will paste it into `SHEET_ID` in `Config` in §5.
10. Create the watched folder. In Google Drive choose **New → New folder** (e.g. `bank-csv`), open it, and note the **ID** from the URL `https://drive.google.com/drive/folders/<this is the ID>`. You will use it in §5 and §6.
11. In Google Drive settings (`drive.google.com/drive/settings`), **uncheck "Convert uploads to Google Docs editor format"**. If it stays on, CSV files are converted into Google Sheets and Shift_JIS remitter names can be corrupted (see Google Drive Help, "Upload files & folders to Google Drive").

Columns of `invoices` to fill in first:

| Column | Contents |
|---|---|
| `invoice_id` | Invoice number (unique) |
| `customer_name` | Billing name (kanji is fine) |
| `payer_name_alias` | **Remitter name(s) as they appear on bank transfers, in katakana, comma-separated.** Japanese banks deliver remitter names in katakana, so a kanji `customer_name` alone will not match. Leaving this empty sharply lowers the auto-match rate (§8) |
| `amount` | Invoice amount including tax (yen, integer) |
| `currency` | `JPY` |
| `due_date` | `yyyy-MM-dd` |
| `status` | `unpaid` |
| `paid_amount` | `0` |

---

## 2. Google setup (10 min)

This template uses three Google services. Create **one n8n credential per service**, up to three in total (**Gmail OAuth2 API** only if you use email intake or email notifications; otherwise deactivate `Watch Gmail Inbox` and `Notify Email` as described in §6.4).

| n8n credential type (as shown in the UI) | Nodes that use it |
|---|---|
| **Google Drive OAuth2 API** | `Watch Drive Folder`, `Download File` |
| **Google Sheets OAuth2 API** | `Read Invoices`, `Read Transactions`, `Update Invoices`, `Upsert Transactions` |
| **Gmail OAuth2 API** | `Watch Gmail Inbox`, `Notify Email` (and `Notify Email` in the Error Handler) |

The procedure follows the official n8n page "Google OAuth2 single service" (reference [1]). The steps below summarize it.

### 2.1 Create a Google Cloud project
1. Log in to the [Google Cloud Console](https://console.cloud.google.com) with your Google account.
2. In the project dropdown at the top, select **New project**.
3. Enter a **Project name** and select **Create**.
4. Check that the project dropdown at the top now shows the project you created.

### 2.2 Enable the APIs
1. Open **APIs & Services > Library** in the left menu.
2. Search for each of the following three APIs and select **ENABLE** for each:
   - **Google Sheets API**
   - **Google Drive API** (the official documentation states that the Google Sheets node requires it too)
   - **Gmail API** (if you create the Gmail credential)
3. The Google Calendar API is not needed for this template.

### 2.3 OAuth consent screen
1. Open **APIs & Services > OAuth consent screen**. Google redirects you to the Overview page of the Google Auth Platform.
2. Select **Get started**.
3. Enter an **App name** (e.g. `n8n`) and a **User support email**, then **Next**.
4. For **Audience**, select **Internal** if you use it inside a Google Workspace organization, or **External** for a personal Gmail account, then **Next**.
5. Enter a contact email and select **Next** → accept the policy and select **Continue** → **Create**.
6. Open **Branding** in the left menu and, under **Authorized domains**, select **Add domain**:
   - n8n Cloud: `n8n.cloud`
   - Self-hosted: the domain of your n8n instance
7. Select **Save**.
8. If you chose **External**, the app is in **Testing** status. Open **Audience** in the left menu and add the Google account you will connect from n8n to **Test users**. Without this, the connection is blocked with an "access denied" screen.
   - Note: according to the official documentation, for a **Testing + External** app **consent and tokens expire after 7 days**. When they expire, reconnect the credential in n8n's credential screen. For long-term operation, consider publishing the app on the Google side (set Publishing status to In production).

### 2.4 Create the OAuth client (Google side) and the n8n credentials
Repeat the following once per credential (up to three times). **One Google OAuth client can be reused by all three credentials** (same Client ID and Client Secret, one redirect URI).

**On n8n Cloud**: Google Drive, Google Sheets and Gmail (including their triggers) support **Managed OAuth2**, so **Sign in with Google** on the credential screen is all you need (no work in Google Cloud Console). The official documentation lists the supported nodes (reference [1]). In that case you can skip §2.1–2.3.

1. In n8n's left menu select **Create** (the create button) → **Credential**.
2. Type `Google Sheets` in the search box and select **Google Sheets OAuth2 API** (second time: **Google Drive OAuth2 API**, third time: **Gmail OAuth2 API**).
3. Copy the **OAuth Redirect URL** shown on the credential screen (for a local self-hosted instance it looks like `http://localhost:5678/rest/oauth2-credential/callback`).
4. In Google Cloud Console open **APIs & Services > Credentials** and select **+ Create credentials > OAuth client ID**.
5. Set **Application type** to **Web application**.
6. Give it a recognizable **Name**, paste the URL from step 3 into **Authorized redirect URIs** **exactly, including the protocol and port number**, and select **Create**.
7. Paste the **Client ID** and **Client Secret** shown by Google into the fields of the same name in n8n's credential screen (watch for leading or trailing spaces).
8. Select **Sign in with Google** and grant access with the Google account you registered in §2.3.
9. Give the credential a recognizable name and **Save**. The name is up to you (e.g. `Google Sheets (payment-ops)`). The workflows reference credentials **not by name but by what you assign to each node in §4.3**.
10. The scopes (permissions) are set by the n8n credential by default. Leave **Custom Scopes** OFF (turning it on reveals a Scope field and the notice "The default scopes needed for the node to work are already set"; the defaults are sufficient).
11. For the second and third credential only steps 1–2 and 7–9 are needed (the same OAuth client is reused).
12. Make sure the Google account used for the Google Sheets credential has **edit access** to the spreadsheet from §1 (not needed if you created it yourself).

---

## 3. Notification targets (only the channels you use, 3–10 min each)

Channels are selected in `Config` → `NOTIFY_CHANNELS` (default `["slack"]`). You do not need to set up channels you will not use. **Never put tokens into Config; they always go into n8n credentials.**

### 3.1 Slack (5 min)
The `Notify Slack` node is built for the **Access Token** (Bot User OAuth Token) method. Follow the official n8n page "Slack credentials" (reference [4]).

1. Open [Slack API Apps](https://api.slack.com/apps) and select **Create New App > From a manifest**.
2. Pick the workspace to post to and select **Next**.
3. Select the **JSON** tab and replace the default manifest with the "manifest for API access token" published on the official n8n page. The minimum scope required is `chat:write` (the official manifest includes more scopes; you may remove the others).
4. **Next** → review → **Create**.
5. In the left menu select **OAuth & Permissions** → under **OAuth Tokens** select **Install to Workspace** → **Allow** (requires workspace admin rights).
6. Copy the **Bot User OAuth Token** (it starts with `xoxb`).
7. In n8n select **Create → Credential** → search `Slack` → select **Slack API**, paste the token into **Access Token** and **Save**. Any credential name is fine.
8. **Leave token rotation OFF.** With rotation on, tokens expire after 12 hours and stop working from n8n, and rotation cannot be turned off again afterwards (official documentation, "Common issues").
9. Decide on the destination channel and **add the app (bot) to that channel.** The Slack API requires the app to be a member of the channel; otherwise posting fails with `not_in_channel` (reference [5]). The Slack help page describing how to add an app to a channel could not be fetched when this guide was written, so look up "add an app to a channel" in the Slack Help Center.
10. Note the value to put into `SLACK_CHANNEL` in `Config`. Either `#channel-name` (e.g. `#deposit-reconciliation`) or the channel ID (a string starting with `C`) works. The channel ID is the `C…` part of the URL `https://app.slack.com/client/T…/C…` when you open the channel in a browser (reference [6]).

### 3.2 Email notifications (0 min)
`Notify Email` uses the **Gmail OAuth2 API** credential you created in §2. The recipient is `NOTIFY_EMAIL_TO` in `Config`.

### 3.3 LINE (10 min)
`Notify LINE` is an HTTP Request node that calls the LINE Messaging API push endpoint (`POST https://api.line.me/v2/bot/message/push`). Authentication is a **Header Auth** credential. LINE Notify is not used because it was discontinued in March 2025.

1. Prepare a Messaging API channel. Since September 4, 2024 it can no longer be created directly in the LINE Developers Console; the order is **create a LINE Official Account → enable the Messaging API in LINE Official Account Manager → log in to the LINE Developers Console** (reference [7]).
2. Open the channel in the LINE Developers Console and issue a channel access token. The official documentation recommends **channel access token v2.1, which has a user-specified expiration (up to 30 days)**. If you run unattended and want to avoid renewing it, you can use a **long-lived channel access token (no expiration, Messaging API channels only)**. Decide for yourself which one to use; when a token expires, issue a new one and update the credential (references [8][9]).
3. Find your own userId (`U` followed by 32 hexadecimal characters; format `U[0-9a-f]{32}`), which is the notification recipient, under **Your user ID** on the channel's **Basic settings** tab. If it is not shown, your Business ID must first be linked to a LINE account (reference [10]).
4. In the LINE app, **add the Official Account as a friend** (reference [9]).
5. In n8n select **Create → Credential** → search `Header Auth` → select **Header Auth**.
6. Enter `Authorization` as **Name** (the header name) and, as **Value**, the single string `Bearer` + one space + the channel access token (exactly one space after `Bearer`; pasting the token alone does not authenticate).
7. Name the credential **`LINE Messaging API`** and **Save**.
8. Put the userId from step 3 into `LINE_TO_USER_ID` in `Config` (§5).

### 3.4 Chatwork (5 min)
`Notify Chatwork` is an HTTP Request node that calls `POST https://api.chatwork.com/v2/rooms/{room_id}/messages`. Authentication is a **Header Auth** credential with the header `X-ChatWorkToken` (references [11][12]).

1. Issue an API token in Chatwork under **利用者名 (your user name, top right) → サービス連携 (Service integrations) → API トークン (API token)**. On plans other than the Personal plan, **your organization admin must approve API use** first (reference [11]).
2. Find the room ID (a number) of the destination room. The Chatwork help page describing how to find a room ID could not be fetched when this guide was written. The official API reference's `GET https://api.chatwork.com/v2/rooms` ("チャット一覧を取得する" — get chat list) returns the `room_id` of each room, so you can use it to find the ID (reference [13]).
3. In n8n select **Create → Credential** → **Header Auth**.
4. Enter `X-ChatWorkToken` as **Name** and the API token as **Value**.
5. Name the credential **`Chatwork API`** and **Save**.
6. Put the room ID into `CHATWORK_ROOM_ID` in `Config` (§5).

---

## 4. Import the workflows (5 min)

### 4.1 Import order
Import the Error Handler first (it is selected in the main workflow's Settings). Use **Import from File** as described in the official n8n page "Export and import" (reference [14]).

1. In n8n's left menu select **Create → Workflow** to open an empty workflow.
2. Open the **three-dots menu (…) in the top right → Import from File** and choose `error-handler.json`.
3. Check that the workflow name is `[Odaji] 01 Error Handler v1.0.0`. **Do not rename it.**
4. Select **Create → Workflow** again to open another empty workflow and import `workflow.json` the same way. Its name is `[Odaji] 01 Bank Deposit Reconciliation v1.0.0`.
5. On 2.x, edits are saved automatically. On 1.x select **Save**.

### 4.2 Checks right after import
1. Check that the canvas shows 30 nodes and 8 sticky notes (the Error Handler shows 11 nodes and 4 sticky notes) and that **no node is red (in an error state)**. If you see "Unknown node" or "Node type not found", your n8n version is too old or a built-in node has been disabled.
2. Nodes without a credential show a warning icon. §4.3 resolves this.
3. The sticky notes contain Japanese (`## JA`) followed by English (`## EN`); they summarize the same content as this guide.

### 4.3 Select the credential in each node
Double-click a node to open it and select the credential in the credential field at the top. **A selection is required in every one of the following nodes.**

Main workflow `[Odaji] 01 Bank Deposit Reconciliation v1.0.0`:

| Node | Credential to select | Notes |
|---|---|---|
| `Watch Drive Folder` | Google Drive OAuth2 API | |
| `Watch Gmail Inbox` | Gmail OAuth2 API | |
| `Download File` | Google Drive OAuth2 API | |
| `Read Invoices` | Google Sheets OAuth2 API | |
| `Read Transactions` | Google Sheets OAuth2 API | |
| `Update Invoices` | Google Sheets OAuth2 API | |
| `Upsert Transactions` | Google Sheets OAuth2 API | |
| `Notify Slack` | Slack API (Access Token) | If `slack` is in `NOTIFY_CHANNELS` |
| `Notify Email` | Gmail OAuth2 API | If `email` is in it |
| `Notify LINE` | Header Auth `LINE Messaging API` | If `line` is in it. Leave Authentication as **Generic Credential Type → Header Auth** |
| `Notify Chatwork` | Header Auth `Chatwork API` | If `chatwork` is in it. Same as above |

Error Handler `[Odaji] 01 Error Handler v1.0.0`:

| Node | Credential to select |
|---|---|
| `Notify Slack` | Slack API (same as the main workflow) |
| `Notify Email` | Gmail OAuth2 API (same as the main workflow) |
| `Notify LINE` | Header Auth `LINE Messaging API` |
| `Notify Chatwork` | Header Auth `Chatwork API` |

- **Deactivate the `Notify …` nodes of channels you do not use, in both the main workflow and the Error Handler** (right-click the node → **Deactivate**; a deactivated node turns grey). When you Publish (activate) a workflow, n8n validates the credentials of every active node, so if even one node without a credential stays active, publishing is refused with **`Cannot publish workflow: … Missing required credential: slackApi`** (or `gmailOAuth2`) (confirmed by the author on n8n 2.40.5). Deactivated nodes are not validated.
- Also remove deactivated channels from `NOTIFY_CHANNELS` (§5). A deactivated node passes its input straight through, so if the channel stays in `NOTIFY_CHANNELS`, `Check Notification Results` counts it as "failed" (with `notify node disabled or not executed (payload passed through)` in `errors`). If it is the only channel, the run fails with `All notification channels failed (1): …`. Notifications never go missing silently.
- If `Notify LINE` / `Notify Chatwork` (HTTP Request) run without a credential, they fail with "Node does not have any credentials set". Always select the Header Auth credential for the channels you use.
- You can switch the Authentication of `Notify Slack` to OAuth2, but then you must create a separate Slack OAuth2 API credential. This guide describes the Access Token method.

### 4.4 Workflow Settings
Set these in the main workflow (references [15][16]).

1. Open the **three-dots menu (…) in the top right → Settings**.
2. Under **Error Workflow (to notify when this one errors)** select **`[Odaji] 01 Error Handler v1.0.0`**.
3. Check that **Timezone** is **Asia/Tokyo** (it is included in `workflow.json`; reselect it if it differs).
4. Select **Save**.
5. Leave the Error Workflow setting in the Error Handler's own Settings **empty** (prevents infinite loops).
6. **Publish the Error Handler** (open the Error Handler, select credentials or deactivate the nodes of unused channels as in §4.3, edit the Error Handler's `Config` as in §5.3, then select **Publish** in the top right and **Publish** again in the dialog; see §7.2 step 2). On the author's n8n 2.40.5, **an Error Workflow that is not published is never invoked when the main workflow fails** (n8n only logs `Calling Error Workflow for "…". Workflow "…" is not active and cannot be executed`). The official documentation (reference [20]) says publishing is not required, but in practice it was. If Publish is refused with `Missing required credential`, revisit the deactivation in §4.3.

---

## 5. Edit `Config` (3–5 min)

Open the `Config` node in the main workflow (Edit Fields (Set), Mode: JSON) and edit the JSON directly. **Replace every value that starts with `REPLACE_ME_` and `replace-me@example.com`.** Take care not to break the JSON syntax (quotes, commas).

Edit the JSON field in **Expression** mode as it is (the last key, `SOURCE`, contains `{{ $prevNode.name }}`); **do not switch it to Fixed** (if you do, `SOURCE` becomes a literal string and `Route by Source` no longer routes correctly). The JSON is about 160 lines long. `SHEET_ID` and `DRIVE_FOLDER_ID` are near the top; `SLACK_CHANNEL` / `NOTIFY_EMAIL_TO` / `LINE_TO_USER_ID` / `CHATWORK_ROOM_ID` follow `NOTIFY_CHANNELS`.

| Key | Required | Default | What to enter |
|---|---|---|---|
| `TZ` | — | `"Asia/Tokyo"` | Time zone for date handling. Keep it equal to the Timezone in the workflow Settings |
| `LANG` | — | `"ja"` | Language of the notification text: `ja` or `en` |
| `SHEET_ID` | **Required** | `"REPLACE_ME_SHEET_ID"` | Spreadsheet ID from §1 step 9 |
| `SHEET_INVOICES` | — | `"invoices"` | Sheet name of the invoice list. Leave as is unless you renamed the tab |
| `SHEET_TRANSACTIONS` | — | `"transactions"` | Sheet name of the transaction ledger |
| `DRIVE_FOLDER_ID` | **Required** | `"REPLACE_ME_DRIVE_FOLDER_ID"` | Watched folder ID from §1 step 10. **For reference only; the live value is the one in the `Watch Drive Folder` node (§6).** Keep both equal |
| `GMAIL_QUERY` | — | `"subject:(入金 OR Deposit) newer_than:1d"` | Gmail search query (`入金` = "deposit"). **For reference only; the live value is the Search field of `Watch Gmail Inbox` (§6).** Keep both equal |
| `RUN_AT` | — | `"09:00"` | Daily re-match time (JST). **For reference only; the live value is in `Run Daily Rematch` (§6)** |
| `TRIGGERS_ENABLED.drive` | — | `true` | Whether to import CSV files from the watched folder |
| `TRIGGERS_ENABLED.gmail` | — | `true` | Whether to import deposit notification emails. Set `false` if unused |
| `TRIGGERS_ENABLED.schedule` | — | `true` | Whether to run the daily re-match |
| `CSV_MAPPING.date_col` | Required if you use bank CSV | `"日付"` (date) | Header of the transaction-date column (must match the string in row 1 of the CSV exactly) |
| `CSV_MAPPING.payer_col` | Same | `"摘要"` (description) | Header of the remitter-name (description) column |
| `CSV_MAPPING.deposit_col` | Same | `"入金額"` (deposit amount) | Header of the deposit-amount column. Rows where it is empty or 0 (withdrawals) are ignored |
| `CSV_MAPPING.withdraw_col` | — | `"出金額"` (withdrawal amount) | Header of the withdrawal-amount column (informational; `""` if there is none) |
| `CSV_MAPPING.memo_col` | — | `""` | Only if there is a memo column separate from the description |
| `CSV_MAPPING.skip_rows` | — | `0` | Number of lines to discard before the header row (e.g. `1` for a CSV with a description line) |
| `CSV_MAPPING.date_format` | — | `"auto"` | `auto` / `yyyy/MM/dd` / `yyyyMMdd` / `yyyy-MM-dd` |
| `CSV_MAPPING.encoding` | — | `"shift_jis"` | `shift_jis` / `utf-8` / `auto`. A file with a UTF-8 BOM is always read as UTF-8 regardless of this setting |
| `MAIL_PARSERS` | Required if you import emails | 2 entries (bankX / bankY) | Parsing rules for deposit notification emails (see 5.2 below) |
| `LEGAL_ENTITY_TOKENS` | — | `["カ)", "(カ", …, "株式会社", …]` | Legal-entity markers and similar tokens stripped from remitter names. Full-width additions are accepted |
| `STRIP_LEADING_DIGITS` | — | `true` | Strip a leading run of digits (remitter number, branch code) from the remitter name |
| `FEE_SET` | — | `[110,165,220,275,330,440,550,660,770,880]` | Differences (yen) accepted as a transfer fee deducted by the payer |
| `NAME_MIN_CONTAINS` | — | `3` | Minimum number of characters for a containment name match |
| `NOTIFY_CHANNELS` | — | `["slack"]` | Any combination of `slack` / `email` / `line` / `chatwork` (array). Empty `[]` = no notifications |
| `SLACK_CHANNEL` | Required if you use `slack` | `"REPLACE_ME_SLACK_CHANNEL_ID"` | `#channel-name` or the `C…` ID (§3.1) |
| `NOTIFY_EMAIL_TO` | Required if you use `email` | `"replace-me@example.com"` | Recipient of the notification email |
| `LINE_TO_USER_ID` | Required if you use `line` | `"REPLACE_ME_LINE_USER_ID"` | LINE userId (§3.3) |
| `CHATWORK_ROOM_ID` | Required if you use `chatwork` | `"REPLACE_ME_CHATWORK_ROOM_ID"` | Chatwork room ID (§3.4) |
| `LINE_API_URL` | — | `"https://api.line.me/v2/bot/message/push"` | LINE push URL. **Do not change** (only if you route the API through a proxy) |
| `CHATWORK_API_BASE_URL` | — | `"https://api.chatwork.com/v2"` | Chatwork API base URL. **Do not change** |
| `NOTIFY_MAX_LINES` | — | `40` | Maximum number of detail lines per notification section. The rest becomes "… and N more" |
| `MESSAGES` | — | Contents of `shared/messages.ja.json` / `messages.en.json` | Notification text (`ja` / `en`). Edit only if you want different wording |
| `SOURCE` | — | `{{ $prevNode.name }}` | Set automatically. **Do not change** |

`REPLACE_ME_…` values left in place for channels you do not use have no effect (those channels never run). To avoid confusion, however, we recommend setting them to an empty string `""`.

### 5.1 Adapting `CSV_MAPPING`
1. Open a CSV downloaded from your bank in a text editor and look at the **column headers in line 1**.
2. Write those headers **verbatim** into `date_col` / `payer_col` / `deposit_col`.
3. If there are description lines before the header, put their count into `skip_rows`.
4. If dates look like `20260917`, set `date_format` to `"yyyyMMdd"` (`auto` also reads it, but being explicit is safer).
5. If the encoding is UTF-8 (without BOM), set `encoding` to `"utf-8"`.
6. Examples are in `fixtures/csv_mapping.examples.json`. `bank_A_sjis.csv` (headers `日付,摘要,入金額,出金額,残高` = date, description, deposit, withdrawal, balance; Shift_JIS) works with the defaults; `bank_B_utf8bom.csv` (headers `取引日,内容,お預入,お引出` = transaction date, details, deposit, withdrawal; UTF-8 with BOM; `yyyyMMdd`) needs these values:

```json
"CSV_MAPPING": {
  "date_col": "取引日", "payer_col": "内容", "deposit_col": "お預入", "withdraw_col": "お引出",
  "memo_col": "", "skip_rows": 0, "date_format": "yyyyMMdd", "encoding": "utf-8"
}
```

### 5.2 Adapting `MAIL_PARSERS`
`MAIL_PARSERS` is an array; the rules are tried in order and **the first matching rule** is used. The reference examples are in `fixtures/mail_parsers.example.json` (they match the bundled fictional emails `mail_bankX.eml` / `mail_bankY.eml`).

| Field | Meaning |
|---|---|
| `name` | Label shown in notifications |
| `from_match` | Substring of the sender address (case-insensitive partial match). Example: `"@example.jp"` |
| `subject_match` | Substring of the subject. Example: `"入金"` (deposit) |
| `amount_regex` | Regular expression applied to the body. **The first capture group `( )` is the amount** |
| `payer_regex` | Likewise, the first capture group is the remitter name |
| `date_regex` | Likewise, the first capture group is the date. If absent, the email's received date is used |

How to adjust the regular expressions:
1. Open one deposit notification email from your bank and find the lines that contain the amount, remitter name and date.
2. The body is **NFKC-normalized** before parsing (full-width alphanumerics become half-width; the default regexes use `[：:]` so that a full-width colon `：` is treated like `:`).
3. For a labelled one-line layout (`入金額：33,000円`, i.e. "Deposit amount: 33,000 yen"), use the bankX pattern `(?:入金額|お振込金額|金額)[：:]\\s*([0-9,]+)` and replace only the label names with your bank's.
4. For a tabular layout (`Amount             JPY 19,800`), use the bankY pattern `Amount\\s+(?:JPY|¥)?\\s*([0-9,]+)` as a starting point.
5. Inside JSON, write `\` as `\\` (`\\s`, `\\d`).
6. Use capturing parentheses `( )` **only around the one value you extract**; make every other group non-capturing `(?: )`.
7. For the remitter name, capturing to the end of the line with `([^\\n]+)` is the safe choice.
8. An email that matches no rule does not stop the run; it appears under "Warnings" in the notification as `no_parser_matched` (no rule matched) or `parser_no_capture` (the regex captured nothing). Use these to tune the rules.
9. A syntactically invalid regular expression makes the run fail (so that a Config mistake is not hidden).

### 5.3 The Error Handler's `Config`
The Error Handler `[Odaji] 01 Error Handler v1.0.0` has its own `Config` node with only the 9 keys needed for notifications: `LANG`, `NOTIFY_CHANNELS`, `SLACK_CHANNEL`, `NOTIFY_EMAIL_TO`, `LINE_TO_USER_ID`, `CHATWORK_ROOM_ID`, `LINE_API_URL`, `CHATWORK_API_BASE_URL`, `MESSAGES`. Enter the same values as in the main workflow and replace `REPLACE_ME_…` and `replace-me@example.com` (the Error Handler cannot read the main workflow's `Config`). Edit the JSON field as it is, without changing its mode. Do this before publishing in §4.4 step 6.

---

## 6. Values that go into the trigger nodes (2 min)

Trigger nodes run before `Config`, so they cannot read its values. **Enter the real values directly into the following three nodes.** `DRIVE_FOLDER_ID` / `GMAIL_QUERY` / `RUN_AT` in `Config` only record what you configured, so keep them equal.

### 6.1 `Watch Drive Folder` (Google Drive Trigger)
1. Open the node.
2. Leave **Trigger On** as the specific-folder option (`Changes Involving a Specific Folder`).
3. Make sure the mode selector on the left of **Folder** shows **ID** (it does right after import) and replace `REPLACE_ME_DRIVE_FOLDER_ID` with the folder ID from §1 step 10 (you can also switch to **Link** and paste the folder URL; **Folder** picks from a list and only works after the credential is connected).
4. Leave **Watch For** as `File Created`. Polling every minute (`Poll Times: Every Minute`) is fine.

### 6.2 `Watch Gmail Inbox` (Gmail Trigger)
1. Open the node.
2. Leave **Simplify** **OFF** (the body is needed; with it ON the body is not returned and cannot be parsed).
3. Enter the search query under **Filters → Search**. The default is `subject:(入金 OR Deposit) newer_than:1d`, which matches the subjects of the two bundled sample emails. Change the `subject:` words or add `from:` to match your bank's notifications. Gmail's `subject:` does not search the body (reference [17]).
4. **Read Status** `Unread and read emails`, **Max Emails per Poll** `10` and polling every 5 minutes can stay as they are.
5. Set `GMAIL_QUERY` in `Config` to the same value.

### 6.3 `Run Daily Rematch` (Schedule Trigger)
1. Open the node.
2. The defaults are **Trigger Interval** `Days`, **Days Between Triggers** `1`, **Trigger at Hour** `9am`, **Trigger at Minute** `0`. If you change them, set `RUN_AT` in `Config` to the same value.
3. The time is interpreted in the Timezone of the workflow Settings (Asia/Tokyo) (reference [18]).

### 6.4 Switching off a path you do not use
- Setting the key in `Config` → `TRIGGERS_ENABLED` to `false` makes that path fall through `Route by Source` into `Skip Disabled Trigger` and end normally. **The trigger node itself keeps polling, however (the Drive / Gmail API calls continue).**
- To stop the API calls as well, deactivate the trigger node (**Deactivate** in the node menu). A deactivated node does not run even after `Publish`.
- If you do not use Gmail at all (neither email intake nor email notifications), set `TRIGGERS_ENABLED.gmail` to `false` and deactivate `Watch Gmail Inbox` and `Notify Email` (in both the main workflow and the Error Handler). If these nodes stay active without a Gmail OAuth2 API credential, publishing is refused with `Missing required credential: gmailOAuth2` (§4.3).
- **Do not rename the trigger nodes.** `Route by Source` branches on the node names (`Watch Drive Folder` / `Watch Gmail Inbox` / `Run Daily Rematch`).

---

## 7. Test run (5 min)

Use the bundled fictional data to check the whole chain: import → matching → sheet update → notification. **Do this before entering real invoice data.**

### 7.1 Put the test data into the sheets
1. Delete the sample rows (rows 2–4) of the `invoices` sheet and import the 20 rows of `fixtures/invoices.seed.csv` (either import as in §1 with **Append to current sheet**, or copy the contents and paste from row 2). The column names in row 1 are identical, so if you paste, do not include the header line.
2. Likewise delete the sample rows of the `transactions` sheet and insert the single row of `fixtures/transactions.seed.csv`.
3. Check that the columns are still formatted as "Plain text" after pasting.

### 7.2 Drop the CSV into the watched folder
1. Check that `CSV_MAPPING` in `Config` still has the defaults (`日付` / `摘要` / `入金額` / `出金額`, `shift_jis`).
2. Publish the main workflow. Select **Publish** in the top right (or Shift+P); a publishing dialog opens (the version name defaults to a UUID and can stay as is). Select **Publish** in the dialog to go live. Triggers do not run until the workflow is published (reference [19]).
3. Upload `fixtures/bank_A_sjis.csv` to the watched folder from §1 step 10 (double-check that Drive's "convert" setting is OFF).
4. Wait one or two minutes, then check the workflow's **Executions** tab: one new execution should appear with a successful (green) status.
   - Note: running the Google Drive Trigger manually with **Execute workflow** returns the single most recent event matching its criteria; if there is none, it throws an error (note in the official documentation). If you want to check manually, run it after placing the file.

### 7.3 Expected result
The notification (`LANG=ja`) reads as follows (the date is the run date; from `tests/CASES.md` §3):

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

Reading the Japanese block: the title line is "processed 11 | auto-matched 4 | needs review 3 | unmatched 4"; the four sections are "needs review (auto-matched by amount only, fee deducted, or combined)", "ambiguous (multiple candidates, not auto-matched; pick one)", "unmatched (no matching invoice)" and "auto-matched"; `振込` / `フリコミ` is the bank's "transfer" prefix on the remitter name; `候補:` means "candidates:"; and the reason suffixes are "(fee ¥220 deducted)", "(amount only, needs review)", "(combined)" and "(partial, remaining ¥150,000)". With `LANG=en` the same lines use the English strings from `shared/messages.en.json` (title `[Reconciliation 2026-09-23] Processed 11 | Auto-matched 4 | Needs review 3 | Unmatched 4`).

Changes on the `invoices` sheet (from `fixtures/README.md` §2):

| invoice_id | status | match_confidence | paid_amount | fee_deducted |
|---|---|---|---|---|
| INV-2026-001 | paid | auto | 33000 | 0 |
| INV-2026-002 | paid | fee_deducted | 54780 | 220 |
| INV-2026-003 | paid | auto | 9800 | 0 |
| INV-2026-004 | paid | amount_only | 128000 | 0 |
| INV-2026-005 / 006 | paid | combined | 700000 / 534567 | 0 |
| INV-2026-007 | partial | auto | 100000 | 0 |
| INV-2026-012 | paid | auto | 27500 | 0 |
| INV-2026-008 / 009 (two invoices with the same amount) | stays unpaid | — | 0 | — |

11 rows are appended to the `transactions` sheet (the 4 withdrawal rows are ignored). `status` is one of `matched` / `unmatched` / `ambiguous`.

### 7.4 Idempotency check (optional)
Drop the same `bank_A_sjis.csv` into the watched folder again (a different file name is fine). The notification reads `【入金消込 …】新規の入金はありませんでした（処理済みのため skip：11 件）` (with `LANG=en`: `[Reconciliation …] No new transactions (skipped as already processed: 11)`), and the sheets do not change.

### 7.5 Email path check (optional)
Send `fixtures/mail_bankX.eml` / `mail_bankY.eml` to your own Gmail address (for example by opening the .eml in a mail client and forwarding it). If they match the Search of `Watch Gmail Inbox`, `INV-2026-018` (104,500 yen) and `INV-2026-019` (19,800 yen) become `paid`. Because the sender will not be `example.jp` / `example.com`, temporarily change `from_match` in `MAIL_PARSERS` to your own sending address for this check.

### 7.6 Remove the test data
1. **Delete all** rows `INV-2026-001` to `INV-2026-020` from the `invoices` sheet.
2. **Delete all** rows added by the test run from the `transactions` sheet (including the one seed row). Leftover rows will not cause a real deposit to be skipped as "already processed" (its `txn_id` will differ), but fictional data would remain in your ledger.
3. The Error Handler cannot be tested manually (the Error Trigger fires only when an automatic run fails; reference [20]). After publishing in §8 you can test it by temporarily setting a wrong notification target, because `Check Notification Results` is designed to fail the run when every channel fails.

---

## 8. Going live (3 min)

1. Enter your real invoices into the `invoices` sheet. **Always fill in `payer_name_alias`.** Remitter names arrive in katakana (including half-width katakana and abbreviated legal-entity markers such as `ｶ)`). Copy the actual remitter names from past bank statements and, if there are several, enter them comma-separated (e.g. `カ)サンプルシヨウジ,サンプルシヨウジ`). If this column is empty, name matching cannot work and you will see more "amount only (needs review)" and "unmatched" results.
2. Set the notification targets in `Config` (`SLACK_CHANNEL` / `NOTIFY_EMAIL_TO` etc.) to their production values, and enter **the same notification settings** in the Error Handler's `Config` (the Error Handler cannot read the main workflow's `Config`).
3. Make sure the main workflow is **published** (if you published in §7.2, you must **Publish** again after changing `Config` (the dialog from §7.2 step 2); on 2.x, edits do not reach production until you publish). **Also make sure the Error Handler is published** (§4.4 step 6; if it is not published it is never invoked. Publish it again after changing its `Config` as well).
4. Operational notes:
   - **Identical personal names**: individuals can share a name. That is why this template makes an amount match mandatory; a deposit whose amount matches but whose name does not is reported as "needs review". Always check these by eye.
   - **The CSV layout changes from one month to the next**: some banks add or drop the header row or add description lines. If a run fails with `CSV column not found`, review `CSV_MAPPING.skip_rows` and the column headers (§9).
   - **Ambiguous and unmatched deposits are settled by a person**: edit `invoices.status` / `paid_amount` / `paid_date` by hand and set `transactions.status` to `matched` (settled) or `ignored` (out of scope). Rows left as `unmatched` / `ambiguous` are re-evaluated by the daily re-match.
   - **Ledger size**: `transactions` is read in full on every run. Split the sheet by year once it exceeds 10,000 rows.
5. **Personal data**: `customer_name` / `customer_email` / `payer_name_alias` are names and email addresses. Keep the spreadsheet's sharing to a minimum and delete rows you no longer need. Notifications (Slack / email / LINE / Chatwork) contain remitter names and amounts, so keep the membership of the destination channel or room to a minimum as well. The template does not store the original bank CSV or notification emails in the sheet, and it keeps no tokens in Config. n8n's execution log (Executions) retains node inputs and outputs, so also review the save settings and retention period in the workflow Settings.

---

## 9. Troubleshooting (as needed)

| Symptom | Cause and fix |
|---|---|
| Remitter names are garbled (`�` or meaningless characters) | `CSV_MAPPING.encoding` does not match the file's actual encoding. Use `shift_jis` for Shift_JIS and `utf-8` for UTF-8. If Drive's "convert" setting is ON and the CSV was converted into a spreadsheet, the text was already broken at conversion time: turn the setting OFF and upload the file again (§1 step 11) |
| The run fails with `CSV column not found: "日付"` | The CSV headers do not match `date_col` / `payer_col` / `deposit_col` in `CSV_MAPPING`. The error message shows the actual headers after `header = …`; use those strings. If there are description lines before the header, increase `skip_rows` |
| The run fails with `CSV has no header row after skip_rows=…` | `skip_rows` is too large |
| No notification arrives (the run succeeded) | (1) Is the channel name (`slack` / `email` / `line` / `chatwork`) in `NOTIFY_CHANNELS`? (2) Did you select a credential in that channel's `Notify …` node? (3) Open the execution under Executions and look at the output of `Check Notification Results`. If `channels_failed` is 1 or more, `errors` contains the reason (`not_in_channel`, 401, etc.). When only some channels fail, the run still counts as successful and the sheets have already been updated |
| The run fails with `All notification channels failed …` | Every configured channel failed. Check `errors` as above. The sheets are updated before the notification, so re-running after the fix is safe: everything is skipped |
| `Notify LINE` / `Notify Chatwork` fail with `Node does not have any credentials set` | No Header Auth credential is selected in the HTTP Request node (§4.3) |
| Slack returns `not_in_channel` | The bot is not a member of the destination channel. Add the app to the channel (§3.1) |
| Slack returns `invalid_auth` / `token_revoked` | Token rotation is ON, or the app was reinstalled. Create a new app with rotation OFF and update the credential |
| A Google node returns `401 unauthorized_client` | The corresponding API (Sheets / Drive / Gmail) is not enabled in Google Cloud (references [21][22]) |
| "Google hasn't verified this app" or "access denied" when connecting to Google | The consent screen is External and in Testing status, and the connecting account is not in Test users (§2.3 step 8) |
| Google nodes start failing after a few days | An External + Testing app expires after 7 days. Reconnect in the credential screen or publish the app (§2.3) |
| `redirect_uri_mismatch` | n8n's OAuth Redirect URL and Google's Authorized redirect URIs differ, even if only by one character (§2.4) |
| `Watch Gmail Inbox` does not fire | The email does not match the Search (`subject:` does not look at the body). To include already-read emails, set Read Status to `Unread and read emails`. **With Simplify ON the body is not returned and cannot be parsed** |
| The same CSV was dropped twice but nothing was matched twice (this is correct) | By design, a transaction whose `txn_id` (date｜amount｜normalized name｜normalized memo) already exists in `transactions`, or is already recorded in an invoice's `matched_txn_ids`, is skipped. A genuine second deposit on the same day with the same amount, name and memo is therefore skipped as well; watch the "skipped as already processed" count in the notification and handle it by hand (`manual`) |
| The Error Handler does not run (the main run did fail) | (1) **Is the Error Handler itself published?** (§4.4 step 6; if not, n8n logs `Workflow "…" is not active and cannot be executed` and does not invoke it). (2) Is it selected under Settings → Error Workflow of the main workflow? (3) The Error Trigger fires **only when an automatic run of a published workflow fails**, never for manual runs. (4) A partial notification failure counts as "processed" and does not fire it (only `Check Notification Results` failing the run when all channels fail does). (5) Did you enter the notification targets in the Error Handler's `Config`? (6) Did you select credentials in the Error Handler's `Notify …` nodes for the channels you use? |
| Publish is refused with `Cannot publish workflow: … Missing required credential: slackApi` / `gmailOAuth2` etc. (main workflow or Error Handler) | A node without a credential is still active (a `Notify …` node, or `Watch Gmail Inbox` if you did not create the Gmail credential). Right-click the nodes of unused channels → **Deactivate**, or select a credential (§4.3, §6.4). Also remove deactivated channels from `NOTIFY_CHANNELS` |
| `errors` of `Check Notification Results` contains `notify node disabled or not executed (payload passed through)` | The `Notify …` node of a channel listed in `NOTIFY_CHANNELS` is deactivated. If you want that channel, activate the node (Activate) and select a credential; if not, remove it from `NOTIFY_CHANNELS` (§4.3) |
| A node's output shows "This data is pinned" | Pinned output from development is still present. Select **Unpin** in the banner. The shipped JSON contains no pinned data; if you pinned data yourself, production runs ignore it (reference [23]) |
| An invoice is not matched and `non_jpy_invoice` appears under "Warnings" | `invoices.currency` is not `JPY`. Only JPY is supported |
| The run stops on an empty sheet | `Read Invoices` / `Read Transactions` have Always Output Data ON and continue even when empty. If the run stops, the column names (row 1) are missing or have been changed |

---

## 10. Checklist (1 min)

Confirm that the deployment is complete:

- [ ] The spreadsheet has `invoices` / `transactions`, the column names are unchanged from the template, and all cells are "Plain text"
- [ ] Google Drive's "Convert uploads to Google Docs editor format" is OFF
- [ ] In Google Cloud, the Google Sheets API / Google Drive API / Gmail API are enabled, and the consent screen (Test users or published) and the OAuth client (redirect URI) are configured
- [ ] Google Sheets OAuth2 API / Google Drive OAuth2 API / Gmail OAuth2 API credentials are created in n8n and connected (Gmail only if you use it; otherwise `Watch Gmail Inbox` and `Notify Email` are deactivated)
- [ ] Credentials for the notification channels you use are created (Slack API, Header Auth `LINE Messaging API`, Header Auth `Chatwork API`)
- [ ] `error-handler.json` then `workflow.json` are imported, with no red nodes
- [ ] Credentials are selected in the 11 nodes of the main workflow and the 4 nodes of the Error Handler. The `Notify …` nodes of unused channels are deactivated (Deactivate) in both workflows and removed from `NOTIFY_CHANNELS`
- [ ] The main workflow's Settings have Error Workflow = `[Odaji] 01 Error Handler v1.0.0` and Timezone = `Asia/Tokyo`
- [ ] Every `REPLACE_ME_…` and `replace-me@example.com` in `Config` has been replaced (main workflow and Error Handler)
- [ ] `CSV_MAPPING` matches your bank's CSV headers / `MAIL_PARSERS` matches your bank's notification emails (for the paths you use)
- [ ] The Folder in `Watch Drive Folder`, the Search in `Watch Gmail Inbox` and the time in `Run Daily Rematch` are set and equal to `DRIVE_FOLDER_ID` / `GMAIL_QUERY` / `RUN_AT` in `Config`
- [ ] The notification and the sheet updates were verified with `fixtures/bank_A_sjis.csv`, and the test data was removed
- [ ] `invoices.payer_name_alias` is filled in for the real invoices
- [ ] The main workflow is **published**
- [ ] The Error Handler is **published** (it is never invoked otherwise)

---

## References / 参考

All fetched and checked on 2026-09-23. n8n UI labels (including the Folder modes Folder / Link / ID of the Google Drive Trigger, the Custom Scopes toggle of the Google credentials and the publishing dialog) were verified on self-hosted n8n 2.40.5.

1. n8n Docs — Google OAuth2 single service (Google Cloud project, enabling APIs, consent screen, OAuth client, Managed OAuth2, troubleshooting): https://docs.n8n.io/integrations/builtin/credentials/google/oauth-single-service.md
2. n8n Docs — Google credentials (nodes that support Managed OAuth2; OAuth2 vs Service Account): https://docs.n8n.io/integrations/builtin/credentials/google.md
3. n8n Docs — Create and edit credentials (creating and naming credentials): https://docs.n8n.io/build/understand-workflows/create-and-edit-credentials.md
4. n8n Docs — Slack credentials (creating the app from a manifest, Bot User OAuth Token, scopes, token rotation): https://docs.n8n.io/integrations/builtin/credentials/slack.md
5. Slack API — chat.postMessage (`not_in_channel`: the app must be a member of the conversation): https://docs.slack.dev/reference/methods/chat.postMessage
6. Slack Help — Locate your Slack URL or ID (URL format `https://app.slack.com/client/T…/C…`): https://slack.com/help/articles/221769328
7. LINE Developers — Get started with the Messaging API (channels are created through a LINE Official Account): https://developers.line.biz/en/docs/messaging-api/getting-started/
8. LINE Developers — Channel access token (types and validity periods): https://developers.line.biz/en/docs/basics/channel-access-token/
9. LINE Developers — Build a bot (issuing a channel access token, adding the account as a friend): https://developers.line.biz/en/docs/messaging-api/building-bot/
10. LINE Developers — Get user IDs (Your user ID under Basic settings): https://developers.line.biz/en/docs/messaging-api/getting-user-ids/
11. Chatwork API — Chatwork API へようこそ (Welcome to the Chatwork API; where to issue the API token, admin approval): https://developer.chatwork.com/docs/getting-started
12. Chatwork API — チャットにメッセージを投稿する (Post a message to a chat; `POST /rooms/{room_id}/messages`, header `x-chatworktoken`): https://developer.chatwork.com/reference/post-rooms-room_id-messages
13. Chatwork API — チャット一覧を取得する (Get chat list; `GET /rooms` returns `room_id`): https://developer.chatwork.com/reference/get-rooms
14. n8n Docs — Export and import (three-dots menu → Import from File): https://docs.n8n.io/build/manage-workflows/export-and-import.md
15. n8n Docs — Configure workflow settings (Error Workflow, Timezone): https://docs.n8n.io/build/manage-workflows/configure-workflow-settings.md
16. n8n Docs — Handle errors gracefully (how to set the Error Workflow): https://docs.n8n.io/build/flow-logic/handle-errors-gracefully.md
17. n8n Docs — Gmail Trigger (Simplify, Search, Read Status, Max Emails per Poll): https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.gmailtrigger.md / Gmail Help — Refine searches in Gmail (search operators): https://support.google.com/mail/answer/7190?hl=en
18. n8n Docs — Schedule Trigger (publishing required, timezone handling, field names of the Days interval): https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger.md
19. n8n Docs — Save and publish workflows / Create and run workflows / Types of executions (Publish; manual vs production executions): https://docs.n8n.io/build/understand-workflows/save-and-publish-workflows.md / https://docs.n8n.io/build/understand-workflows/create-and-run-workflows.md / https://docs.n8n.io/build/understand-workflows/understand-executions/types-of-executions.md
20. n8n Docs — Error Trigger (does not fire on manual runs. The page reads as if an Error Workflow need not be published, but on the author's self-hosted n8n 2.40.5 **an unpublished Error Workflow was not invoked**, so this guide requires publishing it. §4.4 step 6): https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.errortrigger.md
21. n8n Docs — Google Drive Trigger and Common issues (behaviour on manual execution, 401, multiple files): https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.googledrivetrigger.md / https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.googledrivetrigger/common-issues.md
22. n8n Docs — Gmail Trigger Common issues (401): https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.gmailtrigger/common-issues.md
23. n8n Docs — Pin and mock data (Unpin; ignored in production runs): https://docs.n8n.io/build/work-with-data/pin-and-mock-data.md
24. n8n Docs — HTTP Request credentials (Header Auth Name / Value): https://docs.n8n.io/integrations/builtin/credentials/httprequest.md
25. Google Drive Help — Upload files & folders to Google Drive (where the "Convert uploads to Google Docs editor format" setting is): https://support.google.com/drive/answer/2424368?hl=en
26. Google Docs Editors Help — Format numbers in a spreadsheet (Format → Number): https://support.google.com/docs/answer/56470?hl=en
27. n8n Docs — Work with nodes (Deactivate in the node context menu): https://docs.n8n.io/build/understand-workflows/workflow-components/work-with-nodes.md

Pages that could not be fetched: Slack Help "Add an app to a channel" and Chatwork Help "How to find a room ID" (both are stated in the text above, with alternative official sources given). The verification record for the LINE / Chatwork API details (URLs, header names, body formats) is also in the "External APIs" table of `ASSUMPTIONS.md`.

The design and its rationale are in `DESIGN.md`, the acceptance tests in `tests/CASES.md`, and the expected values for the bundled data in `fixtures/README.md`.
