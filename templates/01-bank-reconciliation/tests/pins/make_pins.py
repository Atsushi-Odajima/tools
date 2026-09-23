#!/usr/bin/env python3
"""Generate the pinned-data files in tests/pins/ (see tests/pins/README.md). Python 3 standard library only.

The pins let the registered workflow run end-to-end in a local n8n without Google / Slack / Gmail credentials:
every Google node is pinned, the notification channels are LINE + Chatwork (HTTP Request) pointed at local webhook sinks
or at an unreachable address, and `Config` is pinned with the DESIGN.md §4 defaults plus the smoke overrides.

usage: python3 tests/pins/make_pins.py [--line-url URL] [--chatwork-base-url URL] [--dead-url URL]
"""
import argparse
import base64
import csv
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location('build_workflow', os.path.join(TPL, 'build', 'build_workflow.py'))
bw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bw)

ap = argparse.ArgumentParser()
ap.add_argument('--line-url', default='http://localhost:5678/webhook/p0-sink')
ap.add_argument('--chatwork-base-url', default='http://localhost:5678/webhook/p2-chatwork')
ap.add_argument('--dead-url', default='http://127.0.0.1:9')
ap.add_argument('--txn-rows', help='JSON array of the txn_row items (without _kind) written by a first Drive run; when given, drive-second-run.pin.json is (re)written')
a = ap.parse_args()
SINK_LINE, SINK_CW, DEAD = a.line_url, a.chatwork_base_url, a.dead_url


def config(source, trigger_json, line=SINK_LINE, chatwork=SINK_CW, extra=None):
    """Config output: one item per trigger item (Set 'include all input fields' keeps the trigger fields), SOURCE = trigger name."""
    items = trigger_json if isinstance(trigger_json, list) else [trigger_json]
    out = []
    for t in items:
        c = dict(t)
        c.update(bw.main_config())
        c['SOURCE'] = source
        c.update({'NOTIFY_CHANNELS': ['line', 'chatwork'], 'LINE_TO_USER_ID': 'Utest', 'CHATWORK_ROOM_ID': '1', 'SHEET_ID': 'TEST_SHEET',
                  'LINE_API_URL': line, 'CHATWORK_API_BASE_URL': chatwork})
        if extra:
            c.update(extra)
        out.append({'json': c})
    return out


def sheet_rows(name):
    """fixtures/*.seed.csv → Google Sheets 'Get Row(s)'-shaped items (numeric columns as numbers, everything else as strings)."""
    with open(os.path.join(TPL, 'fixtures', name), encoding='utf-8', newline='') as f:
        out = []
        for r in csv.DictReader(f):
            j = {k: (int(v) if k in ('amount', 'paid_amount', 'fee_deducted', 'remind_stage') and v != '' else v) for k, v in r.items()}
            out.append({'json': j})
        return out


drive_trig = {'id': 'file_test_001', 'name': 'bank_A_sjis.csv', 'mimeType': 'text/csv'}
pdf_trig = {'id': 'file_test_002', 'name': 'memo.pdf', 'mimeType': 'application/pdf'}
with open(os.path.join(TPL, 'fixtures', 'bank_A_sjis.csv'), 'rb') as f:
    csv_b64 = base64.b64encode(f.read()).decode()
download = [{'json': {'name': 'bank_A_sjis.csv', 'mimeType': 'text/csv'},
             'binary': {'data': {'data': csv_b64, 'mimeType': 'text/csv', 'fileName': 'bank_A_sjis.csv'}}}]
with open(os.path.join(TPL, 'fixtures', 'mail_pinned.example.json'), encoding='utf-8') as f:
    gmail_items = json.load(f)['items']
