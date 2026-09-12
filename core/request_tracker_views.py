"""core/request_tracker_views.py — the "My Requests" API (read-only).

GET /api/v1/my-requests/         → everything the caller has submitted.
    ?ai=1                        → DeepSeek-polish each status line (PII-free).
"""
from __future__ import annotations

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.request_tracker import my_requests


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_requests_view(request):
    ai = str(request.GET.get('ai', '')).lower() in ('1', 'true', 'yes')
    items = my_requests(request.user, ai_polish=ai)
    active = sum(1 for r in items if r['bucket'] in ('pending', 'approved'))
    stuck = sum(1 for r in items if r.get('stuck'))
    return Response({
        'items':  items,
        'active': active,
        'stuck':  stuck,
        'total':  len(items),
    })
