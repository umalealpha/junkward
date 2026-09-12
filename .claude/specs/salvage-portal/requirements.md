# Salvage Portal — Requirements

**Status**: Draft · **Owner**: CFO · **Last updated**: 2026-05-14

## 1. Why

Veritas Capital Management (VCM) operates Alpha Direct's salvage yard.
Today the team runs a standalone Node.js + Express + SQLite app
(motor-liquidators), shipped to Claude on 2026-05-14. CFO directive:
fold it into Omni so there is one login, one stack, one audit trail.

## 2. Users and access

| Group                                 | Access |
|---------------------------------------|--------|
| Signed-in user whose Company is `VCM` | Full read/write on Salvage |
| Signed-in user whose Company is `ADIC`| Full read/write on Salvage |
| Everyone else (UNI, ADRG, QIH, …)     | No access. Sidebar item hidden. API returns 403. |

- Buyer-facing public portal **is dropped**. All quote intake comes via
  salvage staff entering it on behalf of the buyer.
- RBAC inside the module (staff / manager / approver) uses the existing
  `core.UserProfile.Title` + role groups — no new permission scheme.

## 3. What the module must do

### 3.1 Salvage inventory
- Create / edit / list / search salvage items. Each item carries a part
  description, vehicle context (brand / model / year / colour / VIN),
  condition (`excellent` / `good` / `fair` / `poor` / `scrap`), asking
  price, reserve price, location, status.
- Image upload (multipart, 10 MB cap, JPEG/PNG/WebP). Stored on S3 in
  prod, local media volume in dev. **Not** SQLite blobs.
- Stock-count flow: salvage manager flags items for a count, scans
  through them, the system records who counted what, when, and whether
  the physical count matched.

### 3.2 Quote intake & sales
- Quote-from-buyer record (buyer name / phone / optional email +
  company + offered price + message). Quote status state machine:
  `pending → under_review → accepted | rejected | countered`.
- On `accepted`, the salvage item flips to `sold` and a `sales` row is
  created. Sales row optionally links to a customer-invoice in
  `billing.Invoice` so finance picks it up (out of scope for v1, but
  the schema must allow it).

### 3.3 Approvals
- Sales above a CFO-configurable BWP threshold (default BWP 50 000)
  require manager approval before payout. One approver, one approval
  record per sale.

### 3.4 Analytics
- Operational dashboard for the salvage manager: current stock value
  (asking & reserve), quotes by status, sales by month, days-on-hand
  per condition bucket. No fancy reporting — these go on a small page
  inside Omni.

### 3.5 Audit
- All writes go through the existing `core.AuditableMixin` / `AuditLog`.
  No separate audit table.

## 4. Data migration

A one-off Django management command imports from
`salvage.db` (SQLite, shipped in `.claude/specs/salvage-portal/source/`)
into the new Postgres tables on cutover:

| From SQLite          | To Postgres                  | Rows  |
|----------------------|------------------------------|-------|
| `salvage_items`      | `salvage_salvageitem`        | 51    |
| `buyer_quotes`       | `salvage_buyerquote`         | 38    |
| `sales`              | `salvage_sale`               | 0     |
| `approvals`          | `salvage_approval`           | 0     |
| `users`              | (mapped to existing Django users by email; 1 row) | 1 |
| `part_categories`    | `salvage_partcategory`       | — seeded |
| `vehicle_brands`     | `salvage_vehiclebrand`       | — seeded |
| `vehicle_models`     | `salvage_vehiclemodel`       | — seeded |
| `salvage_images`     | local FK → `MediaUpload`     | — referenced |
| `audit_log`          | (dropped — Omni uses one global audit) | — |

`item_code` is preserved exactly. Vehicle brand/model FKs are
re-mapped by name. Images are not pulled in v1 (re-upload later).

## 5. Out of scope for v1

- Public buyer portal (dropped per CFO 2026-05-14).
- WhatsApp / SMS notifications to buyers.
- Multi-currency. All amounts in BWP.
- Automatic invoice generation on sale (just the FK column; the JE
  trigger is a future PR).

## 6. Non-functional

- **Stack parity**: Django app `salvage/` + DRF endpoints under
  `/api/v1/salvage/…` + Next.js pages under `/(dashboard)/salvage/…`.
  Same patterns as existing modules. **No** Node.js process anywhere.
- **Auth**: MSAL SSO same as the rest of Omni. The legacy SQLite
  password file is not migrated.
- **DPA**: buyer phone numbers are PII; they live in the same DB as
  the rest of Omni, behind the same SSO gate, and are excluded from
  ARIA prompts.
- **Tests**: Django tests cover the price / status state machine.
  No browser tests in v1.
