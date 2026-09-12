# IFRS 17 module — requirements

**Requested:** CFO, 25-Aug-2026 — *"design the IFRS17 module, ensure we copy the budget
module where we can move figures easily so it changes things and create financial statement
disclosures also."*

**Source of truth:** `~/Desktop/IFRS 17 workings/` (30 files, fetched 25-Aug-2026). The
method statement is `FY26/Alpha Direct IFRS17 Report 2026.pdf` — Empirica Actuaries, 24pp,
valuation date 30 June 2026. **The workbook and that report ARE the spec. Nothing here is
derived from first principles** (standing rule: port the handed file, do not rebuild the
method).

---

## R1 — Move a figure, everything moves (the headline requirement)

Copy the **5-Year Plan Cockpit / Budget Cockpit** pattern exactly, because it already does
what the CFO is asking for and Finance already knows how to drive it:

- A deterministic engine in `frontend/src/lib/ifrs17Model.ts` holding `BASE` levers and one
  `compute(levers, segmentsOn)` function. **The page owns no arithmetic** — same rule as
  `fiveYearModel.ts` and `budgetModel.ts`.
- **Sliders** for every actuarial assumption. Drag one and every KPI, statement line,
  reserve table and disclosure note recomputes instantly.
- **Segment ON/OFF toggles** for the eight reporting segments — built from per-segment
  figures so a switch genuinely removes a segment from every table, not just the total.
  (`fiveYearModel.ts` records why: a group-totals draft cockpit could not really recompute.)
- Deltas always shown against base, so the effect of a change is visible, not inferred.

**Levers, with the real values from the report — these are not invented:**

| Lever | Base (FY2026) | Range | Why it earns a slider |
|---|---|---|---|
| Risk adjustment % of fulfilment cash flows | **6.0%** | 3–12% | Calibrated to the 75th percentile. Drives LIC RA 1,878,006 and ceded RA 1,395,882. |
| Confidence level | **75th** | 60–95th | Stated risk appetite. Shown alongside the RA %. |
| Claims-handling expense factor | **2.4779704082%** | 0–6% | Applied to (gross IBNR + ½ case reserves). **Carried forward unchanged from FY25 because no approved FY26 allocation was provided** — so it is the assumption most likely to move. |
| Salvage & subrogation recovery % | **6.2015%** | 0–15% | Management estimate set from FY25 actual recoveries. Deduction of 2,025,344. |
| Attributable expense share of opex | **92.9%** | 60–100% | Was 80.5% in FY25. The report is explicit that the **apportionment change, not cost escalation**, drives the 22.7% expense rise — 3,891,418 of the 5,398,775. |
| IBNR yr6→7 tail factor | **1.003100** | 1.000000–1.010000 | FY25 used a nil tail (exactly 1.000000). The change alone is worth **896,862** of gross IBNR. |
| Discounting | **OFF** | on/off | Paras 56 / 59(b) expedients. A toggle so the materiality of the election can be shown, not asserted. |
| **JBB Motor QS commission rate** | **25.0% provisional** | 24–41% | 🔴 The sliding scale settles on final underwriting-year loss ratio. At 41% on ceded premium of 54,450,560 this is **+8,712,000 of commission**, which the report states has **not been recognised**. This slider is the single most valuable number on the screen. |
| Onerousness test | OFF | on/off | Engineering 295% and Guarantee 144% gross loss ratios carry **no loss component**, justified on materiality (0.8% of book). Empirica recommends a formal test before FY2027. |
| Health as a modelled segment | OFF | on/off | Health is currently **not** one of the eight segments and is not modelled. It loses 108,337 and carries 70,353 of ceded premium nobody has modelled. Empirica recommends separate modelling + a Health treaty slip before FY2027. |

## R2 — Draft computes live, approved freezes

Mirror `PlanPack` exactly, for the same reason it exists there: an approved figure must be
quotable to a board — here, to auditors.

- `base_figures` stays **empty** while a valuation is a draft; the screen then shows figures
  computed live from `ifrs17Model.ts`, so **a draft can never quote a number the cockpit
  disagrees with**.
- **Approving freezes** the figures into `base_figures`. From then on they are read verbatim
  and never recomputed. `figures_locked` blocks further edits.
- Approval requires the figures being approved to be sent with the request (same guard as
  `PlanPack`: refuse to freeze an empty snapshot).

## R3 — Financial statement disclosures, generated

Every table in the report's Appendix A (IFRS 17 paras 100–105), plus the statements:

1. **Statement of comprehensive income** — insurance revenue, insurance service expenses,
   result before reinsurance, allocation of reinsurance premiums, amounts recoverable, net
   income/expense from reinsurance held, insurance service result, PBT.
2. **Statement of financial position** — insurance contract liabilities/assets, reinsurance
   contract assets/liabilities, net position.
3. **A.1 Movement in insurance contract liabilities by component** — LRC excl. LC · LRC LC ·
   LIC estimates · LIC RA, opening → insurance revenue → incurred claims → amortisation of
   acquisition cash flows → changes to LIC past service → cash flows → closing.
