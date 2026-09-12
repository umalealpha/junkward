# Payroll → GL Posting — Tasks

Sequential build plan. Each task is a single commit unit. Check off as you go.

## Phase 1 — Schema & migrations

- [ ] **T1.1** Add `PAYROLL` to `JournalEntry.JournalType` choices in `ledger/models.py`. Add migration `ledger/migrations/00XX_journaltype_payroll.py`.
- [ ] **T1.2** Add `journal_entry` FK (nullable, PROTECT, related_name=`payroll_periods`) to `PayrollPeriod` in `payroll/models.py`.
- [ ] **T1.3** Add `POSTED` status to `PayrollPeriod.Status` choices (between APPROVED and PAID).
- [ ] **T1.4** Generate migration `payroll/migrations/0004_payrollperiod_journal_entry_status_posted.py` covering both T1.2 and T1.3. Verify `python manage.py makemigrations --dry-run` shows clean state after.
- [ ] **T1.5** Run `python manage.py migrate` against the dev DB. Verify no rows broken (no historic POSTED periods).

## Phase 2 — Permissions & groups

- [ ] **T2.1** Create `payroll/management/commands/setup_payroll_groups.py` — idempotently creates `payroll_poster` Group. Pattern: mirror existing `setup_employees.py`.
- [ ] **T2.2** Implement `_can_post_payroll(user)` and `_can_reverse_payroll(user)` in new file `payroll/services.py`.

## Phase 3 — Validation helpers

- [ ] **T3.1** Implement `_validate_component_mappings(period)` in `payroll/services.py`. Returns `dict[component_id → Account]` or raises ValidationError with full list of missing component codes.
- [ ] **T3.2** Implement `_aggregate_lines_by_component(period)` → `dict[component_id → Decimal]`.
- [ ] **T3.3** Unit tests for both helpers: `payroll/tests/test_services_helpers.py`.

## Phase 4 — Posting service

- [ ] **T4.1** Implement `post_payroll_period(period, user)` in `payroll/services.py` per algorithm in design.md §"Posting algorithm".
- [ ] **T4.2** Wrap in `@transaction.atomic`. Use `select_for_update` on the period.
- [ ] **T4.3** Call `je.post(user=user)` at the end — this is the balance-validation gate.
- [ ] **T4.4** Write `AuditLog` entry with JE reference.

## Phase 5 — Reversal service

- [ ] **T5.1** Implement `reverse_payroll_period(period, user, reason)` per algorithm in design.md §"Reversal algorithm".
- [ ] **T5.2** Guard: refuse if any payslip in period is `PAID`. Guard: CFO group only.
- [ ] **T5.3** AuditLog with both JE references.

## Phase 6 — Tests

- [ ] **T6.1** Write `payroll/tests/test_gl_posting.py` covering all 10 cases in design.md §"Tests" table.
- [ ] **T6.2** Add factory class if missing: `payroll/tests/factories.py`.
- [ ] **T6.3** Run `python manage.py test payroll.tests.test_gl_posting -v 2` — all green.
- [ ] **T6.4** Run full test suite `python manage.py test` — no regressions in billing, procurement, ledger.

## Phase 7 — Reconciliation command

- [ ] **T7.1** Create `payroll/management/commands/reconcile_payroll_period.py`. Args: `--period <name>`. Computes 3 invariants from NFR-2. Exit 0 on match, 1 on mismatch.
- [ ] **T7.2** Smoke-test against the dev DB with a manually-posted period.

## Phase 8 — Admin / API surface

- [ ] **T8.1** Add `post_to_gl` admin action on `PayrollPeriodAdmin` (calls `post_payroll_period` and surfaces errors as admin messages).
- [ ] **T8.2** Add `reverse_gl_post` admin action (CFO-visible only — check user.groups in `get_actions`).
- [ ] **T8.3** Add API endpoints `POST /payroll/api/periods/{id}/post-gl/` and `POST /payroll/api/periods/{id}/reverse-gl/`. Wire via `payroll/api_views.py`. Both require auth.

## Phase 9 — Frontend (lightweight)

- [ ] **T9.1** Add "Post to GL" button on the payroll period detail page (frontend route TBD — likely `frontend/app/payroll/periods/[id]/page.tsx`). Disabled unless `status == APPROVED && user has perm`.
- [ ] **T9.2** Show the JE entry number once posted, with link to ledger.
- [ ] **T9.3** Show "Reverse GL post" action for CFO when `status == POSTED`.

## Phase 10 — Documentation & CFO walkthrough

- [ ] **T10.1** Update `CLAUDE.md` to mention payroll GL posting in the Payroll section.
- [ ] **T10.2** Write a 1-page CFO runbook: how to map components to accounts, how to post, how to reverse. Save as `docs/runbooks/payroll-gl-posting.md`.
- [ ] **T10.3** Demo run on the dev DB with a real April 2026 payroll period (CFO sign-off before merging).

## Phase 11 — Ship

- [ ] **T11.1** Open PR from `feat/payroll-gl-posting-57` → `main`. Title: `feat(payroll): post payroll periods to the GL (#57)`. Link issue #57.
- [ ] **T11.2** CI green, CFO review.
- [ ] **T11.3** Squash-merge to main.
- [ ] **T11.4** Deploy to `omni.alphadirect.co.bw` via AWS CloudShell + EC2 Instance Connect (per CFO standing instruction "never leave pending — push to prod"). Run migrations on prod DB.
- [ ] **T11.5** Run `setup_payroll_groups` on prod. Assign initial members of `payroll_poster` group via Django admin.
- [ ] **T11.6** Close issue #57 with reference to the deploy commit.

## Definition of Done

A real April 2026 payroll period in prod can be:
1. Approved by HR
2. Posted to the GL by a `payroll_poster`
3. Visible in the Trial Balance as DR 6100 + CR 2150 + CR 2160 (and component-specific liabilities for deductions)
4. Reversed by the CFO if needed, before any payslip is marked PAID
5. Reconciled via `manage.py reconcile_payroll_period --period "April 2026"` returning exit 0

All 11 phases delivered. Issue #57 closed. Steering rule 1 honoured for payroll.
