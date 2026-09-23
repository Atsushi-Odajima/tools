// Run one Code node's jsCode from workflow.json outside n8n, with minimal shims for the
// n8n sandbox globals actually used by this template ($input, $('Node'), $now, DateTime,
// this.helpers.getBinaryDataBuffer). Purpose: fast, deterministic unit tests of the matching
// logic against fixtures before running the same code inside local n8n (P3).
//
// usage: node run-code-node.mjs <workflow.json|code.js> <NodeName|-> <scenario.json> [--luxon <path to luxon>]
// scenario.json: { "input": [ {json:{...}, binary?:{data:{data:<base64>,...}}} ],
//                  "nodes": { "Config": [ {json:{...}} ], "Read Invoices": [ ... ] },
//                  "now": "2026-09-23T09:00:00+09:00" }
// prints the returned items as JSON to stdout.
import fs from 'node:fs';
import { createRequire } from 'node:module';
const [wfPath, nodeName, scenarioPath, ...rest] = process.argv.slice(2);
const luxonPath = rest.includes('--luxon') ? rest[rest.indexOf('--luxon') + 1] : 'luxon';
const require = createRequire(import.meta.url);
const { DateTime } = require(luxonPath);
let jsCode;
if (wfPath.endsWith('.js')) {
  // raw Code-node source file (the same text that is embedded into workflow.json)
  jsCode = fs.readFileSync(wfPath, 'utf8');
} else {
  const wf = JSON.parse(fs.readFileSync(wfPath, 'utf8'));
  const node = wf.nodes.find(n => n.name === nodeName);
  if (!node) { console.error(`node not found: ${nodeName}`); process.exit(2); }
  if (node.type !== 'n8n-nodes-base.code') { console.error(`not a Code node: ${nodeName}`); process.exit(2); }
  jsCode = node.parameters.jsCode;
}
const scenario = JSON.parse(fs.readFileSync(scenarioPath, 'utf8'));
const inputItems = scenario.input || [];
const nodeOutputs = scenario.nodes || {};
const nowIso = scenario.now || '2026-09-23T09:00:00+09:00';
const $now = DateTime.fromISO(nowIso, { setZone: true });
const $input = {
  all: () => inputItems,
  first: () => inputItems[0],
  last: () => inputItems[inputItems.length - 1],
  item: inputItems[0],
};
const $ = (name) => {
  const items = nodeOutputs[name];
  if (!items) throw new Error(`Referenced node has no data in scenario: ${name}`);
  return { all: () => items, first: () => items[0], last: () => items[items.length - 1], item: items[0] };
};
const helpers = {
  getBinaryDataBuffer: async (itemIndex, propertyName) => {
    const b = inputItems[itemIndex]?.binary?.[propertyName];
    if (!b) throw new Error(`no binary '${propertyName}' on item ${itemIndex}`);
    return Buffer.from(b.data, 'base64');
  },
};
const items = inputItems; // legacy alias available in n8n
const $json = inputItems[0]?.json;
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const fn = new AsyncFunction('$input', '$', '$now', 'DateTime', 'items', '$json', jsCode);
const result = await fn.call({ helpers }, $input, $, $now, DateTime, items, $json);
process.stdout.write(JSON.stringify(result, null, 1) + '\n');
