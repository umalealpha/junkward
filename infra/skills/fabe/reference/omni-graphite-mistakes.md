# Frequently-done mistakes â€” Omni + Graphite

The Fable 5.1 panel checks every change against this list. Each item is a real,
repeated failure from Alpha Direct history (memory-backed). A change that trips any
CRITICAL item is an automatic FAIL until fixed.

---

## CRITICAL â€” these have broken prod before

### C1. Model changed, migration missing
Django model/field changed but no matching migration in `*/migrations/`.
Prod crashes on deploy or serves stale schema.
**Check:** every `models.py` change has a numbered migration; run `makemigrations --check --dry-run` â†’ must say "No changes detected".

### C2. Migration shipped but backend only restarted, not rebuilt
Migration exists but deploy did `restart`/`up` on the OLD image â†’ migration never runs.
**Check:** migration changes MUST rebuild the backend image (`docker compose build backend`), not just restart. ([[feedback_rebuild_backend_image_on_migration_change]])

### C3. Frontend built with stale Docker cache
Frontend edited but built with cache â†’ OLD bundle served, change invisible.
**Check:** frontend rebuilds use `--no-cache`. ([[feedback_frontend_docker_build_cache]])

### C4. Frozen ADIC numbers touched
Revenue mapping / MA format / dashboard GWP tile changed. FROZEN:
FY25 GWP **125.15M** Â· PAT **0.292M**; FY26 9M GWP **96.18M** Â· PAT **0.950M** (BWP).
**Check:** if the diff touches revenue/GWP/MA/PAT logic or the dashboard GWP tile â†’ FAIL and defer to CFO (3Ã— yes rule). Never silently change. ([[feedback_revenue_format_frozen]])

### C5. Customer / policyholder PII exposed
Names, addresses, Omang/ID/passport, policy/bank numbers, health data going into
chat, an external model, a log, or an export un-anonymised. Org policy AD-POL-AI-GOV-001, not waivable.
**Check:** no real PII in code, fixtures, logs, or error messages. Graphite responses must respect role-gated PiiMask. **The off-subscription panel itself must NOT be sent real PII** â€” if the diff contains customer data rows, run Fable-only (see SKILL.md PII guard).

### C6. Posted journal entry / GL logic changed without sign-off
JE posting, GL account mapping, period close, or balances that must tie.
**Check:** if the diff posts/reverses journals or remaps GL accounts â†’ FAIL and defer to CFO. Outputs must balance; entry_date > today must be rejected ([[project_bug002_future_je]]).

---

## HIGH â€” correctness / data integrity

### H1. Deploy done wrong
- `git pull` as root/sudo on EC2 fails Instance Connect â†’ pull as **ubuntu**. ([[feedback_omni_deploy_pull_as_ubuntu]])
- "Built" â‰  "done". Must deploy + verify in the SAME session. ([[feedback_never_leave_pending]])
- Verify in the RUNNING app (real path, real result), not build-green. ([[feedback_prove_it_gate]])

### H2. Stale branch / clobbered parallel work
Shared checkout â€” a parallel session also pushes to `origin/main`.
**Check:** confirm behind-count before edit/deploy; land via worktree cherry-pick, **never rebase** the shared checkout. ([[project_alpha_finance_stale_branch_wip]])

### H3. Computed a value the source system already holds
Re-derived a field Odoo/Graphite already stores â†’ drift.
**Check:** confirm the source system doesn't already expose the field. ([[feedback_check_source_system_first]])

### H4. Graphite balance / join errors
- Debtor balance = Î£(Invoice) âˆ’ (Payments âˆ’ Reversals); aged buckets can be stale. ([[feedback_graphite_debtor_balance_method]])
- Premium audit join: TRANS PK = `policy_actions.id`. ([[project_portal_graphite_premium_audit]])
- Exceptions / RealPay recon join on `contractNumber`. ([[project_graphite_exceptions_module]])
- Refunds: 3 mechanisms (Cash / DPO / reversal) â€” don't assume one. ([[project_graphite_refund_model]])

### H5. Permission / viewset not locked down
New view/endpoint exposes data without the right permission class (e.g. `CanViewPayroll`).
**Check:** every data-exposing view has an explicit permission gate; approver-only controls enforced server-side (403), not just hidden in UI. ([[project_payroll_viewset_lockdown]], [[project_fm_approver_only_controls]])

### H6. Silent failure / swallowed error / bad fallback
`except: pass`, empty catch, or a fallback that hides a real failure and returns wrong data.
**Check:** errors handled explicitly; no silent swallow; fallback never masks a broken path.

### H7. Excess put on a claims PO
Claims POs carry the FULL amount; the customer pays the repairer the excess directly.
**Check:** no excess deducted on claims purchase orders. ([[feedback_excess_never_on_po]])

