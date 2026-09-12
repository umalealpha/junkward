"""
fnb/statements.py

Pull bank statements from FNB Botswana via the Customer Statement
Execution API and materialise them as `banking.BankStatement` +
`banking.BankStatementLine` rows so the existing reconciliation engine
can match them against open Invoices, Bills, and Payments.

Endpoint: POST /statements/retrieveStatement/v1/
Auth:     OAuth2 client_credentials (handled by FNBClient)
Body:     CustomerStatementRequest { accountId, fromDate, toDate, ... }
Response: CustomerStatement { statementLines: [ { date, amount, narrative, ... } ] }

The mapping from FNB's CustomerStatement schema to our banking models is
deliberately defensive — FNB's schema has several optional fields and the
exact wire format can vary slightly between sandbox and prod. The mapper
in `_persist_statement()` reads the documented fields with a fallback for
each, so a sandbox-vs-prod field name drift doesn't break the import.
"""
from __future__ import annotations

import datetime
import logging
import uuid
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone

from .client import FNBClient
from .endpoints import STATEMENT_RETRIEVE
from .models import FNBSyncLog

log = logging.getLogger(__name__)


def _to_decimal(v) -> Decimal:
    if v in (None, ''):
        return Decimal('0')
    try:
        return Decimal(str(v)).quantize(Decimal('0.01'))
    except Exception:  # noqa: BLE001
        return Decimal('0')


def _to_date(v) -> datetime.date | None:
    if v in (None, ''):
        return None
    if isinstance(v, datetime.date):
        return v
    s = str(v).split('T', 1)[0]
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


@transaction.atomic
def pull_statement(
    bank_account,
    *,
    from_date: Optional[datetime.date] = None,
    to_date:   Optional[datetime.date] = None,
    user = None,
):
    """Fetch the FNB statement for `bank_account` over [from_date, to_date]
    and load it into banking.BankStatement(+Line).

    Returns the BankStatement row created (or the existing row if the same
    period was already imported — match on account + (from_date, to_date)).
    """
    from banking.models import BankStatement, BankStatementLine

    if to_date is None:
        to_date = timezone.localdate()
    if from_date is None:
        from_date = to_date - datetime.timedelta(days=31)

    client = FNBClient(user=user)
    # FNB working sample (confirmed by Kabelo Sekoto via Postman screenshot
    # 2026-05-25): exactly three keys. Adding `currency` or
    # `statementType` returns 400 "Bad Request".
    body = {
        'accountId':  bank_account.account_number,
        'fromDate':   from_date.isoformat(),
        'toDate':     to_date.isoformat(),
    }
    resp = client.post(
        STATEMENT_RETRIEVE,
        service        = FNBSyncLog.Service.STATEMENT,
        json_body      = body,
        request_summary= (f'Retrieve statement {bank_account.account_number} '
                          f'{from_date}..{to_date}'),
        extra_headers  = {'X-Request-ID': str(uuid.uuid4())},
        # FNB statement retrieval is consistently slow (>20s observed
        # 2026-05-26). Give it a 90s read window so a busy day's
        # statement does not time out at the default 15s.
        timeout        = 90,
    )
    return _persist_statement(bank_account, resp.json or {}, from_date, to_date)


