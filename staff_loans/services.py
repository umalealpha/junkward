"""
staff_loans/services.py

Every state change lives here as a named function: permission + segregation
checks, the GL posting, and the crossing into the payroll EmployeeLoan engine.
Views stay thin; the rules stay in one place.

Lifecycle
---------
  DRAFT --submit--> PENDING_CFO
      PENDING_CFO --cfo_decide(approve)--> APPROVED
      PENDING_CFO --cfo_decide(decline)--> DECLINED
          APPROVED --sign--> SIGNED            (employee e-signs the undertaking)
              SIGNED --disburse--> ACTIVE      (HR pays out; creates EmployeeLoan
                                                + posts the issuance GL entry)
  DRAFT/PENDING_CFO/APPROVED/SIGNED --cancel--> CANCELLED
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from core.models import UserProfile

from . import policy
from . import rates
from .models import StaffLoanApplication

log = logging.getLogger(__name__)

ZERO = Decimal('0.00')

# The shared payroll deduction component code (payroll/loan_service.py).
LOAN_REPAYMENT_CODE = 'LOAN_REPAYMENT'

# Known-good ADIC ledger codes (imported chart of accounts) used as hints.
ADIC_RECEIVABLE_HINT = '121010'      # "Staff Loan"
ADIC_INTEREST_HINT = '124004'        # "Interest From Staff Loan"

# Fallback omni-seed codes, created only if a company has no named account.
FALLBACK_RECEIVABLE_CODE = '1260'
FALLBACK_INTEREST_CODE = '4650'


# ---------------------------------------------------------------------------
# People / permissions
# ---------------------------------------------------------------------------

def _profile(user):
    if user is None:
        return None
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        return None


def _is_hr_manager(user) -> bool:
    if user is None:
        return False
    if getattr(user, 'is_superuser', False):
        return True
    p = _profile(user)
    return bool(p and p.is_active and p.title == UserProfile.Title.HR_MANAGER)


def _is_final_approver(user) -> bool:
    """The CFO (or a Django superuser)."""
    if user is None:
        return False
    if getattr(user, 'is_superuser', False):
        return True
    p = _profile(user)
    return bool(p and p.is_active and p.title == UserProfile.Title.CFO)


def hr_managers():
    from django.contrib.auth.models import User
    return list(User.objects.filter(
        profile__title=UserProfile.Title.HR_MANAGER, profile__is_active=True, is_active=True))


def cfo_approvers():
    from django.contrib.auth.models import User
    return list(User.objects.filter(
        profile__title=UserProfile.Title.CFO, profile__is_active=True, is_active=True))


def _is_applicant(app: StaffLoanApplication, user) -> bool:
    return bool(user and app.employee.user_id and app.employee.user_id == user.pk)


# ---------------------------------------------------------------------------
# Salary (the one-month cap basis)
# ---------------------------------------------------------------------------

def monthly_salary_for(employee):
    """The employee's current monthly basic from their active contract, in BWP.

    Returns None if there's no active monthly contract, or if the contract is in
    a non-BWP currency (e.g. ADRisk INR) — we don't convert here, so a non-BWP
    salary can't be compared to a BWP loan cap. Non-BWP staff loans are refused
    rather than mis-capped.
    """
    from payroll.contract_models import EmploymentContract
    today = timezone.localdate()
    c = (EmploymentContract.objects
         .filter(employee=employee,
                 status=EmploymentContract.Status.ACTIVE,
                 frequency=EmploymentContract.Frequency.MONTHLY,
                 start_date__lte=today)
         .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=today))
         .order_by('-start_date')
         .first())
    if c and c.basic:
        cur = getattr(c, 'currency_code_id', None)
        if cur and str(cur).upper() != 'BWP':
            return None  # non-BWP salary — cap can't be checked, refuse staff loan
        return c.basic
    # No active BWP contract on file — fall back to the employee's own payroll
    # record (CFO / Unami directive 2026-07-23: read pay from the employee
    # profile so HR need not upload a separate contract just to size a loan).
    return _latest_payslip_basic(employee)


def _latest_payslip_basic(employee):
    """Monthly BASIC from the employee's most recent payslip, in BWP, or None.

    Fallback salary source when there is no active EmploymentContract. Skips
    foreign-currency (e.g. ADRisk INR) payslips so a non-BWP figure is never
    compared to the BWP one-month cap — mirroring the contract path.
    """
    from payroll.models import Payslip, PayslipLine
    ps = (Payslip.objects
          .filter(employee=employee)
          .select_related('period')
          .order_by('-period__end_date')
          .first())
    if ps is None or ps.is_foreign_currency:
        return None
    total = ZERO
    for ln in (PayslipLine.objects.filter(payslip=ps)
               .select_related('component')):
        code = (getattr(ln.component, 'code', '') or '').upper()
        name = (getattr(ln.component, 'name', '') or '').lower()
        if code in ('BASIC', 'BASIC_SALARY') or 'basic salary' in name:
            total += Decimal(getattr(ln, 'amount', 0) or 0)
    return total if total > 0 else None


# ---------------------------------------------------------------------------
# Ledger accounts
# ---------------------------------------------------------------------------

def _find_account(company, *, contains_all, excludes=(), code_hint=None):
    """Resolve a named account for THIS company. A code hint (e.g. ADIC 121010)
    is only honoured if that account belongs to this company (or to no company),
    so a non-ADIC loan never silently posts to ADIC's account."""
    from ledger.models import Account
    qs = Account.objects.filter(is_active=True, is_summary_only=False)
    for term in contains_all:
        qs = qs.filter(name__icontains=term)
    for ex in excludes:
        qs = qs.exclude(name__icontains=ex)
    own = qs.filter(owner_company=company).first()
    if own:
        return own
    if code_hint:
        hinted = Account.objects.filter(code=code_hint, is_active=True).first()
        if hinted and hinted.owner_company_id in (None, company.id if company else None):
            return hinted
    return qs.filter(owner_company__isnull=True).first()


