// End-to-end chain of the template-01 Code nodes over the REAL fixtures, wired exactly as workflow.json will wire them.
// Every node is executed by tests/unit/run-code-node.mjs (child process) on the SAME code/*.js files that workflow.json embeds
// (ASSUMPTIONS A15), so a shape mismatch between two modules fails here before the workflow is imported into n8n.
//
//   usage: node tests/unit/integration.mjs [--luxon <path to luxon>] [--tmp <dir>] [--keep]
//     --luxon  n8n's luxon copy (default: env LUXON_PATH, else the module name "luxon")
//     --tmp    where per-node scenario / output files are written (default: env UNIT_TMP_DIR, else mktemp under os.tmpdir())
//     --keep   do not delete the per-node files afterwards
//   Node >= 24 with full ICU (TextDecoder('shift_jis')). No dependencies other than luxon (used by the runner only).
//
// Chain (DESIGN.md §2.1 / §3):
//   trigger item → Config (Set, include all input fields, SOURCE = trigger name)
//     → drive:    Download File {json, binary.data = bank CSV} → Parse Bank CSV
//     → gmail:    Parse Mail over the Gmail-Trigger-shaped items derived from the two .eml fixtures
//     → schedule: nothing (the Config item goes straight to Collect Transactions)
//   → Collect Transactions → [Read Invoices = invoices.seed.csv rows] → [Read Transactions = transactions.seed.csv rows or {}]
//   → Normalize Payer → Match Invoices → Route Match Results (split on _kind) → Build Notification
//   → Notify Slack / Email / LINE / Chatwork (simulated success + error-output items) → Merge → Check Notification Results
// Assertions: tests/CASES.md R01–R06, R07 (as part of R08/R13 counts), R08, R09 (+ R09-b gmail), R10, R13, R14-a, R19 (schedule
// no-op), the full ja notification of CASES §3, the title format of CLAUDE.md 付録A, and Check Notification Results (R11-b shapes).
// Expected values are transcribed from fixtures/README.md §2–§6 and tests/CASES.md (never computed here).
// Output: PASS/FAIL per assertion, a summary line, exit 1 on any failure.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TPL = path.resolve(HERE, '..', '..');
const ROOT = path.resolve(TPL, '..', '..');
const FX = path.join(TPL, 'fixtures');
const CODE = path.join(TPL, 'code');
const RUNNER = path.join(HERE, 'run-code-node.mjs');
const NOW = '2026-09-23T09:00:00+09:00';   // run time used by every node ($now); CASES §3 dates the notification 2026-09-23
const TODAY = '2026-09-23';

const argv = process.argv.slice(2);
const argOf = (flag, dflt) => (argv.includes(flag) ? argv[argv.indexOf(flag) + 1] : dflt);
const LUXON = argOf('--luxon', process.env.LUXON_PATH || 'luxon');
const KEEP = argv.includes('--keep');
const TMP_BASE = argOf('--tmp', process.env.UNIT_TMP_DIR || '');
const TMP = TMP_BASE ? path.join(TMP_BASE, 'integration') : fs.mkdtempSync(path.join(os.tmpdir(), 'tpl01-integration-'));
fs.mkdirSync(TMP, { recursive: true });

// ------------------------------------------------------------------------------------------------------------------
// tiny assertion framework
// ------------------------------------------------------------------------------------------------------------------
let pass = 0, fail = 0;
const canon = (v) => JSON.stringify(v, (k, x) => (x && typeof x === 'object' && !Array.isArray(x))
  ? Object.keys(x).sort().reduce((o, kk) => { o[kk] = x[kk]; return o; }, {}) : x);
function check(id, desc, ok, detail) {
  if (ok) { pass++; console.log(`PASS ${id}: ${desc}`); }
  else { fail++; console.log(`FAIL ${id}: ${desc}`); if (detail !== undefined) console.log('    ' + String(detail).split('\n').join('\n    ')); }
}
const eq = (id, desc, got, want) => check(id, desc, canon(got) === canon(want), canon(got) === canon(want) ? undefined : `expected ${canon(want)}\n     got ${canon(got)}`);
const has = (id, desc, hay, needle) => check(id, desc, typeof hay === 'string' && hay.includes(needle), `missing: ${needle}\n     in: ${JSON.stringify(hay)}`);
const not = (id, desc, hay, needle) => check(id, desc, typeof hay === 'string' && !hay.includes(needle), `unexpected: ${needle}`);

