#!/usr/bin/env python3
"""Build unit-test scenarios for the Build Notification / Build Error Message / Check Notification Results Code nodes.

JA: shared/messages.ja.json / messages.en.json（文面の原本）と fixtures/bank_A_sjis.csv（Shift_JIS の実ファイル）から
    tests/unit/scenarios/{build_notification,build_error_message,check_notification_results}/*.json を生成する。
    A の summary は CSV の入金行（日付・摘要・入金額）を実バイト列から読み、消込結果（請求 ID・理由・候補）は
    fixtures/README.md §4 の表を手で写したもの。"expect" の本文は tests/CASES.md §3 の全文と messages.*.json から
    手で書き起こした（コードの出力からは作らない）。README の raw 名義が実 CSV と食い違えば生成を止める。
EN: Generates the scenarios from the real message files and the real Shift_JIS CSV. The A summary takes date / remitter / amount
    from the CSV bytes; the matching outcome per row (invoice ids, reason, candidates) is transcribed from fixtures/README.md §4;
    every expected body is transcribed by hand from tests/CASES.md §3 and shared/messages.*.json (never derived from the code
    under test). The build aborts if a transcribed raw remitter disagrees with the CSV.

Run:  python3 build-notify-scenarios.py        (idempotent; the generated JSON files are committed alongside)
"""
import csv
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
REPO = os.path.abspath(os.path.join(TPL, '..', '..'))
FIX = os.path.join(TPL, 'fixtures')
NOW = '2026-09-23T09:00:00+09:00'
DATE = '2026-09-23'

with open(os.path.join(REPO, 'shared', 'messages.ja.json'), encoding='utf-8') as f:
    MSG_JA = json.load(f)
with open(os.path.join(REPO, 'shared', 'messages.en.json'), encoding='utf-8') as f:
    MSG_EN = json.load(f)
# Config.MESSAGES carries only the two blocks template 01 uses (DESIGN.md §4 "MESSAGES")
MESSAGES = {
    'ja': {'recon_summary': MSG_JA['recon_summary'], 'error_notice': MSG_JA['error_notice']},
    'en': {'recon_summary': MSG_EN['recon_summary'], 'error_notice': MSG_EN['error_notice']},
}

# DESIGN.md §4 defaults (MAIL_PARSERS source of truth: fixtures/mail_parsers.example.json)
with open(os.path.join(FIX, 'mail_parsers.example.json'), encoding='utf-8') as f:
    PARSERS = json.load(f)['MAIL_PARSERS']
BASE_CFG = {
    'TZ': 'Asia/Tokyo', 'LANG': 'ja', 'SHEET_ID': 'REPLACE_ME_SHEET_ID', 'SHEET_INVOICES': 'invoices',
    'SHEET_TRANSACTIONS': 'transactions', 'DRIVE_FOLDER_ID': 'REPLACE_ME_DRIVE_FOLDER_ID',
    'GMAIL_QUERY': 'subject:(入金 OR Deposit) newer_than:1d', 'RUN_AT': '09:00',
    'TRIGGERS_ENABLED': {'drive': True, 'gmail': True, 'schedule': True},
    'CSV_MAPPING': {'date_col': '日付', 'payer_col': '摘要', 'deposit_col': '入金額', 'withdraw_col': '出金額',
                    'memo_col': '', 'skip_rows': 0, 'date_format': 'auto', 'encoding': 'shift_jis'},
    'MAIL_PARSERS': PARSERS,
    'LEGAL_ENTITY_TOKENS': ['カ)', '(カ', 'ユ)', '(ユ', 'ド)', '(ド', 'シヤ)', '(シヤ', 'ザイ)', '(ザイ', 'ガク)', '(ガク', 'イ)', '(イ',
                            'ホ)', '(ホ', '株式会社', '有限会社', '合同会社', '合名会社', '合資会社', '一般社団法人', '一般財団法人',
                            '医療法人', '学校法人', '社会福祉法人', 'カブシキガイシヤ', 'カブシキカイシヤ', 'ユウゲンガイシヤ',
                            'ゴウドウガイシヤ', 'イツパンシヤダンホウジン', 'イリヨウホウジン', '振込', 'フリコミ', 'ゴフリコミ'],
    'STRIP_LEADING_DIGITS': True,
    'FEE_SET': [110, 165, 220, 275, 330, 440, 550, 660, 770, 880],
    'NAME_MIN_CONTAINS': 3,
    'NOTIFY_CHANNELS': ['slack'], 'SLACK_CHANNEL': 'REPLACE_ME_SLACK_CHANNEL_ID', 'NOTIFY_EMAIL_TO': 'replace-me@example.com',
    'LINE_TO_USER_ID': 'REPLACE_ME_LINE_USER_ID', 'CHATWORK_ROOM_ID': 'REPLACE_ME_CHATWORK_ROOM_ID',
    'NOTIFY_MAX_LINES': 40, 'MESSAGES': MESSAGES,
}
# the error handler's own minimal Config (DESIGN.md §2.2 / D20)
ERR_CFG = {
    'LANG': 'ja', 'NOTIFY_CHANNELS': ['slack'], 'SLACK_CHANNEL': 'REPLACE_ME_SLACK_CHANNEL_ID',
    'NOTIFY_EMAIL_TO': 'replace-me@example.com', 'LINE_TO_USER_ID': 'REPLACE_ME_LINE_USER_ID',
    'CHATWORK_ROOM_ID': 'REPLACE_ME_CHATWORK_ROOM_ID',
    'MESSAGES': {'ja': {'error_notice': MSG_JA['error_notice']}, 'en': {'error_notice': MSG_EN['error_notice']}},
}


def config(source, **over):
    cfg = json.loads(json.dumps(BASE_CFG, ensure_ascii=False))
    trigger = {'drive': {'id': 'fixture-bank-A', 'name': 'bank_A_sjis.csv', 'mimeType': 'text/csv', 'SOURCE': 'Watch Drive Folder'},
               'gmail': {'id': '18f3aabb00000001', 'SOURCE': 'Watch Gmail Inbox'},
               'schedule': {'timestamp': '2026-09-24T09:00:00.000+09:00', 'SOURCE': 'Run Daily Rematch'}}[source]
    cfg = {**trigger, **cfg}
    cfg.update(over)
    return [{'json': cfg, 'pairedItem': {'item': 0}}]


