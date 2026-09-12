---
name: aruninbox
description: >-
  Alpha Direct "CEO Monitor" — the daily/weekly executive brief built from the
  CEO's (Arun Iyer, aiyer@) REAL email inbox. Auto-load whenever Prathap types
  /aruninbox, or the task touches: the CEO Monitor / CEO Omni Brief, Arun's inbox
  digest, the "Assign & escalate to" buttons, the svc-ceomonitor mailbox, the
  daily 7am brief or Sunday "CEO — YOU BETTER READ THIS" board read, the
  escalate endpoint /api/ceo-monitor/escalate/, or reading aiyer@ via Graph
  Mail.Read. Carries the architecture, the exact keys/scoping, the prod cron +
  drivers, the design decisions, the safety fixes, and the open refinements so a
  fresh chat continues exactly where this left off. Companion to `omni` (deploy),
  `prat-skill` (dev stack), `fabe` (ship gate). KEEP CURRENT STATE + OPEN ITEMS updated.
---

# /aruninbox — CEO Monitor (Arun's inbox → daily/weekly brief)

Non-technical CFO (Prathap). Plain English to him; do the whole ask in one run.

## What it is
A daily (and weekly) email brief for the **CEO, Arun P. Iyer (aiyer@alphadirect.co.bw)**
that reads **his real inbox**, filters out the noise, and surfaces only the matters he must
personally know — real customer complaints, regulator/NBFIRA, legal threats/letters of demand,
high-value claims/payments (≥ BWP 500k), data/security incidents, major financial escalations.
Each matter has one-click **"Assign & escalate to <exec>"** buttons that create an OmniTask
(which fans out to that exec's task board + email). **Eyes-only: the brief emails ONLY to
aiyer@ (CEO), cc pganesharajah@ (CFO).**

Replaces Sechele's old Power-Automate "CEO Monitor v4" (svc-ceomonitor@ + a SharePoint
`CEO_Monitor_Queue`), which the CEO was unhappy with. Sechele's version was **switched off**
28-Jul-2026 (he confirmed). The CEO monitor is **CFO + CEO eyes only** (Prathap directive).

## People / who's who (verified)
- CEO = **Arun P. Iyer, aiyer@** (pk 61, username `arun.iyer`). ≠ Arjun Iyer (COO, arjuniyer@).
- CFO = **Prathap Ganesharajah, pganesharajah@** (the brief owner; recorded as the escalation assigner).
- Escalation targets (label → handle@alphadirect.co.bw), CFO-confirmed 28-Jul:
  Paul=pbeka · Arjun=arjuniyer · Unami=ubutale · Wangu=wmoses · Bharath=bbalasubramanian ·
  Kago=**ktshutlhedi** (Finance Manager, NOT Pako Kago) · Gao=**gmachobane** (Gaolebale Machobane) · Prathap=pganesharajah.

## Access / keys (Microsoft 365, tenant fb4aec07-793a-494c-92f6-7a527a7f89c0)
- Reading Arun's inbox uses the Graph app **"Omni CEO automation"** (renamed from "Manus Email
  Automation"), **App ID `ca983cff-0d9a-4715-8772-fe1f5a09da5a`**. It has **Mail.Send + Mail.Read**
  (Application). Secret lives in `prat-skill/secrets/manus-graph-sender.env` (local) AND on prod at
  `/opt/ceo-monitor/graph.env` (root 600, keys `CEO_GRAPH_CLIENT_ID/TENANT/CLIENT_SECRET`).
- **Scoped by an Exchange ApplicationAccessPolicy** to the mail-enabled security group
  **`grp-omni-ceo-monitor@`** = {aiyer@, pganesharajah@} only (`RestrictAccess`). So the key can
  open ONLY those two mailboxes — verified: aiyer@ 200, pganesharajah@ 200, everyone else 403.
- **Granting Mail.Read / admin consent / the ApplicationAccessPolicy is a Global-Admin action.**
  Prathap is admin but the "Grant admin consent" button is GREYED for his account — **Sechele**
  (Global Admin) did the consent + the scope policy via Exchange PowerShell. (`New-ApplicationAccessPolicy
  -AppId ca983cff... -PolicyScopeGroupId grp-omni-ceo-monitor@ -AccessRight RestrictAccess`.)
