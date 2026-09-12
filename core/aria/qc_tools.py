"""
core/aria/qc_tools.py — action + search + messaging tools for the Aria AI assistant.

Available to whitelisted managers/EXCO. These tools let Aria act on behalf
of the user: search payments, approve/reject, look up staff, count pending,
and send popup messages to other staff (CFO only).

Every action is audit-logged under the REAL user's name.
"""

from __future__ import annotations

import logging
from django.utils import timezone

log = logging.getLogger('aria.qc_tools')

ARIA_POWER_USERS = {
    'pganesharajah@alphadirect.co.bw',
    'cfo@alphadirect.co.bw',
    'pkago@alphadirect.co.bw',
    'ktshutlhedi@alphadirect.co.bw',
    'kmasilo@alphadirect.co.bw',
    'lbasotli@alphadirect.co.bw',
    'omogomotsi@alphadirect.co.bw',
    'bmokone@alphadirect.co.bw',
    'bnaidu@alphadirect.co.bw',
    'asundaram@alphadirect.co.bw',
    'arjun@alphadirect.co.bw',
    'ubutale@alphadirect.co.bw',
    'dmosweu@alphadirect.co.bw',
}

CFO_EMAILS = {
    'pganesharajah@alphadirect.co.bw',
    'cfo@alphadirect.co.bw',
}


def is_power_user(user) -> bool:
    email = getattr(user, 'email', '') or ''
    return email.lower() in ARIA_POWER_USERS


def is_cfo(user) -> bool:
    email = getattr(user, 'email', '') or ''
    return email.lower() in CFO_EMAILS


def search_payments(*, payee: str = '', ref: str = '', status: str = '',
                    limit: int = 10) -> dict:
    from taskboard.models import PaymentRequest
    from django.db.models import Q

    qs = PaymentRequest.objects.select_related('created_by').order_by('-created_at')
    if ref:
        qs = qs.filter(ref__icontains=ref)
    if payee:
        qs = qs.filter(Q(payee__icontains=payee) | Q(subject__icontains=payee))
    if status:
        qs = qs.filter(status=status)

    results = []
    for p in qs[:limit]:
        total = sum(
            float(li.get('amount', 0))
            for li in (p.line_items or [])
            if isinstance(li, dict)
        )
        results.append({
            'ref': p.ref,
            'payee': p.payee or '',
            'subject': p.subject or '',
            'status': p.get_status_display(),
            'status_code': p.status,
            'category': p.get_category_display() if p.category else '',
            'entity': p.entity or '',
            'total': f'{total:,.2f} {p.currency}',
            'created_by': (p.created_by.get_full_name() if p.created_by else ''),
            'created_at': p.created_at.strftime('%Y-%m-%d %H:%M') if p.created_at else '',
        })

    return {'count': len(results), 'payments': results}


def count_pending(*, user=None) -> dict:
    from taskboard.models import PaymentRequest, OmniTask

    pf = PaymentRequest.objects.filter(status='pending_finance').count()
    pc = PaymentRequest.objects.filter(status='pending_cfo').count()
    exc = PaymentRequest.objects.filter(status='exception').count()
    draft = PaymentRequest.objects.filter(status='draft').count()
    tasks_open = OmniTask.objects.filter(status__in=['open', 'in_progress']).count()

    return {
        'pending_finance_signoff': pf,
        'pending_cfo_authorisation': pc,
        'exceptions_with_committee': exc,
        'drafts': draft,
        'open_tasks': tasks_open,
    }


def lookup_staff(*, name: str = '', email: str = '') -> dict:
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    User = get_user_model()

    qs = User.objects.filter(is_active=True)
    if name:
        parts = name.split()
        q = Q()
        for part in parts:
            q &= (Q(first_name__icontains=part) | Q(last_name__icontains=part)
                   | Q(username__icontains=part))
        qs = qs.filter(q)
    if email:
        qs = qs.filter(email__icontains=email)

    results = []
    for u in qs[:10]:
        results.append({
            'name': u.get_full_name() or u.username,
            'email': u.email or '',
            'is_staff': u.is_staff,
            'last_login': u.last_login.strftime('%Y-%m-%d %H:%M') if u.last_login else 'never',
        })

    return {'count': len(results), 'staff': results}


def approve_payment(*, ref: str, user, notes: str = '') -> dict:
    from taskboard.models import PaymentRequest
    from django.db import transaction
    from core.models import AuditLog

    try:
        p = PaymentRequest.objects.select_related('task', 'created_by').get(ref=ref)
    except PaymentRequest.DoesNotExist:
        return {'ok': False, 'error': f'Payment {ref} not found.'}

    if p.status not in ('pending_finance', 'pending_cfo'):
        return {'ok': False, 'error': f'Payment {ref} is {p.get_status_display()} — cannot approve.'}

    if p.status == 'pending_finance' and p.created_by_id == user.id:
        return {'ok': False, 'error': 'You cannot sign off a payment you raised (segregation of duties).'}

    if p.status == 'pending_finance':
        from taskboard.payment_views import _is_first_approver
        if not _is_first_approver(user):
            return {'ok': False, 'error': 'Only a finance approver (Pako, Kago or Legakwa) can sign off at this stage.'}

    now = timezone.now()
    with transaction.atomic():
        if p.status == 'pending_finance':
            p.status = PaymentRequest.Status.PENDING_CFO
            p.first_approver = user
            p.first_approved_at = now
            p.save(update_fields=['status', 'first_approver', 'first_approved_at', 'updated_at'])
            action_label = 'finance_signoff_via_aria'
        else:
            if not is_cfo(user):
                return {'ok': False, 'error': 'Only the CFO can authorise at this stage.'}
            p.status = PaymentRequest.Status.PAID
            if notes:
                p.decision_notes = notes[:2000]
            p.save(update_fields=['status', 'decision_notes', 'updated_at'])
            if p.task and p.task.status not in ('done', 'cancelled'):
                p.task.status = 'cancelled'
                p.task.completed_at = now
                p.task.save(update_fields=['status', 'completed_at', 'updated_at'])
            action_label = 'cfo_authorise_via_aria'

        AuditLog.objects.create(
            user=user,
            table_name='paymentrequest',
            record_id=str(p.pk),
            action=AuditLog.Action.APPROVE,
            new_values={'aria_action': action_label, 'ref': ref, 'notes': notes or ''},
            description=f'{action_label} via Aria AI assistant',
        )

    return {'ok': True, 'ref': ref, 'new_status': p.get_status_display(),
            'action': action_label, 'acted_by': user.get_full_name()}


