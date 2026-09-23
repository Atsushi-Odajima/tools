#!/usr/bin/env python3
"""Build workflow.json and error-handler.json for template 01 (入金消込 / Bank Deposit Reconciliation).

Deterministic generator (Python 3 standard library only):
  * embeds templates/01-bank-reconciliation/code/*.js verbatim as `jsCode` of the matching Code nodes (ASSUMPTIONS A15)
  * embeds the Config node exactly per DESIGN.md §4 (Set v3.5 JSON-output mode, include all input fields,
    SOURCE = {{ $prevNode.name }}), MESSAGES restricted to recon_summary + error_notice of shared/messages.*.json,
    MAIL_PARSERS from fixtures/mail_parsers.example.json, CSV_MAPPING defaults (bank_A entry of csv_mapping.examples.json)
  * node ids are uuid5 with a fixed namespace, node names / settings / connections / sticky groups per DESIGN.md §2
  * sticky notes: text block above the node rows (>= 48 px clearance), Config key tables in a reference row below the flow;
    note sizes come from TEXT_SIZE (text heights measured in n8n 2.40.5 with Playwright — re-measure after editing a text)
  * asserts: every node type starts with "n8n-nodes-base.", the CLAUDE.md §1-2 secret grep matches nothing, no credentials
    block is present, every Code node's jsCode equals its source file, and the output is byte-identical across runs

usage: python3 build/build_workflow.py [--check]    (--check: build into memory and compare with the files on disk)
"""
import json
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(TPL))
CODE = os.path.join(TPL, 'code')
FX = os.path.join(TPL, 'fixtures')

MAIN_NAME = '[Odaji] 01 Bank Deposit Reconciliation v1.0.0'
ERR_NAME = '[Odaji] 01 Error Handler v1.0.0'
NS = uuid.uuid5(uuid.NAMESPACE_URL, 'https://github.com/Atsushi-Odajima/tools/templates/01-bank-reconciliation')
SETTINGS = {'executionOrder': 'v1', 'timezone': 'Asia/Tokyo', 'saveManualExecutions': True, 'saveExecutionProgress': True}
# CLAUDE.md §1-2 pattern, assembled from pieces so that this source file does not match its own grep
SECRET_RE = re.compile('|'.join(['sk_' + '(live|test)', 'whsec' + '_', 'xoxb' + '-', 'Bearer ' + '[A-Za-z0-9]', '@gmail' + r'\.com']))

# sticky colours measured in n8n 2.40.5 (ASSUMPTIONS A14): 1 = yellow, 3 = red, 4 = green, 5 = blue
YELLOW, RED, GREEN, BLUE = 1, 3, 4, 5
CFG = "$('Config').first().json"


def read(path, mode='r'):
    with open(path, mode, encoding=None if 'b' in mode else 'utf-8', newline='' if 'b' not in mode else None) as f:
        return f.read()


def uid(*parts):
    return str(uuid.uuid5(NS, '/'.join(parts)))


# ----------------------------------------------------------------------------------------------------------------------
# Config (DESIGN.md §4). Every tunable lives here; REPLACE_ME_* placeholders only. Order = the DESIGN table.
# ----------------------------------------------------------------------------------------------------------------------
msg_ja = json.loads(read(os.path.join(ROOT, 'shared', 'messages.ja.json')))
msg_en = json.loads(read(os.path.join(ROOT, 'shared', 'messages.en.json')))
MAIL_PARSERS = json.loads(read(os.path.join(FX, 'mail_parsers.example.json')))['MAIL_PARSERS']
CSV_MAPPING = json.loads(read(os.path.join(FX, 'csv_mapping.examples.json')))['bank_A_sjis.csv']
LEGAL_ENTITY_TOKENS = ['カ)', '(カ', 'ユ)', '(ユ', 'ド)', '(ド', 'シヤ)', '(シヤ', 'ザイ)', '(ザイ', 'ガク)', '(ガク', 'イ)', '(イ', 'ホ)', '(ホ',
                       '株式会社', '有限会社', '合同会社', '合名会社', '合資会社', '一般社団法人', '一般財団法人', '医療法人', '学校法人', '社会福祉法人',
                       'カブシキガイシヤ', 'カブシキカイシヤ', 'ユウゲンガイシヤ', 'ゴウドウガイシヤ', 'イツパンシヤダンホウジン', 'イリヨウホウジン',
                       '振込', 'フリコミ', 'ゴフリコミ']
LINE_API_URL = 'https://api.line.me/v2/bot/message/push'
CHATWORK_API_BASE_URL = 'https://api.chatwork.com/v2'
GMAIL_QUERY = 'subject:(入金 OR Deposit) newer_than:1d'

