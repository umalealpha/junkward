# Odoo Migration — Tasks

Sequential build plan. Each task is a single commit unit.

## Phase 1 — Scaffolding

- [ ] **T1.1** Create `ops/migrations/odoo/__init__.py`
- [ ] **T1.2** Create `ops/migrations/odoo/client.py` — `OdooClient` (auth, search_read pagination, exponential backoff)
- [ ] **T1.3** Create `ops/migrations/odoo/mapping.py` — `ACCOUNT_TYPE_MAP`, `EXCLUDE_ADIC` filter, date cutoff constants
- [ ] **T1.4** Stub `ops/migrations/odoo/importers/{accounts,partners,journal_entries}.py` with `ImportResult` dataclass and `import_*` function signatures

## Phase 2 — XML-RPC client

- [ ] **T2.1** Implement `OdooClient.__init__` reading env vars with fail-closed validation
- [ ] **T2.2** Implement `OdooClient.authenticate` — return uid, raise on failure
- [ ] **T2.3** Implement `OdooClient.search_read` generator — pages 500 at a time, supports any model + domain + fields
- [ ] **T2.4** Implement `_call` retry wrapper — exponential backoff (1s, 2s, 4s) on 5xx + connection errors
- [ ] **T2.5** Unit test `tests/test_client.py` with mocked XML-RPC: pagination, retries, env-var fail-closed

## Phase 3 — Chart of Accounts importer

- [ ] **T3.1** `importers/accounts.py::import_accounts(client, run_id, *, dry_run=True)` — applies `EXCLUDE_ADIC`
- [ ] **T3.2** `ACCOUNT_TYPE_MAP` covering all Odoo `user_type_id` values to Omni `AccountType` choices
- [ ] **T3.3** Idempotency via `Account.objects.get_or_create(code=...)`; never overwrite existing accounts (1990 / 2150 / 2160 / 2199 / etc. stay)
- [ ] **T3.4** Stamp `external_ref = f"odoo:account.account:{id}"` (new field — see Phase 6)

## Phase 4 — Partner importer (vendors + customers)

- [ ] **T4.1** `importers/partners.py::import_vendors(client, run_id, *, dry_run)`
- [ ] **T4.2** `importers/partners.py::import_customers(client, run_id, *, dry_run)`
- [ ] **T4.3** Dual-role partners: two `Contact` rows with `external_ref` suffix `:vendor` / `:customer`
- [ ] **T4.4** Currency lookup with `get_or_create`

## Phase 5 — Journal entries importer

- [ ] **T5.1** `importers/journal_entries.py::import_moves(client, run_id, *, dry_run)`
- [ ] **T5.2** Domain `[('state','=','posted'), ('company_id','not in',[4]), ('date','<=','2026-03-31')]`
- [ ] **T5.3** For each move: fetch `account.move.line` lines, build `JournalEntry` + `JournalEntryLine` rows
- [ ] **T5.4** Skip move if any line references a CoA code missing from alpha-finance (log + result.failed)
- [ ] **T5.5** Wrap each move in `transaction.atomic` so a bad move doesn't poison the batch
- [ ] **T5.6** `entry_number` prefix `ODOO-<odoo_move_id>`, `journal_type='general'`, `source_type='odoo_import'`

## Phase 6 — `external_ref` field on target models

- [ ] **T6.1** Add `external_ref` `CharField(max_length=100, blank=True, default='', db_index=True)` to `ledger.Account`
  - Migration `ledger/migrations/0010_account_external_ref.py`
- [ ] **T6.2** `billing.Contact.external_ref` already exists (verified per recon — `seed_vendors_from_odoo.py` uses it). Verify field name + reuse.
- [ ] **T6.3** `ledger.JournalEntry.source_type` already supports arbitrary strings — no schema change

## Phase 7 — Runner + management command

- [ ] **T7.1** `ops/migrations/odoo/runner.py` — orchestrate the importers in order (CoA → partners → JEs), enforce dependency order
- [ ] **T7.2** `ops/management/commands/migrate_odoo.py`:
  - `--dry-run` (default), `--commit`, `--models`, `--resume <run_id>`, `--cutoff`, `--verbose`
  - Generate `run_id = uuid4()` on each invocation
- [ ] **T7.3** Write summary to `ops/migrations/odoo/runs/<run_id>.json` with counts per model
- [ ] **T7.4** `AuditLog` row on completion summarising the run

## Phase 8 — Reconciliation command

- [ ] **T8.1** `ops/management/commands/reconcile_odoo_import.py` — for each model, compare alpha-finance row counts (where `external_ref LIKE 'odoo:%'`) to Odoo's reported counts
- [ ] **T8.2** Exit 0 on clean match, 1 on drift

## Phase 9 — Tests

- [ ] **T9.1** `ops/migrations/odoo/tests/test_mapping.py` — sample records → expected target rows
- [ ] **T9.2** ADIC company-id record gets skipped even if filter "missed it" (defensive belt)
- [ ] **T9.3** Date > 2026-03-31 gets skipped even if filter missed it
- [ ] **T9.4** Re-import of same Odoo id produces zero new rows
- [ ] **T9.5** Move with missing CoA code is logged + skipped, doesn't crash the batch

## Phase 10 — Docs

- [ ] **T10.1** `ops/migrations/odoo/README.md` — env-var setup, dry-run instructions, recovery procedure
- [ ] **T10.2** Update `CLAUDE.md` with a short pointer

## Phase 11 — Ship

- [ ] **T11.1** Open PR `feat(ops): one-shot Odoo migration with cutoff 2026-03-31, exclude ADIC` — link issue if any
- [ ] **T11.2** CI green
- [ ] **T11.3** Squash-merge to main
- [ ] **T11.4** **Hold deployment** until CFO rotates Odoo password
- [ ] **T11.5** On rotation: add `ODOO_*` env vars to `/etc/alpha-finance/.env` on the EC2
- [ ] **T11.6** Run `python manage.py migrate` (for `external_ref` column) and `python manage.py migrate_odoo --dry-run --verbose` from inside the backend container
- [ ] **T11.7** Review the dry-run summary with the CFO before `--commit`
- [ ] **T11.8** `python manage.py migrate_odoo --commit` once approved
- [ ] **T11.9** `python manage.py reconcile_odoo_import` to confirm clean

## Definition of Done

A fresh dry-run reports realistic counts for CoA, vendors, customers, and journal entries (no ADIC rows, no post-2026-03-31 rows). A `--commit` writes them idempotently. A second `--commit` is a clean no-op. Reconcile command exits 0.
