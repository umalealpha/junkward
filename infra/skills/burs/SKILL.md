---
name: burs
description: >
  Alpha Direct / Beyond Growth BURS bid — the "Lekgetho AI — Smart Revenue Suite"
  concept app AND the live BURS domestic-tax digitalisation procurement (EOI).
  Auto-load whenever Prathap types /burs, or mentions BURS, the Botswana Unified
  Revenue Service, the tax digitalisation / reform / modernisation tender or EOI
  (ref BURS/EOI/OPS/SER/12/2026-2027), Lekgetho AI, the lekgetho-ai-concept repo
  or prathap-alpha.github.io/lekgetho-ai-concept demo, the Smart Audit / Smart
  Capture / e-invoicing / Transaction Monitoring modules, the ITW8/ITW7A/ITW10/VAT002
  forms, Beyond Growth Consultancy / Onneile Maripe, or the Manus presentation
  package. Carries what's built and where (paths, repo, live URL), the teal brand
  spec, the EOI requirements + gap analysis, the consortium strategy, contacts and
  governance rules — so context is never rebuilt from scratch. Keep the CURRENT
  STATE and OPEN ITEMS sections updated as BURS work lands. Fuller record lives in
  `Gods Eye\BURS.md`.
---

# BURS — Lekgetho AI / Domestic Tax Digitalisation Bid

Quick-start context so a fresh chat continues exactly where the last BURS session
left off. **Full record:** `C:\Users\PrathapAsus\OneDrive - Alpha Direct Insurance\Gods Eye\BURS.md`.