- NB: omni prod's OWN Graph app is a DIFFERENT one — `MICROSOFT_CLIENT_ID=fcf2cd9e-...`, sends as
  omni@. It does NOT have Mail.Read. We use ca983cff for reading (creds placed on prod). If ever
  moving off ca983cff, grant fcf2cd9e Mail.Read + add it to the scope group instead.

## Architecture (all on prod EC2 i-02a5d76a61f4f09a5, af-south-1, via SSM)
- **Host cron scripts** in `/opt/ceo-monitor/`: `ceo_engine.py` (render/merge/pipeline, ported from
  `Gods Eye\CEO-Monitor\v5\ceo_monitor_digest.py`), `ceo_driver.py` (daily), `ceo_sunday_driver.py`
  (weekly), `run.sh` + `run_sunday.sh`, `graph.env` (the read key).
- Crons: `/etc/cron.d/ceo-brief` = `0 5 * * *` (05:00 UTC = **07:00 SAST daily**) → run.sh;
  `/etc/cron.d/ceo-board-read` = `0 5 * * 0` (**Sundays 07:00 SAST**) → run_sunday.sh. Both send
  to CEO_TO=aiyer@ CEO_CC=pganesharajah@.
- **Pipeline (each run):** `run.sh` sources graph.env → `docker compose cp` engine into the backend
  container → `docker compose exec -T -e CEO_GRAPH_* -e CEO_SEND/TO/CC backend python manage.py shell
  < driver`. Driver: **gather** = read aiyer@ inbox via Graph (top 25, subject+from+bodyPreview) →
  **classify** = `core.ai_assist.reasoning_complete` (DeepSeek, `max_tokens=4096`) behind
  `is_safe_for_ai()` PII firewall (redacts before send) → strict-significance prompt → **render** via
  engine (cards, colour pills, Ref/Due/Action chips, escalate buttons) → email via `django.core.mail`.
- **Design/brand:** navy #0D1B2A header, orange #F4A623 accents, Book Antiqua headings + Arial body.
  Daily subject **"CEO Omni Brief - {date}"**. Sunday subject **"CEO — YOU BETTER READ THIS - Weekly
  Board Read {date}"** (leads with STILL-OPEN). Empty day → "Nothing needs you today".

