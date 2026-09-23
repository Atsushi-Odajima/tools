// DESIGN.md §6.1: helpers shared between Code nodes must be byte-identical. Compares the marked blocks of two code files.
// usage: node check-shared-helpers.mjs <a.js> <b.js> [more.js ...]   (blocks: "shared helpers", "shared: normalizeDate", "shared: fill / fmtYen")
import fs from 'node:fs';
import path from 'node:path';
const files = process.argv.slice(2);
const BLOCKS = [
  ['// ---- shared helpers: toInt / num / str', '// ---- end shared helpers ----'],
  ['// ---- shared: normalizeDate', '// ---- end shared normalizeDate ----'],
  ['// ---- shared: fill / fmtYen', '// ---- end shared fill / fmtYen ----'],
];
const extract = (text, [start, end]) => {
  const i = text.indexOf(start); if (i < 0) return null;
  const j = text.indexOf(end, i); if (j < 0) return null;
  return text.slice(i, j + end.length);
};
let fail = null;
for (const [start, end] of BLOCKS) {
  const blocks = files.map((f) => extract(fs.readFileSync(f, 'utf8'), [start, end]));
  const present = blocks.map((b, i) => [b, files[i]]).filter(([b]) => b !== null);
  if (present.length < 2) continue;                       // a block that only one file carries is not shared
  const [ref, refFile] = present[0];
  for (const [b, f] of present.slice(1)) {
    if (b !== ref) { fail = `${start.trim()} differs between ${path.basename(refFile)} and ${path.basename(f)}`; break; }
  }
  if (fail) break;
}
console.log(fail ? `FAIL shared-helpers-identical: ${fail}` : `PASS shared-helpers-identical (${files.map((f) => path.basename(f)).join(', ')})`);
process.exit(fail ? 1 : 0);