// ------------------------------------------------------------------------------------------------------------------
// run one Code node through run-code-node.mjs (same code file that workflow.json embeds)
// ------------------------------------------------------------------------------------------------------------------
let runNo = 0;
function runNode(codeFile, label, scenario) {
  const base = path.join(TMP, `${String(++runNo).padStart(2, '0')}-${label.replace(/[^a-z0-9]+/gi, '_')}`);
  fs.writeFileSync(`${base}.scenario.json`, JSON.stringify({ now: NOW, ...scenario }, null, 1));
  const r = spawnSync(process.execPath, [RUNNER, path.join(CODE, codeFile), '-', `${base}.scenario.json`, '--luxon', LUXON],
    { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  fs.writeFileSync(`${base}.out.json`, r.stdout || '');
  fs.writeFileSync(`${base}.err.txt`, r.stderr || '');
  if (r.status !== 0) return { error: (r.stderr || `exit ${r.status}`).trim() };
  return { items: JSON.parse(r.stdout) };
}
function mustRun(codeFile, label, scenario) {
  const r = runNode(codeFile, label, scenario);
  check(`${label}`, `${codeFile} ran (${label})`, !r.error, r.error);
  return r.items || [];
}

// ------------------------------------------------------------------------------------------------------------------
// Config item (DESIGN.md §4 defaults). MESSAGES from shared/messages.*.json, MAIL_PARSERS from fixtures/mail_parsers.example.json,
// CSV_MAPPING from fixtures/csv_mapping.examples.json. Set node "include all input fields" → the trigger fields are kept,
// SOURCE = $prevNode.name (A13). Placeholders only — no real IDs.
// ------------------------------------------------------------------------------------------------------------------
const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const msgJa = readJson(path.join(ROOT, 'shared', 'messages.ja.json'));
const msgEn = readJson(path.join(ROOT, 'shared', 'messages.en.json'));
const MAIL_PARSERS = readJson(path.join(FX, 'mail_parsers.example.json')).MAIL_PARSERS;
const CSV_MAPPINGS = readJson(path.join(FX, 'csv_mapping.examples.json'));
const LEGAL_ENTITY_TOKENS = ['カ)', '(カ', 'ユ)', '(ユ', 'ド)', '(ド', 'シヤ)', '(シヤ', 'ザイ)', '(ザイ', 'ガク)', '(ガク', 'イ)', '(イ', 'ホ)', '(ホ',
  '株式会社', '有限会社', '合同会社', '合名会社', '合資会社', '一般社団法人', '一般財団法人', '医療法人', '学校法人', '社会福祉法人',
  'カブシキガイシヤ', 'カブシキカイシヤ', 'ユウゲンガイシヤ', 'ゴウドウガイシヤ', 'イツパンシヤダンホウジン', 'イリヨウホウジン',
  '振込', 'フリコミ', 'ゴフリコミ'];
function configItem(triggerJson, source, { csv = 'bank_A_sjis.csv', overrides = {} } = {}) {
  return { json: {
    ...triggerJson,                                    // Include in Output: All Input Fields
    TZ: 'Asia/Tokyo', LANG: 'ja',
    SHEET_ID: 'REPLACE_ME_SHEET_ID', SHEET_INVOICES: 'invoices', SHEET_TRANSACTIONS: 'transactions',
    DRIVE_FOLDER_ID: 'REPLACE_ME_DRIVE_FOLDER_ID',
    GMAIL_QUERY: 'subject:(入金 OR Deposit) newer_than:1d', RUN_AT: '09:00',
    TRIGGERS_ENABLED: { drive: true, gmail: true, schedule: true },
    CSV_MAPPING: { ...CSV_MAPPINGS[csv] },
    MAIL_PARSERS,
    LEGAL_ENTITY_TOKENS: [...LEGAL_ENTITY_TOKENS], STRIP_LEADING_DIGITS: true,
    FEE_SET: [110, 165, 220, 275, 330, 440, 550, 660, 770, 880], NAME_MIN_CONTAINS: 3,
    NOTIFY_CHANNELS: ['slack'],
    SLACK_CHANNEL: 'REPLACE_ME_SLACK_CHANNEL_ID', NOTIFY_EMAIL_TO: 'replace-me@example.com',
    LINE_TO_USER_ID: 'REPLACE_ME_LINE_USER_ID', CHATWORK_ROOM_ID: 'REPLACE_ME_CHATWORK_ROOM_ID',
    NOTIFY_MAX_LINES: 40,
    MESSAGES: { ja: { recon_summary: msgJa.recon_summary, error_notice: msgJa.error_notice },
                en: { recon_summary: msgEn.recon_summary, error_notice: msgEn.error_notice } },
    SOURCE: source,                                    // {{ $prevNode.name }}
    ...overrides,
  } };
}

// ------------------------------------------------------------------------------------------------------------------
// fixtures → node inputs
// ------------------------------------------------------------------------------------------------------------------
// RFC 4180-ish CSV (quoted commas / doubled quotes) for the UTF-8 seed files
function parseCsv(text) {
  const rows = []; let row = []; let field = ''; let q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else q = false; } else field += c; }
    else if (c === '"') q = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\r') { /* skip */ }
    else if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
    else field += c;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  return rows.filter((r) => r.some((f) => f.trim() !== ''));
}
// Google Sheets "Get Row(s)" shape (DESIGN §3.5): numbers for numeric columns, "" for empty cells, everything else a string
const INT_COLS = new Set(['amount', 'paid_amount', 'fee_deducted', 'remind_stage']);
function sheetRows(csvName) {
  const [header, ...rows] = parseCsv(fs.readFileSync(path.join(FX, csvName), 'utf8').replace(/^﻿/, ''));
  return rows.map((r) => ({ json: Object.fromEntries(header.map((h, i) => {
    const v = r[i] ?? '';
    return [h, INT_COLS.has(h) && v !== '' ? Number(v) : v];
  })) }));
}
const EMPTY_SHEET = [{ json: {} }];                     // Always Output Data on an empty sheet

// Drive path: trigger item (DESIGN §3.1) → Config → Download File output (DESIGN §3.2: json = file meta, binary.data = the CSV bytes)
function driveTrigger(fileName) {
  return { kind: 'drive#file', id: `FIXTURE_FILE_${fileName}`, name: fileName, mimeType: 'text/csv',
           parents: ['REPLACE_ME_DRIVE_FOLDER_ID'], createdTime: '2026-09-23T00:05:00.000Z' };
}
function downloadFileItem(fileName) {
  const buf = fs.readFileSync(path.join(FX, fileName));
  const t = driveTrigger(fileName);
  return { json: { id: t.id, name: t.name, mimeType: t.mimeType },
           binary: { data: { data: buf.toString('base64'), mimeType: 'text/csv', fileName, fileSize: `${buf.length} B` } } };
}

// Gmail path: the two .eml fixtures → Gmail Trigger (Simplify OFF) items (DESIGN §3.1). Minimal RFC 822 reader:
// unfolded headers, RFC 2047 encoded-words (base64 / quoted-printable, utf-8), base64 / 8bit / quoted-printable body.
function decodeEncodedWords(s) {
  return s.replace(/=\?([^?]+)\?([bBqQ])\?([^?]*)\?=(?:\s+(?==\?))?/g, (m, cs, enc, txt) => {
    const bytes = enc.toLowerCase() === 'b' ? Buffer.from(txt, 'base64')
      : Buffer.from(txt.replace(/_/g, ' ').replace(/=([0-9A-Fa-f]{2})/g, (x, h) => String.fromCharCode(parseInt(h, 16))), 'latin1');
    return new TextDecoder(cs.toLowerCase()).decode(bytes);
  });
}
const MONTHS = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12 };
function rfc822DateToIso(s) {                           // "Thu, 17 Sep 2026 09:12:00 +0900" → "2026-09-17T09:12:00+09:00"
  const m = s.match(/(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})\s+(\d{2}):(\d{2}):(\d{2})\s+([+-])(\d{2})(\d{2})/);
  if (!m) throw new Error(`unparsable Date header: ${s}`);
  const mm = String(MONTHS[m[2].toLowerCase()]).padStart(2, '0');
  return `${m[3]}-${mm}-${m[1].padStart(2, '0')}T${m[4]}:${m[5]}:${m[6]}${m[7]}${m[8]}:${m[9]}`;
}
function gmailItemFromEml(emlName, gmailId) {
  const raw = fs.readFileSync(path.join(FX, emlName), 'latin1');   // byte-preserving; charset decoding is applied per part below
  const sep = raw.indexOf('\r\n\r\n') >= 0 ? '\r\n\r\n' : '\n\n';
  const headText = raw.slice(0, raw.indexOf(sep));
  const bodyText = raw.slice(raw.indexOf(sep) + sep.length);
  const headers = {};
  for (const line of headText.replace(/\r?\n[ \t]+/g, ' ').split(/\r?\n/)) {
    const i = line.indexOf(':'); if (i < 0) continue;
    headers[line.slice(0, i).trim().toLowerCase()] = line.slice(i + 1).trim();
  }
  const charset = (headers['content-type'] || '').match(/charset="?([^";\s]+)"?/i)?.[1] || 'utf-8';
  const cte = (headers['content-transfer-encoding'] || '7bit').toLowerCase();
  let bodyBytes;
  if (cte === 'base64') bodyBytes = Buffer.from(bodyText.replace(/\s+/g, ''), 'base64');
  else if (cte === 'quoted-printable') bodyBytes = Buffer.from(bodyText.replace(/=\r?\n/g, '').replace(/=([0-9A-Fa-f]{2})/g, (x, h) => String.fromCharCode(parseInt(h, 16))), 'latin1');
  else bodyBytes = Buffer.from(bodyText, 'latin1');
  const body = new TextDecoder(charset.toLowerCase()).decode(bodyBytes);
  const subject = decodeEncodedWords(headers.subject || '');
  const fromDecoded = decodeEncodedWords(headers.from || '');
  const fm = fromDecoded.match(/^\s*(?:"?([^"<]*?)"?\s*)?<([^>]+)>\s*$/);
  const name = fm ? (fm[1] || '').trim() : '';
  const address = fm ? fm[2].trim() : fromDecoded.trim();
  return { json: {
    id: gmailId, threadId: gmailId, labelIds: ['INBOX', 'UNREAD'], date: rfc822DateToIso(headers.date || ''),
    from: { value: [{ address, name }], text: name ? `${name} <${address}>` : address },
    to: { value: [{ address: 'owner@example.com', name: '' }], text: 'owner@example.com' },
    subject, text: body, html: '',
  } };
}
const X_ID = '18f3aabb00000001', Y_ID = '18f3aabb00000002';   // fictional Gmail ids (fixtures/mail_pinned.example.json)

