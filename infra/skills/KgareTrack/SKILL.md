---
name: KgareTrack
description: >
  KgareTrack — the Government of Botswana Fleet Tracking, Management & Maintenance
  System (FTMMS) demo + tender bid. LIVE at kgaretrack.pages.dev. Auto-load whenever
  Prathap types /KgareTrack, says "KgareTrack", "Kgare fleet", "the fleet demo", "the
  government fleet tender", or the task touches: the FTMMS demo web app, the Botswana
  government fleet tender (MTI/POU/GFM/SER/07/2026-2027), the Kgare Digital bid pack, the
  financial model, the Stitch design, the pitch deck, or hosting on Cloudflare. Carries the
  project state, file locations, brand, data rules, governance and how to continue.
---

# KgareTrack — Government Fleet (FTMMS) demo + tender bid

**This is a SEPARATE venture, not Alpha Direct.** Alpha Direct governance, brand, and
frozen numbers do NOT apply here (like nako / grc / Tony). Keep the two worlds separate.

## What it is
A bid + demo for the **Government of Botswana** tender **MTI/POU/GFM/SER/07/2026-2027**:
a Fleet Tracking, Management & Maintenance System (FTMMS) for ~6,000 government vehicles
across ministries (MDAs), Ministry of Transport & Infrastructure — Government Fleet Mgmt.

- **Bidder (citizen lead):** Kgare Digital (Proprietary) Limited — UIN **BW00004788608**,
  incorporated 1 Mar 2023. Kgare handles the tender paperwork.
