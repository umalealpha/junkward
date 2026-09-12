# Odoo → Omni ERP Data Migration

**Cutoff:** 31 March 2026 (inclusive)
**Source:** `odoo.alphadirect.co.bw` / database `alphadirect-odoo` (Odoo XML-RPC)
**Target:** alpha-finance Django DB on omni.alphadirect.co.bw
**Exclusions:** Alpha Direct Insurance Company (ADIC, Odoo `res_company.id = 4`) — leave untouched

## Security posture (mandatory)

- **No hardcoded credentials.** All Odoo auth values come from environment variables:
  - `ODOO_URL` (e.g. `https://odoo.alphadirect.co.bw`)
  - `ODOO_DB` (`alphadirect-odoo`)
  - `ODOO_USER` (the integration account email)
  - `ODOO_PASSWORD` (rotated; never the one that was pasted in chat)
- Read from `/etc/alpha-finance/.env` on prod, never committed.
- The migration script fails closed if any env var is missing.
- All XML-RPC requests TLS-pinned to the canonical Odoo host.

## Functional requirements

### FR-1 — Chart of Accounts
Pull every `account.account` from Odoo where `company_id != 4`. Map to alpha-finance `ledger.Account`:
- Odoo `code` → `Account.code`
- Odoo `name` → `Account.name`
- Odoo `user_type_id` mapped to `Account.account_type` choice (see design)
- `is_active = !deprecated`
- Skip if `Account.code` already exists (idempotent — preserve our seeded CoA, never overwrite 1990/2199 etc.)

### FR-2 — Journal Entries (`account.move` where `state == 'posted'`)
- `date <= 2026-03-31` and `company_id != 4`
- Each Odoo move becomes one `ledger.JournalEntry` (status POSTED, journal_type GENERAL, source_type `'odoo_import'`, source_id stored as Odoo move id)
- Each `account.move.line` becomes one `ledger.JournalEntryLine` (debit/credit/account/description/contact).
- Currency taken from Odoo move; exchange_rate from move's existing rate
- **DRY-RUN first** (no DB writes) emitting a summary; only `--commit` flag writes

### FR-3 — Vendor / Supplier master
Odoo `res.partner` where `supplier_rank > 0` and `company_id != 4` (or `company_id IS NULL` which means shared).
→ alpha-finance `billing.Contact` with `contact_type = 'vendor'`.
Idempotent on `external_ref = f"odoo:{partner.id}"`.

### FR-4 — Customer / Debtor master
Odoo `res.partner` where `customer_rank > 0` and (`company_id != 4` or shared).
→ `billing.Contact` with `contact_type = 'customer'`.
Idempotent on `external_ref`.

### FR-5 — Reference data (best-effort)
- `res.company` mapping (Odoo company id → alpha-finance Company code) — required for the FK lookups above
- `account.journal` mapping (informational only, not loaded)
- `res.currency` — only add to alpha-finance Currency if missing

### FR-6 — Audit trail
Every imported record gets:
- `external_ref = "odoo:<model>:<id>"` (unique per model+id, deduplication key)
- `notes` (or equivalent) prepended with `[Migrated from Odoo 2026-05-14]`
- A row in `AuditLog` with `action=CREATE`, `description="Odoo import"`, `user=<the management-command-running user>`

### FR-7 — Reporting
On completion, the command prints:
- Rows fetched per model
- Rows skipped (duplicates / ADIC / post-cutoff)
- Rows imported
- Rows failed (with the first 10 error excerpts)
- Total elapsed time
And writes the same to `ops/migrations/odoo/<run_id>.json`.

### FR-8 — Resumability
Each run gets a UUID; if interrupted, re-running with `--resume <run_id>` skips models already completed.

## Non-functional

- **NFR-1 Idempotency**: re-running the same migration is a no-op (every write checks `external_ref` first).
- **NFR-2 Memory**: stream Odoo results in pages of 500 (`search_read` with `offset` / `limit`) — never load full move history into memory.
- **NFR-3 Rate-limit safe**: max 5 XML-RPC calls per second; backoff on 5xx.
- **NFR-4 Atomicity per row**: each row import wrapped in `transaction.atomic` — partial failures don't poison the run.
- **NFR-5 No DB writes in dry-run**: `--dry-run` mode reads-only from Odoo, prints planned writes.

## Out of scope (deferred)

- ADIC migration (Odoo company_id = 4) — never
- Data > 2026-03-31 — never
- Active Odoo→Omni sync (real-time) — one-shot migration only
- Document/attachment migration (ir.attachment) — pure financial data this round
- Payroll history — handled separately via `setup_employees` / `setup_payroll_components`
- Custom Odoo modules / addons — only standard Odoo models

## Acceptance criteria

1. `python manage.py migrate_odoo --dry-run` produces a counts summary with non-zero rows for each of CoA, JE, Vendor, Customer
2. `python manage.py migrate_odoo --commit` imports cleanly; second invocation reports 0 new rows
3. No `ledger.Account.company` rows for ADIC are created
4. No `JournalEntry.entry_date > 2026-03-31` are created with `source_type='odoo_import'`
5. CFO can run `manage.py reconcile_odoo_import` and see a clean count match vs. Odoo
