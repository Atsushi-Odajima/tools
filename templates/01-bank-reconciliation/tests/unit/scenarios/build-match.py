#!/usr/bin/env python3
# Builds the unit-test scenarios for the Code node "Match Invoices" (code/match_invoices.js, DESIGN.md §6.7) from the REAL
# fixtures in ../../../fixtures/ (via the existing normalize_payer scenarios, which were built from the fixture bytes).
#
#   [NODE_BIN=/path/to/node] [LUXON_PATH=/path/to/node_modules/luxon] python3 tests/unit/scenarios/build-match.py
#                                                                  # rewrites scenarios/match_invoices/*.json
#
# Scenario file = { "input": [item], "nodes": { "Config": [item] }, "now": "...", "expect": {...} }.
# "input" is the ONE item Normalize Payer emits (DESIGN §3.5). It is produced by running the real code/normalize_payer.js
# through tests/unit/run-code-node.mjs on the normalize_payer scenarios (bank_A_seed / bank_B_seed / mail_XY_seed /
# empty_*), or on scenarios derived from them here (extra invoice rows, ledger state after a first run, schedule source).
# The EXPECTED values are NOT computed by match_invoices.js: they are transcribed from fixtures/README.md §2–§6 and
# tests/CASES.md (R01–R06, R09, R13, R14, R18, R19, R23). Where a scenario needs "the ledger after a first run" as INPUT
# (R09 / R18 / R19), the txn rows come from a first run of match_invoices.js, but every assertion stays on the output of
# the run under test.
#
# expect (read by tests/unit/test-match_invoices.sh):
#   length            total item count
#   count             { "<_kind>": n }  number of items per _kind
#   paths             { "<path into the output array>": <deep-equal value> }
#   absent            [ "<path>", ... ]  must be undefined
#   rows              [ { "match": {<json fields that select exactly one item>}, "equals": {<json fields>}, "absent": [fields] } ]
#   no_rows           [ {<json fields>} ]  no item may match these fields
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
UNIT = os.path.abspath(os.path.join(HERE, '..'))
TPL = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
FX = os.path.join(TPL, 'fixtures')
NODE_BIN = os.environ.get('NODE_BIN', 'node')
LUXON = os.environ.get('LUXON_PATH', '')
RUNNER = os.path.join(UNIT, 'run-code-node.mjs')
NORMALIZE_JS = os.path.join(TPL, 'code', 'normalize_payer.js')
MATCH_JS = os.path.join(TPL, 'code', 'match_invoices.js')
NOW = '2026-09-23T09:00:00+09:00'          # run under test
NOW_FIRST = '2026-09-22T09:00:00+09:00'    # "yesterday": the first run whose ledger rows feed R09 / R18 / R19
IMPORTED_AT_FIRST = NOW_FIRST


def run_node(src, scenario):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(scenario, f, ensure_ascii=False)
        path = f.name
    try:
        cmd = [NODE_BIN, RUNNER, src, '-', path] + (['--luxon', LUXON] if LUXON else [])
        out = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        if out.returncode != 0:
            sys.stderr.write(out.stderr)
            raise SystemExit(f'runner failed for {os.path.basename(src)}')
        return json.loads(out.stdout)
    finally:
        os.unlink(path)


def load_np(name):
    with open(os.path.join(HERE, 'normalize_payer', name + '.json'), encoding='utf-8') as f:
        return json.load(f)


def item(j):
    return {'json': j}


def normalize(np_scenario):
    """Run the real Normalize Payer on a normalize_payer scenario → the single item Match Invoices receives."""
    out = run_node(NORMALIZE_JS, {'input': np_scenario['input'], 'nodes': np_scenario['nodes'], 'now': np_scenario.get('now', NOW)})
    assert len(out) == 1, 'Normalize Payer must emit exactly one item'
    return out[0]


def match(np_scenario, now):
    """First run of Match Invoices (only used to derive LEDGER INPUT for later scenarios, never for expectations)."""
    cfg = np_scenario['nodes']['Config']
    return run_node(MATCH_JS, {'input': [normalize(np_scenario)], 'nodes': {'Config': cfg}, 'now': now})


def strip_kind(j):
    return {k: v for k, v in j.items() if k != '_kind'}


def with_source(np_scenario, source_node, collect):
    """Copy of a normalize_payer scenario with another trigger source and Collect Transactions output."""
    sc = json.loads(json.dumps(np_scenario))
    sc['nodes']['Config'][0]['json']['SOURCE'] = source_node
    sc['nodes']['Collect Transactions'] = [item(collect)]
    return sc


def write(name, data):
    d = os.path.join(HERE, 'match_invoices')
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name + '.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('wrote', os.path.relpath(os.path.join(d, name + '.json'), TPL))


# ---------------------------------------------------------------------------------------------------------------
# Oracle: fixtures/README.md §2 / §4 / §5 / §6 and tests/CASES.md — transcribed by hand
# ---------------------------------------------------------------------------------------------------------------
def inv_update(invoice_id, status, paid_amount, paid_date, matched_txn_ids, confidence, fee):
    return {'match': {'_kind': 'invoice_update', 'invoice_id': invoice_id},
            'equals': {'status': status, 'paid_amount': paid_amount, 'paid_date': paid_date, 'matched_txn_ids': matched_txn_ids,
                       'match_confidence': confidence, 'fee_deducted': fee}}


def txn_row(txn_id, source, txn_date, raw, norm, amount, memo, matched, status, suggested, imported_at=NOW):
    return {'match': {'_kind': 'txn_row', 'txn_id': txn_id},
            'equals': {'source': source, 'txn_date': txn_date, 'payer_name_raw': raw, 'payer_name_norm': norm, 'amount': amount,
                       'memo': memo, 'matched_invoice_ids': matched, 'status': status, 'suggested_invoice_ids': suggested,
                       'imported_at': imported_at}}


