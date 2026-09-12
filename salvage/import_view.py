"""
salvage/import_view.py — bulk import of SalvageItem rows from CSV / XLSX.

CFO directive 2026-05-18: the operator needs to add inventory one-by-one
(handled by `/salvage/inventory/new`) AND in bulk. This view accepts a
multipart file, parses it, validates each row, and creates rows in a
single transaction. Every successful row fires `post_intake_to_gl` so
the BS picks up the asset and 105004 picks up the contra-claims credit.

Expected columns (header-row required, case-insensitive, order-free):

    item_code         REQUIRED  unique short code
    part_name         REQUIRED  what was salvaged
    claim_number      optional  policy claim ref
    condition         optional  excellent | good | fair | poor | scrap (default fair)
    status            optional  available | reserved | on_hold | written_off | scrapped
    asking_price      optional  BWP  (default 0)
    reserve_price     optional  BWP  (default 0)
    cost_basis        optional  BWP  (default = reserve_price; what hits BS)
    location          optional  yard text
    received_date     optional  YYYY-MM-DD (default = today)
    notes             optional  free text

Errors are returned per-row with `row_number` (header is row 1) and
`message`. If ANY row fails validation, NOTHING is committed — the user
fixes the file and re-imports. This is intentional: an insurer's
inventory can't drift halfway.
"""
from __future__ import annotations

import datetime as _dt
import io
import logging
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from rest_framework import status as drf_status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Company
from .models import SalvageItem
from .permissions import IsSalvageUser
from .services import post_intake_to_gl
from django.utils import timezone


log = logging.getLogger(__name__)


# Column synonyms — operator-friendly. Each row of the import file is
# matched against this list to find the canonical key.
COLUMN_SYNONYMS: dict[str, tuple[str, ...]] = {
    'item_code':     ('item code', 'code', 'item_code', 'sku'),
    'part_name':     ('part name', 'part', 'description', 'part_name', 'name'),
    'claim_number':  ('claim number', 'claim', 'claim_no', 'claim_number'),
    'condition':     ('condition',),
    'status':        ('status',),
    'asking_price':  ('asking price', 'asking', 'asking_price', 'price'),
    'reserve_price': ('reserve price', 'reserve', 'reserve_price', 'floor'),
    'cost_basis':    ('cost basis', 'cost_basis', 'carrying', 'carrying_value', 'cost'),
    'location':      ('location', 'yard', 'shelf'),
    'received_date': ('received date', 'date', 'received_date', 'intake_date'),
    'notes':         ('notes', 'comment', 'memo'),
}

VALID_CONDITIONS = ('excellent', 'good', 'fair', 'poor', 'scrap')
VALID_STATUSES   = ('available', 'reserved', 'on_hold', 'written_off',
                    'scrapped', 'disposed', 'quoted', 'sold')


def _norm_key(s: str) -> str:
    return (s or '').strip().lower().replace('-', ' ').replace('_', ' ')


def _build_column_map(headers: list[str]) -> dict[str, str]:
    """Match each header to a canonical key. Returns {header: canonical}."""
    out: dict[str, str] = {}
    for h in headers:
        n = _norm_key(h)
        for canonical, synonyms in COLUMN_SYNONYMS.items():
            if n in (_norm_key(s) for s in synonyms):
                out[h] = canonical
                break
    return out


def _decimal(v: Any, default: str = '0') -> Decimal:
    if v in (None, ''):
        return Decimal(default)
    s = str(v).replace(',', '').strip()
    try:
        return Decimal(s or default)
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _date(v: Any) -> _dt.date | None:
    if not v:
        return None
    if isinstance(v, _dt.date):
        return v
    if isinstance(v, _dt.datetime):
        return v.date()
    if isinstance(v, (int, float)):
        # Excel serial date (days since 1899-12-30)
        ms = int(round((float(v) - 25569) * 86400 * 1000))
        return _dt.datetime.utcfromtimestamp(ms / 1000).date()
    s = str(v).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d'):
        try:
            return _dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_file(uploaded_file) -> tuple[list[str], list[dict[str, Any]]]:
    """Return (headers, rows) for either CSV or XLSX uploads."""
    name = (uploaded_file.name or '').lower()
    if name.endswith(('.xlsx', '.xls')):
        try:
            import openpyxl                                   # type: ignore
        except ImportError as exc:
            raise ValueError('openpyxl not installed — cannot read XLSX.') from exc
        wb = openpyxl.load_workbook(uploaded_file, data_only=True, read_only=True)
        ws = wb.active
        if ws is None:
            return [], []
        rows_iter = ws.iter_rows(values_only=True)
        try:
            headers = [str(h or '').strip() for h in next(rows_iter)]
        except StopIteration:
            return [], []
        body = []
        for raw_row in rows_iter:
            if raw_row is None or all((c is None or c == '') for c in raw_row):
                continue
            body.append({headers[i]: (raw_row[i] if i < len(raw_row) else '')
                         for i in range(len(headers))})
        return headers, body
    else:
        import csv
        text = uploaded_file.read().decode('utf-8-sig', errors='replace')
        reader = csv.reader(io.StringIO(text))
        try:
            headers = [h.strip() for h in next(reader)]
        except StopIteration:
            return [], []
        body = [{headers[i]: (row[i] if i < len(row) else '') for i in range(len(headers))}
                for row in reader if any((c or '').strip() for c in row)]
        return headers, body


