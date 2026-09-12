"""
commissions/payroll_feed.py — approved payroll-group commissions flow into
payroll by themselves (CFO 2026-08-28; Phase 1b of the 10-minute payroll,
twin of hris/incentive_payroll_feed.py).

Scope + guardrails (money):

* ONLY groups paid THROUGH payroll (`CommissionGroup.pays_via == PAYROLL`) feed
  payroll. Independent / direct-bank agents keep the payout file + bank run —
  they are never touched here.
* **Email-exact employee match only.** The agent is linked to an Employee by
  `email` iexact — never by name (the name-match "invents a row" scar). No
  email, or no match → skipped and RECORDED (never silent, never guessed).
* **Idempotent, no double-count.** Each submission links to the amendment it fed
  (`CommissionSubmission.payroll_amendment`); a submission already linked is not
  fed again. Per employee there is ONE amendment row per month = the SUM of that
  person's approved payroll-group commissions, so the apply engine's
  update_or_create per component adds up instead of overwriting.
* Batch is created PARSED — **never applied**. The monthly close reviews +
  applies; dual sign-off still pays. Omni never moves money.
* A manually-processed submission (Finance already keyed it) is never re-fed;
  an already-fed submission stays in the sum even after it is marked processed.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Q

COMMISSION_COMPONENT_CODE = 'COMMISSION'
AUTO_BATCH_MARKER = 'AUTO-COMMISSION'


def _commission_component():
    from payroll.models import PayslipComponent
    comp, _ = PayslipComponent.objects.get_or_create(
        code=COMMISSION_COMPONENT_CODE,
        defaults={'name': 'Commission', 'kind': PayslipComponent.Kind.EARNING,
                  'is_taxable': True, 'sort_order': 61},
    )
    return comp


def _target_period(period_label: str):
    from payroll.models import PayrollPeriod
    return PayrollPeriod.objects.filter(period_name=period_label).first()


def _baseline_for(target):
    from payroll.models import PayrollPeriod
    return (PayrollPeriod.objects.filter(start_date__lt=target.start_date)
            .order_by('-start_date', '-created_at').first())


def _employee_for_agent(agent):
    """Link a commission agent to a staff Employee by EMAIL only (exact, active).
    Returns None on anything unclear — the caller records a skip, never guesses."""
    from payroll.models import Employee
    email = (getattr(agent, 'email', '') or '').strip().lower()
    if not email:
        return None
    qs = (Employee.objects.filter(email__iexact=email, is_archived=False)
          .exclude(status=Employee.Status.TERMINATED))
    # Ambiguous (duplicate-employee-row scar) → refuse rather than pick one.
    return qs.first() if qs.count() == 1 else None


def _canonical_batch(target, baseline, company, user):
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
            notes='Auto-generated from approved payroll-group commissions '
                  '(CFO 2026-08-28). Pending — reviewed + applied at the close.',
            uploaded_by=user)
    return batch


def feed_period(*, period_label: str, user=None, group=None) -> dict[str, Any]:
    """Push approved payroll-group commissions for a month into pending payroll
    batches (one per entity). Idempotent. Never raises into the approval path."""
    from payroll.models import PayrollAmendment, PayrollAmendmentBatch
    from commissions.models import CommissionSubmission, CommissionGroup

    target = _target_period(period_label)
    if target is None:
        return {'status': 'no_period', 'pushed': 0, 'skipped': 0}
    baseline = _baseline_for(target)
    if baseline is None:
        return {'status': 'no_baseline', 'pushed': 0, 'skipped': 0}

    # APPROVED subs are candidates to feed; already-fed subs (payroll_amendment
    # set) stay IN the sum even after mark_processed flips them to PAID, so a
    # re-run never drops a person's earlier commission. A manually-PAID sub that
    # was never fed is excluded by both — the double-pay guard.
    subs = (CommissionSubmission.objects
            .select_related('agent', 'group')
            .filter(Q(status=CommissionSubmission.Status.APPROVED)
                    | (Q(payroll_amendment__isnull=False)
                       & ~Q(payroll_amendment__batch__status=PayrollAmendmentBatch.Status.REJECTED)),
                    period_label=period_label,
                    group__pays_via=CommissionGroup.PaysVia.PAYROLL))
    if group is not None:
        subs = subs.filter(group=group)

    # Group by (company, employee); sum net_payable. Skip + record the rest.
    per: dict[tuple, dict[str, Any]] = {}
    skipped: list[dict] = []
    for s in subs:
        emp = _employee_for_agent(s.agent)
        if emp is None:
            skipped.append({'sub_id': str(s.pk), 'agent': s.agent.name,
                            'reason': 'no matching staff employee (email)'})
            continue
        if s.net_payable is None or s.net_payable <= 0:
            skipped.append({'sub_id': str(s.pk), 'agent': s.agent.name,
                            'reason': 'nil or negative net payable'})
            continue
        key = (emp.company_id, emp.pk)
        slot = per.setdefault(key, {'employee': emp, 'total': Decimal('0.00'), 'subs': []})
        slot['total'] += s.net_payable
        slot['subs'].append(s)

    if not per:
        return {'status': 'nothing_to_push', 'pushed': 0, 'skipped': len(skipped),
                'skipped_detail': skipped}

    comp = _commission_component()
    pushed = 0
    batches: dict[Any, Any] = {}
    with transaction.atomic():
        for (company_id, _emp_id), slot in per.items():
            emp = slot['employee']
            company = emp.company
            if company is None:
                skipped.append({'agent': emp.full_name, 'reason': 'employee has no entity'})
                continue
            batch = batches.get(company_id)
            if batch is None:
                batch = _canonical_batch(target, baseline, company, user)
                batches[company_id] = batch
            amd, _ = PayrollAmendment.objects.update_or_create(
                batch=batch, employee=emp,
                kind=PayrollAmendment.Kind.ALLOWANCE_ADD, component=comp,
                defaults={'amount': slot['total'],
                          'employee_ref': emp.employee_number or emp.full_name,
                          'reason': f'Approved commissions {period_label} (auto)',
                          'approver': 'Auto (approved commission)', 'resolution_error': ''})
            for s in slot['subs']:
                if s.payroll_amendment_id != amd.pk:
                    s.payroll_amendment = amd
                    s.save(update_fields=['payroll_amendment'])
            pushed += 1
        for batch in batches.values():
            for sk in skipped:
                PayrollAmendment.objects.get_or_create(
                    batch=batch, employee=None, kind=PayrollAmendment.Kind.OTHER,
                    component=None, employee_ref=(sk.get('agent') or '')[:120],
                    defaults={'amount': Decimal('0.00'),
                              'reason': f'Commission not pushed: {sk["reason"]}',
                              'resolution_error': sk['reason']})
            batch.row_count = batch.amendments.count()
            batch.save(update_fields=['row_count', 'updated_at'])

    return {'status': 'pushed', 'pushed': pushed, 'skipped': len(skipped),
            'skipped_detail': skipped, 'period': period_label}


def feed_submission(sub, user=None) -> dict[str, Any]:
    """Called on final approval: feed the whole month for this submission's group."""
    from commissions.models import CommissionSubmission, CommissionGroup
    if sub.status != CommissionSubmission.Status.APPROVED:
        return {'status': 'not_approved'}
    if sub.group.pays_via != CommissionGroup.PaysVia.PAYROLL:
        return {'status': 'not_payroll_group'}
    # Feed the WHOLE month (not just this submission's group): a person can earn
    # in two payroll-paid groups, and the per-employee amendment must be their
    # SUM across groups — feeding one group would overwrite the other (Fable).
    return feed_period(period_label=sub.period_label, user=user)