def summary(**kw):
    return {'match': {'_kind': 'summary'}, 'equals': kw}


# bank_A_sjis.csv against the seed (fixtures/README.md §4, CASES R01–R06)
A_INV = [
    inv_update('INV-2026-001', 'paid', 33000, '2026-09-01', '2026-09-01|33000|サンプルシヨウジ|', 'auto', 0),
    inv_update('INV-2026-002', 'paid', 54780, '2026-09-02', '2026-09-02|54780|テストコウギヨウ|', 'fee_deducted', 220),
    inv_update('INV-2026-003', 'paid', 9800, '2026-09-03', '2026-09-03|9800|ヤマダタロウ|', 'auto', 0),
    inv_update('INV-2026-004', 'paid', 128000, '2026-09-04', '2026-09-04|128000|サトウケイコ|', 'amount_only', 0),
    inv_update('INV-2026-005', 'paid', 700000, '2026-09-05', '2026-09-05|1234567|テストブツサン|', 'combined', 0),
    inv_update('INV-2026-006', 'paid', 534567, '2026-09-05', '2026-09-05|1234567|テストブツサン|', 'combined', 0),
    inv_update('INV-2026-007', 'partial', 100000, '2026-09-08', '2026-09-08|100000|サンプルシステム|', 'auto', 0),
    inv_update('INV-2026-012', 'paid', 27500, '2026-09-14', '2026-09-14|27500|サンプルフーズトウキヨウ|', 'auto', 0),
]
A_TXN = [
    txn_row('2026-09-01|33000|サンプルシヨウジ|', 'bank_csv', '2026-09-01', '振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ', 'サンプルシヨウジ', 33000, '', 'INV-2026-001', 'matched', ''),
    txn_row('2026-09-02|54780|テストコウギヨウ|', 'bank_csv', '2026-09-02', '振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ', 'テストコウギヨウ', 54780, '', 'INV-2026-002', 'matched', ''),
    txn_row('2026-09-03|9800|ヤマダタロウ|', 'bank_csv', '2026-09-03', 'フリコミ　ヤマダ　タロウ', 'ヤマダタロウ', 9800, '', 'INV-2026-003', 'matched', ''),
    txn_row('2026-09-04|128000|サトウケイコ|', 'bank_csv', '2026-09-04', '振込 ｻﾄｳ ｹｲｺ', 'サトウケイコ', 128000, '', 'INV-2026-004', 'matched', ''),
    txn_row('2026-09-05|1234567|テストブツサン|', 'bank_csv', '2026-09-05', '振込 ｶ)ﾃｽﾄﾌﾞﾂｻﾝ', 'テストブツサン', 1234567, '', 'INV-2026-005,INV-2026-006', 'matched', ''),
    txn_row('2026-09-08|100000|サンプルシステム|', 'bank_csv', '2026-09-08', '振込 ｻﾝﾌﾟﾙｼｽﾃﾑ(ｶ', 'サンプルシステム', 100000, '', 'INV-2026-007', 'matched', ''),
    txn_row('2026-09-09|44000|オオバマサオ|', 'bank_csv', '2026-09-09', '振込 ｵｵﾊﾞ ﾏｻｵ', 'オオバマサオ', 44000, '', '', 'ambiguous', 'INV-2026-008,INV-2026-009'),
    txn_row('2026-09-11|66000|ミホンシヨウカイ|', 'bank_csv', '2026-09-11', '振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ', 'ミホンシヨウカイ', 66000, '', '', 'unmatched', 'INV-2026-015,INV-2026-017'),
    txn_row('2026-09-12|88000|テストケンセツ|', 'bank_csv', '2026-09-12', '振込 ﾃｽﾄｹﾝｾﾂ(ｶ', 'テストケンセツ', 88000, '', '', 'unmatched', ''),
    txn_row('2026-09-14|27500|サンプルフーズトウキヨウ|', 'bank_csv', '2026-09-14', '振込 ｶ)ｻﾝﾌﾟﾙﾌｰｽﾞﾄｳｷﾖｳ', 'サンプルフーズトウキヨウ', 27500, '', 'INV-2026-012', 'matched', ''),
    txn_row('2026-09-15|5500|ナカムラジロウ|', 'bank_csv', '2026-09-15', '振込 ﾅｶﾑﾗ ｼﾞﾛｳ', 'ナカムラジロウ', 5500, '', '', 'unmatched', 'INV-2026-014'),
]
A_SUMMARY = dict(date='2026-09-23', source='drive', file_name='bank_A_sjis.csv', n=11, a=4, b=3, c=4, rematched=0,
                 skipped_existing=0, skipped_duplicate_in_batch=0, ignored_withdraw=4, warnings=[])
A_UNTOUCHED = ['INV-2026-008', 'INV-2026-009', 'INV-2026-010', 'INV-2026-011', 'INV-2026-013', 'INV-2026-014', 'INV-2026-015',
               'INV-2026-016', 'INV-2026-017', 'INV-2026-018', 'INV-2026-019', 'INV-2026-020']
