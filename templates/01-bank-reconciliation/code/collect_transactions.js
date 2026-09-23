// Collect Transactions — n8n Code node (JavaScript, Run Once for All Items). DESIGN.md §6.4 / D01.
// Merge point of the three trigger paths. Always returns exactly ONE item
//   { source, txns, warnings, ignored_withdraw, file_name }
// so that Match Invoices never references a node that did not run in this execution.
// Input items: Parse Bank CSV output (pre-txns `_kind:'txn'`, `_kind:'warning'`, one `_kind:'file_stats'` per file),
// Parse Mail output (pre-txns / warnings), or the Config item on the Schedule path (no `_kind` → txns = []).
// payer_name_norm / txn_id are NOT assigned here (Normalize Payer owns them, D27).
// Shared helpers (toInt / num / str) are byte-identical in every Code node of this template (DESIGN.md §6.1).

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

// ---- ノード本体 / node body (DESIGN.md §6.4) ----
// DECISION: txn / warning objects are passed through unchanged (their `_kind` key included), exactly as the §6.4
// pseudocode does; §3.4 draws warnings without `_kind` but the extra key is harmless downstream (Build Notification
// reads `type`, and `_kind` never reaches a sheet). Normalize Payer strips `_kind` from txns when it builds txn_id.
// DECISION: the pseudocode's local is named `items`; renamed to `inputs` because `items` is n8n's legacy Code-node alias for
// $input.all() (a sandbox global). Redeclaring it is a SyntaxError in tests/unit/run-code-node.mjs (which passes the alias as a
// parameter) and would only shadow the global inside n8n. Logic is unchanged.
const inputs = $input.all().map((i) => i.json);
const cfg = $('Config').first().json;
const source = ({ 'Watch Drive Folder': 'drive', 'Watch Gmail Inbox': 'gmail', 'Run Daily Rematch': 'schedule' })[cfg.SOURCE] || 'unknown';
const txns = inputs.filter((j) => j._kind === 'txn');
const warnings = inputs.filter((j) => j._kind === 'warning');
// DECISION (D31): Parse Bank CSV emits one file_stats item PER FILE (several files can arrive in one Drive poll), so the stats are
// aggregated here: ignored_withdraw = sum, file_name = the file names joined with ", " (Gmail / Schedule paths have none → 0 / "").
const stats = inputs.filter((j) => j._kind === 'file_stats');
const ignored_withdraw = stats.reduce((sum, f) => sum + num(f.ignored_withdraw), 0);
const file_name = stats.map((f) => str(f.file_name)).filter(Boolean).join(', ');
return [{ json: { source, txns, warnings, ignored_withdraw, file_name }, pairedItem: { item: 0 } }];
