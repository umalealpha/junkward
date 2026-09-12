"""
reinsurance/models.py

Reinsurance module — v1 backbone.

Models:
  • Reinsurer            counterparty (Munich Re, Swiss Re, Africa Re, ...)
  • ReinsuranceTreaty    a contract: type, period, share %, retention/limit
  • Cession              premium ceded to reinsurer (per-policy or per-bordereau)
  • ReinsuranceRecovery  claim recovery from reinsurer
  • BordereauImport      header for a CSV/XLSX bordereau upload from broker

GL accounts used (already in setup_chart_of_accounts):
  • 1230  Reinsurance receivable        — recoveries owed by the reinsurer
  • 2120  Reinsurance premium payable   — cessions owed to the reinsurer
  • 4200  Reinsurance premium ceded     — contra-revenue (P&L)
  • 5200  Claims recovered from reinsurers — contra-expense (P&L)

Cession JE:
    DR  4200 Reinsurance premium ceded
    CR  2120 Reinsurance premium payable

Recovery JE:
    DR  1230 Reinsurance receivable
    CR  5200 Claims recovered from reinsurers

This is a v1 backbone. Specifically NOT yet built:
  • Bordereau line model + line-level matching (header-only import for now)
  • Reinsurance commission split out from cession
  • Treaty layer / non-proportional structures (XL, surplus) calc helpers
  • IFRS 17 §63 reinsurance contract roll-forward report
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.utils import timezone

from core.models import AuditableMixin, BaseModel


ZERO = Decimal('0.00')


# ---------------------------------------------------------------------------
# Number generators
# ---------------------------------------------------------------------------

def _next_cession_number():
    year = timezone.now().year
    prefix = f'CES-{year}-'
    with transaction.atomic():
        last = (
            Cession.objects.select_for_update()
            .filter(cession_number__startswith=prefix)
            .order_by('-cession_number')
            .values_list('cession_number', flat=True).first()
        )
        seq = int(last.rsplit('-', 1)[-1]) + 1 if last else 1
        return f'{prefix}{seq:06d}'


def _next_recovery_number():
    year = timezone.now().year
    prefix = f'RCR-{year}-'
    with transaction.atomic():
        last = (
            ReinsuranceRecovery.objects.select_for_update()
            .filter(recovery_number__startswith=prefix)
            .order_by('-recovery_number')
            .values_list('recovery_number', flat=True).first()
        )
        seq = int(last.rsplit('-', 1)[-1]) + 1 if last else 1
        return f'{prefix}{seq:06d}'


def _next_bordereau_number():
    year = timezone.now().year
    prefix = f'BDX-{year}-'
    with transaction.atomic():
        last = (
            BordereauImport.objects.select_for_update()
            .filter(bordereau_number__startswith=prefix)
            .order_by('-bordereau_number')
            .values_list('bordereau_number', flat=True).first()
        )
        seq = int(last.rsplit('-', 1)[-1]) + 1 if last else 1
        return f'{prefix}{seq:06d}'


# ---------------------------------------------------------------------------
# Reinsurer
# ---------------------------------------------------------------------------

class Reinsurer(AuditableMixin, BaseModel):
    """A reinsurance counterparty."""

    name = models.CharField(max_length=200, unique=True)
    short_code = models.CharField(
        max_length=20, unique=True,
        help_text='Short code used in JE descriptions and reports (e.g. MUNICH_RE).',
    )
    country = models.CharField(max_length=2, default='BW',
                                help_text='ISO 3166-1 alpha-2.')
    credit_rating = models.CharField(
        max_length=10, blank=True,
        help_text='Latest counterparty rating (e.g. AA-, A+).',
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.short_code} — {self.name}'


# ---------------------------------------------------------------------------
# Treaty
# ---------------------------------------------------------------------------

class ReinsuranceTreaty(AuditableMixin, BaseModel):
    """A reinsurance contract.

    v1 supports proportional treaties (Quota Share, Surplus). Non-proportional
    (XL, Stop-Loss) is allowed at the type level but the calc helpers are
    flagged TBD.
    """

    class TreatyType(models.TextChoices):
        QUOTA_SHARE = 'quota_share',  'Quota Share (proportional)'
        SURPLUS     = 'surplus',      'Surplus (proportional)'
        XL          = 'xl',           'Excess of Loss (non-proportional)'
        STOP_LOSS   = 'stop_loss',    'Stop Loss (non-proportional)'
        FACULTATIVE = 'facultative',  'Facultative'

    class Status(models.TextChoices):
        DRAFT     = 'draft',     'Draft'
        ACTIVE    = 'active',    'Active'
        EXPIRED   = 'expired',   'Expired'
        CANCELLED = 'cancelled', 'Cancelled'

    treaty_number = models.CharField(max_length=40, unique=True)
    description = models.CharField(max_length=200)
    reinsurer = models.ForeignKey(
        Reinsurer, on_delete=models.PROTECT, related_name='treaties',
    )
    treaty_type = models.CharField(max_length=20, choices=TreatyType.choices)
    line_of_business = models.CharField(
        max_length=80,
        help_text='Motor / Property / Liability / All Lines / etc.',
    )
    inception_date = models.DateField()
    expiry_date = models.DateField()
    currency_code = models.ForeignKey(
        'core.Currency', on_delete=models.PROTECT, default='BWP',
    )

    # Proportional terms
    cession_share_percent = models.DecimalField(
        max_digits=6, decimal_places=4, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text='For QS/Surplus: % of each risk ceded.',
    )
    commission_percent = models.DecimalField(
        max_digits=6, decimal_places=4, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text='Reinsurance commission paid back to us.',
    )

    # Non-proportional terms
    retention_amount = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True,
        help_text='For XL: the retention layer below which we keep the loss.',
    )
    limit_amount = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True,
        help_text='For XL: the upper limit of the layer.',
    )

    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.DRAFT,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-inception_date', 'treaty_number']

    def __str__(self):
        return f'{self.treaty_number} — {self.description}'

    def clean(self):
        if self.expiry_date and self.inception_date and self.expiry_date < self.inception_date:
            raise ValidationError('Expiry date must be on or after inception date.')


# ---------------------------------------------------------------------------
# Cession
# ---------------------------------------------------------------------------

class Cession(AuditableMixin, BaseModel):
    """A premium cession to a reinsurer.

    Can be raised standalone or as part of a bordereau import. Posting to the
    GL is via the matching service function — see services.post_cession.
    """

    class Status(models.TextChoices):
        DRAFT  = 'draft',  'Draft'
        POSTED = 'posted', 'Posted'
        VOIDED = 'voided', 'Voided'

    cession_number = models.CharField(max_length=20, unique=True, editable=False)
    treaty = models.ForeignKey(
        ReinsuranceTreaty, on_delete=models.PROTECT, related_name='cessions',
    )
    cession_date = models.DateField(default=timezone.localdate)
    policy_reference = models.CharField(
        max_length=120, blank=True,
        help_text='Graphite policy number this cession relates to (optional).',
    )
    risk_description = models.CharField(max_length=200, blank=True)

    gross_premium = models.DecimalField(max_digits=18, decimal_places=2)
    ceded_premium = models.DecimalField(max_digits=18, decimal_places=2)
    commission_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO,
        help_text='Reinsurance commission earned (net off the cession).',
    )

    bordereau = models.ForeignKey(
        'BordereauImport', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='cessions',
    )

    # ----- Auto-cession (CFO directive — cession_service.run_cession_pass) ----
    # When a Cession is generated by the auto-cession pass off a posted
    # customer invoice we keep the link back to the source invoice. This
    # FK is also the idempotency anchor — (invoice, treaty) is enforced
    # unique below so re-running the pass is safe.
    invoice = models.ForeignKey(
        'billing.Invoice', null=True, blank=True,
        on_delete=models.PROTECT, related_name='reinsurance_cessions',
        help_text='Source customer invoice this cession was generated from '
                  'by the auto-cession pass. NULL for manual / bordereau cessions.',
    )
    share_percent = models.DecimalField(
        max_digits=6, decimal_places=4, null=True, blank=True,
        help_text='Cession % applied at the time of the auto-cession run. '
                  'Snapshot from treaty.cession_share_percent.',
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    journal_entry = models.OneToOneField(
        'ledger.JournalEntry', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='reinsurance_cession',
    )
    posted_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='cessions_posted',
    )
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-cession_date', '-cession_number']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['treaty', 'status']),
            models.Index(fields=['invoice', 'treaty']),
        ]
        constraints = [
            # Idempotency for the auto-cession pass: one Cession per
            # (invoice, treaty) pair. NULL invoices (manual / bordereau)
            # are not constrained — the UniqueConstraint with a non-NULL
            # condition lets the pass re-run safely while leaving legacy
            # rows alone.
            models.UniqueConstraint(
                fields=['invoice', 'treaty'],
                condition=models.Q(invoice__isnull=False),
                name='uniq_cession_invoice_treaty',
            ),
        ]

    def __str__(self):
        return f'{self.cession_number} — {self.treaty.treaty_number}'

    def save(self, *args, **kwargs):
        if not self.cession_number:
            self.cession_number = _next_cession_number()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Recovery
# ---------------------------------------------------------------------------

class ReinsuranceRecovery(AuditableMixin, BaseModel):
    """A claim recovery from a reinsurer."""

    class Status(models.TextChoices):
        DRAFT     = 'draft',     'Draft'
        POSTED    = 'posted',    'Posted'
        SETTLED   = 'settled',   'Settled (cash received)'
        VOIDED    = 'voided',    'Voided'

    recovery_number = models.CharField(max_length=20, unique=True, editable=False)
    treaty = models.ForeignKey(
        ReinsuranceTreaty, on_delete=models.PROTECT, related_name='recoveries',
    )
    recovery_date = models.DateField(default=timezone.localdate)
    claim_reference = models.CharField(
        max_length=120,
        help_text='Graphite claim number (mandatory for traceability).',
    )

    gross_loss = models.DecimalField(max_digits=18, decimal_places=2)
    ceded_recovery = models.DecimalField(max_digits=18, decimal_places=2)

    notes = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    journal_entry = models.OneToOneField(
        'ledger.JournalEntry', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='reinsurance_recovery',
    )
    posted_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='recoveries_posted',
    )
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-recovery_date', '-recovery_number']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['treaty', 'status']),
        ]

    def __str__(self):
        return f'{self.recovery_number} — {self.claim_reference}'

    def save(self, *args, **kwargs):
        if not self.recovery_number:
            self.recovery_number = _next_recovery_number()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Bordereau import
# ---------------------------------------------------------------------------

class BordereauImport(AuditableMixin, BaseModel):
    """Header for a monthly cession bordereau uploaded by the broker.

    v1 stores the import metadata + raw file reference; line-level breakdown
    is created as Cession rows linked back via FK. A future v2 will add a
    BordereauLine model with line-level matching.
    """

    class Status(models.TextChoices):
        UPLOADED  = 'uploaded',  'Uploaded'
        PARSED    = 'parsed',    'Parsed'
        COMMITTED = 'committed', 'Committed'
        REJECTED  = 'rejected',  'Rejected'

    bordereau_number = models.CharField(max_length=20, unique=True, editable=False)
    treaty = models.ForeignKey(
        ReinsuranceTreaty, on_delete=models.PROTECT, related_name='bordereau_imports',
    )
    period_start = models.DateField()
    period_end = models.DateField()
    received_date = models.DateField(default=timezone.localdate)

    file_name = models.CharField(max_length=240, blank=True)
    line_count = models.PositiveIntegerField(default=0)
    total_gross_premium = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO)
    total_ceded_premium = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO)
    total_commission = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO)

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.UPLOADED)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-received_date', '-bordereau_number']

    def __str__(self):
        return (
            f'{self.bordereau_number} — {self.treaty.treaty_number} '
            f'{self.period_start}→{self.period_end}'
        )

    def save(self, *args, **kwargs):
        if not self.bordereau_number:
            self.bordereau_number = _next_bordereau_number()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# 11-Year Historical Treaty Performance — LOCKED reference dataset
# ---------------------------------------------------------------------------
# CFO directive 2026-08-14. A permanent, locked record of the reinsurance
# programme's 11-year (UWY 2014/15–2025/26) performance, feeding the
# /reinsurance/history board dashboard. Requirements from the CFO:
#   • the data must STAY — it cannot be accidentally deleted (by staff OR by the AI);
#   • amending it requires the user's own password (the same login as HRIS);
#   • every amendment keeps a snapshot of the old numbers (nothing is ever lost);
#   • the dashboard reads from THIS saved copy, never from the source Excel files.
# It is a single-row (singleton) dataset; there is deliberately no delete path.

class ReinsuranceHistory(AuditableMixin, BaseModel):
    """Singleton holding the current, locked 11-year treaty-performance dataset."""

    SINGLETON_KEY = 'PRIMARY'

    key = models.CharField(max_length=20, unique=True, default=SINGLETON_KEY, editable=False)
    data = models.JSONField(default=dict)          # structured figures (see seeder)
    locked = models.BooleanField(default=True)     # read-only unless a password amend is made
    version = models.PositiveIntegerField(default=1)
    last_amended_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='reinsurance_history_amendments',
    )
    last_amended_at = models.DateTimeField(null=True, blank=True)
    source_note = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = 'Reinsurance 11-year history'
        verbose_name_plural = 'Reinsurance 11-year history'

    def __str__(self):
        return f'Reinsurance 11-year history v{self.version} (locked={self.locked})'

    @classmethod
    def current(cls):
        return cls.objects.filter(key=cls.SINGLETON_KEY).first()


class ReinsuranceHistorySnapshot(BaseModel):
    """Immutable copy of the dataset as it was BEFORE each amendment — so the
    old numbers are never lost and every change is auditable."""

    version = models.PositiveIntegerField()
    data = models.JSONField(default=dict)
    amended_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='reinsurance_history_snapshots',
    )
    amended_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-version']

    def __str__(self):
        return f'Reinsurance history snapshot v{self.version}'
