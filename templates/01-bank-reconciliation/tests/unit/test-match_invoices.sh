#!/usr/bin/env bash
# Unit test for the "Match Invoices" Code node: runs every scenario in tests/unit/scenarios/match_invoices/*.json
# through run-code-node.mjs and asserts the scenario's "expect" block. Prints PASS/FAIL per scenario, exit 1 on any failure.
#
#   usage: [NODE_BIN=/path/to/node] [LUXON_PATH=/path/to/node_modules/luxon] tests/unit/test-match_invoices.sh [workflow.json]
#     NODE_BIN    Node >= 20 (default: `node` on PATH)
#     LUXON_PATH  n8n's luxon copy (optional; without it run-code-node.mjs resolves the module name "luxon")
#     workflow.json (optional) — test the jsCode embedded in the workflow instead of code/match_invoices.js
#
# Scenarios are generated from the fixtures by tests/unit/scenarios/build-match.py (see its header for the expect format):
#   length / count {_kind: n} / paths {path: value} / absent [path] / rows [{match, equals, absent}] / no_rows [{fields}]
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TPL="$(cd "$HERE/../.." && pwd)"
MODULE="match_invoices"
NODE_NAME="Match Invoices"
NODE_BIN="${NODE_BIN:-node}"
RUNNER="$HERE/run-code-node.mjs"
SRC="${1:-$TPL/code/$MODULE.js}"
LUXON_ARGS=()
[ -n "${LUXON_PATH:-}" ] && LUXON_ARGS=(--luxon "$LUXON_PATH")

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0
shopt -s nullglob
for sc in "$HERE/scenarios/$MODULE"/*.json; do
  name="$(basename "$sc" .json)"
  if ! "$NODE_BIN" "$RUNNER" "$SRC" "$NODE_NAME" "$sc" ${LUXON_ARGS[@]+"${LUXON_ARGS[@]}"} >"$TMP/out.json" 2>"$TMP/err.txt"; then
    echo "FAIL $name: runner error"; sed 's/^/    /' "$TMP/err.txt"; fail=$((fail + 1)); continue
  fi
  if "$NODE_BIN" - "$sc" "$TMP/out.json" <<'EOF'
const fs = require('fs');
const path = require('path');
const [scPath, outPath] = process.argv.slice(2);
const sc = JSON.parse(fs.readFileSync(scPath, 'utf8'));
const out = JSON.parse(fs.readFileSync(outPath, 'utf8'));
const exp = sc.expect || {};
const canon = (v) => JSON.stringify(v, (k, x) => (x && typeof x === 'object' && !Array.isArray(x))
  ? Object.keys(x).sort().reduce((o, kk) => { o[kk] = x[kk]; return o; }, {}) : x);
const get = (obj, p) => p.split(/[.\[\]]+/).filter(Boolean).reduce((o, k) => (o == null ? undefined : o[k]), obj);
const errors = [];
let n = 0;
if (!Array.isArray(out)) errors.push(`output is not an array: ${typeof out}`);
const items = Array.isArray(out) ? out : [];
if (exp.length !== undefined) { n++; if (items.length !== exp.length) errors.push(`length: expected ${exp.length}, got ${items.length}`); }
for (const [kind, want] of Object.entries(exp.count || {})) {
  n++;
  const got = items.filter((i) => i.json && i.json._kind === kind).length;
  if (got !== want) errors.push(`count[${kind}]: expected ${want}, got ${got}`);
}
for (const [p, want] of Object.entries(exp.paths || {})) {
  n++;
  const got = get(out, p);
  if (canon(got) !== canon(want)) errors.push(`${p}: expected ${canon(want)}, got ${canon(got)}`);
}
for (const p of exp.absent || []) {
  n++;
  const got = get(out, p);
  if (got !== undefined) errors.push(`${p}: expected absent, got ${canon(got)}`);
}
const matches = (j, sel) => j && Object.entries(sel).every(([k, v]) => canon(j[k]) === canon(v));
const label = (sel) => Object.entries(sel).map(([k, v]) => `${k}=${v}`).join(' ');
for (const row of exp.rows || []) {
  n++;
  const hits = items.filter((i) => matches(i.json, row.match));
  if (hits.length !== 1) { errors.push(`row {${label(row.match)}}: expected exactly 1 item, found ${hits.length}`); continue; }
  const j = hits[0].json;
  for (const [k, want] of Object.entries(row.equals || {})) {
    if (canon(j[k]) !== canon(want)) errors.push(`row {${label(row.match)}}.${k}: expected ${canon(want)}, got ${canon(j[k])}`);
  }
  for (const k of row.absent || []) {
    if (j[k] !== undefined) errors.push(`row {${label(row.match)}}.${k}: expected absent, got ${canon(j[k])}`);
  }
  if (!hits[0].pairedItem || hits[0].pairedItem.item !== 0) errors.push(`row {${label(row.match)}}: pairedItem must be {item: 0}`);
}
for (const sel of exp.no_rows || []) {
  n++;
  const hits = items.filter((i) => matches(i.json, sel));
  if (hits.length) errors.push(`no_rows {${label(sel)}}: expected none, found ${hits.length}`);
}
// every txn_row must carry every column of the transactions sheet (shared/sheets-schema.md), every invoice_update its 7 columns
const TXN_COLS = ['txn_id', 'source', 'txn_date', 'payer_name_raw', 'payer_name_norm', 'amount', 'memo', 'matched_invoice_ids', 'status', 'suggested_invoice_ids', 'imported_at'];
const INV_COLS = ['invoice_id', 'status', 'paid_amount', 'paid_date', 'matched_txn_ids', 'match_confidence', 'fee_deducted'];
for (const i of items) {
  const cols = i.json._kind === 'txn_row' ? TXN_COLS : i.json._kind === 'invoice_update' ? INV_COLS : null;
  if (!cols) continue;
  n++;
  const missing = cols.filter((c) => !(c in i.json));
  const extra = Object.keys(i.json).filter((c) => c !== '_kind' && !cols.includes(c));
  if (missing.length || extra.length) errors.push(`${i.json._kind} ${i.json.txn_id || i.json.invoice_id}: missing [${missing}] extra [${extra}]`);
  if (i.json._kind === 'txn_row' && !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$/.test(String(i.json.imported_at))) errors.push(`txn_row ${i.json.txn_id}: imported_at not ISO 8601 with offset: ${i.json.imported_at}`);
}
const name = path.basename(scPath, '.json');
if (errors.length) { console.log(`FAIL ${name}`); for (const e of errors) console.log('    ' + e); process.exit(1); }
console.log(`PASS ${name} (${n} assertions)`);
EOF
  then pass=$((pass + 1)); else fail=$((fail + 1)); fi
done
echo "$MODULE: $pass passed, $fail failed"
[ "$pass" -gt 0 ] && [ "$fail" -eq 0 ]
