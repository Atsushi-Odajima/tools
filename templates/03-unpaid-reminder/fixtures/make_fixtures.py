#!/usr/bin/env python3
"""Generate the Template 03 (未入金リマインド / Unpaid Invoice Reminder) seed fixtures relative to a run date.
Python 3 standard library only. Deterministic: the same --today always produces byte-identical files.

  python3 fixtures/make_fixtures.py                        # TODAY = 2026-10-01 (committed reference date, DESIGN.md D15)
  python3 fixtures/make_fixtures.py --today 2026-10-15     # regenerate both seed CSVs for another run date (P3 without TODAY_OVERRIDE)
  python3 fixtures/make_fixtures.py --check                # build in memory and compare with the files on disk (exit 1 on diff)
  python3 fixtures/make_fixtures.py --expected             # also print the expected outcome for that date (see below)
  python3 fixtures/make_fixtures.py --today 2026-10-15 --out-dir /tmp/x   # write elsewhere (e.g. for a pinned-data build)
  python3 fixtures/make_fixtures.py --check --expected --run-date 2026-10-15 --config '{"LANG":"en"}'   # expectation for the committed seed run on another day / other Config

What it writes (columns are read from shared/*.template.csv so the order can never drift from CLAUDE.md §5):
  * invoices.seed.csv       17 fictional invoices whose due_date = TODAY - offset (offset -3 / +1 / +7 / +14 / +21 / +30), plus the
                            remind_stage / last_reminded_at / promised_date / do_not_remind state that fixtures/README.md documents
  * reminders_log.seed.csv  the rows that must already exist for the "already logged" cases (INV-2026-103/104/107/108/109/110/113/116/117)

--expected prints a Python port of DESIGN.md §6.4–§6.8 (Select Due Invoices → Group By Customer → Build Reminder Emails →
Collect Send Results → Build Owner Notice) applied to the generated rows with the Config defaults of DESIGN.md §4 and the
`test_common` overrides of fixtures/config.examples.json. It is a cross-check for writing fixtures/README.md and tests/CASES.md,
NOT a substitute for running the workflow in n8n (CLAUDE.md §1-5). The subjects / bodies it prints are the literal
shared/messages.<LANG>.json copy with the placeholders filled, so they can be pasted into the expected values.
"""
import argparse
import csv
import io
import json
import os
import re
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(TPL))
SHARED = os.path.join(ROOT, 'shared')
DEFAULT_TODAY = '2026-10-01'          # Thursday, not a Japanese public holiday (DESIGN.md D15 / §7)
NOW_TIME = '10:00:03'                 # time part of now_iso in the printed expectation (the real run uses the clock)
TZ_OFFSET = '+09:00'


def read_header(name):
    with open(os.path.join(SHARED, name), encoding='utf-8', newline='') as f:
        return next(csv.reader(f))


INVOICE_COLUMNS = read_header('invoices.template.csv')
LOG_COLUMNS = read_header('reminders_log.template.csv')
assert INVOICE_COLUMNS == ['invoice_id', 'customer_id', 'customer_name', 'payer_name_alias', 'customer_email', 'amount', 'currency',
                           'issue_date', 'due_date', 'status', 'paid_amount', 'paid_date', 'matched_txn_ids', 'match_confidence',
                           'fee_deducted', 'remind_stage', 'last_reminded_at', 'promised_date', 'do_not_remind', 'notes'], INVOICE_COLUMNS
assert LOG_COLUMNS == ['invoice_id', 'stage', 'mode', 'channel', 'to', 'subject', 'sent_at', 'gmail_message_id'], LOG_COLUMNS

with open(os.path.join(SHARED, 'messages.ja.json'), encoding='utf-8') as f:
    MSG_JA = json.load(f)
with open(os.path.join(SHARED, 'messages.en.json'), encoding='utf-8') as f:
    MSG_EN = json.load(f)