# (key, default value, JA meaning, EN meaning). `MESSAGES` and `SOURCE` are documented but generated.
CONFIG_KEYS = [
    ('TZ', 'Asia/Tokyo', '日付判定と `imported_at` のタイムゾーン。ワークフロー Settings の Timezone とも一致させる',
     'Time zone for date handling and `imported_at`; keep equal to the workflow Timezone setting'),
    ('LANG', 'ja', '通知文面の言語 `ja` / `en`', 'Notification language: `ja` / `en`'),
    ('SHEET_ID', 'REPLACE_ME_SHEET_ID', 'スプレッドシートの ID（URL の `/d/<ID>/`）', 'Spreadsheet ID from the URL (`/d/<ID>/`)'),
    ('SHEET_INVOICES', 'invoices', '請求一覧のシート名', 'Sheet name for invoices'),
    ('SHEET_TRANSACTIONS', 'transactions', '取引台帳のシート名', 'Sheet name for the transaction ledger'),
    ('DRIVE_FOLDER_ID', 'REPLACE_ME_DRIVE_FOLDER_ID', '監視フォルダ ID。**参照用**。実値は `Watch Drive Folder` ノードにも入れる（トリガーは Config を参照できない）',
     'Watched folder ID, **for reference only**: the live value goes into the `Watch Drive Folder` node (triggers cannot read Config)'),
    ('GMAIL_QUERY', GMAIL_QUERY, 'Gmail 検索式。**参照用**。実値は `Watch Gmail Inbox` ノードの Search に入れる。既定は同梱 fixture 2 通の件名に一致する（`subject:` は本文を見ない）',
     'Gmail search, **for reference only**: the live value goes into the `Watch Gmail Inbox` node. The default matches both bundled fixture subjects (`subject:` does not search the body)'),
    ('RUN_AT', '09:00', '再突合の時刻（JST）。**参照用**。実値は `Run Daily Rematch` ノードに入れる',
     'Daily re-match time (JST), **for reference only**: the live value goes into the `Run Daily Rematch` node'),
    ('TRIGGERS_ENABLED', {'drive': True, 'gmail': True, 'schedule': True},
     '3 系統のトリガーの ON／OFF。`Route by Source` が false の系統を `Skip Disabled Trigger` に落とす（OFF でもトリガーのポーリングは続く）',
     'Per-trigger on/off. `Route by Source` drops disabled sources into `Skip Disabled Trigger` (a disabled trigger still polls)'),
    ('CSV_MAPPING', CSV_MAPPING,
     '銀行 CSV の列対応：`date_col` 取引日 / `payer_col` 振込名義（摘要）/ `deposit_col` 入金額（空・0 の行は無視）/ `withdraw_col` 出金額（説明用、無ければ `""`）/ `memo_col` メモ列（無ければ `""`）/ `skip_rows` 見出しより前に捨てる行数 / `date_format` `auto`・`yyyy/MM/dd`・`yyyyMMdd`・`yyyy-MM-dd` / `encoding` `shift_jis`・`utf-8`・`auto`（UTF-8 BOM があれば常に UTF-8）。銀行 B 形式の例は `fixtures/csv_mapping.examples.json`',
     'Bank CSV column mapping: `date_col` date / `payer_col` remitter (description) / `deposit_col` deposit (empty or 0 rows are ignored) / `withdraw_col` withdrawal (informational, `""` if none) / `memo_col` optional memo column (`""` if none) / `skip_rows` rows discarded before the header / `date_format` `auto`, `yyyy/MM/dd`, `yyyyMMdd`, `yyyy-MM-dd` / `encoding` `shift_jis`, `utf-8`, `auto` (a UTF-8 BOM always wins). Bank format B example: `fixtures/csv_mapping.examples.json`'),
    ('MAIL_PARSERS', MAIL_PARSERS,
     '入金通知メールの解析ルール（先頭から順に試し、最初に一致したものを使う）：`name` 識別名 / `from_match` 差出人に含まれる文字列（大文字小文字無視）/ `subject_match` 件名に含まれる文字列 / `amount_regex`・`payer_regex`・`date_regex` NFKC 正規化後の本文に対する正規表現。**第 1 グループ**が値。`date_regex` が無ければメールの受信日。正本は `fixtures/mail_parsers.example.json`',
     'Mail parser rules, first match wins: `name` label / `from_match` substring of From (case-insensitive) / `subject_match` substring of Subject / `amount_regex`, `payer_regex`, `date_regex` JavaScript regexes on the NFKC-normalized body, **group 1** = value; without `date_regex` the email date is used. Source of truth: `fixtures/mail_parsers.example.json`'),
    ('LEGAL_ENTITY_TOKENS', LEGAL_ENTITY_TOKENS,
     '名義から除去する法人格等。`X)` は先頭のみ、`(X` は末尾のみ、それ以外はどこでも除去（全角で追加しても可）',
     'Tokens stripped from remitter names: `X)` only at the start, `(X` only at the end, others anywhere (full-width input is accepted)'),
    ('STRIP_LEADING_DIGITS', True, '名義先頭の数字列（振込人番号・支店コード）を除去', 'Strip a leading run of digits (remitter / branch code)'),
    ('FEE_SET', [110, 165, 220, 275, 330, 440, 550, 660, 770, 880], '先方負担の振込手数料として許容する差額（円）', 'Accepted fee differences in yen (fee deducted by the payer)'),
    ('NAME_MIN_CONTAINS', 3, '包含一致に必要な最小文字数（短い方に適用）', 'Minimum characters for a containment name match (applied to the shorter name)'),
    ('NOTIFY_CHANNELS', ['slack'], '`slack` / `email` / `line` / `chatwork` の組合せ（配列）。空なら通知しない', 'Any combination of `slack` / `email` / `line` / `chatwork` (array). Empty = no notification'),
    ('SLACK_CHANNEL', 'REPLACE_ME_SLACK_CHANNEL_ID', '投稿先チャンネル ID（`C0…`）または `#name`', 'Slack channel ID (`C0…`) or `#name`'),
    ('NOTIFY_EMAIL_TO', 'replace-me@example.com', '通知メールの宛先', 'Notification email recipient'),
    ('LINE_TO_USER_ID', 'REPLACE_ME_LINE_USER_ID', 'LINE push の宛先 userId', 'LINE recipient userId'),
    ('CHATWORK_ROOM_ID', 'REPLACE_ME_CHATWORK_ROOM_ID', 'Chatwork のルーム ID', 'Chatwork room ID'),
    ('LINE_API_URL', LINE_API_URL, 'LINE Messaging API push の URL。**API をプロキシ経由にする場合以外は変更しない**', 'LINE Messaging API push URL. **Do not change unless you proxy the API**'),
    ('CHATWORK_API_BASE_URL', CHATWORK_API_BASE_URL, 'Chatwork API のベース URL（`/rooms/{room_id}/messages` を後ろに付ける）。**API をプロキシ経由にする場合以外は変更しない**',
     'Chatwork API base URL (`/rooms/{room_id}/messages` is appended). **Do not change unless you proxy the API**'),
    ('NOTIFY_MAX_LINES', 40, '通知の各セクションに載せる明細の上限行数。超過分は「…他 N 件」', 'Max detail lines per notification section; the rest becomes "… and N more"'),
    ('MESSAGES', None, '通知文面（`shared/messages.*.json` の `recon_summary` と `error_notice`、`ja` / `en`）。`LANG` で選ぶ。文言を変えるときはここを編集',
     'Notification copy (`recon_summary` and `error_notice` from `shared/messages.*.json`, `ja` / `en`), selected by `LANG`; edit here to change wording'),
    ('SOURCE', None, '自動設定 `{{ $prevNode.name }}`（発火したトリガー名）。**変更しない**', 'Set automatically to `{{ $prevNode.name }}` (the trigger that fired). **Do not change**'),
]

MESSAGES = {'ja': {'recon_summary': msg_ja['recon_summary'], 'error_notice': msg_ja['error_notice']},
            'en': {'recon_summary': msg_en['recon_summary'], 'error_notice': msg_en['error_notice']}}


def main_config():
    cfg = {}
    for key, default, _ja, _en in CONFIG_KEYS:
        if key == 'MESSAGES':
            cfg[key] = MESSAGES
        elif key == 'SOURCE':
            cfg[key] = '{{ $prevNode.name }}'
        else:
            cfg[key] = default
    return cfg


ERR_CONFIG_KEYS = ['LANG', 'NOTIFY_CHANNELS', 'SLACK_CHANNEL', 'NOTIFY_EMAIL_TO', 'LINE_TO_USER_ID', 'CHATWORK_ROOM_ID',
                   'LINE_API_URL', 'CHATWORK_API_BASE_URL']


def error_config():
    full = main_config()
    cfg = {k: full[k] for k in ERR_CONFIG_KEYS}
    cfg['MESSAGES'] = {'ja': {'error_notice': msg_ja['error_notice']}, 'en': {'error_notice': msg_en['error_notice']}}
    return cfg


def json_output(cfg):
    """Set v3.5 JSON-output text. The `=` prefix makes it an expression template: `{{ $prevNode.name }}` is evaluated, everything
    else is literal. json.dumps(indent=2) never produces `{{` or `}}`, so the copy / regexes are passed through untouched."""
    text = json.dumps(cfg, ensure_ascii=False, indent=2)
    assert '{{' not in text.replace('{{ $prevNode.name }}', '') and '}}' not in text.replace('{{ $prevNode.name }}', ''), 'JSON text must not contain {{ / }}'
    return '=' + text


# ----------------------------------------------------------------------------------------------------------------------
# node helpers
# ----------------------------------------------------------------------------------------------------------------------
def node(wf, name, ntype, version, pos, params, **settings):
    n = {'id': uid(wf, name), 'name': name, 'type': 'n8n-nodes-base.' + ntype, 'typeVersion': version,
         'position': list(pos), 'parameters': params}
    for k in ('executeOnce', 'alwaysOutputData', 'retryOnFail', 'maxTries', 'waitBetweenTries', 'onError'):
        if k in settings:
            n[k] = settings[k]
    return n


def code_node(wf, name, pos, js_file):
    return node(wf, name, 'code', 2, pos, {'mode': 'runOnceForAllItems', 'jsCode': read(os.path.join(CODE, js_file))})


def cond(wf, nname, i, left, op_type, op, right='', single=False, right_type=None):
    o = {'type': op_type, 'operation': op}
    if single:
        o['singleValue'] = True
    if right_type:
        o['rightType'] = right_type
    return {'id': uid(wf, nname, 'cond', str(i)), 'leftValue': left, 'rightValue': right, 'operator': o}


def filter_(conditions, combinator='and', case_sensitive=True):
    return {'options': {'caseSensitive': case_sensitive, 'leftValue': '', 'typeValidation': 'strict', 'version': 3},
            'conditions': conditions, 'combinator': combinator}


def if_channel(wf, name, channel, pos):
    return node(wf, name, 'if', 2.3, pos, {
        'conditions': filter_([cond(wf, name, 0, '={{ %s.NOTIFY_CHANNELS }}' % CFG, 'array', 'contains', channel, right_type='any')]),
        'options': {}})