### H8. Hardcoded secret / key
AWS key, API key, password, token in source. History: Graphite key compromise.
**Check:** no secrets in code; env/secret-manager only. ([[security_graphite_key_compromise_2026_07_09]])

---

## MEDIUM â€” Karpathy discipline (the "makes mistakes" root cause)

### K1. Overcomplication
200 lines where 50 do. Speculative config/flexibility nobody asked for.
**Check:** would a senior engineer call this overcomplicated? Minimum code that solves the ask.

### K2. Non-surgical change
"Improved" adjacent code, reformatted, refactored things that weren't broken.
**Check:** every changed line traces to the request. Unrelated dead code is mentioned, not deleted.

### K3. Silent assumptions
Picked one interpretation of an ambiguous ask without surfacing it.
**Check:** assumptions stated; genuine ambiguity flagged, not guessed.

### K4. Weak success criteria
No test / no verifiable "done". "Make it work" instead of a check that passes.
**Check:** there is a concrete, runnable pass/fail. Bug fixes have a regression test.

### K5. Mutation where immutable was expected / N+1 queries
In-place mutation of shared objects; query inside a loop instead of a join/batch.
**Check:** immutable patterns; no obvious N+1.

---

## How the panel scores
- Any CRITICAL tripped â†’ **FAIL** (and C4/C5/C6 â†’ also defer to human).
- Any HIGH tripped â†’ **FAIL** unless the reviewer is confident it's a false positive.
- MEDIUM tripped â†’ **FIX-RECOMMENDED** (not an auto-block) â€” Fable decides.
- Nothing tripped, machine check green â†’ **PASS**.

## LEARNED (CFO-approved, auto-grown)

### L2 — Constant set drifted from the documented rule
**Severity:** HIGH. Proposed 2026-07-25.
A gate keyed off a category/status set (frozenset, choices, status list) silently excludes a member the docstrings, seeder or UI copy assume is in it, so the rule never fires and its dashboard tile is a guaranteed zero. Burned 2026-07-25: supplier_recon's claim-authorisation gate was inert across all 31 claim suppliers on prod because the category its own seeder assigns was missing from CLAIM_BACKED_CATEGORIES. Check: every 'X must Y' claim in a docstring has a test pinning the actual CONSTANT, not just the happy-path category.

### L6 — Control keyed on a resolver with a permissive default
**Severity:** HIGH. Proposed 2026-07-29.
A server-side gate compares against a value produced by a resolver whose last line is a catch-all default (return 'ADIC', or DEFAULT), so UNKNOWN INPUT PASSES THE CONTROL. Burned twice: the lntabeni 2026-07-24 entity-code bug, and the claims-are-ADIC-only rule 2026-07-29 (an unknown or misspelled entity resolved to ADIC and so satisfied the very check meant to stop it, and got stamped PAY/ADIC too). Check: any identity/entity/role check must require a POSITIVE match, never a substring match, and a test must pin that unresolvable input is REFUSED rather than defaulted through. Keep the naming resolver and the control resolver as SEPARATE functions so the default cannot leak back in.

### L12 — Fatal and transient errors swallowed by the same catch
**Severity:** MEDIUM. Proposed 2026-08-15.
An error-swallow added for transient dropouts (timeout, signal loss) also hides terminal failures (permission revoked, source dead), leaving a live Recording/Running UI over a dead feed. Any live-stream error swallow must branch on fatal codes and tell the user. Found by Fable 5 on the Click and Drive GPS fix, PR 670, 2026-08-15.

### L13 — Label / measurement drift
**Severity:** MEDIUM. Proposed 2026-08-17.
A UI relabel narrows or renames a metric without changing its computation, so the label misstates what the engine actually measures. Burned on the NBFIRA prudential page: the row was relabelled "Foreign bonds" while the engine still summed ALL non-BWP holdings — a false statement on a compliance monitor. Check: whenever either the label OR the calculation changes, verify the two still agree; a relabel is a claim about what the number is.

### L14 — dark: variants on a component in a light-themed app = dark-on-dark
**Severity:** MEDIUM. Proposed 2026-08-17 (CFO caught the task-reminder popup unreadable).
A component styled with Tailwind `dark:` variants flips on the VIEWER'S OS dark-mode (prefers-color-scheme), which is INDEPENDENT of Omni's own theme system (html.theme-professional/fun/heavenly). So on a machine in OS dark mode the card goes dark while any hardcoded light-scheme text colours (a fixed `#B42318` red, a `#6B7280` grey) stay put → unreadable dark-on-dark, even though the app itself is light. Check: a modal/toast/card either FULLY theme-adapts (bg AND every text colour switch together) or commits to ONE readable scheme; never a `dark:` background with light-scheme text. Read the actual rendered contrast, don't assume.

