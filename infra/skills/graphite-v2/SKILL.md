---
name: graphite-v2
description: >
  Quick-start context for Alpha Direct's Graphite V2 policy-admin ERP
  (graphite-v2-prod-fe.alphadirect.co.bw). Auto-load whenever Prathap types
  "/graphite-v2", says "work on Graphite" / "Graphite V2" / "GraphiteV2", or the
  task touches Graphite V2: policies (COMG…), claims, ledgers/premium, KYC,
  premium loads, endorsements / schedule PDFs, PII masking, or a Graphite data
  pull. Loads how to reach + safely change the data (ECS-exec into the backend),
  the schema landmines, current state and open items — so a fresh chat continues
  where the last Graphite session left off. Supersedes graphite-navigation (that
  is the OLD email+password V1, browser-only). Complements prat-skill (full dev
  stack), prat-test (ship gate), and omni (its /aware runs over this data).
  Keep "current state" and "open items" updated as Graphite work lands.
---

# Graphite V2 — Alpha Direct policy-admin quick-start

**Talk to Prathap (CFO) in plain English. Do the whole ask in one run — don't stop to ask "can I proceed" except for the hard lines: moving money / billing a live policy, changing someone's access, or deleting live data.** Full dev conventions live in **prat-skill**; the ship gate is **prat-test**. This skill is the Graphite-V2 starting context.

## On load — pull the shared notes first (automatic, never wait to be asked)
The moment /graphite-v2 loads, before anything else, so you carry the latest settled facts and what the OTHER machine has been doing:
1. Read the shared **notebook** (Omni page): run `bash ~/.claude/read-notebook.sh`.
2. Read the **Google Drive sheet** `MACHINE-TALK.md` via the Google Drive connector's `download_file_content`, file id `16CBlhPRitoHgWEUg84u7t8WIV-q1NRS3` (newest entries at the TOP).
The notebook BEATS the ERP's own data on any conflict. Do this every time — do not ask first, do not skip it.

