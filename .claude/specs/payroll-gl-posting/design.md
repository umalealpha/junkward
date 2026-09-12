# Payroll → GL Posting — Design

## Overview

Mirror the established `Invoice.post() → _create_journal_entry()` pattern from `billing/models.py:459-574`. Payroll uses `PayrollPeriod` as the post-level aggregate (one JE per period), with `PayslipLine`-derived totals fed into `JournalEntryLine`s.

## Module surface

New file: `payroll/services.py`

Public API:
```python
def post_payroll_period(period: PayrollPeriod, user: User) -> JournalEntry: ...
def reverse_payroll_period(period: PayrollPeriod, user: User, reason: str) -> JournalEntry: ...
def reconcile_payroll_period(period: PayrollPeriod) -> ReconciliationResult: ...
```

Internal helpers:
```python
def _validate_component_mappings(period: PayrollPeriod) -> list[Account]
def _aggregate_lines_by_component(period: PayrollPeriod) -> dict[PayslipComponent, Decimal]
def _build_journal_lines(je, totals, accounts) -> None
def _can_post_payroll(user) -> bool
def _can_reverse_payroll(user) -> bool
```

## Data model changes

### `PayrollPeriod` model — add fields + status choices

```python
class Status(models.TextChoices):
    OPEN     = 'open',     'Open'
    LOCKED   = 'locked',   'Locked'
    APPROVED = 'approved', 'Approved'
    POSTED   = 'posted',   'Posted to GL'     # NEW
    PAID     = 'paid',     'Paid'

journal_entry = models.ForeignKey(
    'ledger.JournalEntry',
    null=True, blank=True,
    on_delete=models.PROTECT,
    related_name='payroll_periods',
    help_text='The GL entry created when this period was posted. NULL if not yet posted.',
)
```

State machine:
- `OPEN → LOCKED → APPROVED → POSTED → PAID`
- Reverse: `POSTED → APPROVED` (CFO only)

### Migration
`payroll/migrations/0004_payrollperiod_journal_entry_and_status_posted.py`:
- AddField: `journal_entry`
- AlterField: `status` choices (adds `posted`)
- Data migration: no rows to backfill (no historic posts exist)

## Posting algorithm

```
post_payroll_period(period, user):
    @transaction.atomic
    1. Guard: period.status == APPROVED
       Guard: period.journal_entry is None
       Guard: _can_post_payroll(user)
    2. Lock period: select_for_update(of=('self',))
    3. Fetch all approved payslips for period: payslips = period.payslip_set.filter(status=APPROVED)
       Guard: payslips.exists()
    4. Validate component mappings (FR-3):
       - For each PayslipComponent referenced by any line in the period (excl COMPUTED_*)
       - Resolve posting_account_code → ledger.Account.objects.get(code=..., is_active=True)
       - Collect Account objects in dict {component_id: Account}
       - On any miss: raise ValidationError with all missing component codes
    5. Aggregate amounts:
       totals = {component_id: Decimal} from PayslipLine
       net_payable_total = sum(payslip.net_amount for payslip in payslips)
    6. Create JournalEntry (DRAFT):
       je = JournalEntry.objects.create(
           entry_date    = period.pay_date,
           description   = f"Payroll {period.period_name}",
           journal_type  = JournalEntry.JournalType.PAYROLL,   # need new choice
           source_type   = 'payroll_period',
           source_id     = period.pk,
           currency_code = period.company.functional_currency,
           exchange_rate = Decimal('1.0'),
           company       = period.company,
           created_by    = user,
           status        = JournalEntry.Status.DRAFT,
       )
    7. For each component with non-zero total:
         kind = component.kind
         if kind in {EARNING, EARNING_NON_TAXABLE, COMPANY_CONTRIBUTION}:
             JournalEntryLine(debit=total, credit=ZERO, account=accounts[component.id])
         elif kind in {EMPLOYEE_DEDUCTION, EMPLOYEE_PRETAX, TAX}:
             JournalEntryLine(debit=ZERO, credit=total, account=accounts[component.id])
         # COMPUTED_* excluded by step 4 already
    8. Final balancing line:
         salary_payable = Account.objects.get(code='2150', is_active=True)
         JournalEntryLine(debit=ZERO, credit=net_payable_total, account=salary_payable)
    9. je.post(user=user)   # validates DR==CR, sets posted_date
   10. period.status = POSTED
       period.journal_entry = je
       period.save()
   11. AuditLog: action=POST, table='PayrollPeriod', describes JE number
   12. Return je
```

