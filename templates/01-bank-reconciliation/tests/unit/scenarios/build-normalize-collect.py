#!/usr/bin/env python3
# Builds the unit-test scenarios for the Code nodes "Collect Transactions" (code/collect_transactions.js, DESIGN.md §6.4)
# and "Normalize Payer" (code/normalize_payer.js, DESIGN.md §6.6) from the REAL fixtures in ../../../fixtures/.
#
#   python3 tests/unit/scenarios/build-normalize-collect.py        # rewrites scenarios/collect_transactions/*.json
#                                                                  # and scenarios/normalize_payer/*.json
#
# Scenario file = { "input": [items], "nodes": { "<Node name>": [items] }, "now": "...", "expect": {...} }.
# "input" / "nodes" are what tests/unit/run-code-node.mjs feeds to the node; "expect" is read only by
# tests/unit/test-<module>.sh:  expect.length (item count), expect.paths {"<path>": <deep-equal value>},
# expect.absent ["<path>", ...] (must be undefined).
#
# The upstream items (Parse Bank CSV / Parse Mail output) are produced here by a small Python port of the §6.2 / §6.3
# pseudocode applied to the fixture bytes (Shift_JIS via cp932, UTF-8 BOM stripped), so the scenarios are exactly the
# item shapes those nodes emit.  The EXPECTED values (payer_name_norm, txn_id, invoice _names) are NOT computed by
# code: they are transcribed from fixtures/README.md §4–§6 (the P1 oracle) and cross-checked against the decoded
# fixture text so a transcription error fails this script instead of silently passing.
# Rows marked "synthetic" do not exist in the fixtures; they exercise rules the fixtures do not reach (D19 anchoring,
# NFKC / hiragana tokens written by a buyer, STRIP_LEADING_DIGITS=false, memo_norm, bad_date warnings).
import csv
import io
import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
FX = os.path.join(TPL, 'fixtures')
NOW = '2026-09-23T09:00:00+09:00'


# ---------------------------------------------------------------------------------------------------------------
# Config (DESIGN.md §4 defaults; MAIL_PARSERS from fixtures/mail_parsers.example.json; placeholders only)
# ---------------------------------------------------------------------------------------------------------------
def load_json(name):
    with open(os.path.join(FX, name), encoding='utf-8') as f:
        return json.load(f)


CSV_MAPPINGS = load_json('csv_mapping.examples.json')
MAIL_PARSERS = load_json('mail_parsers.example.json')['MAIL_PARSERS']

LEGAL_ENTITY_TOKENS = [
    "カ)", "(カ", "ユ)", "(ユ", "ド)", "(ド", "シヤ)", "(シヤ", "ザイ)", "(ザイ", "ガク)", "(ガク", "イ)", "(イ", "ホ)", "(ホ",
    "株式会社", "有限会社", "合同会社", "合名会社", "合資会社", "一般社団法人", "一般財団法人", "医療法人", "学校法人", "社会福祉法人",
    "カブシキガイシヤ", "カブシキカイシヤ", "ユウゲンガイシヤ", "ゴウドウガイシヤ", "イツパンシヤダンホウジン", "イリヨウホウジン",
    "振込", "フリコミ", "ゴフリコミ",
]


def config(source, csv_mapping='bank_A_sjis.csv', **overrides):
    cfg = {
        'SOURCE': source,
        'TZ': 'Asia/Tokyo',
        'LANG': 'ja',
        'SHEET_ID': 'REPLACE_ME_SHEET_ID',
        'SHEET_INVOICES': 'invoices',
        'SHEET_TRANSACTIONS': 'transactions',
        'DRIVE_FOLDER_ID': 'REPLACE_ME_DRIVE_FOLDER_ID',
        'GMAIL_QUERY': 'subject:(入金 OR Deposit) newer_than:1d',
        'RUN_AT': '09:00',
        'TRIGGERS_ENABLED': {'drive': True, 'gmail': True, 'schedule': True},
        'CSV_MAPPING': dict(CSV_MAPPINGS[csv_mapping]),
        'MAIL_PARSERS': MAIL_PARSERS,
        'LEGAL_ENTITY_TOKENS': list(LEGAL_ENTITY_TOKENS),
        'STRIP_LEADING_DIGITS': True,
        'FEE_SET': [110, 165, 220, 275, 330, 440, 550, 660, 770, 880],
        'NAME_MIN_CONTAINS': 3,
        'NOTIFY_CHANNELS': ['slack'],
        'SLACK_CHANNEL': 'REPLACE_ME_SLACK_CHANNEL_ID',
        'NOTIFY_EMAIL_TO': 'replace-me@example.com',
        'LINE_TO_USER_ID': 'REPLACE_ME_LINE_USER_ID',
        'CHATWORK_ROOM_ID': 'REPLACE_ME_CHATWORK_ROOM_ID',
        'NOTIFY_MAX_LINES': 40,
    }
    cfg.update(overrides)
    return cfg


# Config passes the trigger's own fields through (Include in Output: All Input Fields), so the Config item carries them.
DRIVE_FIELDS = {'A': {'id': 'fixture-bank-A', 'name': 'bank_A_sjis.csv', 'mimeType': 'text/csv'},
                'B': {'id': 'fixture-bank-B', 'name': 'bank_B_utf8bom.csv', 'mimeType': 'text/csv'}}