A_LINE = {  # CASES §3 notification detail (summary lists), reason / fee / remaining_after / candidates
    'auto': [
        {'txn_date': '2026-09-01', 'payer_raw': '振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ', 'amount': 33000, 'source': 'bank_csv', 'invoice_ids': ['INV-2026-001'], 'reason': 'auto', 'fee': 0, 'remaining_after': 0},
        {'txn_date': '2026-09-03', 'payer_raw': 'フリコミ　ヤマダ　タロウ', 'amount': 9800, 'source': 'bank_csv', 'invoice_ids': ['INV-2026-003'], 'reason': 'auto', 'fee': 0, 'remaining_after': 0},
        {'txn_date': '2026-09-08', 'payer_raw': '振込 ｻﾝﾌﾟﾙｼｽﾃﾑ(ｶ', 'amount': 100000, 'source': 'bank_csv', 'invoice_ids': ['INV-2026-007'], 'reason': 'partial', 'fee': 0, 'remaining_after': 150000},
        {'txn_date': '2026-09-14', 'payer_raw': '振込 ｶ)ｻﾝﾌﾟﾙﾌｰｽﾞﾄｳｷﾖｳ', 'amount': 27500, 'source': 'bank_csv', 'invoice_ids': ['INV-2026-012'], 'reason': 'auto', 'fee': 0, 'remaining_after': 0},
    ],
    'needs_review': [
        {'txn_date': '2026-09-02', 'payer_raw': '振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ', 'amount': 54780, 'source': 'bank_csv', 'invoice_ids': ['INV-2026-002'], 'reason': 'fee_deducted', 'fee': 220, 'remaining_after': 0},
        {'txn_date': '2026-09-04', 'payer_raw': '振込 ｻﾄｳ ｹｲｺ', 'amount': 128000, 'source': 'bank_csv', 'invoice_ids': ['INV-2026-004'], 'reason': 'amount_only', 'fee': 0, 'remaining_after': 0},
        {'txn_date': '2026-09-05', 'payer_raw': '振込 ｶ)ﾃｽﾄﾌﾞﾂｻﾝ', 'amount': 1234567, 'source': 'bank_csv', 'invoice_ids': ['INV-2026-005', 'INV-2026-006'], 'reason': 'combined', 'fee': 0, 'remaining_after': 0},
    ],
    'ambiguous': [
        {'txn_date': '2026-09-09', 'payer_raw': '振込 ｵｵﾊﾞ ﾏｻｵ', 'amount': 44000, 'source': 'bank_csv', 'reason': 'same_amount_multiple',
         'candidates': [{'invoice_id': 'INV-2026-008', 'remaining': 44000}, {'invoice_id': 'INV-2026-009', 'remaining': 44000}]},
    ],
    'unmatched': [
        {'txn_date': '2026-09-11', 'payer_raw': '振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ', 'amount': 66000, 'source': 'bank_csv', 'reason': 'no_candidate',
         'candidates': [{'invoice_id': 'INV-2026-015', 'remaining': 57200}, {'invoice_id': 'INV-2026-017', 'remaining': 49500}]},
        {'txn_date': '2026-09-12', 'payer_raw': '振込 ﾃｽﾄｹﾝｾﾂ(ｶ', 'amount': 88000, 'source': 'bank_csv', 'reason': 'no_candidate', 'candidates': []},
        {'txn_date': '2026-09-15', 'payer_raw': '振込 ﾅｶﾑﾗ ｼﾞﾛｳ', 'amount': 5500, 'source': 'bank_csv', 'reason': 'no_candidate',
         'candidates': [{'invoice_id': 'INV-2026-014', 'remaining': 15400}]},
    ],
}


def a_expect(extra_summary=None, warnings=None):
    s = dict(A_SUMMARY)
    if extra_summary:
        s.update(extra_summary)
    if warnings is not None:
        s['warnings'] = warnings
    s.update(A_LINE)
    return {
        'length': 8 + 11 + 1,
        'count': {'invoice_update': 8, 'txn_row': 11, 'summary': 1},
        'rows': A_INV + A_TXN + [summary(**s)],
        'no_rows': [{'_kind': 'invoice_update', 'invoice_id': i} for i in A_UNTOUCHED],
        # output order: invoice_update items first, then txn_row, summary last (DESIGN §6.7 return)
        'paths': {'[0].json._kind': 'invoice_update', '[8].json._kind': 'txn_row', '[19].json._kind': 'summary', '[19].pairedItem': {'item': 0}},
    }


# bank_B_utf8bom.csv against the seed (fixtures/README.md §5, CASES R13)
B_INV = [
    inv_update('INV-2026-013', 'paid', 41800, '2026-09-17', '2026-09-17|41800|ダミーカコウ|', 'auto', 0),
    inv_update('INV-2026-014', 'paid', 15400, '2026-09-18', '2026-09-18|15400|スズキイチロウ|', 'auto', 0),
    inv_update('INV-2026-015', 'paid', 57200, '2026-09-19', '2026-09-19|57200|ミホンプランニング|', 'auto', 0),
    inv_update('INV-2026-016', 'paid', 12100, '2026-09-21', '2026-09-21|12100|タカハシミキ|', 'auto', 0),
]
B_TXN = [
    txn_row('2026-09-17|41800|ダミーカコウ|', 'bank_csv', '2026-09-17', '0123 カ)ダミーカコウ', 'ダミーカコウ', 41800, '', 'INV-2026-013', 'matched', ''),
    txn_row('2026-09-18|15400|スズキイチロウ|', 'bank_csv', '2026-09-18', 'ふりこみ　すずき　いちろう', 'スズキイチロウ', 15400, '', 'INV-2026-014', 'matched', ''),
    txn_row('2026-09-19|57200|ミホンプランニング|', 'bank_csv', '2026-09-19', 'ユ)ミホンプランニング', 'ミホンプランニング', 57200, '', 'INV-2026-015', 'matched', ''),
    txn_row('2026-09-21|12100|タカハシミキ|', 'bank_csv', '2026-09-21', '0045 タカハシ ミキ', 'タカハシミキ', 12100, '', 'INV-2026-016', 'matched', ''),
    txn_row('2026-09-22|7700|ワタナベケン|', 'bank_csv', '2026-09-22', 'フリコミ ワタナベ ケン', 'ワタナベケン', 7700, '', '', 'unmatched', ''),
]
B_SUMMARY = dict(date='2026-09-23', source='drive', file_name='bank_B_utf8bom.csv', n=5, a=4, b=0, c=1, rematched=0,
                 skipped_existing=0, skipped_duplicate_in_batch=0, ignored_withdraw=3, warnings=[], needs_review=[], ambiguous=[],
                 unmatched=[{'txn_date': '2026-09-22', 'payer_raw': 'フリコミ ワタナベ ケン', 'amount': 7700, 'source': 'bank_csv',
                             'reason': 'no_candidate', 'candidates': []}])

