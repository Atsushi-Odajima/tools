// Parse Bank CSV — n8n Code node (JavaScript, Mode: Run Once for All Items). No require().
// Source of truth: templates/01-bank-reconciliation/code/parse_bank_csv.js; workflow.json embeds this text verbatim
// (ASSUMPTIONS A15). Logic: DESIGN.md §6.2 + §6.5. Input: the items from "Download File" (one per file the Drive
// trigger emitted — several when more than one CSV lands in the folder within one poll, D31), each with binary.data
// holding a bank CSV. Output per input item i (pairedItem.item = i): pre-txn items { _kind: 'txn' } (no
// payer_name_norm / txn_id yet — "Normalize Payer" owns those), { _kind: 'warning', type: 'bad_date' } for rows whose
// date cannot be read, and one { _kind: 'file_stats' } item. Withdrawal / empty / zero deposit rows are ignored (R07).
// Shift_JIS is decoded here with TextDecoder because Extract From File has no shift_jis option (ASSUMPTIONS A6).
// A file whose source mimeType is a Google Sheet (Drive converted the upload) is exported by Download File as UTF-8 CSV
// without BOM, so it is decoded as UTF-8 regardless of CSV_MAPPING.encoding (D22).

// ---- shared helpers: toInt / num / str — identical text in every Code node (DESIGN §6.1) ----
// 数値化：全角→半角、カンマ・¥・円・空白を除去して整数（円）。失敗は toInt() = null / num() = 0
const toInt = (v) => {
  if (v === null || v === undefined) return null;
  if (typeof v === 'number') return Number.isFinite(v) ? Math.trunc(v) : null;
  const s = String(v).normalize('NFKC').replace(/[,\s¥￥円]/g, '');
  if (!/^-?\d+(\.\d+)?$/.test(s)) return null;
  return parseInt(s, 10);
};
const num = (v) => toInt(v) ?? 0;
const str = (v) => (v === null || v === undefined) ? '' : String(v).trim();
// ---- end shared helpers ----

// ---- shared: normalizeDate — identical text in Parse Bank CSV and Parse Mail (DESIGN §6.1 / §6.5) ----
// 受け付ける形式：yyyy/MM/dd, yyyyMMdd, yyyy-MM-dd（仕様）＋ yyyy.MM.dd / yyyy年M月d日 / 区切りありの非ゼロ埋め
// format が 'auto' 以外なら Luxon の fromFormat で厳密に解釈する。返り値は 'yyyy-MM-dd' か null（2026/02/30 等）
function normalizeDate(value, format, tz) {
  const s = str(value).normalize('NFKC');
  if (!s) return null;
  let y, m, d;
  if (format && format !== 'auto') {
    const dt = DateTime.fromFormat(s, format, { zone: tz });           // 明示指定は厳密に
    return dt.isValid ? dt.toFormat('yyyy-MM-dd') : null;
  }
  let mt = s.match(/^(\d{4})(\d{2})(\d{2})$/);                          // yyyyMMdd
  if (!mt) mt = s.match(/^(\d{4})[\/\-.年](\d{1,2})[\/\-.月](\d{1,2})日?/); // yyyy/M/d, yyyy-MM-dd, yyyy.M.d, yyyy年M月d日（末尾に時刻があっても可）
  if (!mt) return null;
  [y, m, d] = [Number(mt[1]), Number(mt[2]), Number(mt[3])];
  const dt = DateTime.fromObject({ year: y, month: m, day: d }, { zone: tz });
  return dt.isValid ? dt.toFormat('yyyy-MM-dd') : null;                 // 2026/02/30 等は null
}
// ---- end shared normalizeDate ----

// ---- バイナリ → 文字列（A6：Extract From File は使わない）----
function decodeCsvBuffer(buf, encoding) {
  // UTF-8 BOM は設定に関わらず UTF-8（fixture B）
  if (buf.length >= 3 && buf[0] === 0xef && buf[1] === 0xbb && buf[2] === 0xbf) {
    return new TextDecoder('utf-8').decode(buf.subarray(3));
  }
  const enc = str(encoding || 'shift_jis').toLowerCase();
  if (enc === 'auto') {
    try { return new TextDecoder('utf-8', { fatal: true }).decode(buf); }   // 不正な UTF-8 なら例外
    catch (e) { return new TextDecoder('shift_jis').decode(buf); }
  }
  return new TextDecoder(enc).decode(buf);   // 'shift_jis' / 'utf-8' / 'euc-jp'。未対応名は RangeError → 実行失敗（意図的）
}

