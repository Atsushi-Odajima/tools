// Parse Mail — n8n Code node (JavaScript, Mode: Run Once for All Items). No require().
// Source of truth: templates/01-bank-reconciliation/code/parse_mail.js; workflow.json embeds this text verbatim
// (ASSUMPTIONS A15). Logic: DESIGN.md §6.3 + §6.5. Input: Gmail Trigger items (Simplify OFF: text / html / subject /
// from / date / id). Each mail yields exactly one item: a pre-txn { _kind: 'txn', source: 'gmail' } (no payer_name_norm /
// txn_id yet — "Normalize Payer" owns those) or a { _kind: 'warning' } item (no_parser_matched / parser_no_capture /
// bad_date). Config MAIL_PARSERS are tried in order; the first whose from_match and subject_match both hold is used (D15).

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

// ---- HTML 本文 → テキスト（text が無いメールだけに使う）----
function htmlToText(html) {
  return str(html)
    .replace(/<br\s*\/?>/gi, '\n').replace(/<\/(p|div|tr|li|h\d)>/gi, '\n').replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'");
}
// from_match / subject_match：大文字小文字無視・NFKC 後の部分一致。needle が空なら常に一致（D15）
const includesCI = (hay, needle) => !needle || str(hay).normalize('NFKC').toLowerCase().includes(str(needle).normalize('NFKC').toLowerCase());
const re = (src) => new RegExp(src, 'u');     // 買い手の正規表現。無効なら SyntaxError → 実行失敗（Config の誤りを隠さない）
// DECISION: Gmail Trigger (Simplify OFF) gives `from` as { text, value: [{ address, name }] } (DESIGN §3.1, to be
// confirmed live in P2 §8.3-4). The pseudocode reads from.text; if a runtime shape has no `text`, fall back to the
// addresses in `value` instead of producing "[object Object]". Strings are used as-is.
const fromText = (f) => {
  if (f && typeof f === 'object') {
    if (str(f.text)) return str(f.text);
    if (Array.isArray(f.value)) return f.value.map((v) => str(v && (v.address || v.name))).filter(Boolean).join(', ');
    return '';
  }
  return str(f);
};

// email: Gmail Trigger（Simplify OFF）の json。戻り値は { txn } または { warning }。txn は pre-txn（txn_id 無し）
function parseMail(email, parsers, ctx) {
  const from = fromText(email.from ?? email.headers?.from);
  const subject = str(email.subject);
  const rawBody = str(email.text) || htmlToText(email.html);            // text 優先
  const body = rawBody.normalize('NFKC');                               // 全角数字・全角コロン → 半角、半角カナ → 全角カナ
  const messageId = str(email.id);
  for (const p of parsers) {
    if (!includesCI(from, p.from_match) || !includesCI(subject, p.subject_match)) continue;
    const amountM = re(p.amount_regex).exec(body);
    const payerM = re(p.payer_regex).exec(body);
    const dateM = p.date_regex ? re(p.date_regex).exec(body) : null;
    const amount = amountM ? toInt(amountM[1]) : null;
    if (!(amount > 0) || !payerM) {
      return { warning: { type: 'parser_no_capture', parser: p.name, message_id: messageId, from, subject } };
    }
    let txn_date = dateM ? normalizeDate(dateM[1], 'auto', ctx.tz) : null;
    if (!txn_date) {
      // 本文に日付が無い／読めない → メールの受信日（TZ の暦日）
      const received = DateTime.fromJSDate(new Date(email.date)).setZone(ctx.tz);
      // DECISION: the pseudocode uses the email date unconditionally; an absent or unparsable `date` would otherwise
      // become the literal "Invalid DateTime" and poison txn_id. Emit a bad_date warning instead (safe default).
      if (!received.isValid) {
        return { warning: { type: 'bad_date', parser: p.name, message_id: messageId, from, subject, value: str(email.date) } };
      }
      txn_date = received.toFormat('yyyy-MM-dd');
    }
    const memo = `${subject} (gmail:${messageId})`;                     // D14：別メールの同額入金を潰さない
    return { txn: { _kind: 'txn', source: 'gmail', txn_date, payer_name_raw: str(payerM[1]), amount, memo, _message_id: messageId, _parser: p.name } };
  }
  return { warning: { type: 'no_parser_matched', message_id: messageId, from, subject } };
}

// ---- ノード本体 ----
const cfg = $('Config').first().json;
const ctx = { tz: cfg.TZ };
const out = [];
$input.all().forEach((item, i) => {
  const r = parseMail(item.json, cfg.MAIL_PARSERS, ctx);
  out.push({ json: r.txn ?? { _kind: 'warning', ...r.warning }, pairedItem: { item: i } });
});
return out;
