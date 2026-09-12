# Odoo Migration — Design

## Module surface

New directory: `ops/migrations/odoo/`

```
ops/migrations/odoo/
  __init__.py
  client.py            # XML-RPC client wrapper (auth, search_read with pagination, retries)
  mapping.py           # Odoo→Omni field-level mappers (CoA, JE, partners, currencies)
  importers/
    __init__.py
    accounts.py        # Chart of Accounts
    partners.py        # Customers + Vendors
    journal_entries.py # account.move + account.move.line
  runner.py            # Run orchestration: counts, resumability, audit log
```

Django management command: `ops/management/commands/migrate_odoo.py`

## XML-RPC client (`client.py`)

```python
class OdooClient:
    def __init__(self):
        self.url      = os.environ['ODOO_URL']      # https://odoo.alphadirect.co.bw
        self.db       = os.environ['ODOO_DB']       # alphadirect-odoo
        self.user     = os.environ['ODOO_USER']
        self.password = os.environ['ODOO_PASSWORD'] # fail-closed if unset
        self._uid     = None
        self._common  = ServerProxy(f"{self.url}/xmlrpc/2/common", allow_none=True)
        self._models  = ServerProxy(f"{self.url}/xmlrpc/2/object", allow_none=True)

    def authenticate(self) -> int:
        self._uid = self._common.authenticate(self.db, self.user, self.password, {})
        if not self._uid:
            raise PermissionDenied("Odoo authentication failed")
        return self._uid

    def search_read(self, model, domain, fields, *, batch_size=500):
        """Generator that pages through Odoo records 500 at a time."""
        offset = 0
        while True:
            chunk = self._call('execute_kw',
                self.db, self._uid, self.password,
                model, 'search_read',
                [domain],
                {'fields': fields, 'offset': offset, 'limit': batch_size, 'order': 'id asc'}
            )
            if not chunk:
                return
            yield from chunk
            if len(chunk) < batch_size:
                return
            offset += batch_size

    def _call(self, fn, *args, _max_retries=3):
        # exponential backoff on 5xx / connection errors
        ...
```

## Common filters (the global where-clause every importer applies)

```python
EXCLUDE_ADIC      = ('company_id', 'not in', [4])      # Alpha Direct Insurance Company ID 4
DATE_CUTOFF       = ('date', '<=', '2026-03-31')
ACTIVE_ONLY       = ('active', '=', True)
POSTED_ONLY       = ('state', '=', 'posted')
```

## Importer pattern (mirror this for each model)

```python
@dataclass
class ImportResult:
    fetched: int
    skipped_duplicate: int
    skipped_adic: int           # safety belt; the filter already excludes
    skipped_post_cutoff: int    # safety belt
    imported: int
    failed: int
    errors: list[str]           # first 10

def import_<model>(client, run_id, *, dry_run=True) -> ImportResult:
    result = ImportResult(0, 0, 0, 0, 0, 0, [])
    for record in client.search_read(MODEL, DOMAIN, FIELDS):
        result.fetched += 1
        # Safety belt: never trust the filter
        if record.get('company_id') and record['company_id'][0] == 4:
            result.skipped_adic += 1
            continue
        external_ref = f"odoo:{MODEL}:{record['id']}"
        if Target.objects.filter(external_ref=external_ref).exists():
            result.skipped_duplicate += 1
            continue
        if dry_run:
            result.imported += 1
            continue
        try:
            with transaction.atomic():
                _create_from_odoo(record, external_ref)
                result.imported += 1
        except Exception as exc:
            result.failed += 1
            if len(result.errors) < 10:
                result.errors.append(f"{record['id']}: {exc}")
    return result
```

## Chart of Accounts mapping

| Odoo `account.account` | Omni `ledger.Account` |
|---|---|
| `code` | `code` |
| `name` | `name` |
| `user_type_id` → mapped via `ACCOUNT_TYPE_MAP` | `account_type` |
| `deprecated == False` | `is_active` |
| (currency from `currency_id`) | `currency_code` |
| n/a | `sub_type = 'imported'` (until manually classified) |
| n/a | `description = "[Migrated from Odoo on 2026-05-14]"` |

`ACCOUNT_TYPE_MAP` (Odoo → Omni `AccountType`):
- `asset_*` → `asset`
- `liability_*` → `liability`
- `equity_*` → `equity`
- `income*` → `revenue`
- `expense*` → `expense`
- anything else → `asset` + log warning

**Idempotency:** `Account.objects.get_or_create(code=record['code'], defaults={...})`. Never overwrite an existing account — our 1990 / 2199 / etc. stay intact.