def write(module, name, scenario):
    d = os.path.join(HERE, module)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name + '.json'), 'w', encoding='utf-8') as f:
        json.dump(scenario, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('wrote', module + '/' + name + '.json')


# --------------------------------------------------------------------------------------------------------------
# Summary of fixture A (bank_A_sjis.csv, initial state) — DESIGN.md §3.6 shape, values per fixtures/README.md §4
# --------------------------------------------------------------------------------------------------------------
with open(os.path.join(FIX, 'bank_A_sjis.csv'), 'rb') as f:
    A_TEXT = f.read().decode('cp932')
A_ROWS = list(csv.DictReader(io.StringIO(A_TEXT)))
A_DEPOSITS = [r for r in A_ROWS if r['入金額'].strip()]
assert len(A_DEPOSITS) == 11, len(A_DEPOSITS)

# transcribed from fixtures/README.md §4 (No. = data row of the CSV; only deposit rows appear)
A_OUTCOME = {
    1: ('auto', dict(invoice_ids=['INV-2026-001'], reason='auto', fee=0, remaining_after=0)),
    3: ('needs_review', dict(invoice_ids=['INV-2026-002'], reason='fee_deducted', fee=220, remaining_after=0)),
    4: ('auto', dict(invoice_ids=['INV-2026-003'], reason='auto', fee=0, remaining_after=0)),
    5: ('needs_review', dict(invoice_ids=['INV-2026-004'], reason='amount_only', fee=0, remaining_after=0)),
    6: ('needs_review', dict(invoice_ids=['INV-2026-005', 'INV-2026-006'], reason='combined', fee=0, remaining_after=0)),
    8: ('auto', dict(invoice_ids=['INV-2026-007'], reason='partial', fee=0, remaining_after=150000)),
    9: ('ambiguous', dict(reason='same_amount_multiple', candidates=[{'invoice_id': 'INV-2026-008', 'remaining': 44000},
                                                                     {'invoice_id': 'INV-2026-009', 'remaining': 44000}])),
    11: ('unmatched', dict(reason='no_candidate', candidates=[{'invoice_id': 'INV-2026-015', 'remaining': 57200},
                                                             {'invoice_id': 'INV-2026-017', 'remaining': 49500}])),
    12: ('unmatched', dict(reason='no_candidate', candidates=[])),
    13: ('auto', dict(invoice_ids=['INV-2026-012'], reason='auto', fee=0, remaining_after=0)),
    14: ('unmatched', dict(reason='no_candidate', candidates=[{'invoice_id': 'INV-2026-014', 'remaining': 15400}])),
}
# raw remitter strings as fixtures/README.md §4 prints them — cross-checked against the CSV bytes below
A_RAW = {1: '振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ', 3: '振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ', 4: 'フリコミ　ヤマダ　タロウ', 5: '振込 ｻﾄｳ ｹｲｺ', 6: '振込 ｶ)ﾃｽﾄﾌﾞﾂｻﾝ',
         8: '振込 ｻﾝﾌﾟﾙｼｽﾃﾑ(ｶ', 9: '振込 ｵｵﾊﾞ ﾏｻｵ', 11: '振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ', 12: '振込 ﾃｽﾄｹﾝｾﾂ(ｶ', 13: '振込 ｶ)ｻﾝﾌﾟﾙﾌｰｽﾞﾄｳｷﾖｳ',
         14: '振込 ﾅｶﾑﾗ ｼﾞﾛｳ'}


def summary_A():
    s = dict(date=DATE, source='drive', file_name='bank_A_sjis.csv', n=11, a=4, b=3, c=4, rematched=0, skipped_existing=0,
             skipped_duplicate_in_batch=0, ignored_withdraw=4, auto=[], needs_review=[], ambiguous=[], unmatched=[], warnings=[])
    for i, row in enumerate(A_ROWS, start=1):
        if not row['入金額'].strip():
            continue
        bucket, extra = A_OUTCOME[i]
        raw = row['摘要'].strip()
        if raw != A_RAW[i]:
            raise SystemExit(f'README raw remitter for row {i} ({A_RAW[i]!r}) does not match the CSV ({raw!r})')
        y, m, d = row['日付'].split('/')
        line = {'txn_date': f'{y}-{m}-{d}', 'payer_raw': raw, 'amount': int(row['入金額'].replace(',', '')), 'source': 'bank_csv'}
        s[bucket].append({**line, **extra})
    assert [len(s[k]) for k in ('auto', 'needs_review', 'ambiguous', 'unmatched')] == [4, 3, 1, 3]
    return s


# tests/CASES.md §3 — full expected notification for A, LANG=ja (blank lines: DESIGN §6.8 join('\n\n'), CASES T08)
A_BODY_JA = """【入金消込 2026-09-23】処理 11件｜自動消込 4｜要確認 3｜未消込 4

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
・2026-09-14 振込 ｶ)ｻﾝﾌﾟﾙﾌｰｽﾞﾄｳｷﾖｳ ¥27,500 → INV-2026-012"""

# the same, LANG=en — headings / reasons / bullets are the literal values of shared/messages.en.json recon_summary (CASES.md §5)
A_BODY_EN = """[Reconciliation 2026-09-23] Processed 11 | Auto-matched 4 | Needs review 3 | Unmatched 4

■ Needs review (auto-matched by amount only, fee deducted, or combined)
• 2026-09-02 振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ ¥54,780 → INV-2026-002 (fee ¥220 deducted)
• 2026-09-04 振込 ｻﾄｳ ｹｲｺ ¥128,000 → INV-2026-004 (amount only, needs review)
• 2026-09-05 振込 ｶ)ﾃｽﾄﾌﾞﾂｻﾝ ¥1,234,567 → INV-2026-005, INV-2026-006 (combined)

■ Ambiguous (multiple candidates, not auto-matched; pick one)
• 2026-09-09 振込 ｵｵﾊﾞ ﾏｻｵ ¥44,000 → candidates: INV-2026-008(¥44,000), INV-2026-009(¥44,000)

■ Unmatched (no matching invoice)
• 2026-09-11 振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ ¥66,000 → candidates: INV-2026-015(¥57,200), INV-2026-017(¥49,500)
• 2026-09-12 振込 ﾃｽﾄｹﾝｾﾂ(ｶ ¥88,000 → candidates: —
• 2026-09-15 振込 ﾅｶﾑﾗ ｼﾞﾛｳ ¥5,500 → candidates: INV-2026-014(¥15,400)

■ Auto-matched
• 2026-09-01 振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ ¥33,000 → INV-2026-001
• 2026-09-03 フリコミ　ヤマダ　タロウ ¥9,800 → INV-2026-003
• 2026-09-08 振込 ｻﾝﾌﾟﾙｼｽﾃﾑ(ｶ ¥100,000 → INV-2026-007 (partial, remaining ¥150,000)
• 2026-09-14 振込 ｶ)ｻﾝﾌﾟﾙﾌｰｽﾞﾄｳｷﾖｳ ¥27,500 → INV-2026-012"""

# tests/CASES.md R20 — A with NOTIFY_MAX_LINES=2
A_BODY_JA_MAX2 = """【入金消込 2026-09-23】処理 11件｜自動消込 4｜要確認 3｜未消込 4

■ 要確認（金額のみ一致・手数料差引・合算で自動消込した分）
・2026-09-02 振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ ¥54,780 → INV-2026-002 （手数料 ¥220 差引）
・2026-09-04 振込 ｻﾄｳ ｹｲｺ ¥128,000 → INV-2026-004 （金額のみ一致・要確認）
…他 1 件

■ 候補複数（自動確定せず。候補から選んでください）
・2026-09-09 振込 ｵｵﾊﾞ ﾏｻｵ ¥44,000 → 候補: INV-2026-008(¥44,000), INV-2026-009(¥44,000)

■ 未消込（該当請求なし）
・2026-09-11 振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ ¥66,000 → 候補: INV-2026-015(¥57,200), INV-2026-017(¥49,500)
・2026-09-12 振込 ﾃｽﾄｹﾝｾﾂ(ｶ ¥88,000 → 候補: —
…他 1 件

■ 自動消込
・2026-09-01 振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ ¥33,000 → INV-2026-001
・2026-09-03 フリコミ　ヤマダ　タロウ ¥9,800 → INV-2026-003
…他 2 件"""

for raw in A_RAW.values():          # every CSV remitter must appear verbatim in the two full transcribed bodies (the max-2 body truncates)
    for body in (A_BODY_JA, A_BODY_EN):
        if raw not in body:
            raise SystemExit(f'transcribed body lacks the CSV remitter {raw!r}')


def out_shape(body, title, n_blocks):
    """common assertions on the single output item (DESIGN.md §3.7)"""
    return {
        'length': 1,
        'paths': {
            '[0].json.title': title,
            '[0].json.body_text': body,
            '[0].json.chatwork_text': body,
            '[0].json.line_text': body[:4900],
            '[0].json.slack_blocks[0]': {'type': 'header', 'text': {'type': 'plain_text', 'text': title[:150]}},
            '[0].json.slack_blocks.length': n_blocks,
            '[0].json.slack_blocks[*].type': ['header'] + ['section'] * (n_blocks - 1),
            '[0].json.slack_blocks[*].text.type': ['plain_text'] + ['mrkdwn'] * (n_blocks - 1),
            '[0].pairedItem': {'item': 0},
        },
        'max_length': {'[0].json.slack_blocks[0].text.text': 150, '[0].json.slack_blocks[*].text.text': 3000, '[0].json.line_text': 4900},
    }


# --------------------------------------------------------------------------------------------------------------
# Build Notification
# --------------------------------------------------------------------------------------------------------------
BN = 'build_notification'
sA = summary_A()
TITLE_JA_A = '【入金消込 2026-09-23】処理 11件｜自動消込 4｜要確認 3｜未消込 4'
TITLE_EN_A = '[Reconciliation 2026-09-23] Processed 11 | Auto-matched 4 | Needs review 3 | Unmatched 4'

write(BN, 'a_bank_A_ja', {
    '_comment': 'Fixture A (bank_A_sjis.csv) on the seed, LANG=ja, NOTIFY_MAX_LINES=40: the full notification of tests/CASES.md §3 (R01–R06, T08). '
                '4 sections → 5 Slack blocks; body < 4,900 chars so line_text == body_text.',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **sA}, 'pairedItem': {'item': 0}}], 'nodes': {'Config': config('drive')},
    'expect': out_shape(A_BODY_JA, TITLE_JA_A, 5),
})
write(BN, 'a_bank_A_en', {
    '_comment': 'Same summary with LANG=en: headings / bullets / reason phrases are the literal recon_summary values of shared/messages.en.json.',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **sA}, 'pairedItem': {'item': 0}}], 'nodes': {'Config': config('drive', LANG='en')},
    'expect': out_shape(A_BODY_EN, TITLE_EN_A, 5),
})
write(BN, 'a_bank_A_max_lines_2_ja', {
    '_comment': 'R20: A with NOTIFY_MAX_LINES=2 → needs review 2 + 「…他 1 件」, ambiguous 1, unmatched 2 + 「…他 1 件」, auto 2 + 「…他 2 件」 (D16 more_items).',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **sA}, 'pairedItem': {'item': 0}}], 'nodes': {'Config': config('drive', NOTIFY_MAX_LINES=2)},
    'expect': out_shape(A_BODY_JA_MAX2, TITLE_JA_A, 5),
})

