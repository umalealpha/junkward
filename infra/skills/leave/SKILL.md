---
name: leave
description: >
  Alpha Direct omni "Leave & Productive-Hours Accountability" module — the full agreed
  design for auto-monitoring daily Time Doctor productive hours, collecting staff
  explanations for shortfalls, auto-applying leave when no explanation is given, and a
  weekly in-house AI (Ollama + DeepSeek) summary of excuses to the exec team. Auto-load
  whenever Prathap types /leave, or the task touches: leave auto-apply, productive-hours
  shortfall, the "Excuses feed", the daily 8:30/4pm/5pm shortfall clock, the Saturday
  4-hour rule, the Sunday excuse-summary email, or the Sep-2026 strict switch. Carries
  the settled rules so Prathap never has to re-explain. Companion to `omni` (the ERP
  quick-start) and `prat-skill` (full dev stack). Keep CURRENT STATE + OPEN ITEMS updated.
---

# /leave — Leave & Productive-Hours Accountability (omni)

**Talk to Prathap in plain English (he's a layman). Build the whole ask in one run; only
stop for the hard lines: moving money, changing access, deleting live data.** This module
lives inside **omni** (omni.alphadirect.co.bw) — load the `omni` skill for deploy/run
mechanics and `prat-skill` for the full dev stack.

## Why this exists
Service standards are slipping. Many staff take time off / don't cover their hours without
ever applying for leave. This module makes the **system** catch it (not managers policing by
hand) and — crucially for Prathap — **collects staff explanations as a dataset** so he can
see *why* people aren't working and hold them to account over time
(e.g. "you logged ABC-client visits daily — why did none convert to business?").

## The settled rules (agreed 2026-07-21)

### Daily productive-hours target (Time Doctor)
- **Everyone: 6.5 productive hours/day.**
- **Paul Beka, Unami Butale, Arjun Iyer, Arun Iyer + Ex-Co: 4.5 hours/day.** (They must still
  write a comment if they miss 4.5h — Ex-Co is NOT exempt from explaining.)
- **Saturday = 4 hours** for all general staff. **The five — Arun, Arjun, Paul, Unami and
  Prathap — are OFF on Saturdays.** Everyone else works Saturday.
- **Pure hourly accumulation.** Miss X hours → X hours of leave. No quarter/half/full-day
  banding. (The earlier "under 1 hour Saturday = half day" idea was dropped in favour of
  straight hourly.)
- **No grace zone** on the hours themselves — even 30 minutes short counts, *unless the
  person explains it.*

### The daily clock (always about the PREVIOUS working day)
- **8:30 a.m.** — email to anyone who missed their hours yesterday: "you missed X hours."
- **Explain button** in omni → the person writes **at least 50 words** on why.
- **4:00 p.m.** — reminder if they haven't explained.
- **5:00 p.m.** — **no explanation → leave auto-applied (in hours). Silence is never a free
  pass.**
- Saturday shortfalls are emailed **Monday morning**, never Sunday.
- An **explanation routes to the person's line manager's queue**, reviewed **weekly on
  Mondays** (one digest — a manager with 15 reports must NOT get daily mail). Manager accepts
  → leave reversed; rejects → leave stands.
- The advance "I won't be working on [date]" pre-notification feature already in omni feeds
  straight in.

### The money
- Leave-hours come off the **annual leave balance** first (paid while balance lasts).
- Balance tips **negative → turns unpaid, HR alerted the same day**, signalling the person may
  no longer be needed — with a conversation *before* they hit zero.
- Unpaid = salary deduction; annual-leave balance is the mechanism, negative = the red line.

### Phasing (start slow — "can't be a Hitler at the start")
- **Now → 31 Aug 2026 (warm-up):** the whole machine runs — emails, Excuses feed, manager
  sign-off, AI summary — **but no actual leave/pay is deducted** (warn-and-collect; confirm
  with Prathap before flipping deductions on).
- **From 1 Sep 2026 (strict):** leave actually applies and bites.

### The "Excuses feed" (Prathap's primary interest)
A screen for Prathap + Unami (and optionally each manager for their own team):
- Who missed hours, how many, and **their reason in their own words**.
- A **watch-list** auto-flags excuses Prathap rejects — **"power cut at home" lights up**,
  because the rule is *come to the office or find a way to work*. That's the biggest lie and
  must be flagged on sight.
- A **most-used-words / theme panel** so common excuses surface across the company.
- **Filter by person** to read one employee's whole run before a conversation.

### Weekly AI summary (Sunday 06:00)
- **Ollama + DeepSeek running LOCALLY / in-house** reads the whole week's explanations — **no
  staff answers leave Alpha Direct.**
- Writes a plain-English summary emailed to **Paul, Arun, Unami, Arjun**: excuses grouped
  **by department**, common themes, watch-list hits by name, worst team/day.
- **Fallback if local can't run: DeepSeek CLOUD only.** **NOT Gemini** — Gemini is banned in
  Alpha Direct production (Prathap's own vendor rule). DeepSeek cloud chosen because it's the
  same engine already run in-app as "Aria". The email must ALWAYS fire — that's why a cloud
  safety-net exists at all.

### Fairness catches (must be built in)
- Nothing fires on Sundays, public holidays, approved annual/sick leave, company shutdowns,
  or offsite/training days.
- Approved **half-day** → that day's target halves.
- Rule only applies to people with a **live Time Doctor account**. No TD → email says install
  it + raise an IT ticket, with **one day's grace, one-time only** (can't be claimed again).
- Untracked seniors (marked "don't track") are excluded.

## Recipients (verified from prat-skill/reference/omni-staff-directory.md — never guess)
- Unami Butale `ubutale@alphadirect.co.bw`
- Dorothy K. Ikgopoleng (HR Manager) `dikgopoleng@alphadirect.co.bw`
- Paul Beka `pbeka@alphadirect.co.bw`
- Arjun Iyer (COO — distinct from Arun Iyer / CEO `aiyer@`) `arjuniyer@alphadirect.co.bw`
- Arun Iyer (Sunday-summary recipient + can override/reverse leave) `aiyer@alphadirect.co.bw`

## Where it plugs into omni
- Productive-hours data: the **`integrations`** app (Time Doctor → omni; see memory
  `p-td-intg`, `p-workfo-daily`). Shared matcher
  `integrations/td_matching.py`; 6.5h weekday / 4h Sat already modelled there.
- Leave balances / apply flow: the **`hris`** app (`hris.leave_balance`, apply_leave,
  half-day, opening-balance, encashment).
- Reuse the morning-brief cron pattern (06:50 staff / 07:00 manager) for the daily clock and
  the Sunday 06:00 summary.

## CURRENT STATE (2026-07-22) — SAFE SLICE LIVE
- **PR #415 merged + DEPLOYED to prod** (origin/main `25ba845d`; images rebuilt, backend+frontend
  healthy, `manage.py check` clean, no migration). Warm-up only — **NO teeth, NO new staff emails.**
