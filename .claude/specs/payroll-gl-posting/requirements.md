# Payroll → GL Posting — Requirements

**Closes:** [alpha-finance#57](https://github.com/alphadirectinsurance/alpha-finance/issues/57)

**Steering rule violated today:** Rule 1 — _"Every form that creates a financial transaction MUST post to the GL"_ (`.claude/steering/erp-relationships.md`).

## Business problem

Payroll runs every month. `Payslip` rows are produced with `gross_amount`, `paye_amount`, `net_amount`. None of it ever reaches the General Ledger. Trial Balance is materially understated. External audit will fail.

## Functional requirements

### FR-1 — Post a payroll period to the GL
Given a `PayrollPeriod` with `status = APPROVED` and all its `Payslip`s in `status = APPROVED`,
when an authorised user invokes `post_payroll_period(period, user)`,
then exactly one `JournalEntry` (`journal_type = PAYROLL`, `source_type = 'payroll_period'`, `source_id = period.pk`) is created in DRAFT, balanced, then posted.

### FR-2 — Component-driven account routing
Each `PayslipComponent.posting_account_code` (already a field, currently blank) must resolve to a live `ledger.Account`. The posting service sums `PayslipLine.amount` across all approved payslips for the period, grouped by `PayslipComponent`, and:
- **EARNING, EARNING_NON_TAXABLE, COMPANY_CONTRIBUTION** components → **DEBIT** their posting account
- **EMPLOYEE_DEDUCTION, EMPLOYEE_PRETAX** components → **CREDIT** their posting account (third-party payable)
- **TAX** components → **CREDIT** their posting account (e.g., 2160 PAYE Payable)
- **COMPUTED_GROSS / COMPUTED_NET / COMPUTED_CTC** components → **SKIP** (subtotals, not journalisable)

Plus one balancing **CREDIT** to `2150 Salary Payable` for the total net amount across all payslips in the period.

### FR-3 — Configuration validation gate
Before any payroll period can post, every `PayslipComponent` referenced by at least one `PayslipLine` in the period (excluding COMPUTED_* kinds) must have a non-empty `posting_account_code` that resolves to an active `Account`. If any component is unmapped, `post_payroll_period` raises `ValidationError` listing every unmapped component. No partial post.

### FR-4 — Idempotency
Calling `post_payroll_period(period, user)` twice for the same period must:
- Succeed the first time, creating one JE
- Raise `ValidationError("Period {name} is already posted (JE: {entry_number})")` the second time
Achieved via a new `PayrollPeriod.journal_entry` FK + `status` transition to a new `POSTED` choice (after `APPROVED`, before `PAID`).

### FR-5 — Reversal
A posted period can be reversed by `reverse_payroll_period(period, user, reason)` which:
- Refuses if any payslip in the period is `PAID`
- Creates a contra `JournalEntry` (mirrored debits/credits)
- Sets `period.status = APPROVED`, clears `period.journal_entry`
- Records both operations in `AuditLog`

### FR-6 — Permissions
- `post_payroll_period`: requires user in group `payroll_poster` OR `finance_manager` OR `cfo`
- `reverse_payroll_period`: requires `cfo` (single-step authority — payroll reversal is a CFO-only act)
Pattern mirrors `procurement.services._can_approve_as_cfo`.

### FR-7 — Audit trail
Every post and reverse must:
- Create an `AuditLog` entry (`table='PayrollPeriod', action=POST or REVERSE`)
- Reference the JE entry number in the description
- Capture `user` (no system-attributed posts)

## Non-functional requirements

### NFR-1 — Atomicity
The entire post operation runs in `@transaction.atomic`. Any failure rolls back the period status, the JE, and all JE lines.

### NFR-2 — Reconciliation
A management command `manage.py reconcile_payroll_period <period_name>` must verify, for any posted period:
- Sum of JE debits == sum of approved-payslip earnings + employer contributions
- Sum of JE credits to PAYE Payable == sum of `Payslip.paye_amount`
- Sum of JE credits to Salary Payable == sum of `Payslip.net_amount`
Exits non-zero on any mismatch.

### NFR-3 — Multi-currency
v1 scope: BWP-only. Period currency is locked to `company.functional_currency`. Mixed-currency payroll is out of scope (no employees paid in non-BWP today per recon).

### NFR-4 — Cost-centre detail
v1 scope: All earnings post to the **single** account configured per component (no per-employee cost-centre breakdown in the JE). Department-level analytics live on the source `Payslip` and `Employee.department` fields, queryable via reports. v2 may split into per-department JE lines.

## Out of scope (explicit non-requirements)

- Per-employee individual JE per payslip (use period-level batch)
- Automatic bank payment file generation (separate feature — payroll → payments)
- Tax-filing exports (handled in `payroll/paye.py` already)
- Pension/medical aid third-party remittance workflows
- Mid-period rate changes / proration (handled in PayslipLine recompute)

## Acceptance criteria

A new payroll period can be created, populated, approved, and posted to the GL. The resulting JE balances. The Trial Balance for the period shows salary expense and PAYE/net-pay liabilities. Reversing the period removes those balances. All operations leave a full audit trail. Existing payslip / payroll-period workflows continue to work unchanged for unposted periods.