# DESIGN.md §3.6 example summary (the "…" fields filled with concrete values; counts are the example's 11 / 7 / 2 / 2)
S36 = dict(date=DATE, source='drive', file_name='bank_A_2026-09.csv', n=11, a=7, b=2, c=2, rematched=0, skipped_existing=0,
           skipped_duplicate_in_batch=0, ignored_withdraw=4,
           auto=[{'txn_date': '2026-09-01', 'payer_raw': '振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ', 'amount': 33000, 'source': 'bank_csv',
                  'invoice_ids': ['INV-2026-001'], 'reason': 'auto', 'fee': 0, 'remaining_after': 0}],
           needs_review=[{'txn_date': '2026-09-02', 'payer_raw': 'ｶ)ｻﾝﾌﾟﾙ', 'amount': 32780, 'source': 'bank_csv',
                          'invoice_ids': ['INV-2026-004'], 'reason': 'fee_deducted', 'fee': 220, 'remaining_after': 0}],
           ambiguous=[{'txn_date': '2026-09-10', 'payer_raw': '振込 ﾔﾏﾀﾞ ﾊﾅｺ', 'amount': 50000, 'source': 'bank_csv', 'reason': 'same_amount_multiple',
                       'candidates': [{'invoice_id': 'INV-2026-010', 'remaining': 50000}, {'invoice_id': 'INV-2026-011', 'remaining': 50000}]}],
           unmatched=[{'txn_date': '2026-09-12', 'payer_raw': '振込 ﾃｽﾄｹﾝｾﾂ(ｶ', 'amount': 88000, 'source': 'bank_csv', 'reason': 'no_candidate', 'candidates': []}],
           warnings=[{'type': 'non_jpy_invoice', 'invoice_id': 'INV-2026-022', 'currency': 'USD'}])
