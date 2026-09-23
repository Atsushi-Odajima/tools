// Check Notification Results — n8n Code node (JavaScript, Run Once for All Items). DESIGN.md §6.10 / D17 / §8.2.
// Source of truth: templates/01-bank-reconciliation/code/check_notification_results.js; workflow.json embeds this text verbatim (ASSUMPTIONS A15).
// Input : every item that reached Merge Notification Results (Append, 8 inputs): the success output (main[0]) and the error output
//         (main[1]) of Notify Slack / Notify Email / Notify LINE / Notify Chatwork. Build Notification emits ONE item, so each attempted
//         channel contributes exactly one item to exactly one of its two outputs; channels absent from NOTIFY_CHANNELS contribute nothing.
// Error-output item shape (n8n 2.40.5): the engine merges the paired input json into the node's error item
//         (n8n-core workflow-execute.js handleNodeErrorOutput) → { json: { …title, body_text, …, error: <error> } } where <error> is
//         an OBJECT { message, name, stack } (+ json.details) for HTTP Request v4.5 — measured in local n8n, execution 15, see
//         tests/unit/DISCREPANCIES.md — or the message STRING for nodes that push { json: { error: error.message } } (Slack / Gmail sources).
//         Both shapes are handled below; only the message text is reported.
// Pass-through item shape (n8n 2.40.5, P3 finding F2 / DESIGN D34): a DISABLED node passes its input items through unchanged to its
//         main output, so when a channel is listed in NOTIFY_CHANNELS while its Notify node is disabled (e.g. because the buyer never
//         assigned a credential and disabled the node to be able to activate the workflow), the Build Notification payload
//         { title, body_text, slack_blocks, line_text, chatwork_text } arrives here untouched, without json.error and without any
//         channel response marker. Such an item is counted as FAILED ("notify node disabled or not executed (payload passed through)")
//         so that a silent non-delivery is never reported as a success. Real successes carry the API response instead of the payload:
//         Slack { ok, ts, channel, message }, Gmail { id, threadId, labelIds }, LINE {} or { sentMessages }, Chatwork { message_id }.
// Output: ONE item { channels_attempted, channels_ok, channels_failed, errors[] }. Throws — and thereby reaches the Error Workflow —
//         only when every attempted channel failed (CLAUDE.md §4.3「全チャネル失敗時は Error Workflow へ」). A partial failure is
//         recorded in this output and in the execution log while the run succeeds (the sheets are already written; a re-run is safe).
// Shared helpers toInt / num / str are byte-identical in every Code node (DESIGN.md §6.1).

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

// ---- ノード本体 / node body (DESIGN.md §6.10) ----
// DECISION: the pseudocode's local is named `items`; renamed to `inputs` because `items` is n8n's legacy Code-node alias for $input.all()
// (a sandbox global). Redeclaring it is a SyntaxError in tests/unit/run-code-node.mjs (which passes the alias as a parameter) and would
// only shadow the global inside n8n. Logic is unchanged.
const inputs = $input.all().map((i) => (i.json && typeof i.json === 'object') ? i.json : {});
const has = (j, k) => Object.prototype.hasOwnProperty.call(j, k);
const isError = (j) => j.error !== undefined && j.error !== null;                              // error 出力のアイテムだけが json.error を持つ
// Build Notification のペイロードをそのまま持ち（title+body_text、または slack_blocks / line_text / chatwork_text）、
// チャネル応答のマーカー（Slack ok/ts/channel、Gmail id/threadId/labelIds、LINE sentMessages、Chatwork message_id）が無い
// アイテム = Notify ノードが無効化されていて入力がそのまま通過したもの（D34）。
const PAYLOAD_KEYS = ['slack_blocks', 'line_text', 'chatwork_text'];
const RESPONSE_MARKERS = ['ok', 'ts', 'channel', 'id', 'threadId', 'labelIds', 'sentMessages', 'message_id'];
const isPassThrough = (j) => !isError(j)
  && ((has(j, 'title') && has(j, 'body_text')) || PAYLOAD_KEYS.some((k) => has(j, k)))
  && !RESPONSE_MARKERS.some((k) => has(j, k));
const PASS_THROUGH_MSG = 'notify node disabled or not executed (payload passed through)';
const failed = inputs.filter((j) => isError(j) || isPassThrough(j));
const ok = inputs.length - failed.length;
const messages = failed.map((j) => (isError(j) ? (typeof j.error === 'string' ? j.error : (j.error.message || JSON.stringify(j.error))) : PASS_THROUGH_MSG));
if (inputs.length > 0 && ok === 0) {
  throw new Error(`All notification channels failed (${failed.length}): ${messages.join(' / ')}`);   // 仕様 §4.3：全チャネル失敗時は Error Workflow へ
}
// DECISION: pairedItem is attached only when an input item exists to pair with. The 0-item case is theoretical — with no data on any
// Merge input n8n never executes this node (NOTIFY_CHANNELS = [] ends at the four IF nodes, §6.10) — but a dangling { item: 0 } is avoided.
return [{ json: { channels_attempted: inputs.length, channels_ok: ok, channels_failed: failed.length, errors: messages },
          ...(inputs.length ? { pairedItem: { item: 0 } } : {}) }];
