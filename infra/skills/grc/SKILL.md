---
name: grc
description: Gaborone Rifle Club (GRC) — Prathap's PERSONAL shooting-club treasury workflow + the grc-club app. Auto-load whenever Prathap types /grc, says "Gaborone Rifle Club" / "rifle club" / "raise a/an RQ" / "RQ Control Sheet" / "FNB upload file" / "payment upload" for the club, or the task touches: GRC requisitions (RQ###), the RQ Control Sheet.xlsx, FNB bulk-payment (BInSol) upload files, the grc-club app or its public demo, or GRC payees (PAAM, Laser Tech, John Smuts, Gift wages, Robbie Jordaan, David Eisen, Lenard Wong). Carries the RQ → sign-off → FNB workflow, the EXACT file formats, the payee bank register, the bank-detail guardrail, and the hard-won gotchas/mistakes so they are NEVER repeated. GRC is a PERSONAL project — NOT Alpha Direct (Alpha Direct governance/brand does not apply). Complements prat-skill (dev stack), prat-test (ship gate), and the p-grc-club memory.
---

# GRC — Gaborone Rifle Club treasury

## What it is
Gaborone Rifle Club: a Botswana shooting club Prathap **manages and is the Treasurer of**. Personal project (like Nako Pula / BCAT / Lumen) — **NOT Alpha Direct**; never list under Alpha Direct work; Alpha Direct AI-vendor/brand/DPA rules do not apply. **Prathap is authorised to correspond with GRC parties from his Alpha Direct company account (pganesharajah@alphadirect.co.bw) as a business/marketing activity in his treasurer capacity** — do not re-flag personal/corporate email "mixing" for GRC.

**People:** Authorisers/sign-off = **Lenard Wong** (lenard@lwa.co.bw, L W Architects, also auditor) **and John Smuts** (john@sennfoods.com, Senn Foods) — the RQ line reads "Payment Authorised: L. Wong / J Smuts", either can authorise. Preparer/loader = **P. Ganesharajah**. Common requesters = John Smuts, Lenard Wong, David Eisen (Biz-League). Sign-off `Regards, / Prathap Ganesharajah / Gaborone Rifle Club` (NOT "CFO, Alpha Direct" — this is the club).

## The grc-club APP (the "GRC system")
The web ERP that runs this workflow. Private repo **`Prathap-Alpha/grc-club`**; local `C:\Users\PrathapAsus\work\grc-club`. Public demo `Prathap-Alpha/grc-demo` → https://prathap-alpha.github.io/grc-demo (SAMPLE data only — never real banking/PII on the public demo; it is world-readable).

**Stack:** Next.js 15 (App Router, `params: Promise<>`), React 19, Tailwind v3, TypeScript strict, vitest. **No DB** — JSON file stores under `data/` (git-ignored) via `lib/fileStore.ts` (atomic temp+rename write; `readJson` seeds ONLY on ENOENT, throws on parse-error). `GRC_DATA_DIR` env overrides the data dir (test isolation). Key stores: `rqStore`, `supplierStore`, `memberStore`, `inventoryStore`, `eventStore`/`eventDay`, `approvals`, `ledger`; pure libs `bankGuardrail`, `fnbExport`, `bwBanks`, `coa`, `reports`.

**Run / build / test (never claim "done" without these — prat-test gate):**
- Dev server: `preview_start` name **"grc"** (from `.claude/launch.json`) → **localhost:3007**. The dev server goes **STALE on source edits → stop+start to pick up CODE changes**; DATA (JSON) changes are read live (`force-dynamic`). Screenshot tool times out this env → verify via DOM snapshot / `preview_eval` API calls / file checks.
- `cd C:\Users\PrathapAsus\work\grc-club; npm run build` (also typechecks) · `npm test` (vitest, 142+ tests). Both green before shipping.
- **Login:** `.env` (git-ignored) — `ADMIN_USERNAME="GRC Admin"`, `ADMIN_PASSWORD` (= his phone no., weak — recommend rotation), `AUTH_SECRET` (random, **REQUIRED, ≥16 chars, no fallback**), `GRC_FNB_PAYING_ACCOUNT`/`GRC_FNB_PROFILE` for in-app FNB export. Fresh-login **500** = the running server hasn't loaded `.env` → restart it.