S36_BODY_JA = """【入金消込 2026-09-23】処理 11件｜自動消込 7｜要確認 2｜未消込 2

■ 要確認（金額のみ一致・手数料差引・合算で自動消込した分）
・2026-09-02 ｶ)ｻﾝﾌﾟﾙ ¥32,780 → INV-2026-004 （手数料 ¥220 差引）

■ 候補複数（自動確定せず。候補から選んでください）
・2026-09-10 振込 ﾔﾏﾀﾞ ﾊﾅｺ ¥50,000 → 候補: INV-2026-010(¥50,000), INV-2026-011(¥50,000)

■ 未消込（該当請求なし）
・2026-09-12 振込 ﾃｽﾄｹﾝｾﾂ(ｶ ¥88,000 → 候補: —

■ 自動消込
・2026-09-01 振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ ¥33,000 → INV-2026-001

■ 警告
・non_jpy_invoice INV-2026-022 USD"""
# EN: the warning bullet stays "・" — DESIGN §6.8 lineWarning hardcodes it (see tests/unit/DISCREPANCIES.md)
S36_BODY_EN = """[Reconciliation 2026-09-23] Processed 11 | Auto-matched 7 | Needs review 2 | Unmatched 2

■ Needs review (auto-matched by amount only, fee deducted, or combined)
• 2026-09-02 ｶ)ｻﾝﾌﾟﾙ ¥32,780 → INV-2026-004 (fee ¥220 deducted)

■ Ambiguous (multiple candidates, not auto-matched; pick one)
• 2026-09-10 振込 ﾔﾏﾀﾞ ﾊﾅｺ ¥50,000 → candidates: INV-2026-010(¥50,000), INV-2026-011(¥50,000)

■ Unmatched (no matching invoice)
• 2026-09-12 振込 ﾃｽﾄｹﾝｾﾂ(ｶ ¥88,000 → candidates: —

■ Auto-matched
• 2026-09-01 振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ ¥33,000 → INV-2026-001

■ Warnings
・non_jpy_invoice INV-2026-022 USD"""
write(BN, 'design_3_6_example_ja', {
    '_comment': 'DESIGN.md §3.6 example summary (n 11 / a 7 / b 2 / c 2, one entry per section, non_jpy_invoice warning), LANG=ja → §3.7 output shape; 5 sections → 6 Slack blocks.',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **S36}, 'pairedItem': {'item': 0}}], 'nodes': {'Config': config('drive')},
    'expect': out_shape(S36_BODY_JA, '【入金消込 2026-09-23】処理 11件｜自動消込 7｜要確認 2｜未消込 2', 6),
})
write(BN, 'design_3_6_example_en', {
    '_comment': 'DESIGN.md §3.6 example summary, LANG=en.',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **S36}, 'pairedItem': {'item': 0}}], 'nodes': {'Config': config('drive', LANG='en')},
    'expect': out_shape(S36_BODY_EN, '[Reconciliation 2026-09-23] Processed 11 | Auto-matched 7 | Needs review 2 | Unmatched 2', 6),
})

# every reason phrase incl. overpaid (3d, D07) on the Gmail path
S_REASONS = dict(date=DATE, source='gmail', file_name='', n=6, a=2, b=3, c=1, rematched=0, skipped_existing=0, skipped_duplicate_in_batch=0, ignored_withdraw=0,
                 auto=[{'txn_date': '2026-09-17', 'payer_raw': 'カ)ダミーデンキ', 'amount': 104500, 'source': 'gmail', 'invoice_ids': ['INV-2026-018'], 'reason': 'auto', 'fee': 0, 'remaining_after': 0},
                       {'txn_date': '2026-09-18', 'payer_raw': 'ササキ ハナコ', 'amount': 10000, 'source': 'gmail', 'invoice_ids': ['INV-2026-019'], 'reason': 'partial', 'fee': 0, 'remaining_after': 9800}],
                 needs_review=[{'txn_date': '2026-09-18', 'payer_raw': 'ヤマダ タロウ', 'amount': 9470, 'source': 'gmail', 'invoice_ids': ['INV-2026-003'], 'reason': 'fee_deducted', 'fee': 330, 'remaining_after': 0},
                               {'txn_date': '2026-09-18', 'payer_raw': 'サトウ ケイコ', 'amount': 128000, 'source': 'gmail', 'invoice_ids': ['INV-2026-004'], 'reason': 'amount_only', 'fee': 0, 'remaining_after': 0},
                               {'txn_date': '2026-09-18', 'payer_raw': 'カ)テストブツサン', 'amount': 1234567, 'source': 'gmail', 'invoice_ids': ['INV-2026-005', 'INV-2026-006'], 'reason': 'combined', 'fee': 0, 'remaining_after': 0}],
                 ambiguous=[{'txn_date': '2026-09-18', 'payer_raw': 'ナカムラ ジロウ', 'amount': 20000, 'source': 'gmail', 'reason': 'overpaid', 'candidates': [{'invoice_id': 'INV-2026-014', 'remaining': 15400}]}],
                 unmatched=[], warnings=[])
S_REASONS_BODY = """【入金消込 2026-09-23】処理 6件｜自動消込 2｜要確認 3｜未消込 1

■ 要確認（金額のみ一致・手数料差引・合算で自動消込した分）
・2026-09-18 ヤマダ タロウ ¥9,470 → INV-2026-003 （手数料 ¥330 差引）
・2026-09-18 サトウ ケイコ ¥128,000 → INV-2026-004 （金額のみ一致・要確認）
・2026-09-18 カ)テストブツサン ¥1,234,567 → INV-2026-005, INV-2026-006 （合算）

■ 候補複数（自動確定せず。候補から選んでください）
・2026-09-18 ナカムラ ジロウ ¥20,000 → 候補: INV-2026-014(¥15,400) （超過入金）

■ 自動消込
・2026-09-17 カ)ダミーデンキ ¥104,500 → INV-2026-018
・2026-09-18 ササキ ハナコ ¥10,000 → INV-2026-019 （一部入金・残 ¥9,800）"""
write(BN, 'all_reasons_gmail_ja', {
    '_comment': 'Every recon_summary.reasons.* phrase (amount_only / fee_deducted / combined / partial / overpaid) on the Gmail path; the overpaid case (rule 3d, D07) '
                'is an ambiguous entry with one candidate and the 「（超過入金）」 suffix. No unmatched section → 3 sections, 4 blocks.',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **S_REASONS}, 'pairedItem': {'item': 0}}], 'nodes': {'Config': config('gmail')},
    'expect': out_shape(S_REASONS_BODY, '【入金消込 2026-09-23】処理 6件｜自動消込 2｜要確認 3｜未消込 1', 4),
})