def _ensure_account(company, code, name, account_type, sub_type, parent_code=None):
    from ledger.models import Account
    acct = Account.objects.filter(code=code).first()
    if acct:
        return acct
    parent = Account.objects.filter(code=parent_code).first() if parent_code else None
    return Account.objects.create(
        code=code, name=name, account_type=account_type, sub_type=sub_type,
        parent=parent, is_active=True, owner_company=company,
    )


def resolve_loan_accounts(company):
    """(receivable_account, interest_income_account) for this company.

    Prefers the company's own named accounts (ADIC already has
    "Staff Loan" 121010 + "Interest From Staff Loan" 124004); creates a
    generic fallback only if nothing suitable exists.
    """
    receivable = _find_account(
        company, contains_all=['staff loan'], excludes=['interest'],
        code_hint=ADIC_RECEIVABLE_HINT,
    ) or _ensure_account(company, FALLBACK_RECEIVABLE_CODE, 'Staff loan receivable',
                         'asset', 'current_asset', parent_code='1200')

    interest = _find_account(
        company, contains_all=['staff loan', 'interest'],
        code_hint=ADIC_INTEREST_HINT,
    ) or _ensure_account(company, FALLBACK_INTEREST_CODE, 'Interest income – staff loans',
                        'revenue', 'other_revenue')
    return receivable, interest


def ensure_loan_repayment_component(receivable_code):
    """Bind the payroll LOAN_REPAYMENT deduction to the staff-loan receivable so
    each monthly deduction reduces that one GL balance.

    The component is shared and has a single posting account. The first loan to
    disburse sets it; a loan for a DIFFERENT company (different receivable) is
    refused — multi-entity staff-loan GL is a deliberate follow-up, not a silent
    mis-post. (In practice all staff loans are ADIC, which sets 121010.)
    """
    from payroll.models import PayslipComponent
    comp, _ = PayslipComponent.objects.get_or_create(
        code=LOAN_REPAYMENT_CODE,
        defaults={
            'name': 'Loan Repayment',
            'kind': PayslipComponent.Kind.EMPLOYEE_DEDUCTION,
            'sort_order': 80,
            'is_active': True,
            'is_taxable': False,
        },
    )
    if not (comp.posting_account_code or '').strip():
        comp.posting_account_code = receivable_code
        comp.save(update_fields=['posting_account_code', 'updated_at'])
    elif comp.posting_account_code != receivable_code:
        raise ValidationError(
            'Staff-loan payroll deductions are already set to post to account '
            f'{comp.posting_account_code}. This loan would use {receivable_code} '
            '(a different company). Multi-entity staff loans are not supported '
            'yet — raise this with Finance before disbursing.'
        )
    return comp