# Config defaults that the expectation needs (DESIGN.md §4). Everything else comes from config.examples.json `test_common`.
STAGES_DEFAULT = [{'stage': 0, 'offset_days': -3, 'enabled': False}, {'stage': 1, 'offset_days': 1, 'enabled': True},
                  {'stage': 2, 'offset_days': 7, 'enabled': True}, {'stage': 3, 'offset_days': 14, 'enabled': True}]
CONFIG_DEFAULTS = {'LANG': 'ja', 'STAGES': STAGES_DEFAULT, 'STAGE2_NEW_DEADLINE_DAYS': 7, 'STAGE3_FINAL_DEADLINE_DAYS': 7,
                   'SEND_MODE': 'draft', 'GROUP_BY_CUSTOMER': True, 'SENDER_NAME': 'REPLACE_ME_SENDER_NAME', 'COMPANY': 'REPLACE_ME_COMPANY',
                   'SIGNATURE': 'REPLACE_ME_SIGNATURE', 'BANK_DETAILS': 'REPLACE_ME_BANK_DETAILS', 'NOTIFY_MAX_LINES': 40, 'TODAY_OVERRIDE': ''}

# ----------------------------------------------------------------------------------------------------------------------
# Row specification. `due` = days overdue at TODAY (due_date = TODAY - due). All names, addresses and IDs are fictional.
# The invoice_id range INV-2026-1xx does not overlap Template 01's seed (INV-2026-001..020, 021/022 in its CASES).
# `role` is the fixtures/README.md / tests/CASES.md mapping; it is written into `notes` (JA / EN).
# ----------------------------------------------------------------------------------------------------------------------
INVOICES = [
    # id,  customer, customer_name,                  payer_name_alias,                        email,                  amount, cur,   due, status,     paid,   stage, extra, notes
    ('101', 'C-101', '株式会社サンプル商事',          'カ)サンプルシヨウジ,サンプルシヨウジ',    'keiri@example.jp',     33000, 'JPY',  -3, 'unpaid',    0,      0, {},
     'U17 期限3日前・stage 0 候補（既定 OFF → no_stage_due）/ due in 3 days, stage-0 candidate (off by default → no_stage_due)'),
    ('102', 'C-102', 'テスト工業有限会社',            'ユ)テストコウギヨウ,テストコウギヨウ',    'ap@example.com',       55000, 'JPY',   1, 'unpaid',    0,      0, {},
     'U01 期限+1日 → stage 1 / due +1 day → stage 1'),
    ('103', 'C-103', '見本デザイン合同会社',          'ド)ミホンデザイン,ミホンデザイン',        'info@example.jp',     128000, 'JPY',   7, 'unpaid',    0,      1, {'last': (6, '10:00:05')},
     'U03 期限+7日・stage 1 送付済み → stage 2 / due +7, stage 1 already sent → stage 2'),
    ('104', 'C-104', '株式会社ダミー製作所',          'カ)ダミーセイサクシヨ,ダミーセイサクシヨ', 'billing@example.com',  44000, 'JPY',  14, 'unpaid',    0,      2, {'last': (7, '10:00:06')},
     'U04 期限+14日・stage 2 送付済み → stage 3・escalated / due +14, stage 2 sent → stage 3, escalated'),
    ('105', 'C-105', 'サンプルシステム株式会社',      'サンプルシステム(カ,サンプルシステム',    'ap@example.jp',       250000, 'JPY',   1, 'partial',   100000, 0, {'paid': (-4, 'サンプルシステム')},
     'U08 一部入金（残額 150,000）・期限+1日 → stage 1 / partial (remaining 150,000), due +1 → stage 1'),
    ('106', 'C-106', '有限会社サンプル印刷',          'ユ)サンプルインサツ,サンプルインサツ',    'paid@example.com',     66000, 'JPY',  30, 'paid',      66000,  0, {'paid': (-2, 'サンプルインサツ')},
     'U05 入金済み（対象外 not_open）/ paid, must be excluded (not_open)'),
    ('107', 'C-107', 'テスト商事株式会社',            'テストシヨウジ(カ,テストシヨウジ',        'keiri2@example.jp',    88000, 'JPY',   7, 'unpaid',    0,      1, {'last': (6, '10:00:07'), 'promised': -14},
     'U06 promised_date が未来（skip promised_future）/ promised_date in the future (skip promised_future)'),
    ('108', 'C-108', '株式会社テスト物産',            'カ)テストブツサン,テストブツサン',        'keiri@example.com',   700000, 'JPY',   7, 'unpaid',    0,      1, {'last': (6, '10:00:09')},
     'U11 同一顧客 2 件の 1/2・stage 2 で 1 通 / same customer 1 of 2, one stage-2 email'),
    ('109', 'C-108', '株式会社テスト物産',            'カ)テストブツサン,テストブツサン',        'keiri@example.com',   534567, 'JPY',   7, 'unpaid',    0,      1, {'last': (6, '10:00:09')},
     'U11 同一顧客 2 件の 2/2 / same customer 2 of 2'),
    ('110', 'C-110', 'ダミー企画有限会社',            'ユ)ダミーキカク,ダミーキカク',            'stop@example.jp',      27500, 'JPY',   7, 'unpaid',    0,      1, {'last': (6, '10:00:10'), 'dnr': True},
     'U07 do_not_remind TRUE（対象外）/ do_not_remind TRUE, excluded'),
    ('111', 'C-111', 'Sample Overseas LLC',           'サンプルオーバーシーズ',                  'overseas@example.com', 128000, 'USD',  1, 'unpaid',    0,      0, {},
     'U14 非 JPY（対象外・警告 non_jpy_invoice）/ non-JPY, excluded with warning'),
    ('112', 'C-112', '見本 一郎',                     'ミホンイチロウ',                          '',                     41800, 'JPY',   1, 'unpaid',    0,      0, {},
     'U18 customer_email 空（対象外・警告 missing_email）/ empty customer_email, excluded with warning'),
    ('113', 'C-113', 'サンプル物流株式会社',          'サンプルブツリユウ(カ,サンプルブツリユウ', 'ap3@example.jp',       15400, 'JPY',   7, 'unpaid',    0,      1, {'last': (6, '10:00:11'), 'promised': 11},
     'U13 promised_date が過去（続行 → stage 2）/ promised_date in the past (continue → stage 2)'),
    ('114', 'C-114', 'テスト建材株式会社',            'テストケンザイ(カ,テストケンザイ',        'late@example.com',     57200, 'JPY',  30, 'unpaid',    0,      0, {},
     'U19 導入時に大幅超過・stage 1/2 を飛ばして stage 3 / long overdue at rollout, jumps to stage 3'),
    ('115', 'C-115', 'ダミー出版株式会社',            'カ)ダミーシユツパン,ダミーシユツパン',    'cancel@example.jp',    12100, 'JPY',   7, 'cancelled', 0,      0, {},
     '取消（対象外 not_open）/ cancelled, excluded (not_open)'),
    ('116', 'C-116', '有限会社見本エンジニアリング',  'ユ)ミホンエンジニアリング,ミホンエンジニアリング', 'esc@example.com', 49500, 'JPY', 21, 'escalated', 0, 3, {'last': (7, '10:00:12')},
     'stage 3 送付済み・escalated（対象外 not_open、以後の自動督促なし）/ stage 3 sent, escalated (not_open, no further reminders)'),
    ('117', 'C-117', 'サンプル食品株式会社',          'サンプルシヨクヒン(カ,サンプルシヨクヒン', 'retry@example.jp',     38500, 'JPY',   1, 'unpaid',    0,      0, {},
     'U20 reminders_log に (117, 1) あり・remind_stage 0（already_logged）/ log has (117, 1) but remind_stage 0 (already_logged)'),
]