def empty_summary(source, **over):
    s = dict(date=DATE, source=source, file_name='bank_A_sjis.csv' if source == 'drive' else '', n=0, a=0, b=0, c=0, rematched=0, skipped_existing=0,
             skipped_duplicate_in_batch=0, ignored_withdraw=0, auto=[], needs_review=[], ambiguous=[], unmatched=[], warnings=[])
    s.update(over)
    return s


NO_TXN_JA = '【入金消込 2026-09-23】新規の入金はありませんでした'
write(BN, 'empty_drive_run_ja', {
    '_comment': 'Drive run with n=0 (e.g. a CSV holding only withdrawals): D12 → always notify; title = no_transactions, no section, one header block.',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **empty_summary('drive', ignored_withdraw=4)}, 'pairedItem': {'item': 0}}], 'nodes': {'Config': config('drive')},
    'expect': out_shape(NO_TXN_JA, NO_TXN_JA, 1),
})
write(BN, 'skipped_existing_only_ja', {
    '_comment': 'R09 second run of A: n=0, skipped_existing=11 → no_transactions + 「（処理済みのため skip：11 件）」 (D16 skipped_note) as the only section.',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **empty_summary('drive', skipped_existing=11)}, 'pairedItem': {'item': 0}}], 'nodes': {'Config': config('drive')},
    'expect': out_shape(NO_TXN_JA + '\n\n（処理済みのため skip：11 件）', NO_TXN_JA, 2),
})
write(BN, 'skipped_existing_only_en', {
    '_comment': 'R09-b in English: "(skipped as already processed: 2)".',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **empty_summary('gmail', skipped_existing=2)}, 'pairedItem': {'item': 0}}], 'nodes': {'Config': config('gmail', LANG='en')},
    'expect': out_shape('[Reconciliation 2026-09-23] No new transactions\n\n(skipped as already processed: 2)', '[Reconciliation 2026-09-23] No new transactions', 2),
})
write(BN, 'schedule_no_change_returns_empty', {
    '_comment': 'R19: schedule run, rematched=0, no warnings → [] (D12); nothing downstream runs.',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **empty_summary('schedule')}, 'pairedItem': {'item': 0}}], 'nodes': {'Config': config('schedule')},
    'expect': {'length': 0},
})
write(BN, 'schedule_non_jpy_only_returns_empty', {
    '_comment': 'R23-b: schedule run whose only warning is non_jpy_invoice → [] (D12 / D28: a standing USD invoice must not notify every morning).',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **empty_summary('schedule', warnings=[{'type': 'non_jpy_invoice', 'invoice_id': 'INV-2026-022', 'currency': 'USD'}])}, 'pairedItem': {'item': 0}}],
    'nodes': {'Config': config('schedule')},
    'expect': {'length': 0},
})
write(BN, 'schedule_skipped_only_returns_empty', {
    '_comment': 'Schedule run with skipped_existing > 0 but rematched=0 and no warning → still [] (the D12 rule looks at rematched and actionable warnings only).',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **empty_summary('schedule', skipped_existing=3)}, 'pairedItem': {'item': 0}}], 'nodes': {'Config': config('schedule')},
    'expect': {'length': 0},
})
S_SCHED_WARN = empty_summary('schedule', warnings=[{'type': 'non_jpy_invoice', 'invoice_id': 'INV-2026-022', 'currency': 'USD'},
                                                   {'type': 'bad_date', 'value': '2026/13/45', '_row': 7}])
write(BN, 'schedule_intake_warning_notifies_ja', {
    '_comment': 'Schedule run with an intake warning (bad_date) next to a non_jpy_invoice → notify (D12): no_transactions title + 「■ 警告」 section listing both.',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **S_SCHED_WARN}, 'pairedItem': {'item': 0}}], 'nodes': {'Config': config('schedule')},
    'expect': out_shape(NO_TXN_JA + '\n\n■ 警告\n・non_jpy_invoice INV-2026-022 USD\n・bad_date 2026/13/45', NO_TXN_JA, 2),
})
# R18 as Match Invoices emits it (tests/unit/DISCREPANCIES.md, T07 decision): a / b / c count NEW rows only, the re-matched row is counted in
# `rematched` and listed under auto; unchanged unmatched / ambiguous rows are neither written nor listed.
S_REMATCH = empty_summary('schedule', n=0, a=0, b=0, c=0, rematched=1,
                          auto=[{'txn_date': '2026-09-11', 'payer_raw': '振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ', 'amount': 66000, 'source': 'bank_csv', 'invoice_ids': ['INV-2026-021'], 'reason': 'auto', 'fee': 0, 'remaining_after': 0}])
S_REMATCH_BODY = """【入金消込 2026-09-23】処理 0件｜自動消込 0｜要確認 0｜未消込 0

■ 自動消込
・2026-09-11 振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ ¥66,000 → INV-2026-021"""
write(BN, 'schedule_rematched_ja', {
    '_comment': 'R18: schedule run with rematched=1 (A-11 matched INV-2026-021 after it was registered) → notify (D12); n=0 but rematched>0 selects the '
                'counted title (not no_transactions) and the re-matched line appears under 「■ 自動消込」. Counters as Match Invoices emits them (T07 decision).',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **S_REMATCH}, 'pairedItem': {'item': 0}}], 'nodes': {'Config': config('schedule')},
    'expect': out_shape(S_REMATCH_BODY, '【入金消込 2026-09-23】処理 0件｜自動消込 0｜要確認 0｜未消込 0', 2),
})