// Schedule path: Schedule Trigger item (DESIGN §3.1)
const scheduleTrigger = () => ({ timestamp: '2026-09-23T09:00:00.000+09:00', 'Readable date': 'September 23rd 2026, 9:00:00 am',
  'Readable time': '9:00:00 am', 'Day of week': 'Wednesday', Year: '2026', Month: 'September', 'Day of month': '23',
  Hour: '09', Minute: '00', Second: '00', Timezone: 'Asia/Tokyo (UTC+09:00)' });

// ------------------------------------------------------------------------------------------------------------------
// the chain
// ------------------------------------------------------------------------------------------------------------------
// Runs Collect → Normalize → Match → Route → Build Notification. `intake` = the items that reach Collect Transactions
// (Parse Bank CSV / Parse Mail output, or the Config item on the schedule path).
function reconcile(label, cfgItems, intake, invoices, transactions) {
  const cfg = [cfgItems[0]];                            // $('Config').first()
  const collected = mustRun('collect_transactions.js', `${label} Collect Transactions`, { input: intake, nodes: { Config: cfg } });
  const normalized = mustRun('normalize_payer.js', `${label} Normalize Payer`,
    { input: transactions, nodes: { Config: cfg, 'Collect Transactions': collected, 'Read Invoices': invoices } });
  const matched = mustRun('match_invoices.js', `${label} Match Invoices`, { input: normalized, nodes: { Config: cfg } });
  // Route Match Results (Switch on _kind → outputs 0 / 1 / 2)
  const route = { invoice_update: [], txn_row: [], summary: [], other: [] };
  for (const it of matched) (route[it.json?._kind] || route.other).push(it);
  check(`${label} Route`, 'every Match Invoices item has a routable _kind (invoice_update / txn_row / summary)', route.other.length === 0, canon(route.other));
  check(`${label} Route summary`, 'exactly one summary item reaches Build Notification', route.summary.length === 1, `summary items: ${route.summary.length}`);
  const notification = route.summary.length === 1
    ? mustRun('build_notification.js', `${label} Build Notification`, { input: route.summary, nodes: { Config: cfg } }) : [];
  return { collected, normalized, matched, route, summary: route.summary[0]?.json, notification: notification[0]?.json ?? null, notificationItems: notification };
}
// Simulates Update Invoices / Upsert Transactions (Append or Update on invoice_id / txn_id; unspecified columns keep their value)
function applyToSheets(route, invoices, transactions) {
  const inv = invoices.map((i) => ({ json: { ...i.json } }));
  for (const u of route.invoice_update) {
    const { _kind, ...cols } = u.json;
    const row = inv.find((i) => i.json.invoice_id === cols.invoice_id);
    if (row) Object.assign(row.json, cols); else inv.push({ json: cols });
  }
  const txn = transactions.filter((t) => t.json && t.json.txn_id).map((t) => ({ json: { ...t.json } }));
  for (const r of route.txn_row) {
    const { _kind, ...cols } = r.json;
    const row = txn.find((t) => t.json.txn_id === cols.txn_id);
    if (row) Object.assign(row.json, cols); else txn.push({ json: cols });
  }
  return { invoices: inv, transactions: txn.length ? txn : EMPTY_SHEET };
}
const findInv = (route, id) => route.invoice_update.find((i) => i.json.invoice_id === id)?.json;
const findTxn = (route, id) => route.txn_row.find((i) => i.json.txn_id === id)?.json;
const lines = (text) => String(text).split('\n').filter((l) => l.trim() !== '');   // CASES §3: blank-line count is not asserted
const TXN_COLS = ['txn_id', 'source', 'txn_date', 'payer_name_raw', 'payer_name_norm', 'amount', 'memo', 'matched_invoice_ids', 'status', 'suggested_invoice_ids', 'imported_at'];
const INV_COLS = ['invoice_id', 'status', 'paid_amount', 'paid_date', 'matched_txn_ids', 'match_confidence', 'fee_deducted'];

const seedInvoices = sheetRows('invoices.seed.csv');
const seedTransactions = sheetRows('transactions.seed.csv');
check('seed', 'invoices.seed.csv = 20 rows, transactions.seed.csv = 1 row', seedInvoices.length === 20 && seedTransactions.length === 1);

// ==================================================================================================================
// A. Drive path — bank_A_sjis.csv against the seed (R01–R08, CASES §3)
// ==================================================================================================================
console.log('--- A: drive path, bank_A_sjis.csv, seed sheets ---');
const cfgA = [configItem(driveTrigger('bank_A_sjis.csv'), 'Watch Drive Folder')];
const parsedA = mustRun('parse_bank_csv.js', 'A Parse Bank CSV', { input: [downloadFileItem('bank_A_sjis.csv')], nodes: { Config: cfgA } });
const A = reconcile('A', cfgA, parsedA, seedInvoices, seedTransactions);

// R08 / R07 — decoding and withdrawal filtering
const rawA = ['振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ', '振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ', 'フリコミ　ヤマダ　タロウ', '振込 ｻﾄｳ ｹｲｺ', '振込 ｶ)ﾃｽﾄﾌﾞﾂｻﾝ', '振込 ｻﾝﾌﾟﾙｼｽﾃﾑ(ｶ',
  '振込 ｵｵﾊﾞ ﾏｻｵ', '振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ', '振込 ﾃｽﾄｹﾝｾﾂ(ｶ', '振込 ｶ)ｻﾝﾌﾟﾙﾌｰｽﾞﾄｳｷﾖｳ', '振込 ﾅｶﾑﾗ ｼﾞﾛｳ'];
