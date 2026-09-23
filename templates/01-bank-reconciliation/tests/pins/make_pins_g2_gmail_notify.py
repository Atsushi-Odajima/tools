#!/usr/bin/env python3
"""P3 pins for the g2-gmail-notify cases (R10-idempotent, R11, R13, R17, R23). Python 3 standard library only.

Standalone companion of make_pins.py: it derives every file from the EXISTING pins (drive.pin.json / gmail.pin.json, which are
not modified) plus the Config defaults in build/build_workflow.py and fixtures/, and writes only files whose name starts with a case id.
Sink URLs are the same as make_pins.py (p0-sink / p2-chatwork); tests/results/g2-gmail-notify.md documents the runtime override to an
agent-specific Chatwork sink. Existing pins are never rewritten by this script.

usage: PYTHONDONTWRITEBYTECODE=1 python3 tests/pins/make_pins_g2_gmail_notify.py [--txn-rows <json of the R10 txn_row items>]
"""
import argparse
import base64
import copy
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location('build_workflow', os.path.join(TPL, 'build', 'build_workflow.py'))
bw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bw)

ap = argparse.ArgumentParser()
ap.add_argument('--txn-rows', help='JSON array of the txn_row items (without _kind) written by the first Gmail run (R10); when given, R10-idempotent-gmail-second-run.pin.json is (re)written')
a = ap.parse_args()


def load(name):
    with open(os.path.join(HERE, name), encoding='utf-8') as f:
        return json.load(f)


drive = load('drive.pin.json')          # R01-R08 base: Config NOTIFY_CHANNELS = ["line","chatwork"], sinks p0-sink / p2-chatwork
gmail = load('gmail.pin.json')          # R10 base
ok = [{'json': {'ok': True}}]


def with_config(pin, extra, nodes=None):
    p = copy.deepcopy(pin)
    for it in p['Config']:
        it['json'].update(extra)
    if nodes:
        p.update(nodes)
    return p


pins = {
    # R11: only the configured channels run. Slack / Gmail nodes are pinned (no credentials, BLOCKERS H2); LINE / Chatwork must not execute.
    'R11-slack.pin.json': with_config(drive, {'NOTIFY_CHANNELS': ['slack']}, {'Notify Slack': ok}),
    'R11-email.pin.json': with_config(drive, {'NOTIFY_CHANNELS': ['email']}, {'Notify Email': ok}),
    'R11-all-four.pin.json': with_config(drive, {'NOTIFY_CHANNELS': ['slack', 'email', 'line', 'chatwork']}, {'Notify Slack': ok, 'Notify Email': ok}),
    'R11-none.pin.json': with_config(drive, {'NOTIFY_CHANNELS': []}),
}

# R13: bank_B_utf8bom.csv with the B mapping from fixtures/csv_mapping.examples.json (date_format = yyyyMMdd, encoding = utf-8)
with open(os.path.join(TPL, 'fixtures', 'csv_mapping.examples.json'), encoding='utf-8') as f:
    mapping_b = json.load(f)['bank_B_utf8bom.csv']
with open(os.path.join(TPL, 'fixtures', 'bank_B_utf8bom.csv'), 'rb') as f:
    b_b64 = base64.b64encode(f.read()).decode()
trig_b = {'id': 'file_test_B01', 'name': 'bank_B_utf8bom.csv', 'mimeType': 'text/csv'}
r13 = with_config(drive, {'CSV_MAPPING': mapping_b, **trig_b})
r13['Watch Drive Folder'] = [{'json': trig_b}]
r13['Download File'] = [{'json': {'name': 'bank_B_utf8bom.csv', 'mimeType': 'text/csv'},
                         'binary': {'data': {'data': b_b64, 'mimeType': 'text/csv', 'fileName': 'bank_B_utf8bom.csv'}}}]
pins['R13-bank-B.pin.json'] = r13

# R17: two mails that match no parser / match bankX without captures (CASES.md R17 a / b)
mails17 = [
    {'json': {'id': '18f3aabb00000009', 'date': '2026-09-20T10:00:00+09:00', 'from': {'text': 'someone@example.org'},
              'subject': '会議のご案内', 'text': '来週の会議についてご連絡します。'}},
    {'json': {'id': '18f3aabb00000010', 'date': '2026-09-20T10:05:00+09:00', 'from': {'text': 'サンプル銀行 <notice@example.jp>'},
              'subject': '【サンプル銀行】ご入金のお知らせ', 'text': '本日の入金はありません。'}},
]
r17 = copy.deepcopy(gmail)
r17['Watch Gmail Inbox'] = mails17
base_cfg = {k: v for k, v in gmail['Config'][0]['json'].items() if k in bw.main_config() or k == 'SOURCE'}
r17['Config'] = [{'json': {**m['json'], **base_cfg}} for m in mails17]
pins['R17-parser-mismatch.pin.json'] = r17

# R23: invoices seed + one USD invoice with the same amount as bank_A row 5 (128,000) → must be excluded with a non_jpy_invoice warning
inv022 = {'invoice_id': 'INV-2026-022', 'customer_id': 'C-019', 'customer_name': 'Sample Overseas LLC', 'payer_name_alias': 'サンプルオーバーシーズ',
          'customer_email': 'overseas@example.com', 'amount': 128000, 'currency': 'USD', 'issue_date': '2026-09-01', 'due_date': '2026-09-30',
          'status': 'unpaid', 'paid_amount': 0, 'paid_date': '', 'matched_txn_ids': '', 'match_confidence': '', 'fee_deducted': 0,
          'remind_stage': 0, 'last_reminded_at': '', 'promised_date': '', 'do_not_remind': 'FALSE', 'notes': 'R23 non-JPY invoice (pinned only)'}
r23 = copy.deepcopy(drive)
r23['Read Invoices'] = drive['Read Invoices'] + [{'json': inv022}]
pins['R23-non-jpy.pin.json'] = r23
# R23-b: same invoices from the Schedule trigger, ledger = transactions.seed (1 matched row) → nothing re-matched → Build Notification []
sched = load('schedule.pin.json')
r23b = copy.deepcopy(sched)
r23b['Read Invoices'] = drive['Read Invoices'] + [{'json': inv022}]
pins['R23-b-non-jpy-schedule.pin.json'] = r23b

# R10-idempotent: the same two mails again with Read Transactions = transactions.seed + the 2 txn rows of the first run
if a.txn_rows:
    with open(a.txn_rows, encoding='utf-8') as f:
        rows = json.load(f)
    second = copy.deepcopy(gmail)
    second['Read Transactions'] = sched['Read Transactions'] + [{'json': {k: v for k, v in r.items() if k != '_kind'}} for r in rows]
    pins['R10-idempotent-gmail-second-run.pin.json'] = second

for name, pin in pins.items():
    with open(os.path.join(HERE, name), 'w', encoding='utf-8') as f:
        json.dump(pin, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('wrote', name, sorted(pin.keys()))