def company_bank_accounts(company):
    """Bank/cash accounts HR may disburse from — this company's own (or the
    unassigned/global ones only if the company has none of its own)."""
    from ledger.models import Account
    qs = Account.objects.filter(is_bank_account=True, is_active=True)
    own = qs.filter(owner_company=company)
    chosen = own if own.exists() else qs.filter(owner_company__isnull=True)
    return [{'code': a.code, 'name': a.name} for a in chosen.order_by('code')]


def _resolve_bank_account(company, code):
    from ledger.models import Account
    acct = Account.objects.filter(code=code, is_bank_account=True, is_active=True).first()
    if not acct:
        raise ValidationError({'disbursement_bank_code': 'Choose a valid bank or cash account to pay from.'})
    if acct.owner_company_id not in (None, company.id if company else None):
        raise ValidationError({'disbursement_bank_code': "That account belongs to a different company."})
    return acct


# ---------------------------------------------------------------------------
# Create + submit
# ---------------------------------------------------------------------------

@transaction.atomic
def create_application(*, employee, loan_type, amount_requested, term_months_requested,
                       reason, user, vehicle_description='', vehicle_reg='',
                       blue_book_holder='', no_other_loans=False, purchased_via_veritas=False):
    amount = Decimal(amount_requested or 0)
    term = int(term_months_requested or 0)

    # Attendance gate (CFO 2026-07-28): you cannot apply while the last 20 days
    # have unexplained Time Doctor shortfalls — sort them (leave or a comment) first.
    from hris.attendance_gate import attendance_gate
    ok, _bad, gate_msg = attendance_gate(getattr(employee, 'hris_profile', None))
    if not ok:
        raise ValidationError({'attendance': gate_msg})

    if loan_type == StaffLoanApplication.LoanType.STAFF:
        errs = policy.validate_staff_loan(amount, term, monthly_salary_for(employee))
    elif loan_type == StaffLoanApplication.LoanType.VEHICLE:
        errs = policy.validate_vehicle_loan(amount, term)
        if not blue_book_holder:
            errs['blue_book_holder'] = 'Say whose name the blue book is held under (Alpha Direct or Veritas).'
    else:
        raise ValidationError({'loan_type': 'Unknown loan type.'})
    errs.update(policy.validate_motivation(reason))
    errs.update(policy.validate_declarations(
        no_other_loans=no_other_loans, loan_type=loan_type, purchased_via_veritas=purchased_via_veritas))
    if errs:
        raise ValidationError(errs)

    app = StaffLoanApplication(
        employee=employee,
        loan_type=loan_type,
        amount_requested=amount,
        term_months_requested=term,
        reason=(reason or '').strip(),
        vehicle_description=(vehicle_description or '').strip(),
        vehicle_reg=(vehicle_reg or '').strip(),
        blue_book_holder=blue_book_holder or '',
        no_other_loans_declared=bool(no_other_loans),
        purchased_via_veritas=bool(purchased_via_veritas),
        status=StaffLoanApplication.Status.DRAFT,
        created_by=user,
    )
    app.save(audit_user=user, audit_description='Created staff loan application')
    return app


