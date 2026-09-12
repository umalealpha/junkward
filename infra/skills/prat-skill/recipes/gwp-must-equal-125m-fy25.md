# Recipe: ADIC FY25 GWP must equal 125.15M

**Hard rule.** Per CFO directive 2026-05-16, the only acceptable value for ADIC standalone Gross Written Premium for FY25 (full year ended June 2025) is **125.15 BWP Mn**.

## Why this rule exists

- MA workbook (`MA-June2025-ADIC-FY25.xlsx`) is the single source of truth for ADIC FY25 financials.
- The omni dashboard currently shows 99.1M for the same tile — this is a known bug caused by a missing 26M of FY25 GWP journals that were not migrated from Odoo (the prior accounting system).
- The CFO has corrected the figure 10 times in the source thread. Anything other than 125.15M for FY25 ADIC GWP is wrong.

## When to apply

Any time the user asks for:
- ADIC FY25 Gross Written Premium / GWP / Revenue / Top-line
- Reconciliation between the omni dashboard and the MA workbook
- Year-on-year comparisons that include FY25

## What NOT to do

- ❌ Quote 99.1M (the dashboard figure)
- ❌ Average the two figures
- ❌ Quote a Group consolidated figure unless explicitly asked — and only after confirming the CFO has uploaded the Group financials (currently outstanding).
- ❌ Silently change the figure in any reporting code, MA spec, or dashboard mapping without a 3x-confirm with the CFO.

## Fix in progress

The dashboard will reconcile to 125M once these steps are run:

1. CFO rotates burned Odoo password.
2. New password added to `/etc/alpha-finance/.env` on EC2 `i-02a5d76a61f4f09a5`.
3. `python manage.py migrate_odoo --commit` runs via AWS SSM — pulls the missing 26M of journals.
4. Dashboard tile re-aggregates from the GL and shows 125M.
