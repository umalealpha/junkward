# Recipe — Graphite V2 commercial-policy premium capture (renewal / quarterly load)

**Goal:** load an underwriter's renewal/quarterly premium workbook (granular, per-location) into a Graphite V2 **commercial** policy (COMG/COMD), correctly and reversibly.

**When to use:** an underwriter sends a multi-sheet Excel (one sheet per risk location: Sum Insured / Rate / Annual / Quarterly per cover) and the policy must reflect those premiums. First seen: **Shaysons Investments t/a Builders Mart → policy `COMG2024129498`** (2026 quarterly renewal), 2026-06-25.

## How Graphite stores a commercial policy (learned the hard way — verify per policy)
- **Find the policy:** COMG policies have **`business_name = NULL`** — you cannot find them by insured name. Find by a renewal **attachment** filename (`policy_attachments`) or by `customer_id`. (Shaysons = id **129498**, customer **96339**.)
- The current renewal sits as an **`ANNIVERSARY-RENEW — QUOTE`** with its own **`term_id`/`action_id`**. **Target the LATEST action** (highest action_id) — a term carries several action-versions; for Shaysons the editable quote was **action 43815** (term 8447), NOT 3046/40728 which are older ISSUED versions. (The earlier draft of this recipe said 3046 — wrong; that's the original.) Editable at `/policies/{id}/edit`.
- **Premiums live in SEVERAL structures, not one table:**
  - `policy_coverages` (pc) — one row per (risk_address × coverage type); key = policy_id + term_id + action_id + risk_address_id + coverage_id.
  - `policy_coverage_detail` (pcd) — sub-coverage line: `coverage_value` = sum insured, **`calculated_value` = premium**; `coverage_id` → `tb_cvgpccoverages` (CoverageMaster) sub-coverage `s_ScreenName`.
  - **Only the coarse sub-coverages** are here (e.g. FIRE = "Plant and Machinery" + "Stock"). The underwriter's extra lines (leakage, goods-in-open, claims prep, debris…) are "items"/extensions stored **outside** pcd.
  - `policy_coverages_data` — **Fidelity Guarantee**. Separate tables/structures for **Commercial Motor**, **Goods-in-Transit**, **Public Liability**.
- `tb_cvgpccoverages` = CoverageMaster. Parent codes: FIRE, THEFT, MONEY, BUSINESSINTERUPTION *(sic, one R)*, ELECTRONICEQUIPMENT, FIDELITYGUARANTEE, ACCIDENTALDAMAGE, OFFICECONTENTS, WORKERSCOMPENSATION, COMMERCIALMOTOR, GOODSINTRANSIT, PUBLICLIABILITY.

## Why the native Excel import (the "upload tool") does NOT work for this
`backend/app/Imports/Sheets/CoverageImport.php`: multi-sheet (one per coverage type), columns **Risk Address · Coverage · Limit · Premium**; stores the premium **as-given** into `calculated_value` (no annual/quarterly maths). BUT:
- It writes **sub-coverages by name only** — the underwriter's granular lines don't map 1:1 (6 fire lines vs Graphite's 2).
- **It auto-creates any unrecognised sub-coverage name → duplicate coverages → inflated premium.**
- It ignores items / fidelity / motor / GIT / PL.
→ A converter feeding it loads a fraction and corrupts the rest. **Don't route an underwriter workbook through it.**

## The faithful approach: backend updater, match by SUM-INSURED
1. Parse the underwriter file: use the **"… 2026" sheets** (clean per-location layout: Cover · Sum Insured · Rate · **Annual (col D)** · **Quarterly (col E)**). Ignore the big messy detail sheets.
2. Pull the policy's existing premium records (all structures) for the quote's term/action.
3. **Match each Excel line to a policy record by (risk address + coverage type + sum-insured).** Names differ but sum-insureds tie out — verified: Tutume "fixed asset" 250k → "Plant and Machinery" 250k, same premium.
4. Set premium = the quarterly figure, across **every** structure (pcd `calculated_value`, policy_coverages_data, motor, …).
5. Produce a **complete before→after reconciliation** (every line: old → new; per-coverage + grand totals). **Read-only first — zero writes.**
6. **Commit only after CFO sign-off.** Direct write to live financials ⇒ prat-test gate: back up the affected rows first, reconcile to the agreed total, then commit; re-verify after.

## Traps (all real, from Shaysons)
- **Stray duplicate sheets** inflate totals: Shaysons had a `Ramokgwabana` sheet whose address still read **"Nkoyaphiri"** (a copy) — double-counting. Correct quarterly total = **P184,023.50** (ties to the SUMMARY tab), NOT the naïve all-sheets sum **186,903.11**. Always reconcile to the SUMMARY tab.
- **Excel locations ≠ policy risk addresses:** Shaysons had 29 Excel locations vs **28** on the policy (Ramokgwabana absent) → a new risk address must be added before its premium can load.
- **Premiums currently held are ANNUAL;** loading quarterly quarters them. Confirm the intended basis with the CFO (he confirmed quarterly for Shaysons).
- The locked underwriter file can't be opened while in Excel — **copy it first**, then read the copy (openpyxl).
- The `/policies/{id}/edit` wizard page is **too large for browser-automation** (accessibility tree > 200k tokens; screenshots blank when an editor opens) — drive this via the DB, not the UI.

## DB access
ECS exec into `graphite-backend` — see memory **`r-gph-v2-bulk`** (base64 PHP → `php artisan tinker`, split markers, base64 out). Read-only SELECTs for the reconciliation; writes only after sign-off.

**Status (2026-06-25): DONE + verified on prod — see the EXECUTED section below.** The "match by sum-insured" plan above was NOT what shipped (only ~28% matched); read the EXECUTED section for the method that actually worked and the quote-total landmine the underwriter caught.

---

## EXECUTED 2026-06-25 — what actually shipped, corrections & the quote-total landmine

**DONE + verified.** Loaded the 2026 quarterly into COMG2024129498 (action 43815); the V2 quote now totals **184,023.08**, every section reconciles, and it's durable.

**Corrections to the pre-execution notes above:**
- Target action = **43815** (latest), not 3046.
- Method actually used ≠ "match by sum-insured" (abandoned). What worked: a converter that **aggregates each location's items into the policy's EXISTING primary sub-coverage name** per coverage (so names resolve in `tb_cvgpccoverages`), motor per-vehicle, fidelity as one "Fidelity" line — then drives Graphite's own `EditPolicyImport` over ECS-exec tinker (clear → create vehicles/risk-addresses → import → self-validate total → commit). Full mechanism + the MyISAM-fidelity trap: memory **`r-gph-edit-pol`**.

**THE QUOTE-TOTAL LANDMINE — the P9,197 over-count the underwriter caught:**
- The V2 quote's **Total Premium is NOT the sum of the section detail.** It reads **`policy_actions.annual_premium`**, recomputed by `PolicyCreateController::recomputeActionTotals` over **SIX buckets**: non-motor `policy_coverage_detail.calculated_value` + motor (`calculated_value` + every `premium_*` col) + `policy_extention_detail` + **`policy_specified_items`** + fidelity (`policy_coverages_data`, Fidelity pc only) + motor_traders. (Motor isolation = coverage_id 22/27 — their detail is NOT summed, only the motor block.)
- **A clear-and-reload MUST sweep ALL six bucket tables.** Clearing only pcd/motor/fidelity leaves stale `policy_specified_items` + `policy_extention_detail` from the original build → recompute adds them on top → over-count. Shaysons: +7,295.08 + 1,902.36 = **9,197.44**; quote showed 193,220.52 vs correct 184,023.08.
- **Fix when a commercial quote total is inflated:** soft-delete the stale specified-items/extension rows under the action's pc, then invoke `recomputeActionTotals` (private static → Reflection). It recomputes to the clean figure, durable through any future Rate/issue. **Commercial = product_id 7 has NO rerate engine** (Rate/rerate is motor-comp product 3 only) — the six buckets ARE the rating; there is no "rate" to reduce or nudge.

**GUARDRAILS (do NOT repeat):**
1. **Never hardcode / force / "nudge" a premium total** to hit an expected number — find the data cause. (Shaysons was fixed by clearing strays + recompute, NOT by injecting 184,023.)
2. **Never edit rates in the underwriting closings workbook** to back-fit a total. The closings sheet is the source of truth.
3. **First suspect stale/soft-deleted `policy_specified_items` + `policy_extention_detail`** — the recurring cause of Fire/BI/Theft/Money/PL over-counts in V2 quotes. Filter soft-deleted; never add new.
4. **Reconcile section-by-section against the closings**, not just the headline total, before calling a quote correct.
5. **Verify the figure the USER sees** (the regenerated quote / `policy_actions.annual_premium`) — not just the stored section detail you wrote. (The underwriter saw 193,220.52 while my stored sections read 184,023.08 — I'd confirmed the wrong surface.)