const txnsA = parsedA.filter((i) => i.json._kind === 'txn');
eq('R08-a', 'Parse Bank CSV (Shift_JIS): 11 payer_name_raw values equal fixtures/README.md §4 (no U+FFFD)', txnsA.map((i) => i.json.payer_name_raw), rawA);
check('R08-b', 'no replacement character anywhere in the decoded rows', !JSON.stringify(parsedA).includes('�'));
eq('R07-a', 'file_stats.ignored_withdraw = 4 (rows 2, 7, 10, 15 are withdrawals)', parsedA.find((i) => i.json._kind === 'file_stats')?.json.ignored_withdraw, 4);
eq('R07-b', 'Parse Bank CSV emits 11 txns + 1 file_stats, no warnings', [txnsA.length, parsedA.filter((i) => i.json._kind === 'warning').length, parsedA.length], [11, 0, 12]);
eq('A-collect', 'Collect Transactions: source drive, 11 txns, file_name bank_A_sjis.csv, ignored_withdraw 4, warnings []',
  [A.collected[0].json.source, A.collected[0].json.txns.length, A.collected[0].json.file_name, A.collected[0].json.ignored_withdraw, A.collected[0].json.warnings],
  ['drive', 11, 'bank_A_sjis.csv', 4, []]);
eq('A-normalize', 'Normalize Payer: 11 txn_ids equal fixtures/README.md §4', A.normalized[0].json.txns.map((t) => t.txn_id), [
  '2026-09-01|33000|サンプルシヨウジ|', '2026-09-02|54780|テストコウギヨウ|', '2026-09-03|9800|ヤマダタロウ|', '2026-09-04|128000|サトウケイコ|',
  '2026-09-05|1234567|テストブツサン|', '2026-09-08|100000|サンプルシステム|', '2026-09-09|44000|オオバマサオ|', '2026-09-11|66000|ミホンシヨウカイ|',
  '2026-09-12|88000|テストケンセツ|', '2026-09-14|27500|サンプルフーズトウキヨウ|', '2026-09-15|5500|ナカムラジロウ|']);
eq('A-normalize-existing', 'Normalize Payer: existing = the 1 seed transaction (txn_id kept, payer_name_norm kept)',
  A.normalized[0].json.existing.map((r) => [r.txn_id, r.payer_name_norm, r.status]), [['2026-08-28|66000|ミホンシヨウカイ|', 'ミホンシヨウカイ', 'matched']]);

// summary (fixtures README §4)
const sA = A.summary || {};
eq('A-summary', 'summary n=11 a=4 b=3 c=4 ignored_withdraw=4 skipped_existing=0 skipped_duplicate_in_batch=0 rematched=0 warnings=[] source=drive date=2026-09-23',
  [sA.n, sA.a, sA.b, sA.c, sA.ignored_withdraw, sA.skipped_existing, sA.skipped_duplicate_in_batch, sA.rematched, sA.warnings, sA.source, sA.date],
  [11, 4, 3, 4, 4, 0, 0, 0, [], 'drive', TODAY]);
eq('A-route-counts', 'Route Match Results: 8 invoice_update (output 0), 11 txn_row (output 1), 1 summary (output 2)',
  [A.route.invoice_update.length, A.route.txn_row.length, A.route.summary.length], [8, 11, 1]);
check('A-columns', 'every invoice_update carries exactly the 7 invoices columns and every txn_row exactly the 11 transactions columns (plus _kind)',
  A.route.invoice_update.every((i) => canon(Object.keys(i.json).filter((k) => k !== '_kind').sort()) === canon([...INV_COLS].sort()))
  && A.route.txn_row.every((i) => canon(Object.keys(i.json).filter((k) => k !== '_kind').sort()) === canon([...TXN_COLS].sort())));
check('A-imported_at', 'txn_row.imported_at is ISO 8601 with +09:00 offset (T09 / D30)', A.route.txn_row.every((i) => /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00$/.test(i.json.imported_at)), canon(A.route.txn_row.map((i) => i.json.imported_at)));

// R01
const invUpd = (id, status, paid_amount, paid_date, matched_txn_ids, match_confidence, fee_deducted) =>
  ({ _kind: 'invoice_update', invoice_id: id, status, paid_amount, paid_date, matched_txn_ids, match_confidence, fee_deducted });
eq('R01-a', 'inv[INV-2026-001] = paid / auto / 33000 / fee 0 / 2026-09-01 / matched_txn_ids', findInv(A.route, 'INV-2026-001'),
  invUpd('INV-2026-001', 'paid', 33000, '2026-09-01', '2026-09-01|33000|サンプルシヨウジ|', 'auto', 0));
const t1 = findTxn(A.route, '2026-09-01|33000|サンプルシヨウジ|');
eq('R01-b', 'txn[2026-09-01|33000|サンプルシヨウジ|] = bank_csv / matched / INV-2026-001 / suggested ""', t1 && { ...t1, imported_at: '<checked>' },
  { _kind: 'txn_row', txn_id: '2026-09-01|33000|サンプルシヨウジ|', source: 'bank_csv', txn_date: '2026-09-01', payer_name_raw: '振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ',
    payer_name_norm: 'サンプルシヨウジ', amount: 33000, memo: '', matched_invoice_ids: 'INV-2026-001', status: 'matched', suggested_invoice_ids: '', imported_at: '<checked>' });
eq('R01-c', 'inv[INV-2026-003] = paid / auto / 9800 (full-width remitter)', findInv(A.route, 'INV-2026-003'),
  invUpd('INV-2026-003', 'paid', 9800, '2026-09-03', '2026-09-03|9800|ヤマダタロウ|', 'auto', 0));
eq('R01-d', 'inv[INV-2026-012] = paid / auto / 27500 (containment: remitter ⊃ alias サンプルフーズ)', findInv(A.route, 'INV-2026-012'),
  invUpd('INV-2026-012', 'paid', 27500, '2026-09-14', '2026-09-14|27500|サンプルフーズトウキヨウ|', 'auto', 0));
eq('R01-e', 'INV-2026-017 (same customer as INV-001, different amount) is not updated', findInv(A.route, 'INV-2026-017'), undefined);
// R02
eq('R02-a', 'inv[INV-2026-004] = paid / amount_only / 128000 / fee 0 / 2026-09-04', findInv(A.route, 'INV-2026-004'),
  invUpd('INV-2026-004', 'paid', 128000, '2026-09-04', '2026-09-04|128000|サトウケイコ|', 'amount_only', 0));