- **LIVE now:**
  - **Excuses feed** `/hris/excuses` — read-only, gated CFO/exec/HR (`_can_see_excuses` in
    `hris/workforce_views.py`); `GET /api/v1/timedoctor/excuses/`. Verified as CFO = 200, as a normal
    staffer (Patience) = 403. Shows each person's reason in their own words, watch-list auto-flag
    (`flag_excuse`), most-used-words panel, per-person filter, warm-up banner. Sidebar + command-palette
    links added. **Currently EMPTY and that is correct** — the only recent days were non-working
    (Sat 18, Sun, + Mon 20/Tue 21 public holidays); it fills from the first real weekday brief (Wed 22,
    processed Thu). Short days land as `unjustified` (in the filter); explained → `explained`.
  - **`hris/leave_accountability.py`** (+6 tests) now committed/deployed — the pure rules the feed uses.
  - **Rule explainer lives in the ONE morning brief** (PRs #416 then #419, prod `dc8e6c31`): the "How this
    works" block ("nothing is deducted … you can appeal", flips to enforcement copy at 1 Sep via
    `leave_accountability.enforcement_active`) is in **`build_morning_html`** (the 06:50 email, PRODUCTIVE
    hours). Verified live-rendered. **CFO 2026-07-22: staff get ONE Omni morning email, not two, and NO
    separate mass-mail** — the standalone `send_leave_policy_notice` command was REMOVED (#419).
  - **07:10 daily brief EMAIL silenced** — cron `/etc/cron.d/workforce-daily-brief` now runs
    `send_daily_brief --no-email` (still STORES the WorkdayJustification rows that feed the Excuses feed;
    just no second email). Backup of the old cron line in `/etc/alpha-finance/cron-backups/`. `build_brief_html`
    still carries its own explainer as a dormant fallback if that email is ever re-enabled.
    NOTE: two staff morning emails remain distinct systems — 06:50 morning brief (productive, KEPT) and the
    now-silent 07:10 daily brief (total-hours, storage only). Productive-vs-total rescoring of the STORED rows
    is still the fast-follow before teeth.
- **Decisions locked (CFO 2026-07-22):** go-live comms = **notice first, then daily emails**; auto-apply
  leave + **appeal to reverse** (employee → manager approves → then CFO **or** HR (Unami/Arun) signs off →
  reversed; sits in task manager). On a dispute, keep the leave recorded (dedupe: never double-book a day
  the person already has leave for) — reverse only on sign-off. CFO's own line: paid-leave reversal by
  appeal is fine; the **unpaid** step (real wage docking) needs a human approve-before — parked for 1 Sep.
- Built in worktree `C:\Users\PrathapAsus\work\af-leave-acct` (branch `feat/leave-accountability`).

## NEXT (fast-follow — none needed before 1 Sep, so no rush tonight)
1. **Appeal → manager → CFO/HR sign-off chain.** Reuse the LeaveEncashment staged pattern
   (`core/approvals_views.py`, `hris/leave_encash_notify.py`) + a small `WorkdayAppeal` model + migration
   (hand-trim like encashment 0043 for the known hris drift). Appeal button on `/hris/my-brief`.
2. **PRODUCTIVE-not-TOTAL rescoring** + the Fable CRIT fixes (array-position attribution, `_tracked_lookup`
   bypassing TDMatcher, empty-pull circuit-breaker) — **all blockers before the auto-leave teeth turn on.**
3. The 8:30/4pm/5pm daily clock + 5pm auto-apply-leave command (teeth), gated by `enforcement_active`.
4. The Sunday weekly AI summary (local Ollama+DeepSeek; DeepSeek-cloud fallback; never Gemini).
- **Heads-up carried to CFO:** the existing daily/morning brief is ALREADY emailing staff live and
  scores TOTAL (not productive) hours with the known bug — recommended holding automatic staff
  shortfall emails until productive-hours is verified; CFO aware.

## OLD CURRENT STATE (2026-07-21)
- Design SETTLED (this file). Build STARTED, NOT deployed — Prathap said build, don't
  deploy.
- Feedback email sent to Unami, Dorothy, Paul, Arjun — **suggestions due Monday 11:00
  (2026-07-27)**; otherwise proceed as specified.
- Backdating note: "start from last Saturday" = Sat 18 Jul. Mon 20 + Tue 21 were public
  holidays (no expectation). First real weekday test = Wed 22 Jul.

- **BIG FINDING — the backbone already exists** (from the CFO's 2026-07-14 Workforce Brief
  directive). So this is an EXTENSION, not a greenfield build:
  - `hris/workforce.py` — pure rules: 6.5h weekday / 4h Sat / 0 Sun, public-holiday
    handling, `shortfall_hours()`, `classify_day()` (met/justified/unjustified). Matches our
    settled targets already.
  - `hris/models.py` `WorkdayJustification` — per-employee-per-day required/tracked/justified
    hours + the employee's **explanation text** + reason + status (incl. `PENDING` "awaiting
    employee response" and `EXPLAINED` "pending manager review") + `reviewed_by/at/note` +
    `linked_leave`. The daily explain + weekly manager sign-off ALREADY works.
  - `WorkforceBriefSetting`, `TrackingDirective` (who-tracks), TD daily snapshot in
    `integrations` (migration 0003), the daily-brief/exceptions crons in
    `hris/management/commands/` (send_daily_brief, send_exceptions_report, workforce_hours_report).
  - So the NEW work is only: (a) the hard 8:30/4pm/5pm clock with **5pm auto-apply LEAVE**;
    (b) hourly shortfall→leave off annual balance, negative→unpaid+HR; (c) the CFO
    **Excuses feed** (view over WorkdayJustification.justification) with the power-cut
    **watch-list** + word/theme panel; (d) the **Sunday AI summary** (local Ollama+DeepSeek,
    DeepSeek-cloud fallback); (e) the warm-up→1-Sep strict gate.
- **BUILT so far (verified, not deployed):** `hris/leave_accountability.py` — pure logic for
  hourly shortfall→leave, the 1-Sep enforcement gate, the power-cut watch-list flagger
  (office-exception aware), and word-frequency for the Excuses feed. Tests in
  `hris/tests/test_leave_accountability.py` — **6/6 pass** (standalone, no DB).
- **NEXT:** build the Excuses-feed view/page first (deploy-safe, read-only, it's what
  Prathap most wants to see) — hold the auto-leave teeth until Monday feedback lands so we
  don't churn on rules the four reviewers may change.

## OPEN ITEMS
0. **PRODUCTIVE hours, not total (CFO 2026-07-21).** The target is Time Doctor **productive**
   hours. The current snapshot/brief use `hours_tracked` (TOTAL). Before the teeth go on,
   pull/store PRODUCTIVE hours and measure the shortfall on that.
0b. **Never fire auto-leave on stale/missing data (lesson from the 2026-07-21 brief bug).**
   The daily brief was mis-timed to run BEFORE the Time Doctor pull, so it showed everyone
   0h/"awaiting data" — and Motlatsi (who worked) got a false "0". Auto-leave MUST only run
   AFTER that day's pull has landed, and must treat "no snapshot yet" as *do nothing*, never
   as a zero-hours shortfall. See memory `p-workfo-daily`.
0c. **FABLE AUDIT 2026-07-21 — MUST-FIX before the auto-leave teeth go on (full detail in
   memory `p-workfo-daily`). These pre-date /leave but the teeth would dock
   pay on this data, so they are blockers:**
   - **(CRIT) Productivity attributed by array position** — `integrations/timedoctor.py::aggregate`
     maps timeuse buckets to users by list order; a missing/reordered bucket credits one
     person's productive hours to another. Verify `len(timeuse)==len(ids)` on a live pull;
     fail/skip attribution if not.
   - **(CRIT) `send_daily_brief._tracked_lookup` bypasses the confirmed `TDMatcher`** and can
     merge two TD accounts' hours or credit a contractor's hours to a same-token employee →
     wrong `WorkdayJustification` rows (the auto-leave input). Rebuild the lookup on
     TDMatcher uid→employee links + per-uid snapshot hours.
   - **(CRIT) Rows score TOTAL tracked, not PRODUCTIVE** (CFO wants productive). Settle the
     metric ONCE in `hris/workforce.py`; add `productive_hours` to WorkdayJustification.
   - **(CRIT) Empty/partial pull stored as real zeros; no breaker in send_daily_brief** →
     mass false "please justify". Add a circuit-breaker + refuse to overwrite a good snapshot
     with a collapsed one.
   - (HIGH) UTC-vs-SAST day boundary in `pull_timedoctor` (evening work lands on the wrong
     day); pull failure is silent; on-leave exclusion keyed by NAME with duplicate names.
   - (MED) half-day leave fully justifies a whole day; days stored UNJUSTIFIED immediately —
     **auto-leave must NEVER consume a row whose 14-day response window is still open and
     `responded_at` is null.**
1. Confirm warm-up (Jul–Aug) is warn-and-collect with **no** real deduction until 1 Sep.
2. Manager mapping: use omni reporting lines; flag anyone with no line manager set.
3. Server capacity: can the omni EC2 run Ollama+DeepSeek, or does the local job run on the
   boardroom Mac? (Cloud DeepSeek is only the fallback.)
4. Incorporate Monday-11:00 feedback from the four reviewers before flipping anything on.
