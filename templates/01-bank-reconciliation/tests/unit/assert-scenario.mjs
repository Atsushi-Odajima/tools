// Compare one run-code-node.mjs result with the scenario's "expect" block.
// usage: node assert-scenario.mjs <scenario.json> <stdout-file> <stderr-file> <exit-code>
// expect: { "items": [ ... ] }               → exit code must be 0 and the printed array must deep-equal items
//         { "error_includes": "text" }        → exit code must be non-zero and stderr must contain the text
// Prints "PASS <scenario>" or "FAIL <scenario>: <first difference>" and exits 0 / 1.
import fs from 'node:fs';
import path from 'node:path';
const [scenarioPath, outPath, errPath, codeStr] = process.argv.slice(2);
const name = path.basename(scenarioPath, '.json');
const sc = JSON.parse(fs.readFileSync(scenarioPath, 'utf8'));
const exp = sc.expect || {};
const code = Number(codeStr);
const show = (v) => JSON.stringify(v);
function diff(want, got, p = '$') {
  if (Array.isArray(want)) {
    if (!Array.isArray(got)) return `${p}: expected array, got ${show(got)}`;
    if (want.length !== got.length) return `${p}: expected ${want.length} items, got ${got.length}`;
    for (let i = 0; i < want.length; i++) { const d = diff(want[i], got[i], `${p}[${i}]`); if (d) return d; }
    return null;
  }
  if (want !== null && typeof want === 'object') {
    if (got === null || typeof got !== 'object' || Array.isArray(got)) return `${p}: expected object, got ${show(got)}`;
    const wk = Object.keys(want).sort(), gk = Object.keys(got).sort();
    if (wk.join(',') !== gk.join(',')) return `${p}: expected keys [${wk}], got [${gk}]`;
    for (const k of wk) { const d = diff(want[k], got[k], `${p}.${k}`); if (d) return d; }
    return null;
  }
  return Object.is(want, got) ? null : `${p}: expected ${show(want)} (${typeof want}), got ${show(got)} (${typeof got})`;
}
let fail = null;
const stderr = fs.existsSync(errPath) ? fs.readFileSync(errPath, 'utf8') : '';
if (exp.error_includes) {
  if (code === 0) fail = `expected a failure containing ${show(exp.error_includes)} but the node returned normally`;
  else if (!stderr.includes(exp.error_includes)) fail = `stderr lacks ${show(exp.error_includes)}; stderr: ${stderr.trim().slice(0, 400)}`;
} else if (code !== 0) {
  fail = `exit code ${code}; stderr: ${stderr.trim().slice(0, 400)}`;
} else {
  let actual;
  try { actual = JSON.parse(fs.readFileSync(outPath, 'utf8')); } catch (e) { fail = `stdout is not JSON: ${e.message}`; }
  if (!fail) fail = diff(exp.items, actual);
}
console.log(fail ? `FAIL ${name}: ${fail}` : `PASS ${name}`);
process.exit(fail ? 1 : 0);