@transaction.atomic
def submit_application(app: StaffLoanApplication, user):
    if app.status != StaffLoanApplication.Status.DRAFT:
        raise ValidationError(f'Only a draft can be submitted (this is {app.get_status_display()}).')
    if not _is_applicant(app, user) and not getattr(user, 'is_superuser', False):
        raise ValidationError('Only the applicant may submit their own request.')
    merrs = policy.validate_motivation(app.reason)
    if merrs:
        raise ValidationError(merrs)

    # Re-check the cap at submit and snapshot the basis.
    if app.loan_type == StaffLoanApplication.LoanType.STAFF:
        salary = monthly_salary_for(app.employee)
        errs = policy.validate_staff_loan(app.amount_requested, app.term_months_requested, salary)
        if errs:
            raise ValidationError(errs)
        app.monthly_salary_snapshot = salary
    else:
        errs = policy.validate_vehicle_loan(app.amount_requested, app.term_months_requested)
        if errs:
            raise ValidationError(errs)

    app.status = StaffLoanApplication.Status.PENDING_CFO
    app.submitted_at = timezone.now()
    app.save(audit_user=user, audit_description='Submitted for CFO approval')
    # Long-overdue-task gate (CFO 2026-08-07): applying for a loan with work
    # more than 2 days past due needs an executive countersignature. In
    # practice the CFO already decides loans, so their approval clears it —
    # the record exists so the overdue work is visible when they decide.
    try:
        from hris import exec_signoff_service
        from hris.exec_signoff_models import ExecSignoff
        exec_signoff_service.require_signoff(ExecSignoff.Module.LOAN, app, user)
    except Exception:                       # noqa: BLE001 — never block submit
        # Fail open, but never in silence (DeepSeek review 2026-08-07).
        log.exception('OVERDUE GATE FAILED OPEN on staff loan %s for user id %s — '
                      'submitted WITHOUT the executive check.',
                      app.pk, getattr(user, 'id', None))
    return app


# ---------------------------------------------------------------------------
# CFO decision
# ---------------------------------------------------------------------------

@transaction.atomic
def cfo_decide(app: StaffLoanApplication, user, *, approve, notes='', decline_reason='',
               approved_amount=None, approved_term_months=None, annual_rate_pct=None):
    if app.status != StaffLoanApplication.Status.PENDING_CFO:
        raise ValidationError(f'Only a request pending CFO approval can be decided (this is {app.get_status_display()}).')
    if not _is_final_approver(user):
        raise ValidationError('Only the CFO (or a superuser) may approve a staff loan.')
    if _is_applicant(app, user):
        raise ValidationError('Segregation of duties: you cannot approve your own loan.')

    # Long-overdue-task gate (CFO 2026-08-07). The CFO's own APPROVAL is the
    # countersignature; a superuser who is not CEO/CFO cannot clear it.
    # Deliberately only on the approve path: a rejection must never be recorded
    # as an executive signature (DeepSeek review round 2, 2026-08-07).
    from hris import exec_signoff_service
    from hris.exec_signoff_models import ExecSignoff
    if approve:
        exec_signoff_service.auto_resolve(ExecSignoff.Module.LOAN, app.pk, user)
        _blocking = exec_signoff_service.blocking_signoff(ExecSignoff.Module.LOAN, app.pk)
        if _blocking is not None:
            raise ValidationError(exec_signoff_service.block_message(_blocking))

    app.cfo_decided_by = user
    app.cfo_decided_at = timezone.now()
    app.decision_notes = (notes or '').strip()

    if not approve:
        if not (decline_reason or '').strip():
            raise ValidationError({'decline_reason': 'Give a reason for declining.'})
        app.status = StaffLoanApplication.Status.DECLINED
        app.decline_reason = decline_reason.strip()
        app.save(audit_user=user, audit_description='CFO declined the loan')
        return app

    amount = Decimal(approved_amount) if approved_amount is not None else app.amount_requested
    term = int(approved_term_months) if approved_term_months is not None else app.term_months_requested
    # Default to the current scheme rate (BoB MoPR + spread, refreshed monthly);
    # the CFO may still override it per loan.
    rate = Decimal(annual_rate_pct) if annual_rate_pct is not None else rates.current_annual_rate()

    # The approved figures must still obey the scheme caps + a rate ceiling.
    salary = monthly_salary_for(app.employee)
    if app.loan_type == StaffLoanApplication.LoanType.STAFF:
        errs = policy.validate_staff_loan(amount, term, salary)
    else:
        errs = policy.validate_vehicle_loan(amount, term)
    errs.update(policy.validate_rate(rate))
    # Affordability — the monthly repayment can't exceed one month salary.
    monthly = policy.monthly_instalment(amount, rate, term)
    errs.update(policy.validate_affordability(monthly, salary))
    if errs:
        raise ValidationError(errs)

    app.approved_amount = policy.q(amount)
    app.approved_term_months = term
    app.annual_rate_pct = rate
    app.status = StaffLoanApplication.Status.APPROVED
    app.save(audit_user=user, audit_description='CFO approved the loan')
    return app


