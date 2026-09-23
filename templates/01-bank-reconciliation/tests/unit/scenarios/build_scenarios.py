#!/usr/bin/env python3
"""Build unit-test scenarios for the Parse Bank CSV / Parse Mail Code nodes from the REAL fixtures.

JA: fixtures/ の実ファイル（CSV のバイト列 → base64、.eml → Gmail Trigger（Simplify OFF）形のアイテム）から
    tests/unit/scenarios/<module>/*.json を生成する。各 JSON の "expect" は fixtures/README.md §4〜§6 の期待値表を
    手で写したもの（コードの出力から作らない）。README の raw 名義と実 CSV の内容が食い違えば生成を止める。
EN: Generates tests/unit/scenarios/<module>/*.json from the real fixtures (CSV bytes → base64, .eml → Gmail-Trigger
    shaped items). Every "expect" block is transcribed by hand from fixtures/README.md §4–§6 (never derived from the
    code under test). The build aborts if a transcribed raw remitter string disagrees with the real CSV bytes.

Run:  python3 build_scenarios.py        (idempotent; the generated JSON files are committed alongside)
"""
import base64
import csv
import email
import io
import json
import os
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
FIX = os.path.join(TPL, 'fixtures')
NOW = '2026-09-23T09:00:00+09:00'

with open(os.path.join(FIX, 'csv_mapping.examples.json'), encoding='utf-8') as f:
    MAPPINGS = json.load(f)
with open(os.path.join(FIX, 'mail_parsers.example.json'), encoding='utf-8') as f:
    PARSERS = json.load(f)['MAIL_PARSERS']
MAP_A = MAPPINGS['bank_A_sjis.csv']
MAP_B = MAPPINGS['bank_B_utf8bom.csv']

BASE_CFG = {'TZ': 'Asia/Tokyo', 'LANG': 'ja', 'CSV_MAPPING': MAP_A, 'MAIL_PARSERS': PARSERS}


def read_bytes(name):
    with open(os.path.join(FIX, name), 'rb') as f:
        return f.read()