def _persist_statement(bank_account, payload: dict, from_date, to_date):
    """Translate a CustomerStatement JSON payload into BankStatement+Line.

    Live FNB Botswana response shape (verified 2026-05-25 against
    63001966639):

        {
          "groupHeader": {...},
          "statement": {
            "account": {"accountNumber": "...", "currency": "BWP", ...},
            "balance": [
              {"typeCode": "OPBD", "amountValue": ..., "creditDebitIndicator": "Credit"},
              {"typeCode": "CLBD", "amountValue": ..., "creditDebitIndicator": "Credit"}
            ],
            "entry": [
              {"amountValue": 53.6, "creditDebitIndicator": "Debit",
               "bookingDateTime": "2026-06-01", "valueDate": "2026-06-01",
               "servicerReference": "#MONTHLY ACCOUNT FEE ",
               "bankTransactionCode": {"domainCode": "ACMT", ...},
               "transactionDetails": {"amountValue": 53.6, ...}}
            ]
          }
        }

    Sandbox-style flat keys (`statementLines` / `openingBalance`) are kept
    as fallbacks.
    """
    from banking.models import BankStatement, BankStatementLine

    stmt_root = payload.get('statement') or payload

    # Entries: live key is `entry` under `statement`. Older docs / sandbox
    # used `statementLines` / `transactions` / `entries`.
    lines = (
        stmt_root.get('entry')
        or stmt_root.get('entries')
        or stmt_root.get('statementLines')
        or stmt_root.get('transactions')
        or []
    )

    # Balance array: pick OPBD (opening booked) and CLBD (closing booked).
    # Sign-aware: if CDI == "Debit", flip the amount negative.
    def _bal_amount(bal: dict) -> Decimal:
        amt = _to_decimal(bal.get('amountValue') or bal.get('amount'))
        cdi = (bal.get('creditDebitIndicator') or '').upper()
        if cdi in ('DEBIT', 'DBIT') and amt > 0:
            amt = -amt
        return amt

    opening_balance = Decimal('0.00')
    closing_balance = Decimal('0.00')
    balances = stmt_root.get('balance') or stmt_root.get('balances') or []
    if isinstance(balances, list):
        for b in balances:
            tc = (b.get('typeCode') or b.get('type') or '').upper()
            if tc in ('OPBD', 'PRCD', 'OPENING'):
                opening_balance = _bal_amount(b)
            elif tc in ('CLBD', 'CLAV', 'CLOSING'):
                closing_balance = _bal_amount(b)
    elif isinstance(balances, dict):  # sandbox shape
        opening_balance = _to_decimal(balances.get('opening'))
        closing_balance = _to_decimal(balances.get('closing'))

    # Sandbox-style flat balance fallback
    if opening_balance == 0 and (
        payload.get('openingBalance') or payload.get('openingBalanceAmount')
    ):
        opening_balance = _to_decimal(
            payload.get('openingBalance') or payload.get('openingBalanceAmount')
        )
    if closing_balance == 0 and (
        payload.get('closingBalance') or payload.get('closingBalanceAmount')
    ):
        closing_balance = _to_decimal(
            payload.get('closingBalance') or payload.get('closingBalanceAmount')
        )

    # BankStatement model only has a single `statement_date`; use to_date
    # (period end) as that date. Idempotency: match on
    # (bank_account, statement_date) so re-pulling the same range overwrites.
    file_name = f'FNB API {from_date.isoformat()}..{to_date.isoformat()}'
    statement = BankStatement.objects.filter(
        bank_account=bank_account,
        statement_date=to_date,
        file_name=file_name,
    ).first()
    if statement:
        statement.opening_balance = opening_balance
        statement.closing_balance = closing_balance
        statement.save(update_fields=['opening_balance', 'closing_balance'])
    else:
        statement = BankStatement.objects.create(
            bank_account=bank_account,
            statement_date=to_date,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            file_name=file_name,
        )

    # Wipe old lines for this statement and reinsert. Re-import is idempotent
    # on the (account, statement_date, file_name) tuple, not line content.
    BankStatementLine.objects.filter(statement=statement).delete()

    created = 0
    for ln in lines:
        # FNB Botswana response (confirmed 2026-05-25) nests amount,
        # currency, CDI, reference and counterparty under
        # `transactionDetails`. Top-level fields exist for booking
        # dates and bankTransactionCode classification. Keep flat
        # fallbacks for sandbox parity.
        td = ln.get('transactionDetails') or {}
        btc = ln.get('bankTransactionCode') or {}

        amt = _to_decimal(
            td.get('amountValue')
            or ln.get('amount')
            or ln.get('value')
        )
        cr_dr_raw = (
            td.get('creditDebitIndicator')
            or ln.get('creditDebitIndicator')
            or ln.get('cdi')
            or ''
        )
        cr_dr = cr_dr_raw.upper()
        # FNB BW uses "Debit"/"Credit"; ISO 20022 spec uses "DBIT"/"CRDT".
        # Treat both forms; outflow = negative.
        is_debit  = cr_dr in ('DEBIT',  'DBIT')
        is_credit = cr_dr in ('CREDIT', 'CRDT')
        if is_debit and amt > 0:
            amt = -amt
        elif is_credit and amt < 0:
            amt = -amt

        # Description: prefer `servicerReference` (FNB BW narrative),
        # then build "DOMAIN/FAMILY/SUBFAMILY" from bankTransactionCode,
        # then fall back to sandbox-style fields.
        desc_parts = []
        sr = ln.get('servicerReference')
        if sr:
            desc_parts.append(str(sr).strip())
        btc_str = '/'.join(
            x for x in (
                btc.get('domainCode'),
                btc.get('domainFamilyCode'),
                btc.get('domainSubFamilyCode'),
            ) if x
        )
        if btc_str:
            desc_parts.append(btc_str)
        counterparty = (
            td.get('relatedPartyDebtorName')
            or td.get('relatedPartyDebitorName')   # FNB spec typo
            or td.get('relatedPartyCreditorName')
        )
        if counterparty:
            desc_parts.append(str(counterparty).strip())
        description = ' | '.join(desc_parts) or (
            ln.get('description')
            or ln.get('narrative')
            or ln.get('remittanceInformation')
            or ''
        )

        reference = (
            td.get('referenceEndToEndId')
            or ln.get('reference')
            or ln.get('endToEndId')
            or ''
        )

        created += 1
        BankStatementLine.objects.create(
            statement        = statement,
            line_number      = created,
            transaction_date = _to_date(
                ln.get('bookingDateTime')
                or ln.get('bookingDate')
                or ln.get('valueDate')
                or ln.get('date')
            ) or to_date,
            amount           = amt,
            description      = str(description)[:500],
            reference        = str(reference)[:200],
            raw_data         = ln,
        )

    statement.line_count = created
    statement.save(update_fields=['line_count'])

    log.info('FNB statement loaded: %s %s..%s (%d lines, closing=%s)',
             bank_account.account_number, from_date, to_date,
             created, closing_balance)
    return statement
