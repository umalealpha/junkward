"""bonu/legal_calc.py — every figure the legal-office screens show.

Kept apart from the API on purpose: these are pure functions over the registers,
so the arithmetic that drives two bonuses can be tested directly rather than
through an HTTP round trip.

Two rules run through all of it:

1. **A missing comparison is not a zero saving.** A fee-note line with no entry
   in the rate map returns `None` for its external equivalent, and is reported
   as "no mapping" — never folded in as though handling it in-house saved
   nothing. Counting unmapped lines as zero would understate the saving and
   quietly hide that the map needs a line adding.
2. **One quarter definition.** Calendar quarters — Q1 Jan-Mar … Q4 Oct-Dec —
   the same basis the CFO fixed for the P90,000 member benefit year on
   3 Aug 2026. A bonus measured over a window the contract does not use is not
   enforceable.
"""
from __future__ import annotations

from decimal import Decimal
from datetime import date

ZERO = Decimal('0')


def month_key(d: date) -> str:
    return f'{d.year:04d}-{d.month:02d}'


def quarter_key(d: date) -> str:
    return f'{d.year:04d}-Q{(d.month - 1) // 3 + 1}'


def quarter_months(qkey: str) -> list[str]:
    """The three month keys inside a quarter, in order.

    A year has four quarters. `2026-Q5` parses perfectly well and would put a
    phantom period in the dropdown over an empty screen, so it is refused here
    — the one place that decides what a quarter is.
    """
    year, q = qkey.split('-Q')
    year, q = int(year), int(q)
    if not 1 <= q <= 4:
        raise ValueError(f'{qkey} is not a quarter — a year has Q1 to Q4.')
    start = (q - 1) * 3 + 1
    return [f'{year:04d}-{start + i:02d}' for i in range(3)]


def quarter_of_month(mkey: str) -> str:
    year, month = mkey.split('-')
    return f'{int(year):04d}-Q{(int(month) - 1) // 3 + 1}'


# --------------------------------------------------------------------------
# Fee notes and the external comparison
# --------------------------------------------------------------------------

def mapping_index(mappings) -> dict:
    """Fee description -> mapping, matched case- and space-insensitively so a
    line typed 'Legal Research' still finds the 'Legal research' map entry."""
    return {(m.fee_description or '').strip().lower(): m for m in mappings}


def internal_amount(fee) -> Decimal:
    return (fee.rate or ZERO) * (fee.qty or ZERO)


def external_equivalent(fee, index: dict):
    """What the same line would have cost at the external panel, or None when
    the service has no mapping yet."""
    m = index.get((fee.description or '').strip().lower())
    if m is None:
        return None
    if m.calc_basis == 'per_hour':
        return (m.external_rate or ZERO) * (fee.qty or ZERO)
    # Flat: the external flat fee applies once, whatever hours we spent on it.
    return m.external_rate or ZERO


def fee_line(fee, index: dict) -> dict:
    """One fee-note line with its comparison, ready for the screen."""
    m = index.get((fee.description or '').strip().lower())
    internal = internal_amount(fee)
    external = external_equivalent(fee, index)
    saving = None if external is None else external - internal
    pct = None
    if external is not None and external != ZERO:
        pct = saving / external
    return {
        'id': str(fee.id),
        'date': fee.date.isoformat() if fee.date else None,
        'client': fee.client,
        'portfolio': fee.portfolio,
        'description': fee.description,
        'unit': fee.unit,
        'rate': str(fee.rate),
        'qty': str(fee.qty),
        'amount': str(internal),
        'external_item': m.external_item if m else '',
        'external_rate': None if m is None else str(m.external_rate),
        'calc_basis': m.get_calc_basis_display() if m else '',
        'external_equivalent': None if external is None else str(external),
        'saving': None if saving is None else str(saving),
        'pct_saved': None if pct is None else float(pct),
        'mapped': m is not None,
        'updated_by': fee.updated_by_email,
    }


def totals_for_fees(fees, index: dict) -> dict:
    """Internal billed, external equivalent and the in-house saving over a set
    of fee lines. `internal` counts every line; `external` and `saving` count
    only the mapped ones, and `unmapped` says how many were left out so the
    screen can say it rather than the reader assuming full coverage."""
    internal = ZERO
    external = ZERO
    unmapped = 0
    for f in fees:
        internal += internal_amount(f)
        ext = external_equivalent(f, index)
        if ext is None:
            unmapped += 1
        else:
            external += ext
    # Only the mapped lines have an external side, so the saving must be
    # measured on the mapped lines alone.
    mapped_internal = ZERO
    for f in fees:
        if external_equivalent(f, index) is not None:
            mapped_internal += internal_amount(f)
    saving = external - mapped_internal
    return {
        'internal': internal,
        'mapped_internal': mapped_internal,
        'external': external,
        'saving': saving,
        'pct_saved': (saving / external) if external else None,
        'unmapped': unmapped,
    }


# --------------------------------------------------------------------------
# Invoice savings and the SLA
# --------------------------------------------------------------------------

def savings_total(rows) -> Decimal:
    return sum((r.saving for r in rows), ZERO)


def sla_summary(rows, sla_days: int) -> dict:
    """How many reviewed bills were turned round inside the target. Bills with
    no received date are excluded from both sides — an unknown turnaround is
    not a met one, and counting it as missed would be just as wrong."""
    measured = [r for r in rows if r.turnaround_days is not None]
    within = [r for r in measured if r.turnaround_days <= sla_days]
    return {
        'measured': len(measured),
        'within': len(within),
        'unknown': len(rows) - len(measured),
        'pct': (Decimal(len(within)) / Decimal(len(measured))) if measured else None,
    }


# --------------------------------------------------------------------------
# The two bonuses
# --------------------------------------------------------------------------

def quarterly_bonus(quarter_saving: Decimal, settings) -> dict:
    """2% of the WHOLE quarterly saving once the trigger is reached — not 2% of
    each invoice on its own."""
    met = quarter_saving >= settings.quarterly_threshold
    return {
        'saving': quarter_saving,
        'threshold': settings.quarterly_threshold,
        'met': met,
        'pct': settings.quarterly_bonus_pct,
        'bonus': (quarter_saving * settings.quarterly_bonus_pct) if met else ZERO,
    }


def monthly_bonus(entered, settings) -> Decimal:
    """The entered figure, held to the cap. `entered` is None when the officer
    has not put a figure in for the month yet."""
    if entered is None:
        return ZERO
    return min(Decimal(entered), settings.monthly_bonus_cap)


def advisory_value(hours: Decimal, settings) -> Decimal:
    return (hours or ZERO) * settings.external_hourly_rate