# mail_bankX.eml / mail_bankY.eml against the seed (fixtures/README.md §6, CASES R10)
M_TXN_X = '2026-09-17|104500|ダミーデンキ|【サンプル銀行】ご入金のお知らせ(gmail:18f3aabb00000001)'
M_TXN_Y = '2026-09-18|19800|ササキハナコ|depositnotification-samplebank(gmail:18f3aabb00000002)'
M_INV = [
    inv_update('INV-2026-018', 'paid', 104500, '2026-09-17', M_TXN_X, 'auto', 0),
    inv_update('INV-2026-019', 'paid', 19800, '2026-09-18', M_TXN_Y, 'auto', 0),
]
M_TXN = [
    txn_row(M_TXN_X, 'gmail', '2026-09-17', 'カ)ダミーデンキ', 'ダミーデンキ', 104500, '【サンプル銀行】ご入金のお知らせ (gmail:18f3aabb00000001)', 'INV-2026-018', 'matched', ''),
    txn_row(M_TXN_Y, 'gmail', '2026-09-18', 'ササキ ハナコ', 'ササキハナコ', 19800, 'Deposit Notification - Sample Bank (gmail:18f3aabb00000002)', 'INV-2026-019', 'matched', ''),
]
M_SUMMARY = dict(date='2026-09-23', source='gmail', n=2, a=2, b=0, c=0, rematched=0, skipped_existing=0,
                 skipped_duplicate_in_batch=0, ignored_withdraw=0, warnings=[], needs_review=[], ambiguous=[], unmatched=[])

# R23: one USD invoice with the same amount as A-5 (CASES R23)
INV_022_USD = {'invoice_id': 'INV-2026-022', 'customer_id': 'C-019', 'customer_name': 'Sample Overseas LLC',
               'payer_name_alias': 'サンプルオーバーシーズ', 'customer_email': 'overseas@example.com', 'amount': 128000, 'currency': 'USD',
               'issue_date': '2026-09-01', 'due_date': '2026-09-30', 'status': 'unpaid', 'paid_amount': 0, 'paid_date': '',
               'matched_txn_ids': '', 'match_confidence': '', 'fee_deducted': 0, 'remind_stage': 0, 'last_reminded_at': '',
               'promised_date': '', 'do_not_remind': 'FALSE', 'notes': 'R23 non-JPY (must be excluded with a warning)'}
# R18: the invoice the buyer registers after A ran (CASES R18)
INV_021 = {'invoice_id': 'INV-2026-021', 'customer_id': 'C-009', 'customer_name': '株式会社見本商会',
           'payer_name_alias': 'カ)ミホンシヨウカイ,ミホンシヨウカイ', 'customer_email': 'shokai@example.jp', 'amount': 66000, 'currency': 'JPY',
           'issue_date': '2026-09-15', 'due_date': '2026-10-15', 'status': 'unpaid', 'paid_amount': 0, 'paid_date': '',
           'matched_txn_ids': '', 'match_confidence': '', 'fee_deducted': 0, 'remind_stage': 0, 'last_reminded_at': '',
           'promised_date': '', 'do_not_remind': 'FALSE', 'notes': 'R18 registered after bank_A was processed'}

SCHEDULE_COLLECT = {'source': 'schedule', 'txns': [], 'warnings': [], 'ignored_withdraw': 0, 'file_name': ''}


