# IFRS 17 module — design

**Copy, do not invent.** Three existing things in Omni already solve most of this; the design
is deliberately their shape so Finance recognises the screen and nothing new has to be learned.

| Borrowed from | What it gives us |
|---|---|
| `budgets/` **5-Year Plan Cockpit** (`frontend/src/lib/fiveYearModel.ts` + `/budgets/five-year`) | The move-a-figure-and-everything-moves engine: `BASE` levers → `compute(levers, on)` → `Computed`. Sliders + segment toggles. **The page owns no arithmetic.** |
| `budgets/` **PlanPack / PlanPackFile** | Draft computes live, **approval freezes `base_figures` verbatim**, files attached, Finance-only write. This is what makes a number quotable to a board — or to auditors. |
| `leases/` (IFRS 16) + `nbfira/` | The shape of a standard-specific app: `models` + `engine` + `serializers` + `views`, with the heavy arithmetic in its own module (`a1_math.py` / `builders.py` / `workflow.py`). |

---

## 1. Backend — `ifrs17/` app

```
ifrs17/
  models.py        IFRS17Valuation · IFRS17ValuationFile · IFRS17Assumption
                   IFRS17SegmentResult · IFRS17TreatyResult · IFRS17DataQualityItem
  engine.py        the authoritative arithmetic (mirrors ifrs17Model.ts exactly)
  disclosures.py   builders for the paras 100–105 tables (pattern: nbfira/builders.py)
  bridge.py        the IFRS 17 ↔ Management Accounts reconciliation
  data_request.py  writes the Empirica data-request workbook, pre-filled
  serializers.py
  api_views.py
  ingest.py        server-side ingest of the policy-level premium + IBNR + bordereaux
  migrations/
  tests/
```

### 1.1 `IFRS17Valuation` — the pack (mirrors `PlanPack`)

| Field | Notes |
|---|---|
| `entity` | default `ADIC`. Matches the Omni entity filter. |
| `label` | e.g. `FY2026 · 30 June 2026 · Empirica` |
| `valuation_date` | date |
| `status` | `draft` / `approved` / `archived` |
| `measurement_model` | `paa` (only value today; a field so GMM is a data change, not a rewrite) |
| `actuary` | `Empirica Actuaries` |
| `report_date` | 19-Aug-2026 for FY26 |
| `levers` | **JSONField** — the assumption set this valuation was run on. The slider positions. |
| `base_figures` | **JSONField, frozen on approval.** Empty while draft → screen computes live. |
| `assumptions` | JSONField — the labelled assumption register with sources |
| `narrative` | the actuary's overall assessment |
| `prepared_by` / `approved_by` / `approved_at` | maker ≠ checker enforced in the view |

`figures_locked` property, copied from `PlanPack`: `status == APPROVED and bool(base_figures)`.

### 1.2 `IFRS17SegmentResult` — why the toggles can actually work

One row per (valuation, segment): premium, commission, claims, attributable expense, unearned
premium, case reserves, IBNR, ceded premium, ceded recoveries. **Per-segment storage is the
whole reason a segment switch can remove a segment from every table** — `fiveYearModel.ts`
records that lesson in its own header, and it applies identically here.

Eight segments: Accident · Engineering · Guarantee · Liability · Miscellaneous · Motor ·
Property · Transportation. Health is a **ninth, off by default** (requirement R1) so switching
it on is the exact change Empirica recommended, not a code edit.

### 1.3 `IFRS17TreatyResult` — one row per treaty

General QS · Fire & Engineering Surplus · JBB Motor QS · Motor XL and CAT · Non-motor XL and
CAT · Facultative/AutoFac · Legal Expenses QS · FMRE Motor QS (run-off) · HCV (run-off).
Carries ceded premium, commission, recoveries, net premium cost, ceded unearned premium, and
an `evidence_basis` field — **`treaty_level` vs `aggregate_only`** — because the report is
explicit that ceded case reserves, ceded IBNR and ceded RA are aggregate-only and their treaty
split is a modelling proxy. The screen must show that distinction, not hide it.

### 1.4 `IFRS17DataQualityItem`

The ten register rows from R7: `ref`, `title`, `amount`, `severity`, `owner`, `status`,
`auditor_note`, `target_date`. Pattern: the `exceptions/` module.

### 1.5 `engine.py` — the authoritative arithmetic

Pure functions, no ORM inside the maths, so it is unit-testable against the report's own
tables. It computes, from segment rows + levers:

```
LRC          = unearned premium − acquisition cash flows deferred + loss component
LIC estimate = case reserves + IBNR + CHE reserve − expected salvage/subrogation
CHE reserve  = che_factor × (gross IBNR + ½ gross case reserves)
salvage      = salvage_pct × (gross case reserves + gross IBNR)
RA           = ra_pct × fulfilment cash flows            (gross and ceded)
IBNR         = paid chain ladder by UWY, volume-weighted age-to-age, dev 1–7,
               tail factor = lever;  IBNR = ultimate − observed − case reserves
revenue      = premiums received + movement in LRC
ISE          = incurred claims + attributable expenses + RA on current-period claims
               + amortisation of acquisition cash flows − changes to LIC past service
attributable = attributable_share × total opex, allocated pro-rata to premium
net RI       = −ceded premium allocation + amounts recoverable
```

**Discounting is a no-op while the lever is off** — the election, not an omission. Turning it
on must be a visible, labelled line, never a silent change.