def reject_payment(*, ref: str, user, reason: str) -> dict:
    from taskboard.models import PaymentRequest
    from django.db import transaction
    from core.models import AuditLog

    if not reason:
        return {'ok': False, 'error': 'A reason is required when rejecting.'}

    try:
        p = PaymentRequest.objects.select_related('task').get(ref=ref)
    except PaymentRequest.DoesNotExist:
        return {'ok': False, 'error': f'Payment {ref} not found.'}

    if p.status not in ('pending_finance', 'pending_cfo'):
        return {'ok': False, 'error': f'Payment {ref} is {p.get_status_display()} — cannot reject.'}

    now = timezone.now()
    with transaction.atomic():
        p.status = PaymentRequest.Status.REJECTED
        p.rejected_by = user
        p.rejected_at = now
        p.decision_notes = reason[:2000]
        p.save(update_fields=['status', 'rejected_by', 'rejected_at', 'decision_notes', 'updated_at'])

        if p.task and p.task.status != 'cancelled':
            p.task.status = 'cancelled'
            p.task.completed_at = now
            p.task.save(update_fields=['status', 'completed_at', 'updated_at'])

        AuditLog.objects.create(
            user=user,
            table_name='paymentrequest',
            record_id=str(p.pk),
            action=AuditLog.Action.UPDATE,
            new_values={'aria_action': 'reject_via_aria', 'ref': ref, 'reason': reason},
            description='reject_via_aria via Aria AI assistant',
        )

    return {'ok': True, 'ref': ref, 'new_status': 'Rejected', 'acted_by': user.get_full_name()}


def recent_audit_log(*, table: str = '', limit: int = 10) -> dict:
    from core.models import AuditLog

    qs = AuditLog.objects.order_by('-created_at')
    if table:
        qs = qs.filter(table_name__icontains=table)

    results = []
    for entry in qs[:limit]:
        results.append({
            'user': entry.user.get_full_name() if entry.user else 'system',
            'table': entry.table_name,
            'action': str(entry.action),
            'record_id': entry.record_id or '',
            'at': entry.created_at.strftime('%Y-%m-%d %H:%M') if entry.created_at else '',
        })

    return {'count': len(results), 'entries': results}


def _popup_identifier(u) -> str:
    return (u.email or u.username or '').strip()


def send_popup_message(*, recipient_name: str, message: str, user,
                       confirm_recipient: str = '') -> dict:
    """Send a popup message to a staff member. CFO only.

    TWO CALLS, ALWAYS. The first call never sends: it resolves the name and
    returns who it matched. Only a second call carrying `confirm_recipient`
    (that person's exact email or username) creates the popup.

    The CFO asked Aria to "double check with me the name". Instructing the
    model to confirm is a rule it can skip; requiring an identifier it can only
    have learned from the first call's reply is a gate it cannot. A wrong or
    guessed identifier is refused rather than delivered to the wrong person.
    """
    if not is_cfo(user):
        return {'ok': False, 'error': 'Only the CFO can send popup messages.'}

    if not message.strip():
        return {'ok': False, 'error': 'Message cannot be empty.'}

    from django.contrib.auth import get_user_model
    from django.db.models import Q
    from core.models import AriaPopup
    User = get_user_model()

    parts = recipient_name.strip().split()
    if not parts:
        return {'ok': False, 'error': 'A recipient name is required.'}

    q = Q()
    for part in parts:
        q &= (Q(first_name__icontains=part) | Q(last_name__icontains=part))
    matches = list(User.objects.filter(q, is_active=True)[:5])

    if not matches:
        return {'ok': False, 'error': f'No active staff member found matching "{recipient_name}".'}

    candidates = [
        {'name': u.get_full_name() or u.username, 'confirm_recipient': _popup_identifier(u)}
        for u in matches
    ]

    if not confirm_recipient:
        return {
            'ok': False,
            'needs_confirmation': True,
            'error': ('Not sent yet. Show the CFO exactly who this would go to and the '
                      'message, and ask them to confirm. Then call send_popup_message '
                      'again with confirm_recipient set to that person\'s value below.'),
            'matches': candidates,
            'message_to_send': message,
        }

    wanted = confirm_recipient.strip().lower()
    recipient = next((u for u in matches if _popup_identifier(u).lower() == wanted), None)
    if recipient is None:
        return {
            'ok': False,
            'error': (f'"{confirm_recipient}" is not one of the people matching '
                      f'"{recipient_name}". Nothing was sent. Confirm again using one '
                      f'of the exact values listed.'),
            'matches': candidates,
        }

    AriaPopup.objects.create(sender=user, recipient=recipient, message=message)

    return {
        'ok': True,
        'sent_to': recipient.get_full_name() or recipient.username,
        'email': recipient.email,
        'message_preview': message[:100],
    }