eq('R02-b', 'txn[2026-09-04|128000|サトウケイコ|] = matched / INV-2026-004 / payer_name_norm サトウケイコ',
  (({ status, matched_invoice_ids, payer_name_norm, suggested_invoice_ids }) => ({ status, matched_invoice_ids, payer_name_norm, suggested_invoice_ids }))(findTxn(A.route, '2026-09-04|128000|サトウケイコ|') || {}),
  { status: 'matched', matched_invoice_ids: 'INV-2026-004', payer_name_norm: 'サトウケイコ', suggested_invoice_ids: '' });
// R03
eq('R03-a', 'inv[INV-2026-002] = paid / fee_deducted / 54780 / fee 220 / 2026-09-02', findInv(A.route, 'INV-2026-002'),
  invUpd('INV-2026-002', 'paid', 54780, '2026-09-02', '2026-09-02|54780|テストコウギヨウ|', 'fee_deducted', 220));
eq('R03-b', 'txn[2026-09-02|54780|テストコウギヨウ|] = matched / INV-2026-002',
  (({ status, matched_invoice_ids }) => ({ status, matched_invoice_ids }))(findTxn(A.route, '2026-09-02|54780|テストコウギヨウ|') || {}), { status: 'matched', matched_invoice_ids: 'INV-2026-002' });
// R04
eq('R04-a', 'inv[INV-2026-005] = paid / combined / 700000 (its own remaining) / 2026-09-05', findInv(A.route, 'INV-2026-005'),
  invUpd('INV-2026-005', 'paid', 700000, '2026-09-05', '2026-09-05|1234567|テストブツサン|', 'combined', 0));
eq('R04-b', 'inv[INV-2026-006] = paid / combined / 534567 / same txn_id', findInv(A.route, 'INV-2026-006'),
  invUpd('INV-2026-006', 'paid', 534567, '2026-09-05', '2026-09-05|1234567|テストブツサン|', 'combined', 0));
eq('R04-c', 'txn[2026-09-05|1234567|テストブツサン|] = matched / "INV-2026-005,INV-2026-006" (one row, comma-separated)',
  (({ status, matched_invoice_ids }) => ({ status, matched_invoice_ids }))(findTxn(A.route, '2026-09-05|1234567|テストブツサン|') || {}), { status: 'matched', matched_invoice_ids: 'INV-2026-005,INV-2026-006' });
// R05
eq('R05-a', 'inv[INV-2026-007] = partial / auto / 100000 / fee 0 / 2026-09-08', findInv(A.route, 'INV-2026-007'),
  invUpd('INV-2026-007', 'partial', 100000, '2026-09-08', '2026-09-08|100000|サンプルシステム|', 'auto', 0));
eq('R05-b', 'txn[2026-09-08|100000|サンプルシステム|] = matched / INV-2026-007',
  (({ status, matched_invoice_ids }) => ({ status, matched_invoice_ids }))(findTxn(A.route, '2026-09-08|100000|サンプルシステム|') || {}), { status: 'matched', matched_invoice_ids: 'INV-2026-007' });
// R06
eq('R06-a', 'INV-2026-008 / INV-2026-009 receive no invoice_update', [findInv(A.route, 'INV-2026-008'), findInv(A.route, 'INV-2026-009')], [undefined, undefined]);
eq('R06-b', 'txn[2026-09-09|44000|オオバマサオ|] = ambiguous / matched "" / suggested "INV-2026-008,INV-2026-009" (due_date order)',
  (({ status, matched_invoice_ids, suggested_invoice_ids }) => ({ status, matched_invoice_ids, suggested_invoice_ids }))(findTxn(A.route, '2026-09-09|44000|オオバマサオ|') || {}),
  { status: 'ambiguous', matched_invoice_ids: '', suggested_invoice_ids: 'INV-2026-008,INV-2026-009' });
// rule-5 traps (README §4 rows 11, 12, 14)
eq('A-trap-paid', 'A-11 (same name/amount as paid INV-010) = unmatched, suggested INV-2026-015,INV-2026-017; INV-010 untouched',
  [(({ status, suggested_invoice_ids }) => ({ status, suggested_invoice_ids }))(findTxn(A.route, '2026-09-11|66000|ミホンシヨウカイ|') || {}), findInv(A.route, 'INV-2026-010')],
  [{ status: 'unmatched', suggested_invoice_ids: 'INV-2026-015,INV-2026-017' }, undefined]);
eq('A-trap-cancelled', 'A-12 (same name/amount as cancelled INV-011) = unmatched, suggested ""; INV-011 untouched',
  [(({ status, suggested_invoice_ids }) => ({ status, suggested_invoice_ids }))(findTxn(A.route, '2026-09-12|88000|テストケンセツ|') || {}), findInv(A.route, 'INV-2026-011')],
  [{ status: 'unmatched', suggested_invoice_ids: '' }, undefined]);
eq('A-trap-none', 'A-14 = unmatched, suggested INV-2026-014 (weak similarity only)',
  (({ status, suggested_invoice_ids }) => ({ status, suggested_invoice_ids }))(findTxn(A.route, '2026-09-15|5500|ナカムラジロウ|') || {}), { status: 'unmatched', suggested_invoice_ids: 'INV-2026-014' });

// notification (CASES §3 full text; 付録A title format)
const nA = A.notification || {};
eq('N-title', 'title = 【入金消込 2026-09-23】処理 11件｜自動消込 4｜要確認 3｜未消込 4 (付録A format)', nA.title, '【入金消込 2026-09-23】処理 11件｜自動消込 4｜要確認 3｜未消込 4');
check('N-title-format', 'title matches the 付録A pattern 【入金消込 {date}】処理 {n}件｜自動消込 {a}｜要確認 {b}｜未消込 {c}',
  /^【入金消込 \d{4}-\d{2}-\d{2}】処理 \d+件｜自動消込 \d+｜要確認 \d+｜未消込 \d+$/.test(nA.title || ''), nA.title);
