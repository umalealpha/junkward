"""salvage/api_views.py — salvage portal endpoints.

Phase 1 (existing): read-only inventory + masterdata.
Phase 2 (2026-05-18): BuyerQuote create (public + staff review), Sale
record, SalvageApproval queue.
"""
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .models import (
    BuyerQuote, PartCategory, Sale, SalvageApproval, SalvageItem,
    VehicleBrand, VehicleModel,
)
from core.mixins import CompanyScopedViewSetMixin
from .permissions import IsSalvageUser, user_can_access_salvage
from .services import (
    maybe_create_approval_for_quote,
    maybe_create_approval_for_sale,
    post_sale_to_gl,
    suggest_reserve,
)
from .serializers import (
    BuyerQuoteCreateSerializer,
    BuyerQuoteSerializer,
    PartCategorySerializer,
    PublicSalvageItemSerializer,
    SaleSerializer,
    SalvageApprovalSerializer,
    SalvageItemDetailSerializer,
    SalvageItemListSerializer,
    VehicleBrandSerializer,
    VehicleModelSerializer,
)


# ---------------------------------------------------------------------------
# Inventory (auth-gated, full detail)
# ---------------------------------------------------------------------------
class SalvageItemViewSet(CompanyScopedViewSetMixin,
                          mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.CreateModelMixin,
                          viewsets.GenericViewSet):
    """Read + create. Mutating verbs (update/delete) intentionally absent —
    salvage items are append-only; status transitions happen on related rows
    (BuyerQuote / Sale) so the audit trail is always reconstructable.
    """

    permission_classes = [IsSalvageUser]
    queryset           = SalvageItem.objects.select_related(
                            'category', 'vehicle_brand', 'vehicle_model', 'company',
                         ).prefetch_related('images', 'buyer_quotes').order_by('-created_at')
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = [
        'item_code', 'part_name', 'part_description',
        'claim_number', 'policy_number', 'vin_number',
    ]
    ordering_fields    = ['created_at', 'asking_price', 'item_code']

    def get_queryset(self):
        # super() = CompanyScopedViewSetMixin: strict entity isolation
        # (gates the requested ?company= against the user's UserCompanyAccess
        # and, with no param, scopes to their allowed set). Replaces the old
        # resolve_company_id_param call, which did NOT enforce isolation —
        # a scoped user could read another entity's salvage. (Audit 2026-06-20)
        qs = super().get_queryset()
        for f in ('status', 'condition'):
            v = self.request.query_params.get(f)
            if v:
                qs = qs.filter(**{f: v})
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return SalvageItemListSerializer
        return SalvageItemDetailSerializer

    def perform_create(self, serializer):
        """Save the item then auto-post the intake JE.

        CFO directive 2026-05-18: an insurer's salvage stock is an asset
        on the balance sheet from the moment the claim is written off.
        post_intake_to_gl creates the Dr Inventory / Cr Recoveries entry
        at item.cost_basis. Skips when cost_basis is zero.
        """
        from .services import post_intake_to_gl
        item = serializer.save(
            created_by=self.request.user,
            received_by=self.request.user,
        )
        try:
            post_intake_to_gl(item, user=self.request.user)
        except Exception:                                      # noqa: BLE001
            import logging
            logging.getLogger(__name__).exception(
                'Salvage intake JE failed for item %s — row saved, GL untouched.',
                item.pk,
            )

    @action(detail=True, methods=['get'], url_path='suggest-reserve')
    def suggest_reserve(self, request, pk=None):
        """GET /api/v1/salvage-items/<id>/suggest-reserve/

        Returns a non-binding reserve-price suggestion sourced from:
          - claims gross amount for the linked claim_number, AND
          - the category's expected_recovery_pct (default 30%).

        Response:
            {
              "item_id": "<uuid>",
              "claim_number": "CLM-2026-...",
              "category": "<name|null>",
              "expected_recovery_pct": "0.3000",
              "suggested_reserve": "12345.67",
              "current_reserve": "10000.00"
            }

        The endpoint does NOT mutate the item — the CFO / yard manager
        applies it (or doesn't) via the regular PATCH flow.
        """
        item = self.get_object()
        from decimal import Decimal as _D
        pct = _D('0.30')
        cat_name = None
        if item.category_id and item.category is not None:
            cat_name = item.category.name
            if item.category.expected_recovery_pct is not None:
                pct = _D(item.category.expected_recovery_pct)

        suggested = suggest_reserve(item)
        return Response({
            'item_id':               str(item.pk),
            'claim_number':          item.claim_number or '',
            'category':              cat_name,
            'expected_recovery_pct': f'{pct:.4f}',
            'suggested_reserve':     f'{suggested:.2f}',
            'current_reserve':       f'{_D(item.reserve_price or 0):.2f}',
        })


class PartCategoryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsSalvageUser]
    queryset           = PartCategory.objects.filter(is_active=True).order_by('name')
    serializer_class   = PartCategorySerializer
    pagination_class   = None


class VehicleBrandViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsSalvageUser]
    queryset           = VehicleBrand.objects.filter(is_active=True).order_by('name')
    serializer_class   = VehicleBrandSerializer
    pagination_class   = None


class VehicleModelViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsSalvageUser]
    queryset           = VehicleModel.objects.select_related('brand') \
                                              .filter(is_active=True) \
                                              .order_by('brand__name', 'name')
    serializer_class   = VehicleModelSerializer
    pagination_class   = None

    def get_queryset(self):
        qs = super().get_queryset()
        brand = self.request.query_params.get('brand')
        if brand:
            qs = qs.filter(brand_id=brand)
        return qs


class SalvageAccessProbeView(APIView):
    """GET /api/v1/salvage/me-can-access/ — sidebar probe."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        allowed = user_can_access_salvage(request.user, request=request)
        return Response({
            'can_access': allowed,
            'reason': (
                'VCM/ADIC user or CFO/superuser' if allowed
                else 'restricted to Veritas (VCM) and Alpha Direct (ADIC)'
            ),
        })


# ---------------------------------------------------------------------------
# Buyer quotes (staff review)
# ---------------------------------------------------------------------------
class BuyerQuoteViewSet(viewsets.ModelViewSet):
    """Staff review queue for offers submitted via the public storefront."""
    permission_classes = [IsSalvageUser]
    queryset           = BuyerQuote.objects.select_related(
                             'item', 'reviewed_by',
                         ).order_by('-created_at')
    serializer_class   = BuyerQuoteSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        for f in ('status',):
            v = self.request.query_params.get(f)
            if v:
                qs = qs.filter(**{f: v})
        item = self.request.query_params.get('item')
        if item:
            qs = qs.filter(item_id=item)
        return qs

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def review(self, request, pk=None):
        """POST /api/v1/salvage/buyer-quotes/<id>/review/

        Body: { decision: 'accepted'|'rejected'|'countered',
                counter_price?: number, notes?: string }
        """
        quote = self.get_object()
        decision = (request.data.get('decision') or '').lower()
        if decision not in {'accepted', 'rejected', 'countered'}:
            return Response(
                {'detail': 'decision must be accepted, rejected, or countered.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quote.status = decision
        quote.review_notes = request.data.get('notes', '') or ''
        quote.reviewed_by = request.user
        quote.reviewed_at = timezone.now()
        if decision == 'countered':
            cp = request.data.get('counter_price')
            if cp in (None, ''):
                return Response(
                    {'detail': 'counter_price is required when countering.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            quote.counter_price = cp

        quote.save()

        # When a quote is accepted, flip the item to QUOTED so other buyers
        # see it isn't freely available anymore. The sale step later moves
        # it to SOLD.
        approval = None
        if decision == 'accepted':
            SalvageItem.objects.filter(pk=quote.item_id).update(
                status=SalvageItem.Status.QUOTED,
            )
            # Threshold-driven approval — see salvage.services for the rules.
            approval = maybe_create_approval_for_quote(quote, user=request.user)

        data = BuyerQuoteSerializer(quote).data
        data['approval_required'] = bool(approval)
        if approval:
            data['approval'] = SalvageApprovalSerializer(approval).data
        return Response(data)


# ---------------------------------------------------------------------------
# Sales
# ---------------------------------------------------------------------------
class SaleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSalvageUser]
    queryset           = Sale.objects.select_related(
                             'item', 'buyer_quote', 'approved_by', 'sold_by',
                         ).order_by('-sale_date', '-created_at')
    serializer_class   = SaleSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            sale = serializer.save(sold_by=self.request.user)
            SalvageItem.objects.filter(pk=sale.item_id).update(
                status=SalvageItem.Status.SOLD,
                sold_date=sale.sale_date,
            )
            # Threshold approval: sale < reserve_price or > config threshold.
            maybe_create_approval_for_sale(sale, user=self.request.user)
            # GL posting: DR cash, CR salvage income. Silent no-op if the
            # configured account codes aren't in the CoA.
            try:
                post_sale_to_gl(sale, user=self.request.user)
            except Exception:  # noqa: BLE001
                # Sale row stays; the GL failure is logged inside the service.
                pass


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------
class SalvageApprovalViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSalvageUser]
    queryset           = SalvageApproval.objects.select_related(
                             'item', 'requested_by', 'approved_by',
                         ).order_by('-created_at')
    serializer_class   = SalvageApprovalSerializer

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """POST /api/v1/salvage/approvals/<id>/resolve/
        Body: { decision: 'approved'|'rejected', notes?: string }"""
        appr = self.get_object()
        decision = (request.data.get('decision') or '').lower()
        if decision not in {'approved', 'rejected'}:
            return Response(
                {'detail': 'decision must be approved or rejected.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        appr.status = decision
        appr.approved_by = request.user
        appr.resolved_at = timezone.now()
        notes = request.data.get('notes', '')
        if notes:
            appr.notes = (appr.notes + '\n---\n' + notes) if appr.notes else notes
        appr.save()
        return Response(SalvageApprovalSerializer(appr).data)


# ---------------------------------------------------------------------------
# PUBLIC STOREFRONT — no auth required
# ---------------------------------------------------------------------------
class PublicStorefrontThrottle(AnonRateThrottle):
    rate = '60/minute'


class PublicSalvageListView(APIView):
    """GET /api/v1/salvage/public/items/

    Returns the catalogue of available salvage items for the public-
    facing storefront. No auth required. Read-only.

    Filters: ?q=... (full-text), ?brand=<id>, ?category=<id>, ?max_price=
    """
    permission_classes = [AllowAny]
    throttle_classes   = [PublicStorefrontThrottle]
    authentication_classes = []

    def get(self, request):
        qs = SalvageItem.objects.filter(
            status=SalvageItem.Status.AVAILABLE,
        ).select_related('category', 'vehicle_brand', 'vehicle_model') \
         .prefetch_related('images')

        q = request.query_params.get('q')
        if q:
            qs = qs.filter(part_name__icontains=q) \
              | qs.filter(part_description__icontains=q)
        brand = request.query_params.get('brand')
        if brand:
            qs = qs.filter(vehicle_brand_id=brand)
        category = request.query_params.get('category')
        if category:
            qs = qs.filter(category_id=category)
        max_price = request.query_params.get('max_price')
        if max_price:
            try:
                qs = qs.filter(asking_price__lte=float(max_price))
            except (TypeError, ValueError):
                pass

        # Cap to 200 items — no full enumeration of inventory exposed.
        qs = qs.order_by('-created_at')[:200]
        ser = PublicSalvageItemSerializer(qs, many=True, context={'request': request})
        return Response({'count': len(ser.data), 'results': ser.data})


class PublicSalvageDetailView(APIView):
    """GET /api/v1/salvage/public/items/<item_code>/"""
    permission_classes = [AllowAny]
    throttle_classes   = [PublicStorefrontThrottle]
    authentication_classes = []

    def get(self, request, item_code):
        item = get_object_or_404(
            SalvageItem.objects.select_related(
                'category', 'vehicle_brand', 'vehicle_model',
            ).prefetch_related('images'),
            item_code=item_code,
            status=SalvageItem.Status.AVAILABLE,
        )
        return Response(
            PublicSalvageItemSerializer(item, context={'request': request}).data
        )


class PublicSalvageQuoteSubmitView(APIView):
    """POST /api/v1/salvage/public/quotes/

    Public buyer submits an offer. No auth required. Captures IP + UA
    on the quote for audit / abuse triage.
    """
    permission_classes = [AllowAny]
    throttle_classes   = [PublicStorefrontThrottle]
    authentication_classes = []

    def post(self, request):
        ser = BuyerQuoteCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        # Re-fetch the item to ensure it's still available — protects
        # against a race where two buyers submit on the same item.
        item = SalvageItem.objects.filter(
            pk=ser.validated_data['item'].pk,
            status__in=[SalvageItem.Status.AVAILABLE, SalvageItem.Status.QUOTED],
        ).first()
        if not item:
            return Response(
                {'detail': 'Item is no longer available for quotation.'},
                status=status.HTTP_409_CONFLICT,
            )

        ip = (request.META.get('HTTP_X_FORWARDED_FOR', '')
              .split(',')[0].strip() or request.META.get('REMOTE_ADDR'))
        ua = request.META.get('HTTP_USER_AGENT', '')[:400]
        quote = ser.save(submitter_ip=ip or None, submitter_ua=ua)

        return Response(
            {
                'id': str(quote.pk),
                'received_at': quote.created_at.isoformat(),
                'message': ('Thank you. Your offer has been received and will '
                            'be reviewed within one business day. We will '
                            'contact you on the phone or email you provided.'),
            },
            status=status.HTTP_201_CREATED,
        )
