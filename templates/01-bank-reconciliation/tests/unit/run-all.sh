#!/usr/bin/env bash
# Runs every unit suite of template 01 (one test-<module>.sh per Code node, each over tests/unit/scenarios/<module>/*.json)
# plus the end-to-end chain tests/unit/integration.mjs, all on the same code/*.js files that workflow.json embeds (ASSUMPTIONS A15).
# Prints one PASS/FAIL line per suite (each suite prints its own per-scenario / per-assertion lines above it) and exits
# non-zero if any suite failed.
#
#   usage: [NODE_BIN=/path/to/node] [LUXON_PATH=/path/to/node_modules/luxon] [UNIT_TMP_DIR=/path] tests/unit/run-all.sh [workflow.json]
#     NODE_BIN      Node >= 24 with full ICU (TextDecoder('shift_jis')); default: `node` on PATH
#     LUXON_PATH    n8n's luxon copy (default: the module name "luxon", i.e. it must be resolvable from tests/unit/)
#     UNIT_TMP_DIR  where the suites write their per-scenario stdout/stderr and the integration chain writes its per-node files
#                   (default: each suite uses its own mktemp -d)
#     workflow.json (optional) — forwarded to the module suites that accept it, so the jsCode embedded in the workflow is tested
#                   instead of code/*.js (the integration chain always runs code/*.js)
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TPL="$(cd "$HERE/../.." && pwd)"
NODE_BIN="${NODE_BIN:-node}"
LUXON_PATH="${LUXON_PATH:-luxon}"
export NODE_BIN LUXON_PATH
[ -n "${UNIT_TMP_DIR:-}" ] && export UNIT_TMP_DIR
WF="${1:-}"

pass=0; fail=0; failed_names=()
run_suite() {   # run_suite <name> <command...>
  local name="$1"; shift
  echo "=== $name ==="
  if "$@"; then pass=$((pass + 1)); echo "PASS suite $name"; else fail=$((fail + 1)); failed_names+=("$name"); echo "FAIL suite $name"; fi
}

run_suite shared-helpers "$NODE_BIN" "$HERE/check-shared-helpers.mjs" "$TPL"/code/*.js
for m in parse_bank_csv parse_mail collect_transactions normalize_payer match_invoices build_notification build_error_message check_notification_results; do
  if [ -n "$WF" ] && [ "$m" != "build_error_message" ]; then
    run_suite "test-$m" bash "$HERE/test-$m.sh" "$WF"        # Build Error Message lives in error-handler.json, not workflow.json
  else
    run_suite "test-$m" bash "$HERE/test-$m.sh"
  fi
done
INTEGRATION_ARGS=(--luxon "$LUXON_PATH")
[ -n "${UNIT_TMP_DIR:-}" ] && INTEGRATION_ARGS+=(--tmp "$UNIT_TMP_DIR")
run_suite integration "$NODE_BIN" "$HERE/integration.mjs" "${INTEGRATION_ARGS[@]}"

echo "run-all: $pass suites passed, $fail suites failed${failed_names[*]:+ (${failed_names[*]})}"
[ "$fail" -eq 0 ] && [ "$pass" -gt 0 ]
