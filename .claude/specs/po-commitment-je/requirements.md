# PO Commitment Journal Entry — Requirements

**Closes:** [alpha-finance#58](https://github.com/alphadirectinsurance/alpha-finance/issues/58)

**Steering rule violated today:** Rule 4 — _"Every PO approval MUST create a GL commitment entry"_ (`.claude/steering/erp-relationships.md`).

## Business problem

When the CFO approves a PO, the company has a real legal commitment to spend that money. Today the GL hears about it only when goods are received (`post_grn` posts to the GR/IR clearing account). Between PO approval and goods receipt — sometimes weeks — the trial balance shows zero of these committed liabilities. The CFO cannot answer _"how much have I already committed to spend this month"_ from the ledger.

## Functional requirements

### FR-1 — Post a commitment JE when CFO approves a PO
On successful `cfo_approve(po, user)` the service must, in the same transaction, create a balanced `JournalEntry` with:
- **DR** _Encumbered Purchase Commitments_ (new asset account `1990`) — total `po.total_bwp`
- **CR** _Reserve for Encumbered Commitments_ (new liability account `2199`) — total `po.total_bwp`

JE attributes:
- `journal_type = COMMITMENT` (new choice on `JournalEntry.JournalType`)
- `source_type = 'purchase_order'`, `source_id = po.pk`
- `description = f"Commitment for PO {po.po_number}"`
- `currency_code = po.currency_code`, `exchange_rate = po.exchange_rate` (BWP totals computed once and frozen)

### FR-2 — Persist the FK on the PO
`PurchaseOrder` gains `commitment_journal_entry` FK (nullable, PROTECT, related_name `commitment_for_pos`). Populated on successful approval, cleared on full reversal.

### FR-3 — Reverse commitment on GRN receipt (pro-rata)
When `post_grn(grn, user)` runs, immediately before posting the existing GR/IR entry, the service must post a **partial reversal** of the commitment for the value of goods received:

- **DR** Reserve for Encumbered Commitments (2199) — `Σ (line.quantity_received_now × po_line.unit_price_bwp)`
- **CR** Encumbered Purchase Commitments (1990) — same amount

JE attributes: `journal_type=COMMITMENT_REVERSAL`, `source_type='grn'`, `source_id=grn.pk`, description `"Commitment reversal on GRN {grn.grn_number}"`.

The original GR/IR entry from `post_grn` is unchanged.

### FR-4 — Reverse remaining commitment on cancel/close
On `cancel(po, user, reason)` or any future `close(po, user, reason)`: post a contra JE for the remaining un-received commitment value:

- **DR** Reserve for Encumbered Commitments (2199) — `po.total_bwp - sum_already_reversed_bwp`
- **CR** Encumbered Purchase Commitments (1990) — same

Set `po.commitment_journal_entry = None` only after both forward and reversing entries are accounted for (audit trail preserved via JE source links, not the FK).

### FR-5 — Idempotency
Calling `cfo_approve` twice for the same PO must:
- Succeed the first time, creating one commitment JE
- Already blocked by existing status guard (`Status.PENDING_CFO_APPROVAL` check) — no additional work needed

Calling `post_grn` twice for the same GRN: already blocked by status guard on the existing implementation. Commitment reversal inherits that protection.

### FR-6 — Chart-of-Accounts seeding
The seed command `ledger/management/commands/setup_chart_of_accounts.py` must include:
- `1990 Encumbered Purchase Commitments` — `ASSET`, sub_type `commitment_reserve`
- `2199 Reserve for Encumbered Commitments` — `LIABILITY`, sub_type `commitment_reserve`

Both accounts are normally zero-balance in aggregate (commitments offset their reserves). The TB nets to zero on these two lines unless POs are open.

### FR-7 — Trial-balance presentation
`build_trial_balance` (`reporting/reports.py`) is **unchanged**. The two commitment accounts appear like any other accounts. A separate report `build_open_commitments_report(as_of_date)` shows POs with non-zero outstanding commitment value — _additive_, not replacing the TB.

### FR-8 — Reconciliation invariant
For every PO with `status in {APPROVED, PARTIALLY_RECEIVED}`:
`outstanding_commitment_bwp == po.total_bwp − Σ (received_line.quantity_received × line.unit_price × po.exchange_rate)`

A management command `reconcile_po_commitments` checks this invariant across all open POs and exits non-zero on any drift.

## Non-functional requirements

### NFR-1 — Atomicity
The commitment JE creation runs inside the same `@transaction.atomic` as `cfo_approve`. If JE creation fails, the PO approval is rolled back (PO stays in `PENDING_CFO_APPROVAL`).

### NFR-2 — Backward compatibility
Existing approved POs (status `APPROVED` or beyond, with no `commitment_journal_entry`) are **not** retroactively posted. v1 ships forward-only. A separate backfill script (out of scope) can be run later if CFO wants historic commitments reflected.

### NFR-3 — Performance
GRN-driven commitment reversal must not slow down `post_grn` measurably. Implementation does one extra JE creation per GRN — negligible.

### NFR-4 — Currency handling
Commitments are recorded in BWP only (using `po.total_bwp`, frozen at approval). Foreign-currency POs whose exchange rate changes between approval and GRN: the GRN-time reversal uses the **frozen** approval-time exchange rate so the commitment net-clears exactly. FX differences land in the regular GR/IR entry, unchanged.

## Out of scope

- Retroactive commitments for already-approved historic POs
- Per-cost-centre commitment splits (single line per JE for v1)
- Soft-commitment / requisition stage (Pre-PO commitments)
- Automatic alert when total open commitments breach a budget threshold (future enhancement)
- Multi-currency commitment recognition (frozen at approval rate for v1)

## Acceptance criteria

1. CFO approves a PO → trial balance shows `1990 ↑` and `2199 ↑` by `po.total_bwp`
2. GRN received for partial qty → `1990 ↓` and `2199 ↓` pro-rata; GR/IR posts unchanged
3. PO cancelled → remaining `1990` / `2199` exposure released
4. Open Commitments report shows the correct outstanding value at any point in time
5. `reconcile_po_commitments` returns exit 0 across all open POs after a fresh run of fixtures
6. Existing procurement tests still pass — no regressions