**Parity test (hard gate):** `engine.py` and `ifrs17Model.ts` must return the same numbers to
the cent for the FY2026 base case, and both must reproduce the report. A CI test asserts the
report's own figures — insurance revenue **133,416,295**, ISE **113,980,546**, service result
before RI **19,435,749**, net RI **(6,571,505)**, **PBT 12,864,243**, insurance contract
liabilities **49,927,070**, reinsurance contract assets **35,443,271**, net **14,483,799**,
gross IBNR **21,155,286**, net IBNR **6,672,465**, combined ratio **82%**. Any drift fails the
build. This is the `per-entity-pl-check.py` idea applied to IFRS 17.

### 1.6 Routes

`/api/v1/ifrs17/valuations/` (CRUD) · `.../<id>/approve/` (freeze) ·
`.../<id>/disclosures/` · `.../<id>/bridge/` · `.../<id>/data-request/` (xlsx) ·
`.../<id>/export/` (xlsx + docx) · `.../<id>/quality/` (register).
Registered on the router **and added to `core/tests/route_manifest_baseline.txt`** — a viewset
written and never wired is a mistake this codebase has made twice.

---

## 2. Frontend

### 2.1 `frontend/src/lib/ifrs17Model.ts` — the engine

Exactly the shape of `fiveYearModel.ts`:

```ts
export interface Levers {
  raPct: number            // 0.06
  confidenceLevel: number  // 75
  cheFactorPct: number     // 0.024779704082
  salvageSubroPct: number  // 0.062015
  attributableSharePct: number  // 0.929
  ibnrTailFactor: number   // 1.003100
  discounting: boolean     // false
  jbbCommissionPct: number // 0.25   → 0.41
  onerousTest: boolean     // false
  healthModelled: boolean  // false
}
export const BASE: Levers = { ... }          // Empirica FY2026, verbatim
export const SEGMENTS: Segment[] = [ ... ]   // per-segment, from Table 16 + Table 42
export const TREATIES: Treaty[] = [ ... ]    // Tables 25–29
export function compute(levers: Levers, on: Set<SegmentId>): Computed
```

`Computed` carries: `revenue · ise · serviceResultBeforeRI · netRI · pbt · lrc · licEstimate ·
licRA · insuranceContractLiabilities · reinsuranceContractAssets · netPosition · grossIBNR ·
netIBNR · combinedRatio · lossRatio · bySegment[] · byTreaty[] · byUwy[] · disclosures{...} ·
deltaVsBase{...}`.

Header comment carries, in the `fiveYearModel.ts` tradition: the source file, the report date,
"implemented AS-IS — no figure in the base layer deviates from the report", and the **known
variances not to silently fix** (the 21,490 trial-balance difference, the 149,104 overlay, the
505,382 unposted opening difference).

### 2.2 `/ifrs17` — the cockpit

- **Lever rail** (left): a labelled slider per lever, each showing base → current and the
  delta it causes. Segment toggles as chips, Health visibly OFF with a "not modelled — Empirica
  recommends before FY2027" hint. Motion + spacing per the house design directives (Emil
  Kowalski easing, 4/8px scale, navy `#0D1B2A` / orange `#F4A623`).
- **Tabs:** `Results` · `Statements` · `Reserves` · `Reinsurance` · `Disclosures` · `MA bridge`
  · `Data quality` · `Library`.
- **JBB commission slider gets its own callout** on the Reinsurance tab: drag 25% → 41% and the
  screen shows **+8,712,000 of commission**, labelled *"sensitivity — not recognised"* in the
  report's own words. Never presented as bookable.
- Negatives in red, bold subtotals, deltas always vs base — same visual grammar as the 5-year
  cockpit, so it reads the same way.
- **Library** tab = the pack archive (draft/approved/archived), mirroring the Budget and
  Strategic Plan libraries: an approved valuation reads its frozen figures; a draft shows live
  cockpit figures with an "unapproved — computed live" badge.

### 2.3 Exports

- **xlsx** — one sheet per disclosure table, plus the pre-filled Empirica data-request workbook
  in its own tab layout.
- **docx** — the disclosure notes as they go into the financial statements, house template.
  Reuse the report-generation pattern already used for the BONU Fee Note and Quarterly reports.

---

## 3. The MA bridge (`bridge.py`) — the first thing built

One table, permanently on screen, both directions:

```
IFRS 17 profit before tax                                  12,864,243
  + non-attributable expenses excluded from the service result   2,212,937
  + investment income and other income (MA, outside IFRS 17)          ...
  − ceded reserve movement taken as income under IFRS 17               ...
  − tax                                                                ...
= Management Accounts PAT                                            ...
```

FY2025 is the acid test: the bridge must walk **26,838,707 → 0.292M** and show every step.
Until it does, the module ships nothing else. The `FROZEN_NUMBERS` idea from
`digital-cfo-avatar/tools.py` applies: if a bridged figure disagrees with the frozen register,
**surface both and say which is registered truth** — never pick silently.

---

## 4. What this module explicitly does NOT do

1. It does **not** replace Empirica. Selected IBNR, RA calibration and development factors are
   stored as a signed, dated opinion with the report attached.
2. It does **not** post to the GL. Journal entries from an IFRS 17 valuation are a separate,
   CFO-signed step.
3. It does **not** touch GL mapping, the MA format, or the dashboard GWP tile.
4. It does **not** show a policy row anywhere. The 35MB policy-level premium file is ingested
   server-side and aggregated on the way in.

---

## 5. Build order (rationale)

The bridge first, because it is the live misquote risk. Then the engine + parity test, because
nothing else can be trusted until the module reproduces the report to the cent. Then the
cockpit, which is what the CFO actually asked to drive. Disclosures and the data-request
generator last — they are formatting over an engine that is already proven.
