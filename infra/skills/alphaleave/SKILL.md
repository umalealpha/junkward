---
name: alphaleave
description: >
  Alpha Direct's "Leave & Productive-Hours Accountability" system — the CANONICAL,
  current record of the whole initiative to stop leave banking up for people who
  aren't actually working (the problem that cost a Finance Manager to 20 days of
  ghost-leave + a short-notice exit, and drives leave-encashments by no-shows).
  Auto-load whenever Prathap types /alphaleave or /Alphaleave, or the task touches:
  the leave/productive-hours rule, the Excuses feed, the one-click "explain your
  day" page, docking leave for missed hours, the Saturday 4-hour rule, the daily
  8:30/4pm/5pm clock, or the Sept-2026 strict switch. Supersedes the older `leave`
  skill (same subject; this is the up-to-date one). Companion to `omni` (deploy)
  and `prat-skill` (dev stack). KEEP CURRENT STATE + PENDING updated as work lands.
---

# /alphaleave — Leave & Productive-Hours Accountability (omni)

**Talk to Prathap in plain English (layman). Real staff leave/pay is at stake here —
build with prat-test rigor, dock only when certain, never fake the appeal. Only hard-stop
for: moving money, changing access, deleting live data.** Lives in **omni**
(omni.alphadirect.co.bw). Load `omni` for deploy mechanics, `prat-skill` for the full stack.

## Why this exists (the business case — CFO 2026-07-22)
Leave accrues and gets **encashed by people who aren't coming to work**, then they give
short notice and leave on banked leave. Prathap lost an **FM who was absent 20+ days and
walked out on short notice because he still had leave**. This system makes "not working"
**burn leave down instead of banking it** — transparently, with the person's own explanation
on record, reversible only by a genuine appeal. CEO (Arun) approved 2026-07-22 ("Go for it").

## The settled rules
- **Daily target (Time Doctor PRODUCTIVE hours):** everyone **6.5h/day**; Paul, Unami,
  Arjun, Arun + Ex-Co **4.5h** (comment still required if missed).
- **Saturday = 4h** for all staff; the five (Arun, Arjun, Paul, Unami, CFO) are **off**
  Saturdays. A **missed Saturday = a half-day of leave** (CFO 2026-07-22 — half-day, not 4h).
- **Miss the hours → omni emails you next morning** → you **explain in ≥50 words** (worked
  office/off-site, or on leave) → **no explanation → leave auto-applied**; **appeal** reverses.
- Leave off the **annual balance** first; negative → **unpaid + HR alerted**.
- **Warm-up until 31 Aug 2026, strict from 1 Sep** — BUT the CFO has pulled enforcement
  forward for missed Saturdays now (with the appeal as the safety net).
- "Power cut at home" is NOT accepted (come to office / find a way to work).

## CURRENT STATE (2026-07-22)
**LIVE (built, deployed, tested):**
- **Excuses feed** `/hris/excuses` (CFO/exec/HR-gated) — each person's reason in their own
  words, power-cut watch-list flag, word panel. PR #415.