# warnings of every type the upstream nodes emit (Parse Mail: no_parser_matched / parser_no_capture / bad_date; Parse Bank CSV: bad_date; Match Invoices: non_jpy_invoice)
S_WARN = empty_summary('gmail', warnings=[
    {'type': 'no_parser_matched', 'message_id': '18f3aabb00000009', 'from': 'other@example.net', 'subject': 'Weekly statement'},
    {'type': 'parser_no_capture', 'parser': 'bankX', 'message_id': '18f3aabb00000010', 'from': 'notice@example.jp', 'subject': '【サンプル銀行】ご入金のお知らせ'},
    {'type': 'bad_date', 'parser': 'bankY', 'message_id': '18f3aabb00000011', 'value': '2026-99-99'},
    {'type': 'non_jpy_invoice', 'invoice_id': 'INV-2026-022', 'currency': 'USD'},
])
write(BN, 'warnings_all_types_gmail_ja', {
    '_comment': 'Gmail run with nothing parsed but four warnings → always notify (D12); lineWarning prints type, parser, subject-or-value, invoice_id, currency joined by spaces.',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **S_WARN}, 'pairedItem': {'item': 0}}], 'nodes': {'Config': config('gmail')},
    'expect': out_shape(NO_TXN_JA + '\n\n■ 警告\n・no_parser_matched Weekly statement\n・parser_no_capture bankX 【サンプル銀行】ご入金のお知らせ\n・bad_date bankY 2026-99-99\n・non_jpy_invoice INV-2026-022 USD', NO_TXN_JA, 2),
})

# 200-line summary: NOTIFY_MAX_LINES truncation and the Slack / LINE limits
LINES200 = [{'txn_date': f'2026-09-{(i % 28) + 1:02d}', 'payer_raw': f'振込 ﾃｽﾄ{i:03d}', 'amount': 10000 + i, 'source': 'bank_csv',
             'invoice_ids': [f'INV-2026-{i:03d}'], 'reason': 'amount_only', 'fee': 0, 'remaining_after': 0} for i in range(1, 201)]
S200 = empty_summary('drive', n=200, b=200, needs_review=LINES200)
TITLE200 = '【入金消込 2026-09-23】処理 200件｜自動消込 0｜要確認 200｜未消込 0'
write(BN, 'two_hundred_lines_max_40_ja', {
    '_comment': '200 needs-review lines with NOTIFY_MAX_LINES=40 (default): 40 detail lines + 「…他 160 件」; one section (< 2,900 chars) → 2 blocks; '
                'body < 4,900 so line_text == body_text; header ≤ 150 / section ≤ 3,000 / LINE ≤ 4,900.',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **S200}, 'pairedItem': {'item': 0}}], 'nodes': {'Config': config('drive')},
    'expect': {
        'length': 1,
        'paths': {'[0].json.title': TITLE200, '[0].json.slack_blocks.length': 2, '[0].json.slack_blocks[0].text.text': TITLE200, '[0].pairedItem': {'item': 0}},
        'count': {'[0].json.body_text': {'・2026-09-': 40, '…他 160 件': 1, '\n\n': 1}},
        'contains': {'[0].json.body_text': ['■ 要確認（金額のみ一致・手数料差引・合算で自動消込した分）\n・2026-09-02 振込 ﾃｽﾄ001 ¥10,001 → INV-2026-001 （金額のみ一致・要確認）',
                                            '・2026-09-13 振込 ﾃｽﾄ040 ¥10,040 → INV-2026-040 （金額のみ一致・要確認）\n…他 160 件']},
        'not_contains': {'[0].json.body_text': ['ﾃｽﾄ041', 'INV-2026-200']},
        'equal_paths': {'[0].json.line_text': '[0].json.body_text', '[0].json.chatwork_text': '[0].json.body_text'},
        'max_length': {'[0].json.slack_blocks[0].text.text': 150, '[0].json.slack_blocks[*].text.text': 3000, '[0].json.line_text': 4900},
    },
})
write(BN, 'two_hundred_lines_max_1000_chunked_ja', {
    '_comment': '200 lines with NOTIFY_MAX_LINES=1000: nothing truncated (~11,000 chars); the section is chunked into ≤ 2,900-char Slack blocks, '
                'line_text is cut to exactly 4,900 chars, chatwork_text keeps the full body.',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **S200}, 'pairedItem': {'item': 0}}], 'nodes': {'Config': config('drive', NOTIFY_MAX_LINES=1000)},
    'expect': {
        'length': 1,
        'paths': {'[0].json.title': TITLE200, '[0].json.line_text.length': 4900, '[0].json.slack_blocks[0].text.text': TITLE200},
        'count': {'[0].json.body_text': {'・2026-09-': 200, '…他': 0}},
        'contains': {'[0].json.body_text': ['・2026-09-05 振込 ﾃｽﾄ200 ¥10,200 → INV-2026-200 （金額のみ一致・要確認）']},
        'min_length': {'[0].json.body_text': 4901, '[0].json.slack_blocks': 4},
        'equal_paths': {'[0].json.chatwork_text': '[0].json.body_text'},
        'max_length': {'[0].json.slack_blocks[0].text.text': 150, '[0].json.slack_blocks[*].text.text': 3000, '[0].json.line_text': 4900},
    },
})
LONG_DATE = 'X' * 200
LONG_TITLE = f'【入金消込 {LONG_DATE}】処理 1件｜自動消込 1｜要確認 0｜未消込 0'
write(BN, 'header_slice_150_synthetic', {
    '_comment': 'Synthetic: a 200-char date pushes the title past 150 chars → the Slack header text is title.slice(0, 150) while title / body_text keep the full string.',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **empty_summary('drive', date=LONG_DATE, n=1, a=1, auto=[sA['auto'][0]])}, 'pairedItem': {'item': 0}}],
    'nodes': {'Config': config('drive')},
    'expect': {'length': 1,
               'paths': {'[0].json.title': LONG_TITLE, '[0].json.slack_blocks[0].text.text': LONG_TITLE[:150], '[0].json.slack_blocks[0].text.text.length': 150,
                         '[0].json.slack_blocks.length': 2},
               'max_length': {'[0].json.slack_blocks[0].text.text': 150, '[0].json.slack_blocks[*].text.text': 3000, '[0].json.line_text': 4900}},
})
write(BN, 'missing_messages_fails', {
    '_comment': 'Config without MESSAGES.ja.recon_summary must fail loudly (Config errors are not hidden, DESIGN §2.5).',
    'now': NOW, 'input': [{'json': {'_kind': 'summary', **sA}, 'pairedItem': {'item': 0}}], 'nodes': {'Config': config('drive', MESSAGES={'en': MESSAGES['en']})},
    'expect': {'error_includes': 'Config.MESSAGES.ja.recon_summary is missing'},
})