def sheets_read(wf, name, sheet_key, pos):
    return node(wf, name, 'googleSheets', 4.7, pos, {
        'authentication': 'oAuth2', 'resource': 'sheet', 'operation': 'read',
        'documentId': {'__rl': True, 'mode': 'id', 'value': '={{ %s.SHEET_ID }}' % CFG},
        'sheetName': {'__rl': True, 'mode': 'name', 'value': '={{ %s.%s }}' % (CFG, sheet_key)},
        'options': {'outputFormatting': {'values': {'general': 'UNFORMATTED_VALUE', 'date': 'FORMATTED_STRING'}}}},
        executeOnce=True, alwaysOutputData=True, retryOnFail=True, maxTries=3, waitBetweenTries=2000)


def sheets_upsert(wf, name, sheet_key, match_col, pos):
    return node(wf, name, 'googleSheets', 4.7, pos, {
        'authentication': 'oAuth2', 'resource': 'sheet', 'operation': 'appendOrUpdate',
        'documentId': {'__rl': True, 'mode': 'id', 'value': '={{ %s.SHEET_ID }}' % CFG},
        'sheetName': {'__rl': True, 'mode': 'name', 'value': '={{ %s.%s }}' % (CFG, sheet_key)},
        'columns': {'mappingMode': 'autoMapInputData', 'value': None, 'matchingColumns': [match_col], 'schema': []},
        'options': {'cellFormat': 'RAW', 'handlingExtraData': 'ignoreIt'}},
        retryOnFail=True, maxTries=3, waitBetweenTries=2000)


def notify_nodes(wf, x, ys, continue_on_error):
    """Notify Slack / Email / LINE / Chatwork (DESIGN §2.3 #25–28). Credentials are selected by the buyer per SETUP; no block here."""
    s = dict(retryOnFail=True, maxTries=3, waitBetweenTries=2000)
    if continue_on_error:
        s['onError'] = 'continueErrorOutput'
    return [
        node(wf, 'Notify Slack', 'slack', 2.7, (x, ys[0]), {
            'authentication': 'accessToken', 'resource': 'message', 'operation': 'post', 'select': 'channel',
            'channelId': {'__rl': True, 'mode': 'id', 'value': '={{ %s.SLACK_CHANNEL }}' % CFG},
            'messageType': 'block',
            'blocksUi': '={{ JSON.stringify({ blocks: $json.slack_blocks }) }}',
            'text': '={{ $json.title }}',
            'otherOptions': {'includeLinkToWorkflow': False}}, **s),   # default true would append the buyer's n8n URL + workflow id as an extra block
        node(wf, 'Notify Email', 'gmail', 2.2, (x, ys[1]), {
            'authentication': 'oAuth2', 'resource': 'message', 'operation': 'send',
            'sendTo': '={{ %s.NOTIFY_EMAIL_TO }}' % CFG,
            'subject': '={{ $json.title }}',
            'emailType': 'text',
            'message': '={{ $json.body_text }}',
            'options': {'appendAttribution': False}}, **s),
        node(wf, 'Notify LINE', 'httpRequest', 4.5, (x, ys[2]), {
            'method': 'POST',
            'url': '={{ %s.LINE_API_URL }}' % CFG,
            'authentication': 'genericCredentialType', 'genericAuthType': 'httpHeaderAuth',
            'sendBody': True, 'contentType': 'json', 'specifyBody': 'json',
            'jsonBody': "={{ JSON.stringify({ to: %s.LINE_TO_USER_ID, messages: [{ type: 'text', text: $json.line_text }] }) }}" % CFG,
            'options': {'timeout': 10000}}, **s),
        node(wf, 'Notify Chatwork', 'httpRequest', 4.5, (x, ys[3]), {
            'method': 'POST',
            'url': '={{ %s.CHATWORK_API_BASE_URL }}/rooms/{{ %s.CHATWORK_ROOM_ID }}/messages' % (CFG, CFG),
            'authentication': 'genericCredentialType', 'genericAuthType': 'httpHeaderAuth',
            'sendBody': True, 'contentType': 'form-urlencoded', 'specifyBody': 'keypair',
            'bodyParameters': {'parameters': [{'name': 'body', 'value': '={{ $json.chatwork_text }}'}]},
            'options': {'timeout': 10000}}, **s),
    ]


# ----------------------------------------------------------------------------------------------------------------------
# sticky-note layout: the text block of every note sits ABOVE the node rows it covers, the nodes sit in the lower area
# ----------------------------------------------------------------------------------------------------------------------
GRID = 16                  # n8n 2.x snaps canvas positions to a 16 px grid
TEXT_GAP = 48              # clearance between the bottom of a note's text block and the first node row (>= 40 px)
PAD_BOTTOM = 40            # clearance below the last node row (label included)
LABEL_OVERHANG = 48        # a node label is 192 px wide and centred on the 96 px node box
ROW_GAP = 64               # gap between the node-row notes and the reference row (Caution + Config key tables) below
NODE_H = 144               # node box 96 px + label (measured 123-143 px); exceptions = nodes with named outputs / inputs
NODE_H_EXC = {'Route by Source': 208, 'Route Match Results': 176, 'Merge Notification Results': 356}
# (width, text height) per note. The text height is the rendered height of the markdown block (+ 8 px padding top and
# bottom + 2 px border) measured in n8n 2.40.5 with Playwright at exactly that width; re-measure after editing a text.
TEXT_SIZE = {
    'S1': (480, 794), 'S2': (784, 468), 'S3': (1024, 612), 'S4': (1296, 583), 'S5': (1296, 735), 'S6': (1024, 688),
    'S2K1': (1504, 1455), 'S2K2': (1504, 1501),
    'E1': (480, 544), 'E2': (560, 266), 'E3': (896, 362), 'E2K': (1504, 987),
}


