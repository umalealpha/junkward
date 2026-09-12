"""taskboard/dropbox_views.py — the payments "Drop Box" (CFO handover 2026-09-02).

Drop an invoice (or a folder / ZIP of them) and Omni reads each one and creates a
filled-in DRAFT payment request — payee, amount, invoice number, bank details —
that the raiser CHECKS and corrects, then submits. Staff check a request instead
of typing it.

Reuse first — nothing here is new machinery, it is assembly:
  * payments.invoice_read.read_invoice        — the reader (live 2026-08-22)
  * taskboard.payee_bank_history.last_known_bank — supplier memory (bank details
    we last paid a payee into), so a field the reader missed still fills
  * taskboard.payment_views._next_ref          — the ref generator
  * the normal create endpoint (payment_views.payment_requests POST) does the
    SUBMIT, so every existing control (PAY-SUP-01 invoice fields, PAY-BANK-02 bank,
    PAY-DUP-01 duplicates, CLAIMS positive match, bank-change) is applied exactly
    as before — a draft is NEVER a way around a control.

A draft enters NO approval or FNB path until it is submitted. Omni moves no money.
"""
from __future__ import annotations

import io
import logging
import zipfile
from decimal import Decimal, InvalidOperation

from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from taskboard.models import PaymentRequest

log = logging.getLogger(__name__)

# A reader can read a PDF or an image; anything else in a dropped ZIP is skipped
# (a folder of invoices often carries a stray .xlsx or .DS_Store).
_READABLE_EXT = ('.pdf', '.png', '.jpg', '.jpeg', '.webp', '.heic', '.tif', '.tiff')
_MAX_FILE_BYTES = 20 * 1024 * 1024   # 20 MB per invoice (matches read-invoice)
_MAX_INVOICES = 50                    # one drop is a batch, not the whole archive


def _is_readable(name: str) -> bool:
    return (name or '').lower().endswith(_READABLE_EXT)


def _iter_invoices(files):
    """Yield (filename, bytes) for every invoice in the dropped files, expanding
    any ZIP. Caps the count so one huge archive cannot tie up the reader."""
    n = 0
    for f in files:
        name = getattr(f, 'name', '') or 'invoice'
        raw = f.read()
        if name.lower().endswith('.zip'):
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    for info in z.infolist():
                        if info.is_dir() or not _is_readable(info.filename):
                            continue
                        if info.file_size > _MAX_FILE_BYTES:
                            continue
                        if n >= _MAX_INVOICES:
                            return
                        yield info.filename.rsplit('/', 1)[-1], z.read(info)
                        n += 1
            except zipfile.BadZipFile:
                continue
        elif _is_readable(name):
            if len(raw) > _MAX_FILE_BYTES or n >= _MAX_INVOICES:
                continue
            yield name, raw
            n += 1


def _is_true(v) -> bool:
    """A checkbox-style flag from a JSON body (True, "true", "1", "yes", "on")."""
    return str(v).strip().lower() in ('true', '1', 'yes', 'on')


def _dec(v):
    """A Decimal from whatever the reader or human gave, or None if not a number."""
    if v in (None, ''):
        return None
    try:
        return Decimal(str(v).replace(',', '').strip())
    except (InvalidOperation, TypeError, ValueError):
        return None


def _entered_total(pr) -> Decimal | None:
    """The total the human entered across the draft's lines, or None if no line
    carries a number yet."""
    total, seen = Decimal('0'), False
    for ln in (pr.line_items or []):
        a = _dec((ln or {}).get('amount'))
        if a is not None:
            total += a
            seen = True
    return total if seen else None


def _amount_mismatch(pr) -> bool:
    """True if the reader found an amount on the invoice and the human's entered
    total differs from it — the Drop Box safety catch (PAY-AMT-01)."""
    if pr.draft_read_amount is None:
        return False
    entered = _entered_total(pr)
    return entered is not None and entered != pr.draft_read_amount