# --------------------------------------------------------------------------------------------------------------
# Build Error Message (error-handler.json)
# --------------------------------------------------------------------------------------------------------------
BE = 'build_error_message'
EXEC_ERR = {'execution': {'id': '231', 'url': 'https://n8n.example.com/execution/231', 'retryOf': '34',
                          'error': {'message': 'Example Error Message', 'stack': 'Stacktrace'}, 'lastNodeExecuted': 'Node With Error', 'mode': 'manual'},
            'workflow': {'id': '1', 'name': 'Example Workflow'}}
TRIG_ERR = {'trigger': {'error': {'context': {}, 'name': 'WorkflowActivationError', 'cause': {'message': 'Invalid credentials', 'stack': ''},
                                  'timestamp': 1654609328787, 'message': 'Gmail credentials have expired',
                                  'node': {'parameters': {}, 'name': 'Watch Gmail Inbox', 'type': 'n8n-nodes-base.gmailTrigger', 'typeVersion': 1.4, 'position': [0, 0]}},
                        'mode': 'trigger'},
            'workflow': {'id': 'REPLACE_ME', 'name': '[Odaji] 01 Bank Deposit Reconciliation v1.0.0'}}
EXEC_BODY_JA = """ワークフロー：Example Workflow
失敗したノード：Node With Error
エラー：Example Error Message
実行ログ：https://n8n.example.com/execution/231

実行ログで原因を確認し、修正後に再実行してください。シート書込みやメール送信が途中まで進んでいる可能性があるため、再実行前に台帳シートを確認してください。"""
EXEC_BODY_EN = """Workflow: Example Workflow
Failed node: Node With Error
Error: Example Error Message
Execution log: https://n8n.example.com/execution/231

Check the execution log for the cause, fix it, and re-run. Sheet writes or emails may have partially completed, so check the ledger sheet before re-running."""
TRIG_BODY_JA = """ワークフロー：[Odaji] 01 Bank Deposit Reconciliation v1.0.0
失敗したノード：Watch Gmail Inbox
エラー：Gmail credentials have expired
実行ログ：(not saved)

実行ログで原因を確認し、修正後に再実行してください。シート書込みやメール送信が途中まで進んでいる可能性があるため、再実行前に台帳シートを確認してください。"""


def err_expect(title, body):
    return {'length': 1,
            'paths': {'[0].json.title': title, '[0].json.body_text': body, '[0].json.chatwork_text': body, '[0].json.line_text': body[:4900],
                      '[0].json.slack_blocks': [{'type': 'header', 'text': {'type': 'plain_text', 'text': title[:150]}},
                                                {'type': 'section', 'text': {'type': 'mrkdwn', 'text': body[:2900]}}],
                      '[0].pairedItem': {'item': 0}},
            'max_length': {'[0].json.slack_blocks[0].text.text': 150, '[0].json.slack_blocks[*].text.text': 3000, '[0].json.line_text': 4900}}


def err_config(**over):
    cfg = json.loads(json.dumps(ERR_CFG, ensure_ascii=False))
    cfg.update(over)
    return [{'json': cfg, 'pairedItem': {'item': 0}}]


write(BE, 'execution_error_ja', {
    '_comment': 'Error Trigger "execution error" shape exactly as the n8n docs example (id / url / retryOf / error / lastNodeExecuted / mode), LANG=ja.',
    'now': NOW, 'input': [{'json': EXEC_ERR}], 'nodes': {'Config': err_config()},
    'expect': err_expect('【n8n エラー】Example Workflow', EXEC_BODY_JA),
})
write(BE, 'execution_error_en', {
    '_comment': 'Same item, LANG=en.',
    'now': NOW, 'input': [{'json': EXEC_ERR}], 'nodes': {'Config': err_config(LANG='en')},
    'expect': err_expect('[n8n error] Example Workflow', EXEC_BODY_EN),
})
write(BE, 'trigger_error_ja', {
    '_comment': 'Error Trigger "trigger error" shape (no execution{}; trigger.error.node / .message): failed node = trigger.error.node.name, execution_url = "(not saved)".',
    'now': NOW, 'input': [{'json': TRIG_ERR}], 'nodes': {'Config': err_config()},
    'expect': err_expect('【n8n エラー】[Odaji] 01 Bank Deposit Reconciliation v1.0.0', TRIG_BODY_JA),
})
TRIG_BARE = {'trigger': {'error': {'context': {}, 'name': 'WorkflowActivationError', 'cause': {'message': '', 'stack': ''}, 'timestamp': 1654609328787, 'message': '', 'node': {}},
                         'mode': 'trigger'}, 'workflow': {'id': '', 'name': ''}}
write(BE, 'trigger_error_bare_docs_example_ja', {
    '_comment': 'The docs\' literal trigger-error example (empty message, empty node, empty workflow name): fallbacks "(trigger)" / "unknown error" / "(not saved)".',
    'now': NOW, 'input': [{'json': TRIG_BARE}], 'nodes': {'Config': err_config()},
    'expect': err_expect('【n8n エラー】', """ワークフロー：
失敗したノード：(trigger)
エラー：unknown error
実行ログ：(not saved)

実行ログで原因を確認し、修正後に再実行してください。シート書込みやメール送信が途中まで進んでいる可能性があるため、再実行前に台帳シートを確認してください。"""),
})
UNSAVED = {'execution': {'error': {'message': 'The resource you are requesting could not be found', 'stack': ''}, 'lastNodeExecuted': 'Read Invoices', 'mode': 'trigger'},
           'workflow': {'id': 'REPLACE_ME', 'name': '[Odaji] 01 Bank Deposit Reconciliation v1.0.0'}}
