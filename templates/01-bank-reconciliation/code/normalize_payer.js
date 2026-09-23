// Normalize Payer — n8n Code node (JavaScript, Run Once for All Items). DESIGN.md §6.6 / D27.
// The ONLY place that defines remitter-name normalization, memo_norm and txn_id. Runs right after Read Transactions:
//   $input.all()                      = Read Transactions rows (Always Output Data: an empty sheet yields one {} row → skipped)
//   $('Read Invoices').all()          = invoices rows ({} rows skipped); each row gets _names = normalized customer_name + aliases
//   $('Collect Transactions').first() = { source, txns (pre-txn, no txn_id), warnings, ignored_withdraw, file_name }
// Output: exactly ONE item { source, file_name, ignored_withdraw, warnings, txns, invoices, existing } for Match Invoices.
// Shared helpers toInt / num / str (every Code node) and esc / hiraToKata / splitCsvList / uniq are byte-identical to DESIGN.md §6.1.

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
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');            // 正規表現エスケープ
const hiraToKata = (s) => s.replace(/[ぁ-ゖ]/g, (ch) => String.fromCharCode(ch.charCodeAt(0) + 0x60));
const splitCsvList = (s) => str(s).split(/[,、，]/).map((x) => x.trim()).filter(Boolean);
const uniq = (arr) => [...new Set(arr)];

// 仕様の 5 手順。tokens = cfg.LEGAL_ENTITY_TOKENS, stripLeadingDigits = cfg.STRIP_LEADING_DIGITS
// トークン除去は 2 段階：(a) どこでも除去するトークン（振込・フリコミ・株式会社 等）を先に消し、
// (b) そのあとで前株 `X)`（先頭のみ）・後株 `(X`（末尾のみ）を当てる。1 回の走査で長さ順に混ぜると
// fixture A-1（`振込` + 半角の前株略記 + 名義）は前株トークンが先頭に来る前に試されて残り、`カサンプルシヨウジ` になる（fixture で確認済み）
function normalizePayer(raw, tokens, stripLeadingDigits) {
  let s = str(raw).normalize('NFKC');                                   // 1. NFKC：全角英数→半角、半角カナ→全角カナ（濁点合成）、全角括弧→半角
  s = hiraToKata(s);                                                    // 2. ひらがな→カタカナ
  s = s.replace(/[\s　]+/g, '');                                    // 4a. 空白は先に除去（トークン照合を安定させる）
  const toks = uniq((tokens || []).map((t) => hiraToKata(str(t).normalize('NFKC')).replace(/[\s　]+/g, '')).filter(Boolean))
    .sort((a, b) => b.length - a.length);                               // 長いトークンから
  const anchored = (t) => t.endsWith(')') || t.startsWith('(');
  for (const t of toks) {                                               // 3a. どこでも除去（株式会社・振込・フリコミ 等）
    if (!anchored(t)) s = s.split(t).join('');
  }
  for (const t of toks) {                                               // 3b. 法人格略記のアンカー付き除去（D19）
    if (t.endsWith(')')) s = s.replace(new RegExp('^(\\d*)' + esc(t)), '$1');        // 前株形 カ) … 先頭のみ（先頭の数字列は許容）
    else if (t.startsWith('(')) s = s.replace(new RegExp(esc(t) + '$'), '');         // 後株形 (カ … 末尾のみ
  }
  s = s.replace(/[^\p{L}\p{N}ー]/gu, '');                                // 4b. 文字・数字・長音「ー」以外（・ 記号 括弧）を除去
  if (stripLeadingDigits) s = s.replace(/^\d+/, '');                    // 5. 先頭の振込人番号・支店コード
  return s;
}

// memo_norm：NFKC → 空白除去 → `|` を `/` に → 小文字化。記号は残す（shared/sheets-schema.md と同じ定義）
const normalizeMemo = (memo) => str(memo).normalize('NFKC').replace(/[\s　]+/g, '').replace(/\|/g, '/').toLowerCase();

function buildTxnId(txnDateIso, amount, payerNorm, memoNorm) {
  return `${txnDateIso}|${amount}|${payerNorm}|${memoNorm}`;            // §5：date|amount|payer_norm|memo_norm
}

// pre-txn（_kind: 'txn'）→ txn。_file / _row / _message_id / _parser はそのまま通す
function buildTxn(t, cfg) {
  const { _kind, ...rest } = t;
  const payer_name_norm = normalizePayer(t.payer_name_raw, cfg.LEGAL_ENTITY_TOKENS, cfg.STRIP_LEADING_DIGITS);
  const memo_norm = normalizeMemo(t.memo);
  return { txn_id: buildTxnId(t.txn_date, t.amount, payer_name_norm, memo_norm), ...rest, payer_name_norm };
}

// 請求側の比較対象：customer_name の正規化値 + payer_name_alias 各要素の正規化値（重複除去・空除去）
function invoiceNames(inv, cfg) {
  return uniq([inv.customer_name, ...splitCsvList(inv.payer_name_alias)]
    .map((n) => normalizePayer(n, cfg.LEGAL_ENTITY_TOKENS, cfg.STRIP_LEADING_DIGITS)).filter(Boolean));
}

// ---- ノード本体（Read Transactions の直後。常に 1 アイテム）----
const cfg = $('Config').first().json;
const collected = $('Collect Transactions').first().json;               // { source, txns(pre-txn), warnings, ignored_withdraw, file_name }
const invoices = $('Read Invoices').all().map((i) => i.json)
  .filter((i) => str(i.invoice_id))                                     // Always Output Data の {} を除外
  .map((i) => ({ ...i, _names: invoiceNames(i, cfg) }));
const existing = $input.all().map((i) => i.json)
  .filter((r) => str(r.txn_id))
  .map((r) => ({ ...r, payer_name_norm: str(r.payer_name_norm) || normalizePayer(r.payer_name_raw, cfg.LEGAL_ENTITY_TOKENS, cfg.STRIP_LEADING_DIGITS) }));
const txns = (collected.txns || []).map((t) => buildTxn(t, cfg));
return [{ json: { source: collected.source, file_name: collected.file_name, ignored_withdraw: num(collected.ignored_withdraw),
                  warnings: collected.warnings || [], txns, invoices, existing }, pairedItem: { item: 0 } }];
