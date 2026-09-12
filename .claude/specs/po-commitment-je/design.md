# PO Commitment Journal Entry — Design

## Overview

Add encumbrance-style commitment accounting to procurement. On `cfo_approve`, post a balanced JE (`DR 1990 / CR 2199`) for the full PO value. On `post_grn`, post a pro-rata reversal **before** the existing GR/IR entry. On `cancel`, post a final reversal for the remaining value.

The trial balance therefore shows:
- **1990 Encumbered Purchase Commitments** (asset) — total approved-but-unreceived PO value
- **2199 Reserve for Encumbered Commitments** (liability) — same total, opposite sign

Both net to zero when all POs close cleanly.

## Module surface

Extend `procurement/services.py` (existing) — no new files.

### New service functions

```python
def _post_commitment_je(po: PurchaseOrder, user: User) -> JournalEntry: ...
def _reverse_commitment_for_received_lines(grn: GoodsReceiptNote, user: User) -> JournalEntry | None: ...
def _reverse_remaining_commitment(po: PurchaseOrder, user: User, reason: str) -> JournalEntry | None: ...
```

All prefixed `_` because they're called from `cfo_approve`, `post_grn`, `cancel` — never directly.

### New public function

```python
def build_open_commitments_report(as_of: date, company: Company | None = None) -> dict: ...
```

Lives in `reporting/reports.py`. Returns `{po_number, supplier_name, approved_at, total_committed_bwp, total_received_bwp, outstanding_bwp}` per open PO.

## Data model changes

### `PurchaseOrder` model

```python
commitment_journal_entry = models.ForeignKey(
    'ledger.JournalEntry',
    null=True, blank=True,
    on_delete=models.PROTECT,
    related_name='commitment_for_pos',
    help_text=(
        'The commitment JE created when this PO was CFO-approved. '
        'Cleared once all goods receipted or PO cancelled. '
        'See .claude/steering/erp-relationships.md rule 4.'
    ),
)
```

### `JournalEntry.JournalType` choices

Add two new choices:
```python
COMMITMENT          = 'commitment',          'Commitment'
COMMITMENT_REVERSAL = 'commitment_reversal', 'Commitment Reversal'
```

### Migration

`procurement/migrations/00XX_purchaseorder_commitment_journal_entry.py` — adds FK, nothing else.
`ledger/migrations/00XX_journaltype_commitment.py` — adds two new JournalType choices.

No backfill: existing approved POs have `commitment_journal_entry = NULL` and stay that way (per NFR-2).

### Chart of Accounts

`ledger/management/commands/setup_chart_of_accounts.py` — append two rows to the `ACCOUNTS` list:

```python
{'code': '1990', 'name': 'Encumbered Purchase Commitments', 'account_type': 'ASSET',
 'sub_type': 'commitment_reserve', 'is_active': True},
{'code': '2199', 'name': 'Reserve for Encumbered Commitments', 'account_type': 'LIABILITY',
 'sub_type': 'commitment_reserve', 'is_active': True},
```

Idempotent — command uses `get_or_create`. Existing seeded companies: rerun the command.

## Algorithms

### Commitment posting (called from `cfo_approve`)

```
_post_commitment_je(po, user):
    a1990 = Account.objects.get(code='1990', is_active=True)
    a2199 = Account.objects.get(code='2199', is_active=True)
    total_orig = po.total_amount      # PO currency
    total_bwp  = po.total_bwp          # frozen at submission

    je = JournalEntry.objects.create(
        entry_date    = po.cfo_approved_at.date(),
        description   = f"Commitment for PO {po.po_number}",
        journal_type  = JournalEntry.JournalType.COMMITMENT,
        source_type   = 'purchase_order',
        source_id     = po.pk,
        currency_code = po.currency_code,
        exchange_rate = po.exchange_rate,
        company       = po.company,
        created_by    = user,
        status        = JournalEntry.Status.DRAFT,
    )
    JournalEntryLine.objects.create(
        journal_entry=je, account=a1990,
        debit_amount=total_orig, credit_amount=ZERO,
        debit_bwp=total_bwp,    credit_bwp=ZERO,
    )
    JournalEntryLine.objects.create(
        journal_entry=je, account=a2199,
        debit_amount=ZERO,        credit_amount=total_orig,
        debit_bwp=ZERO,           credit_bwp=total_bwp,
    )
    je.post(user=user, _allow_direct=True)
    return je
```

