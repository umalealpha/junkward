"""
banking/models.py

BankAccount            - maps a GL account to a real bank account
BankStatementFormat    - configurable CSV parsing rules per bank
BankStatement          - header record for one imported statement file
BankStatementLine      - individual transaction row from the statement
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models

from core.models import AuditableMixin, BaseModel, Currency


TWO_PLACES = Decimal('0.01')
ZERO       = Decimal('0.00')


# ---------------------------------------------------------------------------
# BankAccount
# ---------------------------------------------------------------------------

class BankAccount(AuditableMixin, BaseModel):
    """
    Links a real bank account to its corresponding GL clearing account.
    The GL account must have ``is_bank_account=True``.
    """

    gl_account = models.OneToOneField(
        'ledger.Account',
        on_delete=models.PROTECT,
        related_name='bank_account_detail',
        help_text='GL account (is_bank_account must be True)',
    )
    bank_name      = models.CharField(max_length=100)
    account_name   = models.CharField(max_length=200)
    account_number = models.CharField(max_length=50)
    branch_code    = models.CharField(max_length=20, blank=True, null=True)
    currency_code  = models.ForeignKey(
        Currency, on_delete=models.PROTECT, default='BWP',
    )
    is_active            = models.BooleanField(default=True)
    # CFO directive 2026-05-25: FM wants to hide accounts they don't care
    # about from the FNB Integration UI (e.g. E-Wallet Pro Chimidza)
    # without deactivating them everywhere. Soft-hide flag, FNB page
    # filters it out by default but exposes a "Show hidden" toggle.
    hide_in_banking_ui   = models.BooleanField(default=False)
    current_balance      = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO,
    )
    last_reconciled_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['bank_name', 'account_name']

    def __str__(self):
        return f"{self.bank_name} - {self.account_name} ({self.account_number})"


# ---------------------------------------------------------------------------
# BankStatementFormat
# ---------------------------------------------------------------------------

class BankStatementFormat(BaseModel):
    """
    Describes how to parse a CSV bank statement from a specific bank.

    Supply either ``amount_column`` OR both ``debit_column`` and
    ``credit_column`` — not both styles at once.

    ``sign_convention`` only applies when ``amount_column`` is used.
    """

    class SignConvention(models.TextChoices):
        DEBIT_NEGATIVE = 'debit_negative', 'Negative = outflow (most banks)'
        DEBIT_POSITIVE = 'debit_positive', 'Positive = outflow (rare)'

    name      = models.CharField(max_length=100, unique=True)
    bank_name = models.CharField(max_length=100)
    delimiter = models.CharField(max_length=1, default=',')
    encoding  = models.CharField(max_length=20, default='utf-8')
    skip_rows = models.IntegerField(
        default=0,
        help_text='Non-header rows to skip before the data begins',
    )

    # Column names matched case-insensitively against the CSV header
    date_column        = models.CharField(max_length=100)
    date_format        = models.CharField(
        max_length=30, default='%d/%m/%Y',
        help_text="strptime format, e.g. %%d/%%m/%%Y",
    )
    description_column = models.CharField(max_length=100)
    reference_column   = models.CharField(max_length=100, blank=True, null=True)
    balance_column     = models.CharField(max_length=100, blank=True, null=True)

    # Single-amount-column mode
    amount_column    = models.CharField(max_length=100, blank=True, null=True)
    sign_convention  = models.CharField(
        max_length=20,
        choices=SignConvention.choices,
        default=SignConvention.DEBIT_NEGATIVE,
    )

    # Separate-debit-credit-column mode (mutually exclusive with amount_column)
    debit_column  = models.CharField(max_length=100, blank=True, null=True)
    credit_column = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['bank_name', 'name']

    def __str__(self):
        return f"{self.name} ({self.bank_name})"


# ---------------------------------------------------------------------------
# BankStatement
# ---------------------------------------------------------------------------

def _generate_statement_number():
    """Auto-number: STMT-YYYY-NNNNNN"""
    from django.utils import timezone
    from django.db import transaction as db_tx

    year   = timezone.now().year
    prefix = f"STMT-{year}-"
    with db_tx.atomic():
        last = (
            BankStatement.objects
            .select_for_update()
            .filter(statement_number__startswith=prefix)
            .order_by('-statement_number')
            .values_list('statement_number', flat=True)
            .first()
        )
        nxt = int(last.rsplit('-', 1)[-1]) + 1 if last else 1
        return f"{prefix}{nxt:06d}"


class BankStatement(AuditableMixin, BaseModel):
    """Header record for one imported bank statement file."""

    class Status(models.TextChoices):
        IMPORTED         = 'imported',         'Imported'
        IN_PROGRESS      = 'in_progress',      'Reconciliation in progress'
        PENDING_APPROVAL = 'pending_approval', 'Reconciled — awaiting approval'
        RECONCILED       = 'reconciled',       'Reconciled & approved'

    statement_number = models.CharField(max_length=30, unique=True, blank=True)
    bank_account     = models.ForeignKey(
        BankAccount, on_delete=models.PROTECT, related_name='statements',
    )
    statement_date  = models.DateField()
    opening_balance = models.DecimalField(max_digits=18, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=18, decimal_places=2)
    file_name       = models.CharField(max_length=255)
    import_date     = models.DateTimeField(auto_now_add=True)
    imported_by     = models.ForeignKey(
        User, null=True, on_delete=models.SET_NULL,
        related_name='imported_statements',
    )
    status     = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IMPORTED,
    )
    line_count = models.IntegerField(default=0)
    # Segregation of duties (BUG b72695a8, Oprah 2026-06-27): a reconciliation
    # is completed by one person (reconciled_by) and must be independently
    # APPROVED by a different person holding the `bank.approve` permission
    # before it counts as Reconciled. Mirrors the JE submit/approve and
    # PO create/fm_approve two-person controls.
    reconciled_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='reconciled_statements',
    )
    approved_by   = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='approved_statements',
    )
    approved_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-statement_date', '-import_date']

    def __str__(self):
        return (
            f"{self.statement_number} - "
            f"{self.bank_account.bank_name} {self.statement_date}"
        )

    def clean(self):
        # BUG-004: statement date cannot be in the future. "Today" is BOTSWANA's
        # today (settings.TIME_ZONE) — date.today() is the UTC date on a UTC box,
        # which called every statement dated today "future" between 00:00 and
        # 02:00 Gaborone (same midnight window as the JE guards, f9ff6d56).
        from django.core.exceptions import ValidationError
        from django.utils import timezone as _tz
        if self.statement_date and self.statement_date > _tz.localdate():
            raise ValidationError(
                {'statement_date': 'Statement date cannot be in the future.'}
            )

    def save(self, *args, **kwargs):
        if not self.statement_number:
            self.statement_number = _generate_statement_number()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# BankStatementLine
# ---------------------------------------------------------------------------

class BankStatementLine(BaseModel):
    """One transaction row from an imported bank statement."""

    class MatchStatus(models.TextChoices):
        UNMATCHED        = 'unmatched',        'Unmatched'
        AUTO_MATCHED     = 'auto_matched',     'Auto-matched'
        MANUALLY_MATCHED = 'manually_matched', 'Manually matched'
        EXCLUDED         = 'excluded',         'Excluded'

    statement        = models.ForeignKey(
        BankStatement, on_delete=models.CASCADE, related_name='lines',
    )
    line_number      = models.IntegerField()
    transaction_date = models.DateField()
    description      = models.CharField(max_length=500)
    reference        = models.CharField(max_length=200, blank=True, null=True)

    # Positive = inflow (money received), Negative = outflow (money sent)
    amount          = models.DecimalField(max_digits=18, decimal_places=2)
    running_balance = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True,
    )

    match_status = models.CharField(
        max_length=20,
        choices=MatchStatus.choices,
        default=MatchStatus.UNMATCHED,
    )
    matched_payment = models.ForeignKey(
        'payments.Payment',
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name='bank_statement_lines',
    )
    matched_journal_entry = models.ForeignKey(
        'ledger.JournalEntry',
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name='bank_statement_lines',
    )
    match_confidence = models.IntegerField(null=True, blank=True)
    notes            = models.TextField(blank=True, null=True)
    raw_data         = models.JSONField(null=True, blank=True)

    class Meta:
        ordering        = ['statement', 'line_number']
        unique_together = [('statement', 'line_number')]

    def __str__(self):
        direction = 'IN' if self.amount >= 0 else 'OUT'
        return (
            f"{self.statement.statement_number} "
            f"L{self.line_number:03d} "
            f"{self.transaction_date} "
            f"{direction} {abs(self.amount)}"
        )


# ---------------------------------------------------------------------------
# Bank reconciliation rule engine — imported from rec_rules_models so Django
# picks BankRecRule up under the `banking` app label without splitting models
# across modules at the ORM layer. See banking/rec_rules_models.py.
# ---------------------------------------------------------------------------
from .rec_rules_models import BankRecRule  # noqa: E402,F401