// ---- RFC 4180 風の CSV パース（引用符内のカンマ・改行・"" に対応）----
function parseCsvText(text) {
  const rows = []; let row = []; let field = ''; let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else { inQuotes = false; } }
      else { field += c; }
    } else if (c === '"') { inQuotes = true; }
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\r') { /* CRLF の \r は捨てる */ }
    else if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
    else { field += c; }
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  return rows.filter((r) => r.some((f) => f.trim() !== ''));   // 空行除去
}

// ---- 列対応・出金除外・pre-txn 生成 ----
// rows: string[][]（parseCsvText の出力）。payer_name_norm / txn_id は付けない（Normalize Payer の責務）
function parseBankCsv(rows, m, ctx) {
  const skip = num(m.skip_rows);
  const nk = (s) => str(s).normalize('NFKC');
  const body = rows.slice(skip);
  if (!body.length) throw new Error(`CSV has no header row after skip_rows=${skip}`);
  const header = body[0].map(nk);
  const dataRows = body.slice(1).map((r) => Object.fromEntries(header.map((h, i) => [h, r[i] ?? ''])));
  const col = (name, required) => {
    const key = header.find((h) => h === nk(name));
    if (!key && required) throw new Error(`CSV column not found: "${name}". header = ${header.join(' | ')}`);
    return key || null;
  };
  const dateKey = col(m.date_col, true), payerKey = col(m.payer_col, true), depKey = col(m.deposit_col, true);
  const memoKey = m.memo_col ? col(m.memo_col, false) : null;   // withdraw_col は判定に使わない（deposit が空/0 なら無視）

  const txns = []; const warnings = []; let ignored = 0;
  dataRows.forEach((r, idx) => {
    const rowNo = skip + 2 + idx;                        // 1 始まりの物理行番号（見出し = skip+1。空行は数えない）
    const deposit = toInt(r[depKey]);
    if (!(deposit > 0)) { ignored++; return; }           // R07：出金行・空行・小計行を無視
    const txn_date = normalizeDate(r[dateKey], m.date_format, ctx.tz);
    if (!txn_date) { warnings.push({ type: 'bad_date', row: rowNo, value: str(r[dateKey]) }); return; }
    txns.push({ _kind: 'txn', source: 'bank_csv', txn_date, payer_name_raw: str(r[payerKey]), amount: deposit,
                memo: memoKey ? str(r[memoKey]) : '', _file: ctx.fileName, _row: rowNo });
  });
  return { txns, warnings, ignored_withdraw: ignored };
}

// ---- ノード本体 ----
// DECISION (D31): Google Drive Trigger emits EVERY file created since the last poll as one item each of a single execution
// (GoogleDriveTrigger.node.js poll() → returnJsonArray(files)); Check File Is CSV / Download File run per item. All input items
// are parsed here (not only item 0) and every output item is paired with its source item index.
// DECISION (D22): Download File passes the trigger json through (download.operation.js `json: item.json`), so the source
// mimeType is visible. A Google Sheet export is always UTF-8 (no BOM) → decode as utf-8, not CSV_MAPPING.encoding.
const cfg = $('Config').first().json;
const inputs = $input.all();
const out = [];
for (let i = 0; i < inputs.length; i++) {
  const it = inputs[i];
  const ctx = { tz: cfg.TZ, fileName: it.json.name || it.binary?.data?.fileName || '' };
  const isSheetExport = str(it.json.mimeType) === 'application/vnd.google-apps.spreadsheet';
  const buf = await this.helpers.getBinaryDataBuffer(i, 'data');        // itemIndex, binary property（A12 で動作確認済み）
  const text = decodeCsvBuffer(buf, isSheetExport ? 'utf-8' : cfg.CSV_MAPPING.encoding);
  const { txns, warnings, ignored_withdraw } = parseBankCsv(parseCsvText(text), cfg.CSV_MAPPING, ctx);
  out.push(
    ...txns.map((t) => ({ json: t, pairedItem: { item: i } })),
    ...warnings.map((w) => ({ json: { _kind: 'warning', ...w }, pairedItem: { item: i } })),
    { json: { _kind: 'file_stats', file_name: ctx.fileName, ignored_withdraw, rows_total: txns.length + warnings.length + ignored_withdraw }, pairedItem: { item: i } },
  );
}
return out;