# reminders_log rows that exist before the run: (invoice ids sharing one email, stage, days before TODAY, time).
# Subjects are the literal shared/messages.ja.json subjects (grouped rows carry the grouped subject, sheets-schema.md).
LOG = [
    (['103'], 1, 6, '10:00:05'),
    (['104'], 1, 13, '10:00:06'), (['104'], 2, 7, '10:00:06'),
    (['107'], 1, 6, '10:00:07'),
    (['108', '109'], 1, 6, '10:00:09'),
    (['110'], 1, 6, '10:00:10'),
    (['113'], 1, 6, '10:00:11'),
    (['116'], 1, 20, '10:00:12'), (['116'], 2, 14, '10:00:12'), (['116'], 3, 7, '10:00:12'),
    (['117'], 1, 0, '10:00:08'),   # U16 / U20: written by an earlier run today whose Update Invoice Stage failed (remind_stage stays 0)
]


def inv_id(s):
    return f'INV-2026-{s}'


def parse_today(s):
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except ValueError:
        sys.exit(f'--today must be yyyy-MM-dd: {s!r}')


def iso(d, t):
    return f'{d.isoformat()}T{t}{TZ_OFFSET}'


def ja_subject(stage, ids):
    return MSG_JA['reminder'][f'stage{stage}']['subject'].replace('{invoice_id}', '、'.join(inv_id(i) for i in ids))


