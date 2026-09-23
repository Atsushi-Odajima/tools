#!/usr/bin/env bash
# Unit test for the "Collect Transactions" Code node: runs every scenario in tests/unit/scenarios/collect_transactions/*.json
# through run-code-node.mjs and asserts the scenario's "expect" block. Prints PASS/FAIL per scenario, exit 1 on any failure.
#
#   usage: [NODE_BIN=/path/to/node] [LUXON_PATH=/path/to/node_modules/luxon] tests/unit/test-collect_transactions.sh [workflow.json]
#     NODE_BIN    Node >= 20 (default: `node` on PATH)
#     LUXON_PATH  n8n's luxon copy (optional; without it run-code-node.mjs resolves the module name "luxon")
#     workflow.json (optional) — test the jsCode embedded in the workflow instead of code/collect_transactions.js
#
# Scenarios are generated from the fixtures by tests/unit/scenarios/build-normalize-collect.py (see its header).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TPL="$(cd "$HERE/../.." && pwd)"
MODULE="collect_transactions"
NODE_NAME="Collect Transactions"
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
if (exp.length !== undefined && !(Array.isArray(out) && out.length === exp.length)) {
  errors.push(`length: expected ${exp.length}, got ${Array.isArray(out) ? out.length : typeof out}`);
}
for (const [p, want] of Object.entries(exp.paths || {})) {
  const got = get(out, p);
  if (canon(got) !== canon(want)) errors.push(`${p}: expected ${canon(want)}, got ${canon(got)}`);
}
for (const p of exp.absent || []) {
  const got = get(out, p);
  if (got !== undefined) errors.push(`${p}: expected absent, got ${canon(got)}`);
}
const name = path.basename(scPath, '.json');
if (errors.length) { console.log(`FAIL ${name}`); for (const e of errors) console.log('    ' + e); process.exit(1); }
const n = Object.keys(exp.paths || {}).length + (exp.absent || []).length + (exp.length !== undefined ? 1 : 0);
console.log(`PASS ${name} (${n} assertions)`);
EOF
  then pass=$((pass + 1)); else fail=$((fail + 1)); fi
done
echo "$MODULE: $pass passed, $fail failed"
[ "$pass" -gt 0 ] && [ "$fail" -eq 0 ]
