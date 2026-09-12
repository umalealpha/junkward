---
name: omni
description: >
  Quick-start context for the Alpha Direct omni ERP (omni.alphadirect.co.bw).
  Auto-load whenever Prathap types "/omni", says "work on omni", or the task
  touches omni: Graphite Aware reports, the staff email login / sign-in,
  weekly Excel exports, omni deploys, or omni user/access questions. Loads the
  current build state, open items, and the working + deploy rules so a fresh
  chat continues exactly where the last omni session left off. Complements
  prat-skill (the full dev stack) — this is the omni-specific quick start.
  Keep the "current state" and "open items" sections updated as omni work lands.
---

# omni — Alpha Direct ERP quick-start

**Talk to Prathap (CFO) in plain English. Do the whole ask in one run — don't stop to ask "can I proceed" except for the hard lines: moving money, changing someone's access/permissions, or deleting live data.** Full working conventions live in **prat-skill** (load it for the deep dev stack); this skill is the omni-specific starting context.

> 🚫 **OMNI NEVER MOVES MONEY.** Every "payment / approve / authorise / mark-as-paid" in omni is a WORKFLOW RECORD only — it never debits an account. Real money leaves ONLY when the CFO authorises it himself in the FNB app with 2-factor. Never call omni payment work "money-critical" or "money movement" (CFO angry ~100×). A wrong omni payment record is a data bug — fix it — not money moving.

**DISPLAY RULE — figures always carry a thousands-separator comma** (CFO 2026-08-30): every number omni shows is grouped, e.g. `980,309` / `P 11,912,578.57`, never `980309`. Use a shared formatter (`toLocaleString('en')` / `Intl.NumberFormat`); money keeps 2 decimals, stays in Pula, VAT rounds HALF UP.

## On load — pull the shared notes first (automatic, never wait to be asked)
The moment /omni loads, before anything else, so you carry the latest settled facts and what the OTHER machine has been doing:
1. Read the shared **notebook** (Omni page): run `bash ~/.claude/read-notebook.sh`. **This beats omni's own database on any conflict.**
2. Read `MACHINE-TALK.md` at the top of the git repo — `git -C "C:/Users/PrathapAsus/work/alpha-finance" fetch origin -q && git show origin/main:MACHINE-TALK.md | tail -30` (newest at the BOTTOM). This is the ONE shared mailbox both machines read AND write (union-merge via GitHub). The old Google-Drive and OneDrive `Gods Eye` copies are RETIRED — do NOT read them.

Do this every time — do not ask first, do not skip it.

## What omni is
- **omni** = the Alpha Direct ERP at **omni.alphadirect.co.bw** — Django backend + Next.js front end. NOT OMNIUS.
- **Work repo (Windows):** `C:\Users\PrathapAsus\work\alpha-finance` (gh auth `Prathap-Alpha`). Never use the OneDrive `Gods Eye\alpha-finance` copy — it's stale.
- **Prod:** EC2 `i-02a5d76a61f4f09a5`, af-south-1. Live domain fronted by Cloudflare.

## The build + ship workflow (use the skills, don't hand-roll)
- **`/code`** = build + test, then STOP (does NOT go live). Reads notebook + machine-talk + memory, then runs prat-skill → Karpathy → lane-b → fabe.
- **`/deploy`** = the partner go-live step — takes already-tested code live safely via the fabe ship-gate (right lane, no parallel-session clash, near-zero downtime, proves the live site survived).
- **`/fabe`** = the actual ship-gate: tests → fixes → deploys via AWS SSM. Hard tripwires on secrets / frozen numbers / PII; pauses for the CFO on those. The old `prat-test` skill is RETIRED.
- **`/deepseek`** = independent second-opinion review (off-subscription), no deploy.
- Sibling skills for omni-adjacent work: **`fnb`** (banking / payment approval), **`graphite-v2`** (policy-admin ERP behind Aware), **`Payroll`** (payroll runbook + mistake list), **`alphaleave`** (leave & productive-hours — supersedes the old `leave` skill), **`pending`** (asked-vs-done check).

## How to run / deploy (for the AI)
- Run prod code via AWS SSM: `aws ssm send-command --profile claude-cli --region af-south-1 --instance-ids i-02a5d76a61f4f09a5 --document-name AWS-RunShellScript` (NOT `AWS-RunShellCommand`). Poll `get-command-invocation`.
- Django shell: base64-pipe python into `sudo docker compose --env-file /etc/alpha-finance/.env exec -T backend python manage.py shell`.
- **Deploy:** git on the box runs as **ubuntu** — `sudo -u ubuntu git -C /opt/alpha-finance fetch origin main && … reset --hard origin/main`; then `docker compose --env-file /etc/alpha-finance/.env build backend frontend` → `up -d`. Backend auto-migrates on start.
- **Gotchas:** frontend recreate can hit "container name already in use" → force-remove then `up -d`. **Parallel sessions share the one clone** — `git add` only YOUR files, never commit another session's work, verify against `origin/main` not the local tree. Big data → S3 presign → curl → `docker cp`. **One migration leaf on merged main before deploying** — two parallel branches = two leaves = prod crash-loop while the site still serves 200. A new env var set only in `.env` also needs a matching line in docker-compose or it arrives EMPTY and the grant silently no-ops.
- **Discipline:** test on the real running system before "done"; verify the live site, not a local checkout; passwords/keys never in plain text; never weaken auth or move money.