def main():
    np_A = load_np('bank_A_seed')
    cfg_A = np_A['nodes']['Config']

    # ---- bank_A against the seed (R01–R06, summary counts) ----
    write('bank_A_seed', {
        '_comment': 'bank_A_sjis.csv (11 deposits) against invoices.seed + transactions.seed. Expected per fixtures/README.md §4 and CASES R01–R06.',
        'input': [normalize(np_A)], 'nodes': {'Config': cfg_A}, 'now': NOW, 'expect': a_expect()})

    # ---- bank_A with an EMPTY transactions sheet (R14-a: Read Transactions = [{}]) ----
    write('bank_A_empty_transactions', {
        '_comment': 'R14-a: same as bank_A_seed but Read Transactions = [{}] (existing = []). Identical result, skipped_existing = 0.',
        'input': [normalize(load_np('empty_transactions_sheet'))], 'nodes': {'Config': cfg_A}, 'now': NOW, 'expect': a_expect()})

    # ---- bank_A with BOTH sheets empty (R14-b) ----
    all_unmatched = [txn_row(r['match']['txn_id'], 'bank_csv', r['equals']['txn_date'], r['equals']['payer_name_raw'], r['equals']['payer_name_norm'],
                             r['equals']['amount'], '', '', 'unmatched', '') for r in A_TXN]
    write('bank_A_empty_invoices', {
        '_comment': 'R14-b: Read Invoices and Read Transactions both [{}]. All 11 txns unmatched, no candidates, no invoice_update, c = 11.',
        'input': [normalize(load_np('empty_both_sheets'))], 'nodes': {'Config': cfg_A}, 'now': NOW,
        'expect': {'length': 12, 'count': {'invoice_update': 0, 'txn_row': 11, 'summary': 1},
                   'rows': all_unmatched + [summary(n=11, a=0, b=0, c=11, rematched=0, skipped_existing=0, skipped_duplicate_in_batch=0,
                                                     ignored_withdraw=4, warnings=[], auto=[], needs_review=[], ambiguous=[])],
                   'paths': {'[11].json.unmatched.length': 11, '[11].json.unmatched[0].candidates': []}}})

    # ---- bank_A with a non-JPY invoice of the same amount as A-5 (R23) ----
    np_A_usd = json.loads(json.dumps(np_A))
    np_A_usd['nodes']['Read Invoices'] = np_A_usd['nodes']['Read Invoices'] + [item(INV_022_USD)]
    exp = a_expect(warnings=[{'type': 'non_jpy_invoice', 'invoice_id': 'INV-2026-022', 'currency': 'USD'}])
    exp['no_rows'].append({'_kind': 'invoice_update', 'invoice_id': 'INV-2026-022'})
    write('bank_A_non_jpy_invoice', {
        '_comment': 'R23: Read Invoices = seed + INV-2026-022 (USD, 128000 = A-5 amount). Same result as bank_A_seed plus one non_jpy_invoice warning; INV-022 never matched nor suggested.',
        'input': [normalize(np_A_usd)], 'nodes': {'Config': cfg_A}, 'now': NOW, 'expect': exp})

    # ---- ledger after a first run of A "yesterday" (INPUT for R09 / R18 / R19) ----
    first = match(np_A, NOW_FIRST)
    first_txn_rows = [strip_kind(i['json']) for i in first if i['json']['_kind'] == 'txn_row']
    first_inv_updates = {i['json']['invoice_id']: strip_kind(i['json']) for i in first if i['json']['_kind'] == 'invoice_update'}
    assert len(first_txn_rows) == 11 and len(first_inv_updates) == 8, 'first run of bank_A did not produce 11 txn rows / 8 invoice updates'
    ledger = np_A['input'] + [item(r) for r in first_txn_rows]                      # transactions.seed + A's 11 rows
    invoices_after_A = []
    for it in np_A['nodes']['Read Invoices']:                                          # invoices.seed with A's updates applied
        j = dict(it['json'])
        j.update(first_inv_updates.get(j['invoice_id'], {}))
        invoices_after_A.append(item(j))

    # ---- R09: the same A batch again → everything skipped, nothing written ----
    np_A_again = json.loads(json.dumps(np_A))
    np_A_again['input'] = ledger
    np_A_again['nodes']['Read Invoices'] = invoices_after_A
    write('bank_A_rerun_existing', {
        '_comment': 'R09: bank_A again with Read Transactions = seed + the 11 txn rows of the first run and Read Invoices after A. Only the summary is emitted: skipped_existing = 11, no invoice_update, no txn_row.',
        'input': [normalize(np_A_again)], 'nodes': {'Config': cfg_A}, 'now': NOW,
        'expect': {'length': 1, 'count': {'invoice_update': 0, 'txn_row': 0, 'summary': 1},
                   'rows': [summary(date='2026-09-23', source='drive', file_name='bank_A_sjis.csv', n=0, a=0, b=0, c=0, rematched=0,
                                    skipped_existing=11, skipped_duplicate_in_batch=0, ignored_withdraw=4, warnings=[],
                                    auto=[], needs_review=[], ambiguous=[], unmatched=[])],
                   'paths': {'[0].json._kind': 'summary', '[0].pairedItem': {'item': 0}}}})

    # ---- D32: Update Invoices succeeded but Upsert Transactions failed → re-run with the ledger unchanged ----
    # Read Invoices already carries A's updates (matched_txn_ids filled), Read Transactions = seed only. The 7 applied txns must NOT
    # be applied again (before D32: A-1 was applied to INV-2026-017 as partial 33000 and A-8 to INV-2026-007 as partial 200000);
    # only their ledger rows are written (matched, imported_at = now). The 4 never-applied txns are matched as new against the
    # updated invoices and yield the same rows as in the first run.
    np_A_inv_only = json.loads(json.dumps(np_A))
    np_A_inv_only['nodes']['Read Invoices'] = invoices_after_A
    write('bank_A_rerun_after_invoice_write_only', {
        '_comment': 'D32: bank_A again with Read Invoices AFTER A (matched_txn_ids recorded) but Read Transactions = seed only (the previous '
                    'Upsert Transactions failed). No invoice_update at all; 11 txn_rows: the 7 applied txns are re-emitted as matched ledger '
                    'rows (from matched_txn_ids) and counted in skipped_existing, the 4 others are matched as new (n = 4, c = 4).',
        'input': [normalize(np_A_inv_only)], 'nodes': {'Config': cfg_A}, 'now': NOW,
        'expect': {'length': 12, 'count': {'invoice_update': 0, 'txn_row': 11, 'summary': 1},
                   'rows': A_TXN + [summary(date='2026-09-23', source='drive', file_name='bank_A_sjis.csv', n=4, a=0, b=0, c=4, rematched=0,
                                            skipped_existing=7, skipped_duplicate_in_batch=0, ignored_withdraw=4, warnings=[],
                                            auto=[], needs_review=[], ambiguous=A_LINE['ambiguous'], unmatched=A_LINE['unmatched'])],
                   'no_rows': [{'_kind': 'invoice_update', 'invoice_id': 'INV-2026-017'}, {'_kind': 'invoice_update', 'invoice_id': 'INV-2026-007'}],
                   'paths': {'[0].json._kind': 'txn_row', '[11].json._kind': 'summary'}}})

    # ---- R18: schedule run after the buyer registers INV-2026-021 → A-11 becomes matched, rematched = 1 ----
    np_sched = with_source(np_A, 'Run Daily Rematch', SCHEDULE_COLLECT)
    np_sched['input'] = ledger
    np_sched['nodes']['Read Invoices'] = invoices_after_A + [item(INV_021)]
    write('schedule_rematch_after_invoice_added', {
        '_comment': 'R18: Run Daily Rematch with transactions = seed + A rows (A-11 unmatched, imported_at of the first run) and invoices after A + INV-2026-021. A-11 → matched INV-021 (imported_at preserved), rematched = 1, n = 0; A-9 / A-12 / A-14 unchanged → not written back.',
        'input': [normalize(np_sched)], 'nodes': {'Config': np_sched['nodes']['Config']}, 'now': NOW,
        'expect': {'length': 3, 'count': {'invoice_update': 1, 'txn_row': 1, 'summary': 1},
                   'rows': [inv_update('INV-2026-021', 'paid', 66000, '2026-09-11', '2026-09-11|66000|ミホンシヨウカイ|', 'auto', 0),
                            txn_row('2026-09-11|66000|ミホンシヨウカイ|', 'bank_csv', '2026-09-11', '振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ', 'ミホンシヨウカイ', 66000, '',
                                    'INV-2026-021', 'matched', '', imported_at=IMPORTED_AT_FIRST),
                            summary(date='2026-09-23', source='schedule', file_name='', n=0, a=0, b=0, c=0, rematched=1, skipped_existing=0,
                                    skipped_duplicate_in_batch=0, ignored_withdraw=0, warnings=[], needs_review=[], ambiguous=[], unmatched=[],
                                    auto=[{'txn_date': '2026-09-11', 'payer_raw': '振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ', 'amount': 66000, 'source': 'bank_csv',
                                           'invoice_ids': ['INV-2026-021'], 'reason': 'auto', 'fee': 0, 'remaining_after': 0}])],
                   'no_rows': [{'_kind': 'txn_row', 'txn_id': '2026-09-09|44000|オオバマサオ|'},
                               {'_kind': 'txn_row', 'txn_id': '2026-09-12|88000|テストケンセツ|'},
                               {'_kind': 'txn_row', 'txn_id': '2026-09-15|5500|ナカムラジロウ|'},
                               {'_kind': 'txn_row', 'txn_id': '2026-08-28|66000|ミホンシヨウカイ|'}]}})

    # ---- R19: schedule run with no change → summary only (and R23-b: a non-JPY warning does not change that) ----
    np_sched0 = with_source(np_A, 'Run Daily Rematch', SCHEDULE_COLLECT)
    np_sched0['input'] = ledger
    np_sched0['nodes']['Read Invoices'] = invoices_after_A + [item(INV_022_USD)]
    write('schedule_no_change', {
        '_comment': 'R19 / R23-b: Run Daily Rematch on the ledger after A without new invoices (plus the USD row of R23). No row changes → summary only, rematched = 0, warnings = [non_jpy_invoice].',
        'input': [normalize(np_sched0)], 'nodes': {'Config': np_sched0['nodes']['Config']}, 'now': NOW,
        'expect': {'length': 1, 'count': {'invoice_update': 0, 'txn_row': 0, 'summary': 1},
                   'rows': [summary(date='2026-09-23', source='schedule', n=0, a=0, b=0, c=0, rematched=0, skipped_existing=0,
                                    skipped_duplicate_in_batch=0, ignored_withdraw=0, auto=[], needs_review=[], ambiguous=[], unmatched=[],
                                    warnings=[{'type': 'non_jpy_invoice', 'invoice_id': 'INV-2026-022', 'currency': 'USD'}])]}})

    # ---- bank_B against the seed (R13) ----
    np_B = load_np('bank_B_seed')
    write('bank_B_seed', {
        '_comment': 'bank_B_utf8bom.csv (5 deposits) against the seed. Expected per fixtures/README.md §5 and CASES R13.',
        'input': [normalize(np_B)], 'nodes': {'Config': np_B['nodes']['Config']}, 'now': NOW,
        'expect': {'length': 4 + 5 + 1, 'count': {'invoice_update': 4, 'txn_row': 5, 'summary': 1},
                   'rows': B_INV + B_TXN + [summary(**B_SUMMARY)],
                   'paths': {'[9].json.auto.length': 4, '[9].json.auto[0].invoice_ids': ['INV-2026-013']}}})

    # ---- the two mails against the seed (R10, gmail source) ----
    np_M = load_np('mail_XY_seed')
    write('mail_XY_seed', {
        '_comment': 'mail_bankX.eml / mail_bankY.eml (via Parse Mail → Collect Transactions → Normalize Payer) against the seed. Expected per fixtures/README.md §6 and CASES R10.',
        'input': [normalize(np_M)], 'nodes': {'Config': np_M['nodes']['Config']}, 'now': NOW,
        'expect': {'length': 2 + 2 + 1, 'count': {'invoice_update': 2, 'txn_row': 2, 'summary': 1},
                   'rows': M_INV + M_TXN + [summary(**M_SUMMARY)]}})

    # ---- synthetic: rules the fixtures do not reach (3d overpaid, D13 in-batch duplicate, 4 conflict / multiple combinations,
    #      partial invoice remaining, schedule skip of matched / ignored rows) ----
    syn_invoices = [
        {'invoice_id': 'SYN-001', 'customer_name': 'アルファ株式会社', 'payer_name_alias': 'アルフア', 'amount': 10000, 'currency': 'JPY', 'due_date': '2026-09-30', 'status': 'unpaid', 'paid_amount': 0},
        {'invoice_id': 'SYN-002', 'customer_name': 'ベータ商店', 'payer_name_alias': 'ベータ', 'amount': 30000, 'currency': 'JPY', 'due_date': '2026-09-30', 'status': 'partial', 'paid_amount': 10000},
        {'invoice_id': 'SYN-003', 'customer_name': 'ガンマ企画', 'payer_name_alias': 'ガンマ', 'amount': 20000, 'currency': 'JPY', 'due_date': '2026-09-30', 'status': 'unpaid', 'paid_amount': 0},
        {'invoice_id': 'SYN-004', 'customer_name': 'デルタ', 'payer_name_alias': 'デルタ', 'amount': 1000, 'currency': 'JPY', 'due_date': '2026-09-10', 'status': 'unpaid', 'paid_amount': 0},
        {'invoice_id': 'SYN-005', 'customer_name': 'デルタ', 'payer_name_alias': 'デルタ', 'amount': 2000, 'currency': 'JPY', 'due_date': '2026-09-20', 'status': 'unpaid', 'paid_amount': 0},
        {'invoice_id': 'SYN-006', 'customer_name': 'デルタ', 'payer_name_alias': 'デルタ', 'amount': 3000, 'currency': 'JPY', 'due_date': '2026-09-30', 'status': 'unpaid', 'paid_amount': 0},
        {'invoice_id': 'SYN-007', 'customer_name': 'デルタ', 'payer_name_alias': 'デルタ', 'amount': 4000, 'currency': 'JPY', 'due_date': '2026-10-05', 'status': 'unpaid', 'paid_amount': 0},
        {'invoice_id': 'SYN-008', 'customer_name': 'イプシロン', 'payer_name_alias': 'イプシロン', 'amount': 20000, 'currency': 'JPY', 'due_date': '2026-10-05', 'status': 'unpaid', 'paid_amount': 0},
    ]
    def pre(date, raw, amount):
        return {'_kind': 'txn', 'source': 'bank_csv', 'txn_date': date, 'payer_name_raw': raw, 'amount': amount, 'memo': '', '_file': 'syn.csv', '_row': 0}
    syn_txns = [
        pre('2026-09-20', 'アルフア', 12000),          # 3d: name only, amount > remaining (10000), fee 2000 not in FEE_SET → ambiguous/overpaid
        pre('2026-09-20', 'ベータ', 20000),            # 1 against a partial invoice: remaining 30000-10000 = 20000 → auto, paid_amount 30000
        pre('2026-09-20', 'ベータ', 20000),            # D13: same txn_id twice in one batch → skipped_duplicate_in_batch
        pre('2026-09-21', 'ガンマ', 20000),            # 4: byAmt = {SYN-003 (consumed? no), SYN-008}, byName = {SYN-003} → both = 1 → auto (SYN-008 has the same amount but the name decides)
        pre('2026-09-22', 'デルタ', 5000),             # 4: 1000+4000 and 2000+3000 both sum to 5000 → multiple_combinations, no invoice written
        pre('2026-09-22', 'ゼータ', 20000),            # 4: byAmt = {SYN-008} and byName = {} → rule 2 amount_only … SYN-003 consumed above
    ]
    syn_collect = {'source': 'drive', 'txns': syn_txns, 'warnings': [], 'ignored_withdraw': 0, 'file_name': 'syn.csv'}
    np_syn = with_source(np_A, 'Watch Drive Folder', syn_collect)
    np_syn['input'] = [item({})]
    np_syn['nodes']['Read Invoices'] = [item(i) for i in syn_invoices]
    write('rules_synthetic', {
        '_comment': 'Synthetic (not in fixtures): 3d overpaid → ambiguous(overpaid, 1 candidate); rule 1 against a partial invoice uses remaining and adds to paid_amount; D13 duplicate txn_id in one batch; 3b with two subsets summing to the amount → multiple_combinations; rule 2 after the same-amount invoice was consumed.',
        'input': [normalize(np_syn)], 'nodes': {'Config': cfg_A}, 'now': NOW,
        'expect': {'length': 3 + 5 + 1, 'count': {'invoice_update': 3, 'txn_row': 5, 'summary': 1},
                   'rows': [
                       inv_update('SYN-002', 'paid', 30000, '2026-09-20', '2026-09-20|20000|ベータ|', 'auto', 0),
                       inv_update('SYN-003', 'paid', 20000, '2026-09-21', '2026-09-21|20000|ガンマ|', 'auto', 0),
                       inv_update('SYN-008', 'paid', 20000, '2026-09-22', '2026-09-22|20000|ゼータ|', 'amount_only', 0),
                       txn_row('2026-09-20|12000|アルフア|', 'bank_csv', '2026-09-20', 'アルフア', 'アルフア', 12000, '', '', 'ambiguous', 'SYN-001'),
                       txn_row('2026-09-20|20000|ベータ|', 'bank_csv', '2026-09-20', 'ベータ', 'ベータ', 20000, '', 'SYN-002', 'matched', ''),
                       txn_row('2026-09-21|20000|ガンマ|', 'bank_csv', '2026-09-21', 'ガンマ', 'ガンマ', 20000, '', 'SYN-003', 'matched', ''),
                       txn_row('2026-09-22|5000|デルタ|', 'bank_csv', '2026-09-22', 'デルタ', 'デルタ', 5000, '', '', 'ambiguous', 'SYN-007,SYN-006,SYN-005'),
                       txn_row('2026-09-22|20000|ゼータ|', 'bank_csv', '2026-09-22', 'ゼータ', 'ゼータ', 20000, '', 'SYN-008', 'matched', ''),
                       summary(n=5, a=2, b=1, c=2, rematched=0, skipped_existing=0, skipped_duplicate_in_batch=1, ignored_withdraw=0, warnings=[]),
                   ],
                   'no_rows': [{'_kind': 'invoice_update', 'invoice_id': 'SYN-001'}, {'_kind': 'invoice_update', 'invoice_id': 'SYN-004'},
                               {'_kind': 'invoice_update', 'invoice_id': 'SYN-005'}, {'_kind': 'invoice_update', 'invoice_id': 'SYN-006'},
                               {'_kind': 'invoice_update', 'invoice_id': 'SYN-007'}],
                   'paths': {'[8].json.ambiguous[0].reason': 'overpaid', '[8].json.ambiguous[0].candidates': [{'invoice_id': 'SYN-001', 'remaining': 10000}],
                             '[8].json.ambiguous[1].reason': 'multiple_combinations', '[8].json.ambiguous[1].candidates.length': 3,
                             '[8].json.needs_review[0].reason': 'amount_only', '[8].json.needs_review[0].invoice_ids': ['SYN-008']}}})

    # ---- synthetic schedule: matched / ignored rows are never re-matched; unchanged ambiguous rows are not written back;
    #      an unmatched row whose candidates changed is written back (status unchanged, so rematched does not count it) ----
    def ledger_row(txn_id, date, name, amount, status, suggested, matched=''):
        return item({'txn_id': txn_id, 'source': 'bank_csv', 'txn_date': date, 'payer_name_raw': name, 'payer_name_norm': name, 'amount': amount,
                     'memo': '', 'matched_invoice_ids': matched, 'status': status, 'suggested_invoice_ids': suggested, 'imported_at': IMPORTED_AT_FIRST})
    syn_ledger = [
        ledger_row('2026-09-01|10000|アルフア|', '2026-09-01', 'アルフア', 10000, 'ignored', ''),            # would match SYN-001 → must be skipped
        ledger_row('2026-09-02|20000|ベータ|', '2026-09-02', 'ベータ', 20000, 'matched', '', 'OLD-1'),      # would match SYN-002 → must be skipped
        ledger_row('2026-09-03|20000|ガンマ|', '2026-09-03', 'ガンマ', 20000, 'unmatched', ''),             # now matches SYN-003 → rematched
        ledger_row('2026-09-04|20000|ゼータ|', '2026-09-04', 'ゼータ', 20000, 'ambiguous', 'SYN-002,SYN-008'),  # same_amount_multiple, same candidates → not written
        ledger_row('2026-09-05|20500|シータ|', '2026-09-05', 'シータ', 20500, 'unmatched', ''),             # still unmatched, candidates within 10% appear → written
    ]
    np_syn_sched = with_source(np_A, 'Run Daily Rematch', SCHEDULE_COLLECT)
    np_syn_sched['input'] = syn_ledger
    np_syn_sched['nodes']['Read Invoices'] = [item(i) for i in syn_invoices]
    write('schedule_synthetic_skip_and_change', {
        '_comment': 'Synthetic schedule run: ignored / matched rows are left alone (even though SYN-001 / SYN-002 would match); ガンマ (unmatched) now matches SYN-003 → rematched = 1; ゼータ (ambiguous, same candidates SYN-002,SYN-008) → not written; シータ (unmatched, no candidates before) now gets SYN-002,SYN-008 within 10% → written back, status unchanged.',
        'input': [normalize(np_syn_sched)], 'nodes': {'Config': np_syn_sched['nodes']['Config']}, 'now': NOW,
        'expect': {'length': 4, 'count': {'invoice_update': 1, 'txn_row': 2, 'summary': 1},
                   'rows': [inv_update('SYN-003', 'paid', 20000, '2026-09-03', '2026-09-03|20000|ガンマ|', 'auto', 0),
                            txn_row('2026-09-03|20000|ガンマ|', 'bank_csv', '2026-09-03', 'ガンマ', 'ガンマ', 20000, '', 'SYN-003', 'matched', '', imported_at=IMPORTED_AT_FIRST),
                            txn_row('2026-09-05|20500|シータ|', 'bank_csv', '2026-09-05', 'シータ', 'シータ', 20500, '', '', 'unmatched', 'SYN-002,SYN-008', imported_at=IMPORTED_AT_FIRST),
                            summary(n=0, a=0, b=0, c=0, rematched=1, skipped_existing=0, skipped_duplicate_in_batch=0, ignored_withdraw=0, warnings=[],
                                    needs_review=[], ambiguous=[],
                                    auto=[{'txn_date': '2026-09-03', 'payer_raw': 'ガンマ', 'amount': 20000, 'source': 'bank_csv', 'invoice_ids': ['SYN-003'], 'reason': 'auto', 'fee': 0, 'remaining_after': 0}],
                                    unmatched=[{'txn_date': '2026-09-05', 'payer_raw': 'シータ', 'amount': 20500, 'source': 'bank_csv', 'reason': 'no_candidate',
                                                'candidates': [{'invoice_id': 'SYN-002', 'remaining': 20000}, {'invoice_id': 'SYN-008', 'remaining': 20000}]}])],
                   'no_rows': [{'_kind': 'invoice_update', 'invoice_id': 'SYN-001'}, {'_kind': 'invoice_update', 'invoice_id': 'SYN-002'},
                               {'_kind': 'txn_row', 'txn_id': '2026-09-01|10000|アルフア|'}, {'_kind': 'txn_row', 'txn_id': '2026-09-02|20000|ベータ|'},
                               {'_kind': 'txn_row', 'txn_id': '2026-09-04|20000|ゼータ|'}]}})


if __name__ == '__main__':
    main()