4. **A.2 Movement in reinsurance contract assets by component** — ARC · ARC LRC · ARIC
   estimates · ARIC RA, including the disclosed **149,104 opening overlay difference**.
5. **A.3 Analysis of insurance revenue** — premiums received, movement in LRC, split into
   expected claims, recovery of acquisition cash flows, risk-adjustment release + margin.
6. **A.4 Analysis of amounts recoverable from reinsurers** — direct recoveries received vs
   the non-cash contribution from the movement in ceded reserves.
7. **Reserves analysis** — gross by type, IBNR by underwriting year, gross/ceded/net.
8. **Composition of contract balances** and **movement opening→closing**.
9. **Reinsurance programme** — treaty terms, ceded premium/commission/recoveries by treaty,
   net premium cost, direct economics, ceded unearned premium by treaty, reinsurer panel with
   ratings and default probabilities.
10. **Segment table** — premium, commission, claims, loss ratio, combined ratio.

Each table must render on screen AND export (xlsx + a Word/PDF disclosure note), because the
auditors receive documents, not screens.

## R4 — The IFRS 17 ↔ Management Accounts bridge (non-negotiable)

The report's FY2025 GWP is **125,148,692**, which ties to the frozen 125.15M exactly. But its
FY2025 profit before tax is **26,838,707** while the frozen MA FY25 **PAT is 0.292M**.

Both are correct — IFRS 17 excludes non-attributable overheads, investment income, other
income and tax, and takes the ceded reserve movement as income. **A permanent, visible bridge
between the two is the module's first deliverable**, before any disclosure table, because the
first time somebody quotes one figure in the other's meeting it is a production incident.

## R5 — Produce the actuary's data request automatically

`FY26/Alpha Direct - IFRS17 Data Request FY2026.xlsx` is the input contract Empirica sends
every year and Finance fills **by hand**. Tabs: `Instructions` · `1. Premium & UPR` ·
`2. Claims & OCR` · `3. IBNR CHER & Recon` · `3b. Claims Extract (IBNR)` · `4. Reinsurance` ·
`5. Expenses` · `6. Checklist`. Omni already holds the source for nearly all of it. The module
generates the workbook, pre-filled, tied to the trial balance.

## R6 — Hold the actuary's outputs; do not replace the actuary

The selected IBNR, the risk-adjustment calibration and the development factors are a **signed
actuarial opinion**. The module stores them as versioned, dated, signed-off inputs with the
report attached — it does not recompute them and then disagree with Empirica. The engine's
levers exist to show **sensitivity**, and every sensitivity is labelled as such, never as a
bookable adjustment. (The report is explicit about this on the JBB commission.)

## R7 — Data quality register

Ten items in the report need a permanent, tracked home rather than a paragraph nobody re-reads:

| # | Item | Amount |
|---|---|---|
| 1 | JBB commission at provisional 25% vs 24–41% sliding scale, unrecognised | **8,712,000** |
| 2 | Reinsurer panel only **70%** of shares confirmed (FY25: 90%); Continental Re B+, 2.44% PD; no ECL computed | ~60,000 est. |
| 3 | Health not modelled; no Health treaty slip supplied | 70,353 ceded |
| 4 | Engineering 295% / Guarantee 144% loss ratios, no loss component carried | 1,076,575 premium |
| 5 | Ceded case reserves / IBNR / RA are **aggregate only** — treaty split is a model allocation, not a fact | 23,264,702 |
| 6 | FY25 opening unearned-premium difference **not posted** | 505,382 |
| 7 | Opening overlay difference, unsupported prior-year XL/CAT row | 149,104 |
| 8 | Profit commission accrued; settlement date "plausible, not contractually evidenced"; JBB attribution a technical proxy | 1,427,557 |
| 9 | Trial balance GWP 133,437,785 vs IFRS 17 revenue 133,416,295 | 21,490 |
| 10 | Case reserves unmappable to an origin year — kept in the liability, excluded from the chain-ladder deduction | 401,561 |

Each row: owner, status, target date, and the note that goes to the auditors.

---

## Non-functional / guardrails

- **NF1 — Frozen wall.** The module **reads** the ledger and produces its own statements. It
  does **not** touch GL mapping, the MA format, or the dashboard GWP tile. Any change there
  needs three explicit yeses.
- **NF2 — Access.** Read = finance/management (`CanViewFinancials`). Write = Finance only.
  Approve/freeze = CFO or Financial Controller, and **the approver may not be the preparer**
  (same maker-checker shape as the rest of Omni).
- **NF3 — PII.** `UPR_Policylevelpremium JUNE 26.xlsx` is 35MB of **policy-level** data.
  Ingest it server-side, aggregate on the way in, and never surface a policy row on a screen,
  in an export or to any external model (AD-POL-AI-GOV-001).
- **NF4 — Every figure traceable.** Each number carries its source (workbook cell, GL account,
  or "management judgement") — the report does this and the auditors will ask.
- **NF5 — Prior year.** FY2025 comparatives come from the FY25 model on the same PAA basis, so
  both dates are measured consistently. `FY25 prior/` holds that pack.