## Journal Entries mapping

```python
DOMAIN = [
    ('state', '=', 'posted'),
    ('company_id', 'not in', [4]),
    ('date', '<=', '2026-03-31'),
]
FIELDS = ['id', 'name', 'date', 'company_id', 'currency_id',
         'journal_id', 'ref', 'narration', 'line_ids']
```

For each move: read line_ids → `client.search_read('account.move.line', [('move_id','=',move_id)], LINE_FIELDS)`.

| Odoo `account.move` | Omni `JournalEntry` |
|---|---|
| `name` | `entry_number` (prefix `ODOO-`) |
| `date` | `entry_date` |
| `narration` or `ref` | `description` |
| n/a | `journal_type = 'general'` |
| n/a | `source_type = 'odoo_import'`, `source_id = odoo_move_id` |
| `currency_id` | `currency_code` (FK lookup) |
| `company_id` | `company` (FK lookup via mapping) |
| n/a | `status = 'posted'` |
| n/a | `is_related_party = False` (manual review later) |
| n/a | `created_by = <command-runner user>` |

For each `account.move.line` → `JournalEntryLine`:
- `account_id` → FK to `ledger.Account.code`
- `debit` / `credit` → `debit_amount` / `credit_amount`
- `partner_id` → `contact` FK (if mapped)
- `name` → `description`

**Skip rule:** if any line references an account code not in alpha-finance, fail the whole move (rollback via `transaction.atomic`) and log the missing code. The CoA importer should run first.

## Partner mapping (Vendors + Customers)

Source: `res.partner`.

```python
VENDOR_DOMAIN   = [('supplier_rank', '>', 0), ('company_id', 'not in', [4])]
CUSTOMER_DOMAIN = [('customer_rank', '>', 0), ('company_id', 'not in', [4])]
```

| Odoo `res.partner` | Omni `billing.Contact` |
|---|---|
| `name` | `name` |
| `vat` | `tax_id` |
| `email` | `email` |
| `phone` / `mobile` | `phone` |
| `street`+`city` | `address` |
| `country_id` | `country` |
| derived from rank | `contact_type = 'vendor'` or `'customer'` |
| n/a | `external_ref = f"odoo:res.partner:{id}"` |
| `is_company` | (informational) |

A partner that is both vendor + customer gets two `Contact` rows (one of each type), each with a distinct `external_ref` suffix (`:vendor` / `:customer`).

## Currency mapping
Odoo `res.currency.name` (e.g. `USD`) → `core.Currency.code`. If missing in alpha-finance, create with `get_or_create`.

## Management command

`ops/management/commands/migrate_odoo.py`:

```
usage: manage.py migrate_odoo [--dry-run | --commit]
                              [--models cox,partners,journal_entries]
                              [--resume <run_id>]
                              [--cutoff 2026-03-31]
                              [--verbose]
```

- Default `--dry-run` (safety first).
- `--commit` actually writes. Refuses if any of CoA/partners/etc. haven't been dry-run-validated in the same run.
- Stamps each row's `external_ref`, writes summary JSON to `ops/migrations/odoo/<run_id>.json`.

## Tests (`ops/migrations/odoo/tests/`)

`test_client.py`:
- Mock XML-RPC server returning fixture data, verify pagination + retry behaviour
- Verify env-var loading fails closed

`test_mapping.py`:
- Sample Odoo records → expected Omni rows (CoA, JE, partner)
- ADIC company-id record gets skipped even if filter "missed it"
- Date > 2026-03-31 gets skipped even if filter missed it
- Re-import of same Odoo id produces zero new rows

`test_command.py`:
- `--dry-run` writes nothing
- `--commit` after `--dry-run` writes expected counts

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Odoo schema differs from this design's field assumptions | Run `--dry-run --verbose` first; the verbose mode dumps Odoo's raw record for the first 3 of each model so we catch shape mismatches before commit |
| Account code clash between Odoo and our seeded CoA (e.g. Odoo also has `1990` for something else) | `get_or_create(code=...)` — Odoo's row gets SKIPPED, our seeded row wins. Logged as duplicate. |
| Move references account not yet imported | CoA importer must run FIRST. Command enforces order via dependency graph. |
| Multi-company moves spanning ADIC + non-ADIC | Odoo doesn't allow cross-company moves; filter on `move.company_id != 4` is sufficient |
| Currency missing from alpha-finance | Auto-create via `get_or_create` |
| Massive move history runs > 1 hour | Pagination of 500; resumable via `--resume <run_id>` |
| Partner is both vendor + customer | Two `Contact` rows with distinct `external_ref` suffix |