def build_rows(today):
    """Return (invoice rows, log rows) as lists of dicts in column order."""
    log_rows, gmail_ids = [], {}
    entries = sorted(LOG, key=lambda e: (today - timedelta(days=e[2]), e[3], e[0][0]))
    for n, (ids, stage, before, t) in enumerate(entries, 1):
        mid = f'18f60a1b2c3d4e{n:02x}'                                    # fictional Gmail message id, shared by grouped invoices
        sent = iso(today - timedelta(days=before), t)
        for i in ids:
            gmail_ids[(i, stage)] = (sent, mid)
            email = next(r for r in INVOICES if r[0] == i)[4]
            log_rows.append({'invoice_id': inv_id(i), 'stage': stage, 'mode': 'draft', 'channel': 'gmail', 'to': email,
                             'subject': ja_subject(stage, ids), 'sent_at': sent, 'gmail_message_id': mid})
    invoices = []
    for (s, cust, name, alias, email, amount, cur, due, status, paid, stage, extra, notes) in INVOICES:
        due_date = today - timedelta(days=due)
        paid_date = matched = conf = ''
        if paid:
            pd = due_date + timedelta(days=extra['paid'][0])
            paid_date, matched, conf = pd.isoformat(), f'{pd.isoformat()}|{paid}|{extra["paid"][1]}|', 'auto'
        last = ''
        if stage:
            last = gmail_ids[(s, stage)][0]                                 # last_reminded_at = the sent_at of the latest logged stage
        promised = (today - timedelta(days=extra['promised'])).isoformat() if 'promised' in extra else ''
        invoices.append({'invoice_id': inv_id(s), 'customer_id': cust, 'customer_name': name, 'payer_name_alias': alias, 'customer_email': email,
                         'amount': amount, 'currency': cur, 'issue_date': (due_date - timedelta(days=30)).isoformat(), 'due_date': due_date.isoformat(),
                         'status': status, 'paid_amount': paid, 'paid_date': paid_date, 'matched_txn_ids': matched, 'match_confidence': conf,
                         'fee_deducted': 0, 'remind_stage': stage, 'last_reminded_at': last, 'promised_date': promised,
                         'do_not_remind': 'TRUE' if extra.get('dnr') else 'FALSE', 'notes': notes})
    return invoices, log_rows


def to_csv(rows, columns):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, lineterminator='\n')       # UTF-8, no BOM, LF (same as Template 01 fixtures)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


# ----------------------------------------------------------------------------------------------------------------------
# Expected outcome: Python port of DESIGN.md §6.4–§6.8 (kept structurally identical to the pseudocode; cross-check only)
# ----------------------------------------------------------------------------------------------------------------------
def to_int(v):
    if v is None:
        return None
    if isinstance(v, int):
        return v
    s = re.sub(r'[,\s¥￥円]', '', str(v))
    return int(float(s)) if re.fullmatch(r'-?\d+(\.\d+)?', s) else None


def num(v):
    return to_int(v) or 0


def s_(v):
    return '' if v is None else str(v).strip()


def is_true(v):
    return v is True or s_(v).lower() in ('true', '1', 'yes', 'y', 'on')


