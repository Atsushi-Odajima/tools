// Assert one run-code-node.mjs result against the scenario's "expect" block (a superset of the inline checker in test-normalize_payer.sh
// and of assert-scenario.mjs). Prints "PASS <scenario> (<n> assertions)" or "FAIL <scenario>" + one line per failed assertion; exit 0 / 1.
// usage: node assert-paths.mjs <scenario.json> <stdout-file> <stderr-file> <exit-code>
// expect keys (all optional; every listed assertion must hold):
//   error_includes: "text"                      → exit code must be non-zero and stderr must contain the text (nothing else is checked)
//   length: N                                   → the returned array has exactly N items
//   paths: { "<path>": value }                  → deep-equal (canonical JSON, key order ignored) at that path; with "[*]" the value is the
//                                                 list of every match (e.g. "[0].json.slack_blocks[*].type": ["header","section"])
//   absent: [ "<path>" ]                        → undefined at that path
//   max_length: { "<path>": N }                 → string / array length ≤ N ("[*]" in a path applies the check to every element)
//   min_length: { "<path>": N }                 → string / array length ≥ N
//   contains: { "<path>": [ "sub", … ] }        → the string at path contains every substring
//   not_contains: { "<path>": [ "sub", … ] }    → the string at path contains none of the substrings
//   count: { "<path>": { "needle": N } }        → each needle occurs exactly N times in the string at path
//   equal_paths: { "<path>": "<other path>" }   → the values at both paths are deep-equal
// path syntax: "[0].json.body_text", "[0].json.slack_blocks[*].text.text", "[0].json.line_text.length"
import fs from 'node:fs';
import path from 'node:path';
const [scenarioPath, outPath, errPath, codeStr] = process.argv.slice(2);
const name = path.basename(scenarioPath, '.json');
const sc = JSON.parse(fs.readFileSync(scenarioPath, 'utf8'));
const exp = sc.expect || {};
const code = Number(codeStr);
const stderr = fs.existsSync(errPath) ? fs.readFileSync(errPath, 'utf8') : '';
const canon = (v) => JSON.stringify(v, (k, x) => (x && typeof x === 'object' && !Array.isArray(x))
  ? Object.keys(x).sort().reduce((o, kk) => { o[kk] = x[kk]; return o; }, {}) : x);
const tokens = (p) => p.split(/[.\[\]]+/).filter(Boolean);
// resolve → array of values (several when the path contains "*"); a missing key yields undefined
const resolve = (obj, p) => tokens(p).reduce((acc, k) => acc.flatMap((o) => {
  if (o === null || o === undefined) return [undefined];
  if (k === '*') return Array.isArray(o) ? o : [undefined];
  return [o[k]];
}), [obj]);
const get = (obj, p) => resolve(obj, p)[0];
const errors = [];
let n = 0;
const check = (ok, msg) => { n++; if (!ok) errors.push(msg); };
const show = (v) => { const s = canon(v); return s === undefined ? 'undefined' : (s.length > 300 ? s.slice(0, 300) + '…' : s); };

if (exp.error_includes) {
  check(code !== 0, `expected a failure containing ${JSON.stringify(exp.error_includes)} but the node returned normally`);
  if (code !== 0) check(stderr.includes(exp.error_includes), `stderr lacks ${JSON.stringify(exp.error_includes)}; stderr: ${stderr.trim().slice(0, 400)}`);
} else if (code !== 0) {
  check(false, `exit code ${code}; stderr: ${stderr.trim().slice(0, 400)}`);
} else {
  let out;
  try { out = JSON.parse(fs.readFileSync(outPath, 'utf8')); } catch (e) { check(false, `stdout is not JSON: ${e.message}`); }
  if (out !== undefined) {
    if (exp.length !== undefined) check(Array.isArray(out) && out.length === exp.length, `length: expected ${exp.length}, got ${Array.isArray(out) ? out.length : typeof out}`);
    for (const [p, want] of Object.entries(exp.paths || {})) {
      const got = p.includes('*') ? resolve(out, p) : get(out, p);                 // a wildcard path compares the whole list of matches
      check(canon(got) === canon(want), `${p}: expected ${show(want)}, got ${show(got)}`);
    }
    for (const p of exp.absent || []) { const got = get(out, p); check(got === undefined, `${p}: expected absent, got ${show(got)}`); }
    for (const [p, max] of Object.entries(exp.max_length || {})) for (const [i, v] of resolve(out, p).entries()) {
      check(v !== undefined && v !== null && v.length <= max, `${p}[#${i}]: expected length ≤ ${max}, got ${v === undefined || v === null ? show(v) : v.length}`);
    }
    for (const [p, min] of Object.entries(exp.min_length || {})) for (const [i, v] of resolve(out, p).entries()) {
      check(v !== undefined && v !== null && v.length >= min, `${p}[#${i}]: expected length ≥ ${min}, got ${v === undefined || v === null ? show(v) : v.length}`);
    }
    for (const [p, subs] of Object.entries(exp.contains || {})) { const v = get(out, p); for (const s of subs) check(typeof v === 'string' && v.includes(s), `${p}: expected to contain ${JSON.stringify(s)}`); }
    for (const [p, subs] of Object.entries(exp.not_contains || {})) { const v = get(out, p); for (const s of subs) check(typeof v === 'string' && !v.includes(s), `${p}: expected NOT to contain ${JSON.stringify(s)}`); }
    for (const [p, needles] of Object.entries(exp.count || {})) {
      const v = get(out, p);
      for (const [needle, want] of Object.entries(needles)) {
        const got = typeof v === 'string' ? v.split(needle).length - 1 : -1;
        check(got === want, `${p}: expected ${want} × ${JSON.stringify(needle)}, got ${got}`);
      }
    }
    for (const [p, q] of Object.entries(exp.equal_paths || {})) check(canon(get(out, p)) === canon(get(out, q)), `${p} ≠ ${q}`);
  }
}
if (errors.length) { console.log(`FAIL ${name}`); for (const e of errors) console.log('    ' + e); process.exit(1); }
console.log(`PASS ${name} (${n} assertions)`);
