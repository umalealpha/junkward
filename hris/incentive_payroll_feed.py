"""
hris/incentive_payroll_feed.py — approved incentives flow into payroll by
themselves (CFO 2026-08-28: "let anything be pushed to payroll to make it easy;
I don't want my people to work hard in that area").

What it does, and the guardrails that keep it safe:

* When an incentive request is fully approved, every line is pushed into a
  single PENDING payroll amendment batch for that month + entity. Finance never
  re-keys it. The batch is created PARSED, **never applied** — the monthly
  payroll close still reviews and applies it, and dual sign-off still pays it.
  Omni never moves money; it only prepares the batch.
* **Real employee only.** A line is pushed using its resolved `employee`
  foreign key — never a name match — so it can never invent or mis-target a
  person (the name-mismatch scar). Lines with no employee, or an employee in a
  different entity, are skipped and reported, not guessed.
* **Idempotent + no double-count.** Each line links to the amendment it fed
  (`IncentiveLine.payroll_amendment`); a line already linked is never pushed
  again. Per employee there is exactly ONE amendment row per month whose amount
  is the SUM of that person's approved incentive lines — so two incentives for
  the same person in one month add up instead of overwriting each other (the
  apply engine does update_or_create per component).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction

INCENTIVE_COMPONENT_CODE = 'INCENTIVE'
AUTO_BATCH_MARKER = 'AUTO-INCENTIVE'


def _incentive_component():
    """The taxable earning line incentives land on. Created once, reused."""
    from payroll.models import PayslipComponent
    comp, _ = PayslipComponent.objects.get_or_create(
        code=INCENTIVE_COMPONENT_CODE,
        defaults={
            'name': 'Incentive',
            'kind': PayslipComponent.Kind.EARNING,   # taxable earning
            'is_taxable': True,
            'sort_order': 60,
        },
    )
    return comp


def _target_period(period_label: str):
    from payroll.models import PayrollPeriod
    return PayrollPeriod.objects.filter(period_name=period_label).first()


def _baseline_for(target):
    """The month whose payslips are the starting point — the latest period
    strictly before the target. None on the very first period."""
    from payroll.models import PayrollPeriod
    return (PayrollPeriod.objects.filter(start_date__lt=target.start_date)
            .order_by('-start_date', '-created_at').first())


def _canonical_batch(target, baseline, company, user):
    """One PARSED auto-batch per (target period, entity). Reused across every
    incentive request in that month so the whole month lands in ONE batch."""
    from payroll.models import PayrollAmendmentBatch
    batch = (PayrollAmendmentBatch.objects.select_for_update()
             .filter(target_period=target, company=company,
                     file_name=AUTO_BATCH_MARKER,
                     status=PayrollAmendmentBatch.Status.PARSED)
             .first())
    if batch is None:
        batch = PayrollAmendmentBatch.objects.create(
            target_period=target, baseline_period=baseline, company=company,
            file_name=AUTO_BATCH_MARKER, status=PayrollAmendmentBatch.Status.PARSED,
            notes='Auto-generated from approved incentives (CFO 2026-08-28). '
                  'Pending — reviewed and applied at the monthly payroll close.',
            uploaded_by=user,
        )
    return batch


def feed_period_company(*, period_label: str, company, user=None) -> dict[str, Any]:
    """Push all APPROVED incentive lines for one month + entity into the pending
    payroll batch. Idempotent: safe to re-run; only adds/updates, never doubles.
    Returns a plain-English status dict — never raises into the approval path."""
    from payroll.models import Employee, PayrollAmendment
    from hris.incentive_models import IncentiveLine, IncentiveRequest

    if company is None:
        return {'status': 'no_company', 'detail': 'The request has no entity set.',
                'pushed': 0, 'skipped': 0}
    target = _target_period(period_label)
    if target is None:
        return {'status': 'no_period', 'detail': f'No payroll period {period_label} yet.',
                'pushed': 0, 'skipped': 0}
    baseline = _baseline_for(target)
    if baseline is None:
        return {'status': 'no_baseline', 'detail': f'No period before {period_label}.',
                'pushed': 0, 'skipped': 0}

    # Pull approved lines for the month + entity. Exclude requests Finance
    # already MANUALLY keyed into payroll (payroll_processed AND never auto-fed)
    # — the double-pay guard — but KEEP a line that this feed itself already
    # pushed (payroll_amendment set), even if its request was later marked
    # processed, so recomputing the per-employee sum never drops it (Fable r2).
    from django.db.models import Q
    lines = (IncentiveLine.objects
             .select_related('employee', 'request')
             .filter(Q(request__payroll_processed=False) | Q(payroll_amendment__isnull=False),
                     request__status=IncentiveRequest.Status.APPROVED,
                     request__company=company,
                     request__period=period_label))

    # Group by resolved, same-entity employee. Skip (report) everything else.
    per_emp: dict[Any, dict[str, Any]] = {}
    skipped: list[dict] = []
    for ln in lines:
        emp = ln.employee
        if emp is None:
            skipped.append({'line_id': str(ln.pk), 'name': ln.name,
                            'reason': 'no employee linked'})
            continue
        if emp.company_id != company.pk:
            skipped.append({'line_id': str(ln.pk), 'name': ln.name,
                            'reason': 'employee belongs to a different entity'})
            continue
        slot = per_emp.setdefault(emp.pk, {'employee': emp, 'total': Decimal('0.00'),
                                           'lines': []})
        slot['total'] += ln.amount
        slot['lines'].append(ln)

    if not per_emp:
        return {'status': 'nothing_to_push', 'pushed': 0, 'skipped': len(skipped),
                'skipped_detail': skipped}

    comp = _incentive_component()
    pushed_emps = 0
    with transaction.atomic():
        batch = _canonical_batch(target, baseline, company, user)
        for slot in per_emp.values():
            emp = slot['employee']
            amd, _created = PayrollAmendment.objects.update_or_create(
                batch=batch, employee=emp,
                kind=PayrollAmendment.Kind.ALLOWANCE_ADD, component=comp,
                defaults={
                    'amount': slot['total'],
                    'employee_ref': emp.employee_number or emp.full_name,
                    'reason': f'Approved incentives {period_label} (auto)',
                    'approver': 'Auto (approved incentive)',
                    'resolution_error': '',
                },
            )
            # Link every contributing line to this amendment (idempotency guard).
            for ln in slot['lines']:
                if ln.payroll_amendment_id != amd.pk:
                    ln.payroll_amendment = amd
                    ln.save(update_fields=['payroll_amendment', 'updated_at'])
            pushed_emps += 1
        # Never-silent: surface every skipped line as a zero-amount row carrying
        # a resolution_error, so an approved incentive that could not be pushed
        # is visible on the batch at the close instead of vanishing.
        for sk in skipped:
            PayrollAmendment.objects.get_or_create(
                batch=batch, employee=None, kind=PayrollAmendment.Kind.OTHER,
                component=None, employee_ref=(sk['name'] or '')[:120],
                defaults={'amount': Decimal('0.00'),
                          'reason': f'Incentive not pushed: {sk["reason"]}',
                          'resolution_error': sk['reason']},
            )
        batch.row_count = batch.amendments.count()
        batch.save(update_fields=['row_count', 'updated_at'])

    return {'status': 'pushed', 'pushed': pushed_emps, 'skipped': len(skipped),
            'skipped_detail': skipped, 'batch_id': str(batch.pk),
            'period': period_label, 'company': company.code}


def feed_for_request(req, user=None) -> dict[str, Any]:
    """Convenience: push everything for the request's month + entity (recomputes
    the whole month so the just-approved request is included). Called on approval."""
    return feed_period_company(period_label=req.period, company=req.company, user=user)