const expectedBodyA = [
  '【入金消込 2026-09-23】処理 11件｜自動消込 4｜要確認 3｜未消込 4',
  '■ 要確認（金額のみ一致・手数料差引・合算で自動消込した分）',
  '・2026-09-02 振込 ﾃｽﾄｺｳｷﾞﾖｳ(ﾕ ¥54,780 → INV-2026-002 （手数料 ¥220 差引）',
  '・2026-09-04 振込 ｻﾄｳ ｹｲｺ ¥128,000 → INV-2026-004 （金額のみ一致・要確認）',
  '・2026-09-05 振込 ｶ)ﾃｽﾄﾌﾞﾂｻﾝ ¥1,234,567 → INV-2026-005, INV-2026-006 （合算）',
  '■ 候補複数（自動確定せず。候補から選んでください）',
  '・2026-09-09 振込 ｵｵﾊﾞ ﾏｻｵ ¥44,000 → 候補: INV-2026-008(¥44,000), INV-2026-009(¥44,000)',
  '■ 未消込（該当請求なし）',
  '・2026-09-11 振込 ｶ)ﾐﾎﾝｼﾖｳｶｲ ¥66,000 → 候補: INV-2026-015(¥57,200), INV-2026-017(¥49,500)',
  '・2026-09-12 振込 ﾃｽﾄｹﾝｾﾂ(ｶ ¥88,000 → 候補: —',
  '・2026-09-15 振込 ﾅｶﾑﾗ ｼﾞﾛｳ ¥5,500 → 候補: INV-2026-014(¥15,400)',
  '■ 自動消込',
  '・2026-09-01 振込 ｶ)ｻﾝﾌﾟﾙｼﾖｳｼﾞ ¥33,000 → INV-2026-001',
  '・2026-09-03 フリコミ　ヤマダ　タロウ ¥9,800 → INV-2026-003',
  '・2026-09-08 振込 ｻﾝﾌﾟﾙｼｽﾃﾑ(ｶ ¥100,000 → INV-2026-007 （一部入金・残 ¥150,000）',
  '・2026-09-14 振込 ｶ)ｻﾝﾌﾟﾙﾌｰｽﾞﾄｳｷﾖｳ ¥27,500 → INV-2026-012',
];
eq('N-body', 'body_text (non-blank lines) equals tests/CASES.md §3 verbatim', lines(nA.body_text || ''), expectedBodyA);
check('N-body-blank', 'title and each section are separated by exactly one blank line (T08)', (nA.body_text || '').split('\n\n').length === 5, JSON.stringify(nA.body_text));
eq('N-keys', 'Build Notification emits title / body_text / slack_blocks / line_text / chatwork_text', Object.keys(nA).sort(), ['body_text', 'chatwork_text', 'line_text', 'slack_blocks', 'title']);
eq('N-slack', 'slack_blocks = header(title) + 4 sections (needs review / ambiguous / unmatched / auto)',
  [nA.slack_blocks?.[0]?.type, nA.slack_blocks?.[0]?.text?.text, nA.slack_blocks?.length, nA.slack_blocks?.slice(1).map((b) => b.text.text.split('\n')[0])],
  ['header', nA.title, 5, [expectedBodyA[1], expectedBodyA[5], expectedBodyA[7], expectedBodyA[11]]]);
eq('N-line-chatwork', 'line_text and chatwork_text equal body_text (short body)', [nA.line_text, nA.chatwork_text], [nA.body_text, nA.body_text]);

// ==================================================================================================================
// R09 — the same CSV a second time, sheets updated by pass 1 → everything skipped, no writes, no_transactions notice
// ==================================================================================================================
console.log('--- R09: drive path, bank_A_sjis.csv again after pass 1 was written to the sheets ---');
const sheetsAfterA = applyToSheets(A.route, seedInvoices, seedTransactions);
eq('R09-setup', 'pass-1 writes applied: transactions sheet = 1 seed + 11 new rows without _kind', [sheetsAfterA.transactions.length, sheetsAfterA.transactions.some((t) => '_kind' in t.json)], [12, false]);
const parsedA2 = mustRun('parse_bank_csv.js', 'R09 Parse Bank CSV', { input: [downloadFileItem('bank_A_sjis.csv')], nodes: { Config: cfgA } });
eq('R09-parse', 'Parse Bank CSV output is identical on the second pass', parsedA2, parsedA);
const A2 = reconcile('R09', cfgA, parsedA2, sheetsAfterA.invoices, sheetsAfterA.transactions);
const s2 = A2.summary || {};
eq('R09-a', 'Match Invoices emits the summary only: n=0 a=0 b=0 c=0 skipped_existing=11 skipped_duplicate_in_batch=0',
  [A2.matched.length, A2.route.invoice_update.length, A2.route.txn_row.length, s2.n, s2.a, s2.b, s2.c, s2.skipped_existing, s2.skipped_duplicate_in_batch],
  [1, 0, 0, 0, 0, 0, 0, 11, 0]);
eq('R09-b', 'notification title = 【入金消込 2026-09-23】新規の入金はありませんでした, body contains （処理済みのため skip：11 件）',
  [A2.notification?.title, lines(A2.notification?.body_text || '')], ['【入金消込 2026-09-23】新規の入金はありませんでした', ['【入金消込 2026-09-23】新規の入金はありませんでした', '（処理済みのため skip：11 件）']]);
const sheetsAfterA2 = applyToSheets(A2.route, sheetsAfterA.invoices, sheetsAfterA.transactions);
eq('R09-c', 'sheet state is unchanged by the second pass (zero diff)', sheetsAfterA2, sheetsAfterA);

// ==================================================================================================================
// R14-a — empty transactions sheet ({} from Always Output Data) → same result as pass 1
// ==================================================================================================================
console.log('--- R14-a: drive path, bank_A_sjis.csv, empty transactions sheet ---');
const A14 = reconcile('R14a', cfgA, parsedA, seedInvoices, EMPTY_SHEET);
eq('R14a-a', 'Normalize Payer: existing = [] (the {} row is skipped)', A14.normalized[0].json.existing, []);
eq('R14a-b', 'Match Invoices output equals the seed run (skipped_existing=0)', A14.matched, A.matched);
eq('R14a-c', 'notification equals the seed run', A14.notification, A.notification);

// ==================================================================================================================
// B. Drive path — bank_B_utf8bom.csv with the B CSV_MAPPING (R13, R08 BOM, R07)
// ==================================================================================================================
console.log('--- B: drive path, bank_B_utf8bom.csv, seed sheets ---');
const cfgB = [configItem(driveTrigger('bank_B_utf8bom.csv'), 'Watch Drive Folder', { csv: 'bank_B_utf8bom.csv' })];
const parsedB = mustRun('parse_bank_csv.js', 'B Parse Bank CSV', { input: [downloadFileItem('bank_B_utf8bom.csv')], nodes: { Config: cfgB } });
const txnsB = parsedB.filter((i) => i.json._kind === 'txn');
eq('R08-c', 'UTF-8 BOM: header 取引日 resolved (no "CSV column not found"), 5 deposits with raw names of README §5, dates yyyy-MM-dd',
  txnsB.map((i) => [i.json.txn_date, i.json.payer_name_raw, i.json.amount]),
  [['2026-09-17', '0123 カ)ダミーカコウ', 41800], ['2026-09-18', 'ふりこみ　すずき　いちろう', 15400], ['2026-09-19', 'ユ)ミホンプランニング', 57200],
   ['2026-09-21', '0045 タカハシ ミキ', 12100], ['2026-09-22', 'フリコミ ワタナベ ケン', 7700]]);
eq('R07-c', 'B: ignored_withdraw = 3', parsedB.find((i) => i.json._kind === 'file_stats')?.json.ignored_withdraw, 3);
const B = reconcile('B', cfgB, parsedB, seedInvoices, seedTransactions);
eq('R13-a', 'payer_name_norm: ダミーカコウ / スズキイチロウ / ミホンプランニング / タカハシミキ / ワタナベケン',
  B.normalized[0].json.txns.map((t) => t.payer_name_norm), ['ダミーカコウ', 'スズキイチロウ', 'ミホンプランニング', 'タカハシミキ', 'ワタナベケン']);