# D31: a second CSV created in the same Drive poll (derived from the A header: one deposit that matches nothing + one withdrawal, cp932)
second_rows = [['日付', '摘要', '入金額', '出金額', '残高'], ['2026/09/16', '振込 ﾆﾏｲﾒ ﾃｽﾄ', '1,000', '', '1,000'], ['2026/09/17', '引落 ﾃｽﾄ', '', '3,000', '-2,000']]
second_csv = ('\r\n'.join(','.join(f'"{c}"' if ',' in c else c for c in r) for r in second_rows) + '\r\n').encode('cp932')
second_trig = {'id': 'file_test_003', 'name': 'bank_A_second.csv', 'mimeType': 'text/csv'}
download_two = download + [{'json': {'name': 'bank_A_second.csv', 'mimeType': 'text/csv'},
                            'binary': {'data': {'data': base64.b64encode(second_csv).decode(), 'mimeType': 'text/csv', 'fileName': 'bank_A_second.csv'}}}]
# D22: a Google Sheet that Drive converted on upload: trigger mimeType = spreadsheet, Download File exports UTF-8 CSV (no BOM) and
# passes the trigger json through (download.operation.js `json: item.json`)
sheet_trig = {'id': 'file_test_004', 'name': 'bank_A_sjis', 'mimeType': 'application/vnd.google-apps.spreadsheet'}
with open(os.path.join(TPL, 'fixtures', 'bank_A_sjis.csv'), 'rb') as f:
    sheet_b64 = base64.b64encode(f.read().decode('cp932').encode('utf-8')).decode()
download_sheet = [{'json': dict(sheet_trig), 'binary': {'data': {'data': sheet_b64, 'mimeType': 'text/csv', 'fileName': 'bank_A_sjis.csv'}}}]
sched_trig = {'timestamp': '2026-09-24T09:00:00.000+09:00'}
invoices = sheet_rows('invoices.seed.csv')
transactions = sheet_rows('transactions.seed.csv')
empty_sheet = [{'json': {}}]                    # Always Output Data on an empty sheet
ok = [{'json': {'ok': True}}]                   # dummy so the write nodes do not execute

