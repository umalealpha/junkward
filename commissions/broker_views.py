"""commissions/broker_views.py — the Broker Commission screen's API.

Access (CFO 2026-09-08): the five named people plus any commissions reviewer or
superuser. Read AND write — the CFO asked explicitly that their access not be
limited. Customer names are returned to this auth-gated screen only and must
never be put in an AI prompt, a log line or a scheduled email
(AD-POL-AI-GOV-001).
"""
from __future__ import annotations

import datetime as _dt
import logging
import re as _re
import os
import tempfile

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from commissions import brokers as svc
from commissions.access import is_reviewer
from commissions.models import Broker, BrokerPolicy
from django.utils import timezone

log = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 60 * 1024 * 1024


def _clean_period(raw):
    """'' or a valid YYYY-MM; None means the caller sent something else.

    The model's validator does NOT run on update_or_create, so a truncated
    '2026-8' would land in the unique key and then never match a month filter —
    an invisible row rather than an error.
    """
    p = str(raw or '').strip()
    if not p:
        return ''
    return p if _re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', p) else None


class CanUseBrokerModule(BasePermission):
    message = 'The broker commission register is restricted to the finance team.'

    def has_permission(self, request, view) -> bool:
        u = getattr(request, 'user', None)
        if not (u and getattr(u, 'is_authenticated', False)):
            return False
        return bool(getattr(u, 'is_superuser', False)) or is_reviewer(u)


def _broker_json(b: Broker, counts: dict) -> dict:
    c = counts.get(b.id, {})
    return {
        'id': str(b.id), 'name': b.name, 'short_name': b.short_name,
        'is_active': b.is_active, 'notes': b.notes,
        'aliases': [a.graphite_agency_name for a in b.aliases.all()],
        'graphite_policies': c.get('policies', 0),
        'live_policies': c.get('live_policies', 0),
        'annual_premium': c.get('annual_premium', 0.0),
        'added_rows': b.added_rows,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated, CanUseBrokerModule])
def broker_list(request):
    """Every broker, with their live commercial + domestic book from Graphite."""
    from realpay import graphite_feed
    book = graphite_feed.broker_book()
    by_agency = {r['agency']: r for r in book.get('rows', [])}
    from django.db.models import Count
    # annotate the count instead of b.policies.count() per broker — that loaded
    # every BrokerPolicy row (names included) just to count them.
    qs = Broker.objects.prefetch_related('aliases').annotate(added_rows=Count('policies'))
    counts: dict = {}
    for b in qs:
        agg = {'policies': 0, 'live_policies': 0, 'annual_premium': 0.0}
        for al in b.aliases.all():
            r = by_agency.get(al.graphite_agency_name)
            if r:
                agg['policies'] += r['policies']
                agg['live_policies'] += r['live_policies']
                agg['annual_premium'] += r['annual_premium']
        counts[b.id] = agg
    rows = sorted((_broker_json(b, counts) for b in qs),
                  key=lambda r: (-r['graphite_policies'], r['name']))

    # Agencies writing broker business that no Broker owns yet — this is exactly
    # the question Rose asked ("which brokers need tabs created?"), answered from
    # data instead of by eye.
    # .all() rides the prefetch; .values_list() would re-query per broker.
    claimed = {a.graphite_agency_name for b in qs for a in b.aliases.all()}
    unclaimed = [r for r in book.get('rows', [])
                 if r['agency'] not in claimed and not svc.is_direct_channel(r['agency'])]
    return Response({
        'brokers': rows,
        'graphite_live': bool(book.get('configured')),
        'unclaimed_agencies': sorted(unclaimed, key=lambda r: -r['policies'])[:50],
        'possible_duplicates': svc.possible_duplicates(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, CanUseBrokerModule])
def broker_detail(request, pk):
    try:
        b = Broker.objects.prefetch_related('aliases', 'policies').get(pk=pk)
    except Broker.DoesNotExist:
        return Response({'detail': 'No such broker.'}, status=404)
    active_only = (request.query_params.get('active_only') or '').lower() in ('1', 'true', 'yes')
    # A broker sheet pays on what was collected in ONE month — that is what
    # Finance's 'Current Status' column means. Default to the current month so
    # the screen opens on a figure that can be reconciled, never an all-history
    # mix (the same lesson as the RealPay collections dashboard, 2026-09-07).
    period = (request.query_params.get('period') or '').strip()
    start = end = None
    if period:
        try:
            y, m = period.split('-')
            start = _dt.date(int(y), int(m), 1)
            end = (_dt.date(int(y) + (m == '12'), (int(m) % 12) + 1, 1) - _dt.timedelta(days=1))
        except (ValueError, TypeError):
            return Response({'detail': 'Month must look like 2026-08.'}, status=400)
    else:
        today = timezone.localdate()
        start, end = today.replace(day=1), today
        period = today.strftime('%Y-%m')
    data = svc.broker_clients(b, active_only=active_only, start=start, end=end)
    data['period'] = period
    return Response({
        'broker': {'id': str(b.id), 'name': b.name, 'short_name': b.short_name,
                   'notes': b.notes, 'is_active': b.is_active,
                   'aliases': [a.graphite_agency_name for a in b.aliases.all()]},
        **data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, CanUseBrokerModule])
def broker_sync(request):
    """Rebuild the register from Graphite. Idempotent; never deletes a broker."""
    return Response(svc.sync_brokers_from_graphite())


@api_view(['POST'])
@permission_classes([IsAuthenticated, CanUseBrokerModule])
def broker_add_policy(request, pk):
    try:
        b = Broker.objects.get(pk=pk)
    except Broker.DoesNotExist:
        return Response({'detail': 'No such broker.'}, status=404)
    pol = str(request.data.get('policy_number') or '').strip()
    if not pol:
        return Response({'detail': 'A policy number is required.'}, status=400)

    from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

    def money(k):
        try:
            # HALF UP, not Python's default HALF_EVEN — rounding is a tax
            # decision and VAT rounds half up (CFO standing order).
            return Decimal(str(request.data.get(k) or '0')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError):
            return Decimal('0.00')

    period = _clean_period(request.data.get('period_label'))
    if period is None:
        return Response({'detail': 'Month must look like 2026-08.'}, status=400)

    obj, made = BrokerPolicy.objects.update_or_create(
        broker=b, policy_number=pol[:60], period_label=period,
        defaults={
            'insured_name': str(request.data.get('insured_name') or '')[:160],
            'premium': money('premium'), 'amount_received': money('amount_received'),
            'motor_premium': money('motor_premium'), 'motor_commission': money('motor_commission'),
            'non_motor_premium': money('non_motor_premium'),
            'non_motor_commission': money('non_motor_commission'),
            'commission_payable': money('commission_payable'), 'vat': money('vat'),
            'source': BrokerPolicy.Source.MANUAL, 'added_by': request.user,
        })
    return Response({'id': str(obj.id), 'created': made,
                     'policy_number': obj.policy_number}, status=201 if made else 200)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, CanUseBrokerModule])