const sB = B.summary || {};
eq('R13-b', 'summary n=5 a=4 b=0 c=1 ignored_withdraw=3 warnings=[]', [sB.n, sB.a, sB.b, sB.c, sB.ignored_withdraw, sB.warnings], [5, 4, 0, 1, 3, []]);
eq('R13-c', 'inv[INV-2026-013] = paid / auto / 41800 / 2026-09-17 (leading digits stripped)', findInv(B.route, 'INV-2026-013'),
  invUpd('INV-2026-013', 'paid', 41800, '2026-09-17', '2026-09-17|41800|ダミーカコウ|', 'auto', 0));
eq('R13-d', 'inv[INV-2026-014] = paid / auto / 15400 / 2026-09-18 (hiragana → katakana)', findInv(B.route, 'INV-2026-014'),
  invUpd('INV-2026-014', 'paid', 15400, '2026-09-18', '2026-09-18|15400|スズキイチロウ|', 'auto', 0));
eq('R13-e', 'inv[INV-2026-015] = paid / auto / 57200 / 2026-09-19 (ユ) stripped)', findInv(B.route, 'INV-2026-015'),
  invUpd('INV-2026-015', 'paid', 57200, '2026-09-19', '2026-09-19|57200|ミホンプランニング|', 'auto', 0));
eq('R13-f', 'inv[INV-2026-016] = paid / auto / 12100 / 2026-09-21', findInv(B.route, 'INV-2026-016'),
  invUpd('INV-2026-016', 'paid', 12100, '2026-09-21', '2026-09-21|12100|タカハシミキ|', 'auto', 0));
eq('R13-g', 'txn[2026-09-22|7700|ワタナベケン|] = unmatched / suggested ""; 4 invoice_update, 5 txn_row',
  [(({ status, suggested_invoice_ids, matched_invoice_ids }) => ({ status, suggested_invoice_ids, matched_invoice_ids }))(findTxn(B.route, '2026-09-22|7700|ワタナベケン|') || {}), B.route.invoice_update.length, B.route.txn_row.length],
  [{ status: 'unmatched', suggested_invoice_ids: '', matched_invoice_ids: '' }, 4, 5]);
eq('R13-h', 'notification: title 処理 5件｜自動消込 4｜要確認 0｜未消込 1, unmatched line, 4 auto lines', lines(B.notification?.body_text || ''), [
  '【入金消込 2026-09-23】処理 5件｜自動消込 4｜要確認 0｜未消込 1',
  '■ 未消込（該当請求なし）',
  '・2026-09-22 フリコミ ワタナベ ケン ¥7,700 → 候補: —',
  '■ 自動消込',
  '・2026-09-17 0123 カ)ダミーカコウ ¥41,800 → INV-2026-013',
  '・2026-09-18 ふりこみ　すずき　いちろう ¥15,400 → INV-2026-014',
  '・2026-09-19 ユ)ミホンプランニング ¥57,200 → INV-2026-015',
  '・2026-09-21 0045 タカハシ ミキ ¥12,100 → INV-2026-016',
]);

// ==================================================================================================================
// M. Gmail path — mail_bankX.eml + mail_bankY.eml (R10, R09-b)
// ==================================================================================================================
console.log('--- M: gmail path, mail_bankX.eml + mail_bankY.eml, seed sheets ---');
const mailX = gmailItemFromEml('mail_bankX.eml', X_ID);
const mailY = gmailItemFromEml('mail_bankY.eml', Y_ID);
const pinned = readJson(path.join(FX, 'mail_pinned.example.json')).items;
// The .eml bodies keep their RFC 822 CRLF line endings; mail_pinned.example.json stores the decoded body with LF. Both shapes are
// fed to Parse Mail below (a live Gmail Trigger may deliver either), so the comparison here normalizes line endings only.
eq('M-eml', '.eml-derived Gmail items equal fixtures/mail_pinned.example.json (subject / from / date / text modulo CRLF→LF)',
  [mailX, mailY].map((m) => [m.json.subject, m.json.from, m.json.date, m.json.text.replace(/\r\n/g, '\n')]),
  pinned.map((m) => [m.json.subject, m.json.from, m.json.date, m.json.text]));
// Gmail Trigger emits one item per mail; Config (include all input fields) yields one merged item per mail; Route by Source → Parse Mail
const cfgM = [mailX, mailY].map((m) => configItem(m.json, 'Watch Gmail Inbox'));
const parsedM = mustRun('parse_mail.js', 'M Parse Mail', { input: cfgM, nodes: { Config: cfgM } });
const cfgMpinned = pinned.map((m) => configItem(m.json, 'Watch Gmail Inbox'));
const parsedMpinned = mustRun('parse_mail.js', 'M Parse Mail (pinned LF bodies)', { input: cfgMpinned, nodes: { Config: cfgMpinned } });
eq('M-crlf', 'Parse Mail output is identical for CRLF (.eml) and LF (pinned example) bodies', parsedMpinned, parsedM);
eq('R10-a', 'Parse Mail: X → 104500 / カ)ダミーデンキ / 2026-09-17 (bankX), Y → 19800 / ササキ ハナコ / 2026-09-18 from the body (bankY)',
  parsedM.map((i) => i.json), [
    { _kind: 'txn', source: 'gmail', txn_date: '2026-09-17', payer_name_raw: 'カ)ダミーデンキ', amount: 104500, memo: `【サンプル銀行】ご入金のお知らせ (gmail:${X_ID})`, _message_id: X_ID, _parser: 'bankX' },
    { _kind: 'txn', source: 'gmail', txn_date: '2026-09-18', payer_name_raw: 'ササキ ハナコ', amount: 19800, memo: `Deposit Notification - Sample Bank (gmail:${Y_ID})`, _message_id: Y_ID, _parser: 'bankY' },
  ]);
eq('R10-paired', 'Parse Mail pairedItem 0 / 1', parsedM.map((i) => i.pairedItem), [{ item: 0 }, { item: 1 }]);
const M = reconcile('M', cfgM, parsedM, seedInvoices, seedTransactions);
eq('M-collect', 'Collect Transactions: source gmail, 2 txns, warnings [], ignored_withdraw 0, file_name ""',
  [M.collected[0].json.source, M.collected[0].json.txns.length, M.collected[0].json.warnings, M.collected[0].json.ignored_withdraw, M.collected[0].json.file_name], ['gmail', 2, [], 0, '']);
eq('R10-b', 'inv[INV-2026-018] = paid / auto / 104500 / 2026-09-17 / txn_id with the NFKC-lowercased subject memo', findInv(M.route, 'INV-2026-018'),
  invUpd('INV-2026-018', 'paid', 104500, '2026-09-17', `2026-09-17|104500|ダミーデンキ|【サンプル銀行】ご入金のお知らせ(gmail:${X_ID})`, 'auto', 0));