class SalvageItemImportView(APIView):
    """POST /api/v1/salvage-items/import/

    Body (multipart):
      file       — .csv or .xlsx
      company    — optional Company id; defaults to the user's current
                   topbar selection (frontend sends it explicitly so the
                   import always lands in the right entity).
      dry_run    — 'true' to validate without committing
      auto_post  — 'true' (default) to fire post_intake_to_gl per row

    Response:
      { created, skipped, errors[], intake_jes_posted }
    """
    permission_classes = [IsAuthenticated, IsSalvageUser]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded = request.FILES.get('file')
        if not uploaded:
            return Response({'detail': 'file is required.'},
                            status=drf_status.HTTP_400_BAD_REQUEST)
        if uploaded.size > 20 * 1024 * 1024:
            return Response({'detail': 'File exceeds 20 MB limit.'},
                            status=drf_status.HTTP_400_BAD_REQUEST)

        company = None
        company_id = (request.data.get('company') or '').strip()
        if company_id:
            company = Company.objects.filter(pk=company_id).first()
        dry_run    = (request.data.get('dry_run') or '').lower() == 'true'
        auto_post  = (request.data.get('auto_post') or 'true').lower() == 'true'

        try:
            headers, rows = _parse_file(uploaded)
        except Exception as exc:                              # noqa: BLE001
            return Response({'detail': f'Could not read file: {exc}'},
                            status=drf_status.HTTP_400_BAD_REQUEST)

        if not headers:
            return Response({'detail': 'File has no header row.'},
                            status=drf_status.HTTP_400_BAD_REQUEST)
        col_map = _build_column_map(headers)
        if 'item_code' not in col_map.values() or 'part_name' not in col_map.values():
            return Response(
                {'detail': 'File must contain at least "item_code" and "part_name" columns.',
                 'headers_found': headers,
                 'allowed_synonyms': COLUMN_SYNONYMS},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        # Pre-flight validation — pass 1
        errors: list[dict[str, Any]] = []
        cleaned: list[dict[str, Any]] = []
        seen_codes: set[str] = set()
        existing_codes = set(SalvageItem.objects.values_list('item_code', flat=True))

        for idx, raw in enumerate(rows, start=2):    # +2 = header row 1
            row: dict[str, Any] = {}
            for h, v in raw.items():
                canonical = col_map.get(h)
                if canonical:
                    row[canonical] = v

            code = str(row.get('item_code') or '').strip()
            name = str(row.get('part_name') or '').strip()
            if not code:
                errors.append({'row_number': idx, 'message': 'item_code is required.'})
                continue
            if not name:
                errors.append({'row_number': idx, 'message': 'part_name is required.'})
                continue
            if code in seen_codes:
                errors.append({'row_number': idx,
                               'message': f'duplicate item_code "{code}" in this file.'})
                continue
            if code in existing_codes:
                errors.append({'row_number': idx,
                               'message': f'item_code "{code}" already exists in the DB.'})
                continue
            seen_codes.add(code)

            cond = (str(row.get('condition') or 'fair').strip().lower()) or 'fair'
            if cond not in VALID_CONDITIONS:
                errors.append({'row_number': idx,
                               'message': f'invalid condition "{cond}". '
                                          f'Allowed: {", ".join(VALID_CONDITIONS)}.'})
                continue
            stat = (str(row.get('status') or 'available').strip().lower()) or 'available'
            if stat not in VALID_STATUSES:
                errors.append({'row_number': idx,
                               'message': f'invalid status "{stat}". '
                                          f'Allowed: {", ".join(VALID_STATUSES)}.'})
                continue

            ask  = _decimal(row.get('asking_price'))
            res  = _decimal(row.get('reserve_price'))
            cb   = _decimal(row.get('cost_basis'), default=str(res))
            if cb == 0 and res > 0:
                cb = res

            cleaned.append({
                'item_code':     code,
                'part_name':     name[:200],
                'claim_number':  str(row.get('claim_number') or '').strip()[:60],
                'condition':     cond,
                'status':        stat,
                'asking_price':  ask,
                'reserve_price': res,
                'cost_basis':    cb,
                'location':      str(row.get('location') or '').strip()[:80],
                'received_date': _date(row.get('received_date')),
                'notes':         str(row.get('notes') or '').strip(),
            })

        if errors:
            return Response(
                {'detail': 'Validation failed — nothing was committed.',
                 'errors': errors[:200],
                 'sample_size': len(rows)},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        if dry_run:
            return Response({'dry_run': True, 'rows_validated': len(cleaned),
                             'first_5': cleaned[:5]})

        # Commit — pass 2
        created = 0
        je_count = 0
        with transaction.atomic():
            for r in cleaned:
                item = SalvageItem.objects.create(
                    item_code     = r['item_code'],
                    part_name     = r['part_name'],
                    claim_number  = r['claim_number'],
                    condition     = r['condition'],
                    status        = r['status'],
                    asking_price  = r['asking_price'],
                    reserve_price = r['reserve_price'],
                    cost_basis    = r['cost_basis'],
                    location      = r['location'],
                    received_date = r['received_date'] or timezone.localdate(),
                    notes         = r['notes'],
                    company       = company,
                    created_by    = request.user,
                    received_by   = request.user,
                )
                created += 1
                if auto_post:
                    try:
                        je = post_intake_to_gl(item, user=request.user)
                        if je is not None:
                            je_count += 1
                    except Exception:                          # noqa: BLE001
                        log.exception('Intake JE failed for %s during bulk import.', item.item_code)

        return Response(
            {'created':            created,
             'skipped':            0,
             'intake_jes_posted':  je_count,
             'company':            getattr(company, 'code', '') if company else '',
             'message':            f'Imported {created} salvage items. {je_count} intake JEs posted.'},
            status=drf_status.HTTP_201_CREATED,
        )