- **One-click "explain your day" page** — `GET/POST /api/leave-explain/<token>/` (MUST be
  under `/api/` — Caddy routes only /api/* to Django; a bare path 404s to the Next frontend).
  No-login, django-signing token = {employee_id, date}, 21-day expiry, CSRF-exempt (token is
  the gate), server-side escaped, ≥50-word gate. Stores `WorkdayJustification` (status
  EXPLAINED) → shows in the Excuses feed. PRs #417/#418.
- **`send_saturday_explain` command** — emails each no-hours (`--band zero`) or under-1h
  (`--band under1`) payroll staffer their per-person button; excludes the 5 Sat-off execs
  (name AND email), confirmed leavers, approved-leave. Dry-run default. PR #420.
- **SENT for Sat 18 Jul:** 28 (zero hours) + 9 (under an hour) = **37 staff** emailed the
  explain button. **NO leave applied yet.** (2 of "the 11" were outside contractors, not on
  AD leave — correctly excluded.)
- Leave-rule explainer consolidated into the ONE morning brief (PR #419). The general
  warm-up notice command `send_leave_policy_notice` exists (dry-run; 82 staff).

**PENDING — the actual docking engine (NOT built; must be right — real pay):**
1. **Apply command** — for a day, dock a **half-day** annual `LeaveRequest` to each
   **confirmed** no-show who didn't explain. omni's leave `days_calc` EXCLUDES Saturdays, so
   force `days=0.5` via a per-record `LeaveRequest.objects.filter(id=..).update(days=…)`
   (do NOT change the shared save()/compute_days — high blast radius). Leave balance is
   DERIVED from LeaveRequest.days, so create=dock, cancel=restore.
2. **Real appeal-reversal** — link the created LeaveRequest to the WorkdayJustification;
   an upheld appeal/late explanation CANCELS it → balance auto-restores. (Fable: today the
   appeal only flips a label — cosmetic. MUST fix before docking.)
3. **Confirmed-match ONLY** — dock via `TimeDoctorUserMap.confirmed` (snapshot payload
   carries `user_id`), never fuzzy name (mononyms / variant TD names / ambiguous → dock the
   wrong person). Snapshot payload member = {user_id, name, hours_tracked, …}.
4. **Snapshot-sanity guard** — ABORT the run if the day's snapshot is missing or coverage is
   below a threshold vs the roster (else a failed pull docks the whole company).
5. **Flip the all-staff "nothing is deducted" morning-brief copy** in the same release that
   starts docking (don't dock while the email says otherwise).
6. **ONE CFO summary email** — all responses + the leave applied, together (NOT per-response).
   Escape the explanation text in the HTML.
7. **Idempotent** — never double-book a day already on leave, never apply twice on re-run,
   only genuine non-responders.

**THE GATE TO DOCKING EVERYONE — identity confirmation:** only **7 staff have a confirmed
`TimeDoctorUserMap`**. So today only ~3 Saturday no-shows are safely dockable; ~81 eligible
are matched by fuzzy name only and CANNOT be safely docked (would hit someone who worked).
Close this via the **Who-Tracks panel** `/hris/tracking-setup` (HR ticks "this TD account =
this person"). Give HR the unconfirmed list; as each is confirmed the engine docks them.

## Fable-5 audit verdicts (2026-07-22) — the explain page/token are SECURE; three MUST-fix before any dock
(1) don't dock during the declared warm-up while staff were told "nothing is deducted";
(2) never dock on fuzzy match or a bad/partial Time Doctor day (confirmed-map + snapshot guard);
(3) make the appeal actually cancel the leave (it's cosmetic today). Also: token resubmission
can void a manager review (lock once responded/reviewed); ≥50-word gate is soft (rely on
manager review); leaked link lets B answer as A (accepted warm-up risk, tighten before live).

## Build lessons + landmines (hard-won)
- **DEPLOY: always `sudo -u ubuntu git fetch origin main` BEFORE `reset --hard origin/main`** —
  a stale ref silently deploys OLD code AND false-passes a verify (bit me twice).
- **Caddy routes only `/api/*` to Django** — public server-rendered pages go under /api/.
- **Frontend build swaps** (box RAM ~3.8G) → slow (~8min); backend-only deploys are quick.
- **Leavers are NOT reliably detectable in omni** — the `active` flag AND latest-payslip BOTH
  missed real leavers (Letsweletse Marumo, Milidzani Muzila had June payslips but had left).
  **HR (Unami/Dorothy) is the only reliable leaver source.** Don't dock/email off omni status.
- **Duplicate/shared-email employee records** (e.g. "Arjun Parameswaran" on arjuniyer@) →
  exclude execs by EMAIL as well as name; de-dupe recipients.
- **Metric is PRODUCTIVE hours, not total tracked** — the daily/morning brief + snapshot
  currently score `hours_tracked` (TOTAL); switch to productive before strict enforcement.

## Where it plugs in
`hris/` (WorkdayJustification, leave_balance/LeaveRequest, workforce.py rules, workforce_views
justify/excuses, morning_brief, send_daily_brief, leave_explain.py, send_saturday_explain).
`integrations/` (Time Doctor snapshot + `td_matching.TDMatcher` confirmed-map + timedoctor_recon).
Excuses/CFO view: `/hris/excuses`. Who-Tracks: `/hris/tracking-setup`.

## NEXT
Build the docking engine (items 1-7 above) with the Fable guards, TEST hard (dry-run +
single-record dock+reverse proof + snapshot-abort), deploy, and it docks confirmed no-shows
(this Saturday + daily), reversible by appeal, with the ONE CFO summary. In parallel drive
HR to confirm the 81 identities so enforcement becomes total. Related memory:
`p-leave-acctblty`, `p-workfo-daily`, `p-td-intg`.