def _make_draft(me, read: dict, filename: str) -> PaymentRequest:
    """One DRAFT payment request from one read invoice, filled as far as we can and
    flagging what a human must confirm. Saves a draft; validates nothing (a draft
    may be incomplete — the create endpoint validates on submit)."""
    from taskboard.payee_bank_history import last_known_bank
    from taskboard.payment_views import _next_ref

    payee = (read.get('payee_name') or '').strip()[:200]
    amount = read.get('total_amount')
    inv = (read.get('invoice_number') or '').strip()[:60]
    acct = (read.get('account_number') or '').strip()
    bank = (read.get('bank_name') or '').strip()
    branch = (read.get('branch_code') or '').strip()

    # Supplier memory: fill any bank field the reader missed from what we last
    # paid this payee into. A human still confirms it before submit.
    account_name = payee
    if payee:
        remembered = last_known_bank(payee)
        if remembered:
            acct = acct or (remembered.get('account_number') or '')
            bank = bank or (remembered.get('bank_name') or '')
            branch = branch or (remembered.get('branch_code') or '')
            account_name = remembered.get('account_name') or payee

    needs = []
    if not payee:
        needs.append('payee')
    if amount in (None, '', 0):
        needs.append('amount')
    if not acct:
        needs.append('account_number')
    # The claims-vs-operations choice is NEVER guessed from a read (CFO 2026-07-29)
    # — the human always picks it, so it is always on the check list.
    needs.append('category')

    entity = 'Alpha Direct Insurance Company'
    subject = (f'{payee} — invoice {inv}' if (payee and inv)
               else payee or f'Invoice ({filename})')[:200]
    line = {
        'description': (f'Invoice {inv}' if inv else f'Invoice from {filename}')[:200],
        'amount': str(amount) if amount not in (None, '') else '',
        'invoice_number': inv,
    }
    return PaymentRequest.objects.create(
        ref=_next_ref(entity), entity=entity,
        status=PaymentRequest.Status.DRAFT,
        subject=subject, payee=payee, category='',
        account_name=account_name, account_number=acct,
        bank_name=bank, branch_code=branch,
        line_items=[line], created_by=me,
        draft_source_file=filename[:255], draft_needs_check=needs,
        # The amount we read off the invoice — the safety catch compares the
        # human's entered total to this on submit (PAY-AMT-01).
        draft_read_amount=_dec(amount),
    )


def _draft_json(pr: PaymentRequest) -> dict:
    return {
        'id': str(pr.id), 'ref': pr.ref, 'status': pr.status,
        'subject': pr.subject, 'payee': pr.payee, 'category': pr.category,
        'entity': pr.entity, 'currency': pr.currency,
        'account_name': pr.account_name, 'account_number': pr.account_number,
        'bank_name': pr.bank_name, 'branch_code': pr.branch_code,
        'line_items': pr.line_items or [],
        'needs_check': pr.draft_needs_check or [],
        'source_file': pr.draft_source_file,
        # Safety catch (PAY-AMT-01): the amount the reader found, and whether the
        # human's entered total currently disagrees with it.
        'read_amount': (str(pr.draft_read_amount)
                        if pr.draft_read_amount is not None else None),
        'amount_mismatch': _amount_mismatch(pr),
        # Fraud flag (PAY-BANK-01): the reason a human gave for a changed bank.
        'bank_change_reason': pr.bank_change_reason,
        'created_at': pr.created_at.isoformat(),
    }


