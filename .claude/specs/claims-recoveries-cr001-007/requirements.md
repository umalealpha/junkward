# Claims Recoveries — Subrogations & Salvages — Requirements (CR-001 → CR-007)

**Source:** Oprah Mogomotsi email to EXCO + CFO, 2026-05-28 13:26.
**Spec owner:** Claude (CFO partnership).
**Project:** alpha-finance ERP — `claims-recoveries` parent + `claims/salvages` + `claims/subrogations` + `salvage/` Django app.
**Steering rules in scope:** `.claude/steering/erp-relationships.md` (chain integrity), Prat Skill §5 (GL touch = 3x-confirm), Prat Skill §6 (post-deploy 5-step gate).

---

## Order of execution (locked)

1. **CR-001 fix — Critical, ship same session.** Bug, not enhancement.
2. CR-005 sidebar rename + badges — Low, trivial frontend.
3. CR-002 Claims Recoveries landing dashboard.
4. CR-003 Subrogations enhancements.
5. CR-004 Salvage Inventory enhancements + Veritas register.
6. **CR-006 Salvage GL posting — gated.** Requires Finance Manager to assign 3 GL codes in Settings. Requires CFO 3x-confirm on the 20% sum-insured rate.
7. **CR-007 Subrogation GL posting — gated.** Requires Finance Manager GL codes.

---

## CR-001 — Salvage Inventory access bug (Critical)

**Symptom:** Salvage Inventory page returns *"Couldn't load inventory — access restricted to VCM/ADIC"* even when the topbar company selector is set to ADIC.

