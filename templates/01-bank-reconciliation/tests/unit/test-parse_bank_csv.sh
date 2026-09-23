#!/usr/bin/env bash
# Unit tests for the Code node source code/parse_bank_csv.js (run outside n8n via run-code-node.mjs).
# Every scenarios/parse_bank_csv/*.json is executed and compared with its "expect" block (assert-scenario.mjs);
# the shared-helper blocks are also checked for byte-identity across the Code node files (DESIGN.md §6.1).
# Prints PASS/FAIL per scenario, a summary line, and exits non-zero if anything failed.
# Env: NODE_BIN (default: node, needs Node >= 20 with full ICU for TextDecoder('shift_jis')),
#      LUXON_PATH (default: luxon — point it at n8n's copy, e.g. <n8n>/node_modules/luxon),
#      UNIT_TMP_DIR (default: mktemp -d; per-scenario stdout/stderr files are written there).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TPL="$(cd "$HERE/../.." && pwd)"
NODE_BIN="${NODE_BIN:-node}"
LUXON_PATH="${LUXON_PATH:-luxon}"
TMP="${UNIT_TMP_DIR:-$(mktemp -d)}"
CODE="$TPL/code/parse_bank_csv.js"
mkdir -p "$TMP"
pass=0; fail=0
if "$NODE_BIN" "$HERE/check-shared-helpers.mjs" "$TPL/code/parse_bank_csv.js" "$TPL/code/parse_mail.js"; then pass=$((pass+1)); else fail=$((fail+1)); fi
for sc in "$HERE"/scenarios/parse_bank_csv/*.json; do
  base="$(basename "$sc" .json)"
  "$NODE_BIN" "$HERE/run-code-node.mjs" "$CODE" - "$sc" --luxon "$LUXON_PATH" >"$TMP/$base.out.json" 2>"$TMP/$base.err.txt"
  code=$?
  if "$NODE_BIN" "$HERE/assert-scenario.mjs" "$sc" "$TMP/$base.out.json" "$TMP/$base.err.txt" "$code"; then pass=$((pass+1)); else fail=$((fail+1)); fi
done
echo "parse_bank_csv: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