# ---------------------------------------------------------------------------
# Employee signs the undertaking
# ---------------------------------------------------------------------------

@transaction.atomic
def sign_application(app: StaffLoanApplication, user, *, signature_data_url,
                     signatory_full_name, ip=''):
    if app.status != StaffLoanApplication.Status.APPROVED:
        raise ValidationError(f'Only an approved loan can be signed (this is {app.get_status_display()}).')
    if not _is_applicant(app, user):
        raise ValidationError('Only the applicant may sign their own undertaking.')
    if not signature_data_url or not str(signature_data_url).startswith('data:image/'):
        raise ValidationError({'signature_data_url': 'A signature is required.'})
    if not (signatory_full_name or '').strip():
        raise ValidationError({'signatory_full_name': 'Enter your full name as signatory.'})

    app.signature_data_url = signature_data_url
    app.signatory_full_name = signatory_full_name.strip()
    app.signed_at = timezone.now()
    app.signed_ip = (ip or '')[:45]
    app.status = StaffLoanApplication.Status.SIGNED
    app.save(audit_user=user, audit_description='Employee signed the loan undertaking')
    return app


# ---------------------------------------------------------------------------
# HR disburses — creates the EmployeeLoan + posts the issuance GL entry
# ---------------------------------------------------------------------------

@transaction.atomic
def disburse(app: StaffLoanApplication, user, *, disbursement_bank_code,
             disbursement_ref='', blue_book_received=False):
    # Lock the row and re-read committed state, so two concurrent disburse calls
    # (double-click / client retry) can't both create a loan + post a JE. The
    # second caller blocks here, then sees status=active and bails below.
    # `of=('self',)` is load-bearing on Postgres: employee__company is nullable,
    # so select_related puts it on the nullable side of a LEFT OUTER JOIN and a
    # bare FOR UPDATE is rejected ("FOR UPDATE cannot be applied to the nullable
    # side of an outer join") — which made every disbursement 500. Lock the
    # application row only; the joined rows are read-only here.
    app = (StaffLoanApplication.objects
           .select_for_update(of=('self',))
           .select_related('employee', 'employee__company')
           .get(pk=app.pk))

    if app.status != StaffLoanApplication.Status.SIGNED:
        raise ValidationError(f'Only a signed loan can be disbursed (this is {app.get_status_display()}).')
    if not _is_hr_manager(user):
        raise ValidationError('Only an HR Manager (or superuser) may process the disbursement.')
    if _is_applicant(app, user):
        raise ValidationError('Segregation of duties: you cannot disburse your own loan.')
    if app.cfo_decided_by_id and app.cfo_decided_by_id == user.pk:
        raise ValidationError('Segregation of duties: the person who approved a loan cannot also disburse it.')
    if app.employee_loan_id:
        raise ValidationError('This loan has already been disbursed.')

    company = app.employee.company
    if company is None:
        raise ValidationError('This employee has no company on their payroll record — HR must set it before disbursing.')

    # Vehicle loans: the blue book must be in hand before money goes out
    # (same control shape as "salvage in the yard before settlement").
    if app.is_vehicle:
        if not app.blue_book_holder:
            raise ValidationError({'blue_book_holder': 'Set whose name holds the blue book first.'})
        if not blue_book_received:
            raise ValidationError({'blue_book_received': 'Confirm the vehicle blue book is held before disbursing.'})

    bank_account = _resolve_bank_account(company, disbursement_bank_code)

    principal_cash = policy.q(app.effective_amount)          # cash paid to the employee
    total = app.total_repayable                               # booked as receivable
    if total <= 0:
        raise ValidationError('Loan amount resolves to zero — check the approved amount and term.')

    # Resolve GL accounts + claim the shared payroll deduction component BEFORE
    # creating anything — a cross-company block then fails cleanly with nothing
    # half-created (the whole function is atomic anyway).
    receivable, interest_acct = resolve_loan_accounts(company)
    ensure_loan_repayment_component(receivable.code)

    from payroll.contract_models import EmployeeLoan

    # Reuse the live amortising engine. Interest is capitalised into the
    # principal and the rate set to 0 so the monthly deduction is a flat
    # total/term against the single receivable account.
    loan = EmployeeLoan.objects.create(
        employee=app.employee,
        principal=total,
        annual_rate_pct=ZERO,
        term_months=app.effective_term,
        start_period=None,
        status=EmployeeLoan.Status.ACTIVE,
        outstanding=total,
    )

    je = _post_issuance_je(app, bank_account, user, receivable, interest_acct,
                           principal_cash=principal_cash, total=total)

    if app.is_vehicle:
        app.blue_book_received = True
    app.employee_loan = loan
    app.issuance_journal_entry = je
    app.disbursed_by = user
    app.disbursed_at = timezone.now()
    app.disbursement_ref = (disbursement_ref or '').strip()
    app.disbursement_bank_code = bank_account.code
    app.status = StaffLoanApplication.Status.ACTIVE
    app.save(audit_user=user, audit_description=f'Disbursed loan; EmployeeLoan {loan.pk}, JE {je.entry_number}')
    return app