## What this is (TL;DR)
- A working, clickable **concept app** demonstrating an AI-assisted domestic-tax
  platform for **BURS** (Botswana's national tax authority).
- BURS then published a **real EOI** for exactly this → the concept became a live bid.
- The app maps to the EOI's **Phase 1 (e-invoicing + transaction monitoring)** and
  **Phase 2 (enterprise tax management platform)** — 12 modules.
- **Branded to Beyond Growth Consultancy** (partner / implementing company; NDA
  signed 18 Jun 2026). Client/presentation contact: **Onneile Maripe, CEO**.
- A **Manus package + ZIP** exist for building the presentation.

## NON-NEGOTIABLE WORKING RULES
1. **Never publish internal material to the PUBLIC repo.** Partner PII, bid strategy,
   `manus-package/`, `*.zip`, `_source_paper.txt`, `BURS.md` all stay out of
   `lekgetho-ai-concept` (they are gitignored / kept in Gods Eye root). The repo +
   GitHub Pages are world-readable.
2. **All demo data is SYNTHETIC.** No live taxpayer PII, ever (AD-POL-AI-GOV-001).
   Production extraction engine = an approved vision AI (Claude), never Google.
3. **The app is necessary but NOT sufficient for the EOI.** The honest truth stands:
   MR1 "≥2 national-tax-admin implementations" + MR2 "≥2 revenue-authority reference
   letters" are pass/fail and unmet alone → **bid as a CONSORTIUM**. Never imply we
   qualify solo.
4. **BURS logo/branding** used only with authorisation; keep the concept disclaimer.
5. **Parallel writers on this repo** — another agent has pushed here. Always
   `git fetch` + inspect + `git pull --rebase` before pushing; integrate, never
   force-push over unseen work.
6. **Verify before "done"** (prat-test + delivery-discipline): check the LIVE URL /
   computed styles, not a stale copy. Screenshot tool is flaky — use live-DOM checks.
7. **The NDA is confidential** — never send it to Manus or any external service.

## Where everything lives
| Thing | Location |
|---|---|
| Live demo | https://prathap-alpha.github.io/lekgetho-ai-concept/ |
| GitHub repo (PUBLIC) | https://github.com/Prathap-Alpha/lekgetho-ai-concept (acct `Prathap-Alpha`) |
| App (single file) | `Gods Eye\BURS-Concept\index.html` |
| Local preview | launch cfg `burs-static` → `http://localhost:8090/BURS-Concept/index.html` |
| Manus package | `Gods Eye\BURS-Concept\manus-package\` (gitignored) |
| Manus ZIP (give to Manus) | `Gods Eye\BURS-Manus-Package.zip` |
| BURS source questionnaire | `Gods Eye\BURS-Concept\_source_paper.txt` (gitignored) |
| Full project record | `Gods Eye\BURS.md` (gitignored / private) |

**Deploy = push to `main`** → GitHub Pages rebuilds ~1 min (same URL). Single
self-contained HTML; vanilla JS + Three.js r128 (lazy from cdnjs). One `<script>`
block → a syntax error kills everything; locate with `node --check`.

## The app (12 modules)
Overview · **e-Invoicing (CTC)** · **Transaction Monitoring** · **Smart Audit** ⭐ ·
**Smart Capture** ⭐ · Taxpayer 360 · Taxpayer Service (bilingual EN/Setswana) ·
Back-Office (AI audit selection) · Customs & Excise · Analytics & BI · Integrations ·
EOI Coverage (maps app → EOI Phase 1/2).
- **Smart Audit:** auto-fills BURS's VAT Compliance Verification questionnaire from
  connected data (CIPA, Lekgetho Live, banking, customs); flags declared-vs-actual
  inconsistencies; risk verdict + auto doc-request list; ~90 min → 5 min.
- **Smart Capture:** photograph receipt/Omang/payslip → on-device OCR (tesseract.js)
  → auto-fills official **ITW8, ITW7A, ITW10, VAT 002**; "one photo, four forms".
- Look-and-feel: Omni "heavenly" glass + holographic KPIs + 3D hero globe
  (customs-flow arcs, spinning Pula coin) + ambient wireframe field + card tilt.

## Brand spec (BURS teal→blue, per EOI letterhead)
teal `#0E9CB0` · header teal `#0E8294` · deep blue `#103A66` · mid blue `#134A78` ·
cyan `#16C2D6` · light bg `#E8F6F8` · Botswana flag stripe (lt-blue `#75AADB`/white/black).
App currently brands as **Beyond Growth Consultancy** (implementing company). Get
BURS's official brand guide for exact hex if possible.

## The EOI
- **Ref:** `BURS/EOI/OPS/SER/12/2026-2027` — *Procurement of Domestic Tax
  Digitalisation Reform and Modernisation Solution*.
- **Closing:** 12:00, **3 July 2026** · **queries** to `procurement@burs.org.bw`
  ≥7 days before (~26 June) · **physical** submission (1 original + 2 copies), Tender
  Box, BURS Head Office, Plot 54379 CBD Gaborone · state Phase 1 / Phase 2 / Both.
- **Gap:** app covers MR1 solution+innovation ✅; missing/weak = commercial model,
  methodology, **national-tax-admin implementations (MR1)** ❌, **reference letters
  (MR2)** ❌, company profile depth. MR4 incorporation / MR5 3-yr audited financials /
  MR6 tax clearance = obtainable ✅. → consortium, lead **Phase 1**.

## Partners & contacts
- **Beyond Growth Consultancy** (partner, NDA signed) — accounting/advisory firm,
  Gaborone. Services: ESG & Sustainability, Financial Accounting & Reporting, Internal
  Audit & Controls (SOX/ICFR).
- **Onneile Maripe** — BFP, FCA — **CEO** — presentation/client contact —
  `omaripe@beyondgrowth.co.bw` (full details incl. cell in `BURS.md`). CC:
  `rkamuvete@beyondgrowth.co.bw`.
- A specialist e-invoicing/CTC vendor with live national references is still needed
  for MR1/MR2 (Beyond Growth alone doesn't close that gate).

## Governance flags
Conflict of interest (Alpha Direct is itself a BURS taxpayer — framed as a strength) ·
no live PII · logo with authorisation · synthetic data · public-repo hygiene.

## CURRENT STATE (update as work lands) — 2026-06-20
- App: 12 modules live, teal/Beyond-Growth brand, 3D artifacts, prat-tested.
- Manus package + `BURS-Manus-Package.zip` built and ready to hand over.
- `BURS.md` full record saved to Gods Eye root.

## OPEN ITEMS
- [ ] Bid / no-bid decision (CFO).
- [ ] Consortium partner with national-tax-admin references (Kenya/Rwanda/LatAm-class).
- [ ] Written technical proposal (exec summary, solution, approach, methodology/roadmap,
      commercial/funding model, innovation, skills transfer/localisation).
- [ ] Company docs: incorporation, 3-yr audited financials, tax clearance.
- [ ] Optional clarification-query email to BURS by ~26 June.
- [ ] Hand ZIP to Manus for the presentation.
- [ ] If bidding: physical submission before 3 July 12:00.
