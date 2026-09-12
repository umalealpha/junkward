---
description: Canonical Trial Balance + P&L sanity check against omni's own GL. PASS/BLOCK verdict, JSON receipt under reports/.
---

# /tb-check — Trial Balance + P&L sanity check

Runs `python manage.py tb_check` inside the alpha-finance backend
container. Implements the 5-failure-mode prevention pattern from
`~/.claude/skills/prat-skill/recipes/tb-check.md`.

## Usage

```
/tb-check                                  # FY26-9M, all companies
/tb-check FY26-9M VCM                      # 9-month VCM check
/tb-check FY25 ADI                         # FY25 ADI full year
/tb-check 2025-07-01 2026-03-31 ADIC       # explicit dates
```

## What this does

1. Parse positional args:
   - If first arg matches a preset (`FY25`, `FY26`, `FY26-9M`, `FY26-Q1..Q3`),
     use that and the second arg as `--company`.
   - Else treat as `--start <iso> --end <iso>` plus optional company.
2. Run `python manage.py tb_check` with the resolved flags.
3. Report verdict + tie-out figures inline. Receipt JSON path goes back as
   `reports/tb-check-YYYYMMDD-HHMMSS.json`.

## When to invoke this

- Before publishing any P&L to the CFO / board.
- After every Odoo migration (`migrate_odoo`).
- After any CoA seed change.
- Any time the dashboard number disagrees with the MA workbook by > 100k BWP.

## Failure modes this prevents

a) Sign-flip on revenue (raw `SUM(balance)` misread as loss)
b) Draft journals leaking into "posted" totals
c) Wrong period column (entry_date vs created_at)
d) Suspense / RE / FX accounts contaminating the P&L bucket
e) Net income not equal to change in Retained Earnings

If any of the above is true the command exits non-zero and prints the
specific check that failed + a fix suggestion.

## Exit codes

- `0` — PASS, the number is trustworthy.
- `1` — BLOCK, fix the failing check before quoting the figure anywhere.