def fill(tpl, vars_):
    return re.sub(r'\{(\w+)\}', lambda m: str(vars_[m.group(1)]) if m.group(1) in vars_ else m.group(0), str(tpl))


def yen(n):
    return f'{int(n):,}'


def norm_date(v):
    v = s_(v)
    m = re.match(r'^(\d{4})(\d{2})(\d{2})$', v) or re.match(r'^(\d{4})[\/\-.年](\d{1,2})[\/\-.月](\d{1,2})日?', v)
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat() if m else None


def select_due(invoices, log_rows, today, cfg, biz_warnings=()):
    stages = [{'stage': num(x['stage']), 'offset_days': to_int(x['offset_days']), 'enabled': x['enabled'] is True} for x in cfg['STAGES']]
    enabled = [x for x in stages if x['enabled']]
    logged = {f"{s_(r['invoice_id'])}|{num(r['stage'])}" for r in log_rows if s_(r['invoice_id'])}
    skipped = {k: 0 for k in ('not_open', 'do_not_remind', 'promised_future', 'no_stage_due', 'already_at_stage', 'already_logged', 'non_jpy', 'missing_email', 'bad_due_date')}
    warnings, candidates = list(biz_warnings), []
    for raw in invoices:
        if not s_(raw.get('invoice_id')):
            continue
        inv = dict(raw, invoice_id=s_(raw['invoice_id']), status=s_(raw['status']).lower(), amount=num(raw['amount']), paid_amount=num(raw['paid_amount']), remind_stage=num(raw['remind_stage']))
        if inv['status'] not in ('unpaid', 'partial'):
            skipped['not_open'] += 1; continue
        if is_true(inv['do_not_remind']):
            skipped['do_not_remind'] += 1; continue
        cur = s_(inv['currency']).upper()
        if cur and cur != 'JPY':
            skipped['non_jpy'] += 1; warnings.append({'type': 'non_jpy_invoice', 'invoice_id': inv['invoice_id'], 'currency': cur}); continue
        promised = norm_date(inv['promised_date'])
        if promised and promised >= today.isoformat():
            skipped['promised_future'] += 1; continue
        due = norm_date(inv['due_date'])
        if not due:
            skipped['bad_due_date'] += 1; warnings.append({'type': 'bad_due_date', 'invoice_id': inv['invoice_id'], 'value': s_(inv['due_date'])}); continue
        days = (today - date.fromisoformat(due)).days
        target = None
        for st in enabled:
            if days >= st['offset_days']:
                target = st['stage']
        if target is None:
            skipped['no_stage_due'] += 1; continue
        due_now = target > inv['remind_stage'] or (target == 0 and inv['remind_stage'] == 0)
        if not due_now:
            skipped['already_at_stage'] += 1; continue
        if f"{inv['invoice_id']}|{target}" in logged:
            skipped['already_logged'] += 1; continue
        email = s_(inv['customer_email'])
        if not email or '@' not in email:
            skipped['missing_email'] += 1; warnings.append({'type': 'missing_email', 'invoice_id': inv['invoice_id']}); continue
        remaining = inv['amount'] - inv['paid_amount']
        if remaining <= 0:
            skipped['not_open'] += 1; continue
        candidates.append({'invoice_id': inv['invoice_id'], 'customer_id': s_(inv['customer_id']), 'customer_name': s_(inv['customer_name']), 'customer_email': email,
                           'amount': inv['amount'], 'paid_amount': inv['paid_amount'], 'remaining': remaining, 'status': inv['status'], 'due_date': due,
                           'days_overdue': days, 'remind_stage': inv['remind_stage'], 'target_stage': target})
    return candidates, skipped, warnings


