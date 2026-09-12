# HRIS-002 — Leave Report

Requested by Oprah Mogomotsi (omogomotsi@) via email 2026-06-10, forwarded by CFO
("fix respond via email"). Source spec is the email verbatim; deltas noted below.

## Functional requirements

1. **Route** `/hris/leave/report` (frontend) + `GET /hris/api/leave-report/` (backend).
2. **Access**: manager / HR / finance-manager tier only; employees (ess) must not
   see the page, the nav link, or the API. Mapped to the existing capability
   system: gate = `view_team` (held by mgr, hr, hris, ceo, admin, superadmin —
   never ess). Managers see ONLY their direct reports (+ themselves); roles with
   `view_all` see every employee in the selected company.
3. **Navigation**: "Leave Report" link in the Leave page header next to
   "Back to HRIS", rendered only when `useHrisCan('view_team')`.
4. **Filters**: period (default = current leave year), leave type multi-select
   (7 CoS types + All), department dropdown (default All), employee search.
5. **Table**: one row per employee × selected leave type:
   Employee · Department · Leave Type · Opening Balance · Accrued · Taken ·
   Closing Balance. Subtotal row per employee, grand total at bottom.
   Accrued shows "—" for flat-entitlement types (everything except Annual).
6. **Summary cards**: headcount with leave activity in period · total days
   taken · average days taken per employee-with-activity.
7. **Export**: CSV button, filename `Leave_Report_<from>_to_<to>.csv`.
   (Excel "optional but preferred" — CSV ships now, opens natively in Excel;
   XLSX deferred.)
8. **Styling**: existing HRIS orange/dark card+table conventions.

## Balance semantics (must mirror existing leave_balances logic)

- Leave year = calendar year of `date_from` (existing code: Jan 1 anchor).
- Annual accrues monthly: entitlement × months/12 (CoS §7.5.1); other types are
  flat, available-on-need.
- **Opening** (annual) = entitlement × (months before period start)/12 − approved
  days taken before period start within the leave year.
  **Opening** (flat) = entitlement − approved days taken before period start.
- **Accrued in period** (annual only) = entitlement × months-in-period/12,
  accrual clamped at the current month when the period end is in the future
  (mirrors apply-time rule). Flat types: null → "—".
- **Taken** = APPROVED requests only (per Oprah's spec; note leave_balances
  counts PENDING too for its 'used' — intentional difference, documented).
- **Closing** = opening + accrued − taken.
- Date ranges spanning years are clamped to the leave year of `date_from`.

## Non-functional

- Company scoping via `resolve_company_id_param` (multi-entity isolation).
- Frontend fetches via `authedHrisFetch` (MSAL Bearer; never raw fetch+Token).
- Test requirement from requester: at least one employee across two leave
  types before reporting back.
