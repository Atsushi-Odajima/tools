// Match Invoices — n8n Code node (JavaScript, Run Once for All Items). DESIGN.md §6.7 / D07–D13 / D18 / D28.
// The matching core. Input: $input.first().json = the ONE item emitted by Normalize Payer
//   { source, file_name, ignored_withdraw, warnings, txns (with txn_id / payer_name_norm), invoices (with _names), existing }.
// Rules (auto-confirm only 1, 2, 3a, 3b, 3c):
//   1 name+amount (auto) / 2 amount only, one candidate (amount_only) / 3a fee in FEE_SET, one name (fee_deducted)
//   3b unique 2–3 invoice subset of one payer summing to the amount (combined) / 3c amount < remaining, one name (partial, auto)
//   3d overpaid → ambiguous, never confirmed / 4 several candidates → ambiguous / 5 nothing → unmatched.
// Output (single output, split later by Route Match Results on _kind):
//   { _kind: 'invoice_update', invoice_id, status, paid_amount, paid_date, matched_txn_ids, match_confidence, fee_deducted }  (one per invoice, aggregated)
//   { _kind: 'txn_row', <every transactions column of shared/sheets-schema.md> }
//   { _kind: 'summary', date, source, file_name, n, a, b, c, rematched, skipped_existing, skipped_duplicate_in_batch, ignored_withdraw,
//     auto[], needs_review[], ambiguous[], unmatched[], warnings[] }
// Idempotency: txn_ids already in `existing` are skipped (R09); a txn_id already recorded in some invoice's `matched_txn_ids`
// (Update Invoices succeeded but Upsert Transactions failed on a previous run) is not applied again — only its ledger row is
// (re)written (D32); duplicates inside one batch are skipped and counted (D13); on the schedule run only existing
// unmatched / ambiguous rows are re-matched and written back only when changed (D10).
// Shared helpers toInt / num / str (every Code node) and splitCsvList / uniq (also in Normalize Payer) are byte-identical to DESIGN.md §6.1.

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
const splitCsvList = (s) => str(s).split(/[,、，]/).map((x) => x.trim()).filter(Boolean);
const uniq = (arr) => [...new Set(arr)];

// 最長共通部分文字列の長さ（候補スコア用。名義は 10〜20 文字なので O(n*m) で十分）
function lcsLength(a, b) {
  let best = 0;
  const prev = new Array(b.length + 1).fill(0);
  for (let i = 1; i <= a.length; i++) {
    let diagonal = 0;
    for (let j = 1; j <= b.length; j++) {
      const tmp = prev[j];
      prev[j] = a[i - 1] === b[j - 1] ? diagonal + 1 : 0;
      if (prev[j] > best) best = prev[j];
      diagonal = tmp;
    }
  }
  return best;
}

// ---- 名義照合（完全一致／包含。短い方が NAME_MIN_CONTAINS 文字以上）----
function nameRank(payerNorm, inv, cfg) {
  if (!payerNorm) return 0;
  let rank = 0;
  const minContains = num(cfg.NAME_MIN_CONTAINS) || 3;
  for (const name of inv._names || []) {
    if (name === payerNorm) return 3;
    const shorter = Math.min(name.length, payerNorm.length);
    if (shorter >= minContains && (payerNorm.includes(name) || name.includes(payerNorm))) rank = Math.max(rank, 2);
    else if (lcsLength(name, payerNorm) >= 2) rank = Math.max(rank, 1);   // 候補提示用の弱い類似（突合には使わない）
  }
  return rank;
}
const nameMatch = (payerNorm, inv, cfg) => nameRank(payerNorm, inv, cfg) >= 2;

// ---- 3b：byName の 2〜3 件の部分集合で remaining の合計 == amount のもの（全列挙。件数が多いときは due_date 昇順で先頭 12 件に制限）----
function subsetsSummingTo(list, target, minK, maxK) {
  const cands = [...list].sort((a, b) => str(a.due_date).localeCompare(str(b.due_date)) || a.invoice_id.localeCompare(b.invoice_id)).slice(0, 12);
  const hits = [];
  const walk = (start, chosen, sum) => {
    if (chosen.length >= minK && sum === target) hits.push([...chosen]);
    if (chosen.length === maxK || sum >= target) return;                     // remaining > 0 なので枝刈り可
    for (let i = start; i < cands.length; i++) walk(i + 1, [...chosen, cands[i]], sum + cands[i].remaining);
  };
  walk(0, [], 0);
  return hits;
}