def group_by_customer(candidates, cfg):
    groups = {}
    for c in candidates:
        ck = s_(c['customer_id']) or c['customer_email'].lower()
        key = f"{ck}|{c['target_stage']}" if cfg['GROUP_BY_CUSTOMER'] is True else f"{c['invoice_id']}|{c['target_stage']}"
        g = groups.setdefault(key, {'group_key': key, 'customer_key': ck, 'stage': c['target_stage'], 'customer_name': c['customer_name'], 'emails': [], 'invoices': []})
        if c['customer_email'] not in g['emails']:
            g['emails'].append(c['customer_email'])
        g['invoices'].append({k: c[k] for k in ('invoice_id', 'remaining', 'amount', 'due_date', 'days_overdue', 'status', 'remind_stage')})
    out = []
    for g in groups.values():
        g['to'] = ', '.join(g['emails'])
        g['invoices'].sort(key=lambda i: (i['due_date'], i['invoice_id']))
        out.append(g)
    out.sort(key=lambda g: (g['stage'], g['customer_name'], g['group_key']))
    return out


def build_emails(groups, today, cfg):
    lang = 'en' if cfg['LANG'] == 'en' else 'ja'
    M = (MSG_EN if lang == 'en' else MSG_JA)['reminder']
    new_deadline = (today + timedelta(days=num(cfg['STAGE2_NEW_DEADLINE_DAYS']) or 7)).isoformat()
    final_deadline = (today + timedelta(days=num(cfg['STAGE3_FINAL_DEADLINE_DAYS']) or 7)).isoformat()
    SEP, BULLET = (', ', '•') if lang == 'en' else ('、', '・')
    PER = ['invoice_id', 'remaining', 'amount', 'due_date']
    inv_vars = lambda i: {'invoice_id': i['invoice_id'], 'remaining': yen(i['remaining']), 'amount': yen(i['amount']), 'due_date': i['due_date']}
    group_vars = lambda invs: {'invoice_id': SEP.join(i['invoice_id'] for i in invs), 'remaining': yen(sum(i['remaining'] for i in invs)),
                               'amount': yen(sum(i['amount'] for i in invs)), 'due_date': sorted(i['due_date'] for i in invs)[0]}

    def render(tpl, common, invs):
        if len(invs) == 1:
            return fill(tpl, {**common, **inv_vars(invs[0])})
        lines = str(tpl).split('\n')
        i = next((k for k, l in enumerate(lines) if l.startswith(BULLET)), -1)
        if i < 0:
            return fill(tpl, {**common, **group_vars(invs)})
        j = i
        while j < len(lines) and lines[j].startswith(BULLET):
            j += 1
        block = lines[i:j]
        per = [l for l in block if any(f'{{{k}}}' in l for k in PER)]
        com = [l for l in block if not any(f'{{{k}}}' in l for k in PER)]
        repeated = '\n\n'.join('\n'.join(fill(l, {**common, **inv_vars(inv)}) for l in per) for inv in invs)
        tail = ('\n\n' + '\n'.join(fill(l, common) for l in com)) if com else ''
        gv = {**common, **group_vars(invs)}
        return '\n'.join([fill(l, gv) for l in lines[:i]] + [repeated + tail] + [fill(l, gv) for l in lines[j:]])

    common = {'bank_details': s_(cfg['BANK_DETAILS']), 'sender_name': s_(cfg['SENDER_NAME']), 'company': s_(cfg['COMPANY']), 'signature': s_(cfg['SIGNATURE']),
              'new_deadline': new_deadline, 'final_deadline': final_deadline}
    out = []
    for g in groups:
        m = M[f"stage{g['stage']}"]
        vars_ = {**common, 'customer_name': g['customer_name']}
        subject = fill(m['subject'], {**vars_, **(inv_vars(g['invoices'][0]) if len(g['invoices']) == 1 else group_vars(g['invoices']))})
        out.append({'_kind': 'email', 'group_key': g['group_key'], 'customer_key': g['customer_key'], 'stage': g['stage'], 'customer_name': g['customer_name'], 'to': g['to'],
                    'subject': subject, 'body': render(m['body'], vars_, g['invoices']), 'new_deadline': new_deadline if g['stage'] == 2 else '',
                    'final_deadline': final_deadline if g['stage'] == 3 else '', 'invoices': g['invoices']})
    return out


