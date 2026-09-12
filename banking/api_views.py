"""banking/api_views.py"""
from django.core.exceptions import ValidationError
from rest_framework import filters, mixins, parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.mixins import CompanyScopedViewSetMixin
from core.permissions import CanViewFinancials
from .models import BankAccount, BankRecRule, BankStatement, BankStatementLine
from .rec_engine import match_statement_lines
from .serializers import (
    BankAccountSerializer,
    BankRecRuleSerializer,
    BankStatementDetailSerializer,
    BankStatementLineSerializer,
    BankStatementListSerializer,
)
from .services import BankStatementImporter, ReconciliationEngine


def _refresh_recon_state(stmt: BankStatement, user=None) -> None:
    """
    Recompute a statement's reconciliation status after any matching activity.

    Fully matched → PENDING_APPROVAL (not RECONCILED). Segregation of duties
    (BUG b72695a8): the person who matches the lines (reconciled_by) cannot
    finalise their own work — a second person holding `bank.approve` must
    approve it (see approve_reconciliation) before it counts as Reconciled and
    BankAccount.last_reconciled_date is stamped. This mirrors je.submit→approve
    and po.create→fm_approve.
    """
    unmatched = stmt.lines.filter(
        match_status=BankStatementLine.MatchStatus.UNMATCHED
    ).count()
    total = stmt.lines.count()
    if total and unmatched == 0:
        # All lines matched → hand off to an independent approver. Do NOT mark
        # RECONCILED or stamp last_reconciled_date here — that happens only on
        # approval by a different user.
        if stmt.status != BankStatement.Status.RECONCILED:
            stmt.status = BankStatement.Status.PENDING_APPROVAL
            if user is not None and stmt.reconciled_by_id is None:
                stmt.reconciled_by = user
            stmt.save(update_fields=['status', 'reconciled_by', 'updated_at'])
    elif unmatched < total:
        if stmt.status not in (BankStatement.Status.IN_PROGRESS,
                               BankStatement.Status.RECONCILED):
            stmt.status = BankStatement.Status.IN_PROGRESS
            stmt.save(update_fields=['status', 'updated_at'])


class BankAccountViewSet(CompanyScopedViewSetMixin,
                          mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          viewsets.GenericViewSet):
    # CFO structural audit 2026-05-19: scope BankAccount via its GL account's
    # owner_company so the topbar entity filter survives.
    # SECURITY FIX (2026-07-14): this had no gate beyond IsAuthenticated — any
    # employee scoped to a company could read its bank account numbers.
    permission_classes = [IsAuthenticated, CanViewFinancials]
    company_lookup_field = 'gl_account__owner_company_id'
    queryset = BankAccount.objects.select_related(
        'gl_account', 'currency_code'
    ).filter(
        is_active=True,
        gl_account__is_active=True,           # honour BANK-003 deactivations
        gl_account__is_bank_account=True,     # exclude post-reclass non-cash GLs (BANK-005b)
    ).order_by('bank_name', 'account_name')
    serializer_class = BankAccountSerializer
    filter_backends  = [filters.SearchFilter]
    search_fields    = ['bank_name', 'account_name', 'account_number']

    def get_queryset(self):
        # Company filter is applied by CompanyScopedViewSetMixin via the
        # `company_lookup_field = 'gl_account__owner_company_id'` override.
        return super().get_queryset()

    def get_serializer_context(self):
        # CFO directive 2026-05-25 (BANK-001): the /banking page must
        # show the GL truth, not the cached `current_balance` field.
        # Pull JEL aggregate for every linked GL account in one query
        # + the latest BankStatement closing balance per BankAccount.
        from decimal import Decimal
        from django.db.models import Sum
        from ledger.models import JournalEntry, JournalEntryLine

        ctx = super().get_serializer_context()
        qs = self.get_queryset()
        gl_ids = list(qs.values_list('gl_account_id', flat=True))
        zero = Decimal('0.00')

        book_balances: dict = {}
        if gl_ids:
            rows = (
                JournalEntryLine.objects
                .filter(
                    account_id__in=gl_ids,
                    journal_entry__status=JournalEntry.Status.POSTED,
                )
                .values('account_id')
                .annotate(dr=Sum('debit_bwp'), cr=Sum('credit_bwp'))
            )
            for r in rows:
                bal = (r['dr'] or zero) - (r['cr'] or zero)
                book_balances[r['account_id']] = str(bal.quantize(Decimal('0.01')))
        ctx['book_balances'] = book_balances

        latest_statements: dict = {}
        ba_ids = list(qs.values_list('id', flat=True))
        if ba_ids:
            for stmt in (
                BankStatement.objects.filter(bank_account_id__in=ba_ids)
                .order_by('bank_account_id', '-statement_date')
            ):
                if stmt.bank_account_id not in latest_statements:
                    latest_statements[stmt.bank_account_id] = {
                        'closing_balance': stmt.closing_balance,
                        'statement_date': stmt.statement_date,
                    }
        ctx['latest_statements'] = latest_statements
        return ctx