// ---- 候補スコア（suggested_invoice_ids 上位 3 件）----
// score = nameRank * 10 + amountProximity * 9  … 名義の段階（3 完全 / 2 包含 / 1 部分共通 / 0）が常に金額近似より優先
// amountProximity = 1 - min(1, |remaining - amount| / max(remaining, amount))   … 1.0 = 同額
// withThreshold=true（未消込）のときは nameRank >= 1 または amountProximity >= 0.9（差 10% 以内）の請求だけを候補にする
function rankCandidates(txn, invs, cfg, withThreshold) {
  return invs.map((inv) => {
    const nr = nameRank(txn.payer_name_norm, inv, cfg);
    const diff = Math.abs(inv.remaining - txn.amount);
    const prox = 1 - Math.min(1, diff / Math.max(inv.remaining, txn.amount, 1));
    return { inv, nr, prox, diff, score: nr * 10 + prox * 9 };
  })
  .filter((x) => !withThreshold || x.nr >= 1 || x.prox >= 0.9)
  .sort((x, y) => y.score - x.score || x.diff - y.diff || str(x.inv.due_date).localeCompare(str(y.inv.due_date)) || x.inv.invoice_id.localeCompare(y.inv.invoice_id))
  .slice(0, 3)
  .map((x) => ({ invoice_id: x.inv.invoice_id, remaining: x.inv.remaining, score: Math.round(x.score * 100) / 100 }));
}

