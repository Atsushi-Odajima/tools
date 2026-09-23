// Build Notification — n8n Code node (JavaScript, Run Once for All Items). DESIGN.md §6.8 / §3.7 / D12 / D16 / D28.
// Source of truth: templates/01-bank-reconciliation/code/build_notification.js; workflow.json embeds this text verbatim (ASSUMPTIONS A15).
// Input : $input.first().json = the ONE `_kind: 'summary'` item of Match Invoices (Route Match Results output 2):
//         { date, source, file_name, n, a, b, c, rematched, skipped_existing, skipped_duplicate_in_batch, ignored_withdraw,
//           auto[], needs_review[], ambiguous[], unmatched[], warnings[] }
// Output: exactly ONE item { title, body_text, slack_blocks, line_text, chatwork_text } consumed by Check … Enabled → Notify …,
//         or [] when no notification is due (D12) — then no downstream node runs.
// Copy  : cfg.MESSAGES[LANG].recon_summary (shared/messages.*.json incl. the D16 keys). Sections in order: needs review → ambiguous →
//         unmatched → auto → warnings; each capped at cfg.NOTIFY_MAX_LINES lines (default 40) followed by more_items.
// Limits: Slack header ≤ 150 chars, section text ≤ 3,000 chars (chunked at 2,900; docs.slack.dev Block Kit reference, 2026-09-23);
//         LINE text ≤ 4,900 (API limit 5,000); Chatwork gets the full body (API limit 65,535; ASSUMPTIONS.md 外部 API).
// Shared helpers toInt / num / str (every Code node) and fill / fmtYen (also in Build Error Message) are byte-identical to DESIGN.md §6.1.

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

// ---- shared: fill / fmtYen — identical text in Build Notification and Build Error Message (DESIGN §6.1) ----
const fill = (tpl, vars) => String(tpl).replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));   // {name} 置換。未知のキーは残す
const fmtYen = (n, lang) => Number(n).toLocaleString(lang === 'en' ? 'en-US' : 'ja-JP');                       // 33000 → "33,000"
// ---- end shared fill / fmtYen ----

// ---- ノード本体 / node body (DESIGN.md §6.8) ----
const cfg = $('Config').first().json;
const s = $input.first().json;                                        // summary
const lang = cfg.LANG === 'en' ? 'en' : 'ja';
const m = cfg.MESSAGES && cfg.MESSAGES[lang] && cfg.MESSAGES[lang].recon_summary;   // shared/messages.*.json の recon_summary（D16 のキーを含む）
if (!m) throw new Error(`Config.MESSAGES.${lang}.recon_summary is missing`);         // Config の誤りは隠さず失敗させる（§2.5）
// DECISION: the summary's arrays and counters are read through arr() / num() so a partial or hand-edited summary (missing key,
// numeric string) cannot throw on .filter / .map or print "undefined"; Match Invoices always emits every key, so the normal path is unchanged.
const arr = (v) => (Array.isArray(v) ? v : []);
const warnings = arr(s.warnings);

// D12：Drive / Gmail 実行は常に通知（0 件でも no_transactions）。Schedule 実行は状態が変わったか、取込警告があるときだけ。
// non_jpy_invoice は常設の状態なので Schedule 実行の判定には数えない（USD 請求が 1 件あるだけで毎朝通知しない、D28）
const actionableWarnings = warnings.filter((w) => w.type !== 'non_jpy_invoice');
if (s.source === 'schedule' && num(s.rematched) === 0 && actionableWarnings.length === 0) return [];

const yen = (n) => fmtYen(n, lang);
const reasonText = (d) => {                                            // D16：messages.*.json の recon_summary.reasons
  const r = m.reasons;
  switch (d.reason) {
    case 'amount_only': return r.amount_only;
    case 'fee_deducted': return fill(r.fee_deducted, { fee: yen(d.fee) });
    case 'combined': return r.combined;
    case 'partial': return fill(r.partial, { remaining: yen(d.remaining_after) });
    case 'overpaid': return r.overpaid;
    default: return '';                                                // auto / same_amount_multiple / no_candidate 等は理由句なし
  }
};
const lineMatched = (d) => fill(m.line_item, { txn_date: d.txn_date, payer_raw: d.payer_raw, amount: yen(d.amount),
                                                invoice_id: arr(d.invoice_ids).join(', ') + (reasonText(d) ? ` ${reasonText(d)}` : '') });
const lineCands = (d) => fill(m.line_item_candidates, { txn_date: d.txn_date, payer_raw: d.payer_raw, amount: yen(d.amount),
                                                          candidates: arr(d.candidates).length
                                                            ? arr(d.candidates).map((c) => `${c.invoice_id}(¥${yen(c.remaining)})`).join(', ') + (reasonText(d) ? ` ${reasonText(d)}` : '')
                                                            : '—' });
const lineWarning = (w) => '・' + [w.type, w.parser, w.subject || w.value, w.invoice_id, w.currency].filter(Boolean).join(' ');   // 例: ・non_jpy_invoice INV-2026-022 USD

function section(heading, lines) {                                     // 見出し + 明細（NOTIFY_MAX_LINES 行まで）+ 「…他 N 件」
  if (!lines.length) return null;
  const max = num(cfg.NOTIFY_MAX_LINES) || 40;
  const shown = lines.slice(0, max);
  if (lines.length > max) shown.push(fill(m.more_items, { n: lines.length - max }));
  return [heading, ...shown].join('\n');
}

let title;
let sections = [];
if (num(s.n) === 0 && num(s.rematched) === 0) {
  title = fill(m.no_transactions, { date: str(s.date) });
  if (num(s.skipped_existing)) sections.push(fill(m.skipped_note, { n: num(s.skipped_existing) }));      // 「（処理済みのため skip：N 件）」（R09）
} else {
  title = fill(m.title, { date: str(s.date), n: num(s.n), a: num(s.a), b: num(s.b), c: num(s.c) });
  sections.push(section(m.needs_review_heading, arr(s.needs_review).map(lineMatched)));
  sections.push(section(m.ambiguous_heading, arr(s.ambiguous).map(lineCands)));
  sections.push(section(m.unmatched_heading, arr(s.unmatched).map(lineCands)));
  sections.push(section(m.auto_heading, arr(s.auto).map(lineMatched)));
}
if (warnings.length) sections.push(section(m.warnings_heading, warnings.map(lineWarning)));
sections = sections.filter(Boolean);

const body_text = [title, ...sections].join('\n\n').trim();
const chunk = (text, size) => { const out = []; for (let i = 0; i < text.length; i += size) out.push(text.slice(i, i + size)); return out; };
const slack_blocks = [
  { type: 'header', text: { type: 'plain_text', text: title.slice(0, 150) } },                                   // header text ≤ 150 文字
  ...sections.flatMap((sec) => chunk(sec, 2900).map((t) => ({ type: 'section', text: { type: 'mrkdwn', text: t } }))),   // section text ≤ 3,000 文字
];
return [{ json: { title, body_text, slack_blocks, line_text: body_text.slice(0, 4900), chatwork_text: body_text }, pairedItem: { item: 0 } }];