### Integration into existing `cfo_approve`

```python
def cfo_approve(po, user):
    # ... existing guards unchanged ...
    po.cfo_approved_by = user
    po.cfo_approved_at = timezone.now()
    po.status = PurchaseOrder.Status.APPROVED
    po._allow_status_transition = True
    po.save(audit_user=user, audit_description=f"CFO-approved {po.po_number}")

    je = _post_commitment_je(po, user)
    po.commitment_journal_entry = je
    po.save(update_fields=['commitment_journal_entry'])

    AuditLog.objects.create(
        ...,
        new_values={'status': po.status, 'cfo_approved_by': str(user.pk),
                    'commitment_je': je.entry_number},
        ...
    )
    return po
```

### GRN-triggered reversal

```
_reverse_commitment_for_received_lines(grn, user) -> JournalEntry | None:
    po = grn.purchase_order
    if po.commitment_journal_entry is None:
        return None      # PO from before this feature shipped — skip

    reversal_value_bwp = sum(
        ln.quantity_received_now * ln.po_line.unit_price * po.exchange_rate
        for ln in grn.lines.all()
    )
    if reversal_value_bwp <= ZERO:
        return None

    reversal_value_orig = reversal_value_bwp / po.exchange_rate

    a1990 = Account.objects.get(code='1990', is_active=True)
    a2199 = Account.objects.get(code='2199', is_active=True)

    je = JournalEntry.objects.create(
        entry_date=grn.receipt_date,
        description=f"Commitment reversal on GRN {grn.grn_number}",
        journal_type=JournalEntry.JournalType.COMMITMENT_REVERSAL,
        source_type='grn', source_id=grn.pk,
        currency_code=po.currency_code, exchange_rate=po.exchange_rate,
        company=po.company, created_by=user,
        status=JournalEntry.Status.DRAFT,
    )
    JournalEntryLine.objects.create(je, a2199, debit=reversal_value_orig, debit_bwp=reversal_value_bwp)
    JournalEntryLine.objects.create(je, a1990, credit=reversal_value_orig, credit_bwp=reversal_value_bwp)
    je.post(user=user, _allow_direct=True)
    return je
```

### Integration into existing `post_grn`

In `procurement/services.py` `post_grn`, **after** GRN status validation, **before** the existing `je = JournalEntry.objects.create(... PURCHASES ...)`:

```python
_reverse_commitment_for_received_lines(grn, user)
```

This means the ledger sees: commitment reversal first, then the real expense entry. Net effect on TB:
- `1990 ↓`, `2199 ↓` (commitment closed for the received portion)
- DR Expense, CR GR/IR 2145 (existing entry, unchanged)

When the bill arrives and posts: CR Payables, DR GR/IR — closes 2145. Standard flow.

### Cancel-triggered reversal

```
_reverse_remaining_commitment(po, user, reason) -> JournalEntry | None:
    if po.commitment_journal_entry is None:
        return None

    received_bwp = sum(
        ln.quantity_received * ln.unit_price * po.exchange_rate
        for ln in po.lines.all()
    )
    remaining_bwp = po.total_bwp - received_bwp
    if remaining_bwp <= ZERO:
        return None

    # Same JE pattern as _reverse_commitment_for_received_lines,
    # but value = remaining, description references the cancel reason
    ...
```

Integrates into `cancel(po, user, reason)` just before `po.save(...)`.

## Permissions

Unchanged — already enforced by existing `cfo_approve` / `cancel` guards. The new commitment service functions are private (`_` prefix) and inherit the caller's authorisation.