write(BE, 'execution_error_unsaved_no_url_ja', {
    '_comment': 'Execution error without execution.id / execution.url (execution not saved): execution_url falls back to "(not saved)".',
    'now': NOW, 'input': [{'json': UNSAVED}], 'nodes': {'Config': err_config()},
    'expect': {'length': 1, 'paths': {'[0].json.title': '【n8n エラー】[Odaji] 01 Bank Deposit Reconciliation v1.0.0'},
               'contains': {'[0].json.body_text': ['失敗したノード：Read Invoices\n', 'エラー：The resource you are requesting could not be found\n', '実行ログ：(not saved)\n']}},
})
write(BE, 'unknown_lang_falls_back_to_ja', {
    '_comment': 'LANG other than "en" selects the Japanese copy (§6.9 lang = LANG === "en" ? "en" : "ja").',
    'now': NOW, 'input': [{'json': EXEC_ERR}], 'nodes': {'Config': err_config(LANG='fr')},
    'expect': err_expect('【n8n エラー】Example Workflow', EXEC_BODY_JA),
})
write(BE, 'missing_messages_fails', {
    '_comment': 'Config without MESSAGES.en.error_notice must fail loudly.',
    'now': NOW, 'input': [{'json': EXEC_ERR}], 'nodes': {'Config': err_config(LANG='en', MESSAGES={'ja': ERR_CFG['MESSAGES']['ja']})},
    'expect': {'error_includes': 'Config.MESSAGES.en.error_notice is missing'},
})

# --------------------------------------------------------------------------------------------------------------
# Check Notification Results
# --------------------------------------------------------------------------------------------------------------
CR = 'check_notification_results'
NOTE = {'title': TITLE_JA_A, 'body_text': A_BODY_JA, 'slack_blocks': [], 'line_text': A_BODY_JA, 'chatwork_text': A_BODY_JA}
OK_SLACK = {'json': {'ok': True, 'channel': 'C0REPLACEME', 'ts': '1758585600.000100', 'message': {'type': 'message', 'text': TITLE_JA_A}}, 'pairedItem': {'item': 0}}
OK_GMAIL = {'json': {'id': '18f3aabb0000ffff', 'threadId': '18f3aabb0000ffff', 'labelIds': ['SENT']}, 'pairedItem': {'item': 0}}
OK_LINE = {'json': {}, 'pairedItem': {'item': 0}}                              # LINE push returns an empty JSON object on 200
OK_CHATWORK = {'json': {'message_id': '1234567890123456789'}, 'pairedItem': {'item': 0}}
# error-output items = the paired input json merged with the node's error item (n8n-core handleNodeErrorOutput).
# Slack / Gmail push error = message string; HTTP Request v4.5 yields error = { message, name, stack } + details
# (measured in local n8n 2.40.5, execution 15 — tests/unit/DISCREPANCIES.md).
ERR_SLACK = {'json': {**NOTE, 'error': 'The resource you are requesting could not be found'}, 'pairedItem': {'item': 0}}
ERR_LINE = {'json': {**NOTE, 'error': {'code': 'ECONNREFUSED', 'message': 'connect ECONNREFUSED 127.0.0.1:9', 'name': 'Error',
                                      'stack': 'Error: connect ECONNREFUSED 127.0.0.1:9\n    at AxiosError.from (…)'},
                     'details': {'message': 'The service refused the connection - perhaps it is offline', 'httpCode': 'ECONNREFUSED', 'body': None, 'context': {'itemIndex': 0}}},
            'pairedItem': {'item': 0}}
ERR_OBJ = {'json': {**NOTE, 'error': {'message': 'Authorization failed - please check your credentials', 'description': '401 - Unauthorized'}}, 'pairedItem': {'item': 0}}
ERR_OBJ_NOMSG = {'json': {**NOTE, 'error': {'code': 'ETIMEDOUT'}}, 'pairedItem': {'item': 0}}

write(CR, 'all_ok_four_channels', {
    '_comment': 'NOTIFY_CHANNELS = all four, every Notify succeeded (real-looking Slack / Gmail / LINE / Chatwork responses, no json.error).',
    'now': NOW, 'input': [OK_SLACK, OK_GMAIL, OK_LINE, OK_CHATWORK], 'nodes': {},
    'expect': {'length': 1, 'paths': {'[0].json': {'channels_attempted': 4, 'channels_ok': 4, 'channels_failed': 0, 'errors': []}, '[0].pairedItem': {'item': 0}}},
})
write(CR, 'partial_failure_run_succeeds', {
    '_comment': 'R11-b: Slack failed (string error), Email ok, LINE failed (HTTP Request object error as measured in n8n) → the node returns normally with channels_failed=2 (no Error Workflow).',
    'now': NOW, 'input': [OK_GMAIL, ERR_SLACK, ERR_LINE], 'nodes': {},
    'expect': {'length': 1, 'paths': {'[0].json': {'channels_attempted': 3, 'channels_ok': 1, 'channels_failed': 2,
                                                   'errors': ['The resource you are requesting could not be found', 'connect ECONNREFUSED 127.0.0.1:9']},
                                      '[0].pairedItem': {'item': 0}}},
})
write(CR, 'error_object_shapes', {
    '_comment': 'json.error as an object with message → the message; as an object without message → JSON text; json.error = null counts as success (§6.10).',
    'now': NOW, 'input': [ERR_OBJ, ERR_OBJ_NOMSG, {'json': {'ok': True, 'error': None}, 'pairedItem': {'item': 0}}], 'nodes': {},
    'expect': {'length': 1, 'paths': {'[0].json': {'channels_attempted': 3, 'channels_ok': 1, 'channels_failed': 2,
                                                   'errors': ['Authorization failed - please check your credentials', '{"code":"ETIMEDOUT"}']}}},
})
write(CR, 'all_failed_throws', {
    '_comment': 'R11-b second half: every attempted channel failed → throw → the run fails and the Error Workflow fires (D17, CLAUDE.md §4.3).',
    'now': NOW, 'input': [ERR_SLACK, ERR_LINE], 'nodes': {},
    'expect': {'error_includes': 'All notification channels failed (2): The resource you are requesting could not be found / connect ECONNREFUSED 127.0.0.1:9'},
})
write(CR, 'single_channel_failed_throws', {
    '_comment': 'NOTIFY_CHANNELS = ["slack"] with an invalid SLACK_CHANNEL: one attempted, one failed → throw.',
    'now': NOW, 'input': [ERR_SLACK], 'nodes': {},
    'expect': {'error_includes': 'All notification channels failed (1): The resource you are requesting could not be found'},
})
write(CR, 'zero_items', {
    '_comment': 'No input at all (theoretical — with NOTIFY_CHANNELS = [] n8n never runs this node): no throw, zero counters, no pairedItem.',
    'now': NOW, 'input': [], 'nodes': {},
    'expect': {'length': 1, 'paths': {'[0].json': {'channels_attempted': 0, 'channels_ok': 0, 'channels_failed': 0, 'errors': []}}, 'absent': ['[0].pairedItem']},
})