## Escalate endpoint (LIVE, omni code — PRs #520/#522/#527, prod)
`core/ceo_monitor_views.py` + url `path('api/ceo-monitor/escalate/', ...)`. Must be under **/api/**
(non-/api → Next.js → 404). **Token IS the gate, no login** (omni sessions are FE tokens not Django
sessions) — signed via `django.core.signing` (salt `ceo-monitor-escalate`, 14-day expiry), `@csrf_exempt`.
**GET renders a "Escalate to X? Confirm" page with NO side effect; the OmniTask is created only on POST**
(the Confirm button). This is the critical safety fix (/fabe caught it): Microsoft 365 SafeLinks
pre-fetches GET links, so side-effect-on-GET would auto-fire every escalate button. Fail-loud 400 if the
CEO account can't be resolved. Idempotent per (assignee, `source='ceomon:<ref>'[:30]`). Tests:
`core/tests/test_ceo_monitor_escalate.py` (GET-creates-nothing lock etc.); CI runs the whole suite.
Drivers build buttons via `from core.ceo_monitor_views import make_escalation_token`.

## CURRENT STATE (28-Jul-2026) — LIVE
- Daily brief + Sunday board read + escalate buttons ALL live on prod. First inbox-based daily = the
  next 07:00 SAST. Escalate endpoint deployed + live-verified (GET→confirm 0 tasks, POST→1 task, CEO=assigner).
- **Daily driver reads Arun's REAL inbox** — verified end-to-end on prod (25 msgs pulled, 10 PII
  redactions, junk filtered, real matters surfaced). Real preview sent to Prathap.
- /fabe gate passed (Fable SHIP after fixing the GET-mutation bug). Ledger logged.

## CLAUDE-DESIGN RESKIN + "WAITING ON YOU" — LIVE from 12-Aug-2026 (min-disruption: no off-time send; flows on the normal 06:30 SAST cron)
The live `ceo_engine.py`/`ceo_driver.py` now render the CFO's Claude Design (600px table email:
logo header, one-thing box, cards w/ CRITICAL/HIGH pill badges + your escalate-pill footer w/ real tokens,
3-col meetings w/ EXT pills, Tomorrow number strip, Setswana PS, compact DPA footer) — source
`Gods Eye\CEO-Monitor\v6\ceo_engine_v6_prod.py` (design reskin via `apply_design.py`) + `ceo_driver_live_v6.py`.
Backups: `ceo_engine_pre_design.bak` / `ceo_driver_pre_design.bak` (one-step rollback). Design HTML the CFO built
is pulled from claude.ai/design via the OmeletteService GetFile trick (see `r-claude-design`).
NEW: **"Waiting on YOU"** block = the CEO's own OmniTask inbox (approvals/sign-offs assigned to him, `profile__title='ceo'`,
`OmniTask.filter(assignee=ceo, status__in=['pending','in_progress'])`, age + overdue flag) via `fetch_waiting_on_ceo()`.
At_stake now falls back to the classifier category for section labels (complaint→Customer Complaints etc.).

## MAGIC LINK — ENGINE LIVE ON PROD 12-Aug-2026 5:05pm (focused-action, no session-mint); emails NOT wired yet
LIVE via surgical cherry-pick onto prod (commits 04e72b5e engine + d655a6f9 ping; rollback point 0740e77a): `core/magic_action.py`
+ route `/api/magic/<token>/`. PROVEN cold — external POST with NO login returned "It works... as Prathap Ganesharajah".
manage.py check passed, root 200, zero staff impact (no email wired). Repo copies in worktree C:/af-magic (branch feat/magic-link, PR #635).
TWO FOLLOW-UPS before wiring real actions: (1) **single-use jti is best-effort only — cache not shared, replays currently
succeed → HARDEN with a DB-backed jti table before any real approve action.** (2) **PR #635 must merge to main or the next
`git reset --hard origin/main` deploy DROPS the cherry-pick** — blocked by pre-existing red main build (hris test_daily_tasks
imports removed CFO_EMAIL; spawned a fix task, NOT mine). Once main's green, merge #635. Initial post-deploy 404 was a transient
during the backend restart (Caddy /api/* + Django both route it fine once up). CFO reversed the money carve-out: payment/payroll
approvals ARE one-click (Omni approval != money out; FNB app is the egress gate — [[f-appr-not-money]]).
NEXT (per-flow, each with its own permission re-check + cold-click proof): wire payment/payroll/JE/petty-cash/PO approvals +
dialogue + tasks; deploy quietly. FULL login-from-link version stays BLOCKED by the harness safety classifier — not doing it.

## MAGIC LINK — original plan (CFO: "sweep everywhere people get email, put the magic link"; rollout = build-once-wire-everywhere)
No-login deep link for STAFF emails: click → establishes their normal Omni FE session + lands on the item, no password.
MECHANISM (mapped): Omni FE session = DRF authtoken in localStorage `alpha_token` (validated by `core/token_auth.py`
ExpiringTokenAuthentication, 15h TTL, DB-lookup so server CAN mint via `Token.objects.get_or_create(user)`). Safe design =
pure-Django endpoint under `/api/magic/<token>/` (same-origin: Django page sets localStorage.alpha_token + redirects into
the Next app — NO frontend build needed), signing.dumps `{u,path,jti}`, short max_age, single-use jti, GET-inert/POST-act
(SafeLinks-safe), ONLY for active internal Users. Mirror `core/ceo_monitor_views.py` escalate + `hris/leave_actions`.
TARGET SET (~15 staff emails, from inventory): core/notifications.py 10 flows (JE/payment/petty-cash/dialogue/import/payroll/
assets), taskboard task-assigned+comment, hris amendment/disciplinary/encashment/incentive-status, customer_refunds CFO-auth,
helpdesk/bug-report. ALREADY signed (reuse): leave-action, spend-action, incentive-submit, escalate, manager-accountability,
explain-my-day. EXCLUDE (external): PO PDF to supplier, healthcare vendor e-sign, vendor onboarding invite.
CAUTION: don't rush auth to all-staff — prove with a cold click first; repo is 830-behind + 40 worktrees (work off origin/main).
PROGRESS 12-Aug: full login-from-link (session-minting `core/magic_link.py`) was BLOCKED by the harness safety
classifier (account-takeover risk) — do NOT try to route around it; needs a deliberate human-reviewed exception.
CFO decision (UPDATED 12-Aug, supersedes the money carve-out): ALL Omni approvals — INCLUDING payments/payroll —
get the SAME true one-click magic link. Rationale (CFO, 20yrs): an Omni approval is a workflow step, it does NOT
move money; cash only leaves via the FNB app (dual auth at the bank). So a leaked one-click Omni approval can't
release funds — no special view-only carve-out needed. Do NOT re-litigate this. See [[f-appr-not-money]]. SAFE focused-action ENGINE
BUILT + committed on branch `feat/magic-link` (worktree C:/af-magic): `core/magic_action.py` (signed-token, GET-inert
SafeLinks-safe, POST-acts, re-checks in-app permission, single-use, NO session mint — mirrors escalate/leave-action) +
url `/api/magic/<token>/`. NOT DEPLOYED, NOT wired to any live email. KEY REALISATION: DD reviewer sign is NOT one-click
(reviewer must add manager scores first → "open to work" bucket); genuine one-click = approve/reject/acknowledge decisions.
NEXT: wire the true one-click approvals (JE/petty-cash/PO), cold-click-prove one on a throwaway (never write-test real
prod data), then deploy; do the "view-no-login" pages for money separately. Already-signed flows to reuse: leave-action,
spend-action, incentive, escalate.

## v6 REDESIGN — LIVE TO CEO from 12-Aug-2026 (per CEO feedback + CFO "go live")
**LIVE:** v6 is now the daily brief. `/opt/ceo-monitor/ceo_engine.py` = v6 engine (backup `ceo_engine_pre_v6.bak`);
`/opt/ceo-monitor/ceo_driver.py` = v6 live driver (backup `ceo_driver_pre_v6.bak`), real recipients CEO_TO=aiyer@
CC=pganesharajah@ via run.sh. Cron `/etc/cron.d/ceo-brief` = `30 4 * * *` (04:30 UTC / 06:30 SAST). Rollback =
restore the two .bak files. Repo copies: `Gods Eye\CEO-Monitor\v6\ceo_engine_v6_prod.py` + `ceo_driver_live_v6.py`
(preview-only forced-to-CFO variant kept as `ceo_driver_v6_preview.py`).
LIVE features: new Claude-Design look; facts->points-scoring->recommendation playbook; score>=40 nonsense gate;
"one thing today"; **calendar meetings block (Arun + Prathap live; Arjun pending group propagation)** via
Calendars.Read (granted 12-Aug by Sechele on app ca983cff, scope group grp-omni-ceo-monitor@ + arjuniyer@ added);
tomorrow big-number strip; **deeper "why" (classify prompt demands amount+party+ask, 850 chars of body, engine
rejects vague lines but keeps concrete qualitative ones)**; small witty **Setswana** sign-off keyed to the day's
meetings (local keyword map, no PII to any model). Badge shows severity word only (no score number), per CFO design.
KNOWN: DeepSeek significance still wobbles run-to-run (1 vs 2-3 matters) — inherent; safety-net + gate mitigate.
NEXT: body-fact chips (deadline/days-open from body), future-events plan pages, stateful "resolved" memory.

## v6 REDESIGN — original build log (12-Aug-2026, per CEO feedback + CFO)
CEO unhappy with old brief: too shallow, no solutions, weak prioritisation, wants calendar + future-events.
New Claude-Design look + brain built. Files (NOT live to CEO; live daily still = ceo_engine.py/ceo_driver.py):
- `/opt/ceo-monitor/ceo_engine_v6.py` — self-contained v6 engine (new look; facts→points-scoring→recommendation
  playbook; "one thing today"; factual-only "why" (never fabricates; rejects vague LLM lines); score>=40 gate).
  Source in repo `Gods Eye\CEO-Monitor\v6\ceo_engine_v6_prod.py` (+ local `ceo_monitor_digest_v6.py`).
- `/opt/ceo-monitor/ceo_driver_v6_preview.py` — copy of live driver, loads v6 engine, adds facts/score/recommend,
  score>=40 inclusion gate, v6 escalate grid (real tokens, recommended owner highlighted), **recipient HARD-FORCED
  to pganesharajah@ only** (never CEO). Run without CEO_SEND for debug.
- CFO previews verified live from Arun's REAL inbox (SENT to pganesharajah@ only): nonsense (Mitch Morrison
  Commissioner letter) dropped by the score gate; real matters (E-Power Critical, Karabo High) kept.
- Key fix: scorer must read the EMAIL TEXT, not DeepSeek's category label ("regulatory" contains "regulator" →
  false +40). Prompt over-tightening dropped real claims → reverted to original prompt + rely on score gate.
- OPEN: (1) meetings block BUILT but BLOCKED — app ca983cff has NO Calendars.Read (403 on all 3 mailboxes);
  ticket TKT-0105 + urgent email to Sechele sent (grant Calendars.Read + admin consent + add arjuniyer@ to
  grp-omni-ceo-monitor@). (2) "why it matters" still thin — needs BODY-fact extraction (amount/ask/days-open/
  deadline out of the email body); amounts already parse from summary when present. (3) future-events plan pages
  + stateful memory (deploy ceo-monitor-omni branch) still to do. (4) Not yet flipped live to CEO — awaiting CFO.

## DESIGN FIXES DONE (29-Jul, in the live daily driver)
- **Escalate buttons** were cramped in Outlook (inline-block margins collapse). Now a **table,
  4-per-row grid** (each an evenly-spaced bordered button). Outlook-safe.
- **Thread de-dup:** emails in ONE thread (normalised subject, strip RE:/FW:) collapse to **ONE
  card**, headed by the TOPIC (not the sender), with "N emails in this thread (from …)". The 5
  "Large Payment" cards → 1.
- **Source noise filter** in gather(): drops automated/system/marketing senders (Omni ERP, svc-,
  no-reply, Pinterest, LinkedIn, newsletters) + junk subjects (Development Dialogue, "did not answer
  on team downtime", unsubscribe, sign-in) BEFORE classification (~9/25 dropped).
- **Deterministic safety-net:** DeepSeek significance is non-deterministic (same inbox gave 5 matters
  one run, 0 the next). A high-precision keyword floor (`_STRONG`: not happy/dissatisf/ombudsman/
  nbfira/letter of demand/summons/court order/litigation/data breach/class action/authorisation
  request/repudiat) FORCES obvious matters in even if the LLM drops them, so a real matter is never
  missed (erring toward inclusion — right for a CEO brief). Keep `_STRONG` HIGH-PRECISION (broad words
  like escalat/payment/claim caught internal noise — removed).

## FIXES 29-Jul (CEO complaints: no names + escalate didn't email)
- **Escalate button now EMAILS the exec.** OmniTask.create did NOT auto-email on this path, so a
  confirmed escalation made the task but sent nothing. `core/ceo_monitor_views.py` POST branch now calls
  `_email_assignee()` (EmailMultiAlternatives via omni backend, try/except) — PR #530, live, tested.
- **NAMES now show — pulled from the email itself (DPA-safe).** `_extract_party(subject,from)` pulls the
  real customer name + ref from the un-redacted SUBJECT (e.g. "Re: Boikhutso Lorraine Maseng - 72770634"
  → "Boikhutso Lorraine Maseng (72770634)"). The name is NOT sent to any model (DeepSeek/Gemini still
  only see is_safe_for_ai()-redacted text). Re-hydrated into the matter (generic "customer" → real name).
  Full body now fetched (was bodyPreview) + HTML→text.
- **Consumer Watchdog / Ombudsman / NBFIRA = always-surface, reputational.** Detected by SUBJECT+SENDER
  only (`_watchdog_which` — NOT body text; "nbfira" in a signature/body must not trigger — that was a
  false positive on the tool-proposal email). Forces significant + category=regulatory + ≥High + a
  "…following up, reputational/regulatory risk" why. `consumerwatchdog@bes.bw` = Richard Harriman / CW.
- **Guaranteed coverage:** gather() = recent 50 UNION a `$search` sweep for "consumer watchdog"/ombudsman/
  nbfira/complaint/"letter of demand" (ConsistencyLevel: eventual) so an older-but-critical email is
  never missed (the watchdog email fell out of a 40-window once).
- **DeepSeek primary, Gemini fallback** (CFO pref): if DeepSeek errors OR returns 0-significant while
  strong-signal candidates exist → retry with `gemini_complete`. Both firewalled.
- **Design (from 29-Jul earlier):** escalate buttons = 4-per-row table grid (Outlook-safe); ONE card per
  email thread (normalised subject), headed by the TOPIC/party not the sender; source noise-filter drops
  Omni-system/no-reply/Pinterest/newsletters.
- Verified live (preview to CFO): 3 threads — Boikhutso Lorraine Maseng (Consumer Watchdog, named) +
  Bonno Kelapile (NBFIRA returns) + Large Payment (Critical, 6 merged). Escalate email tested OK.
- **run.sh recipients: CEO_TO=aiyer@ CEO_CC=pganesharajah@** (CFO approved 29-Jul → pointed back to the
  CEO). Daily 05:00 UTC / 07:00 SAST. (Was temporarily CFO-only overnight while the name/escalate fixes
  landed.)

## TWO DAILY-BRIEF FIXES — DEPLOYED LIVE 13-Aug-2026 (built /lane-b intent, shipped via /fabe)
CEO/CFO reported the Thu 13-Aug daily brief (1) duplicated the same issue and (2) had squished escalate buttons.
Diagnosed on the LIVE render (read-only prod probe, no send):
- **Issue 1 "duplication" = party-label collapse, NOT a thread-key dup.** `_extract_party` (in ceo_driver.py) grabbed the
  subject's leading words as the customer name, so every "FORMAL COMPLAINT: …" email headed with party="FORMAL COMPLAINT".
  Two DIFFERENT matters (pension fund + MRI) both showed "FORMAL COMPLAINT / HIGH" → looked like one alert twice.
  Fix: strip generic admin prefixes (formal complaint/urgent/reminder/… ) + stacked RE:/FW:, never keep a generic word as
  the name; fall back to topic/sender. Pension→"Unresolved Pension Fund", MRI→sender name (distinct).
- **Issue 2 "squished buttons" = v6 regression.** The active escalate renderer `_esc_row_v6` uses inline-block pills with
  margins that Outlook collapses. The Outlook-safe 4-per-row table grid `_esc_row` already existed at line ~31 but was
  clobbered by `E._escalate_row=_esc_row_v6` at line ~217. Fix: `_esc_row_v6` now delegates to a table grid
  (`render_escalate_row`, 4/row, block <a> in <td>, rec-owner highlighted). (Dead `_esc_row` left in — flag for cleanup.)
- **Built via /lane-b intent** but the local cost-gateway (:4000) was returning EMPTY completions (all models burned the
  token budget on reasoning, text_tokens=0) → built reliably instead, gated by runnable pytest (11 tests, fail-without-fix
  proven) + Opus VERIFIED + Fable SHIP. Gateway fix spawned as a separate task.
- **DEPLOYED:** prod `/opt/ceo-monitor/ceo_driver.py` now md5 `d126c8b651ace772924ccc27c40f7020` (repo source
  `Gods Eye\CEO-Monitor\v6\ceo_driver_live_v6.py` matches). Backup on box: `ceo_driver_pre_dedup_fix.bak` (rollback = cp
  back). Host-cron script, NOT git/docker — deployed by file copy via SSM; next 06:30 SAST cron uses it (no restart needed).
  Live read-only render verified: pension card party='Unresolved Pension Fund' (was 'FORMAL COMPLAINT'), escalate footer =
  Outlook-safe table grid, driver 0 inline-block. /fabe: Fable SHIP (Fable-only — cost gateway :4000 was down). Ledger logged.

## OPEN ITEMS / refinements
1. **Severity/wording still wobbles run-to-run** (LLM called the payment thread "Critical" one run,
   "Watch/routine" the next — undersells a real matter). Fix: temperature=0 if the gateway supports it,
   and/or bump safety-net-forced items to a severity floor (≥ High) so a forced real matter isn't shown
   as "Watch"; and tighten so pure sales proposals don't slip in. (Quality; not blocking.)
2. **SUNDAY = "Sunday CEO Dashboard" — a bigger multi-source advisory email (CFO spec 28-Jul).**
   Rebuild the Sunday email (rename to "Sunday CEO Dashboard") as a LONG, advisory read that
   summarises the week's problems from FOUR sources and advises the CEO:
   (a) **Alpha Brain** — compliance/intel picture (`core.compliance_brain.latest_summary` + `core.intel_summary`).
   (b) **Graphite claims dashboard — SLA breaches** — count, worst brokers/agents, advice (via aware.engine
       over the claims tables; the original digest cited "325 SLA breaches" + reserves > P9M).
   (c) **Time Doctor productive hours** — who's working / who isn't (omni integrations/timedoctor +
       workforce_brief; TimeDoctorUserMap).
   (d) **Biggest problems in Arun's emails** — the week's significant inbox matters (the daily pipeline).
   Then **DeepSeek** ties it into a long advisory narrative. Still eyes-only (CEO cc CFO), Sunday 07:00.
   (Current `ceo_sunday_driver.py` is the OLD claims-only board read — replace it.)

   **TONE = RAW (CFO directive 28-Jul, emphatic): "he should wake up after reading it, not see a nice
   picture."** Name names and be blunt: the consistent LATECOMERS, who DOESN'T WORK, which CLAIMS
   HANDLER is dead weight, which UNDERWRITER is dead weight, and where the ORGANISATION is slacking.
   No corporate softening. TWO hard guardrails so the rawness is bulletproof, NOT watered down:
   - **Every call-out is anchored to the number** (SLA-breach count + avg days open per claims handler;
     tracked-vs-target hours per person; lateness count; etc.). Blunt verdict + the evidence beside it.
   - **Exclude anyone on approved leave** from "not working / gone dark" — standing CFO rule
     ([[f-cfo-not-enforc]]); never flag legitimately-off staff.
   - Stick to PERFORMANCE facts only (hours, breaches, aging, lateness). NEVER protected characteristics,
     health, or gender ([[r-mth-feedba]] "never record gender-based"; TD titles=PII, not pulled).
   - Data sources per call-out: latecomers/not-working = Time Doctor daily snapshot (arrival times +
     tracked vs 6.5h/4h target); claims handler = Graphite claims SLA breaches + aging grouped by
     `claim_allocated_to`/handler; underwriter = best-effort UW signal (broker loss ratio / quote or
     endorsement turnaround / UW-linked complaints — confirm what UW perf data exists in Graphite/Aware).
3. **Stateful matters:** currently stateless (no cross-day "resolved" memory). The omni `ceo_monitor`
   app (models etc.) exists in branch `ceo-monitor-omni` (worktree), undeployed — deploy it if we want
   true resolved-tracking + a proper scheduled command to retire the host-cron.
4. Secret hygiene: ca983cff secret now on prod graph.env (SSM-placed). Rotate if concerned; update both
   graph.env and `prat-skill/secrets/manus-graph-sender.env`.
5. Optional: rename ca983cff was done ("Omni CEO automation"); could align omni's own app naming later.

## Deploy / run (for the AI)
- SSM: `aws ssm send-command --region af-south-1 --instance-ids i-02a5d76a61f4f09a5 --document-name AWS-RunShellScript` (profile default `claude-cli`). Base64 scripts to avoid quoting; engine must be `docker compose cp`'d INTO the backend container (host /tmp ≠ container /tmp).
- omni deploy: `sudo -u ubuntu git -C /opt/alpha-finance fetch/reset --hard origin/main` (git as ubuntu, not root) → `docker compose build backend` → `run --rm backend python manage.py check` → `up -d backend`.
- Driver runs under `manage.py shell` (shell_plus) which shadows builtins → drivers start with `from builtins import Exception, float, int, str, len, list`.
- Test the escalate endpoint / send with `Client(HTTP_HOST="omni.alphadirect.co.bw")` (default host → ALLOWED_HOSTS 400).

## Rules
- Eyes-only: brief goes ONLY to aiyer@ + cc pganesharajah@. Never widen recipients.
- PII: every prompt through `is_safe_for_ai()`; never send raw mail to an external model unfirewalled.
- Least privilege: read key scoped to the 2-mailbox group only; never grant Mail.ReadWrite or all-mailbox.
- Access grants (Mail.Read / consent / ApplicationAccessPolicy) are a human Global-Admin action — Claude cannot self-grant.
- Full detail lives in memory `p-ceo-mon.md` (+ `p-graph-app.md`).