**Modules (all built):** RQ Payments (`/rq`, `/rq/new`, `/rq/[ref]`: raise / amend / **delete** [pending or rejected only; authorised/paid are audit-locked] / authorise / reject / **mark-paid** / **approval magic-link** to Lenard / **FNB export**) · Suppliers + **bank guardrail** (`/suppliers`: NO_DETAILS→PENDING_CONFIRM→LOCKED, blind re-key, change-detection/anti-BEC, penny-test flag) · Members (P1,500/yr) · Inventory (ammo/clays) · Events + day reconciliation · Ledger/Journals/Reports (double-entry → JV/GL/P&L/BS/Cashflow, seeded from FY25). Auth = HMAC-signed session cookie (`lib/auth.ts`, Edge+Node) + `middleware.ts` gating all routes except `/login`, `/api/auth/login`, `/authorize/*`, `/api/approvals/*`.

**Security — hardened by a full audit (commit `301a28c`, "19 fixes"); don't weaken:** requireSecret (no default secret), session **expiry** + **constant-time** compare, **atomic** store writes, **CSPRNG** approval tokens, amend **revokes** stale approval links, FNB **penny-test + amount==Σlines** gates, CSV **formula-injection** strip (`sanitizeReference`), demo **XSS escaping**.

**Design system:** "High-Velocity Heritage" — navy #0D1B2A / clay #F4A623 / brass #C9A227 / cream #F5F1E6; Playfair Display / Space Grotesk / Geist Mono; glassmorphism; real GRC crest at `public/grc-logo.png`.

