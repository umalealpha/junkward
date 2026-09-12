---
name: nako
description: Use when Prathap types /nako or says "Nako" / "Nako Pula" / "continue Nako Pula", or works on the Nako Pula app — his PERSONAL Nako Tech SME accounting + patient-management PWA at nakotech.africa (repo Prathap-Alpha/Nako-Tech). Covers its bugfixes, Supabase migrations, ledger/VAT/payroll/depreciation postings, RLS/security, the Playwright e2e suite, deploys, and the ERP roadmap. This is Nako Tech (personal) — NOT Alpha Direct; Alpha Direct governance/brand does not apply and Gemini is allowed here.
---

# Nako Pula

Mobile-first accounting + patient-management PWA for Botswana SMEs (doctors, dentists, pharmacists, clubs, hospitality). Owner: **Nako Tech Pty Ltd — Prathap's personal business, NOT Alpha Direct.** Live public beta at **https://nakotech.africa**. Full running log lives in memory `p-nako-pula.md` — read it for history; this skill is the operating brief.

## Where things are
| | |
|---|---|
| Repo | `github.com/Prathap-Alpha/Nako-Tech` (PRIVATE, on GitHub Pro so Pages still serves) |
| Local clone | `C:\Users\PrathapAsus\nako-pula` (pnpm monorepo; app in `apps/web`) |
| Stack | React 18 + Vite + TS PWA; **Supabase** (Postgres + RLS, Auth, Storage, Edge Functions/Deno); Google Gemini (OCR/AI); hosted on GitHub Pages |
| Supabase project | `xvqnuycevvirmehzbtyj.supabase.co` |
| Client mode | real Supabase when `VITE_SUPABASE_URL`/`ANON_KEY` set, else a localStorage **mock** (`apps/web/src/lib/supabase.ts`) |

## App routes (`/app...`)
`/app` dashboard · `/app/customers` · `/app/suppliers` · `/app/invoices` · `/app/inventory` · `/app/journal` · `/app/payroll` · `/app/reminders` · `/app/reports` · **`/app/assets`** (fixed assets — not in every nav) · `/app/receipts` · `/app/patients` · `/app/burs` · `/app/settings`

## Deploy / CI
- **Migrations** (`supabase/migrations/*.sql`): auto-apply to prod via `.github/workflows/apply-migrations.yml` on push to `main` — GATED on the `SUPABASE_ACCESS_TOKEN` repo secret.
- **Frontend**: `deploy-pages.yml` → GitHub Pages on push to main.
- **Edge functions deploy MANUALLY** (`supabase functions deploy <name>`) — NOT in CI.
- **"Done" = merged + CI applied + verified on the live site**, never just "build green."
- Git hygiene: feature branch → PR → merge; **never push to `main` directly**. To avoid stale-base diffs, branch off fresh remote main: `git fetch; git checkout -B <br> origin/main; git cherry-pick <commit>`.

## Accounting conventions (get these right)
- GL codes: `1000` Cash · `1200` Inventory · `1500` Fixed Assets at cost · `1510` Accumulated Depreciation · `2100` VAT Output · `2110` VAT Input · `2200` PAYE · `4000` Sales · `5000` COGS · `5100` Salaries · `5900` Depreciation · `6000` Other Expenses.
- Every posting must be **balanced** (sum debits = sum credits); `journal_lines` has a Dr-XOR-Cr CHECK.
- **Date entries `today`, never month-end** — the dashboard "this month" window is month-start → NOW, so a future-dated same-month entry is silently excluded (that was "Bug B").
- Make postings **idempotent** (skip if an entry already exists for that `source`+`source_id`/reference).
- RLS: owner-scoped via `businesses.owner_id` / `user_owns_business()`; admins get **SELECT-only**, never write-bypass (especially patient PHI). Migrations idempotent: `IF NOT EXISTS` / `DROP POLICY IF EXISTS` / `ON CONFLICT DO NOTHING`.

## How to verify (prat-test)
`pnpm -C <repo> -r build` (tsc + vite) → migration parse (`python -m sqlfluff parse --dialect postgres`) → **LIVE UI check**: drive nakotech.africa, do the action, then read the **Journal** and **Reports** (Trial Balance must show "Balanced ✓"). Ops notes: the in-app browser's screenshots intermittently time out and ref-clicks sometimes miss — prefer **coordinate clicks** and **`get_page_text`** as the reliable evidence tool; zoom drifts (`ctrl+0` resets).

## Shipped (PRs #16–#23, all merged + verified live)
Missing tables (employees, customers, suppliers, fixed_assets); receipts Storage bucket (now private + signed URLs); security NP-01..06 + PHI admin write-bypass fix; 6 functional fixes (invoice mark-paid→ledger + backfill, inventory explicit-GL + VAT split, block ≤0 journals, edge-fn JWT verify, Balance-Sheet out-of-balance banner, payroll duplicate-post guard); payroll date-window (Bug B); **fixed-asset depreciation posting** (Dr 5900 / Cr 1510). Playwright e2e scaffold + a daily workflow that runs against the mock (safe).

## ERP roadmap — do in VERIFIED increments (never a fake "best ERP done")
1. Inventory item **cost/price capture** on the Add-item form → COGS auto-posts on new items.
2. Fixed-asset **disposal / sale** postings (remove cost + accum dep, book gain/loss).
3. **One-click VAT / PAYE settlement** (Dr liability / Cr cash) instead of a manual journal.
4. **NP-07 / NP-08** — signup account-enumeration + auth rate-limiting.
5. e2e **selector calibration** + a dedicated test tenant, then trust the daily loop.

## Guardrails (do not cross)
- **Never fabricate** certificates, "cleared / passed / tested" claims, or test results to Tlotlo, clients, or the public. Report only what's genuinely verified. Real DPA compliance = the Botswana **IDPC**; a real pen-test cert = an **accredited firm**; an AI/internal assessment is neither.
- **Never handle secrets** (`SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`) — rotation is Prathap's job in the Supabase dashboard.
- Test only with synthetic data on a throwaway tenant; never pollute the public demo (tag test rows `AUTOTEST-*`); demo password is the public string `admin` (rotate before real data).

## People
Channel partner: **BIYU AI Agency — Tlotlo Johane** (`tlotlojohane94@gmail.com`), 35% lifetime referral deal. Reply to his bug reports as Prathap via `prat-skill/tools/send_mail.py` (from `pganesharajah@`).