google = {'Read Invoices': invoices, 'Read Transactions': empty_sheet, 'Update Invoices': ok, 'Upsert Transactions': ok}
pins = {
    'drive.pin.json': {'Watch Drive Folder': [{'json': drive_trig}], 'Download File': download, 'Config': config('Watch Drive Folder', drive_trig), **google},
    'drive-realconfig.pin.json': {'Watch Drive Folder': [{'json': drive_trig}], 'Download File': download, **google,
                                  'Notify Slack': ok},                        # Config NOT pinned: the real Set node runs (default NOTIFY_CHANNELS = ["slack"])
    'gmail.pin.json': {'Watch Gmail Inbox': gmail_items, 'Config': config('Watch Gmail Inbox', [g['json'] for g in gmail_items]), **google},
    'gmail-realconfig.pin.json': {'Watch Gmail Inbox': gmail_items, **google, 'Notify Slack': ok},   # Config NOT pinned (2 trigger items → 2 Config items)
    'schedule.pin.json': {'Run Daily Rematch': [{'json': sched_trig}], 'Config': config('Run Daily Rematch', sched_trig), **google, 'Read Transactions': transactions},
    'drive-nonecsv.pin.json': {'Watch Drive Folder': [{'json': pdf_trig}], 'Download File': download, 'Config': config('Watch Drive Folder', pdf_trig), **google},
    'notify-partial-fail.pin.json': {'Watch Drive Folder': [{'json': drive_trig}], 'Download File': download,
                                     'Config': config('Watch Drive Folder', drive_trig, line=SINK_LINE, chatwork=DEAD), **google},
    'notify-all-fail.pin.json': {'Watch Drive Folder': [{'json': drive_trig}], 'Download File': download,
                                 'Config': config('Watch Drive Folder', drive_trig, line=DEAD, chatwork=DEAD), **google},
    'gmail-disabled.pin.json': {'Watch Gmail Inbox': gmail_items, **google,
                                'Config': config('Watch Gmail Inbox', [g['json'] for g in gmail_items], extra={'TRIGGERS_ENABLED': {'drive': True, 'gmail': False, 'schedule': True}})},
    'unknown-source.pin.json': {'Watch Drive Folder': [{'json': drive_trig}], 'Download File': download, 'Config': config('Manual', drive_trig), **google},
    'drive-two-files.pin.json': {'Watch Drive Folder': [{'json': drive_trig}, {'json': second_trig}], 'Download File': download_two,
                                 'Config': config('Watch Drive Folder', [drive_trig, second_trig]), **google},
    'drive-sheet-export.pin.json': {'Watch Drive Folder': [{'json': sheet_trig}], 'Download File': download_sheet,
                                    'Config': config('Watch Drive Folder', sheet_trig), **google},
}
# second Drive run (R09): Read Transactions = seed + the 11 txn rows written by the first run (transactions columns only).
# The rows come from a real first execution (--txn-rows), so the file is only rewritten when that argument is given.
if a.txn_rows:
    with open(a.txn_rows, encoding='utf-8') as f:
        rows = json.load(f)
    second = json.loads(json.dumps(pins['drive.pin.json']))
    second['Read Transactions'] = transactions + [{'json': {k: v for k, v in r.items() if k != '_kind'}} for r in rows]
    pins['drive-second-run.pin.json'] = second
    # schedule re-match (CASES R18): ledger = seed + the 11 rows of the first run; invoices = seed + the buyer's new INV-2026-021
    # (66,000 JPY, alias ミホンシヨウカイ) → the unmatched row 2026-09-11|66000|ミホンシヨウカイ| becomes matched, rematched = 1
    inv021 = {'invoice_id': 'INV-2026-021', 'customer_id': 'C-009', 'customer_name': '株式会社見本商会', 'payer_name_alias': 'カ)ミホンシヨウカイ,ミホンシヨウカイ',
              'customer_email': 'shokai@example.jp', 'amount': 66000, 'currency': 'JPY', 'issue_date': '2026-09-15', 'due_date': '2026-10-15',
              'status': 'unpaid', 'paid_amount': 0, 'paid_date': '', 'matched_txn_ids': '', 'match_confidence': '', 'fee_deducted': 0,
              'remind_stage': 0, 'last_reminded_at': '', 'promised_date': '', 'do_not_remind': 'FALSE', 'notes': 'R18 registered after bank_A'}
    pins['schedule-rematch.pin.json'] = {'Run Daily Rematch': [{'json': sched_trig}], 'Config': config('Run Daily Rematch', sched_trig), **google,
                                         'Read Invoices': invoices + [{'json': inv021}], 'Read Transactions': second['Read Transactions']}

# error handler: Error Trigger pinned with the example item of the n8n Error Trigger docs, its own Config with LINE + Chatwork
err_item = {'execution': {'id': '231', 'url': 'https://n8n.example.com/execution/231', 'retryOf': '34',
                          'error': {'message': 'Example Error Message', 'stack': 'Stacktrace'}, 'lastNodeExecuted': 'Node With Error', 'mode': 'manual'},
            'workflow': {'id': '1', 'name': 'Example Workflow'}}
ecfg = bw.error_config()
ecfg.update({'NOTIFY_CHANNELS': ['line', 'chatwork'], 'LINE_TO_USER_ID': 'Utest', 'CHATWORK_ROOM_ID': '1', 'LINE_API_URL': SINK_LINE, 'CHATWORK_API_BASE_URL': SINK_CW})
pins['error-handler.pin.json'] = {'Catch Workflow Error': [{'json': err_item}], 'Config': [{'json': {**err_item, **ecfg}}]}

for name, pin in pins.items():
    with open(os.path.join(HERE, name), 'w', encoding='utf-8') as f:
        json.dump(pin, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('wrote', name, sorted(pin.keys()))