def broker_delete_policy(request, pk, policy_id):
    """Remove a row a person added. A row that only exists in Graphite cannot be
    deleted here — it is Graphite's record, and hiding it would make the sheet
    disagree with the book."""
    try:
        obj = BrokerPolicy.objects.get(pk=policy_id, broker_id=pk)
    except BrokerPolicy.DoesNotExist:
        return Response({'detail': 'That row is not one Omni added — it comes from '
                                   'Graphite and cannot be deleted here.'}, status=404)
    pol = obj.policy_number
    obj.delete()
    return Response({'deleted': True, 'policy_number': pol})


@api_view(['POST'])
@permission_classes([IsAuthenticated, CanUseBrokerModule])
def broker_upload(request):
    """Import a multi-tab broker workbook. `preview=1` parses without writing."""
    f = request.FILES.get('file')
    if not f:
        return Response({'detail': 'Attach the broker workbook.'}, status=400)
    if f.size > MAX_UPLOAD_BYTES:
        return Response({'detail': 'That file is larger than 60 MB.'}, status=400)
    name = (f.name or '').lower()
    if not name.endswith(('.xlsx', '.xlsm', '.xlsb', '.xls', '.ods')):
        return Response({'detail': 'Upload a spreadsheet (.xlsx, .xlsm, .xlsb, .xls or .ods).'},
                        status=400)
    preview = str(request.data.get('preview') or '').lower() in ('1', 'true', 'yes')
    period = _clean_period(request.data.get('period_label'))
    if period is None:
        return Response({'detail': 'Month must look like 2026-08.'}, status=400)

    suffix = os.path.splitext(name)[1]
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        for chunk in f.chunks():
            tmp.write(chunk)
        tmp.flush()
        tmp.close()
        out = svc.import_workbook(tmp.name, period_label=period,
                                  user=request.user, commit=not preview)
    except Exception as exc:  # noqa: BLE001 — a bad workbook is a 400, not a 500
        log.exception('broker workbook import failed')
        return Response({'detail': f'That workbook could not be read: {exc}'}, status=400)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
    return Response(out)


@api_view(['POST'])
@permission_classes([IsAuthenticated, CanUseBrokerModule])
def broker_absorb(request, pk):
    """Fold another broker into this one — for the near-duplicates automatic
    merging cannot safely close (e.g. 'Minet Botswana' and 'Minet Francistown').
    A person confirms; the machine does not guess."""
    other_id = str(request.data.get('other_id') or '').strip()
    if not other_id:
        return Response({'detail': 'Say which broker to fold in.'}, status=400)
    try:
        keeper = Broker.objects.get(pk=pk)
        other = Broker.objects.get(pk=other_id)
    except (Broker.DoesNotExist, ValueError, TypeError):
        return Response({'detail': 'No such broker.'}, status=404)
    try:
        return Response(svc.absorb(keeper, other))
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=400)