def collect(emails, today, now_iso, cfg, skipped, warnings, gmail_ids):
    mode = cfg['SEND_MODE']
    summary = {'date': today.isoformat(), 'mode': mode, 'n': 0, 'emails_ok': 0, 'emails_failed': 0, 'items': [], 'failed': [], 'escalated': [], 'skipped': skipped,
               'warnings': warnings, 'today_override': cfg['TODAY_OVERRIDE']}
    updates, log_rows = [], []
    for idx, em in enumerate(emails):
        for inv in em['invoices']:
            summary['items'].append({'customer_name': em['customer_name'], 'invoice_id': inv['invoice_id'], 'remaining': inv['remaining'], 'stage': em['stage'], 'to': em['to'], 'ok': True})
        summary['emails_ok'] += 1; summary['n'] += 1
        if mode == 'owner_only':
            continue
        mid = gmail_ids[idx % len(gmail_ids)]
        for inv in em['invoices']:
            log_rows.append({'_kind': 'log_row', 'invoice_id': inv['invoice_id'], 'stage': em['stage'], 'mode': 'sent' if mode == 'send' else 'draft', 'channel': 'gmail',
                             'to': em['to'], 'subject': em['subject'], 'sent_at': now_iso, 'gmail_message_id': mid})
            updates.append({'_kind': 'invoice_update', 'invoice_id': inv['invoice_id'], 'status': 'escalated' if em['stage'] == 3 else inv['status'],
                            'remind_stage': max(inv['remind_stage'], em['stage']), 'last_reminded_at': now_iso})
            if em['stage'] == 3:
                summary['escalated'].append({'invoice_id': inv['invoice_id'], 'customer_name': em['customer_name'], 'remaining': inv['remaining'], 'due_date': inv['due_date'],
                                             'days_overdue': inv['days_overdue'], 'final_deadline': em['final_deadline']})
    return updates, log_rows, summary


def owner_notice(summary, cfg):
    lang = 'en' if cfg['LANG'] == 'en' else 'ja'
    M = MSG_EN if lang == 'en' else MSG_JA
    s = summary
    if not (s['n'] > 0 or s['failed'] or s['escalated'] or s['warnings']):
        return []
    mx = num(cfg['NOTIFY_MAX_LINES']) or 40
    cap = lambda lines: lines[:mx] + [f'…+{len(lines) - mx}'] if len(lines) > mx else lines
    head = []
    if s_(s['today_override']):
        head.append(f"TODAY_OVERRIDE={s['today_override']}")
    if s['mode'] != 'draft':
        head.append(f"SEND_MODE={s['mode']}")
    ok = cap([fill(M['draft_summary']['line_item'], {'customer_name': i['customer_name'], 'invoice_id': i['invoice_id'], 'remaining': yen(i['remaining']), 'stage': i['stage']}) for i in s['items'] if i['ok']])
    failed = cap([f"✗ {f['to']} | {', '.join(f['invoice_ids'])} | {f['error']}" for f in s['failed']])
    warn = cap(['・' + ' '.join(str(w[k]) for k in ('type', 'invoice_id', 'currency', 'value', 'detail') if w.get(k)) for w in s['warnings']])
    title = fill(M['draft_summary']['title'], {'date': s['date'], 'n': s['n']})
    sections = [x for x in ['\n'.join(head), '\n'.join(ok), '\n'.join(['■ failed'] + failed) if failed else '', '\n'.join(['■ warnings'] + warn) if warn else ''] if x]
    out = [{'title': title, 'body_text': '\n\n'.join([title] + sections).strip()}]
    for e in s['escalated']:
        v = {'invoice_id': e['invoice_id'], 'customer_name': e['customer_name'], 'remaining': yen(e['remaining']), 'due_date': e['due_date'], 'days_overdue': e['days_overdue'], 'final_deadline': e['final_deadline']}
        t = fill(M['escalated']['title'], v)
        out.append({'title': t, 'body_text': '\n\n'.join([t, fill(M['escalated']['body'], v)]).strip()})
    return out


def load_config(overrides):
    cfg = dict(CONFIG_DEFAULTS)
    p = os.path.join(HERE, 'config.examples.json')
    if os.path.exists(p):
        with open(p, encoding='utf-8') as f:
            cfg.update(json.load(f).get('test_common', {}))
    cfg.update(overrides or {})
    return cfg