SCHEDULE_FIELDS = {'timestamp': '2026-09-24T09:00:00.000+09:00', 'Readable date': 'September 24th 2026, 9:00:00 am',
                   'Day of week': 'Thursday', 'Year': '2026', 'Month': 'September', 'Day of month': '24',
                   'Hour': '09', 'Minute': '00', 'Second': '00', 'Timezone': 'Asia/Tokyo (UTC+09:00)'}


def item(j, paired=0):
    return {'json': j, 'pairedItem': {'item': paired}}


# ---------------------------------------------------------------------------------------------------------------
# Python port of DESIGN.md §6.1 / §6.5 / §6.2 / §6.3 (only what is needed to build the upstream items)
# ---------------------------------------------------------------------------------------------------------------
def to_int(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    s = re.sub(r'[,\s¥￥円]', '', unicodedata.normalize('NFKC', str(v)))
    if not re.fullmatch(r'-?\d+(\.\d+)?', s):
        return None
    return int(s.split('.')[0])


def sstr(v):
    return '' if v is None else str(v).strip()


def normalize_date(value, fmt):
    s = unicodedata.normalize('NFKC', sstr(value))
    if not s:
        return None
    if fmt and fmt != 'auto':
        if fmt == 'yyyyMMdd':
            m = re.fullmatch(r'(\d{4})(\d{2})(\d{2})', s)
        elif fmt == 'yyyy/MM/dd':
            m = re.fullmatch(r'(\d{4})/(\d{2})/(\d{2})', s)
        elif fmt == 'yyyy-MM-dd':
            m = re.fullmatch(r'(\d{4})-(\d{2})-(\d{2})', s)
        else:
            raise ValueError(fmt)
    else:
        m = re.fullmatch(r'(\d{4})(\d{2})(\d{2})', s) or re.match(r'^(\d{4})[/\-.年](\d{1,2})[/\-.月](\d{1,2})日?', s)
    if not m:
        return None
    return '%04d-%02d-%02d' % (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def decode_csv(path):
    b = open(path, 'rb').read()
    if b[:3] == b'\xef\xbb\xbf':
        return b[3:].decode('utf-8')
    return b.decode('cp932')            # WHATWG 'shift_jis' == windows-31j == cp932


def parse_bank_csv_items(path, mapping, file_name):
    """Parse Bank CSV output items (§6.2): pre-txns, warnings, one file_stats item."""
    rows = [r for r in csv.reader(io.StringIO(decode_csv(path), newline='')) if any(f.strip() for f in r)]
    skip = int(mapping['skip_rows'])
    body = rows[skip:]
    header = [unicodedata.normalize('NFKC', h) for h in body[0]]
    nk = lambda s: unicodedata.normalize('NFKC', sstr(s))
    for col in ('date_col', 'payer_col', 'deposit_col'):
        assert nk(mapping[col]) in header, (mapping[col], header)
    date_i, payer_i, dep_i = (header.index(nk(mapping[c])) for c in ('date_col', 'payer_col', 'deposit_col'))
    memo_i = header.index(nk(mapping['memo_col'])) if mapping.get('memo_col') else None
    txns, warnings, ignored = [], [], 0
    for idx, r in enumerate(body[1:]):
        row_no = skip + 2 + idx
        cell = lambda i: r[i] if i is not None and i < len(r) else ''
        dep = to_int(cell(dep_i))
        if not (dep is not None and dep > 0):
            ignored += 1
            continue
        d = normalize_date(cell(date_i), mapping['date_format'])
        if not d:
            warnings.append({'_kind': 'warning', 'type': 'bad_date', 'row': row_no, 'value': sstr(cell(date_i))})
            continue
        txns.append({'_kind': 'txn', 'source': 'bank_csv', 'txn_date': d, 'payer_name_raw': sstr(cell(payer_i)),
                     'amount': dep, 'memo': sstr(cell(memo_i)) if memo_i is not None else '', '_file': file_name, '_row': row_no})
    stats = {'_kind': 'file_stats', 'file_name': file_name, 'ignored_withdraw': ignored,
             'rows_total': len(txns) + len(warnings) + ignored}
    return [item(t) for t in txns] + [item(w) for w in warnings] + [item(stats)]


def parse_mail_items():
    """Parse Mail output items (§6.3) for the two pinned fixture mails."""
    out = []
    for i, it in enumerate(load_json('mail_pinned.example.json')['items']):
        email = it['json']
        frm, subject = email['from']['text'], email['subject']
        body = unicodedata.normalize('NFKC', email['text'])
        mid = email['id']
        ci = lambda hay, needle: (not needle) or unicodedata.normalize('NFKC', needle).lower() in unicodedata.normalize('NFKC', hay).lower()
        for p in MAIL_PARSERS:
            if not (ci(frm, p['from_match']) and ci(subject, p['subject_match'])):
                continue
            am, pm, dm = (re.search(p['amount_regex'], body), re.search(p['payer_regex'], body),
                          re.search(p['date_regex'], body) if p.get('date_regex') else None)
            amount = to_int(am.group(1)) if am else None
            assert amount and pm, (p['name'], amount, pm)
            d = normalize_date(dm.group(1), 'auto') if dm else None
            assert d, 'fixture mails carry a body date'
            out.append(item({'_kind': 'txn', 'source': 'gmail', 'txn_date': d, 'payer_name_raw': sstr(pm.group(1)),
                             'amount': amount, 'memo': '%s (gmail:%s)' % (subject, mid), '_message_id': mid, '_parser': p['name']}, i))
            break
        else:
            raise AssertionError('no parser matched fixture mail ' + mid)
    return out


# ---------------------------------------------------------------------------------------------------------------
# Google Sheets "Get Row(s)" shaped items from the seed CSVs (one item per row, header keys, numbers for the int
# columns, everything else a string, empty cell = "")
# ---------------------------------------------------------------------------------------------------------------
INT_COLS = {'amount', 'paid_amount', 'fee_deducted', 'remind_stage'}


def sheet_rows(name):
    with open(os.path.join(FX, name), encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        j = {}
        for k, v in r.items():
            j[k] = (int(v) if v != '' else '') if k in INT_COLS else v
        out.append({'json': j})
    return out


INVOICES = sheet_rows('invoices.seed.csv')
TRANSACTIONS = sheet_rows('transactions.seed.csv')
EMPTY_SHEET = [{'json': {}}]            # Always Output Data on an empty sheet


# ---------------------------------------------------------------------------------------------------------------
# Oracle: transcribed from fixtures/README.md (NOT computed). (_row, raw, payer_name_norm, txn_id)
# ---------------------------------------------------------------------------------------------------------------
ORACLE_A = [
    (2, '振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ', 'サンプルシヨウジ', '2026-09-01|33000|サンプルシヨウジ|'),
    (4, '振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ', 'テストコウギヨウ', '2026-09-02|54780|テストコウギヨウ|'),
    (5, 'フリコミ　ヤマダ　タロウ', 'ヤマダタロウ', '2026-09-03|9800|ヤマダタロウ|'),
    (6, '振込 ｻﾄｳ ｹｲｺ', 'サトウケイコ', '2026-09-04|128000|サトウケイコ|'),
    (7, '振込 ｶ)ﾃｽﾄﾌﾞﾂｻﾝ', 'テストブツサン', '2026-09-05|1234567|テストブツサン|'),
    (9, '振込 ｻﾝﾌﾟﾙｼｽﾃﾑ(ｶ', 'サンプルシステム', '2026-09-08|100000|サンプルシステム|'),
    (10, '振込 ｵｵﾊﾞ ﾏｻｵ', 'オオバマサオ', '2026-09-09|44000|オオバマサオ|'),
    (12, '振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ', 'ミホンシヨウカイ', '2026-09-11|66000|ミホンシヨウカイ|'),
    (13, '振込 ﾃｽﾄｹﾝｾﾂ(ｶ', 'テストケンセツ', '2026-09-12|88000|テストケンセツ|'),
    (14, '振込 ｶ)ｻﾝﾌﾟﾙﾌｰｽﾞﾄｳｷﾖｳ', 'サンプルフーズトウキヨウ', '2026-09-14|27500|サンプルフーズトウキヨウ|'),
    (15, '振込 ﾅｶﾑﾗ ｼﾞﾛｳ', 'ナカムラジロウ', '2026-09-15|5500|ナカムラジロウ|'),
]
ORACLE_B = [
    (2, '0123 カ)ダミーカコウ', 'ダミーカコウ', '2026-09-17|41800|ダミーカコウ|'),
    (4, 'ふりこみ　すずき　いちろう', 'スズキイチロウ', '2026-09-18|15400|スズキイチロウ|'),
    (5, 'ユ)ミホンプランニング', 'ミホンプランニング', '2026-09-19|57200|ミホンプランニング|'),
    (7, '0045 タカハシ ミキ', 'タカハシミキ', '2026-09-21|12100|タカハシミキ|'),
    (8, 'フリコミ ワタナベ ケン', 'ワタナベケン', '2026-09-22|7700|ワタナベケン|'),
]
# README §6: mail payer_name_raw is captured from the NFKC-normalized body (T04), memo = "<subject> (gmail:<id>)"
ORACLE_M = [
    ('カ)ダミーデンキ', 104500, '2026-09-17', '【サンプル銀行】ご入金のお知らせ (gmail:18f3aabb00000001)', 'ダミーデンキ',
     '2026-09-17|104500|ダミーデンキ|【サンプル銀行】ご入金のお知らせ(gmail:18f3aabb00000001)'),
    ('ササキ ハナコ', 19800, '2026-09-18', 'Deposit Notification - Sample Bank (gmail:18f3aabb00000002)', 'ササキハナコ',
     '2026-09-18|19800|ササキハナコ|depositnotification-samplebank(gmail:18f3aabb00000002)'),
]
# invoice _names = uniq(normalizePayer(customer_name), normalizePayer(each alias)) — derived by hand from the seed
ORACLE_NAMES = {
    'INV-2026-001': ['サンプル商事', 'サンプルシヨウジ'],
    'INV-2026-002': ['テスト工業', 'テストコウギヨウ', 'テストコウギョウ'],
    'INV-2026-003': ['山田太郎', 'ヤマダタロウ'],
    'INV-2026-004': ['ミホンデザイン'],
    'INV-2026-005': ['テスト物産', 'テストブツサン'],
    'INV-2026-006': ['テスト物産', 'テストブツサン'],
    'INV-2026-007': ['サンプルシステム'],
    'INV-2026-008': ['見本印刷'],
    'INV-2026-009': ['モデル企画'],
    'INV-2026-010': ['見本商会', 'ミホンシヨウカイ'],
    'INV-2026-011': ['テスト建設', 'テストケンセツ'],
    'INV-2026-012': ['サンプルフーズ'],
    'INV-2026-013': ['ダミー加工', 'ダミーカコウ'],
    'INV-2026-014': ['鈴木一郎', 'スズキイチロウ'],
    'INV-2026-015': ['見本プランニング', 'ミホンプランニング'],
    'INV-2026-016': ['高橋美紀', 'タカハシミキ'],
    'INV-2026-017': ['サンプル商事', 'サンプルシヨウジ'],
    'INV-2026-018': ['ダミー電機', 'ダミーデンキ'],
    'INV-2026-019': ['佐々木花子', 'ササキハナコ'],
    'INV-2026-020': ['サンプル運輸', 'サンプルウンユ'],
}

# ---------------------------------------------------------------------------------------------------------------
# Upstream items from the real fixtures + cross-checks against the oracle transcription
# ---------------------------------------------------------------------------------------------------------------
PBC_A = parse_bank_csv_items(os.path.join(FX, 'bank_A_sjis.csv'), CSV_MAPPINGS['bank_A_sjis.csv'], 'bank_A_sjis.csv')
PBC_B = parse_bank_csv_items(os.path.join(FX, 'bank_B_utf8bom.csv'), CSV_MAPPINGS['bank_B_utf8bom.csv'], 'bank_B_utf8bom.csv')
PM_XY = parse_mail_items()

for items_, oracle, n_ignored in ((PBC_A, ORACLE_A, 4), (PBC_B, ORACLE_B, 3)):
    txns = [i['json'] for i in items_ if i['json']['_kind'] == 'txn']
    stats = [i['json'] for i in items_ if i['json']['_kind'] == 'file_stats'][0]
    assert len(txns) == len(oracle), (len(txns), len(oracle))
    assert stats['ignored_withdraw'] == n_ignored, stats
    for t, (row, raw, _norm, txn_id) in zip(txns, oracle):
        assert t['_row'] == row and t['payer_name_raw'] == raw, (t, row, raw)
        assert '�' not in t['payer_name_raw']
        d, a, _ = txn_id.split('|', 2)
        assert t['txn_date'] == d and t['amount'] == int(a), (t, txn_id)
for t, (raw, amount, d, memo, _norm, _id) in zip([i['json'] for i in PM_XY], ORACLE_M):
    assert (t['payer_name_raw'], t['amount'], t['txn_date'], t['memo']) == (raw, amount, d, memo), (t, raw, amount, d, memo)


def collected(source, pbc_items):
    txns = [i['json'] for i in pbc_items if i['json'].get('_kind') == 'txn']
    warnings = [i['json'] for i in pbc_items if i['json'].get('_kind') == 'warning']
    stats = next((i['json'] for i in pbc_items if i['json'].get('_kind') == 'file_stats'), {})
    return [item({'source': source, 'txns': txns, 'warnings': warnings,
                  'ignored_withdraw': int(stats.get('ignored_withdraw', 0) or 0), 'file_name': stats.get('file_name', '')})]


COLLECTED_A = collected('drive', PBC_A)
COLLECTED_B = collected('drive', PBC_B)
COLLECTED_M = collected('gmail', PM_XY)
COLLECTED_S = [item({'source': 'schedule', 'txns': [], 'warnings': [], 'ignored_withdraw': 0, 'file_name': ''})]


# ---------------------------------------------------------------------------------------------------------------
# Scenario writers
# ---------------------------------------------------------------------------------------------------------------
def write(module, name, data):
    d = os.path.join(HERE, module)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name + '.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('wrote', module + '/' + name + '.json')


def txn_paths(prefix, oracle_rows, source, file_name):
    paths, absent = {}, []
    for i, (row, raw, norm, txn_id) in enumerate(oracle_rows):
        p = '%s[%d]' % (prefix, i)
        d, a, _ = txn_id.split('|', 2)
        paths.update({p + '.txn_id': txn_id, p + '.payer_name_norm': norm, p + '.payer_name_raw': raw,
                      p + '.txn_date': d, p + '.amount': int(a), p + '.source': source, p + '.memo': '',
                      p + '._file': file_name, p + '._row': row})
        absent.append(p + '._kind')
    return paths, absent


def names_paths(prefix):
    paths = {prefix + '.length': len(INVOICES)}
    for i, inv in enumerate(INVOICES):
        iid = inv['json']['invoice_id']
        paths['%s[%d].invoice_id' % (prefix, i)] = iid
        paths['%s[%d]._names' % (prefix, i)] = ORACLE_NAMES[iid]
    # pass-through of the sheet row (Match Invoices does the numeric coercion)
    paths[prefix + '[0].amount'] = 33000
    paths[prefix + '[0].status'] = 'unpaid'
    paths[prefix + '[9].status'] = 'paid'
    return paths


def base_expect(source, file_name, ignored, n_txn, n_inv, n_existing):
    return {'length': 1, 'paths': {
        '[0].json.source': source, '[0].json.file_name': file_name, '[0].json.ignored_withdraw': ignored,
        '[0].json.warnings': [], '[0].json.txns.length': n_txn, '[0].json.invoices.length': n_inv,
        '[0].json.existing.length': n_existing, '[0].pairedItem': {'item': 0}}, 'absent': []}


# ===== normalize_payer =====
def np_scenarios():
    seed_existing = {'[0].json.existing[0].txn_id': '2026-08-28|66000|ミホンシヨウカイ|',
                     '[0].json.existing[0].payer_name_norm': 'ミホンシヨウカイ',
                     '[0].json.existing[0].payer_name_raw': '振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ',
                     '[0].json.existing[0].status': 'matched', '[0].json.existing[0].amount': 66000,
                     '[0].json.existing[0].matched_invoice_ids': 'INV-2026-010'}

    # 1. bank_A: all 11 remitters of bank_A_sjis.csv + 20 seed invoices + 1 seed transaction
    e = base_expect('drive', 'bank_A_sjis.csv', 4, 11, 20, 1)
    p, a = txn_paths('[0].json.txns', ORACLE_A, 'bank_csv', 'bank_A_sjis.csv')
    e['paths'].update(p); e['absent'] += a
    e['paths'].update(names_paths('[0].json.invoices'))
    e['paths'].update(seed_existing)
    write('normalize_payer', 'bank_A_seed', {
        '_comment': 'bank_A_sjis.csv (11 deposits, Config defaults) after Parse Bank CSV → Collect Transactions; invoices = invoices.seed.csv; '
                    'input ($input) = transactions.seed.csv. Expected payer_name_norm / txn_id / _names per fixtures/README.md §2, §4.',
        'input': TRANSACTIONS, 'nodes': {'Config': [item(dict(DRIVE_FIELDS['A'], **config('Watch Drive Folder')))],
                                         'Read Invoices': INVOICES, 'Collect Transactions': COLLECTED_A}, 'now': NOW, 'expect': e})

    # 2. bank_B: BOM, yyyyMMdd, leading digits, hiragana, ユ)
    e = base_expect('drive', 'bank_B_utf8bom.csv', 3, 5, 20, 1)
    p, a = txn_paths('[0].json.txns', ORACLE_B, 'bank_csv', 'bank_B_utf8bom.csv')
    e['paths'].update(p); e['absent'] += a
    e['paths'].update(names_paths('[0].json.invoices'))
    e['paths'].update(seed_existing)
    write('normalize_payer', 'bank_B_seed', {
        '_comment': 'bank_B_utf8bom.csv (5 deposits, CSV_MAPPING = bank_B entry of csv_mapping.examples.json). Expected per fixtures/README.md §5.',
        'input': TRANSACTIONS, 'nodes': {'Config': [item(dict(DRIVE_FIELDS['B'], **config('Watch Drive Folder', 'bank_B_utf8bom.csv')))],
                                         'Read Invoices': INVOICES, 'Collect Transactions': COLLECTED_B}, 'now': NOW, 'expect': e})

    # 3. the two fixture mails (Gmail path): memo_norm keeps 【】() and lowercases, payer_name_raw is NFKC (T04)
    e = base_expect('gmail', '', 0, 2, 20, 1)
    for i, (raw, amount, d, memo, norm, txn_id) in enumerate(ORACLE_M):
        p = '[0].json.txns[%d]' % i
        e['paths'].update({p + '.txn_id': txn_id, p + '.payer_name_norm': norm, p + '.payer_name_raw': raw, p + '.amount': amount,
                           p + '.txn_date': d, p + '.memo': memo, p + '.source': 'gmail',
                           p + '._message_id': PM_XY[i]['json']['_message_id'], p + '._parser': PM_XY[i]['json']['_parser']})
        e['absent'].append(p + '._kind')
    e['paths'].update(seed_existing)
    write('normalize_payer', 'mail_XY_seed', {
        '_comment': 'mail_bankX.eml / mail_bankY.eml (via mail_pinned.example.json + mail_parsers.example.json) after Parse Mail → Collect Transactions. Expected per fixtures/README.md §6.',
        'input': TRANSACTIONS, 'nodes': {'Config': [item(config('Watch Gmail Inbox'))], 'Read Invoices': INVOICES,
                                         'Collect Transactions': COLLECTED_M}, 'now': NOW, 'expect': e})

    # 4. R14-a: transactions sheet empty (Always Output Data → one {} item) — must not become an "existing" row
    e = base_expect('drive', 'bank_A_sjis.csv', 4, 11, 20, 0)
    e['paths']['[0].json.existing'] = []
    e['paths']['[0].json.txns[0].txn_id'] = ORACLE_A[0][3]
    write('normalize_payer', 'empty_transactions_sheet', {
        '_comment': 'R14-a: Read Transactions = [{json:{}}] (empty sheet with Always Output Data). The {} row is skipped; invoices = seed; txns = bank_A.',
        'input': EMPTY_SHEET, 'nodes': {'Config': [item(dict(DRIVE_FIELDS['A'], **config('Watch Drive Folder')))],
                                        'Read Invoices': INVOICES, 'Collect Transactions': COLLECTED_A}, 'now': NOW, 'expect': e})

    # 5. R14-b: both sheets empty
    e = base_expect('drive', 'bank_A_sjis.csv', 4, 11, 0, 0)
    e['paths']['[0].json.existing'] = []
    e['paths']['[0].json.invoices'] = []
    p, a = txn_paths('[0].json.txns', ORACLE_A, 'bank_csv', 'bank_A_sjis.csv')
    e['paths'].update(p); e['absent'] += a
    write('normalize_payer', 'empty_both_sheets', {
        '_comment': 'R14-b: Read Invoices and Read Transactions both = [{json:{}}]. Neither {} row is treated as data; all 11 txns still get txn_id.',
        'input': EMPTY_SHEET, 'nodes': {'Config': [item(dict(DRIVE_FIELDS['A'], **config('Watch Drive Folder')))],
                                        'Read Invoices': EMPTY_SHEET, 'Collect Transactions': COLLECTED_A}, 'now': NOW, 'expect': e})

    # 6. Schedule path: no new txns; an existing row without payer_name_norm is back-filled from payer_name_raw
    derived = dict(TRANSACTIONS[0]['json'])
    derived.update({'txn_id': '2026-09-15|5500|ナカムラジロウ|', 'txn_date': '2026-09-15', 'payer_name_raw': '振込 ﾅｶﾑﾗ ｼﾞﾛｳ',
                    'payer_name_norm': '', 'amount': 5500, 'matched_invoice_ids': '', 'status': 'unmatched',
                    'suggested_invoice_ids': 'INV-2026-014', 'imported_at': '2026-09-16T09:05:12+09:00'})
    e = base_expect('schedule', '', 0, 0, 20, 2)
    e['paths'].update(seed_existing)
    e['paths'].update({'[0].json.txns': [], '[0].json.existing[1].txn_id': derived['txn_id'],
                       '[0].json.existing[1].payer_name_norm': 'ナカムラジロウ', '[0].json.existing[1].status': 'unmatched'})
    e['paths'].update(names_paths('[0].json.invoices'))
    write('normalize_payer', 'schedule_existing_backfill', {
        '_comment': 'Run Daily Rematch: Collect Transactions = { source: schedule, txns: [] }. input = transactions.seed.csv + one derived '
                    'unmatched row (bank_A row 14 as it would sit in the ledger, payer_name_norm blanked by hand) → payer_name_norm is back-filled '
                    'from payer_name_raw. Row 2 is synthetic (derived from the fixture), not in transactions.seed.csv.',
        'input': [TRANSACTIONS[0], {'json': derived}], 'nodes': {'Config': [item(dict(SCHEDULE_FIELDS, **config('Run Daily Rematch')))],
                                                                'Read Invoices': INVOICES, 'Collect Transactions': COLLECTED_S}, 'now': NOW, 'expect': e})

    # 7. synthetic: D19 anchoring negatives, punctuation, memo_norm, txn_id with memo
    syn = [
        ('タナカ)ヒロシ', '', 'タナカヒロシ'),                     # カ) not at the start → kept (only the ')' falls to 4b)
        ('サンプル(カサービス', '', 'サンプルカサービス'),          # (カ not at the end → kept
        ('ｶ)ｻﾝﾌﾟﾙ･ｼﾖｳｼﾞ', '', 'サンプルシヨウジ'),                 # half-width ･ → NFKC ・ → removed by 4b
        ('12 ｶ)ﾃｽﾄ(ｶ', '', 'テスト'),                             # digits + カ) at start AND (カ at end
        ('振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ', '振込 A|B 参考', 'サンプルシヨウジ'),   # memo: NFKC, spaces out, | → /, lowercase
        ('ｶﾌﾞｼｷｶﾞｲｼﾔ ﾐﾎﾝ', '', 'ミホン'),                         # formal reading カブシキガイシヤ removed anywhere
        ('ﾃｽﾄ-ｼｽﾃﾑ ｶ)', '', 'テストシステムカ'),                    # カ) at the END is not the 前株 form → only ')' and '-' dropped
    ]
    pre = [{'_kind': 'txn', 'source': 'bank_csv', 'txn_date': '2026-09-2%d' % i, 'payer_name_raw': raw, 'amount': 1000 + i,
            'memo': memo, '_file': 'synthetic.csv', '_row': i + 2} for i, (raw, memo, _n) in enumerate(syn)]
    coll = [item({'source': 'drive', 'txns': pre, 'warnings': [], 'ignored_withdraw': 0, 'file_name': 'synthetic.csv'})]
    e = base_expect('drive', 'synthetic.csv', 0, len(syn), 0, 0)
    for i, (raw, memo, norm) in enumerate(syn):
        p = '[0].json.txns[%d]' % i
        memo_norm = re.sub(r'[\s　]+', '', unicodedata.normalize('NFKC', memo)).replace('|', '/').lower()
        e['paths'].update({p + '.payer_name_norm': norm, p + '.txn_id': '2026-09-2%d|%d|%s|%s' % (i, 1000 + i, norm, memo_norm),
                           p + '.memo': memo})
        e['absent'].append(p + '._kind')
    write('normalize_payer', 'token_anchoring_synthetic', {
        '_comment': 'SYNTHETIC remitters (not in fixtures): D19 anchoring — X) only at the start (leading digits allowed), (X only at the end; '
                    'punctuation removal; memo_norm (NFKC → no spaces → | to / → lowercase) inside txn_id. Config defaults.',
        'input': EMPTY_SHEET, 'nodes': {'Config': [item(dict(DRIVE_FIELDS['A'], **config('Watch Drive Folder')))],
                                        'Read Invoices': EMPTY_SHEET, 'Collect Transactions': coll}, 'now': NOW, 'expect': e})

    # 8. synthetic Config: buyer-written tokens (full-width, hiragana, spaced), STRIP_LEADING_DIGITS=false, alias with 、 separators
    tokens = ['カ）', '（ユ', 'ふりこみ', '株式 会社', '', 'カ）']
    rows = [
        ('振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ', '振込カサンプルシヨウジ'),  # 振込 not in the custom list → stays, so カ) is no longer at the start → only ')' drops
        ('0123 カ)ダミーカコウ', '0123ダミーカコウ'),       # STRIP_LEADING_DIGITS=false keeps the leading digits
        ('ふりこみ　すずき　いちろう', 'スズキイチロウ'),   # hiragana token → katakana → removed anywhere
        ('ﾐﾎﾝ(ﾕ', 'ミホン'),                               # （ユ full-width → NFKC (ユ → anchored at the end
        ('株式会社サンプル', 'サンプル'),                   # '株式 会社' token: spaces removed before comparison
    ]
    pre = [{'_kind': 'txn', 'source': 'bank_csv', 'txn_date': '2026-09-1%d' % i, 'payer_name_raw': raw, 'amount': 500 + i,
            'memo': '', '_file': 'synthetic.csv', '_row': i + 2} for i, (raw, _n) in enumerate(rows)]
    coll = [item({'source': 'drive', 'txns': pre, 'warnings': [], 'ignored_withdraw': 0, 'file_name': 'synthetic.csv'})]
    inv = [{'json': {'invoice_id': 'INV-X-001', 'customer_name': '株式会社サンプル', 'payer_name_alias': 'カ）サンプル、 サンプル ,サンプル（ユ', 'amount': 500,
                     'currency': 'JPY', 'status': 'unpaid', 'paid_amount': 0, 'fee_deducted': 0, 'remind_stage': 0}},
           {'json': {'invoice_id': '', 'customer_name': 'ヘッダーだけの空行', 'payer_name_alias': '', 'amount': '', 'status': ''}}]
    e = base_expect('drive', 'synthetic.csv', 0, len(rows), 1, 0)
    for i, (raw, norm) in enumerate(rows):
        p = '[0].json.txns[%d]' % i
        e['paths'].update({p + '.payer_name_norm': norm, p + '.txn_id': '2026-09-1%d|%d|%s|' % (i, 500 + i, norm)})
    e['paths'].update({'[0].json.invoices[0].invoice_id': 'INV-X-001', '[0].json.invoices[0]._names': ['サンプル']})
    write('normalize_payer', 'config_variants_synthetic', {
        '_comment': 'SYNTHETIC: LEGAL_ENTITY_TOKENS written by a buyer in full-width / hiragana / with spaces / duplicates / empty, '
                    'STRIP_LEADING_DIGITS=false, payer_name_alias separated by 、 and spaces, and an invoice row with empty invoice_id (skipped).',
        'input': EMPTY_SHEET, 'nodes': {'Config': [item(dict(DRIVE_FIELDS['A'], **config('Watch Drive Folder', LEGAL_ENTITY_TOKENS=tokens,
                                                                                            STRIP_LEADING_DIGITS=False)))],
                                        'Read Invoices': inv, 'Collect Transactions': coll}, 'now': NOW, 'expect': e})


# ===== collect_transactions =====
def ct_scenarios():
    def expect_collect(source, txns, warnings, ignored, file_name):
        return {'length': 1, 'paths': {'[0].json.source': source, '[0].json.txns': txns, '[0].json.warnings': warnings,
                                       '[0].json.ignored_withdraw': ignored, '[0].json.file_name': file_name,
                                       '[0].pairedItem': {'item': 0}},
                'absent': ['[0].json.txns[0].txn_id', '[0].json.txns[0].payer_name_norm']}

    txA = [i['json'] for i in PBC_A if i['json']['_kind'] == 'txn']
    write('collect_transactions', 'drive_bank_A', {
        '_comment': 'Drive path: input = Parse Bank CSV output for bank_A_sjis.csv (11 pre-txns + file_stats with ignored_withdraw=4). '
                    'Config.SOURCE = Watch Drive Folder → source "drive". txns pass through unchanged (no txn_id yet).',
        'input': PBC_A, 'nodes': {'Config': [item(dict(DRIVE_FIELDS['A'], **config('Watch Drive Folder')))]}, 'now': NOW,
        'expect': expect_collect('drive', txA, [], 4, 'bank_A_sjis.csv')})

    txB = [i['json'] for i in PBC_B if i['json']['_kind'] == 'txn']
    write('collect_transactions', 'drive_bank_B', {
        '_comment': 'Drive path: Parse Bank CSV output for bank_B_utf8bom.csv (5 pre-txns, ignored_withdraw=3).',
        'input': PBC_B, 'nodes': {'Config': [item(dict(DRIVE_FIELDS['B'], **config('Watch Drive Folder', 'bank_B_utf8bom.csv')))]}, 'now': NOW,
        'expect': expect_collect('drive', txB, [], 3, 'bank_B_utf8bom.csv')})

    txM = [i['json'] for i in PM_XY]
    write('collect_transactions', 'gmail_two_mails', {
        '_comment': 'Gmail path: input = Parse Mail output for mail_bankX.eml + mail_bankY.eml (2 pre-txns, no file_stats). '
                    'Config.SOURCE = Watch Gmail Inbox → source "gmail", ignored_withdraw 0, file_name "".',
        'input': PM_XY, 'nodes': {'Config': [item(config('Watch Gmail Inbox'))]}, 'now': NOW,
        'expect': expect_collect('gmail', txM, [], 0, '')})

    warn = {'_kind': 'warning', 'type': 'no_parser_matched', 'message_id': '18f3aabb00000003', 'from': 'news@example.org', 'subject': 'Newsletter'}
    write('collect_transactions', 'gmail_with_warning', {
        '_comment': 'Gmail path with a third, SYNTHETIC mail that matched no parser (R17): Parse Mail emits a warning item; it must land in warnings, not txns.',
        'input': [PM_XY[0], item(warn, 1), PM_XY[1]], 'nodes': {'Config': [item(config('Watch Gmail Inbox'))]}, 'now': NOW,
        'expect': expect_collect('gmail', txM, [warn], 0, '')})

    e = expect_collect('schedule', [], [], 0, '')
    e['absent'] = ['[0].json.txns[0]']
    write('collect_transactions', 'schedule', {
        '_comment': 'Schedule path: the input item is the Config output itself (Schedule Trigger fields + Config keys, no _kind) → '
                    '{ source: "schedule", txns: [], warnings: [], ignored_withdraw: 0, file_name: "" }.',
        'input': [item(dict(SCHEDULE_FIELDS, **config('Run Daily Rematch')))],
        'nodes': {'Config': [item(dict(SCHEDULE_FIELDS, **config('Run Daily Rematch')))]}, 'now': NOW, 'expect': e})

    e = expect_collect('unknown', txA, [], 4, 'bank_A_sjis.csv')
    write('collect_transactions', 'unknown_source', {
        '_comment': 'Config.SOURCE is a node name outside the three triggers (e.g. a Manual Trigger while testing) → source "unknown"; items still collected.',
        'input': PBC_A, 'nodes': {'Config': [item(config('Manual Trigger'))]}, 'now': NOW, 'expect': e})

    # D31: two files in one Drive poll → Parse Bank CSV emits one file_stats per file; Collect sums ignored_withdraw and joins names.
    write('collect_transactions', 'drive_two_files', {
        '_comment': 'D31: input = Parse Bank CSV output for bank_A_sjis.csv followed by bank_B_utf8bom.csv (two file_stats items). '
                    'txns = A then B (16), ignored_withdraw = 4 + 3, file_name = "bank_A_sjis.csv, bank_B_utf8bom.csv".',
        'input': PBC_A + PBC_B, 'nodes': {'Config': [item(dict(DRIVE_FIELDS['A'], **config('Watch Drive Folder')))]}, 'now': NOW,
        'expect': expect_collect('drive', txA + txB, [], 7, 'bank_A_sjis.csv, bank_B_utf8bom.csv')})

    bad = {'_kind': 'warning', 'type': 'bad_date', 'row': 17, 'value': '2026/02/30'}
    stats = {'_kind': 'file_stats', 'file_name': 'bank_A_sjis.csv', 'ignored_withdraw': 4, 'rows_total': 16}
    write('collect_transactions', 'drive_bad_date_warning', {
        '_comment': 'SYNTHETIC: bank_A items plus one bad_date warning (a 16th data row with 2026/02/30) and file_stats accordingly. '
                    'The warning goes to warnings; the count of txns and ignored_withdraw are unchanged.',
        'input': [i for i in PBC_A if i['json']['_kind'] == 'txn'] + [item(bad), item(stats)],
        'nodes': {'Config': [item(dict(DRIVE_FIELDS['A'], **config('Watch Drive Folder')))]}, 'now': NOW,
        'expect': expect_collect('drive', txA, [bad], 4, 'bank_A_sjis.csv')})


if __name__ == '__main__':
    np_scenarios()
    ct_scenarios()
