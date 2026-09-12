# Salvage Portal — Tasks

**Status**: Draft · **Last updated**: 2026-05-14

Phased so each PR is < 600 LoC and ships independently. Stop after
any phase if priorities change.

## Phase 1 — Skeleton + read-only inventory (≈ 1 day)

- [ ] T1.1 New Django app `salvage/` (`apps.py`, registered in
      `INSTALLED_APPS`).
- [ ] T1.2 Models: `PartCategory`, `VehicleBrand`, `VehicleModel`,
      `SalvageItem`, `SalvageImage`. Initial migration `0001_initial`.
- [ ] T1.3 `permissions.IsSalvageUser` (VCM/ADIC gate). Unit-test it.
- [ ] T1.4 `SalvageItemViewSet` read-only (`list`, `retrieve`).
      Serializer with vehicle + category nested.
- [ ] T1.5 `masterdata` endpoint (categories / brands / models).
- [ ] T1.6 `management/commands/import_motor_liquidators.py` with
      `--dry-run`. Imports master data + 51 items + assigns company=VCM.
- [ ] T1.7 Next.js routes:
      - `(dashboard)/salvage/page.tsx` — landing (placeholder KPIs)
      - `(dashboard)/salvage/inventory/page.tsx` — list/filter
      - `(dashboard)/salvage/inventory/[id]/page.tsx` — read-only detail
- [ ] T1.8 Sidebar entry, gated by `me.company in ['VCM','ADIC']`.
- [ ] T1.9 Deploy + run import on prod. Verify 51 items show on
      `/salvage/inventory` for a VCM user, 403 for others.

## Phase 2 — Inventory write + quotes (≈ 1 day)

- [ ] T2.1 `SalvageItem` create / update via DRF. Form validation
      (asking ≥ reserve, etc).
- [ ] T2.2 Image upload endpoint + `SalvageImage` model. S3 in prod.
- [ ] T2.3 `BuyerQuote` model + viewset. `accept` / `reject` /
      `counter` actions (state machine).
- [ ] T2.4 On `accept` → `Sale` row + item.status='sold'. Atomic.
- [ ] T2.5 Frontend: `inventory/new`, edit modal on detail page,
      quotes tab on item detail.
- [ ] T2.6 `quotes/page.tsx` — inbox, status filter, action buttons.
- [ ] T2.7 Import buyer_quotes (38 rows) in the management command.

## Phase 3 — Sales register + approvals + stock counts (≈ 1 day)

- [ ] T3.1 `Sale` model already exists; add list endpoint + monthly
      summary.
- [ ] T3.2 `Approval` model + endpoint. Threshold from `Settings`
      (default BWP 50 000).
- [ ] T3.3 `StockCount` + `StockCountLine` models. Open / scan /
      complete endpoints.
- [ ] T3.4 Frontend pages: sales, stock-counts list, stock-count
      detail (scan-through screen).
- [ ] T3.5 Dashboard hooked up (stock value, quotes by status, sales
      by month).
- [ ] T3.6 ARIA insight ribbon on `/salvage` (re-use `po` ctx for now;
      add `salvage` ctx in a follow-up).

## Phase 4 — Polish + handover (≈ 0.5 day)

- [ ] T4.1 Walk through with VCM team (Moses, Tshephang, Lesego,
      Tumiso). Capture friction list.
- [ ] T4.2 README in `salvage/` covering the import command + how to
      flip the threshold.
- [ ] T4.3 Decommission note added to `.claude/specs/salvage-portal/source/README.md`
      so the old node app is officially marked superseded.

## Definition of done (each phase)

- Tests green; `python manage.py test salvage` passes.
- A VCM user can use the new screens; a UNI user gets a clean
  "page not found" with no data leakage.
- One screenshot in the PR description showing the deployed page.
- The `import_motor_liquidators` command is re-runnable (idempotent).