## GL IS EMPTY IN OMNI ON PURPOSE — do not raise it (settled 19-Aug-2026)
10 of 12 entities show ZERO journal entries since 1 May 2026 — **that is correct.** Odoo is the book of record for the GL right now; omni is not. An empty omni GL is the migration state, not a broken feed. Do not "fix" it, investigate it, or report it as a finding. The GL balances transfer out of Odoo into omni **after the audit, from ~19 Sep 2026** — a planned migration, not a bug. Anything counting postings per entity (dashboards, daily brief) looks alarming until then — check against this note before escalating.

## Current state — what's live now (as of 2026-09-05)
Newest first. Detail lives in the named memory; this is the map, not the changelog.
- **Redundancy & re-hire transfers + leaver final leave pay** LIVE 5-Sep (PR #758, main `3df1f062`) — HRIS → Transfers has a mode picker: *Carry over* (same record) or *Redundancy & re-hire* (terminate at source on effective−1, pay out or carry the leave, new record at destination with login + Time Doctor link + reports). Leaver final leave pay = `LeaveEncashment kind=settlement`, full balance, CFO→HR→Finance; Finance still types Leave Pay on the final payslip. Same release: Unami AND Dorothy decide roster flags ("Not my report" on the emailed feedback page + Monthly Feedback); HR (hris tier) can open Who-tracks and confirm a TD link (switch stays CFO/Arun/Arjun); Leave Admin "Apply for someone"; `manage.py check_recipient_access` + send_mail.py pre-send access block. `p-rehire-xfer`.
- **Petty-cash Unicoin ring-fence** LIVE 31-Aug — raisers Bakang/Phatsimo Moseki only; approvers Keetile (1st)/Bharath only; red theft notice. `p-petty-cash-ringfe`.
- **My Omni personal home** LIVE 29-Aug (prod `5e9c7cfc`) — post-login front door `/my-omni`, aggregates existing feeds + announcements. `p-omni-home`.
- **Payment History / register screen** LIVE 29-Aug (`b4cf084d`) — the missing FRONTEND over an already-live backend. `p-pay-hist-detect`.
- **Omni refresh banner fix** LIVE 25-Aug (`154d069c`) — closes the old "Windows changes don't show" open item; build-id now stamped once in the Dockerfile so the refresh banner fires on every deploy. `p-omni-refres`.
- **AI CV screening** LIVE 25-Aug (PR #718, `d4703062`) — enabled omni's NATIVE recruitment AI, identity-redacted + PII-firewalled. `p-hire-scrn-svc`.
- **Payroll Monthly Pack & Checks** LIVE 24-Aug · **Archived-leaver propagation** DEPLOYED 24-Aug (Humans 168→156). `p-payr-mth-pack`, `p-arch-leaver`.
- **FNB payment reference + POP + invoice-OCR** LIVE 22-Aug — batch name reads `payee + Omni number + (O)`. Plus **FNB email auto-reconcile**. `p-fnb-pay-refere`, `p-fnb-email`.
- **Supplier-list upload** LIVE 21-Aug (`9f108fa0`) · **BONU legal claim-intake + lawyer-payments** LIVE 21-Aug (`123bae6b`) · **EFT-export permission gate** (PR #698). Machine-talk 21-Aug.
- **Compliance:** NBFIRA filed-return upload LIVE + A.1 "Compare / fix to workbook method" (proven to the cent) · Refunds "Already paid" LIVE · DPO/DPIA register LIVE. `p-nbfira-filed`, `p-dpo-dpia-reg`.
- **Built, NOT yet deployed:** FX Payment Planning. `p-fx-pay-planni`.

Older shipped work (Jul and before — Leave Encashment, Vehicle Register, Workforce/Time-Doctor briefs, Development Dialogue, taskboard presets, staff email login, Graphite Aware) is recorded in the memory index (`MEMORY.md`) — pull the named memory when a task touches it, rather than reading it here.

## Staff email login + Graphite Aware (stable facts)
- **Graphite Aware reports** (exec whitelist, read-only over Graphite V2): Broker Analysis (claims money per broker, not a loss ratio), Top 50 Dom (names masked to initials), Claims Registry (open+pending, safe fields). Each auto-saves a dated Excel every Sunday 06:00 (cron `/etc/cron.d/aware-reports`, kept 26 weeks), downloadable in-app.
- **Staff email login** (`/staff-login`, non-SSO): email → password → 6-digit code emailed → in. Default password **`Omni123`**, forced change on first login; emailed code is the real 2nd factor. Admin break-glass (`/break-glass`, `/api-token-auth/`) is separate.
- **Group-staff domains allowed:** `alphadirect.co.bw`, `.co.zm`, `.co.za`, `insurance.co.bw`, `theriskco.com`, `quantum.co.bw`, `motorliquidators.co.bw`. **Blocked:** shared/role boxes (`hc@`, `people@`, `internalauditors@`) and outsiders (gmail etc.).
- **User hygiene:** never-logged-in duplicate account = just delete, don't ask. Seed default password with `python manage.py seed_staff_passwords` (never clobbers a changed password).

## Open items (needs Prathap / next session)
1. **`adrisk` domain** — named as genuine group staff but no adrisk address exists in omni/M365 yet. Need the exact domain before adding to the group list.
2. **FX Payment Planning** — built, not yet deployed. `p-fx-pay-planni`.
3. **Duplicate "Brightside" broker** in Graphite (book split across two agency rows) — cleanup pending.
4. Optional: a proper actuarial **broker loss-ratio** (earned premium matched to claims by underwriting year).

## Deeper context
Auto-memory (`MEMORY.md`) is loaded each session. Load **prat-skill** for the full dev/deploy/quality stack, and the sibling skills named under "The build + ship workflow" above for their areas.