def _owned_draft(me, pk):
    return (PaymentRequest.objects
            .filter(pk=pk, created_by=me, status=PaymentRequest.Status.DRAFT)
            .first())


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def drop_box(request):
    """POST /payment-requests/drop-box/ — drop invoice(s) as `files` (one, many,
    or a ZIP); get back one filled DRAFT per invoice for the raiser to check."""
    files = request.FILES.getlist('files') or (
        [request.FILES['file']] if 'file' in request.FILES else [])
    if not files:
        return Response({'detail': 'Attach at least one invoice as "files".'}, status=400)

    from payments.invoice_read import read_invoice
    drafts, unreadable = [], []
    for filename, raw in _iter_invoices(files):
        try:
            read = read_invoice(raw, filename=filename)
        except Exception:                                          # noqa: BLE001
            # A bad scan must never take the whole drop down — record it and
            # keep going; the raiser can type that one by hand.
            log.exception('drop-box: read failed for %s', filename)
            unreadable.append(filename)
            continue
        drafts.append(_draft_json(_make_draft(request.user, read, filename)))

    if not drafts and not unreadable:
        return Response({'detail': 'No readable invoices found (PDF or image, or a '
                                   'ZIP of them).'}, status=400)
    return Response({'created': len(drafts), 'drafts': drafts,
                     'unreadable': unreadable}, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def drafts(request):
    """GET /payment-requests/drafts/ — the raiser's own drafts, newest first."""
    qs = (PaymentRequest.objects
          .filter(created_by=request.user, status=PaymentRequest.Status.DRAFT)
          .order_by('-created_at')[:200])
    return Response({'drafts': [_draft_json(p) for p in qs]})


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def draft_detail(request, pk):
    """PATCH edits a draft's fields (the raiser correcting the read); DELETE
    discards it. Only the raiser, only while still a draft."""
    pr = _owned_draft(request.user, pk)
    if pr is None:
        return Response({'detail': 'Draft not found.'}, status=404)

    if request.method == 'DELETE':
        pr.delete()
        return Response(status=204)

    d = request.data or {}
    EDITABLE = ('subject', 'payee', 'category', 'entity', 'currency',
                'account_name', 'account_number', 'bank_name', 'branch_code',
                'bank_change_reason')
    changed = []
    for field in EDITABLE:
        if field in d:
            setattr(pr, field, (d.get(field) or ''))
            changed.append(field)
    if 'line_items' in d and isinstance(d['line_items'], list):
        pr.line_items = d['line_items']
        changed.append('line_items')
    # A field the human filled is no longer a "needs check".
    if pr.draft_needs_check:
        still = [f for f in pr.draft_needs_check
                 if not (getattr(pr, f, '') or (f == 'amount' and _has_amount(pr)))]
        pr.draft_needs_check = still
        changed.append('draft_needs_check')
    if changed:
        pr.save(update_fields=list(dict.fromkeys(changed + ['updated_at'])))
    return Response(_draft_json(pr))


def _has_amount(pr) -> bool:
    for ln in (pr.line_items or []):
        try:
            if float(str(ln.get('amount') or 0).replace(',', '')) > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_draft(request, pk):
    """POST /payment-requests/drafts/<id>/submit/ — submit a checked draft.

    Reuses the NORMAL create endpoint so every control fires exactly as on a
    hand-typed request: it builds the create payload from the draft, calls the
    create view, and on success deletes the draft. On a validation failure it
    hands the errors straight back — that IS the "please check" state, unchanged.
    """
    pr = _owned_draft(request.user, pk)
    if pr is None:
        return Response({'detail': 'Draft not found.'}, status=404)

    d = request.data or {}

    # SAFETY CATCH — amount mismatch (PAY-AMT-01). The amount the human is about
    # to submit must match the amount we read off the invoice; if it does not,
    # stop and make them look. They clear it by fixing the amount, or by
    # confirming the change (confirm_amount) — a human decision, never automatic.
    if _amount_mismatch(pr) and not _is_true(d.get('confirm_amount')):
        entered = _entered_total(pr)
        cur = pr.currency or 'BWP'
        return Response({
            'control': 'PAY-AMT-01',
            'detail': (f'The amount entered ({cur} {entered:,.2f}) does not match the '
                       f'amount we read from the invoice ({cur} {pr.draft_read_amount:,.2f}). '
                       f'Correct the amount, or confirm the change and submit again.'),
            'read_amount': str(pr.draft_read_amount),
            'entered_amount': str(entered),
        }, status=409)

    payload = {
        'subject': pr.subject, 'category': pr.category, 'payee': pr.payee,
        'entity': pr.entity, 'currency': pr.currency,
        'account_name': pr.account_name, 'account_number': pr.account_number,
        'bank_name': pr.bank_name, 'branch_code': pr.branch_code,
        'account_type': pr.account_type,
        'claim_payee_type': pr.claim_payee_type,
        'line_items': pr.line_items or [],
        # Fraud flag (PAY-BANK-01): a changed payee account no longer blocks —
        # the create endpoint enters the request as an EXCEPTION for the
        # committee (CFO 2026-09-02) and returns 201 with an `exception` block.
        # The raiser's explanation still rides along for the committee to read.
        'bank_change_reason': (d.get('bank_change_reason')
                               or pr.bank_change_reason or ''),
    }
    # The create endpoint's own gates (a NEW payee needs a tick that the account
    # was checked — PAY-BANK-03; a supplier invoice not yet due needs a payment
    # date on/after the due date or a CFO reason — PAY-SUP-01) answer the same
    # way on a submitted draft as on a hand-typed request. Forward the human's
    # answers so the raiser can clear each control here instead of the draft
    # becoming a dead-end (Fable 5.1 audit 2026-09-02, H6: payment_date and
    # early_payment_reason were never forwarded, so a not-yet-due supplier draft
    # could NEVER be submitted). A missing answer means the control still
    # fires — the draft is never a way around it.
    for k in ('new_payee_confirmed', 'payment_date', 'early_payment_reason',
              'funds_already_moved', 'due_date', 'verifier', 'approver_id'):
        if k in d:
            payload[k] = d[k]
    # PAY-SUP-01 also wants each supplier line ticked "early-settlement discount
    # checked". A dropped invoice has no such tick, so the raiser gives it on
    # submit and it is applied to every line.
    if _is_true(d.get('discount_checked')):
        payload['line_items'] = [{**ln, 'discount_checked': True}
                                 for ln in (payload['line_items'] or []) if isinstance(ln, dict)]
    # Late import to avoid a circular import at module load.
    from taskboard.payment_views import payment_requests
    factory = APIRequestFactory()
    inner = factory.post('/api/v1/payment-requests/', payload, format='json')
    force_authenticate(inner, user=request.user)
    resp = payment_requests(inner)

    if resp.status_code == 201:
        pr.delete()   # the checked draft has become a real, submitted request
    return Response(getattr(resp, 'data', {}), status=resp.status_code)
