# Salvage Portal — Design

**Status**: Draft · **Last updated**: 2026-05-14

## 1. App layout

New Django app `salvage/` next to `payroll/`, `claims/`, `procurement/`.
New Next.js route group at `frontend/src/app/(dashboard)/salvage/`.

```
salvage/
  models.py
  serializers.py
  api_views.py
  permissions.py     ← VCM/ADIC-only gate
  admin.py
  management/commands/
    import_motor_liquidators.py   ← one-off SQLite → Postgres
  migrations/
    0001_initial.py
```

## 2. Data model

```python
class PartCategory(BaseModel):
    name, description, is_active

class VehicleBrand(BaseModel):
    name, is_active

class VehicleModel(BaseModel):
    brand = FK(VehicleBrand)
    name, is_active

class SalvageItem(AuditableMixin, BaseModel):
    item_code        = CharField(unique=True)            # 'SAL-2026-0001' style; existing codes preserved on import
    claim_number     = CharField(blank=True)             # links to claims module later (no FK in v1)
    policy_number    = CharField(blank=True)
    category         = FK(PartCategory, null=True)
    part_name, part_description, quantity (default 1)
    vehicle_brand    = FK(VehicleBrand, null=True)
    vehicle_model    = FK(VehicleModel, null=True)
    vehicle_year, vehicle_colour, vin_number
    condition        = Choices: excellent/good/fair/poor/scrap
    asking_price, reserve_price  (Decimal 18,2)
    status           = Choices: available / reserved / sold / scrapped / on_hold
    location         (warehouse bay / row)
    company          = FK(core.Company)                  # always VCM, but stored for future multi-yard
    created_by, posted_at

class SalvageImage(BaseModel):
    item             = FK(SalvageItem, related_name='images')
    image            = ImageField(upload_to='salvage/%Y/%m/')
    caption, ordering

class BuyerQuote(AuditableMixin, BaseModel):
    item             = FK(SalvageItem, related_name='quotes')
    buyer_name, buyer_email (blank), buyer_phone, buyer_company (blank)
    offered_price    = Decimal 18,2
    message
    status           = Choices: pending/under_review/accepted/rejected/countered
    reviewed_by      = FK(User, null=True)
    review_notes, reviewed_at

class Sale(AuditableMixin, BaseModel):
    item             = OneToOne(SalvageItem)
    quote            = FK(BuyerQuote, null=True)         # null if walk-in
    sold_price       = Decimal 18,2
    buyer_name, buyer_phone, buyer_company, buyer_email
    sold_by          = FK(User)
    sold_at          = DateTimeField
    invoice          = FK(billing.Invoice, null=True)    # set later by finance
    notes

class Approval(BaseModel):
    sale             = OneToOne(Sale)
    approver         = FK(User)
    approved_at, decision (approve/reject), notes
    threshold_bwp    = Decimal 18,2   # snapshot of the rule at approval time

class StockCount(AuditableMixin, BaseModel):
    started_at, completed_at, counted_by = FK(User)
    notes

class StockCountLine(BaseModel):
    count            = FK(StockCount, related_name='lines')
    item             = FK(SalvageItem)
    expected_qty     = IntegerField
    counted_qty      = IntegerField (null=True until counted)
    variance         = property (counted - expected)
```

## 3. Permissions

`salvage/permissions.py`:

```python
class IsSalvageUser(BasePermission):
    """
    Caller must be signed in AND their UserProfile.company.code ∈
    {'VCM','ADIC'}. Superusers bypass. Used by every salvage viewset.
    """
```

Sidebar visibility flag on the frontend: `me.company in ['VCM','ADIC']`.
The sidebar `Salvage` group is hidden otherwise; the user sees a 404 if
they hit `/salvage` directly.

## 4. API surface

Mounted at `/api/v1/salvage/`:

| Method · Path                                          | Purpose |
|--------------------------------------------------------|---------|
| `GET/POST  /salvage-items/`                            | List, create |
| `GET/PATCH /salvage-items/{id}/`                       | Detail, edit |
| `POST      /salvage-items/{id}/images/`                | Upload image |
| `GET/POST  /salvage-quotes/`                           | List, create |
| `POST      /salvage-quotes/{id}/accept/`               | Accept → flips item to sold + spawns Sale |
| `POST      /salvage-quotes/{id}/reject/`               |  |
| `POST      /salvage-quotes/{id}/counter/`              | body: counter_price |
| `GET       /salvage-sales/`                            | List sales |
| `POST      /salvage-sales/{id}/approve/`               | Manager approval (≥ threshold) |
| `GET       /salvage-stock-counts/`                     | List counts |
| `POST      /salvage-stock-counts/`                     | Open new count |
| `POST      /salvage-stock-counts/{id}/lines/{id}/count/`  body: counted_qty |
| `POST      /salvage-stock-counts/{id}/complete/`       | Lock the count |
| `GET       /salvage-analytics/dashboard/`              | Manager dashboard payload |
| `GET       /salvage-masterdata/{categories,brands,models}/` | For dropdowns |

All gated by `IsSalvageUser`.

## 5. Frontend

Next.js pages under `(dashboard)/salvage/`:

- `page.tsx` — landing dashboard (KPIs + recent activity)
- `inventory/page.tsx` — list / filter / search
- `inventory/new/page.tsx` — create form
- `inventory/[id]/page.tsx` — detail + edit + images + quotes tab
- `quotes/page.tsx` — quote inbox (pending first)
- `sales/page.tsx` — sales register + monthly totals
- `stock-counts/page.tsx` — open counts + history
- `stock-counts/[id]/page.tsx` — scan-through screen

Same theme tokens, Book Antiqua hero on the landing, ARIA insight
ribbon contextually ('po' context will do — Manus AI plans an
explicit 'salvage' context in a follow-up).

Sidebar entry, gated by `me.company in ['VCM','ADIC']`:

```
Salvage  (icon: Box)
  ├ Dashboard
  ├ Inventory
  ├ Quotes
  ├ Sales
  └ Stock Counts
```

## 6. State machines

```
SalvageItem.status:
  available ─create─→ available
            ─reserve(quote)─→ reserved
            ─sell─→ sold
            ─mark_scrapped─→ scrapped
            ─hold─→ on_hold
   on_hold  ─release─→ available
  reserved  ─quote_rejected─→ available
            ─sell─→ sold

BuyerQuote.status:
  pending ─review─→ under_review
          ─accept─→ accepted  (item.status → sold; Sale created)
          ─reject─→ rejected
          ─counter(price)─→ countered
```

## 7. Migration

`python manage.py import_motor_liquidators --source <path>`:
- Reads `salvage.db` via the `sqlite3` stdlib module.
- Master data first (categories, brands, models) — get_or_create by name.
- Salvage items next — get_or_create by `item_code`. Sets company=VCM,
  created_by=<bot user>.
- Quotes after items. Skips if (item_code, buyer_phone, offered_price)
  already exists.
- Reports counts per table.

Dry-run flag: `--dry-run` prints what *would* be created.

## 8. Deploy

Standard alpha-finance flow: new Django app + migration + new Next.js
routes. No extra container. Buyer-facing static HTML from the old app
is **not** ported. `node_modules/`, `server.js`, `salvage.db*` are
left under `.claude/specs/salvage-portal/source/` and never reach the
runtime image.

## 9. Risks

1. **Image volume**: existing app has them on local disk under
   `uploads/`. v1 ships without image import; salvage team re-uploads.
   Future PR can backfill from S3.
2. **User mapping**: the SQLite `users` table has 1 admin user. Their
   `email` will be matched against Omni `auth.User.email` on import;
   on miss, salvage rows are attributed to a generated `system` user.
3. **Claims linkage**: `claim_number` is a free text field today. A
   follow-up will turn it into FK once Claims module exposes a lookup.