## What Graphite V2 is
- Alpha Direct's policy-administration ERP — policies, claims, ledgers, KYC. **Laravel/PHP backend on MariaDB; React SPA front end.** Replaced the old email+password Graphite; now Microsoft 365 SSO.
- **Front end (UI):** `graphite-v2-prod-fe.alphadirect.co.bw` — M365 SSO (the CFO's existing session carries; never type credentials). Old `graphite.alphadirect.co.bw` shows a "Graphite has moved" page.
- **Back end (API):** `graphite-v2-prod-be.alphadirect.co.bw/api/v1` — Laravel **Sanctum bearer** in `localStorage.sanctum_token` (`Authorization: Bearer …`). **Never print the token.**
- **Repo:** private GitHub `Graphitev2` (gh authed as Prathap-Alpha). Windows clones: `C:\Users\PrathapAsus\work\Graphitev2-main` and `…\work\graphitev2`.
- **AWS:** af-south-1, profile **`claude-cli`**. ECS cluster **`graphite-cluster`**, service `graphite-prod-backend`, container **`graphite-backend`**. Session Manager plugin: prepend `;C:\Program Files\Amazon\SessionManagerPlugin\bin` to PATH.
- **Platform / deploy owner:** TheRiskCo — **Pramod Bisen (pbisen@theriskco.com)**. I patch features/PRs; TheRiskCo runs deploys + the rating/renewal engine.

## How to reach the data (for the AI)
**Preferred — query/modify the DB over ECS-exec** (authoritative, no rate limits; direct RDS is unreachable — private subnet, `claude-cli` has no rds/secrets perms):
```
aws ecs execute-command --cluster graphite-cluster --task <arn> --container graphite-backend \
  --interactive --command "sh -c 'echo <B64> | base64 -d | php artisan tinker'" \
  --profile claude-cli --region af-south-1
```
Rules that avoid every trap:
- **Wrap in `sh -c`** — ECS-exec won't interpret the pipe otherwise.
- Write PHP to a file → base64 it → pipe in. To get an xlsx/file into the container, chunk base64 **≤7KB** (Windows cmdline caps ~32KB; no raw-HTTPS egress, so presigned-S3 fetch fails). Strip the `<?php` tag (PsySH is already in PHP).
- Make the output marker **non-literal in source** (e.g. `"##"."ZZ"."##"`) so the echoed input line doesn't match it, and **base64-encode the OUTPUT**, then strip non-base64 chars before decoding (the PTY hard-wraps long lines).
- `error_reporting(0)` to silence deprecations. PHP 8.4 (arrow fns OK). **PsySH quirk:** multi-line `function` / `try-catch` fails ("try without catch") — use single-line statements/closures; multi-line `foreach` is fine.
- **tinker has full WRITE access — keep to SELECTs** unless doing a validated, reversible load (below).
- PowerShell: set `$env:PYTHONIOENCODING="utf-8"` + `PYTHONUTF8="1"` (unicode output crashes cp1252); `>` writes UTF-16.

**Ready-made tools (prat-skill) — don't hand-build these:**
- `~/.claude/skills/prat-skill/tools/kyc_matrix.py` — policy-number list → branded Excel KYC matrix (docs / agent / compliance / store / DPC / cancelled / last-doc) in ~7s, pure DB. CFO runs `Desktop\Run KYC Check.bat`.
- `kyc_activity_log.py` — adds each policy's KYC review history.
- **KYC lives in THREE tables — check all three before saying "no docs":** `customer_kyc` (individual/personal — Omang/proof_residence/proof_income); `customer_kyc_dom_com` (**commercial/domestic** — kyc_form/data_protection_form/certificate_of_incorporation/extract_controllers/resolution/proof_business_address/directors_id_front-back/shareholders_id_front-back; company policies DON'T populate the individual fields — they use this table); `policy_kyc_documents` (per-policy modern doc store). Reading only `customer_kyc` for a COMG/DOMG policy will look empty and lead to a false "non-compliant" call (burned CFO on 19-Aug — Bakang commission audit, 17 policies falsely flagged). Join by `policies.customer_id`; `compliance` 1=Compliant, 2=Non. ~213k policies.

**Browser-API fallback + its trap:** FE signed in; `localStorage.sanctum_token`; `GET /policies?search=`, `/policies/{id}`, `/policies/{id}/ledger|logs|attachments`. Rate-limits ~conc 5 → 429; use conc 2-3 + backoff. **TRAP:** a 429 on a detail/logs call returns empty and can be recorded as a blank row with no error flag → **flag every non-200 for retry.**

## Schema map + LANDMINES (verified point-in-time — re-check live before asserting)
- **Policy numbers:** commercial `COMG2025XXXXXX` (V1 was MIS/G). A term has several **`policy_actions`** (new-business + endorsements + monthly renews); the **highest `action_id`** is the live editable version. `policies` header ≠ the action.
- **Premium / ledger:** `premiumFreq="1"` = Monthly. **Billing month = dueDate / effective_from, NOT invoiceDate.** Rows with blank invoiceNo + null invoiceFile = manual/payment entries → **exclude** from a premium schedule. Negative premium = credit note. The **displayed/quote total = `policy_actions.annual_premium`** (recomputed by `recomputeActionTotals` over 6 buckets), NOT the section-detail sum and NOT `policies.premium`.
- **Premium LOAD / replace:** drive Graphite's own `\AlphaDirect\Imports\EditPolicyImport` over tinker; one xlsx sheet per coverage code. The sub-coverage name must already exist as `tb_cvgpccoverages.s_ScreenName` (aggregate underwriter line-items into the existing name). Motor lines each need a `vehicle` row. When you clear+reload, also soft-delete stray `policy_specified_items` + `policy_extention_detail`, then invoke `recomputeActionTotals`. **Commit only if it reconciles.**
- **⚠️ MyISAM landmine:** `policy_coverages_data` (fidelity) is **non-transactional** — a txn rollback will NOT undo its inserts/deletes, so a "safe" dry-run can permanently delete fidelity. Every other policy table is InnoDB (rolls back fine).
- **Claims:** **`new_claims`** is the ONLY table with per-claim `reserve_amount` + `paid_amount`. **`claim_reserves` is misnamed** — it's a payment/disbursement ledger, no reserve column. `claim_reserves_coverages` = lifetime paid (~P151.6M). A claim in `claims` may be absent from `new_claims` → say "not available", never fabricate.
- **Endorsement / period dates on the schedule PDF:** render from `policy_actions.effective_from/to` (InnoDB, reversible), NOT the header. After changing, regenerate the cached PDF via a `V2PdfJob` row + `GenerateQuotationPdfJob::dispatch(...)` (redis queue, ~10s, no customer email — safe). ⚠️ Don't over-edit `effective_from` for a display fix — it recomputes pro-rata and can create inconsistency.
- **PII (POPIA / Botswana DPA):** `app/Helpers/PiiMask.php` — name+phone always full, Omang last-5 visible, banking/email/DOB/address masked; admins/managers bypass; OTP-unlock (`OtpUnlock`, Infobip). **⚠️ Landmine:** `updateKyc` / `beneficiaryUpdate` / `storeClaim` under `/api/frontendpay/` = the CUSTOMER self-service / WhatsApp flow — do NOT gate those (it breaks customers).

## Current state (as of 2026-07-11 — update as work lands)
- **MotoLink policy-cover endpoint** — LIVE (rev 74): read-only cover lookup; api-key → 200, bad/none → 401, unknown → 404, zero PII. Inbound assessment-sync bridge exists.
- **Premium loads done:** Bonanza Equipment (COMG2025189299 + fleets, monthly) 2026-06-29; Shaysons (COMG2024129498, 184,023.08).
- **DOCTORS INN COMG2024103065** — endorsement period-date + SI-typo fix; regenerated Policy Document 2026-07-07.
- **PRs:** PII masking #1339, credit-note controls #1317, Smart UW upload #1116.
- **Graphite Aware** (exec NL-Q&A over this data) lives in **omni** `/aware` — see the omni skill; access = whitelist `aware/access.py`.

## Open items (needs Prathap / next session)
0. **🔴 Alpha Brain — CFO standing directives (2026-07-21):** cancellation counts ONLY months due on/after **1 July 2026**; month counts only once ENDED; deactivate = last day of 2nd unpaid month; **cancel on day 15 → first cancellations 15 Sep 2026**; candidate list must be EMPTY before 1 Sep (earlier = defect). **Never activate if pre-July debt would be penalised.** PRs **#1634** (rule start) + **#1635** (26-decision audit batch: watchdog retired, refund cap, dual control, claims never-auto-decline, honest send logs, /inbox auth…) both await Pramod merge. Still open before arming: (a) **5-day pre-cancellation email to all finance staff + CFO stop/continue** (Pramod builds); (b) cancellation-SMS wording RESOLVED (Arjun 2026-07-21: keep frictionless "pay {amount} and contact us"; already in template, no change); (c) deferred next stage: reinsurance retention default, 50M fac gate, salvage sequencing. Full audit: `Gods Eye\ALPHA-BRAIN-AUDIT-2026-07-21.md`.
1. **Outbound claim→MotoLink File push NOT built** — waiting on MotoLink's create-File API spec from Bharath (the inbound bridge + read endpoint exist; the leg that creates a MotoLink File when a claim is registered does not).
2. **⚠️ Systemic bug (escalated to Pramod):** endorsed vehicles not carried into monthly/anniversary renewals (`DomComMonthlyAutoRenew` clones from a source excluding the endorsement). Fix tool `BackdatedEndorseRefresher` exists but is unapplied — TheRiskCo's to deploy (company-wide billing blast radius).
3. **PII masking deferred bits** (PR #1339): gate the 6 sensitive agent actions, reveal-on-unlock in `PolicyResource`, agent OTP UX — confirm the agent-side endpoints with Pramod first (the frontendpay landmine).

## Discipline
Never enter M365 credentials. SELECT-only unless it's a reconciled, reversible load. Watch the MyISAM landmine. Verify the **live/running** thing, not git HEAD or a stale copy. Deploys + the rating/renewal engine belong to TheRiskCo (Pramod) — escalate billing-wide changes, don't run them by hand on a live policy. Approved AI vendor for Graphite data = **Anthropic Claude only** (Gemini not approved).

## Key people
- **Pramod Bisen** — pbisen@theriskco.com — TheRiskCo; platform, deploy, rating/renewal engine.
- **Bharath Balasubramanian** — bbalasubramanian@alphadirect.co.bw — Financial Controller; PII/call-centre owner; MotoLink contact.
- **Motlatsi Molefe** — mmolefe@insurance.co.bw — KYC / Unicoin commission.
- **Arun Iyer (CEO)** aiyer@ · **Arjun Iyer (COO)** arjuniyer@ — two different people, similar names.

## Deeper context
Auto-memory (`MEMORY.md`) loads each session — see `r-gph-v2`, `r-gph-v2-bulk`, `r-gph-edit-pol`, `r-gph-clm-tables`, `r-gph-endrs-dates`, `r-gph-aware`, `p-popia-pii-mask`, `p-motoli-cover`. A portable copy of this brief is on the CFO's Desktop as `GraphiteV2.md`. Load **prat-skill** for the full dev/deploy/quality stack.