def _post_issuance_je(app, bank_account, user, receivable, interest_acct, *, principal_cash, total):
    from ledger.models import JournalEntry, JournalEntryLine

    company = app.employee.company
    interest = policy.q(total - principal_cash)

    je = JournalEntry.objects.create(
        entry_date=timezone.localdate(),
        description=f'Staff loan disbursement — {app.employee.full_name} ({app.get_loan_type_display()})',
        journal_type=JournalEntry.JournalType.GENERAL,
        source_type='staff_loan_application',
        source_id=app.pk,
        currency_code=getattr(company, 'base_currency', None),
        exchange_rate=Decimal('1.00000000'),
        company=company,
        created_by=user,
        status=JournalEntry.Status.DRAFT,
        is_related_party=False,
    )
    JournalEntryLine.objects.create(
        journal_entry=je, account=receivable, description='Staff loan receivable',
        debit_amount=total, credit_amount=ZERO, debit_bwp=total, credit_bwp=ZERO,
    )
    JournalEntryLine.objects.create(
        journal_entry=je, account=bank_account, description='Loan paid to employee',
        debit_amount=ZERO, credit_amount=principal_cash, debit_bwp=ZERO, credit_bwp=principal_cash,
    )
    if interest > 0:
        JournalEntryLine.objects.create(
            journal_entry=je, account=interest_acct, description='Interest on staff loan',
            debit_amount=ZERO, credit_amount=interest, debit_bwp=ZERO, credit_bwp=interest,
        )
    je.post(user=user, _allow_direct=True)
    return je


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

@transaction.atomic
def cancel_application(app: StaffLoanApplication, user):
    if app.status in (StaffLoanApplication.Status.ACTIVE,
                      StaffLoanApplication.Status.DECLINED,
                      StaffLoanApplication.Status.CANCELLED):
        raise ValidationError(f'Cannot cancel a loan that is {app.get_status_display()}.')
    if not _is_applicant(app, user) and not getattr(user, 'is_superuser', False):
        raise ValidationError('Only the applicant (or a superuser) may cancel.')
    app.status = StaffLoanApplication.Status.CANCELLED
    app.save(audit_user=user, audit_description='Cancelled the loan application')
    return app
