"""
commissions/models.py — monthly agent-commission submission module.

One online form for agents to submit their monthly commission (per-policy
lines) instead of emailing Excel workbooks. Three flows — independent agents
(10% withholding), in-house/payroll agents (no withholding), and the BDU sales
team — are modelled as configuration rows (CommissionGroup), not code branches.

Standalone by design (CFO boundary, mirrors agent_portal): this module
computes + exports a payout file. GL posting, the payment run and sign-off
stay manual finance controls — no ledger/payments coupling here.
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

from core.models import BaseModel

# Month key must be exactly YYYY-MM (01–12) so the unique constraint and the
# payout export never split on a typo like '2026-6'.
PERIOD_VALIDATOR = RegexValidator(r'^\d{4}-(0[1-9]|1[0-2])$',
                                  'Period must be YYYY-MM, e.g. 2026-06.')


class CommissionGroup(BaseModel):
    """One of the three commission flows. Withholding rate + pay route are
    configuration so a policy change (e.g. how BDU is paid) is one field, not
    a code change."""

    class Key(models.TextChoices):
        INDEPENDENT = 'independent', 'Independent agents'
        IN_HOUSE    = 'in_house',    'In-house / payroll agents'
        BDU         = 'bdu',         'BDU domestic sales team'

    class PaysVia(models.TextChoices):
        DIRECT_BANK = 'direct_bank', 'Direct bank payment'
        PAYROLL     = 'payroll',     'Through payroll'

    key = models.CharField(max_length=20, choices=Key.choices, unique=True)
    name = models.CharField(max_length=80)
    # e.g. 0.1000 == 10% withholding tax deducted before payment.
    withholding_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    pays_via = models.CharField(max_length=12, choices=PaysVia.choices, default=PaysVia.DIRECT_BANK)
    owner_name = models.CharField(max_length=120, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        ordering = ['name']

    def __str__(self):
        return self.name


class CommissionAgent(BaseModel):
    """An agent who submits commission. Name is the natural key (matches how the
    workbooks identify the agent). Belongs to exactly one group."""
    name = models.CharField(max_length=160, unique=True)
    agent_code = models.CharField(max_length=20, blank=True, default='')
    group = models.ForeignKey(CommissionGroup, on_delete=models.PROTECT, related_name='agents')
    # Optional — used to match the signed-in user to their own submissions.
    email = models.CharField(max_length=160, blank=True, default='')
    # An independent agent working DIRECTLY for us has 10% withheld; one working
    # THROUGH a company does not (CFO 2026-07-15). This flag switches withholding
    # off for the via-company case. Irrelevant for payroll groups (they withhold
    # 0% anyway). Effective rate = 0 if works_via_company else group.withholding_rate.
    works_via_company = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        ordering = ['name']

    def __str__(self):
        return self.name


class CommissionBankAccount(BaseModel):
    """Agent bank details for payout. Sensitive — server-side only, access-gated
    at the API and never returned to a non-manager. Agents are payees (not
    policyholders); this mirrors how agent_portal / payroll treat payee bank
    data. Only agents WITH an account number are 'ready to pay'."""
    agent = models.OneToOneField(CommissionAgent, on_delete=models.CASCADE, related_name='bank')
    bank_name = models.CharField(max_length=120, blank=True, default='')
    account_name = models.CharField(max_length=160, blank=True, default='')
    account_number = models.CharField(max_length=40)
    branch_code = models.CharField(max_length=20, blank=True, default='')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='+')

    def __str__(self):
        return f"{self.agent.name} · {self.bank_name}"


class CommissionSubmission(BaseModel):
    """One agent's commission for one month. Totals are stored so a later config
    change never silently rewrites a signed-off figure (the rate in force is
    snapshotted at submit time)."""

    class Status(models.TextChoices):
        # Three-stage approval chain (CFO 2026-07-15): agent → 1st review
        # (Bokani/Tlamelo) → 2nd review (Pako/Kago) → final approval (CFO).
        DRAFT         = 'draft',         'Draft'
        SUBMITTED     = 'submitted',     'Submitted — 1st review'
        SECOND_REVIEW = 'second_review', '1st reviewed — 2nd review'
        FINAL_REVIEW  = 'final_review',  '2nd reviewed — final approval'
        APPROVED      = 'approved',      'Approved — awaiting payroll'
        REJECTED      = 'rejected',      'Rejected'
        PAID          = 'paid',          'Paid — payroll processed'

    agent = models.ForeignKey(CommissionAgent, on_delete=models.PROTECT, related_name='submissions')
    # Snapshot of the agent's group at create time (kept even if the agent later moves group).
    group = models.ForeignKey(CommissionGroup, on_delete=models.PROTECT, related_name='submissions')
    period_label = models.CharField(max_length=7, validators=[PERIOD_VALIDATOR],
                                    help_text="Month as YYYY-MM, e.g. 2026-05.")
    status = models.CharField(max_length=14, choices=Status.choices, default=Status.DRAFT)

    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='+')
    submitted_at = models.DateTimeField(null=True, blank=True)
    # Per-stage sign-off stamps (who approved at each of the three stages).
    first_reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                          on_delete=models.SET_NULL, related_name='+')
    first_reviewed_at = models.DateTimeField(null=True, blank=True)
    second_reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                           on_delete=models.SET_NULL, related_name='+')
    second_reviewed_at = models.DateTimeField(null=True, blank=True)
    final_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name='+')
    final_at = models.DateTimeField(null=True, blank=True)
    # Payroll processing (after CFO final approval) + the notify-out stamp.
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                on_delete=models.SET_NULL, related_name='+')
    paid_at = models.DateTimeField(null=True, blank=True)
    notified_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=300, blank=True, default='')

    # Computed + stored on recompute/submit.
    gross_commission = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    withholding_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    withholding_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    net_payable = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    # Auto-feed to payroll (CFO 2026-08-28): set when an approved payroll-group
    # commission is pushed into a pending payroll batch. Idempotency guard — a
    # submission already linked is never fed twice.
    payroll_amendment = models.ForeignKey(
        'payroll.PayrollAmendment', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='commission_submissions')

    # The original uploaded workbook, kept so a reviewer can download and verify it
    # before approving (Bokani Makosha 2026-08-12; CFO chose to retain the file
    # rather than the previous parse-then-delete). Only per-policy agent uploads
    # attach a file; served only through the gated `statement` download action.
    statement_file     = models.FileField(upload_to='commission_statements/',
                                           null=True, blank=True)
    statement_filename = models.CharField(max_length=255, blank=True, default='')

    class Meta(BaseModel.Meta):
        ordering = ['-period_label', 'agent__name']
        # One submission per agent per month.
        constraints = [
            models.UniqueConstraint(fields=['agent', 'period_label'],
                                    name='uniq_commission_agent_period'),
        ]
        indexes = [
            models.Index(fields=['group', 'period_label']),
            models.Index(fields=['status', 'period_label']),
        ]

    def __str__(self):
        return f"{self.agent.name} · {self.period_label} · {self.get_status_display()}"


class CommissionSubmissionLine(BaseModel):
    """A single per-policy line on a submission — the fields the agents' Excel
    workbooks carry today."""

    class TxnType(models.TextChoices):
        NEW_BUSINESS   = 'new_business',   'New business'
        RENEWAL        = 'renewal',        'Renewal'
        ENDORSEMENT    = 'endorsement',    'Endorsement'
        PREVIOUS_MONTH = 'previous_month', 'Previous month'

    submission = models.ForeignKey(CommissionSubmission, on_delete=models.CASCADE, related_name='lines')
    policy_number = models.CharField(max_length=60, blank=True, default='', db_index=True)
    client_name = models.CharField(max_length=160, blank=True, default='')
    transaction_type = models.CharField(max_length=16, choices=TxnType.choices,
                                        default=TxnType.NEW_BUSINESS)
    # Annual / Monthly (from the source 'Data' tab). Blank when not stated.
    frequency = models.CharField(max_length=10, blank=True, default='')
    amount_collected = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    annualised_premium = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    # Commission rate as entered (informational — the payable is commission_amount,
    # not this). Wide precision so an odd/large rate in a source sheet never blocks
    # an import (Patience's June sheet had a rate ≥ 1000).
    commission_rate = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0.0000'))
    # 'Amount Applicable for Commission (P)' — the base the commission is worked on.
    amount_applicable = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    collection_date = models.DateField(null=True, blank=True)
    is_policy_closed = models.BooleanField(default=False)
    # The commission earned on this line, as entered (kept verbatim so it matches
    # the agent's own working; see service.computed_commission for a cross-check).
    commission_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))

    class Meta(BaseModel.Meta):
        ordering = ['created_at']

    def __str__(self):
        return f"{self.policy_number or '(no policy)'} · {self.commission_amount}"


class CommissionAmendment(BaseModel):
    """Append-only audit trail of an edit to a submission's lines (CFO 2026-07-17).

    When a staff member disagrees with a premium/rate and amends the collected
    amount, rate or commission on their DRAFT/REJECTED submission, one row is
    written here: who changed it, the full before/after line set, the gross
    before/after, and an Aria (DeepSeek) plain-English note. Never edited or
    deleted — it is the amendment trail Bokani/Tlamelo/CFO can inspect."""
    submission = models.ForeignKey(CommissionSubmission, on_delete=models.CASCADE,
                                   related_name='amendments')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name='+')
    # Full line snapshots (list of dicts) so the trail stands alone even if the
    # submission is later re-edited or deleted-and-recreated.
    old_lines = models.JSONField(default=list)
    new_lines = models.JSONField(default=list)
    old_gross = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    new_gross = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    # Aria's plain-English summary of what changed (deterministic fallback if the
    # DeepSeek call is unavailable — the trail is never blocked on the AI).
    note = models.TextField(blank=True, default='')

    class Meta(BaseModel.Meta):
        ordering = ['-created_at']
        indexes = [models.Index(fields=['submission', 'created_at'])]

    def __str__(self):
        return f"amend {self.submission_id} · {self.old_gross}→{self.new_gross}"


# ─── Broker commission (Rose Mokgware's request, CFO 2026-09-08) ─────────────
# Replaces the 28-tab "Broker Commission - <Month>.xlsm" workbook. The broker's
# client list is DERIVED from Graphite (policies.agency_id -> agencies), so the
# tabs no longer have to be kept by hand; BrokerPolicy holds only the rows a
# human added or uploaded on top, and the collection status is read live from
# RealPay rather than pasted in from a downloaded report.

class Broker(BaseModel):
    """An intermediary we pay commission to.

    Graphite carries the same broker under several agency rows — Redhill exists
    twice (spelled "Hilrange" AND "Hildrage"), Dynamic three times, Kgare three,
    SATIB twice. Paying per agency row would split one broker's commission, so a
    Broker owns many BrokerAlias rows and the register merges on this side.
    """
    name = models.CharField(max_length=160, unique=True)
    short_name = models.CharField(
        max_length=40, blank=True, default='',
        help_text="What Finance calls them on the workbook tab, e.g. 'Finsef'.")
    is_active = models.BooleanField(default=True)
    notes = models.CharField(max_length=300, blank=True, default='')

    class Meta(BaseModel.Meta):
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class BrokerAlias(BaseModel):
    """One Graphite agency name that belongs to this broker."""
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, related_name='aliases')
    graphite_agency_name = models.CharField(max_length=200)
    graphite_agency_id = models.CharField(max_length=40, blank=True, default='')

    class Meta(BaseModel.Meta):
        ordering = ['graphite_agency_name']
        constraints = [
            models.UniqueConstraint(fields=['graphite_agency_name'],
                                    name='uniq_broker_alias_agency_name'),
        ]

    def __str__(self) -> str:
        return f'{self.graphite_agency_name} → {self.broker.name}'


class BrokerPolicy(BaseModel):
    """A policy on a broker's commission sheet that Graphite does not already
    give us — added in-app or uploaded from the old workbook.

    Deliberately NOT a mirror of every Graphite policy: the live list is read
    from Graphite on every request, and duplicating it here would go stale the
    way the workbook did. Rows here are the human overlay, and `source` records
    which is which so nobody has to guess later.
    """
    class Source(models.TextChoices):
        MANUAL = 'manual', 'Added in Omni'
        UPLOAD = 'upload', 'Uploaded from a workbook'

    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, related_name='policies')
    policy_number = models.CharField(max_length=60, db_index=True)
    insured_name = models.CharField(
        max_length=160, blank=True, default='',
        help_text='PII — shown in the auth-gated screen only, never sent to an AI pipeline.')
    period_label = models.CharField(
        max_length=7, blank=True, default='', validators=[PERIOD_VALIDATOR],
        help_text='Month this row belongs to, YYYY-MM. Blank = standing.')

    premium = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    amount_received = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    motor_premium = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    motor_commission = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    non_motor_premium = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    non_motor_commission = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    commission_payable = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    vat = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))

    source = models.CharField(max_length=8, choices=Source.choices, default=Source.MANUAL)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name='+')

    class Meta(BaseModel.Meta):
        ordering = ['policy_number']
        constraints = [
            models.UniqueConstraint(fields=['broker', 'policy_number', 'period_label'],
                                    name='uniq_broker_policy_period'),
        ]
        indexes = [models.Index(fields=['broker', 'period_label'])]

    def __str__(self) -> str:
        return f'{self.broker.name} · {self.policy_number}'
