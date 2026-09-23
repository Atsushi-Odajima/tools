#!/usr/bin/env python3
"""P3 pins for g3-schedule-error (CASES R18 / R19 / R21 / R22). Derived from the existing pins only; make_pins.py and its files are not touched.
JA: 既存 pin（drive / schedule / schedule-rematch / error-handler）から派生させる。`R18-bank-A-invoice-updates.json` は bank_A を 1 回流した実行の
    `invoice_update` 8 件（`_kind` 除去。ローカル n8n 実行 146）で、seed に適用して「A 反映済みの invoices シート」を作る。
EN: `R18-bank-A-invoice-updates.json` holds the 8 `invoice_update` items of a first bank_A run (local execution 146); applied to the seed
    they give the "invoices sheet after A" that CASES R18 / R19 require (the ledger rows come from `schedule-rematch.pin.json`).
usage: PYTHONDONTWRITEBYTECODE=1 python3 tests/pins/make_pins_g3_schedule_error.py
"""
import copy, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
def load(name):
    with open(os.path.join(HERE, name), encoding='utf-8') as f:
        return json.load(f)
drive, schedule, rematch, errh = load('drive.pin.json'), load('schedule.pin.json'), load('schedule-rematch.pin.json'), load('error-handler.pin.json')
updates = load('R18-bank-A-invoice-updates.json')

# invoices after bank_A: seed (schedule.pin.json Read Invoices) + the 8 invoice_update items applied on invoice_id
inv_after_a = copy.deepcopy(schedule['Read Invoices'])
by_id = {u['invoice_id']: u for u in updates}
for it in inv_after_a:
    u = by_id.get(it['json']['invoice_id'])
    if u:
        it['json'].update({k: v for k, v in u.items() if k != 'invoice_id'})
assert sum(1 for it in inv_after_a if it['json']['status'] in ('paid', 'partial')) == 8 + sum(1 for it in schedule['Read Invoices'] if it['json']['status'] in ('paid', 'partial'))
# ledger after bank_A: transactions.seed + the 11 txn_row items of the first run (as stored in schedule-rematch.pin.json)
ledger_after_a = copy.deepcopy(rematch['Read Transactions'])
assert len(ledger_after_a) == 12
inv021 = copy.deepcopy(rematch['Read Invoices'][-1])          # the buyer's new INV-2026-021 (66,000 JPY, alias ミホンシヨウカイ)
assert inv021['json']['invoice_id'] == 'INV-2026-021'

def with_triggers(pin, **flags):
    p = copy.deepcopy(pin)
    for it in p['Config']:
        it['json']['TRIGGERS_ENABLED'] = {**it['json']['TRIGGERS_ENABLED'], **flags}
    return p

pins = {
    # R19: schedule right after A, nothing changed → summary only, Build Notification []
    'R19-schedule-no-change.pin.json': {**copy.deepcopy(schedule), 'Read Invoices': inv_after_a, 'Read Transactions': ledger_after_a},
    # R18: same state + INV-2026-021 registered → 2026-09-11|66000|ミホンシヨウカイ| becomes matched, rematched = 1, no other txn_row
    'R18-schedule-rematch-after-A.pin.json': {**copy.deepcopy(schedule), 'Read Invoices': inv_after_a + [inv021], 'Read Transactions': ledger_after_a},
    # R22: TRIGGERS_ENABLED.drive = false with the Drive trigger / schedule = false with the Schedule trigger (gmail = false is gmail-disabled.pin.json)
    'R22-drive-disabled.pin.json': with_triggers(drive, drive=False),
    'R22-schedule-disabled.pin.json': with_triggers(schedule, schedule=False),
}
# R21: Error Trigger item of the *trigger error* shape (n8n docs "Error data" → trigger), same Config as error-handler.pin.json
trig_err = {'trigger': {'error': {'context': {}, 'name': 'WorkflowActivationError',
                                  'cause': {'message': 'Poll failed: invalid_grant', 'stack': 'Stacktrace'},
                                  'timestamp': 1790150000000, 'message': 'Poll failed: invalid_grant',
                                  'node': {'parameters': {}, 'id': 'trigger-node-id', 'name': 'Watch Drive Folder',
                                           'type': 'n8n-nodes-base.googleDriveTrigger', 'typeVersion': 1, 'position': [0, 0]}},
                        'mode': 'trigger'},
            'workflow': {'id': '1', 'name': 'Example Trigger Workflow'}}
ecfg = {k: v for k, v in errh['Config'][0]['json'].items() if k not in ('execution', 'workflow')}
pins['R21-trigger-error.pin.json'] = {'Catch Workflow Error': [{'json': trig_err}], 'Config': [{'json': {**trig_err, **ecfg}}]}

for name, pin in pins.items():
    with open(os.path.join(HERE, name), 'w', encoding='utf-8') as f:
        json.dump(pin, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('wrote', name, {k: len(v) for k, v in pin.items()})