### L15 — An action button offered for a state the backend will reject
**Severity:** HIGH. Proposed 2026-08-17 (CFO: "if this is already signed off why is it asking me to sign off again").
A pending item shows an Approve/action button while a later state change has made the action impossible — the handler re-guards and just errors. Burned on a payroll addition: raised while the period was OPEN, the period was then signed off, and the queue still showed a live Approve next to a "period already signed off — reopen first" banner; clicking it only errored. Check: the row's `can_action` flag must gate on EVERY precondition the handler re-checks (period state, lock, window — not just permission/SoD), and when blocked, surface the REASON ("reopen the period first") instead of a dead button.

### L18 — Framework default variant bound to the OS, not the app theme
**Severity:** MEDIUM. Proposed 2026-08-17.
A UI framework's default variant (e.g. Tailwind v4 dark:) binds to the OS media query (prefers-color-scheme) unless explicitly re-scoped. Any app with an in-app theme switch MUST pin the variant to its own theme class (@custom-variant dark scoped to the theme class), or the user's OS setting silently overrides the chosen in-app theme. Burned 2026-08-17: dark: utilities fired on OS-dark even in the light Professional theme, showing dark panels the QC flagged. Found by Fable 5.

### L19 — External-feed identity matched by NAME instead of the confirmed id link
**Severity:** HIGH. Proposed 2026-08-27 (CFO, escalated: "~20th time, never fuck around with Modiri and Chris").
When a person's external-system display name differs from their HR/payroll name, any code that resolves them by fuzzy name (norm_name / token-subset on a payload `name` vs `employee.full_name`) silently returns 0/None — a false "0 hours / you're behind" email, a zero/absent attendance record (feeds leave docking), and wrong dashboard/coverage. Burned repeatedly on Time Doctor across FIVE commands: **Modiri Fofo Katai = TD "Modiri Mokati"** (worked 3.07h, emailed a "0 hours" nudge) and **Christopher Kelefatse = TD "Christopher Kelefatshe"** (one-letter surname), plus Arjun / Galaletseng / Phatsimo / Prathap. **Phatsimo's surname changed on MARRIAGE (HR "Ojang" → married "Moseki" in Time Doctor)** — names legitimately DRIFT over a life (marriage, spelling, middle names, "(ExCo)" tags, device labels), so a name is never a stable key; only the id is. The confirmed `TimeDoctorUserMap` (stable td_user_id) already links them — the defect is code IGNORING it and re-guessing by name. **Check:** resolve Time Doctor hours ONLY via `integrations.td_matching.hours_by_employee` / `TDMatcher` (confirmed td_user_id first; name/email only as the guarded unique-hit-both-ways fallback for accounts nobody has confirmed). NEVER write a bespoke name/token match on the snapshot `name`. An employee absent from the resolver = no matched account (caller supplies the default); a 0 is never asserted as fact for a name miss. Same class as L6 (permissive default) and the FNB-orphan false accusation (G15). Locked by `integrations.test_td_matching.HoursByEmployeeTests`.

### L23 — Query-string deep link read once on mount
**Severity:** MEDIUM. Proposed 2026-09-05.
A ?param read via window.location.search inside a []-dep effect or a useState initializer never re-fires on same-route client navigation (Next Link/router.push only swap searchParams), so a menu or palette entry differing from the current page only by query does nothing. Any href carrying ? on a route the user may already be on must key off useSearchParams(). Found 5-Sep-2026 in PR #757; payments/page.tsx ?type=receipt is the same class.