eq('R10-c', 'inv[INV-2026-019] = paid / auto / 19800 / 2026-09-18', findInv(M.route, 'INV-2026-019'),
  invUpd('INV-2026-019', 'paid', 19800, '2026-09-18', `2026-09-18|19800|ササキハナコ|depositnotification-samplebank(gmail:${Y_ID})`, 'auto', 0));
eq('R10-d', 'transactions: 2 rows, source gmail, memo = subject + " (gmail:<id>)", status matched',
  M.route.txn_row.map((i) => [i.json.txn_id, i.json.source, i.json.memo, i.json.status, i.json.matched_invoice_ids, i.json.payer_name_norm]), [
    [`2026-09-17|104500|ダミーデンキ|【サンプル銀行】ご入金のお知らせ(gmail:${X_ID})`, 'gmail', `【サンプル銀行】ご入金のお知らせ (gmail:${X_ID})`, 'matched', 'INV-2026-018', 'ダミーデンキ'],
    [`2026-09-18|19800|ササキハナコ|depositnotification-samplebank(gmail:${Y_ID})`, 'gmail', `Deposit Notification - Sample Bank (gmail:${Y_ID})`, 'matched', 'INV-2026-019', 'ササキハナコ'],
  ]);
const sM = M.summary || {};
eq('R10-e', 'summary n=2 a=2 b=0 c=0 warnings=[] source=gmail', [sM.n, sM.a, sM.b, sM.c, sM.warnings, sM.source], [2, 2, 0, 0, [], 'gmail']);
eq('R10-f', 'notification: 処理 2件｜自動消込 2｜要確認 0｜未消込 0 + 2 auto lines', lines(M.notification?.body_text || ''), [
  '【入金消込 2026-09-23】処理 2件｜自動消込 2｜要確認 0｜未消込 0',
  '■ 自動消込',
  '・2026-09-17 カ)ダミーデンキ ¥104,500 → INV-2026-018',
  '・2026-09-18 ササキ ハナコ ¥19,800 → INV-2026-019',
]);
// R09-b: the same two mails again
const sheetsAfterM = applyToSheets(M.route, seedInvoices, seedTransactions);
const M2 = reconcile('R09b', cfgM, parsedM, sheetsAfterM.invoices, sheetsAfterM.transactions);
eq('R09b', 'gmail second pass: summary only, skipped_existing=2, no_transactions title', [M2.matched.length, M2.summary?.skipped_existing, M2.notification?.title],
  [1, 2, '【入金消込 2026-09-23】新規の入金はありませんでした']);

// ==================================================================================================================
// S. Schedule path — no new txns, nothing to re-match → summary only, Build Notification returns [] (R19)
// ==================================================================================================================
console.log('--- S: schedule path, seed sheets ---');
const cfgS = [configItem(scheduleTrigger(), 'Run Daily Rematch')];
const S = reconcile('S', cfgS, cfgS, seedInvoices, seedTransactions);   // Route by Source "schedule" → Collect Transactions receives the Config item
eq('S-collect', 'Collect Transactions: { source schedule, txns [], warnings [] }', [S.collected[0].json.source, S.collected[0].json.txns, S.collected[0].json.warnings], ['schedule', [], []]);
eq('R19', 'schedule with no change: Match emits the summary only (rematched 0) and Build Notification returns []',
  [S.matched.length, S.summary?.rematched, S.route.txn_row.length, S.notificationItems], [1, 0, 0, []]);

// ==================================================================================================================
// C. Check Notification Results — Notify success / error-output items built from the A notification (R11-b shapes)
// ==================================================================================================================
console.log('--- C: Check Notification Results over simulated Notify outputs ---');
const notif = A.notification;
const okItem = () => ({ json: { ok: true, channel: 'C_FIXTURE', ts: '0.0' } });                                   // Notify success output (API response)
const errString = (msg) => ({ json: { ...notif, error: msg } });                                                    // Slack / Gmail error output (string)
const errObject = (msg) => ({ json: { ...notif, error: { message: msg, name: 'Error', stack: '' }, details: {} } });   // HTTP Request v4.5 error output (object)
const C1 = runNode('check_notification_results.js', 'C all ok', { input: [okItem()], nodes: { Config: cfgA } });
eq('C-1', 'NOTIFY_CHANNELS=["slack"], Slack ok → { attempted 1, ok 1, failed 0, errors [] }', C1.items?.[0]?.json, { channels_attempted: 1, channels_ok: 1, channels_failed: 0, errors: [] });
const C2 = runNode('check_notification_results.js', 'C partial', { input: [okItem(), errObject('connect ECONNREFUSED 127.0.0.1:9'), errString('channel_not_found')], nodes: { Config: cfgA } });
eq('C-2', 'partial failure (1 ok, HTTP object error, Slack string error) → run succeeds with both messages', C2.items?.[0]?.json,
  { channels_attempted: 3, channels_ok: 1, channels_failed: 2, errors: ['connect ECONNREFUSED 127.0.0.1:9', 'channel_not_found'] });
const C3 = runNode('check_notification_results.js', 'C all failed', { input: [errString('channel_not_found'), errObject('connect ECONNREFUSED 127.0.0.1:9')], nodes: { Config: cfgA } });
check('C-3', 'all channels failed → throws "All notification channels failed (2): …" (→ Error Workflow, D17)',
  !!C3.error && C3.error.includes('All notification channels failed (2): channel_not_found / connect ECONNREFUSED 127.0.0.1:9'), C3.error || canon(C3.items));
const passThrough = () => ({ json: { ...notif } });                                                                // DISABLED Notify node: input passed through unchanged (F2 / D34)
const C4 = runNode('check_notification_results.js', 'C pass-through + ok', { input: [passThrough(), okItem()], nodes: { Config: cfgA } });
eq('C-4', 'a disabled Notify node passes the payload through → counted as failed, run succeeds (D34)', C4.items?.[0]?.json,
  { channels_attempted: 2, channels_ok: 1, channels_failed: 1, errors: ['notify node disabled or not executed (payload passed through)'] });
const C5 = runNode('check_notification_results.js', 'C pass-through only', { input: [passThrough()], nodes: { Config: cfgA } });
check('C-5', 'only a passed-through payload → throws "All notification channels failed (1): notify node disabled …" (D34)',
  !!C5.error && C5.error.includes('All notification channels failed (1): notify node disabled or not executed (payload passed through)'), C5.error || canon(C5.items));

// ==================================================================================================================
console.log(`integration: ${pass} passed, ${fail} failed (${runNo} node runs, files in ${TMP})`);
if (!KEEP && fail === 0 && !TMP_BASE) fs.rmSync(TMP, { recursive: true, force: true });
process.exit(fail === 0 && pass > 0 ? 0 : 1);
