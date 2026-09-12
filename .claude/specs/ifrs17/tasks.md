# IFRS 17 module — tasks

Ordered. Each task states its own **done test** — "built" is not done.

## Phase 1 — the bridge (the live misquote risk)

- [ ] **T1.1** `ifrs17/bridge.py` — IFRS 17 ↔ MA reconciliation, both years.
      *Done when:* a test walks FY2025 IFRS 17 PBT **26,838,707 → MA PAT 0.292M** with every
      step named, and FY2026 PBT 12,864,243 → the FY26 MA PAT once the audit closes.
- [ ] **T1.2** Frozen-register guard — if a bridged figure disagrees with the frozen register,
      surface BOTH and name which is registered truth (pattern: `digital-cfo-avatar/tools.py`
      `detect_frozen_conflict`). *Done when:* a deliberately wrong figure produces both numbers,
      not a silent pick.

## Phase 2 — engine + parity (nothing is trustworthy until this passes)

- [ ] **T2.1** `ifrs17/models.py` + migration — `IFRS17Valuation`, `IFRS17ValuationFile`,
      `IFRS17SegmentResult`, `IFRS17TreatyResult`, `IFRS17DataQualityItem`, `IFRS17Assumption`.
      *Done when:* `makemigrations --check` clean and the **`--skip-checks` probe** agrees
      (the phantom-drift trap).
- [ ] **T2.2** `ifrs17/engine.py` — LRC, LIC, CHE, salvage, RA, IBNR chain ladder, revenue,
      ISE, attributable expenses, net reinsurance.
- [ ] **T2.3** 🔴 **Parity test (hard gate).** Assert the engine reproduces the report to the
      cent: revenue 133,416,295 · ISE 113,980,546 · result before RI 19,435,749 · net RI
      (6,571,505) · **PBT 12,864,243** · ICL 49,927,070 · RCA 35,443,271 · net 14,483,799 ·
      gross IBNR 21,155,286 · net IBNR 6,672,465 · combined 82%. Plus the FY2025 comparatives.
      *Done when:* the test fails if any lever's default is nudged.
- [ ] **T2.4** Seed FY2026 + FY2025 from the workings (`ingest.py`, server-side, aggregating —
      **never** a policy row out of the 35MB file). *Done when:* segment totals tie to Table 16
      and unearned premium ties to Table 42.
- [ ] **T2.5** `disclosures.py` — the paras 100–105 builders (A.1–A.4 + reserves + composition).
      *Done when:* each generated table equals the report's table.

## Phase 3 — the cockpit (what the CFO asked to drive)

- [ ] **T3.1** `frontend/src/lib/ifrs17Model.ts` — `Levers`, `BASE`, `SEGMENTS`, `TREATIES`,
      `compute()`. Header carries source, "AS-IS", and the known variances not to fix.
- [ ] **T3.2** 🔴 **TS↔Python parity test.** Same inputs → same outputs to the cent, both
      matching the report. *Done when:* changing one side alone goes red.
- [ ] **T3.3** `/ifrs17` page — lever rail, 8 segment toggles + Health off, 8 tabs, deltas vs
      base, negatives red, house palette + motion.
- [ ] **T3.4** JBB commission callout — 25% → 41% shows **+8,712,000**, labelled
      *"sensitivity — not recognised"*. *Done when:* rendered and READ at 1120 and 1280.
- [ ] **T3.5** Library tab — draft computes live with an "unapproved" badge; approved reads
      frozen figures. *Done when:* both states rendered and READ.

## Phase 4 — write path

- [ ] **T4.1** `api_views.py` + serializers; register on the router **and** add to
      `route_manifest_baseline.txt`. *Done when:* routes answer 200 for finance, 403 for
      operational staff (`Title.OPERATIONS`, not a default profile — the default title is
      `accountant`, which is finance).
- [ ] **T4.2** Approve/freeze — copies `PlanPack`: refuses to freeze empty figures, blocks
      edits once locked, and **approver ≠ preparer**. *Done when:* each refusal is tested.
- [ ] **T4.3** Data-quality register CRUD + the ten seeded rows.

## Phase 5 — out the door

- [ ] **T5.1** xlsx export — one sheet per disclosure table.
- [ ] **T5.2** docx disclosure notes, house template.
- [ ] **T5.3** `data_request.py` — the Empirica workbook, pre-filled, tied to the trial balance.
      *Done when:* a generated workbook opens in Excel with the same tabs and its totals tie.
- [ ] **T5.4** `/fabe`, then deploy (backend image **rebuilt** — migrations; frontend rebuilt
      `--no-cache`), then the eyes-on gate on the live page.

## Guardrails on every task

- Never touch GL mapping, MA format, or the dashboard GWP tile.
- No policy-level row on a screen, in an export, or to any external model.
- A sensitivity is labelled a sensitivity, never a bookable adjustment.
- Approved figures are read verbatim, never recomputed.