def write(module, name, scenario):
    d = os.path.join(HERE, module)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name + '.json'), 'w', encoding='utf-8') as f:
        json.dump(scenario, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('wrote', module + '/' + name + '.json')


# --------------------------------------------------------------------------------------------------------------
# Parse Bank CSV
# --------------------------------------------------------------------------------------------------------------
def download_item(csv_bytes, file_name, json_name=None, json_mime='text/csv'):
    """One Download File output item: json = the trigger fields passed through (DESIGN §3.2), binary.data = the CSV bytes."""
    return {
        'json': {'id': 'fixture-' + file_name, 'name': file_name if json_name is None else json_name, 'mimeType': json_mime},
        'binary': {'data': {'data': base64.b64encode(csv_bytes).decode('ascii'), 'mimeType': 'text/csv',
                            'fileName': file_name, 'fileSize': f'{len(csv_bytes)} B'}},
    }


def csv_scenario(comment, csv_bytes, file_name, mapping, expect, items=None):
    return {
        '_comment': comment,
        'now': NOW,
        'input': items if items is not None else [download_item(csv_bytes, file_name)],
        'nodes': {'Config': [{'json': {**BASE_CFG, 'CSV_MAPPING': mapping}}]},
        'expect': expect,
    }


def txn(date, raw, amount, file_name, row, memo='', paired=0):
    return {'json': {'_kind': 'txn', 'source': 'bank_csv', 'txn_date': date, 'payer_name_raw': raw, 'amount': amount,
                     'memo': memo, '_file': file_name, '_row': row}, 'pairedItem': {'item': paired}}


def warning(paired=0, **fields):
    return {'json': {'_kind': 'warning', **fields}, 'pairedItem': {'item': paired}}


def file_stats(file_name, ignored, total, paired=0):
    return {'json': {'_kind': 'file_stats', 'file_name': file_name, 'ignored_withdraw': ignored, 'rows_total': total},
            'pairedItem': {'item': paired}}


# fixtures/README.md §4 — bank_A_sjis.csv: (physical row, txn_date, 摘要 raw, 入金額). Withdrawal rows 3, 8, 11, 16 are ignored.
A_TXNS = [
    (2, '2026-09-01', '振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ', 33000),
    (4, '2026-09-02', '振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ', 54780),
    (5, '2026-09-03', 'フリコミ　ヤマダ　タロウ', 9800),
    (6, '2026-09-04', '振込 ｻﾄｳ ｹｲｺ', 128000),
    (7, '2026-09-05', '振込 ｶ)ﾃｽﾄﾌﾞﾂｻﾝ', 1234567),
    (9, '2026-09-08', '振込 ｻﾝﾌﾟﾙｼｽﾃﾑ(ｶ', 100000),
    (10, '2026-09-09', '振込 ｵｵﾊﾞ ﾏｻｵ', 44000),
    (12, '2026-09-11', '振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ', 66000),
    (13, '2026-09-12', '振込 ﾃｽﾄｹﾝｾﾂ(ｶ', 88000),
    (14, '2026-09-14', '振込 ｶ)ｻﾝﾌﾟﾙﾌｰｽﾞﾄｳｷﾖｳ', 27500),
    (15, '2026-09-15', '振込 ﾅｶﾑﾗ ｼﾞﾛｳ', 5500),
]
A_IGNORED, A_ROWS_TOTAL = 4, 15

# fixtures/README.md §5 — bank_B_utf8bom.csv. Withdrawal rows 3, 6, 9 are ignored.
B_TXNS = [
    (2, '2026-09-17', '0123 カ)ダミーカコウ', 41800),
    (4, '2026-09-18', 'ふりこみ　すずき　いちろう', 15400),
    (5, '2026-09-19', 'ユ)ミホンプランニング', 57200),
    (7, '2026-09-21', '0045 タカハシ ミキ', 12100),
    (8, '2026-09-22', 'フリコミ ワタナベ ケン', 7700),
]
B_IGNORED, B_ROWS_TOTAL = 3, 8


def sanity_check(csv_bytes, encoding, mapping, expected, skip=0):
    """Abort if the transcribed README values disagree with the real fixture bytes (independent Python decoder)."""
    text = csv_bytes.decode(encoding)
    rows = list(csv.reader(io.StringIO(text, newline='')))[skip:]
    header = rows[0]
    got = []
    for i, r in enumerate(rows[1:]):
        rec = dict(zip(header, r))
        dep = rec.get(mapping['deposit_col'], '').replace(',', '')
        if dep and int(dep) > 0:
            got.append((skip + 2 + i, rec[mapping['payer_col']], int(dep)))
    want = [(row + skip, raw, amount) for row, _, raw, amount in expected]
    if got != want:
        raise SystemExit(f'README transcription disagrees with fixture bytes:\n got  {got}\n want {want}')


def expect_items(txns, file_name, ignored, total, row_shift=0, paired=0):
    return [txn(d, raw, amt, file_name, row + row_shift, paired=paired) for row, d, raw, amt in txns] + [file_stats(file_name, ignored, total, paired=paired)]


def build_csv_scenarios():
    a = read_bytes('bank_A_sjis.csv')
    a1 = read_bytes('bank_A_sjis_skip1.csv')
    b = read_bytes('bank_B_utf8bom.csv')
    sanity_check(a, 'cp932', MAP_A, A_TXNS)
    sanity_check(a1, 'cp932', MAP_A, A_TXNS, skip=1)
    sanity_check(b, 'utf-8-sig', MAP_B, B_TXNS)
    assert b[:3] == b'\xef\xbb\xbf'

    exp_a = {'items': expect_items(A_TXNS, 'bank_A_sjis.csv', A_IGNORED, A_ROWS_TOTAL)}
    write('parse_bank_csv', 'bank_A_sjis',
          csv_scenario('R01–R09 / R07 / R08: bank_A_sjis.csv (Shift_JIS, CRLF, quoted amounts) with the default CSV_MAPPING '
                       '(encoding shift_jis). Expect the 11 pre-txns of fixtures/README.md §4 in file order, then file_stats '
                       '(ignored_withdraw 4, rows_total 15). No U+FFFD, memo "" (no memo_col).', a, 'bank_A_sjis.csv', MAP_A, exp_a))
    write('parse_bank_csv', 'bank_A_sjis_encoding_auto',
          csv_scenario('encoding "auto" on cp932 bytes: strict UTF-8 decode fails → falls back to shift_jis → identical result to '
                       'the explicit shift_jis scenario.', a, 'bank_A_sjis.csv', {**MAP_A, 'encoding': 'auto'}, exp_a))
    write('parse_bank_csv', 'bank_A_sjis_skip1_skip_rows_1',
          csv_scenario('R15: bank_A_sjis_skip1.csv (one title line before the header) with skip_rows=1 → the same 11 pre-txns as '
                       'bank_A_sjis.csv with _row one larger; ignored_withdraw 4.', a1, 'bank_A_sjis_skip1.csv',
                       {**MAP_A, 'skip_rows': 1},
                       {'items': expect_items(A_TXNS, 'bank_A_sjis_skip1.csv', A_IGNORED, A_ROWS_TOTAL, row_shift=1)}))
    write('parse_bank_csv', 'bank_A_sjis_skip1_skip_rows_0_fails',
          csv_scenario('R15 negative: bank_A_sjis_skip1.csv with skip_rows=0 must fail loudly (the title line becomes the header) '
                       'instead of silently yielding zero rows.', a1, 'bank_A_sjis_skip1.csv', MAP_A,
                       {'error_includes': 'CSV column not found: "日付"'}))

    exp_b = {'items': expect_items(B_TXNS, 'bank_B_utf8bom.csv', B_IGNORED, B_ROWS_TOTAL)}
    write('parse_bank_csv', 'bank_B_utf8bom',
          csv_scenario('R13 / R08: bank_B_utf8bom.csv (UTF-8 BOM, yyyyMMdd, no thousands separators) with the B CSV_MAPPING '
                       '(encoding utf-8, date_format yyyyMMdd). BOM must not remain in the first header (取引日). Expect the 5 '
                       'pre-txns of fixtures/README.md §5, then file_stats (ignored_withdraw 3, rows_total 8).',
                       b, 'bank_B_utf8bom.csv', MAP_B, exp_b))
    write('parse_bank_csv', 'bank_B_utf8bom_encoding_shift_jis_bom_wins',
          csv_scenario('A UTF-8 BOM wins over the configured encoding: same file with encoding shift_jis → identical result.',
                       b, 'bank_B_utf8bom.csv', {**MAP_B, 'encoding': 'shift_jis'}, exp_b))
    write('parse_bank_csv', 'bank_B_utf8bom_encoding_auto_date_format_auto',
          csv_scenario('encoding auto + date_format auto on the B file → identical result (yyyyMMdd is accepted by auto).',
                       b, 'bank_B_utf8bom.csv', {**MAP_B, 'encoding': 'auto', 'date_format': 'auto'}, exp_b))

    # Derived from the real B fixture: the same bytes without the BOM (UTF-8 without BOM).
    nobom = b[3:]
    exp_nobom = {'items': expect_items(B_TXNS, 'bank_B_utf8_nobom.csv', B_IGNORED, B_ROWS_TOTAL)}
    write('parse_bank_csv', 'bank_utf8_nobom_encoding_auto',
          csv_scenario('bank_B_utf8bom.csv with the BOM stripped (UTF-8 without BOM) and encoding "auto": strict UTF-8 decode '
                       'succeeds → same 5 pre-txns.', nobom, 'bank_B_utf8_nobom.csv', {**MAP_B, 'encoding': 'auto'}, exp_nobom))
    write('parse_bank_csv', 'bank_utf8_nobom_encoding_utf8',
          csv_scenario('Same BOM-less bytes with explicit encoding utf-8 → same result.', nobom, 'bank_B_utf8_nobom.csv',
                       {**MAP_B, 'encoding': 'utf-8'}, exp_nobom))

    # Derived from the real A fixture: header + only its withdrawal rows (入金額 empty) → no txn at all.
    a_rows = list(csv.reader(io.StringIO(a.decode('cp932'), newline='')))
    wd_rows = [a_rows[0]] + [r for r in a_rows[1:] if r[2].strip() == '']
    assert len(wd_rows) == 1 + A_IGNORED
    buf = io.StringIO()
    csv.writer(buf, lineterminator='\r\n').writerows(wd_rows)
    all_wd = buf.getvalue().encode('cp932')
    write('parse_bank_csv', 'bank_all_withdrawals',
          csv_scenario('R07: the header of bank_A_sjis.csv plus only its 4 withdrawal rows (Shift_JIS). No pre-txn is produced; '
                       'the only output item is file_stats with ignored_withdraw 4 and rows_total 4.', all_wd,
                       'bank_A_withdrawals_only.csv', MAP_A, {'items': [file_stats('bank_A_withdrawals_only.csv', 4, 4)]}))

    # Synthetic edge cases in the A layout (Shift_JIS, CRLF), memo_col = 残高 so the memo mapping is exercised too.
    edge_rows = [
        ['日付', '摘要', '入金額', '出金額', '残高'],
        ['2026/02/30', '振込 ﾊﾞｯﾄﾞﾃﾞｰﾄ', '1,000', '', '1,000'],          # row 2: invalid calendar date → bad_date warning
        ['2026/09/20', '振込 ｾﾞﾛ', '0', '', '1,000'],                    # row 3: deposit 0 → ignored
        ['2026/09/21', '振込 ｶ)ｶﾝﾏ,ｲﾘ', '１０，０００', '', '11,000'],    # row 4: quoted comma in name, full-width digits/comma amount
        ['2026/09/22', '振込 "ﾆｼﾞｭｳ" ｲﾝﾖｳ', '2,000', '', '13,000'],       # row 5: doubled quotes inside a quoted field
        ['2026-09-23', '振込 ﾊｲﾌﾝ', '3000', '', '16,000'],               # row 6: yyyy-MM-dd
        ['20260924', '振込 ﾑｸｷﾞﾘ', '4000', '', '20,000'],                # row 7: yyyyMMdd
        ['2026/09/26', '振込 ﾐｼﾞｶｲ', '5000'],                            # row 8: short row (missing columns → "")
        ['2026/9/28', '振込 ﾋﾄｹﾀ', '6000', '', '30,500'],                # row 9: non zero-padded month/day
        ['２０２６年９月２９日', '振込 ｾﾞﾝｶｸ', '7,000', '', '37,500'],    # row 10: full-width Japanese date → NFKC
        ['2026/09/30', '振込 ﾏｲﾅｽ', '-500', '', '37,000'],               # row 11: negative deposit → ignored
    ]
    buf = io.StringIO()
    csv.writer(buf, lineterminator='\r\n').writerows(edge_rows)
    edge = buf.getvalue().encode('cp932')
    assert b'"\xe5\xb6' not in edge  # (no accidental UTF-8)
    fn = 'bank_edge_cases.csv'
    write('parse_bank_csv', 'bank_synthetic_edge_memo_col',
          csv_scenario('Synthetic edge cases in the A layout (Shift_JIS) with memo_col=残高: bad calendar date → bad_date warning '
                       '(row 2), deposit 0 and negative deposit ignored, quoted comma / doubled quotes / short row / '
                       'yyyy-MM-dd / yyyyMMdd / non-padded / full-width Japanese date all parse. Output order: txns, warnings, '
                       'file_stats.', edge, fn, {**MAP_A, 'memo_col': '残高'},
                       {'items': [
                           txn('2026-09-21', '振込 ｶ)ｶﾝﾏ,ｲﾘ', 10000, fn, 4, memo='11,000'),
                           txn('2026-09-22', '振込 "ﾆｼﾞｭｳ" ｲﾝﾖｳ', 2000, fn, 5, memo='13,000'),
                           txn('2026-09-23', '振込 ﾊｲﾌﾝ', 3000, fn, 6, memo='16,000'),
                           txn('2026-09-24', '振込 ﾑｸｷﾞﾘ', 4000, fn, 7, memo='20,000'),
                           txn('2026-09-26', '振込 ﾐｼﾞｶｲ', 5000, fn, 8, memo=''),
                           txn('2026-09-28', '振込 ﾋﾄｹﾀ', 6000, fn, 9, memo='30,500'),
                           txn('2026-09-29', '振込 ｾﾞﾝｶｸ', 7000, fn, 10, memo='37,500'),
                           warning(type='bad_date', row=2, value='2026/02/30'),
                           file_stats(fn, 2, 10),
                       ]}))

    # D31: two files in one execution (Drive Trigger emits every file created since the last poll as one item each):
    # item 0 = bank_A_sjis.csv, item 1 = the synthetic edge-case file with the default mapping (no memo_col → memo "").
    # Output = item 0's txns + file_stats (pairedItem 0), then item 1's txns + bad_date warning + file_stats (pairedItem 1).
    edge_no_memo = [txn(t['json']['txn_date'], t['json']['payer_name_raw'], t['json']['amount'], fn, t['json']['_row'], memo='', paired=1)
                    for t in [txn('2026-09-21', '振込 ｶ)ｶﾝﾏ,ｲﾘ', 10000, fn, 4), txn('2026-09-22', '振込 "ﾆｼﾞｭｳ" ｲﾝﾖｳ', 2000, fn, 5),
                              txn('2026-09-23', '振込 ﾊｲﾌﾝ', 3000, fn, 6), txn('2026-09-24', '振込 ﾑｸｷﾞﾘ', 4000, fn, 7),
                              txn('2026-09-26', '振込 ﾐｼﾞｶｲ', 5000, fn, 8), txn('2026-09-28', '振込 ﾋﾄｹﾀ', 6000, fn, 9),
                              txn('2026-09-29', '振込 ｾﾞﾝｶｸ', 7000, fn, 10)]]
    write('parse_bank_csv', 'two_files_A_and_edge_in_one_run',
          csv_scenario('D31: two Download File items in one execution (two CSVs created in the same Drive poll). Both must be parsed: '
                       'the 11 A pre-txns + A file_stats paired to item 0, then the 7 edge pre-txns + its bad_date warning + '
                       'file_stats paired to item 1 (24 items). Before D31 only item 0 was read (12 items, one file).',
                       None, None, MAP_A,
                       {'items': expect_items(A_TXNS, 'bank_A_sjis.csv', A_IGNORED, A_ROWS_TOTAL) + edge_no_memo +
                                 [warning(paired=1, type='bad_date', row=2, value='2026/02/30'), file_stats(fn, 2, 10, paired=1)]},
                       items=[download_item(a, 'bank_A_sjis.csv'), download_item(edge, fn)]))

    # D22: a Google Sheet that Drive converted on upload. Download File exports it as UTF-8 CSV WITHOUT BOM and passes the
    # trigger json through (mimeType application/vnd.google-apps.spreadsheet, name without extension). It must be decoded as
    # UTF-8 even though CSV_MAPPING.encoding is the default shift_jis.
    a_utf8 = a.decode('cp932').encode('utf-8')
    assert a_utf8[:3] != b'\xef\xbb\xbf'
    sheet_item = download_item(a_utf8, 'bank_A_sjis.csv', json_name='bank_A_sjis', json_mime='application/vnd.google-apps.spreadsheet')
    write('parse_bank_csv', 'sheets_export_utf8_nobom_default_shift_jis',
          csv_scenario('D22: Download File output of a converted Google Sheet (json.mimeType application/vnd.google-apps.spreadsheet, '
                       'binary = bank_A re-encoded as UTF-8 without BOM) with the DEFAULT mapping (encoding shift_jis). The source '
                       'mimeType forces UTF-8, so the 11 A pre-txns come out intact; _file is json.name (the Drive file name).',
                       None, None, MAP_A, {'items': expect_items(A_TXNS, 'bank_A_sjis', A_IGNORED, A_ROWS_TOTAL)}, items=[sheet_item]))
    write('parse_bank_csv', 'plain_utf8_nobom_default_shift_jis_fails',
          csv_scenario('Control for D22: the same UTF-8 bytes uploaded as a plain CSV (mimeType text/csv) with encoding shift_jis are '
                       'NOT special-cased and fail loudly on the mojibake header (the buyer must set encoding utf-8 or auto).',
                       a_utf8, 'bank_A_utf8.csv', MAP_A, {'error_includes': 'CSV column not found: "日付"'}))

    write('parse_bank_csv', 'bank_A_explicit_date_format_strict',
          csv_scenario('date_format "yyyy/MM/dd" (explicit) on bank_A_sjis.csv: every date is zero-padded so the strict Luxon '
                       'parse yields the same 11 pre-txns.', a, 'bank_A_sjis.csv', {**MAP_A, 'date_format': 'yyyy/MM/dd'}, exp_a))
    write('parse_bank_csv', 'bank_A_explicit_wrong_date_format_all_bad_date',
          csv_scenario('date_format "yyyyMMdd" (explicit, wrong for A): strict parsing rejects 2026/09/01 etc., so every deposit '
                       'row becomes a bad_date warning (rows 2,4,5,6,7,9,10,12,13,14,15) and rows_total stays 15.',
                       a, 'bank_A_sjis.csv', {**MAP_A, 'date_format': 'yyyyMMdd'},
                       {'items': [warning(type='bad_date', row=row, value=raw_date) for row, raw_date in
                                  [(2, '2026/09/01'), (4, '2026/09/02'), (5, '2026/09/03'), (6, '2026/09/04'), (7, '2026/09/05'),
                                   (9, '2026/09/08'), (10, '2026/09/09'), (12, '2026/09/11'), (13, '2026/09/12'),
                                   (14, '2026/09/14'), (15, '2026/09/15')]] + [file_stats('bank_A_sjis.csv', 4, 15)]}))
    write('parse_bank_csv', 'bank_A_missing_column_fails',
          csv_scenario('A wrong deposit_col ("入金") must fail with the column name and the actual header listed.',
                       a, 'bank_A_sjis.csv', {**MAP_A, 'deposit_col': '入金'},
                       {'error_includes': 'CSV column not found: "入金". header = 日付 | 摘要 | 入金額 | 出金額 | 残高'}))
    write('parse_bank_csv', 'bank_A_skip_rows_too_large_fails',
          csv_scenario('skip_rows larger than the file must fail loudly.', a, 'bank_A_sjis.csv', {**MAP_A, 'skip_rows': 99},
                       {'error_includes': 'CSV has no header row after skip_rows=99'}))
    write('parse_bank_csv', 'bank_A_unsupported_encoding_fails',
          csv_scenario('An encoding label TextDecoder does not know ("utf-99") must fail (RangeError), not decode silently.',
                       a, 'bank_A_sjis.csv', {**MAP_A, 'encoding': 'utf-99'}, {'error_includes': 'is not supported'}))


# --------------------------------------------------------------------------------------------------------------
# Parse Mail
# --------------------------------------------------------------------------------------------------------------
def gmail_item_from_eml(eml_name, gmail_id):
    """Gmail Trigger (Simplify OFF) shaped json built from the real .eml with Python's email package."""
    msg = email.message_from_bytes(read_bytes(eml_name))
    subject = str(make_header(decode_header(msg['Subject'])))
    name, addr = parseaddr(str(make_header(decode_header(msg['From']))))
    date = parsedate_to_datetime(msg['Date']).isoformat()
    body = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8')
    return {
        'id': gmail_id, 'threadId': gmail_id, 'labelIds': ['INBOX', 'UNREAD'], 'date': date,
        'from': {'value': [{'address': addr, 'name': name}], 'text': f'{name} <{addr}>' if name else addr},
        'to': {'value': [{'address': 'owner@example.com', 'name': ''}], 'text': 'owner@example.com'},
        'subject': subject, 'text': body, 'html': '',
    }


def mail_scenario(comment, items, expect_items_):
    return {'_comment': comment, 'now': NOW, 'input': [{'json': j} for j in items],
            'nodes': {'Config': [{'json': BASE_CFG}]}, 'expect': {'items': expect_items_}}


def mail_txn(i, date, raw, amount, subject, gmail_id, parser):
    return {'json': {'_kind': 'txn', 'source': 'gmail', 'txn_date': date, 'payer_name_raw': raw, 'amount': amount,
                     'memo': f'{subject} (gmail:{gmail_id})', '_message_id': gmail_id, '_parser': parser},
            'pairedItem': {'item': i}}


def mail_warning(i, **fields):
    return {'json': {'_kind': 'warning', **fields}, 'pairedItem': {'item': i}}


def build_mail_scenarios():
    X_ID, Y_ID = '18f3aabb00000001', '18f3aabb00000002'   # fictional Gmail ids from fixtures/mail_pinned.example.json
    x = gmail_item_from_eml('mail_bankX.eml', X_ID)
    y = gmail_item_from_eml('mail_bankY.eml', Y_ID)
    assert x['subject'] == '【サンプル銀行】ご入金のお知らせ' and x['from']['text'] == 'サンプル銀行 <notice@example.jp>'
    assert y['subject'] == 'Deposit Notification - Sample Bank' and y['from']['text'] == 'Sample Bank Online <alerts@example.com>'
    assert x['date'] == '2026-09-17T09:12:00+09:00' and y['date'] == '2026-09-19T08:30:00+09:00'
    assert '日付：２０２６年９月１７日' in x['text'] and 'Transaction Date   2026-09-18' in y['text']

    # fixtures/README.md §6 expectations
    X_TXN = lambda i: mail_txn(i, '2026-09-17', 'カ)ダミーデンキ', 104500, x['subject'], X_ID, 'bankX')
    Y_TXN = lambda i: mail_txn(i, '2026-09-18', 'ササキ ハナコ', 19800, y['subject'], Y_ID, 'bankY')

    write('parse_mail', 'mail_bankX_eml',
          mail_scenario('R10: mail_bankX.eml (labeled lines, full-width digits/colons, half-width kana) parsed with Python email '
                        'into a Gmail-Trigger (Simplify OFF) item. Parser bankX. Expect amount 104500, payer_name_raw '
                        'カ)ダミーデンキ (post-NFKC), txn_date 2026-09-17 from the body, memo = subject + " (gmail:<id>)".',
                        [x], [X_TXN(0)]))
    write('parse_mail', 'mail_bankY_eml',
          mail_scenario('R10: mail_bankY.eml (table layout, no colons). Parser bankY. Expect 19800 / "ササキ ハナコ" / '
                        'txn_date 2026-09-18 taken from the body, NOT the 2026-09-19 Date header.', [y], [Y_TXN(0)]))

    # R17 (a) no parser matches, (b) parser matches but captures nothing — shapes from tests/CASES.md R17
    r17a = {'id': '18f3aabb00000009', 'date': '2026-09-20T10:00:00+09:00', 'from': {'text': 'someone@example.org'},
            'subject': '会議のご案内', 'text': '来週の会議についてご連絡します。'}
    r17b = {'id': '18f3aabb00000010', 'date': '2026-09-20T10:05:00+09:00', 'from': {'text': 'サンプル銀行 <notice@example.jp>'},
            'subject': '【サンプル銀行】ご入金のお知らせ', 'text': '本日の入金はありません。'}
    W17A = lambda i: mail_warning(i, type='no_parser_matched', message_id='18f3aabb00000009', from_='someone@example.org',
                                  subject='会議のご案内')
    W17B = lambda i: mail_warning(i, type='parser_no_capture', parser='bankX', message_id='18f3aabb00000010',
                                  from_='サンプル銀行 <notice@example.jp>', subject='【サンプル銀行】ご入金のお知らせ')

    def fix_from(item):   # "from" is a reserved word in Python kwargs
        j = item['json']
        if 'from_' in j:
            j['from'] = j.pop('from_')
        return item

    write('parse_mail', 'mail_no_parser_matched',
          mail_scenario('R17(a): a mail from someone@example.org with subject 会議のご案内 matches no MAIL_PARSERS entry → '
                        'warning no_parser_matched carrying message_id / from / subject.', [r17a], [fix_from(W17A(0))]))
    write('parse_mail', 'mail_parser_no_capture',
          mail_scenario('R17(b): from/subject match bankX but the body has no amount or remitter line → warning '
                        'parser_no_capture with parser=bankX.', [r17b], [fix_from(W17B(0))]))

    x_nodate = {**x, 'text': '\r\n'.join(l for l in x['text'].split('\r\n') if not l.startswith('日付'))}
    assert '日付' not in x_nodate['text']
    write('parse_mail', 'mail_bankX_no_date_line_fallback',
          mail_scenario('mail_bankX.eml with its 日付 line removed: date_regex finds nothing → txn_date falls back to the '
                        'email Date header (2026-09-17T09:12:00+09:00 → 2026-09-17 in Asia/Tokyo).', [x_nodate], [X_TXN(0)]))
    x_nodate_utc = {**x_nodate, 'date': '2026-09-16T23:30:00.000Z'}
    write('parse_mail', 'mail_bankX_no_date_line_fallback_utc',
          mail_scenario('Same, but the email date is given in UTC (2026-09-16T23:30:00Z = 2026-09-17 08:30 JST): the fallback '
                        'must use the Config TZ calendar day → 2026-09-17, not 2026-09-16.', [x_nodate_utc], [X_TXN(0)]))
    x_nodate_baddate = {**x_nodate, 'date': ''}
    write('parse_mail', 'mail_bankX_no_date_anywhere_warning',
          mail_scenario('DECISION coverage: no date line in the body AND an empty/unparsable email date → a bad_date warning '
                        '(parser bankX) instead of a txn with an invalid date.', [x_nodate_baddate],
                        [mail_warning(0, type='bad_date', parser='bankX', message_id=X_ID, **{'from': x['from']['text']},
                                      subject=x['subject'], value='')]))

    html = '<html><body>' + ''.join(f'<p>{l}</p>' for l in x['text'].split('\r\n')) + '</body></html>'
    x_html = {**x, 'text': '', 'html': html}
    write('parse_mail', 'mail_bankX_html_only',
          mail_scenario('mail_bankX.eml body delivered as HTML only (text empty): htmlToText turns </p> into newlines so the '
                        'same values are extracted.', [x_html], [X_TXN(0)]))

    x_from_value_only = {**x, 'from': {'value': [{'address': 'notice@example.jp', 'name': 'サンプル銀行'}]}}
    write('parse_mail', 'mail_bankX_from_value_only',
          mail_scenario('DECISION coverage: `from` without `text` (only value[].address) still matches bankX via the address.',
                        [x_from_value_only], [X_TXN(0)]))

    write('parse_mail', 'mail_batch_mixed',
          mail_scenario('Four mails in one run (X, Y, R17a, R17b): one output item per input, in order, pairedItem 0..3.',
                        [x, y, r17a, r17b], [X_TXN(0), Y_TXN(1), fix_from(W17A(2)), fix_from(W17B(3))]))


if __name__ == '__main__':
    build_csv_scenarios()
    build_mail_scenarios()