- **Software builder:** **Risk Software Africa** (Prathap's company) — the **disclosed**
  technical sub-contractor that builds the software + app.
- **Product name for the app:** **KgareTrack**.
- **Developer (7-Sep-2026):** **Unopa Male — umale@alphadirect.co.bw** is Prathap's software
  developer and now owns the build (see [[r-unopa-male-dev]]). Handover zip sent
  7-Sep 12:40: live app + a copy of repo `Prathap-Alpha/FTMMS-Blueprint` + `START-HERE.md`.
  Awaiting his GitHub username (company email account) before repo access can be granted, and
  awaiting Prathap's call on which Anthropic account he signs Claude Code in under.

## GOVERNANCE (important, do not cross)
Tender is **reserved for 100% citizen-owned firms** (Public Procurement Act s.76(2)). Lawful
structure = **Kgare as genuine lead + Risk Software Africa named as a DISCLOSED sub-contractor**
(the tender's staffing form allows sub-contractor personnel if identified). Must NOT: hide the
real builder, or present Risk Software Africa's track record / CVs as Kgare's own — that is
illegal "fronting". Kgare's Company Profile (Sec 1) and 5 references (Sec 2) must be Kgare's OWN
and truthful. **Never build/word anything that conceals the real performer, makes a false promise,
or hides a secret in client code.** (These lines held across the whole build.)

## Tender facts (from the OCR of the tender PDF — `Desktop\Projects\FTMMS Tender - full text (OCR).txt`)
- **Closes 10:00, Wed 9 Sep 2026.** Sealed, two-envelope, hand-delivered to GFM HQ, Varsha House, CBD, Gaborone, Office 0.5B. No email/late.
- **QCBS — Quality 70% / Cost 30%.** Min qualifying technical mark 70%. Lowest price gets the full 30%.
- **Shape:** 9–12 month build + **12-month support & maintenance** (SLA). Lump sum on 5 lines (Project Initiation, Architecture Blueprint, FTMMS Development, Integration, Deployment). **VAT 14% on top.** BWP.
- **Hosted at the Government DIT Data Centre** (NOT public cloud). **Source code owned by Govt.**
- 9 modules + integration (existing telematics = **Tata Fleet Edge**).
- Compliance docs from Kgare: PPRA reg (ICT Code 120: 01/02/06), BURS clearance, Form M beneficial owners (+bank letter, unchanged through delivery), Declaration T2.2GM, Cert. of Authority of Signatory, Form F Integrity, Form of Offer & Acceptance (T2.2GA).

## Financials (draft, in the model)
Bid ~**P7.38m excl VAT** (~P8.41m incl VAT) at 35% margin; cost ~**P5.47m**; profit ~P1.91m
(P1.49m after tax). Model has Assumptions, Cost Build-up, Price Schedule, **P&L**, **Cashflow
forecast**, dashboard. Two dials: margin, and Tata data fee.

## The demo app (KgareTrack) — LIVE
- **Live URL: https://kgaretrack.pages.dev** (Cloudflare Pages, project `kgaretrack`).
- **Files:** `C:\Users\PrathapAsus\work\ftmms-app\` = `index.html` (single-page, self-contained)
  + `coat.png` + **`kgare-logo.png`**. Desktop copy: `Desktop\ftmms-app\`. Zip: `Desktop\Projects\KgareTrack app.zip`.
- **Design = Apple-clean** (Prathap rejected the busy first Stitch look). Inter font, white/grey
  (`--bg #f5f5f7`), blue accent **`#1b6ec2`**, hairline dividers, calm cards, spacious tables,
  small status dots. **The real Kgare logo** (kgare-logo.png, cropped from their FB page) sits top-
  of-sidebar above "KgareTrack · Fleet Management". "Demo · sample data" badge always shown.
  Status colours: in-use green `#34c759`, idle amber `#ff9f0a`, maintenance blue, incident red `#ff3b30`.
- **Map = REAL Leaflet + OpenStreetMap tiles** (`https://{s}.tile.openstreetmap.org/...`), markers
  at real city lat/lng (Gaborone, Francistown, Maun…). NOTE: CartoDB "light_all" tiles now watermark
  "API KEY REQUIRED" — do NOT use them; OSM standard is free/no-key.
- **Screens (single-page, JS `render('x')` nav):** dashboard, map, vehicles, drivers, accidents,
  idle, maintenance, reports **+ fuel, alerts, triplog, disposal** (the value-add group)
  **+ repairs, parts** (the Workshop & parts group, added 7-Sep on Lawrence's request).
  Dashboard has a **Fleet Health 82/100** card and **8 clickable KPI cards** in 2 rows of 4
  (Due for service → maintenance, Idle → idle, Open incidents → accidents, Open repair orders
  → repairs, Parts below reorder → parts). Drivers has a **risk-score** column.
  Table rows open a detail pop-up. Top search is an **"ask in plain words"** bar (placeholder — the
  DeepSeek AI is NOT wired yet).
- **Workshop & parts (7-Sep):** `V.repairs` = 6 job cards RO-2411…RO-2395 with separate parts /
  labour / total columns; `rod(id)` pop-up shows the individual parts issued to the card (an
  `items` array per RO), and falls back to "closed and archived" for history-only RO numbers.
  `V.parts` has 3 tabs driven by `let ptab` + `pt(t)`: Parts & consumables (`PARTS`, re-order
  flags, stock value), Tyres (`TYRES`, life-used bar from kmNow-kmFit over expected life, one
  FLAGGED row → `tf()`), Batteries (`BATT`, warranty state, one FLAGGED row → `bf()`).
  `V.maintenance` gained an Action column (open RO link, else "Raise repair order") and a
  **maintenance history** table (`MHIST`). Reports gained 2 cards. The flagged tyre/battery rows
  are the selling point — they show the fraud a paper register hides.
- **Layout fixes made 7-Sep (keep them):** `.plate`/`.num`/`.pill` are `white-space:nowrap`,
  `tbl()` wraps every table in `overflow-x:auto`, `.grid>*{min-width:0}` so a wide table scrolls
  instead of pushing the page, `.cards3` goes 2-up under 1000px, `.kpis` base is 4 columns.
  Verified: all 14 screens, no horizontal overflow and no JS errors at 390 / 768 / 1024 / 1440 /
  1920 px (Playwright sweep).
- **SAMPLE DATA RULES (Prathap directive):** Botswana plates `B ### ABC`; **full Setswana names**
  (Kefilwe Mogorosi, Kabo Sebego, Kagiso Tshekedi, Tumelo Moloi, Masego Sechele, Goitseone Tau,
  Kealeboga Seretse…); **real Gaborone streets** (Nelson Mandela Drive, Khama Crescent, Julius
  Nyerere Drive, Independence Avenue, Western Bypass, Lobatse Road, A1 Highway/Mahalapye); **Pula**.
  Never real government/citizen data.
- **Run locally:** double-click `index.html`, or `cd work\ftmms-app && python -m http.server 8123`.

## Kgare Digital brand (CORRECTED 7-Sep-2026 — read this before touching any collateral)
🔴 **The bidder is Kgare Digital (Pty) Ltd, NOT Kgare Insurance Brokers (Pty) Ltd.** The whole
pack was built on the Insurance Brokers logo until Lawrence Keadibele corrected it on 7 Sep
("Kindly ensure that all branding, company references, and wording throughout the bid reflect
Kgare Digital"). There is **no tagline** — "Leave it to us" belongs to the brokers, never use it.
- **Logo:** `work\kgare-brand\kgare-digital-logo.png` (his `Production Logo.png`, whitespace
  trimmed, 1069x343, aspect **3.117**). Shipped as `kgare-logo.png` (~20 KB) in the app.
  The old 184 KB `kgare-logo.png` is the brokers' logo, parked at
  `work\kgare-brand\kgare-logo-INSURANCE-BROKERS-old.png` — never ship it.
- **Colours, measured off his logo:** maroon **`#941B1E`**, grey **`#818486`**, white.
  Dark-maroon accent **`#6B1417`** (was `#5F3636`).
- **Old values now WRONG:** `#8B2E2E`, `#5F3636`, `#8A8A8B`.
- **The proposal was in ALPHA DIRECT's brand** — navy `#0D1B2A` headings and orange `#F4A623`
  notes. Both replaced (navy→`#941B1E`, orange→`#818486`). Alpha Direct colours in a Kgare
  Digital tender are not just off-brand, they hint at who really built it, which is the
  fronting risk the whole governance section exists to avoid. Check for them in anything new.
- **Company name in copy:** always "Kgare Digital (Pty) Ltd" or "Kgare Digital", never bare "Kgare".

## Deliverables (all in `Desktop\Projects\`)
- `FTMMS Technical Proposal (DRAFT) 2026-09-07.docx` ← **CURRENT** (adds Section 5.7 Workshop,
  Parts Inventory & Consumable-Life Management). The 2026-09-06 file is the previous version.
- `FTMMS Compliance Checklist (DRAFT) …xlsx`
- `FTMMS Bid - Financial Model (DRAFT) … (updated).xlsx` (P&L + cashflow)
- `FTMMS - Google Stitch request (App + Website) …docx` (13 web + 8 app + 11 value-add screens)
- **`KgareTrack - Government of Botswana Presentation.pptx`** (**25 slides** since 7-Sep, Kgare
  maroon/grey, logo on cover + close, one slide per feature with its screenshot). ~2.1 MB.
  22-slide predecessor kept as `…Presentation (v1 pre-parts).pptx`.
- `Email - KgareTrack Kgare Digital rebrand + parts (DRAFT, open and send).eml` — NOT sent.
- Kgare Digital logo + his original email attachments: `work\kgare-brand\`.
- `KgareTrack - Manus deploy runbook.md` and `KgareTrack - Manus RE-DEPLOY runbook.md`
- Email drafts (`.eml`) + `FTMMS Tender - full text (OCR).txt`
- Stitch export source: `work\ftmms-stitch\…` (DESIGN.md "Sovereign Mobility").
- App screenshots for the deck: `worktmms-shots\*.jpg` (now 16 screens + 4 pop-up shots,
  captured via Playwright; `deckcheck\*.png` are PowerPoint-exported slide checks).

## Hosting + how to re-deploy
Cloudflare Pages, project **`kgaretrack`** → **kgaretrack.pages.dev**. **A browser tool CANNOT
finish the upload** — Cloudflare opens Windows' native file dialog, which no automation (mine,
Chrome, Obscura) can operate, and there is no `<input type=file>` in the DOM until the dialog opens.
**To re-deploy: hand `Desktop\Projects\KgareTrack - Manus RE-DEPLOY runbook.md` to Manus**, or drag
the `ftmms-app` folder into Cloudflare yourself. Demo/sample data only; production runs at the Govt
DIT Data Centre — never real data on Cloudflare.

## Tooling notes learned this build
- **Screenshots:** Playwright (chromium at `%LOCALAPPDATA%\ms-playwright`) opens `file:///…/index.html`,
  calls `render('screen')`, waits for tiles, `page.screenshot()`. This is how the deck shots were made.
- **Email:** send with `skills\prat-skill\tools\send_mail.py` (Graph, `--attach` works, Mail.Send OK).
  Creating an Outlook *draft* via Graph `/messages` returns **403** (needs Mail.ReadWrite). Outlook COM
  and some sends get **intermittently blocked by the auto-mode classifier** — retry, or hand a `.eml`.
- **OCR (no tesseract):** `rapidocr-onnxruntime` (pip, no admin) + PyMuPDF page render.

## Current state (7 Sep 2026, second pass) — KGARE DIGITAL REBRAND + English pass, NOT REDEPLOYED

**Done in the 7-Sep rebrand pass** (Lawrence's 09:30 email; Prathap had promised him
"done today by 11am, modified presentation and application sent for your review"):
- **App:** new logo shipped as `kgare-logo.png`, `alt="Kgare Digital"`, max-width 190px.
- **Deck:** logo on the cover (slide 1) and closing slide (25), sized by aspect not stretched;
  30 wording hits swapped ("Kgare · KgareTrack" → "Kgare Digital · KgareTrack" on every slide,
  "WHY KGARE" → "WHY KGARE DIGITAL", both "Leave it to us" lines and the "Leave the fleet to
  us" promise replaced); colours repainted; **all 15 app screenshots re-shot**, because the
  old ones had the brokers' logo inside the picture.
- **Proposal, checklist, financial model:** bare "Kgare" → "Kgare Digital"; the Kgare Digital
  logo added to the Technical Offer cover above the Submitted-by table; Alpha Direct's navy and
  orange replaced; "Prepared 6 September" → 7 September.
- **English pass (17 deck fixes + 2 app fixes):** "Six live numbers" → "Eight" (my own parts
  build had made it untrue), em dashes doing a comma's job removed per the humanize rule,
  "life-limited items" → "wear items" on the deck, several clumsy lines rewritten.
- Email redrafted as `Email - KgareTrack Kgare Digital rebrand + parts (DRAFT, open and send).eml`
  (2.0 MB, final deck attached, "Mr Lawrence" spelled correctly — his own thread says "Lawrance").
  The superseded parts-only draft was deleted. **Still send only AFTER the redeploy.**

### Two traps this pass taught — both cost real time
- **python-pptx leaves replaced images in the package.** Swapping the 15 screenshots twice took
  the deck from 2.1 MB to **6.7 MB** of dead image parts, and a 7 MB email. Fix:
  `scratchpad/purge_media.py` prunes rels whose rId no longer appears in the owning part, then
  drops unreferenced `ppt/media/*`. 6.68 MB → 1.51 MB. Run it after ANY picture swap.
- **PowerPoint COM served a STALE render of a file inside OneDrive.** Two exports in a row showed
  "Six live numbers" while python-pptx AND the raw slide XML said "Eight". **Copy the file out of
  OneDrive (e.g. to `work\`) and export from there**, and kill lingering POWERPNT/WINWORD first.
  Trusting that first render would have shipped a deck I had "verified" as wrong.

## Superseded state (7 Sep 2026, first pass) — parts + repair orders BUILT, NOT YET REDEPLOYED

**🔴 kgaretrack.pages.dev still serves the 6-Sep version.** The 7-Sep build (Workshop &
parts) is finished and verified locally but the Cloudflare upload cannot be automated (see
"Hosting" below) and there is no CLOUDFLARE_API_TOKEN on this machine, so `wrangler pages deploy`
is not an option either. Hand `Desktop\Projects\KgareTrack - Manus RE-DEPLOY runbook.md` to
Manus, or drag `Desktoptmms-app` into Cloudflare. `index.html` is now ~47 KB (the old one is
~31 KB — use that to tell them apart).

**Done 7 Sep, on Lawrence Keadibele's 7-Sep email suggestion** (Parts Inventory / Repair Order
module, covering tyre management and battery replacement records):
- App: Repair Orders + Parts & Inventory (Parts / Tyres / Batteries tabs), Maintenance upgraded
  with an Action column and a maintenance history, 2 new dashboard cards, 2 new report cards.
- Technical Proposal → `FTMMS Technical Proposal (DRAFT) 2026-09-07.docx`: Table 4 (required
  functional areas) and Table 6 (M-03, M-04 — M-04 renamed **Repairs, Workshop & Parts**)
  enriched; a 3.3 bullet on the **GFM Inventory Processes at Appendix C & D**; a whole new
  **Section 5.7 Workshop, Parts Inventory & Consumable-Life Management** (5.7.1 job cards,
  5.7.2 stores, 5.7.3 tyres/batteries/life-limited items, 5.7.4 reporting); an Appendix A item
  to obtain GFM's current parts catalogue during AS-IS.
  **Framed as depth INSIDE the nine modules, not a tenth module** — the ToR says nine, and the
  tender already asks for "repairs tracking", so this is not a scope or price change.
- Deck → now **25 slides**: slide 12 refreshed, new 13 Repair Orders / 14 Parts & Inventory /
  15 Tyres, batteries & life-limited items; slide 5 card and slide 21 value text updated.
  Backup of the 22-slide version: `…Presentation (v1 pre-parts).pptx`.
  **Deck trap:** every bullet paragraph has TWO runs — a maroon bold "•  " glyph and the dark
  grey (#2B2B2B) sentence. Collapsing them into one run turns the whole bullet bold maroon.
  Split the line across both runs.
- Reply drafted, NOT sent: `Desktop\Projects\Email - KgareTrack parts and repair orders added
  (DRAFT, open and send).eml` (same To/Cc as the 6-Sep mail, updated deck attached, and it asks
  Kgare for the outstanding compliance documents). **Send it only after the redeploy** — it
  points Lawrence at the Workshop & parts menu.
- PowerPoint COM works for checking a deck: open read-only, `Slides.Item(i).Export(png,"PNG",1600,900)`.
  LibreOffice is NOT installed on this machine.

## Previous state (6 Sep 2026) — COMPLETE & LIVE
Bid pack + model + Stitch request DONE. Demo app built from Stitch export, then **redesigned
Apple-clean**, given the **real Kgare logo**, a **real OSM Botswana map**, all **value-add feature
screens**, **clickable KPI cards**, and authentically-Botswana data. **DEPLOYED LIVE** at
kgaretrack.pages.dev (deployed + re-deployed via Manus). 22-slide **pitch deck** built. Email
**SENT** from pganesharajah@ to the tender group — **To:** Lawrence@kgaredigital.co.bw,
aiyer@ (Arun), mtlagae@ (Meduduetso); **Cc:** tiny@kgare.co.bw, thabo@kgare.co.bw, ceooffice@
(Modiri), arjuniyer@ (Arjun), Accounts@kgaredigital.co.bw (Onalethata), **umale@ (Unopa Male, new dev)**
— with the presentation attached and "open on a laptop for full features".

## SCOPE — whose job is what (Prathap, 7-Sep-2026)
**"my job is only building software, let them handle the other things."**
- **Ours (Risk Software Africa):** the app, the demo, the technical write-up, architecture, screenshots,
  the deck, and the price for the work.
- **Kgare Digital's, and never put on Prathap's list:** PPRA, BURS, Form M + bank letter, the sworn
  forms, company profile, their own five references, CVs and certificates, printing, sealing and hand
  delivery. Report as context if asked, then stop. Never tell him to chase Lawrence.

## Open items
- **DeepSeek "ask in plain words" AI is still a placeholder** — build only if asked. Key stays
  server-side, never in the client, and no tender data goes to DeepSeek.
- Optional: the remaining mobile screens, and wiring live Tata Fleet Edge data.
- **CLOSED 7-Sep:** the rebranded build is LIVE on kgaretrack.pages.dev (Manus uploaded, verified
  independently in a browser). All three emails sent to Lawrence and the group by 10:34. The
  commercial agreement with Kgare Digital is Prathap's own — do not offer to draft it again.
- **Kgare to supply:** PPRA reg, BURS clearance, Form M beneficial owners (+bank letter), **5 of
  Kgare's OWN project references**, and **team CVs** (mark Risk Software Africa staff as disclosed
  sub-contractors). These finish the Technical Offer (Sections 1, 2, 6) before the tender submission.
- **DeepSeek "ask in plain words" AI is a placeholder, not wired.** Build only if asked: key stays
  server-side (never client), no sensitive/tender data to DeepSeek. See [[p-kgaret-open]].
- Optional: build the remaining/mobile screens and wire live Tata Fleet Edge data.
