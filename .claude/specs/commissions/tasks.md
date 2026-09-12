# Commissions module — Tasks

Build order (each verifiable). Lands on branch `feat/commissions`, NOT main.

- [ ] **T1 — App scaffold.** `commissions/` app: `__init__.py`, `apps.py`, `admin.py`. Register `'commissions'` in `alpha_finance/settings.py` LOCAL_APPS. → verify: `manage.py check` clean.
- [ ] **T2 — Models.** `models.py`: CommissionGroup, CommissionAgent, CommissionBankAccount, CommissionSubmission, CommissionSubmissionLine. → verify: `makemigrations commissions` produces 0001.
- [ ] **T3 — Seed groups.** Data migration 0002 seeds the 3 groups (independent 10%/direct, in_house 0%/payroll, bdu 10%/direct). → verify: migrate applies; 3 rows present.
- [ ] **T4 — Service.** `service.py`: pure `compute_totals`, `recompute_submission`, `submit`, `review`, `payout_rows`, `export_payout_csv`, `monthly_summary`. → verify: pure-python unit test of the math + flow.
- [ ] **T5 — Access + API.** `access.py`, `serializers.py`, `api_views.py`; wire router block in `api_router.py`. → verify: `manage.py check`; endpoints resolve.
- [ ] **T6 — Tests.** `tests.py`: withholding math (10% / 0%), totals recompute, submit→review flow, self-approval block, export ready/held split. → verify: `manage.py test commissions` green.
- [ ] **T7 — Frontend.** `commissions/page.tsx`, `api.ts` helpers, Sidebar + CommandPalette entries. → verify: typecheck / build; page renders locally.
- [ ] **T8 — Commit to `feat/commissions`.** Do NOT merge to main (main auto-deploys 05:09). → verify: branch pushed, clean diff.

## Withholding rules (CFO-confirmed 2026-07-15)
- Independent, direct → 10%; independent via a company → 0% (`works_via_company`).
- In-house → 0% (payroll). BDU → 0% (payroll).

## Later (separate job): back-load historical commission sheets
- Server-side upload + parse (openpyxl / local OCR) → submission lines. Client
  names stay in omni — never in chat or an external AI (AD-POL-AI-GOV-001).
- Needs a real sample sheet to map columns (don't guess).

## Held for CFO go (RULE #2 pause reasons)
- **Deploy to live prod** (new agent-payment workflow — outward/irreversible; prior session reserved this for EXCO).
- **Send the EXCO announcement email** (sending on his behalf is his call, per the handover).