def snap_down(v):
    return (v // GRID) * GRID


def snap_up(v):
    return -((-v) // GRID) * GRID


def sticky(wf, name, color, pos, width, height, ja, en):
    content = '## JA\n' + ja.strip() + '\n\n## EN\n' + en.strip() + '\n'
    return {'id': uid(wf, name), 'name': name, 'type': 'n8n-nodes-base.stickyNote', 'typeVersion': 1,
            'position': list(pos), 'parameters': {'content': content, 'height': height, 'width': width, 'color': color}}


def group_sticky(wf, key, name, color, x, nodes, members, ja, en):
    """Note that covers `members`: text block on top, then TEXT_GAP, then the node rows, then PAD_BOTTOM."""
    width, text_h = TEXT_SIZE[key]
    ns = [n for n in nodes if n['name'] in members]
    assert len(ns) == len(members), name
    left = min(n['position'][0] for n in ns) - LABEL_OVERHANG
    right = max(n['position'][0] for n in ns) + 96 + LABEL_OVERHANG
    assert x <= left and right <= x + width, '%s: nodes %d..%d outside note %d..%d' % (name, left, right, x, x + width)
    top = snap_down(min(n['position'][1] for n in ns) - TEXT_GAP - text_h)
    bottom = snap_up(max(n['position'][1] + NODE_H_EXC.get(n['name'], NODE_H) for n in ns) + PAD_BOTTOM)
    return sticky(wf, name, color, (x, top), width, bottom - top, ja, en)


def text_sticky(wf, key, name, color, pos, ja, en):
    """Note without nodes: exactly as tall as its text (+ grid rounding)."""
    width, text_h = TEXT_SIZE[key]
    return sticky(wf, name, color, pos, width, snap_up(text_h + 8), ja, en)


def bottom_of(stickies):
    return max(s['position'][1] + s['parameters']['height'] for s in stickies)


def connect(conns, src, dst, out_index=0, in_index=0):
    outs = conns.setdefault(src, {'main': []})['main']
    while len(outs) <= out_index:
        outs.append([])
    outs[out_index].append({'node': dst, 'type': 'main', 'index': in_index})


# ----------------------------------------------------------------------------------------------------------------------
# sticky texts (## JA → ## EN). Config note is generated from CONFIG_KEYS so it cannot drift from the JSON.
# ----------------------------------------------------------------------------------------------------------------------
def default_text(v):
    if isinstance(v, (dict, list)) and len(json.dumps(v, ensure_ascii=False)) > 90:
        return '（Config の JSON を参照 / see the JSON）'
    return '`' + json.dumps(v, ensure_ascii=False) + '`'


CONFIG_KEY_SPLIT = 11   # keys 1-11 (TZ .. MAIL_PARSERS) in table note 1/2, the rest (LEGAL_ENTITY_TOKENS .. SOURCE) in 2/2


def config_intro_text():
    ja = ['### Config — 買い手が触るのは **この Config** と入力グループの **トリガー 3 ノード**だけ',
          '`REPLACE_ME_…` と `replace-me@…` を自分の値に置き換える。トークン類（Slack / Google / LINE / Chatwork）は Config に書かず n8n の Credential に登録する。',
          'ワークフロー Settings の Error workflow に `' + ERR_NAME + '` を指定し、そのワークフロー内の Config にも同じ通知設定を入れる。',
          '`TRIGGERS_ENABLED` の 3 キー（`drive` / `gmail` / `schedule`）は `true` / `false`。`Route by Source` は `SOURCE`（トリガー名）と `TRIGGERS_ENABLED.<key>` の AND で振り分け、OFF の系統と未知の `SOURCE` は `Skip Disabled Trigger` で正常終了する。',
          '**全キーの既定値と意味は、下の黄色い「Config キー一覧（1/2）」「（2/2）」に載せている。**']
    en = ['### Config — the buyer edits only **this Config** and the **three trigger nodes** in the Input group',
          'Replace every `REPLACE_ME_…` / `replace-me@…` with your own values. Tokens (Slack / Google / LINE / Chatwork) never go into Config; register them as n8n Credentials.',
          'Set the workflow Settings → Error workflow to `' + ERR_NAME + '` and mirror the notification keys into that workflow\'s Config.',
          '`TRIGGERS_ENABLED` has three booleans (`drive` / `gmail` / `schedule`). `Route by Source` routes on `SOURCE` (trigger name) AND `TRIGGERS_ENABLED.<key>`; disabled sources and unknown `SOURCE` values end in `Skip Disabled Trigger` without an error.',
          '**Every key, its default and its meaning are listed in the yellow "Config keys (1/2)" and "(2/2)" notes below.**']
    return '\n'.join(ja), '\n'.join(en)


def config_keys_text(part):
    keys = CONFIG_KEYS[:CONFIG_KEY_SPLIT] if part == 1 else CONFIG_KEYS[CONFIG_KEY_SPLIT:]
    first, last = keys[0][0], keys[-1][0]
    ja = ['### Config キー一覧（%d/2）— `%s` 〜 `%s`' % (part, first, last),
          '既定値と意味。順序は `Config` ノード（上の黄色グループ）の JSON と同じ。', '',
          '| キー | 既定値 | 意味 |', '|---|---|---|']
    en = ['### Config keys (%d/2) — `%s` … `%s`' % (part, first, last),
          'Defaults and meaning, in the order of the `Config` node JSON (yellow group above).', '',
          '| Key | Default | Meaning |', '|---|---|---|']
    for key, default, mja, men in keys:
        if key == 'MESSAGES':
            d = '（`shared/messages.ja.json` / `messages.en.json`）'
        elif key == 'SOURCE':
            d = '`{{ $prevNode.name }}`'
        else:
            d = default_text(default)
        ja.append('| `%s` | %s | %s |' % (key, d, mja))
        en.append('| `%s` | %s | %s |' % (key, d, men))
    return '\n'.join(ja), '\n'.join(en)


S1_JA = """### 入力 — 3 系統のトリガー
- **Watch Drive Folder**：監視フォルダに CSV が置かれたら起動（毎分ポーリング）。フォルダ ID は **このノードの Folder** に入れる（Config の `DRIVE_FOLDER_ID` は参照用。トリガーは Config より前に動くため式で参照できない）
- **Watch Gmail Inbox**：入金通知メールで起動（5 分ごと、Simplify OFF、既読・未読とも、最大 10 通／回）。検索式は **このノードの Search** に入れる（Config の `GMAIL_QUERY` と同じ値にする）
- **Run Daily Rematch**：毎日 09:00 JST に未消込・曖昧の取引を再突合。時刻は **このノード** で変える（Config の `RUN_AT` と同じ値にする）
- `TRIGGERS_ENABLED` で OFF にした系統は `Route by Source` で `Skip Disabled Trigger` に落ちるだけで、**トリガーノード自体のポーリング（Drive／Gmail API の呼出し）は続く**。呼出しも止めたいときはそのトリガーノードを無効化（Deactivate）する
- トリガーのノード名を変えたら `Route by Source` のルール（`SOURCE` の比較値）も直す"""
S1_EN = """### Input — three triggers
- **Watch Drive Folder**: fires when a CSV is created in the watched folder (polls every minute). Put the folder ID into **this node's Folder** (Config `DRIVE_FOLDER_ID` is a documented mirror; triggers run before Config and cannot read it)
- **Watch Gmail Inbox**: fires on deposit-notification mails (every 5 minutes, Simplify OFF, read and unread, max 10 per poll). Put the search into **this node's Search** (keep it equal to Config `GMAIL_QUERY`)
- **Run Daily Rematch**: re-matches unmatched / ambiguous transactions daily at 09:00 JST. Change the time in **this node** (keep it equal to Config `RUN_AT`)
- A source switched off in `TRIGGERS_ENABLED` only falls through `Route by Source` into `Skip Disabled Trigger`; **the trigger node keeps polling (Drive / Gmail API calls continue)**. Deactivate the trigger node to stop the calls as well
- If you rename a trigger node, update the matching rule (`SOURCE` value) in `Route by Source`"""

S3_JA = """### 取込 — CSV とメールを取引（pre-txn）にする
- `Check File Is CSV`：名前が `.csv` で終わるか MIME が `text/csv` / Google スプレッドシートのものだけ通す。それ以外は `Skip Non-CSV File` で正常終了
- `Download File`：Google Drive からバイナリで取得。スプレッドシートに変換されていた場合は UTF-8 の CSV としてエクスポートされ、`Parse Bank CSV` は `CSV_MAPPING.encoding` に関わらず UTF-8 として読む（Drive の変換で既に壊れた文字は直らないので、Drive の「アップロードを変換」は OFF にする）
- `Parse Bank CSV`（Code）：**Shift_JIS の復号は Code ノードの `TextDecoder('shift_jis')`** で行う（Extract From File には Shift_JIS が無い）。UTF-8 BOM は除去、`CSV_MAPPING.skip_rows` 行を捨ててから見出しを読む。出金行・入金額が空／0 の行は無視。列が見つからなければ明示的に失敗する（黙って 0 件にしない）。同じポーリングで複数の CSV が届いた場合は全ファイルを解析する（`file_stats` はファイルごと）
- `Parse Mail`（Code）：`MAIL_PARSERS` を先頭から試し、最初に一致したパーサで本文（NFKC 正規化後）から金額・名義・日付を抽出。一致しない／取れないメールは警告として通知に出す。自行の通知に合わせて `fixtures/mail_parsers.example.json` を参考に正規表現を調整する
- `Collect Transactions`（Code）：3 経路の合流点。常に 1 アイテム `{ source, txns[], warnings[] }` を返す"""
S3_EN = """### Intake — CSV and mail → pre-transactions
- `Check File Is CSV`: passes only files whose name ends in `.csv` or whose MIME type is `text/csv` / a Google Sheet; anything else ends in `Skip Non-CSV File` without an error
- `Download File`: downloads the file as binary from Google Drive; a converted Google Sheet is exported as UTF-8 CSV and `Parse Bank CSV` decodes it as UTF-8 regardless of `CSV_MAPPING.encoding` (characters already broken by Drive's conversion are not repaired, so turn Drive's "convert uploads" off)
- `Parse Bank CSV` (Code): **Shift_JIS is decoded in the Code node with `TextDecoder('shift_jis')`** (Extract From File has no Shift_JIS). Strips a UTF-8 BOM, discards `CSV_MAPPING.skip_rows` lines before the header, ignores withdrawal rows and rows with an empty / zero deposit, and fails loudly when a mapped column is missing. When several CSVs arrive in the same poll, every file is parsed (one `file_stats` per file)
- `Parse Mail` (Code): tries `MAIL_PARSERS` in order and extracts amount / remitter / date from the NFKC-normalized body with the first matching parser; mails that match no parser or yield no capture become warnings in the notification. Adjust the regexes to your bank's mails using `fixtures/mail_parsers.example.json`
- `Collect Transactions` (Code): merge point of the three paths; always emits one item `{ source, txns[], warnings[] }`"""

S4_JA = """### 突合 — 名義正規化と規則 1〜5
- `Read Invoices` / `Read Transactions`：Google Sheets Get Row(s)、Values (unformatted)。Execute Once（取引数に関わらず 1 回だけ読む）＋ Always Output Data（空シートでも後段を止めない）
- `Normalize Payer`（Code）：**名義正規化と `txn_id`（`日付|金額|正規化名義|正規化メモ`）を決める唯一の場所**。NFKC → ひらがな→カタカナ → `LEGAL_ENTITY_TOKENS` 除去 → 空白・記号除去（`ー` は保持）→ 先頭の数字列除去。`customer_name` と `payer_name_alias` も同じ関数で正規化して比較する
- `Match Invoices`（Code）：`transactions` に既存の `txn_id`、および請求の `matched_txn_ids` に既に記録された `txn_id` は skip（冪等。後者は台帳行だけを書き直す）。規則 1 名義＋金額一致 → `auto`／2 金額のみ一致 1 件 → `amount_only`（要確認）／3a 差額が `FEE_SET` → `fee_deducted`／3b 同一名義 2〜3 件の合計が一意に一致 → `combined`／3c 残額未満 → `partial`／3d 超過・4 候補複数 → `ambiguous`（自動確定しない、候補上位 3 件）／5 該当なし → `unmatched`。**自動確定は 1・2・3a・3b・3c のみ**
- `currency` が `JPY` 以外の請求は対象外にし、`non_jpy_invoice` として警告に出す。`status` が `unpaid` / `partial` 以外の請求は候補にならない
- Schedule 経路は `unmatched` / `ambiguous` の既存行だけを再突合し、変化した行だけ書き戻す
- `Route Match Results`：`_kind` = `invoice_update` / `txn_row` / `summary` を出力 0 / 1 / 2 に分ける"""
S4_EN = """### Matching — name normalization and rules 1–5
- `Read Invoices` / `Read Transactions`: Google Sheets Get Row(s), Values (unformatted), Execute Once (one read per run regardless of transaction count) + Always Output Data (an empty sheet does not stop the run)
- `Normalize Payer` (Code): **the only place that defines name normalization and `txn_id` (`date|amount|normalized name|normalized memo`)**: NFKC → hiragana→katakana → strip `LEGAL_ENTITY_TOKENS` → strip spaces / punctuation (keeps `ー`) → strip leading digits. `customer_name` and `payer_name_alias` are normalized with the same function
- `Match Invoices` (Code): `txn_id`s already in `transactions`, and `txn_id`s already recorded in an invoice's `matched_txn_ids`, are skipped (idempotent; the latter only rewrites the ledger row). Rule 1 name + amount → `auto` / 2 amount only, one candidate → `amount_only` (needs review) / 3a difference in `FEE_SET` → `fee_deducted` / 3b unique 2–3 invoice subset of one payer → `combined` / 3c below remaining → `partial` / 3d overpaid and 4 several candidates → `ambiguous` (never auto-confirmed, top 3 suggested) / 5 nothing → `unmatched`. **Only 1, 2, 3a, 3b and 3c auto-confirm**
- Invoices whose `currency` is not `JPY` are excluded with a `non_jpy_invoice` warning; invoices whose `status` is not `unpaid` / `partial` are never candidates
- The schedule path re-matches only existing `unmatched` / `ambiguous` rows and writes back only those that changed
- `Route Match Results`: splits `_kind` = `invoice_update` / `txn_row` / `summary` into outputs 0 / 1 / 2"""

S5_JA = """### 出力 — シート更新と通知
- `Update Invoices`：`invoices` を `invoice_id` で Append or Update（`status` / `paid_amount` / `paid_date` / `matched_txn_ids` / `match_confidence` / `fee_deducted`）。`Upsert Transactions`：`transactions` を `txn_id` で Append or Update。どちらも **Cell Format: Let n8n format**（文字列を文字列のまま保存）、余分な項目（`_kind`）は無視。**通知より先にシートへ書く**ので、通知が失敗しても再実行は全件 skip で安全
- `Build Notification`（Code）：`MESSAGES[LANG].recon_summary` でサマリ（処理 N 件／自動消込 A／要確認 B／未消込 C）と明細を組む。Drive／Gmail 実行は常に通知、Schedule 実行は変化か取込警告があるときだけ
- 通知チャネルは Config `NOTIFY_CHANNELS`（`slack` / `email` / `line` / `chatwork`）で ON／OFF。`Check … Enabled` が false のチャネルは実行されない
- Credential：`Notify Slack` は Slack の Credential、`Notify Email` は Gmail OAuth2、`Notify LINE` は Header Auth Credential **`LINE Messaging API`**（ヘッダ名 `Authorization`、値は `Bearer ` の後にチャネルアクセストークン）、`Notify Chatwork` は Header Auth Credential **`Chatwork API`**（ヘッダ名 `X-ChatWorkToken`、値は API トークン）。各ノードで選択する
- LINE／Chatwork の URL は Config `LINE_API_URL` / `CHATWORK_API_BASE_URL` から読む（API をプロキシ経由にする場合以外は変更しない）
- **通知は設定した全チャネルを試し、全チャネルが失敗したときだけ** `Check Notification Results` が実行を失敗させて Error Workflow に回す。一部失敗は `Check Notification Results` の出力（`channels_failed`）と実行ログで分かる
- **使わないチャネルの `Notify …` ノードは無効化（右クリック → Deactivate）するか Credential を選ぶ。** 有効化（Publish）時に n8n は有効な全ノードの Credential を検証するため、未設定のままでは `Missing required credential` で有効化できない。無効化したノードは入力をそのまま通すので、そのチャネルを `NOTIFY_CHANNELS` に残すと `Check Notification Results` が「失敗チャネル」（`notify node disabled or not executed`）として数える。無効化したチャネルは `NOTIFY_CHANNELS` からも外す"""
S5_EN = """### Output — sheet writes and notifications
- `Update Invoices`: Append or Update on `invoices` matched by `invoice_id` (`status` / `paid_amount` / `paid_date` / `matched_txn_ids` / `match_confidence` / `fee_deducted`). `Upsert Transactions`: Append or Update on `transactions` matched by `txn_id`. Both use **Cell Format: Let n8n format** (strings stay strings) and ignore extra fields (`_kind`). **Sheets are written before the notification**, so a re-run after a failed notification safely skips everything
- `Build Notification` (Code): builds the summary (processed N / auto-matched A / needs review B / unmatched C) and detail lines from `MESSAGES[LANG].recon_summary`. Drive / Gmail runs always notify; schedule runs only when something changed or an intake warning exists
- Channels are switched on in Config `NOTIFY_CHANNELS` (`slack` / `email` / `line` / `chatwork`); a channel whose `Check … Enabled` is false never runs
- Credentials: `Notify Slack` uses your Slack credential, `Notify Email` Gmail OAuth2, `Notify LINE` a Header Auth credential named **`LINE Messaging API`** (header `Authorization`, value `Bearer ` followed by the channel access token), `Notify Chatwork` a Header Auth credential named **`Chatwork API`** (header `X-ChatWorkToken`, value = the API token). Select them in each node
- LINE / Chatwork URLs come from Config `LINE_API_URL` / `CHATWORK_API_BASE_URL` (do not change unless you proxy the API)
- **Every configured channel is attempted; only when all of them fail** does `Check Notification Results` fail the run and hand it to the Error Workflow. A partial failure shows in that node's output (`channels_failed`) and in the execution log
- **Disable the `Notify …` nodes of channels you do not use (right-click → Deactivate) or assign a credential.** Publishing validates the credentials of every enabled node, so an unassigned node blocks activation with `Missing required credential`. A disabled node passes its input through unchanged, so a channel that stays in `NOTIFY_CHANNELS` while its node is disabled is reported by `Check Notification Results` as a failed channel (`notify node disabled or not executed`); remove disabled channels from `NOTIFY_CHANNELS` too"""

S6_JA = """### 注意 — 導入前に必ず読む
- **振込名義はカナで届く。** `invoices.payer_name_alias` に振込名義（カナ、カンマ区切り）を入れないと自動消込率が大きく落ちる。漢字の `customer_name` だけでは一致しない
- **同姓同名**は起きる。だから金額一致を必須にしている。金額のみ一致（規則 2）は通知の「要確認」で目視する
- **銀行 CSV は月をまたぐと形式が変わる**ことがある（見出し行の有無・説明行）。`CSV_MAPPING.skip_rows` と列見出しを見直す
- **曖昧・未消込は自動確定しない。** シートの `invoices.status` / `paid_amount` と `transactions.status`（`matched` か `ignored`）を人が直す。`ignored` は再突合の対象外
- **Error Workflow の設定**：Settings → Error workflow に `""" + ERR_NAME + """` を選ぶ → 保存 → 本体を有効化（Activate）。Error Trigger は自動実行でしか発火しない。Error Workflow 側の Config にも通知設定を入れる
- **Error Workflow 自身も有効化（Publish）する。** n8n 2.40.5 では有効化されていない Error Workflow は呼び出されない（ログに `is not active and cannot be executed`）。有効化には Error Workflow 側の `Notify …` でも Credential を選ぶか、使わないチャネルのノードを無効化する必要がある
- 設定は Config だけでは足りない 3 か所：`Watch Drive Folder`（フォルダ）、`Watch Gmail Inbox`（検索式）、`Run Daily Rematch`（時刻）
- 通貨は JPY のみ。`transactions` は毎回全件読むので 1 万行を超えたら年次でシートを分ける"""
S6_EN = """### Caution — read before going live
- **Remitter names arrive in katakana.** Fill `invoices.payer_name_alias` (katakana, comma-separated) or the auto-match rate drops sharply; a kanji `customer_name` alone does not match
- **People share names**, which is why an amount match is mandatory; amount-only matches (rule 2) are listed under "needs review" for a human check
- **Bank CSV layouts drift between months** (header row present or not, extra description lines): review `CSV_MAPPING.skip_rows` and the column headers
- **Ambiguous and unmatched rows are never auto-confirmed.** Fix `invoices.status` / `paid_amount` and `transactions.status` (`matched` or `ignored`) by hand; `ignored` rows are excluded from re-matching
- **Error Workflow setup**: Settings → Error workflow → select `""" + ERR_NAME + """` → save → activate this workflow. The Error Trigger only fires for automatic runs. Mirror the notification keys into the error workflow's Config
- **Publish (activate) the Error Workflow itself as well.** n8n 2.40.5 does not invoke an Error Workflow that is not active (log: `is not active and cannot be executed`). To activate it, select credentials in its `Notify …` nodes too, or disable the nodes of channels you do not use
- Three settings live outside Config: `Watch Drive Folder` (folder), `Watch Gmail Inbox` (search), `Run Daily Rematch` (time)
- JPY only. `transactions` is read in full on every run; split the sheet yearly beyond ~10,000 rows"""

E1_JA = """### 入力 — Error Trigger
本体 `""" + MAIN_NAME + """` の Settings → Error workflow にこのワークフローを指定する。Error Trigger は本体が**自動実行で失敗したとき**だけ発火する（手動実行では発火しない）。このワークフロー自身の Error workflow 設定は空のままにする（無限ループ防止）。
**このワークフロー自身も有効化（Publish）する。** 有効化されていない Error Workflow は呼び出されない（n8n 2.40.5 実測）。有効化時に `Notify …` 4 ノードの Credential が検証されるので、使わないチャネルのノードは無効化（右クリック → Deactivate）し、`NOTIFY_CHANNELS` からも外す。"""
E1_EN = """### Input — Error Trigger
Select this workflow in Settings → Error workflow of `""" + MAIN_NAME + """`. The Error Trigger fires only when the main workflow **fails in an automatic run** (never for manual runs). Leave this workflow's own Error workflow setting empty (no loops).
**Publish (activate) this workflow as well.** An Error Workflow that is not active is never invoked (measured in n8n 2.40.5). Activation validates the credentials of the four `Notify …` nodes, so disable the nodes of channels you do not use (right-click → Deactivate) and remove them from `NOTIFY_CHANNELS`."""


def error_config_intro_text():
    ja = ['### Config — 通知に必要なキーだけ（本体の Config は参照できないため同じ値をここにも入れる）',
          '**キーの既定値と意味は、下の黄色い「Config キー一覧」に載せている。**']
    en = ['### Config — only the notification keys (the main Config is not reachable, so mirror the values here)',
          '**Every key, its default and its meaning are listed in the yellow "Config keys" note below.**']
    return '\n'.join(ja), '\n'.join(en)


def error_config_keys_text():
    keys = {k: (d, ja, en) for k, d, ja, en in CONFIG_KEYS}
    ja = ['### Config キー一覧 — 本体の Config と同じ値を入れる', '', '| キー | 既定値 | 意味 |', '|---|---|---|']
    en = ['### Config keys — mirror the values of the main Config', '', '| Key | Default | Meaning |', '|---|---|---|']
    for k in ERR_CONFIG_KEYS:
        d, mja, men = keys[k]
        ja.append('| `%s` | %s | %s |' % (k, default_text(d), mja))
        en.append('| `%s` | %s | %s |' % (k, default_text(d), men))
    ja.append('| `MESSAGES` | （`shared/messages.*.json` の `error_notice`） | エラー通知の文面（`ja` / `en`） |')
    en.append('| `MESSAGES` | (`error_notice` of `shared/messages.*.json`) | Error notice copy (`ja` / `en`) |')
    return '\n'.join(ja), '\n'.join(en)


E3_JA = """### 出力 — エラー通知
- `Build Error Message`（Code）：`MESSAGES[LANG].error_notice` でワークフロー名・失敗ノード・エラー・実行ログ URL を組む
- チャネルは Config `NOTIFY_CHANNELS` で ON／OFF。Credential は本体と同じ名前のものを各ノードで選ぶ（Slack、Gmail OAuth2、Header Auth `LINE Messaging API` / `Chatwork API`）
- ここの Notify ノードは On Error = Stop（失敗しても次の受け皿は無い）。Merge／Check は置かない"""
E3_EN = """### Output — error notification
- `Build Error Message` (Code): fills `MESSAGES[LANG].error_notice` with the workflow name, failed node, error and execution URL
- Channels are switched on in Config `NOTIFY_CHANNELS`; select the same credentials as in the main workflow in each node (Slack, Gmail OAuth2, Header Auth `LINE Messaging API` / `Chatwork API`)
- The Notify nodes here keep On Error = Stop (there is no further fallback); no Merge / Check node"""


# ----------------------------------------------------------------------------------------------------------------------
# main workflow
# ----------------------------------------------------------------------------------------------------------------------
def build_main():
    wf = MAIN_NAME
    nodes, conns = [], {}
    # --- input (blue) ---
    nodes.append(node(wf, 'Watch Drive Folder', 'googleDriveTrigger', 1, (0, 0), {
        'pollTimes': {'item': [{'mode': 'everyMinute'}]},
        'authentication': 'oAuth2',
        'triggerOn': 'specificFolder',
        'folderToWatch': {'__rl': True, 'mode': 'id', 'value': 'REPLACE_ME_DRIVE_FOLDER_ID'},
        'event': 'fileCreated',
        'options': {}}))
    nodes.append(node(wf, 'Watch Gmail Inbox', 'gmailTrigger', 1.4, (0, 200), {
        'pollTimes': {'item': [{'mode': 'everyX', 'value': 5, 'unit': 'minutes'}]},
        'authentication': 'oAuth2',
        'simple': False,
        'maxResults': 10,
        'filters': {'q': GMAIL_QUERY, 'readStatus': 'both'},
        'options': {}}))
    nodes.append(node(wf, 'Run Daily Rematch', 'scheduleTrigger', 1.4, (0, 400), {
        'rule': {'interval': [{'field': 'days', 'daysInterval': 1, 'triggerAtHour': 9, 'triggerAtMinute': 0}]}}))
    # --- config / routing (yellow) ---
    nodes.append(node(wf, 'Config', 'set', 3.5, (300, 200), {
        'mode': 'raw', 'jsonOutput': json_output(main_config()), 'includeOtherFields': True, 'options': {}}))
    rules = []
    for i, (source, key, out) in enumerate([('Watch Drive Folder', 'drive', 'drive'), ('Watch Gmail Inbox', 'gmail', 'gmail'),
                                            ('Run Daily Rematch', 'schedule', 'schedule')]):
        rules.append({'conditions': filter_([
            cond(wf, 'Route by Source', 2 * i, '={{ $json.SOURCE }}', 'string', 'equals', source),
            cond(wf, 'Route by Source', 2 * i + 1, '={{ $json.TRIGGERS_ENABLED.%s }}' % key, 'boolean', 'true', single=True)]),
            'renameOutput': True, 'outputKey': out})
    nodes.append(node(wf, 'Route by Source', 'switch', 3.4, (560, 200), {
        'rules': {'values': rules},
        'options': {'fallbackOutput': 'extra', 'renameFallbackOutput': 'disabled'}}))
    nodes.append(node(wf, 'Skip Disabled Trigger', 'noOp', 1, (840, 620), {}))
    # --- CSV / mail intake (blue) ---
    nodes.append(node(wf, 'Check File Is CSV', 'if', 2.3, (1100, 0), {
        'conditions': filter_([
            cond(wf, 'Check File Is CSV', 0, '={{ $json.name }}', 'string', 'endsWith', '.csv'),
            cond(wf, 'Check File Is CSV', 1, '={{ $json.mimeType }}', 'string', 'equals', 'text/csv'),
            cond(wf, 'Check File Is CSV', 2, '={{ $json.mimeType }}', 'string', 'equals', 'application/vnd.google-apps.spreadsheet')],
            combinator='or', case_sensitive=False),
        'options': {'ignoreCase': True}}))
    nodes.append(node(wf, 'Skip Non-CSV File', 'noOp', 1, (1360, -180), {}))
    nodes.append(node(wf, 'Download File', 'googleDrive', 3, (1360, 0), {
        'authentication': 'oAuth2', 'resource': 'file', 'operation': 'download',
        'fileId': {'__rl': True, 'mode': 'id', 'value': '={{ $json.id }}'},
        'options': {'binaryPropertyName': 'data', 'googleFileConversion': {'conversion': {'sheetsToFormat': 'text/csv'}}}},
        retryOnFail=True, maxTries=3, waitBetweenTries=2000))
    nodes.append(code_node(wf, 'Parse Bank CSV', (1620, 0), 'parse_bank_csv.js'))
    nodes.append(code_node(wf, 'Parse Mail', (1360, 200), 'parse_mail.js'))
    nodes.append(code_node(wf, 'Collect Transactions', (1880, 200), 'collect_transactions.js'))
    # --- ledger read + matching (yellow) ---
    nodes.append(sheets_read(wf, 'Read Invoices', 'SHEET_INVOICES', (2140, 200)))
    nodes.append(sheets_read(wf, 'Read Transactions', 'SHEET_TRANSACTIONS', (2400, 200)))
    nodes.append(code_node(wf, 'Normalize Payer', (2660, 200), 'normalize_payer.js'))
    nodes.append(code_node(wf, 'Match Invoices', (2920, 200), 'match_invoices.js'))
    nodes.append(node(wf, 'Route Match Results', 'switch', 3.4, (3180, 200), {
        'rules': {'values': [
            {'conditions': filter_([cond(wf, 'Route Match Results', i, '={{ $json._kind }}', 'string', 'equals', kind)]),
             'renameOutput': True, 'outputKey': kind}
            for i, kind in enumerate(['invoice_update', 'txn_row', 'summary'])]},
        'options': {}}))
    # --- output (green) ---
    nodes.append(sheets_upsert(wf, 'Update Invoices', 'SHEET_INVOICES', 'invoice_id', (3460, 0)))
    nodes.append(sheets_upsert(wf, 'Upsert Transactions', 'SHEET_TRANSACTIONS', 'txn_id', (3460, 200)))
    nodes.append(code_node(wf, 'Build Notification', (3460, 400), 'build_notification.js'))
    ifs = [('Check Slack Enabled', 'slack'), ('Check Email Enabled', 'email'), ('Check LINE Enabled', 'line'), ('Check Chatwork Enabled', 'chatwork')]
    ys = [200, 400, 600, 800]
    for (name, ch), y in zip(ifs, ys):
        nodes.append(if_channel(wf, name, ch, (3720, y)))
    notifies = notify_nodes(wf, 3980, ys, continue_on_error=True)
    nodes.extend(notifies)
    nodes.append(node(wf, 'Merge Notification Results', 'merge', 3.2, (4240, 500), {'mode': 'append', 'numberInputs': 8}))
    nodes.append(code_node(wf, 'Check Notification Results', (4500, 500), 'check_notification_results.js'))

    # --- connections (DESIGN §2.1) ---
    for t in ('Watch Drive Folder', 'Watch Gmail Inbox', 'Run Daily Rematch'):
        connect(conns, t, 'Config')
    connect(conns, 'Config', 'Route by Source')
    connect(conns, 'Route by Source', 'Check File Is CSV', 0)
    connect(conns, 'Route by Source', 'Parse Mail', 1)
    connect(conns, 'Route by Source', 'Collect Transactions', 2)
    connect(conns, 'Route by Source', 'Skip Disabled Trigger', 3)
    connect(conns, 'Check File Is CSV', 'Download File', 0)
    connect(conns, 'Check File Is CSV', 'Skip Non-CSV File', 1)
    connect(conns, 'Download File', 'Parse Bank CSV')
    connect(conns, 'Parse Bank CSV', 'Collect Transactions')
    connect(conns, 'Parse Mail', 'Collect Transactions')
    connect(conns, 'Collect Transactions', 'Read Invoices')
    connect(conns, 'Read Invoices', 'Read Transactions')
    connect(conns, 'Read Transactions', 'Normalize Payer')
    connect(conns, 'Normalize Payer', 'Match Invoices')
    connect(conns, 'Match Invoices', 'Route Match Results')
    connect(conns, 'Route Match Results', 'Update Invoices', 0)
    connect(conns, 'Route Match Results', 'Upsert Transactions', 1)
    connect(conns, 'Route Match Results', 'Build Notification', 2)
    for name, _ch in ifs:
        connect(conns, 'Build Notification', name)
    for (name, _ch), n in zip(ifs, notifies):
        connect(conns, name, n['name'], 0)
    for i, n in enumerate(notifies):
        connect(conns, n['name'], 'Merge Notification Results', 0, i)        # success output → inputs 1–4
        connect(conns, n['name'], 'Merge Notification Results', 1, 4 + i)    # error output → inputs 5–8
    connect(conns, 'Merge Notification Results', 'Check Notification Results')

    # --- sticky notes (DESIGN §2.4): text above the node rows; Caution + Config key tables in a reference row below ---
    cfg_ja, cfg_en = config_intro_text()
    k1_ja, k1_en = config_keys_text(1)
    k2_ja, k2_en = config_keys_text(2)
    stickies = [
        group_sticky(wf, 'S1', 'Sticky Note S1 Input', BLUE, -256, nodes, ['Watch Drive Folder', 'Watch Gmail Inbox', 'Run Daily Rematch'], S1_JA, S1_EN),
        group_sticky(wf, 'S2', 'Sticky Note S2 Config', YELLOW, 240, nodes, ['Config', 'Route by Source', 'Skip Disabled Trigger'], cfg_ja, cfg_en),
        group_sticky(wf, 'S3', 'Sticky Note S3 Intake', BLUE, 1040, nodes,
                     ['Check File Is CSV', 'Skip Non-CSV File', 'Download File', 'Parse Bank CSV', 'Parse Mail', 'Collect Transactions'], S3_JA, S3_EN),
        group_sticky(wf, 'S4', 'Sticky Note S4 Matching', YELLOW, 2080, nodes,
                     ['Read Invoices', 'Read Transactions', 'Normalize Payer', 'Match Invoices', 'Route Match Results'], S4_JA, S4_EN),
        group_sticky(wf, 'S5', 'Sticky Note S5 Output', GREEN, 3408, nodes,
                     ['Update Invoices', 'Upsert Transactions', 'Build Notification'] + [i for i, _c in ifs] + [n['name'] for n in notifies]
                     + ['Merge Notification Results', 'Check Notification Results'], S5_JA, S5_EN),
    ]
    row2 = bottom_of(stickies) + ROW_GAP
    stickies.append(text_sticky(wf, 'S6', 'Sticky Note S6 Caution', RED, (-256, row2), S6_JA, S6_EN))
    x = -256 + TEXT_SIZE['S6'][0] + 32
    stickies.append(text_sticky(wf, 'S2K1', 'Sticky Note S2 Config Keys 1', YELLOW, (x, row2), k1_ja, k1_en))
    x += TEXT_SIZE['S2K1'][0] + 32
    stickies.append(text_sticky(wf, 'S2K2', 'Sticky Note S2 Config Keys 2', YELLOW, (x, row2), k2_ja, k2_en))
    return {'name': wf, 'nodes': stickies + nodes, 'connections': conns, 'settings': dict(SETTINGS)}


# ----------------------------------------------------------------------------------------------------------------------
# error handler (DESIGN §2.2)
# ----------------------------------------------------------------------------------------------------------------------
def build_error():
    wf = ERR_NAME
    nodes, conns = [], {}
    nodes.append(node(wf, 'Catch Workflow Error', 'errorTrigger', 1, (0, 300), {}))
    nodes.append(node(wf, 'Config', 'set', 3.5, (300, 300), {
        'mode': 'raw', 'jsonOutput': json_output(error_config()), 'includeOtherFields': True, 'options': {}}))
    nodes.append(code_node(wf, 'Build Error Message', (900, 300), 'build_error_message.js'))   # inside E3 (green), DESIGN §2.3 row E3
    ifs = [('Check Slack Enabled', 'slack'), ('Check Email Enabled', 'email'), ('Check LINE Enabled', 'line'), ('Check Chatwork Enabled', 'chatwork')]
    ys = [0, 200, 400, 600]
    for (name, ch), y in zip(ifs, ys):
        nodes.append(if_channel(wf, name, ch, (1160, y)))
    notifies = notify_nodes(wf, 1420, ys, continue_on_error=False)
    nodes.extend(notifies)
    connect(conns, 'Catch Workflow Error', 'Config')
    connect(conns, 'Config', 'Build Error Message')
    for name, _ch in ifs:
        connect(conns, 'Build Error Message', name)
    for (name, _ch), n in zip(ifs, notifies):
        connect(conns, name, n['name'], 0)
    cfg_ja, cfg_en = error_config_intro_text()
    k_ja, k_en = error_config_keys_text()
    stickies = [
        group_sticky(wf, 'E1', 'Sticky Note E1 Input', BLUE, -256, nodes, ['Catch Workflow Error'], E1_JA, E1_EN),
        group_sticky(wf, 'E2', 'Sticky Note E2 Config', YELLOW, 240, nodes, ['Config'], cfg_ja, cfg_en),
        group_sticky(wf, 'E3', 'Sticky Note E3 Output', GREEN, 848, nodes,
                     ['Build Error Message'] + [i for i, _c in ifs] + [n['name'] for n in notifies], E3_JA, E3_EN),
    ]
    stickies.append(text_sticky(wf, 'E2K', 'Sticky Note E2 Config Keys', YELLOW, (240, bottom_of(stickies) + ROW_GAP), k_ja, k_en))
    return {'name': wf, 'nodes': stickies + nodes, 'connections': conns, 'settings': dict(SETTINGS)}


# ----------------------------------------------------------------------------------------------------------------------
# checks + output
# ----------------------------------------------------------------------------------------------------------------------
def dumps(wf):
    return json.dumps(wf, ensure_ascii=False, indent=2) + '\n'


def check(wf, text):
    names = set()
    for n in wf['nodes']:
        assert n['type'].startswith('n8n-nodes-base.'), 'non built-in node type: ' + n['type']
        assert 'credentials' not in n, 'credentials block present in ' + n['name']
        assert n['name'] not in names, 'duplicate node name ' + n['name']
        names.add(n['name'])
        if n['type'] == 'n8n-nodes-base.code':
            src = {'Parse Bank CSV': 'parse_bank_csv.js', 'Parse Mail': 'parse_mail.js', 'Collect Transactions': 'collect_transactions.js',
                   'Normalize Payer': 'normalize_payer.js', 'Match Invoices': 'match_invoices.js', 'Build Notification': 'build_notification.js',
                   'Check Notification Results': 'check_notification_results.js', 'Build Error Message': 'build_error_message.js'}[n['name']]
            assert n['parameters']['jsCode'] == read(os.path.join(CODE, src)), 'jsCode differs from code/' + src
            code_lines = [ln.split('//')[0] for ln in n['parameters']['jsCode'].split('\n')]   # ignore comments
            assert not any(re.search(r'\brequire\s*\(', ln) for ln in code_lines), 'require() in ' + n['name']
        if n['type'] == 'n8n-nodes-base.stickyNote':
            c = n['parameters']['content']
            assert c.startswith('## JA\n') and '\n## EN\n' in c, 'sticky order JA → EN: ' + n['name']
    for src, outs in wf['connections'].items():
        assert src in names, 'connection from unknown node ' + src
        for out in outs['main']:
            for c in out:
                assert c['node'] in names, 'connection to unknown node ' + c['node']
    m = SECRET_RE.search(text)
    assert m is None, 'secret grep matched: ' + m.group(0)
    assert 'REPLACE_ME_SHEET_ID' in text or wf['name'] == ERR_NAME


def main():
    outputs = {os.path.join(TPL, 'workflow.json'): build_main(), os.path.join(TPL, 'error-handler.json'): build_error()}
    check_only = '--check' in sys.argv
    for path, wf in outputs.items():
        text = dumps(wf)
        check(wf, text)
        assert dumps(build_main() if wf['name'] == MAIN_NAME else build_error()) == text, 'build is not deterministic'
        if check_only:
            assert read(path) == text, 'on-disk file differs: ' + path
            print('OK (unchanged)', os.path.relpath(path, TPL), len(text), 'bytes')
        else:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(text)
            print('wrote', os.path.relpath(path, TPL), len(text), 'bytes,', len(wf['nodes']), 'nodes')


if __name__ == '__main__':
    main()