### L24 — Identity re-keyed but its inbound FKs left behind
**Severity:** HIGH. Proposed 2026-09-06.
When a person or entity gets a NEW primary record (re-hire, merge, re-import), every FK that points AT the old record (reports, approvers, Time Doctor maps, loans, incentive lines, documents) must be re-pointed or explicitly listed as staying with the old record. Test by asserting the old pk has zero inbound rows except history tables. Burned 2026-09-05: the first cut of the re-hire transfer left everyone who reported to the old record orphaned (Fable review, PR #758). CFO approved 2026-09-06.

### L25 — UTC-date-slice-for-local-day (local-midnight Date read as UTC)
**Severity:** HIGH. Proposed 2026-09-06.
A calendar-day Date built at local midnight (new Date(y,m,d), YYYY-MM-DD +T00:00:00, setDate(0), or a SheetJS cellDates import) then serialised with toISOString().slice(0,10) / .split(T)[0] shifts a FULL DAY early at every hour in any UTC+ zone (Botswana UTC+2); now does so between 00:00-02:00 local. Never serialise a shown/stored calendar date with toISOString; use localYmd()/addDaysYmd() from @/lib/utils. Exempt: export filenames, UTC-anchored date-only maths, Excel-serial to UTC conversion.

### L26 — Error swallowed inside an outer atomic() block silently rolls back the caller's save
**Severity:** HIGH. Proposed 2026-09-09.
A try/except Exception added as housekeeping-must-never-break-the-save runs INSIDE the caller's @transaction.atomic. A caught DatabaseError leaves the Postgres transaction aborted, so the outer block silently rolls back the very save the catch was protecting, with no error surfaced. CHECK: any swallow inside an atomic caller must open its own savepoint (with transaction.atomic()) inside the try, or move to transaction.on_commit. The test must inject a REAL database error, never a mocked Python exception - a mock does not abort the transaction and passes either way, proving nothing. Found 2026-09-09 on the manager-return task-close review (the feedback sibling avoided it only by luck of call placement). CFO approved 2026-09-09.

### L27 — ONE reader for a figure that several jobs and screens must agree on
**Severity:** HIGH. Proposed 2026-09-09.
When more than one job or screen answers the same question about a person ('how many hours did they work on day D'), they must all go through ONE reader, never each dig into the raw source with its own window and its own freshness. Four readers of Time Doctor hours disagreed on 9-Sep-2026: send_morning_brief read live and emailed 3.24h while send_daily_brief, reconcile_workday_records, enforce_td_deductions and the /my-omni tile read the frozen snapshot and showed/stored 1.74h — same person, same day. The employee saw both numbers and reported it. Fix: integrations.td_live.rows_for_day(day, snapshot_payload) is the single decision point (live first, snapshot fallback, and it REFUSES a live read whose total is below the stored total — aggregate() emits a row per roster user, so a 200 with an empty worklog is a full list of ZEROS that a truthiness check cannot detect and writing it would score the whole company at 0h). Anything that writes a record, docks leave, or shows a manager/employee a figure reads via that one function. Display-only readers still to migrate: send_weekly_hours_review, leave_excuse_service, send_saturday_explain, send_hours_reminder, reporting/cost_per_hour. CFO approved 2026-09-09.

### L28 — A machine may never LOWER a person's recorded figure from an external feed
**Severity:** HIGH. Proposed 2026-09-09.
Time Doctor only ever ADDS time to a past day (an offline machine uploading its buffer); it never subtracts. So a figure BELOW what is already recorded means an incomplete read, never less work. No cron/command may revise a person's recorded hours DOWNWARD from a feed read - refuse it, record the refusal, and escalate when it coincides with a deduction; a genuine reduction is a human, audited decision. Generalise beyond hours to any external-feed figure that accumulates. ALSO: before changing how a field is WRITTEN, list every scheduled job that REWRITES the same field afterwards (reconcile/backfill/sync/enforce) and prove the fix survives the next run of each - grep the field name across */management/commands and infra/cron/*.cron, and make the regression test run the follow-on job too. Burned 9-Sep-2026: the same employee reported the same lost hours TWICE (5dffc022 closed as resolved, then c82def7f). send_daily_brief was switched to a live read and reconcile_workday_records re-imposed the stale 06:30 snapshot 30 minutes later, every day, with a tidy AuditLog row; its guard protected STATUS but not HOURS. enforce_td_deductions read the same frozen snapshot and would dock a FULL UNPAID DAY off 0.00h while the record already held 3.20h. Two further staff were caught by the new rule within minutes of deploy. Locked by hris.tests.test_hours_never_go_down + EnforceTests.test_a_late_upload_the_snapshot_never_saw_stops_the_docking. CFO approved 2026-09-09.

### L29 — Best-so-far loop seeded with None treats a legitimate zero as absent
**Severity:** HIGH. Proposed 2026-09-09.
A conditional accumulator written 'if x > (best or 0)' never accepts the first value when that value is 0, so 'matched with 0' collapses into 'not found'. Burned 2026-09-09 on the Telegram hours lookup: a correctly-linked employee who tracked 0.00h was told they had no matched Time Doctor account and to confirm a link that was already fine. Check: any best-so-far loop starts from None and tests 'is None or ...'; a test pins the all-zero row.

### L30 — Sibling fields fetched by matching on the VALUE of the primary field, not the row identity
**Severity:** HIGH. Proposed 2026-09-09.
Picking 'the row whose hours equal the answer' returns a stranger's row whenever two people share a value, and 0.0 is the commonest shared value on a roster. Burned 2026-09-09: asking for one Christopher printed the other Christopher's productive percentage and last-seen under the first one's name. Check: presentation extras come from the row resolved by the same id key that produced the figure, never by re-matching on the figure itself.