// ---- 本体 ----
function matchInvoices(newTxns, invoices, existingRows, cfg, ctx) {
  const today = ctx.now.toFormat('yyyy-MM-dd');
  const nowStr = ctx.now.toFormat("yyyy-MM-dd'T'HH:mm:ssZZ");          // ISO 8601 + JST オフセット（sheets-schema.md の datetime）例 2026-09-23T09:05:12+09:00
  const feeSet = (Array.isArray(cfg.FEE_SET) ? cfg.FEE_SET : []).map(num);   // DECISION: Config の FEE_SET は数値化してから比較（"220" と書かれても効く）

  const summary = { date: today, source: ctx.source, file_name: ctx.file_name, n: 0, a: 0, b: 0, c: 0, rematched: 0,
                    skipped_existing: 0, skipped_duplicate_in_batch: 0, ignored_withdraw: num(ctx.ignored_withdraw),
                    auto: [], needs_review: [], ambiguous: [], unmatched: [], warnings: [...(ctx.warnings || [])] };

  // 台帳の整形：open = currency が JPY（空欄は JPY 扱い）かつ status ∈ {unpaid, partial} かつ remaining > 0。_names は Normalize Payer 済み
  const open = invoices
    .map((i) => ({ ...i, invoice_id: str(i.invoice_id), status: str(i.status).toLowerCase(),
                   amount: num(i.amount), paid_amount: num(i.paid_amount), fee_deducted: num(i.fee_deducted) }))
    .filter((i) => i.status === 'unpaid' || i.status === 'partial')
    .filter((i) => {                                                     // sheets-schema.md：01 は JPY のみ。他通貨は対象外にして警告（D28）
      const c = str(i.currency).toUpperCase();
      if (c && c !== 'JPY') { summary.warnings.push({ type: 'non_jpy_invoice', invoice_id: i.invoice_id, currency: c }); return false; }
      return true;
    })
    .map((i) => ({ ...i, remaining: i.amount - i.paid_amount }))
    .filter((i) => i.remaining > 0);

  const existingById = new Map(existingRows.map((r) => [str(r.txn_id), r]));
  // D32：請求側の matched_txn_ids に既に記録された txn_id → 入金は適用済み（前回 Update Invoices 成功・Upsert Transactions 失敗）。
  // 再適用すると同じ入金が同一名義の別請求に消し込まれるため、台帳行だけを書き直して skip する
  const appliedTo = new Map();                  // txn_id → [invoice_id, …]
  for (const inv of invoices) for (const id of splitCsvList(inv.matched_txn_ids)) appliedTo.set(id, [...(appliedTo.get(id) || []), str(inv.invoice_id)]);
  const consumed = new Set();                    // この実行で消費した invoice_id（全額・一部を問わず）
  const invoiceUpdates = new Map();              // invoice_id → 更新行（集約）
  const txnRows = [];

  // 処理キュー：新規（冪等チェック済み）＋ Schedule 経路なら既存の unmatched / ambiguous
  const queue = []; const seen = new Set();
  for (const t of newTxns) {
    if (existingById.has(t.txn_id)) { summary.skipped_existing++; continue; }          // R09：既存は skip
    if (seen.has(t.txn_id)) { summary.skipped_duplicate_in_batch++; continue; }        // D13：同一実行内の重複
    if (appliedTo.has(t.txn_id)) {                                                       // D32：請求に適用済み → 台帳行の修復のみ
      txnRows.push({ ...txnRowBase(t, nowStr), matched_invoice_ids: appliedTo.get(t.txn_id).join(','), status: 'matched', suggested_invoice_ids: '' });
      summary.skipped_existing++; seen.add(t.txn_id); continue;
    }
    seen.add(t.txn_id); queue.push({ txn: t, isNew: true, prev: null });
  }
  if (ctx.source === 'schedule') {                                                       // D10：再突合は Schedule のみ
    for (const r of existingRows) {
      const st = str(r.status).toLowerCase();
      if (st !== 'unmatched' && st !== 'ambiguous') continue;                          // matched / ignored は対象外
      queue.push({ txn: rowToTxn(r), isNew: false, prev: r });
    }
  }

  for (const { txn, isNew, prev } of queue) {
    const avail = open.filter((i) => !consumed.has(i.invoice_id));
    const byAmt = avail.filter((i) => i.remaining === txn.amount);
    const byName = avail.filter((i) => nameMatch(txn.payer_name_norm, i, cfg));
    const both = byAmt.filter((i) => byName.includes(i));
    let r;
    if (both.length === 1) {                                                       // 1. 名義・金額一致
      r = full([both[0]], 'auto', 0);
    } else if (both.length >= 2) {                                                 // 4. 同額・同名義が複数
      r = ambiguous(both, 'multiple_full_matches');
    } else if (byAmt.length === 1 && byName.length === 0) {                         // 2. 金額のみ一致・候補1
      r = full([byAmt[0]], 'amount_only', 0);
    } else if (byAmt.length >= 2 && byName.length === 0) {                          // 4. 同額請求が複数・名義不一致（R06）
      r = ambiguous(byAmt, 'same_amount_multiple');
    } else if (byAmt.length === 0) {                                               // 3. 金額一致なし
      if (byName.length === 1) {
        const inv = byName[0]; const fee = inv.remaining - txn.amount;
        if (feeSet.includes(fee)) r = full([inv], 'fee_deducted', fee);              // 3a. 手数料差引（名義1件）
        else if (txn.amount < inv.remaining) r = partial(inv);                      // 3c. 一部入金
        else r = ambiguous([inv], 'overpaid');                                      // 3d. 超過 → 自動確定しない（D07）
      } else if (byName.length >= 2) {
        const combos = subsetsSummingTo(byName, txn.amount, 2, 3);
        if (combos.length === 1) r = full(combos[0], 'combined', 0);                // 3b. 合算（一意のときだけ）
        else r = ambiguous(byName, combos.length > 1 ? 'multiple_combinations' : 'name_multiple');   // 4.
      } else {
        r = unmatched();                                                            // 5. 候補なし
      }
    } else {                                                                       // 4. 金額一致と名義一致が別の請求を指す
      r = ambiguous(uniq([...byAmt, ...byName]), 'amount_name_conflict');
    }
    apply(r, txn, isNew, prev);
  }

  return { invoiceUpdates: [...invoiceUpdates.values()], txnRows, summary };

  // ---- 判定結果の生成 ----
  function full(invs, confidence, fee) { return { kind: 'matched', invoices: invs, confidence, fee }; }
  function partial(inv) { return { kind: 'partial', invoices: [inv], confidence: 'auto', fee: 0 }; }
  function ambiguous(cands, reason) { return { kind: 'ambiguous', candidates: cands, reason }; }
  function unmatched() { return { kind: 'unmatched' }; }

  // ---- 適用：invoice 更新行・txn 行・サマリ ----
  // DECISION (T07 / R18 note): a・b・c は新規 txn だけを数え、n = a + b + c を保つ（D11「新規のみ」）。再突合で matched になった既存行は
  //   rematched にだけ数え、明細（auto / needs_review）には載せる。変化のない既存の unmatched / ambiguous は書き戻さず明細にも載せない。
  //   候補だけが変わった既存行は書き戻し、明細にも載せる（人が見る材料）。
  function apply(r, txn, isNew, prev) {
    const line = { txn_date: txn.txn_date, payer_raw: txn.payer_name_raw, amount: txn.amount, source: txn.source };
    const importedAt = prev ? str(prev.imported_at) : nowStr;
    if (isNew) summary.n++;

    if (r.kind === 'matched' || r.kind === 'partial') {
      const ids = [];
      for (const inv of r.invoices) {
        const add = r.confidence === 'combined' ? inv.remaining : txn.amount;      // 合算は各請求の残額を充当
        const paid = inv.paid_amount + add;
        const status = r.kind === 'partial' ? 'partial' : 'paid';                  // fee_deducted は残額-手数料=入金なので paid
        const prevUpd = invoiceUpdates.get(inv.invoice_id);                        // 同一実行で 2 回目は来ない（consumed）が念のため集約
        invoiceUpdates.set(inv.invoice_id, {
          invoice_id: inv.invoice_id, status, paid_amount: paid, paid_date: txn.txn_date,
          matched_txn_ids: uniq([...splitCsvList(prevUpd ? prevUpd.matched_txn_ids : inv.matched_txn_ids), txn.txn_id]).join(','),
          match_confidence: r.confidence, fee_deducted: r.confidence === 'fee_deducted' ? r.fee : inv.fee_deducted });
        consumed.add(inv.invoice_id);                                              // D09：以後の txn からは見えない
        ids.push(inv.invoice_id);
      }
      txnRows.push({ ...txnRowBase(txn, importedAt), matched_invoice_ids: ids.join(','), status: 'matched', suggested_invoice_ids: '' });
      const detail = { ...line, invoice_ids: ids, reason: r.kind === 'partial' ? 'partial' : r.confidence, fee: r.fee,
                       remaining_after: r.kind === 'partial' ? r.invoices[0].remaining - txn.amount : 0 };
      if (r.confidence === 'auto') { if (isNew) summary.a++; summary.auto.push(detail); }       // 規則 1・3c
      else { if (isNew) summary.b++; summary.needs_review.push(detail); }                       // 規則 2・3a・3b → 要確認
      if (!isNew) summary.rematched++;
      return;
    }

    // ambiguous / unmatched：invoice は書かない
    const cands = r.kind === 'ambiguous' ? rankCandidates(txn, r.candidates, cfg, false) : rankCandidates(txn, avail(), cfg, true);
    const suggested = cands.map((c) => c.invoice_id).join(',');
    const status = r.kind;
    const detail = { ...line, reason: r.reason || 'no_candidate', candidates: cands.map((c) => ({ invoice_id: c.invoice_id, remaining: c.remaining })) };
    const changed = isNew || str(prev.status).toLowerCase() !== status || str(prev.suggested_invoice_ids) !== suggested;
    if (changed) {
      txnRows.push({ ...txnRowBase(txn, importedAt), matched_invoice_ids: '', status, suggested_invoice_ids: suggested });   // 既存行は変化があるときだけ書く
    }
    if (isNew) summary.c++;
    if (changed) (status === 'ambiguous' ? summary.ambiguous : summary.unmatched).push(detail);
    function avail() { return open.filter((i) => !consumed.has(i.invoice_id)); }
  }

  function txnRowBase(txn, importedAt) {
    return { txn_id: txn.txn_id, source: txn.source, txn_date: txn.txn_date, payer_name_raw: txn.payer_name_raw,
             payer_name_norm: txn.payer_name_norm, amount: txn.amount, memo: txn.memo, imported_at: importedAt };
  }
  function rowToTxn(r) {           // transactions の既存行 → txn（再突合用。payer_name_norm は Normalize Payer が補完済み）
    return { txn_id: str(r.txn_id), source: str(r.source), txn_date: str(r.txn_date), payer_name_raw: str(r.payer_name_raw),
             payer_name_norm: str(r.payer_name_norm), amount: num(r.amount), memo: str(r.memo) };
  }
}

// ---- 入力 ----
const cfg = $('Config').first().json;
const now = $now.setZone(cfg.TZ);                                        // DECISION: DateTime.now().setZone(TZ) と同値（A12）。$now は単体実行でも固定できる
const data = $input.first().json;                                        // Normalize Payer の 1 アイテム

const result = matchInvoices(data.txns || [], data.invoices || [], data.existing || [], cfg, {
  now, source: data.source, warnings: data.warnings, ignored_withdraw: data.ignored_withdraw, file_name: data.file_name });
return [
  ...result.invoiceUpdates.map((u) => ({ json: { _kind: 'invoice_update', ...u }, pairedItem: { item: 0 } })),
  ...result.txnRows.map((r) => ({ json: { _kind: 'txn_row', ...r }, pairedItem: { item: 0 } })),
  { json: { _kind: 'summary', ...result.summary }, pairedItem: { item: 0 } },
];