**Deploy:** app is **LOCAL only** (localhost:3007), not hosted. To give members real, gated access the authenticated app must be **deployed** (needs Prathap's Railway login — a hard gate) — the public Pages demo can't hold real data. I deploy/merge to his personal Git; he does not review code (deliver finished + prat-test'd).

## The payment workflow (what "raise a RQ" means)
Request arrives (Outlook .msg / email / invoice attached) → look up payee bank in the control sheet → **raise the RQ** = do ALL of:
1. **App** `grc-club` — add the RQ to `C:\Users\PrathapAsus\work\grc-club\data\rqs.json` (bump `counter`; status PENDING_AUTH; supplierId; bankInfo; lines whose amounts sum to `amount`).
2. **Control sheet** — fill the RQ row in `RQ Control Sheet.xlsx` sheet **'RQ Control 3'** (cols A-E: RQ Number | Supplier | Details | Amount | Bank Ac details). Rows RQ341..RQ421 are pre-numbered EMPTY slots — fill the next one.
3. **RQ PDF** — house-format sheet saved to `C:\Users\PrathapAsus\My Drive\GRC\2. RQ\2026\RQ### - <desc>.pdf`.
4. **FNB upload file** (for bank transfers) — BInSol CSV in `…\2. RQ\2026\FNB Upload Jun2026\`.
Then it goes to **Lenard / John to sign off**, and Prathap uploads + authorises at FNB. **I only ever prepare drafts — never move money, never auto-authorise.** Each RQ still needs sign-off (that IS the "proper authorisation" the external-email caution banners demand).

**Numbering:** next RQ = the 2026-folder max + 1 (authoritative), mirrored by `data/rqs.json` counter. As of Jul 2026 the batch reached **RQ347**.

## FNB BInSol upload file — EXACT format (get this wrong = 0 records or rejection)
Reference known-good file: `C:\Users\PrathapAsus\My Drive\GRC\2. RQ\GRC_Payment_Batch_RQ334-337_Apr2026.csv`. Template: `Downloads\Payment_CSV_Template_All.csv`.
- **EVERY line padded to 36 comma fields** (incl. the first 3), else FNB imports 0 records.
- L0 = `BInSol - U ver 1.00` + 35 commas
- L1 = **execution date `DD-MM-YYYY`** + 35 commas — **MUST be today or future** (once-off payment rejects a past date: "Execution Date Not Valid For Once Off Payment"). Stamp with the CURRENT date, not the RQ date.
- L2 = `<paying account>,<profile>` + 34 commas → GRC FNB account **62860939267**, profile **…9012** (lift both verbatim from the April file's L2).
- L3 = the 36 column headers (RECIPIENT NAME, RECIPIENT ACCOUNT, RECIPIENT ACCOUNT TYPE, BRANCHCODE, AMOUNT, OWN REFERENCE, RECIPIENT REFERENCE, EMAIL 1 NOTIFY, EMAIL 1 ADDRESS, EMAIL 1 SUBJECT, …).
- Data row cols: [0] recipient name (≤30, sanitised), [1] account (digits), [2] account-type `1`, [3] 6-digit branch code, [4] amount `0.00` (2dp), [5] OWN REFERENCE, [6] RECIPIENT REFERENCE, [7] `Y`, [8] `cfo@alphadirect.co.bw` (POP notify — CFO wants all POPs there; CONFIRMED accepted by FNB), [9] subject e.g. `GRC Payment RQ###`.
- **LF line endings**; UTF-8 no BOM.
- **REFERENCES (standing CFO rule, 2026-07-16): include RQ number + invoice number + the recipient's reference.** e.g. OWN REFERENCE = `RQ### IN######` (GRC statement), RECIPIENT REFERENCE = `IN###### RQ###` (payee statement); each ≤20 chars, sanitised. Older files used just the RQ number both sides — upgrade going forward.
- One file per payee, plus a combined multi-row file. Amount MUST equal the sum of the RQ line items.
- **eWallet payees (e.g. Gift wages) are NOT in the bulk file** — paid via FNB's eWallet send. RQ + sheet + PDF only, no CSV.

## RQ document (house format) — what a printed RQ looks like
White A4 sheet: real GRC crest top-left (`grc-club/public/grc-logo.png`, transparent, cropped from the RQ PDFs) + "Gaborone Rifle Club / Unit 2, Plot 144, Mountain View · P.O. Box 26374, Gaborone" · DATE · PAYABLE TO (payee, prominent) · RQ NUMBER · table [Date · RQ Number · Transaction Details · Amount (P)] · TOTAL · **BANK AC NUMBER / eWALLET** (bullet block) · Payment Loaded: P. Ganesharajah · Payment Authorised: L. Wong / J Smuts · GRC footer. Generate with `pymupdf` `fitz.Story` (HTML→PDF), logo via `fitz.Archive(public dir)`. The originals are Excel-template→Foxit PDFs; the template tabs are 'Actual RQ Manual' / 'Actual RQ Formula'.

## Bank register + the guardrail
- Bank details live in `RQ Control Sheet.xlsx` sheet **'Bank AC details'** and in the free-text "Bank Ac details" column of past 'RQ Control 3' rows (bullet-block format).
- **Bank-detail guardrail (hard rule):** use the **on-file / proven** account (from the register / past successful payments), NOT one freshly typed in an external email. Do a **3-way check** on every account before an FNB file: (T1) re-read/consistency across sources, (T2) cross-document corroboration, (T3) deterministic structure (all-digits, correct length per bank, valid 6-digit branch, not phone/VAT). **Recommend a P1 penny-test on a first/changed payment.**

### Confirmed payee banking (as used / verified)
- **PAAM** (Pan African Ammunition Manufacturers): **First Capital Bank, 0002704009398, Main Branch 800267, SWIFT FRCGBWGA.** (Absa ··9053 is an OLD account — do NOT use.)
- **Laser Tech** (Khan'z (Pty) Ltd t/a Laser Tech): **FNB, 63004129929, Industrial branch 281667.** (11 digits — see mistake #8.)
- **John Smuts**: **Standard Chartered, 0100180211500, Game City Branch, branch code 662867.**
- **Robbie Jordaan** (Robert Lee Jordaan): **FNB, 62454262785, First Place Branch 283767.**
- **David Eisen** (Biz-League): **FNB, 62018726044, Gaborone Industrial branch 281667.**
- **Gift wages** (range helper): **FNB eWallet ····4752** (8-digit; paid via eWallet, not bulk file). Amounts ~P1,000-1,650/mo.

## MISTAKES MADE HERE — do not repeat
1. **openpyxl SILENTLY DROPS the workbook's embedded images/drawings on save.** The RQ Control Sheet has 4 template images → NEVER `openpyxl.save` it. Edit it ONLY via **Excel COM from PowerShell** (`New-Object -ComObject Excel.Application`; pywin32 is NOT installed but PS COM works, Office 16). openpyxl `data_only=True` read is fine; saving is the killer. Always `Copy-Item` a backup first; verify `media/` entry count is unchanged after.
2. **PAAM/Softline invoice totals mis-read → underpaid by the VAT.** On these invoices the payable is the **Total (incl 14% VAT)**, NOT "Amount Excl Tax" / "Sub Total". The `pymupdf` text extraction JUMBLES the totals block order — do NOT map it positionally; verify the figure against the visual/screenshot. (RQ347: took Sub Total P10,877.20 as the total; real Total = P12,400.00 = 10,877.20 + 1,522.80 VAT.)
3. **Bank account eye-read off an invoice IMAGE dropped a digit.** Read Laser Tech as `6304129929` (10) off the photo; the proven account is `63004129929` (11). FNB rejected the 10-digit row. **The control-sheet/proven value BEATS an eye-read of an image; validate digit-length per bank (FNB BW = 11).**
4. **FNB "Execution Date Not Valid For Once Off Payment"** = L1 date was in the past. Stamp L1 with TODAY (or future) every time; re-bump if uploaded a later day.
5. **FNB imported 0 records** = the first 3 lines were not padded to 36 columns and the paying account was a `<<placeholder>>`. Pad all lines; use the real paying account 62860939267 + profile from the April file.
6. **Bullet mojibake in Excel cells** (`•`→`â€¢`): caused by `Get-Content -Raw` reading a UTF-8 temp file on PowerShell 5.1. Build special chars IN-script with `[char]0x2022` / `[char]10`, or read with `-Encoding utf8`. Don't round-trip UTF-8 through a temp file into COM.
7. **PowerShell `$var:` in a string** = "drive-qualified variable" parse error that aborts the whole script → use `-f` format or `${var}`.
8. **Never name a Python script `inspect.py`** (shadows the stdlib → numpy/openpyxl break). Windows console needs `sys.stdout.reconfigure(encoding='utf-8')` for `•`/`—`.
9. **PermissionError writing a file in the FNB Upload folder** = it's open in Excel / a preview / mid Google-Drive-sync. Ask Prathap to close it, then retry (can't overwrite a Windows-locked file, even via temp+rename).
10. **Claude-in-Chrome extension canNOT read Prathap's existing logged-in banking tab** (it works only in its own MCP tab group; a fresh nav to the FNB app errors — no deep-link). To read a live bank report: have him Download it and Read the file, or compare to a saved prior file.
11. **RQ341 special case:** Lenard corrected PAAM to a specific **P17,240** ("after discount" = the pre-VAT figure) — a deliberate authoriser override, not the invoice total P19,432.80. When an authoriser gives an explicit amount, apply it but flag the VAT reconciliation.

## Tools & locations
- Read .msg: `extract_msg`. Read xlsx: `openpyxl` (read only). PDFs: `pymupdf`/`fitz` (poppler NOT installed; `fitz.Story` renders HTML→PDF). Images: `Pillow`. Edit the master xlsx: Excel COM via PowerShell.
- App: `C:\Users\PrathapAsus\work\grc-club` (private repo Prathap-Alpha/grc-club). Public demo: `work\grc-demo` → prathap-alpha.github.io/grc-demo (SAMPLE data only — never real banking/PII).
- Source data: `C:\Users\PrathapAsus\My Drive\GRC` (Google Drive). Control sheet: `…\2. RQ\RQ Control Sheet.xlsx`. RQ PDFs: `…\2. RQ\2026\`. FNB files: `…\2. RQ\2026\FNB Upload Jun2026\`.
- Deeper running record: the `p-grc-club` memory note.

## Standing rules
- Prepare drafts only; sign-off (Lenard/John) + Prathap's FNB authorisation are the human gates — never bypassed.
- Mask full account numbers in chat (last 4); full numbers only go into the files/sheet (Prathap's own data).
- Keep this skill's payee register, "MISTAKES", and standing rules current as GRC work lands.