**Root cause (verified by source-read 2026-05-28):**
`salvage/permissions.py::user_can_access_salvage` checks **only** `Employee.company.code` against the static `{'VCM','ADIC'}` set. It does **not** honour the topbar selector (`resolve_company_id_param(request)` → `X-Company-ID` header → `Company.code`). Users whose `Employee.company` points to a stale company row (e.g. legacy `ADI`, soft-deleted PR #104) or is null are denied even when they have legitimate access to the ADIC tenant.

**Fix:** Extend `user_can_access_salvage` to also pass when:
- The active company resolved from the request (selector / header / profile default) is in `SALVAGE_COMPANY_CODES`, **and**
- The user is permitted in that tenant via the existing `allowed_company_ids(user)` guard.

**Acceptance criteria:**
1. ADIC-permitted user with Employee.company null OR stale: selector on ADIC → 200. Selector on RSA → 403.
2. Non-ADIC/VCM user: 403 regardless of selector spoof.
3. Superuser + CFO bypass: unchanged.
4. `SalvageAccessProbeView` sidebar probe returns matching state.
5. Existing pytest suite passes; no regressions on `salvage/` viewsets.

**Affected files (≤ 3):**
- `salvage/permissions.py` — signature + new check
- `salvage/api_views.py` — pass `request` to the 3 call sites
- `salvage/tests/test_permissions.py` — add the selector-honour test (create if missing)

---

## CR-002 — Claims Recoveries landing dashboard (High)

**Replace** the current `claims-recoveries/page.tsx` redirect to `/claims/subrogations` with a parent dashboard at `/claims-recoveries`. Subrogations and Salvages become sub-items.

**KPI tiles (top row):**
| Tile | Source | Formula |
|---|---|---|
| Open Recoverables (BWP) | Subrogation + Salvage | Sum of outstanding across both sub-modules, filtered by active company |
| Recovered MTD | Subrogation + Salvage | Sum of receipts dated current month |
| Recovered YTD | Subrogation + Salvage | Sum of receipts dated current fiscal YTD |
| Recovery Ratio | Computed | Recovered / (Recovered + Open) × 100 |
| Aging buckets | Subrogation outstanding | 0-30 / 31-60 / 61-90 / 90+ days since opened |
| Top 5 debtors | Subrogation | Highest outstanding by third-party insurer |
| Top 5 salvage buyers | Salvage | Highest paid by buyer (filtered Veritas = 1 buyer in v1) |

**Behaviour:**
- Honours active company selector (CR-001 applies)
- Tiles drill-through to filtered sub-page (e.g. clicking "Aging 90+" → subrogations filtered to age ≥ 90)
- Loading skeleton + error boundary
- Mobile-responsive (CFO uses on the road)

---

## CR-003 — Subrogations page (High)

**Table columns:**
Claim Ref · Loss Date · Third Party/Insurer · Amount Claimed (BWP) · Recovered · Outstanding · Status · Age (days) · Assignee · Next Action Date

**KPI tiles at top:** Open BWP · Recovered MTD · Recovery Rate · Aging buckets

**Filters (expanded):**
- Date range: Loss date / Opened date (two pickers)
- Assignee (multi)
- Third-party insurer (multi, typeahead)
- Amount band (≤ 50k · 50k-250k · 250k-1M · > 1M)
- Age bucket (0-30 · 31-60 · 61-90 · 90+)
- "Show only mine" toggle

**Status workflow (replaces current options):**
`Identified → Demand Sent → Negotiation → Settlement Agreed → Partial → Fully Recovered → In Litigation → Written Off`

State machine, not free-form. Backward transitions allowed only with comment.

**Bulk actions:**
- Assign (single user)
- Change status (with comment if backward)
- Send demand letter (templated, attaches PDF to record)
- Write-off (requires `finance_manager` group approval + mandatory comment) — **soft only**, no permanent delete

**Export to CSV/XLSX:** respects current filters.

**Empty-state:** "Download template" link → CSV template + import instructions.

**Per record:**
- Audit trail (who/what/when, immutable)
- Attachments (police reports, demand letters)
- Comments thread
- Activity timeline
- Deep link from Claims module: `/claims/<claim_ref>/recoveries`

---

## CR-004 — Salvage Inventory page (High)

**KPI tiles:** Items on Hand · Reserved Value · Sold MTD · Avg Days-to-Sell · Recovery vs Reserve

**Table columns:**
+ Location/Yard · Reserve Price · Days in Stock · Linked Claim · Buyer

**Filters:**
- Location/Yard (multi)
- Date received (range)
- Days-in-stock band (≤ 30 · 31-90 · 91-180 · > 180)
- Linked-claim presence (Yes / No / Either)

**Quick row actions:** Reserve · Mark Sold · Scrap · Generate Sale Invoice · Link to Claim

**View toggle:** Gallery (photo grid) / Table

**Buyers sub-page:**
- Manage approved buyers, bids, offers
- Approve / reject workflow
- Veritas (VCM) is a pre-registered approved buyer (related party flag)

**Veritas Related Party Sales register (sub-report):**
Columns: Item Code · Description · Linked Claim · Sum Insured · Sale Value (= 20% × Sum Insured) · Sale Date · Invoice Ref · Payment Status (outstanding / partial / settled) · Outstanding Receivable

Capabilities:
- Export to Excel + PDF
- Reconciliation panel: `Veritas register total BWP X — GL Receivable from Veritas BWP Y — Variance BWP Z`. Variance must be 0. Red badge if not.
- NBFIRA disclosure feed: **deferred until Compliance → NBFIRA module exists.** TODO stub link.

Per record: audit trail, attachments (sale notes, photos), activity timeline, deep link to linked claim.

---

## CR-005 — Sidebar & navigation (Low)

- Rename "Salvages" → "Salvage Inventory" in `frontend/src/components/layout/Sidebar.tsx`.
- Add open-count badges on each Claims-Recoveries sub-item: `Subrogations [N open]`, `Salvage Inventory [N overdue]`.
- Counts hit a lightweight `/claims-recoveries/badge-counts/` endpoint with 60s frontend cache.

---

## CR-006 — GL posting — Salvages (Medium · gated)

**Trigger:** Salvage record status → `Sold` (Step 1) and `Fully Recovered` (Step 2).

**Step 1 — Income recognition (on mark sold):**
| Leg | Account | Amount |
|---|---|---|
| DR | Receivable from Veritas — `[CONFIG: AR_VERITAS]` | 20% × sum insured (linked policy) |
| CR | Salvage Recoveries Income — `[CONFIG: SALVAGE_INCOME]` | 20% × sum insured |

- Rate **fixed at 20%**, NOT user-editable.
- Sum insured pulled automatically from `claim → policy.sum_insured`.

**Step 2 — Receipt (on payment recorded):**
| Leg | Account | Amount |
|---|---|---|
| DR | Cash/Bank (user-selected at receipt time) | Actual amount received |
| CR | Receivable from Veritas — same as Step 1 | Actual amount received |

- Partial payments supported. AR balance reduces until zero.

**Approval:** Both JEs require `finance_manager` group approval before posting (reuses payroll PR #62 / PO PR #63 approval pattern).

**Status gates:**
- Salvage status → `Sold` ONLY after Step 1 JE approved + posted.
- Salvage status → `Fully Recovered` ONLY after Step 2 clears AR to zero.

**Config gate (BLOCKING):**
- 3 placeholders in Settings: `AR_VERITAS`, `SALVAGE_INCOME`. System blocks any salvage Sold-marking if either is unset.

**3x-confirm gates needed before code:**
1. CFO confirms 20% rate is correct + frozen.
2. Finance Manager assigns the 3 GL codes (registered in Settings).
3. CFO confirms the receivable account is shared with subrogations CR-007 or separate.

---

## CR-007 — GL posting — Subrogations (Medium · gated)

**Trigger:** Subrogation receipt recorded.

| Leg | Account | Amount |
|---|---|---|
| DR | Cash/Bank (user-selected) | Actual amount received |
| CR | Subrogation Recoveries Income — `[CONFIG: SUBRO_INCOME]` | Actual amount received |

- Partial recoveries: outstanding balance reduces with each receipt.
- Requires `finance_manager` approval before posting.

**Config gate:** `SUBRO_INCOME` placeholder in Settings. Block posting if unset.

**3x-confirm:** CFO confirms `SUBRO_INCOME` is its own account or shares with another revenue line.

---

## General rules (all tickets)

- **No permanent deletes.** All destructive actions are soft + audit-trailed.
- **Write-offs:** require `finance_manager` group approval + mandatory comment.
- **Audit trails immutable and exportable** (CSV + PDF).
- **Each frontend deploy** must pass post-deploy 5-step (health probe → backend shell test → Chrome MCP browser smoke → re-test exact CFO request → close-out).

---

## Gates summary (block code on these)

| Ticket | Gate | Owner |
|---|---|---|
| CR-006 | Confirm 20% rate frozen | CFO 3x-confirm |
| CR-006 | Assign `AR_VERITAS` + `SALVAGE_INCOME` GL codes in Settings | Finance Manager |
| CR-007 | Assign `SUBRO_INCOME` GL code | Finance Manager |
| CR-004 | NBFIRA module disclosure link — stub TODO; build live link after Compliance module exists | Deferred |
