# omni / alpha-finance — guardrails & recurring failure patterns

Source: full forensic audit 2026-06-11 (5 parallel auditors over the 85k-LOC
backend, 28 Django apps). Read this before touching any financial-posting,
reporting, upload, or permission code. The ledger CORE is well-built — the
recurring failures are at the EDGES and in MISSING TESTS.

## The one rule that protects everything
**Every PR that touches `ledger`, `reporting`, posting services, or permissions
must keep the CI invariant suite green** (`ledger/tests/test_financial_invariants.py`,
run by `.github/workflows/ci.yml`). If you change posting/immutability/period/
isolation behaviour, update the tests in the SAME PR — never delete a test to
make a build pass. CI runs `manage.py check` + `makemigrations --check` +
the suite on a clean postgres:16.

## Recurring failure patterns (these keep recurring — check for them every time)

1. **Entity-isolation leak on list/report endpoints.** A queryset that filters
   by company ONLY when `?company=` is supplied leaks all 12 entities when the
   param is absent. FIX: use `CompanyScopedViewSetMixin` (Branch B scopes to
   the caller's `allowed_company_ids`), NOT a bare `resolve_company_id_param`
   that returns None→no-filter. Report APIViews (`reporting/views.py`,
   `reporting/dashboard.py`, `ledger/views.py TrialBalanceView`) default to an
   all-entity rollup — a number the CFO reads as ADIC but is a 12-entity merge.
   This is the #1 "wrong number reaches the CFO" / FROZEN-NUMBERS risk.

2. **IDOR on detail/delete/confirm/reject.** A list view scopes to the user but
   the detail/mutate view does `Model.objects.get(pk=pk)` with no owner scope —
   any authenticated user actions another's record by UUID. FIX: scope the
   lookup to owner-or-staff (see `documents/views.py _get_owned_upload`).

3. **`company=NULL` on auto-posted JEs.** Every posting service MUST pass
   `company=` to `JournalEntry.objects.create`. Reinsurance (`reinsurance/
   services.py`) and batch upload (`ledger/api_views.py`) omit it → those JEs
   are invisible to per-entity reports AND bypass `ledger/locks.py` (which
   short-circuits when `company_code != 'ADIC'`). NOTE: Cession/Treaty have no
   company field — needs a decided entity source, not a guess.

4. **Silent `except Exception: pass` in a calc path ships a wrong number.**
   `payroll/models.py recompute_totals` swallows a failed PAYE recompute and
   saves stale tax; the healthcare parser falls back to heuristic silently.
   FIX: log + set a `*_failed` flag + block downstream posting; never `pass`
   on a path that produces a financial figure. (There is no `LOGGING` config
   in settings — WARNING-level logs are invisible to the morning-check.)

5. **Duplicate-import double-count.** No unique constraint = re-upload sums
   twice (the healthcare GWP bug Tlamelo hit; bank statements have the same
   gap). FIX: `UniqueConstraint` on the business key
   (`HealthcareUpload(kind,period_year,period_month,direction)`;
   `BankStatement(bank_account,statement_date,closing_balance)` or a file hash).

6. **Posting/immutability enforced in ONE place, no DB backstop.** Balance
   (debits==credits) is checked only in `post()`, not at the DB/model level —
   any `.update(status='posted')` or direct create bypasses it. Keep the
   invariant tests as the guard; consider a model `clean()` / DB CHECK.

7. **`is_taxable` flag is decorative.** PAYE keys taxability off
   `component.kind` (EARNING vs EARNING_NON_TAXABLE), NOT the `is_taxable`
   field — a mis-catalogued component silently mis-taxes. Tax tables: never
   have two active `TaxBracket` rows share a `lower_bound` (resident +
   non-resident overlap → ordering-dependent mis-select; see
   [[p-paye-check-2026]]).

8. **Payslip totals not recomputed on save.** The docstring claims it; there's
   no `save()`/signal hook. A serializer/admin edit persists stale net that
   posts the wrong salary-payable. FIX: recompute in `save()` or a signal, and
   assert `net == gross − paye − deductions` before `post_payroll_period`.

9. **Deploy that reports green while broken.** The smoke probe must FAIL the
   job (exit 1) on non-2xx/3xx, not echo WARN. Deploy has no migration
   rollback or pre-migrate snapshot — a bad migration bricks prod. Take an
   inline `pg_dump` before `migrate` and gate on a health check.

10. **Posted-JE hard-delete (`JEClearingRequest`).** A bulk date-range DELETE
    of POSTED entries via raw SQL, bypassing immutability, not intersected
    with locked periods. By CFO directive — do NOT remove without sign-off,
    but it's the single highest-blast-radius surface. Prefer reversal.

## Compose / ops landmines
- `docker-compose.yml` uses `${VAR:?}` (hard-fail) on `SECRET_KEY`,
  `DJANGO_SUPERUSER_PASSWORD`, `DB_PASSWORD` — if any is unset in
  `/etc/alpha-finance/.env`, EVERY `docker compose` command fails at parse
  time (incl. `ps`/`logs`/backup). Workaround to run shell on prod:
  `sudo docker exec -i alpha-finance-backend python manage.py shell < script`.
- Default credentials to remove: Telegram bot `admin123` (`bot.py`), frozen-
  drift override `Alpha@12345` (`ledger/locks.py`, `cfo_upload.py`) — confirm
  `OMNI_FINANCIAL_LOCK_OVERRIDE` is set in prod.
- `django-axes` lockout state is per-process (no shared `CACHES`) → brute-force
  protection diluted ~4× across gunicorn workers. Add a Redis/DB cache backend.

## How to run financial checks on prod (Windows)
AWS CLI profile **claude-cli** (scoped IAM: SSM+EC2-read+S3, no console). SSM
`AWS-RunShellScript`; base64 a python script and pipe into
`docker exec -i alpha-finance-backend python manage.py shell`. See
[[r-omni-bkp]] for the profile + [[p-system-sweep]]
patterns.