def expected(invoices, log_rows, today, cfg):
    now_iso = iso(today, NOW_TIME)
    cands, skipped, warnings = select_due(invoices, log_rows, today, cfg)
    groups = group_by_customer(cands, cfg)
    emails = build_emails(groups, today, cfg)
    gmail_ids = [f'18f7{n:012x}' for n in range(1, 9)]                     # matches fixtures/gmail_pinned.example.json (draft: message.id / send: id)
    updates, logs, summary = collect(emails, today, now_iso, cfg, skipped, warnings, gmail_ids)
    notices = owner_notice(summary, cfg)
    return {'today': today.isoformat(), 'now_iso': now_iso, 'candidates': cands, 'skipped': skipped, 'warnings': warnings, 'groups': groups, 'emails': emails,
            'invoice_updates': updates, 'log_rows': logs, 'summary': {k: v for k, v in summary.items() if k not in ('skipped', 'warnings')}, 'owner_notices': notices}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--today', default=DEFAULT_TODAY, help=f'run date yyyy-MM-dd that the offsets are relative to (default {DEFAULT_TODAY})')
    ap.add_argument('--out-dir', default=HERE, help='directory to write invoices.seed.csv / reminders_log.seed.csv into (default: this directory)')
    ap.add_argument('--check', action='store_true', help='do not write; exit 1 if the generated CSVs differ from the files in --out-dir')
    ap.add_argument('--expected', action='store_true', help='print the expected outcome (JSON) for --today with the DESIGN.md §4 defaults + config.examples.json test_common')
    ap.add_argument('--config', help='JSON object of Config overrides applied on top of the defaults for --expected (e.g. \'{"LANG":"en"}\')')
    ap.add_argument('--run-date', help='for --expected only: evaluate the seed built for --today as if the workflow ran on this date (TODAY_OVERRIDE), e.g. U06-b / U15 / U17-b')
    a = ap.parse_args()
    today = parse_today(a.today)
    run_date = parse_today(a.run_date) if a.run_date else today
    invoices, log_rows = build_rows(today)
    files = {'invoices.seed.csv': to_csv(invoices, INVOICE_COLUMNS), 'reminders_log.seed.csv': to_csv(log_rows, LOG_COLUMNS)}

    # warn when the chosen date is not a business day under the default Config (the run would end in Skip Non-Business Day, U09 / U21)
    hol = os.path.join(HERE, 'holidays.example.json')
    holidays = set()
    if os.path.exists(hol):
        with open(hol, encoding='utf-8') as f:
            holidays = set(json.load(f).get('HOLIDAYS', []))
    if today.weekday() >= 5 or today.isoformat() in holidays:
        why = 'weekend' if today.weekday() >= 5 else 'a Japanese public holiday (fixtures/holidays.example.json)'
        print(f'note: {today} is {why}; with the default Config the workflow ends in Skip Non-Business Day (CASES U09 / U21). '
              f'Pick a business day, set SKIP_WEEKENDS=false or edit HOLIDAYS for the reminder cases.', file=sys.stderr)

    if a.check:
        bad = 0
        for name, text in files.items():
            p = os.path.join(a.out_dir, name)
            on_disk = open(p, encoding='utf-8', newline='').read() if os.path.exists(p) else None
            status = 'OK' if on_disk == text else ('MISSING' if on_disk is None else 'DIFF')
            bad += status != 'OK'
            print(f'{status}: {p}')
        if bad:
            sys.exit(1)
    else:
        os.makedirs(a.out_dir, exist_ok=True)
        for name, text in files.items():
            p = os.path.join(a.out_dir, name)
            with open(p, 'w', encoding='utf-8', newline='') as f:
                f.write(text)
            print(f'wrote {p} ({text.count(chr(10)) - 1} rows, TODAY={today})')
    if a.expected:
        cfg = load_config(json.loads(a.config) if a.config else None)
        cfg['TODAY_OVERRIDE'] = run_date.isoformat()
        print(json.dumps(expected(invoices, log_rows, run_date, cfg), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
