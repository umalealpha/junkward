"""
payroll/loan_service.py

CFO directive 2026-05-24 — Payroll + HR upgrades pass, item #2.

`apply_loan_repayments(period)` walks every ACTIVE EmployeeLoan whose
`start_period.start_date` is on or before `period.start_date`, computes the
monthly amortisation (straight-line when annual_rate_pct == 0, otherwise
the standard PMT formula), and:

  1. Inserts (or updates) a LoanRepayment row for (loan, period) — idempotent.
  2. Materialises a PayslipLine on the employee's Payslip for `period`
     against component_code = 'LOAN_REPAYMENT' (created if missing).
  3. Decrements `loan.outstanding`; flips `status='paid'` when balance hits 0.

Idempotent — re-running with the same period is a no-op (the existing
LoanRepayment row short-circuits the loop). No GL writes happen here;
the existing GL posting service picks the LOAN_REPAYMENT PayslipLine up
like any other line on its next post.

Bible-check guard: payroll/ only. No ledger / reporting / billing imports.
"""

from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone


logger = logging.getLogger(__name__)

ZERO       = Decimal('0.00')
TWO_PLACES = Decimal('0.01')

LOAN_REPAYMENT_CODE = 'LOAN_REPAYMENT'


def _q(amount: Decimal) -> Decimal:
    """Round to 2 dp half-up (BWP convention)."""
    return amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _monthly_instalment(loan) -> Decimal:
    """Standard amortising payment per month.

    Straight-line when annual_rate_pct == 0:
        instalment = principal / term_months
    Otherwise standard PMT:
        i = rate/12; n = term_months
        instalment = principal * i / (1 - (1+i)^-n)
    """
    p   = Decimal(loan.principal or ZERO)
    n   = int(loan.term_months or 0)
    if n <= 0 or p <= 0:
        return ZERO

    apr = Decimal(loan.annual_rate_pct or ZERO)
    if apr == 0:
        return _q(p / Decimal(n))

    i = apr / Decimal('100') / Decimal('12')
    # (1+i)^-n via Decimal
    one_plus_i = Decimal('1') + i
    factor = one_plus_i ** (-n)
    instalment = p * i / (Decimal('1') - factor)
    return _q(instalment)


def _split_principal_interest(loan, instalment: Decimal) -> tuple[Decimal, Decimal]:
    """For a given instalment, split into (principal, interest) for THIS period."""
    apr = Decimal(loan.annual_rate_pct or ZERO)
    outstanding = Decimal(loan.outstanding or ZERO)
    if apr == 0:
        return (_q(min(instalment, outstanding)), ZERO)
    monthly_rate = apr / Decimal('100') / Decimal('12')
    interest_due = _q(outstanding * monthly_rate)
    principal_part = _q(instalment - interest_due)
    if principal_part > outstanding:
        principal_part = _q(outstanding)
    return (principal_part, interest_due)


def _ensure_loan_repayment_component():
    """Make sure a PayslipComponent with code=LOAN_REPAYMENT exists."""
    from .models import PayslipComponent
    comp, _ = PayslipComponent.objects.get_or_create(
        code=LOAN_REPAYMENT_CODE,
        defaults={
            'name':       'Loan Repayment',
            'kind':       PayslipComponent.Kind.EMPLOYEE_DEDUCTION,
            'sort_order': 80,
            'is_active':  True,
            'is_taxable': False,
        },
    )
    return comp


def _ensure_payslip(employee, period):
    """Get or create the (employee, period) payslip — DRAFT status."""
    from .models import Payslip
    payslip, _ = Payslip.objects.get_or_create(
        employee=employee, period=period,
        defaults={'company': getattr(employee, 'company', None)},
    )
    return payslip


@transaction.atomic
def apply_loan_repayments(period):
    """Materialise loan deductions for every eligible active loan.

    Returns a summary dict {created, skipped, paid_off, total_principal,
    total_interest}.

    Idempotent: a LoanRepayment already on (loan, period) short-circuits
    that loan (no second deduction, no double-decrement of outstanding).
    """
    from .models import (
        EmployeeLoan, LoanRepayment, PayslipLine,
    )

    component = _ensure_loan_repayment_component()

    summary = {
        'created':         0,
        'skipped':         0,
        'paid_off':        0,
        'total_principal': ZERO,
        'total_interest':  ZERO,
    }

    eligible = (
        EmployeeLoan.objects
        .filter(status=EmployeeLoan.Status.ACTIVE)
        .filter(outstanding__gt=0)
        .select_related('employee', 'start_period')
    )

    for loan in eligible:
        # Loan must have started on or before the target period.
        if loan.start_period_id:
            if loan.start_period.start_date > period.start_date:
                continue
        # Idempotent guard.
        if LoanRepayment.objects.filter(loan=loan, period=period).exists():
            summary['skipped'] += 1
            continue

        instalment = _monthly_instalment(loan)
        if instalment <= 0:
            summary['skipped'] += 1
            continue

        principal_part, interest_part = _split_principal_interest(loan, instalment)
        instalment_actual = _q(principal_part + interest_part)
        if instalment_actual <= 0:
            summary['skipped'] += 1
            continue

        # 1. LoanRepayment ledger row.
        LoanRepayment.objects.create(
            loan=loan,
            period=period,
            principal=principal_part,
            interest=interest_part,
            posted_at=timezone.now(),
        )

        # 2. PayslipLine on the employee's payslip.
        payslip = _ensure_payslip(loan.employee, period)
        line, created = PayslipLine.objects.get_or_create(
            payslip=payslip, component=component,
            defaults={
                'amount': instalment_actual,
                'notes':  f'Auto-loan repayment for loan {loan.id}',
            },
        )
        if not created:
            # Multiple loans for the same employee — accumulate the line.
            line.amount = _q(Decimal(line.amount or ZERO) + instalment_actual)
            line.save(update_fields=['amount', 'updated_at'])

        # 3. Decrement outstanding, flip status if fully paid.
        loan.outstanding = _q(Decimal(loan.outstanding or ZERO) - principal_part)
        update_fields = ['outstanding', 'updated_at']
        if loan.outstanding <= 0:
            loan.outstanding = ZERO
            loan.status = EmployeeLoan.Status.PAID
            update_fields.append('status')
            summary['paid_off'] += 1
        loan.save(update_fields=update_fields)

        summary['created']         += 1
        summary['total_principal'] += principal_part
        summary['total_interest']  += interest_part

    logger.info('apply_loan_repayments(%s) → %s', period.period_name, summary)
    return summary
