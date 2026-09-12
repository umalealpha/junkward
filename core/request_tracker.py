"""core/request_tracker.py — unified "My Requests" tracker (CFO directive 2026-08-04).

Aggregates every approval-workflow request a staff member has SUBMITTED — leave,
leave pay (encashment), staff loan, petty cash, payment request — into one
normalised list so they can see the status, whose desk it is on right now, and
what is next.

This is the requester-side twin of core/approvals_views.pending_approvals_for
(the approver side). READ ONLY — it never changes a request. Each module is read
in its own try/except so one broken module can never blank the whole page. The
per-module "mine" filters mirror those verified in each module's own list view.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Optional

from django.utils import timezone

from core.request_tracker_ai import plain_status_line

log = logging.getLogger(__name__)

# Buckets that still sit on someone's desk (aging applies).
_IN_FLIGHT = {'pending', 'approved'}
# How many days on one desk before we flag it as aging/stuck.
_AGING_DAYS = 5
# Hard cap on external AI-polish calls per request (so ?ai=1 can never fan a
# single page load out into an unbounded number of metered LLM calls).
_AI_POLISH_CAP = 10


@dataclass
class TrackedRequest:
    kind: str
    kind_label: str
    id: str
    title: str
    amount: Optional[float]
    currency: str
    bucket: str                   # pending|approved|rejected|paid|cancelled|draft
    status_label: str
    holder_label: str             # whose desk now ('' when finished)
    next_label: str               # what is next ('' when none)
    submitted_at: Optional[str]
    updated_at: Optional[str]
    days_waiting: Optional[int]
    href: str
    timeline: list = field(default_factory=list)
    stuck: bool = False
    status_line: str = ''

    def to_dict(self) -> dict:
        return asdict(self)


def _iso(dt):
    return dt.isoformat() if dt else None


def _days_since(dt):
    if not dt:
        return None
    return max(0, (timezone.now() - dt).days)


def _step(label, done, at=None):
    return {'label': label, 'done': bool(done), 'at': _iso(at)}


# ── Per-module adapters — each returns list[TrackedRequest] for THIS user ──────

def _leave_pay(user):
    from hris.leave_encash_models import LeaveEncashment as LE
    buckets = {'pending_cfo': 'pending', 'pending_hr': 'pending',
               'pending_finance': 'pending', 'approved': 'approved',
               'rejected': 'rejected', 'paid': 'paid'}
    holders = {'pending_cfo': 'the CFO', 'pending_hr': 'HR',
               'pending_finance': 'Finance (FC/FM)', 'approved': 'Finance (for payment)'}
    nexts = {'pending_cfo': 'HR', 'pending_hr': 'Finance',
             'pending_finance': 'payment', 'approved': 'payment'}
    out = []
    for e in LE.objects.filter(applicant=user).select_related('employee'):
        bucket = buckets.get(e.status, 'pending')
        out.append(TrackedRequest(
            kind='leave_pay', kind_label='Leave Pay', id=str(e.pk),
            title=f'{e.days} days', amount=float(e.amount or 0), currency='BWP',
            bucket=bucket, status_label=e.get_status_display(),
            holder_label=holders.get(e.status, ''), next_label=nexts.get(e.status, ''),
            submitted_at=_iso(e.created_at), updated_at=_iso(e.updated_at),
            days_waiting=_days_since(e.updated_at) if bucket in _IN_FLIGHT else None,
            href='/hris/leave-encashment',
            timeline=[
                _step('Submitted', True, e.created_at),
                _step('CFO', e.cfo_approved_at, e.cfo_approved_at),
                _step('HR', e.hr_approved_at, e.hr_approved_at),
                _step('Finance', e.finance_approved_at, e.finance_approved_at),
                _step('Paid', e.payroll_processed_at, e.payroll_processed_at),
            ],
        ))
    return out


def _leave(user):
    from hris.models import LeaveRequest
    try:
        from hris.feature_views import _profile_for
        profile = _profile_for(user)
    except Exception:                       # noqa: BLE001
        profile = None
    if profile is None:
        return []
    # Leave has no payment leg, so an APPROVED leave request is finished — map it
    # to a terminal bucket ('paid' renders as "Done") so it is not counted "in
    # progress" forever.
    buckets = {'draft': 'draft', 'pending': 'pending', 'approved': 'paid',
               'refused': 'rejected', 'cancelled': 'cancelled'}
    out = []
    for lr in LeaveRequest.objects.filter(profile=profile).select_related('leave_type'):
        bucket = buckets.get(lr.status, 'pending')
        out.append(TrackedRequest(
            kind='leave', kind_label='Leave', id=str(lr.pk),
            title=f'{lr.leave_type} · {lr.days} day(s)', amount=None, currency='',
            bucket=bucket, status_label=lr.get_status_display(),
            holder_label='your approver' if lr.status == 'pending' else '',
            next_label='',
            submitted_at=_iso(lr.created_at), updated_at=_iso(lr.updated_at),
            days_waiting=_days_since(lr.updated_at) if bucket == 'pending' else None,
            href='/hris/leave',
            timeline=[
                _step('Submitted', lr.status != 'draft', lr.created_at),
                _step('Decision', lr.decided_at, lr.decided_at),
            ],
        ))
    return out


def _loan(user):
    from staff_loans.models import StaffLoanApplication as SLA
    buckets = {'draft': 'draft', 'pending_cfo': 'pending', 'approved': 'approved',
               'signed': 'approved', 'active': 'paid', 'declined': 'rejected',
               'cancelled': 'cancelled'}
    holders = {'pending_cfo': 'the CFO', 'approved': 'you (to sign)',
               'signed': 'HR (to disburse)'}
    nexts = {'pending_cfo': 'your signature', 'approved': 'HR disbursement',
             'signed': 'payout'}
    out = []
    for l in SLA.objects.filter(employee__user=user).select_related('employee'):
        bucket = buckets.get(l.status, 'pending')
        try:
            title = f'{l.get_loan_type_display()} loan'
        except Exception:                   # noqa: BLE001
            title = 'Staff loan'
        out.append(TrackedRequest(
            kind='loan', kind_label='Loan', id=str(l.pk),
            title=title,
            amount=float(l.approved_amount or l.amount_requested or 0), currency='BWP',
            bucket=bucket, status_label=l.get_status_display(),
            holder_label=holders.get(l.status, ''), next_label=nexts.get(l.status, ''),
            submitted_at=_iso(l.submitted_at or l.created_at), updated_at=_iso(l.updated_at),
            days_waiting=_days_since(l.updated_at) if bucket in _IN_FLIGHT else None,
            href='/hris/staff-loans',
            timeline=[
                _step('Submitted', l.status != 'draft', l.submitted_at or l.created_at),
                _step('CFO approval', l.cfo_decided_at, l.cfo_decided_at),
                _step('Signed', l.signed_at, l.signed_at),
                _step('Disbursed', l.disbursed_at, l.disbursed_at),
            ],
        ))
    return out


def _petty(user):
    from petty_cash.models import PettyCashVoucher as PCV
    buckets = {'draft': 'draft', 'pending_approval': 'pending',
               'one_signature': 'pending', 'posted': 'approved',
               'reimbursed': 'paid', 'rejected': 'rejected'}
    holders = {'pending_approval': 'a finance signatory',
               'one_signature': 'a second finance signatory',
               'posted': 'Finance (to reimburse)'}
    nexts = {'pending_approval': 'first signature', 'one_signature': 'second signature',
             'posted': 'reimbursement'}
    out = []
    for v in PCV.objects.filter(created_by=user):
        bucket = buckets.get(v.status, 'pending')
        out.append(TrackedRequest(
            kind='petty_cash', kind_label='Petty Cash', id=str(v.pk),
            title=(v.description or v.payee or v.voucher_number or 'Petty cash')[:80],
            amount=float(v.amount or 0), currency='BWP',
            bucket=bucket, status_label=v.get_status_display(),
            holder_label=holders.get(v.status, ''), next_label=nexts.get(v.status, ''),
            submitted_at=_iso(v.submitted_at or v.created_at), updated_at=_iso(v.updated_at),
            days_waiting=_days_since(v.updated_at) if bucket in _IN_FLIGHT else None,
            href='/petty-cash',
            timeline=[
                _step('Submitted', v.status != 'draft', v.submitted_at or v.created_at),
                _step('First signature', v.first_approved_at, v.first_approved_at),
                _step('Second signature', v.approved_at, v.approved_at),
                _step('Reimbursed', v.status == 'reimbursed', None),
            ],
        ))
    return out


def _payment(user):
    from taskboard.models import PaymentRequest as PR
    buckets = {'pending_finance': 'pending', 'pending_cfo': 'pending',
               'rejected': 'rejected', 'paid': 'paid', 'cancelled': 'cancelled'}
    holders = {'pending_finance': 'Finance', 'pending_cfo': 'the CFO'}
    nexts = {'pending_finance': 'CFO authorisation', 'pending_cfo': 'payment'}
    out = []
    for p in PR.objects.filter(created_by=user):
        bucket = buckets.get(p.status, 'pending')
        out.append(TrackedRequest(
            kind='payment', kind_label='Payment', id=str(p.pk),
            title=(p.subject or p.payee or p.ref or 'Payment request')[:80],
            amount=float(p.total or 0), currency=(getattr(p, 'currency', '') or 'BWP'),
            bucket=bucket, status_label=p.get_status_display(),
            holder_label=holders.get(p.status, ''), next_label=nexts.get(p.status, ''),
            submitted_at=_iso(p.created_at), updated_at=_iso(p.updated_at),
            days_waiting=_days_since(p.updated_at) if bucket == 'pending' else None,
            href='/payment-requests',
            timeline=[
                _step('Submitted', True, p.created_at),
                _step('Finance sign-off', p.first_approved_at, p.first_approved_at),
                _step('CFO authorised / Paid', p.status == 'paid', None),
            ],
        ))
    return out


_ADAPTERS = (_leave_pay, _leave, _loan, _petty, _payment)
_BUCKET_ORDER = {'pending': 0, 'approved': 1, 'draft': 2,
                 'rejected': 3, 'paid': 4, 'cancelled': 5}


def my_requests(user, *, ai_polish: bool = False) -> list[dict]:
    """Every request THIS user submitted, across all five workflows, newest and
    most-active first. `ai_polish=True` runs each in-flight line through DeepSeek
    (PII-free) for friendlier phrasing; default off keeps the list instant."""
    if not user or not getattr(user, 'is_authenticated', False):
        return []
    items: list[TrackedRequest] = []
    for fn in _ADAPTERS:
        try:
            items.extend(fn(user))
        except Exception:                   # noqa: BLE001 — one module must not blank the page
            log.exception('request_tracker: %s failed', getattr(fn, '__name__', fn))

    items.sort(key=lambda r: r.updated_at or '', reverse=True)
    items.sort(key=lambda r: _BUCKET_ORDER.get(r.bucket, 9))

    polished = 0
    for r in items:
        r.stuck = bool(r.days_waiting is not None and r.days_waiting >= _AGING_DAYS)
        done = (r.bucket == 'paid')
        # Only polish in-flight rows, and never more than the cap (fabe L7).
        want_ai = ai_polish and r.bucket in _IN_FLIGHT and polished < _AI_POLISH_CAP
        r.status_line = plain_status_line(
            kind_label=r.kind_label, status_label=r.status_label,
            holder_label=r.holder_label, days_waiting=r.days_waiting,
            next_label=r.next_label, done=done, rejected=(r.bucket == 'rejected'),
            use_ai=want_ai,
        )
        if want_ai:
            polished += 1
    return [r.to_dict() for r in items]