class BankStatementViewSet(CompanyScopedViewSetMixin,
                            mixins.ListModelMixin,
                            mixins.RetrieveModelMixin,
                            viewsets.GenericViewSet):
    # CFO directive 2026-05-19 (Manus master guide § 1): scope statements
    # via the bank account's GL account owner_company.
    # SECURITY FIX (2026-07-14): this had no gate beyond IsAuthenticated — any
    # employee scoped to a company could read its bank statements.
    permission_classes = [IsAuthenticated, CanViewFinancials]
    company_lookup_field = 'bank_account__gl_account__owner_company_id'
    queryset = BankStatement.objects.select_related(
        'bank_account', 'imported_by'
    ).order_by('-statement_date', '-import_date')
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields   = ['statement_number', 'bank_account__account_name', 'file_name']
    ordering_fields = ['statement_date', 'import_date', 'status']

    def get_serializer_class(self):
        if self.action in ('retrieve', 'import_statement', 'run_matching'):
            return BankStatementDetailSerializer
        return BankStatementListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        ba = self.request.query_params.get('bank_account')
        if ba:
            qs = qs.filter(bank_account_id=ba)
        st = self.request.query_params.get('status')
        if st:
            qs = qs.filter(status=st)
        return qs

    @action(
        detail=False, methods=['post'], url_path='import',
        parser_classes=[parsers.MultiPartParser, parsers.FormParser],
    )
    def import_statement(self, request):
        """
        POST /api/v1/bank-statements/import/
        Body (multipart/form-data):
          file            - CSV or .xlsx statement file
          bank_account_id - UUID of BankAccount
          format_name     - optional BankStatementFormat name. When omitted the
                            columns are read off the file's own header row.

        Bug 713d6218 (2026-08-03): this used to default to a format named
        'FNB BWP Current Account'. No BankStatementFormat rows existed on prod,
        so every single upload returned "Statement format ... not found" — the
        button had never worked. Excel files also died on .decode(). Now a named
        format still wins if given, otherwise the file describes itself.
        """
        from .models import BankStatementFormat
        from .statement_files import (
            StatementFileError, build_format_from_file, strip_preamble, to_csv_text,
        )

        csv_file       = request.FILES.get('file')
        # Accept either key — the upload modal historically posted 'bank_account'
        # while this view read 'bank_account_id', which surfaced as a spurious
        # "bank_account_id is required" (2026-06-08). Tolerate both.
        bank_account_id = request.data.get('bank_account_id') or request.data.get('bank_account')
        format_name    = (request.data.get('format_name') or '').strip()

        if not csv_file:
            return Response({'error': 'No file uploaded.'}, status=status.HTTP_400_BAD_REQUEST)
        if not bank_account_id:
            return Response({'error': 'bank_account_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            bank_account = BankAccount.objects.get(pk=bank_account_id)
        except BankAccount.DoesNotExist:
            return Response({'error': 'BankAccount not found.'}, status=status.HTTP_404_NOT_FOUND)

        fmt = None
        if format_name:
            fmt = BankStatementFormat.objects.filter(name=format_name).first()
            if fmt is None:
                known = list(
                    BankStatementFormat.objects.values_list('name', flat=True)[:10]
                )
                return Response(
                    {'error': (
                        f"Statement format '{format_name}' is not set up."
                        + (f" Formats available: {', '.join(known)}." if known
                           else ' Leave the format blank and the columns will be '
                                'read from the file itself.')
                    )},
                    status=status.HTTP_404_NOT_FOUND,
                )

        try:
            csv_text = to_csv_text(csv_file, encoding=(fmt.encoding if fmt else 'utf-8'))
            if fmt is None:
                fmt, skip = build_format_from_file(
                    csv_text, bank_name=bank_account.bank_name or '')
                csv_text = strip_preamble(csv_text, skip)
            importer = BankStatementImporter(fmt)
            stmt = importer.import_csv(
                csv_text, bank_account,
                user=request.user,
                file_name=csv_file.name,
            )
        except StatementFileError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = BankStatementDetailSerializer(stmt, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='run-matching')
    def run_matching(self, request, pk=None):
        """
        POST /api/v1/bank-statements/{pk}/run-matching/
        Runs the auto-matching engine. Returns match counts.
        """
        stmt   = self.get_object()
        engine = ReconciliationEngine(stmt)
        result = engine.run()
        return Response(result)

    @action(detail=True, methods=['post'], url_path='auto-reconcile')
    def auto_reconcile(self, request, pk=None):
        """
        POST /api/v1/bank-statements/{pk}/auto-reconcile/
        Run the rule-based reconciliation engine (banking.rec_engine).

        Body (all optional):
          {"dry_run": true}   -> preview without persisting

        Returns
          {"two_way_matched": N, "rule_matched": N, "still_unmatched": N}
        """
        stmt = self.get_object()
        dry  = bool(request.data.get('dry_run', False))
        try:
            counts = match_statement_lines(stmt, dry_run=dry)
        except Exception as exc:                            # noqa: BLE001
            return Response({'error': str(exc)},
                            status=status.HTTP_400_BAD_REQUEST)
        if not dry:
            _refresh_recon_state(stmt, user=request.user)
        return Response(counts)

    @action(detail=True, methods=['post'], url_path='approve-reconciliation')
    def approve_reconciliation(self, request, pk=None):
        """
        POST /api/v1/bank-statements/{pk}/approve-reconciliation/
        Second-person approval of a completed reconciliation (BUG b72695a8).

        Segregation of duties:
          * requires the `bank.approve` permission;
          * the approver MUST be a different user from `reconciled_by`;
          * statement must be PENDING_APPROVAL (fully matched, awaiting sign-off).
        Only on approval is the statement marked RECONCILED and the bank
        account's last_reconciled_date stamped.
        """
        from django.utils import timezone
        from core.models import user_has_permission

        stmt = self.get_object()
        if not user_has_permission(request.user, 'bank.approve'):
            return Response(
                {'detail': 'You do not have the bank.approve permission to '
                           'approve a bank reconciliation.'},
                status=status.HTTP_403_FORBIDDEN)
        if stmt.status != BankStatement.Status.PENDING_APPROVAL:
            return Response(
                {'detail': f'Statement is "{stmt.get_status_display()}" — only a '
                           'fully-matched reconciliation awaiting approval can be approved.'},
                status=status.HTTP_400_BAD_REQUEST)
        if stmt.reconciled_by_id and stmt.reconciled_by_id == request.user.pk:
            return Response(
                {'detail': 'Segregation of duties: you reconciled this statement, '
                           'so a different person must approve it.'},
                status=status.HTTP_403_FORBIDDEN)

        stmt.status      = BankStatement.Status.RECONCILED
        stmt.approved_by = request.user
        stmt.approved_at = timezone.now()
        stmt.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
        acct = stmt.bank_account
        if (acct.last_reconciled_date is None
                or stmt.statement_date > acct.last_reconciled_date):
            acct.last_reconciled_date = stmt.statement_date
            acct.save(update_fields=['last_reconciled_date', 'updated_at'])
        return Response({
            'status':       stmt.status,
            'approved_by':  request.user.get_username(),
            'reconciled_by': stmt.reconciled_by.get_username() if stmt.reconciled_by_id else None,
        })


class BankStatementLineViewSet(mixins.ListModelMixin,
                                mixins.RetrieveModelMixin,
                                viewsets.GenericViewSet):
    # SECURITY FIX (2026-07-14): had no gate beyond IsAuthenticated, and unlike
    # its sibling viewsets isn't even company-scoped — any employee could read
    # any bank statement's transaction lines by ?statement=<id>.
    permission_classes = [IsAuthenticated, CanViewFinancials]
    queryset = BankStatementLine.objects.select_related(
        'statement__bank_account', 'matched_payment', 'matched_journal_entry'
    ).order_by('statement', 'line_number')
    serializer_class = BankStatementLineSerializer
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['description', 'reference', 'statement__statement_number']
    ordering_fields  = ['transaction_date', 'amount', 'match_status']

    def get_queryset(self):
        qs = super().get_queryset()
        stmt = self.request.query_params.get('statement')
        if stmt:
            qs = qs.filter(statement_id=stmt)
        ms = self.request.query_params.get('match_status')
        if ms:
            qs = qs.filter(match_status=ms)
        return qs

    @action(detail=True, methods=['post'], url_path='match')
    def match(self, request, pk=None):
        """
        POST /api/v1/bank-statement-lines/{pk}/match/
        Body: {"payment_id": "uuid"} or {"journal_entry_id": "uuid"}
        Manually matches a statement line to a payment or JE.
        """
        line       = self.get_object()
        payment_id = request.data.get('payment_id')
        je_id      = request.data.get('journal_entry_id')

        if not payment_id and not je_id:
            return Response(
                {'error': 'Provide payment_id or journal_entry_id.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment_id:
            from payments.models import Payment
            try:
                payment = Payment.objects.get(pk=payment_id)
            except Payment.DoesNotExist:
                return Response({'error': 'Payment not found.'}, status=status.HTTP_404_NOT_FOUND)
            # Validate amount matches (abs comparison for sign differences)
            if abs(line.amount) != abs(payment.amount):
                return Response(
                    {'error': f'Amount mismatch: statement line {line.amount} vs payment {payment.amount}.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            line.matched_payment    = payment
            line.matched_journal_entry = None

        elif je_id:
            from ledger.models import JournalEntry
            try:
                je = JournalEntry.objects.get(pk=je_id)
            except JournalEntry.DoesNotExist:
                return Response({'error': 'Journal entry not found.'}, status=status.HTTP_404_NOT_FOUND)
            line.matched_journal_entry = je
            line.matched_payment       = None

        line.match_status     = BankStatementLine.MatchStatus.MANUALLY_MATCHED
        line.match_confidence = 100
        line.save()
        _refresh_recon_state(line.statement, user=request.user)

        serializer = BankStatementLineSerializer(line, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='create-payment')
    def create_payment(self, request, pk=None):
        """PAY-003 init path #2 — "Create Payment" from a bank-rec line.

        Creates a draft SENT payment from this statement line (amount, date,
        the statement's GL bank account), submits it into the SAME tier
        approval queue as the bill-"Pay" path, and links the line to it
        (matched_payment). Once the approver approves, the payment posts
        DR AP / CR Bank exactly like the bill path. Body:
          {contact_id, reference(optional), payment_method(optional),
           bill_id(optional — allocate to this bill)}
        """
        from decimal import Decimal
        from django.db import transaction as _txn
        from django.core.exceptions import ValidationError as _VErr
        from payments.models import Payment, PaymentAllocation
        from payments.serializers import PaymentDetailSerializer
        from billing.models import Contact, Invoice

        line = self.get_object()
        if line.matched_payment_id:
            return Response(
                {'error': f'Line already linked to payment {line.matched_payment.payment_number}.'},
                status=status.HTTP_400_BAD_REQUEST)
        if line.amount >= 0:
            return Response(
                {'error': 'Create-Payment is for outflow (negative) lines only.'},
                status=status.HTTP_400_BAD_REQUEST)

        contact_id = request.data.get('contact_id')
        if not contact_id:
            return Response({'error': 'contact_id is required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            contact = Contact.objects.get(pk=contact_id)
        except Contact.DoesNotExist:
            return Response({'error': 'Contact not found.'}, status=status.HTTP_404_NOT_FOUND)

        bank_acct = line.statement.bank_account
        gl = bank_acct.gl_account
        if gl is None:
            return Response(
                {'error': f'Bank account {bank_acct} has no linked GL account.'},
                status=status.HTTP_400_BAD_REQUEST)

        amount    = abs(line.amount)
        reference = (request.data.get('reference') or line.reference or line.description or '')[:200]
        method    = request.data.get('payment_method') or Payment.PaymentMethod.BANK_TRANSFER
        bill_id   = request.data.get('bill_id')

        try:
            with _txn.atomic():
                payment = Payment(
                    payment_type   = Payment.PaymentType.SENT,
                    contact        = contact,
                    company        = getattr(gl, 'owner_company', None) or getattr(bank_acct, 'company', None),
                    bank_account   = gl,
                    payment_date   = line.transaction_date,
                    currency_code_id = bank_acct.currency_code_id or 'BWP',
                    amount         = amount,
                    payment_method = method,
                    reference      = reference,
                    description    = f"PAY-003 bank-rec payment — stmt line {line.line_number}",
                    created_by     = request.user,
                )
                payment.save(audit_user=request.user)
                if bill_id:
                    try:
                        bill = Invoice.objects.get(pk=bill_id)
                        PaymentAllocation.objects.create(
                            payment=payment, invoice=bill,
                            amount_allocated=min(amount, bill.total_amount or amount))
                    except Invoice.DoesNotExist:
                        pass
                tier, role = payment.submit_for_approval(user=request.user)
                # Link the line to the new payment (pending approval).
                line.matched_payment    = payment
                line.match_status       = BankStatementLine.MatchStatus.MANUALLY_MATCHED
                line.match_confidence   = 100
                line.save()
        except (_VErr, Exception) as e:
            msg = e.messages[0] if hasattr(e, 'messages') else str(e)
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)

        _refresh_recon_state(line.statement, user=request.user)
        data = PaymentDetailSerializer(payment, context={'request': request}).data
        data['assigned_tier'] = tier
        data['assigned_role'] = role
        data['statement_line_id'] = str(line.pk)
        return Response(data, status=status.HTTP_201_CREATED)


class BankRecRuleViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    """
    Full CRUD for BankRecRule. Scoped via the rule's `company_id` so the
    topbar entity switcher filters correctly.

    SECURITY FIX (2026-07-14): had no gate beyond IsAuthenticated.

    Routes (after `api_router.register('bank-rec-rules', ...)`):
      GET    /api/v1/bank-rec-rules/
      POST   /api/v1/bank-rec-rules/
      GET    /api/v1/bank-rec-rules/<id>/
      PATCH  /api/v1/bank-rec-rules/<id>/
      DELETE /api/v1/bank-rec-rules/<id>/
    """
    permission_classes = [IsAuthenticated, CanViewFinancials]
    company_lookup_field = 'company_id'
    queryset = BankRecRule.objects.select_related(
        'company', 'target_account', 'target_contact', 'created_by',
    ).order_by('priority', 'created_at')
    serializer_class = BankRecRuleSerializer
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['description_regex', 'target_account__code',
                        'target_account__name', 'target_contact__name']
    ordering_fields  = ['priority', 'created_at', 'is_active']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