## Open Commitments report

`reporting/reports.py::build_open_commitments_report(as_of, company=None)`:

```python
qs = PurchaseOrder.objects.filter(
    status__in=[Status.APPROVED, Status.PARTIALLY_RECEIVED],
    cfo_approved_at__date__lte=as_of,
).select_related('supplier', 'company')
if company:
    qs = qs.filter(company=company)

rows = []
for po in qs:
    received = sum(ln.quantity_received * ln.unit_price * po.exchange_rate for ln in po.lines.all())
    outstanding = po.total_bwp - received
    if outstanding > ZERO:
        rows.append({...})
return {'as_of': as_of, 'rows': rows, 'total_outstanding_bwp': sum(r['outstanding_bwp'] for r in rows)}
```

Exposed via:
- API: `GET /reporting/api/open-commitments/?as_of=2026-05-31&company=ADIC`
- CSV download: `GET /reporting/api/open-commitments/?format=csv`
- (Optional v2) frontend widget on CFO dashboard

## Reconciliation command

`procurement/management/commands/reconcile_po_commitments.py`:

For each open PO, computes the FR-8 invariant. Outputs a table:

```
PO         Approved    Total BWP   Received BWP   Expected Outstanding   Ledger Outstanding   Drift
PO-0421    2026-04-12  120,000.00     45,000.00            75,000.00            75,000.00     OK
PO-0422    2026-04-14  300,000.00          0.00           300,000.00           299,997.30  -2.70 ✘
...
```

Exit 0 if all OK, 1 if any drift.

## Tests

`procurement/tests/test_po_commitment_je.py` (new):

| Test | Asserts |
|------|---------|
| `test_cfo_approve_creates_commitment_je` | JE exists, lines DR 1990 / CR 2199, sum == po.total_bwp |
| `test_cfo_approve_populates_commitment_fk` | `po.commitment_journal_entry` set after save |
| `test_grn_post_reverses_commitment_pro_rata` | new JE with mirrored lines for received qty value |
| `test_grn_post_grir_entry_unchanged` | existing GR/IR JE still posted, total unaffected |
| `test_partial_grn_then_full_grn_closes_commitment` | sum of all reversals == po.total_bwp |
| `test_cancel_after_partial_receipt_reverses_remaining` | one final reversal JE for remaining value |
| `test_legacy_approved_po_grn_post_skips_reversal` | PO with NULL commitment_je → no commitment reversal JE |
| `test_commitment_je_rollback_on_save_failure` | force PO save error → commitment JE rolled back too |
| `test_open_commitments_report_basic` | report returns expected rows + totals |
| `test_reconcile_command_exit_codes` | clean state: exit 0; introduce drift: exit 1 |

`reporting/tests/test_open_commitments.py` — report query tests, isolated from service.

## Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| Accounts 1990/2199 not seeded in a target company | Migration triggers `setup_chart_of_accounts.py` rerun; reconcile command fails loudly |
| Legacy POs lack `commitment_journal_entry` FK | Guard in `_reverse_commitment_for_received_lines` returns early if None |
| FX rate drift between approval and GRN | Frozen `po.exchange_rate` used for reversal — commitments always net to zero in BWP |
| `po.total_bwp` could change post-approval (line edits) | Existing post-approval line-edit guards on `PurchaseOrder` already prevent this (status-immutability) |
| Misuse: someone manually edits a commitment JE | JE immutability guard (`Status.POSTED` is immutable in `ledger/models.py`) already blocks this |
| Backfill of historic POs requested later | Out of scope here. Separate `backfill_po_commitments` script can be designed in a v2 spec |

## Out of scope (deferred to v2)

- Backfill of historic open POs
- Per-cost-centre splits in the commitment JE
- Budget threshold alerts when total open commitments breach a planned ceiling
- Soft-commitment / requisition stage (Pre-PO encumbrance)
- Commitment ageing report (30/60/90 days approved-but-not-received)
