# PO Commitment Journal Entry — Tasks

Sequential build plan. Each task is a single commit unit.

## Phase 1 — Chart of Accounts & ledger schema

- [ ] **T1.1** Append `1990 Encumbered Purchase Commitments` (ASSET) and `2199 Reserve for Encumbered Commitments` (LIABILITY) to `ACCOUNTS` list in `ledger/management/commands/setup_chart_of_accounts.py`.
- [ ] **T1.2** Add `COMMITMENT` and `COMMITMENT_REVERSAL` to `JournalEntry.JournalType` choices in `ledger/models.py`.
- [ ] **T1.3** Migration `ledger/migrations/00XX_journaltype_commitment.py`.
- [ ] **T1.4** Rerun `python manage.py setup_chart_of_accounts` on dev DB; verify both accounts exist and are active.

## Phase 2 — Procurement schema

- [ ] **T2.1** Add `commitment_journal_entry` FK (nullable, PROTECT, related_name `commitment_for_pos`) to `PurchaseOrder` in `procurement/models.py`.
- [ ] **T2.2** Migration `procurement/migrations/00XX_purchaseorder_commitment_journal_entry.py`.
- [ ] **T2.3** Run `python manage.py migrate procurement` on dev DB.

## Phase 3 — Service: commitment posting

- [ ] **T3.1** Implement `_post_commitment_je(po, user)` in `procurement/services.py` per design.md §"Commitment posting".
- [ ] **T3.2** Wire into existing `cfo_approve(po, user)` — call after `po.save()`, save `po.commitment_journal_entry`, include JE number in `AuditLog`.
- [ ] **T3.3** Wrap in `@transaction.atomic` (already on `cfo_approve`).

## Phase 4 — Service: GRN-triggered reversal

- [ ] **T4.1** Implement `_reverse_commitment_for_received_lines(grn, user)` per design.md §"GRN-triggered reversal".
- [ ] **T4.2** Wire into existing `post_grn(grn, user)` — call before the existing PURCHASES JE creation.
- [ ] **T4.3** Handle the case where `po.commitment_journal_entry is None` (legacy approved POs from before this feature shipped) — return None, log info.

## Phase 5 — Service: cancel-triggered reversal

- [ ] **T5.1** Implement `_reverse_remaining_commitment(po, user, reason)` per design.md §"Cancel-triggered reversal".
- [ ] **T5.2** Wire into existing `cancel(po, user, reason)` — call before `po.save()`.

## Phase 6 — Tests

- [ ] **T6.1** Write `procurement/tests/test_po_commitment_je.py` covering the 10 cases in design.md §"Tests" table.
- [ ] **T6.2** Add test factories if missing: `procurement/tests/factories.py` — `PurchaseOrderFactory`, `PurchaseOrderLineFactory`, `GoodsReceiptNoteFactory`.
- [ ] **T6.3** Run `python manage.py test procurement.tests.test_po_commitment_je -v 2` — all green.
- [ ] **T6.4** Run full test suite `python manage.py test` — no regressions in billing/ledger/reporting.

## Phase 7 — Open Commitments report

- [ ] **T7.1** Implement `build_open_commitments_report(as_of, company=None)` in `reporting/reports.py`.
- [ ] **T7.2** Add API endpoint in `reporting/api_views.py`: `GET /reporting/api/open-commitments/`.
- [ ] **T7.3** CSV download support via `?format=csv`.
- [ ] **T7.4** Tests in `reporting/tests/test_open_commitments.py`.

## Phase 8 — Reconciliation command

- [ ] **T8.1** Create `procurement/management/commands/reconcile_po_commitments.py`. Args: `--company <code>` (optional, defaults to all). Computes FR-8 invariant for all open POs.
- [ ] **T8.2** Output: aligned table per design.md §"Reconciliation command".
- [ ] **T8.3** Exit 0 on clean, 1 on drift.
- [ ] **T8.4** Smoke-test against dev DB after seeding a few open POs.

## Phase 9 — Admin / API

- [ ] **T9.1** Show `commitment_journal_entry` as a read-only field on `PurchaseOrderAdmin`, with a link to the JE in admin.
- [ ] **T9.2** Add JE numbers in the PO API serializer (`procurement/serializers.py`): `commitment_je_number`, `commitment_reversal_je_numbers` (list).

## Phase 10 — Frontend (lightweight)

- [ ] **T10.1** Show "Outstanding commitment: BWP X" on the PO detail page (frontend route `frontend/app/procurement/po/[id]/page.tsx` or equivalent). Computed client-side from `po.total_bwp` minus sum-of-received-line-values.
- [ ] **T10.2** Add an "Open Commitments" report page under `frontend/app/reporting/` — table view + CSV download button. Wire to the new API endpoint.
- [ ] **T10.3** Add an "Open Commitments" tile to the CFO dashboard showing total BWP outstanding (optional v1 — skip if time-constrained).

## Phase 11 — Documentation & CFO walkthrough

- [ ] **T11.1** Update `CLAUDE.md` to document the commitment-accounting pattern in the Procurement section.
- [ ] **T11.2** Write a 1-page CFO runbook `docs/runbooks/po-commitments.md` — what the two new accounts mean, how to read the Open Commitments report, when to expect drift.
- [ ] **T11.3** Demo on dev DB: approve a PO → see TB lines → receive partial → see commitment shrink → cancel remainder → see commitment clear. CFO sign-off before final merge.

## Phase 12 — Ship

- [ ] **T12.1** Open PR from `feat/po-commitment-je-58` → `main`. Title: `feat(procurement): post commitment JE on PO approval (#58)`. Link issue #58.
- [ ] **T12.2** CI green, CFO review.
- [ ] **T12.3** Squash-merge to main.
- [ ] **T12.4** Deploy to `omni.alphadirect.co.bw` via AWS CloudShell + EC2 Instance Connect:
  1. Pull main on EC2
  2. Run `python manage.py migrate ledger procurement`
  3. Run `python manage.py setup_chart_of_accounts` for each tenant company
  4. Restart Gunicorn
  5. Verify via `python manage.py reconcile_po_commitments`
- [ ] **T12.5** Close issue #58 with the deploy commit hash.

## Definition of Done

A new PO approved in production:
1. Creates a balanced commitment JE visible in the Trial Balance
2. Reverses pro-rata when goods are receipted
3. Reverses the remainder when the PO is cancelled
4. Is visible on the Open Commitments report at any point
5. Reconciles cleanly via `reconcile_po_commitments`

All 12 phases delivered. Issue #58 closed. Steering rule 4 honoured.