### Why this balances

Standard double-entry payroll:
```
DR Salaries Expense (sum of EARNING + COMPANY_CONTRIBUTION components)
  CR PAYE Payable (sum of TAX components — e.g., paye_amount)
  CR Other Deductions Payable (sum of EMPLOYEE_DEDUCTION components)
  CR Salary Payable (net_amount total)
```

Identity: gross + employer contributions = PAYE + deductions + net pay. Because the system already enforces this on the Payslip via the COMPUTED_NET = gross − tax − deductions formula, the JE always balances when built from the same source data. The line 9 `je.post()` call catches any mathematical drift defensively.

## Reversal algorithm

```
reverse_payroll_period(period, user, reason):
    @transaction.atomic
    1. Guard: period.status == POSTED
       Guard: period.payslip_set.filter(status=PAID).exists() → ValidationError
       Guard: _can_reverse_payroll(user)  # CFO only
    2. original_je = period.journal_entry
    3. Create contra JE — mirror every line with DR/CR swapped
       JE description: f"Reversal of {original_je.entry_number}: {reason}"
       source_type='payroll_period_reversal', source_id=period.pk
    4. contra_je.post(user=user)
    5. period.status = APPROVED
       period.journal_entry = None
       period.save()
    6. AuditLog: action=REVERSE on PayrollPeriod, references both JEs
    7. Return contra_je
```

## Permissions

```python
def _can_post_payroll(user) -> bool:
    return (
        user.is_superuser or
        user.groups.filter(name__in=['payroll_poster', 'finance_manager', 'cfo']).exists()
    )

def _can_reverse_payroll(user) -> bool:
    return user.is_superuser or user.groups.filter(name='cfo').exists()
```

Group seeding: `payroll/management/commands/setup_payroll_groups.py` (new) idempotently creates `payroll_poster` group.

## Reconciliation command

`payroll/management/commands/reconcile_payroll_period.py`:
- Takes `--period <name>` arg
- For a posted period, computes 3 invariants (see NFR-2)
- Prints a table; exit 0 on all-match, exit 1 on any mismatch

## Tests

`payroll/tests/test_gl_posting.py` (new) — Django TestCase:

| Test | Asserts |
|------|---------|
| `test_post_balances_dr_cr` | JE lines DR sum == CR sum |
| `test_post_writes_period_journal_entry_fk` | period.journal_entry == created JE |
| `test_post_idempotent_raises` | second call raises ValidationError |
| `test_post_unmapped_component_raises` | ValidationError lists all missing codes |
| `test_post_skips_computed_components` | no JE line for COMPUTED_GROSS/NET/CTC |
| `test_post_excludes_unapproved_payslips` | a DRAFT payslip in same period is ignored |
| `test_reverse_creates_contra_je` | sum of original + contra == 0 per account |
| `test_reverse_blocked_if_any_payslip_paid` | ValidationError |
| `test_reverse_requires_cfo_group` | non-CFO raises PermissionError-ish ValidationError |
| `test_audit_log_created` | AuditLog row exists for POST and REVERSE |

Factory: `payroll/tests/factories.py` (extend if exists; create otherwise) — `PayrollPeriodFactory`, `PayslipFactory`, `PayslipLineFactory`.

## Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| `posting_account_code` blank on existing components | FR-3 gate; no post possible until CFO seeds them via admin |
| Race: two posts concurrent | `select_for_update` on the period row (step 2) |
| Account 2150 / 2160 not seeded in target company | Reconcile command run before first post; seeding via existing `setup_chart_of_accounts.py` |
| Adding `PAYROLL` to `JournalType` enum mid-deploy | Migration adds choice; existing JEs unaffected (additive) |
| Reversal abuse | CFO-only + AuditLog + reason mandatory + paid-payslip guard |

## Out of scope (deferred to v2)

- Per-department JE line splits (v1 batches by component only)
- Multi-currency payroll
- Automated bank-payment file generation post-JE
- Pension/medical aid auto-remittance workflows
