// Build Error Message — n8n Code node (JavaScript, Run Once for All Items) in error-handler.json. DESIGN.md §6.9 / §2.2 / D20.
// Source of truth: templates/01-bank-reconciliation/code/build_error_message.js; error-handler.json embeds this text verbatim (ASSUMPTIONS A15).
// Input : $input.first().json = the Error Trigger item. Two shapes (n8n docs, Error Trigger → "Error data"):
//   execution error: { execution: { id?, url?, retryOf?, error: { message, stack }, lastNodeExecuted, mode }, workflow: { id, name } }
//   trigger error  : { trigger: { error: { name, message, node: { name, … }, cause: { message, stack }, timestamp, context }, mode: 'trigger' },
//                      workflow: { id, name } }
//   execution.id / execution.url exist only when the execution was saved (absent for a trigger-node failure).
// Config: the error handler's own minimal Config (D20): LANG, NOTIFY_CHANNELS, SLACK_CHANNEL, NOTIFY_EMAIL_TO, LINE_TO_USER_ID,
//         CHATWORK_ROOM_ID, MESSAGES = { ja: { error_notice }, en: { error_notice } } (shared/messages.*.json).
// Output: exactly ONE item { title, body_text, slack_blocks, line_text, chatwork_text } — the same shape as Build Notification, so the
//         Check … Enabled / Notify … nodes are configured identically in both workflows (§2.3 E4〜).
// Shared helpers toInt / num / str (every Code node) and fill / fmtYen (also in Build Notification) are byte-identical to DESIGN.md §6.1.

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

// ---- shared: fill / fmtYen — identical text in Build Notification and Build Error Message (DESIGN §6.1) ----
const fill = (tpl, vars) => String(tpl).replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));   // {name} 置換。未知のキーは残す
const fmtYen = (n, lang) => Number(n).toLocaleString(lang === 'en' ? 'en-US' : 'ja-JP');                       // 33000 → "33,000"
// ---- end shared fill / fmtYen ----

// ---- ノード本体 / node body (DESIGN.md §6.9) ----
const e = $input.first().json;                 // Error Trigger の出力
const cfg = $('Config').first().json;          // Error Workflow 自身の Config（D20）
const lang = cfg.LANG === 'en' ? 'en' : 'ja';
const m = cfg.MESSAGES && cfg.MESSAGES[lang] && cfg.MESSAGES[lang].error_notice;    // shared/messages.*.json の error_notice
if (!m) throw new Error(`Config.MESSAGES.${lang}.error_notice is missing`);          // Config の誤りは隠さず失敗させる（§2.5）
const vars = {
  workflow_name: str(e.workflow?.name),
  last_node: str(e.execution?.lastNodeExecuted) || str(e.trigger?.error?.node?.name) || '(trigger)',
  message: str(e.execution?.error?.message) || str(e.trigger?.error?.message) || 'unknown error',
  execution_url: str(e.execution?.url) || '(not saved)',               // 実行が保存されていない（トリガー失敗等）ときは URL が無い
};
const title = fill(m.title, vars);
const body_text = fill(m.body, vars);
return [{ json: { title, body_text,
  slack_blocks: [{ type: 'header', text: { type: 'plain_text', text: title.slice(0, 150) } },       // header text ≤ 150 文字
                 { type: 'section', text: { type: 'mrkdwn', text: body_text.slice(0, 2900) } }],    // section text ≤ 3,000 文字
  line_text: body_text.slice(0, 4900), chatwork_text: body_text }, pairedItem: { item: 0 } }];
