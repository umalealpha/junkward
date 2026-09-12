# Taskboard + Reminder Engine — Design

## Stack (matches what Omni actually runs)
Django + PostgreSQL + DRF, Next.js frontend. `TIME_ZONE=Africa/Gaborone`,
`USE_TZ=True`. IMPORTANT: this repo has **no Celery worker** — scheduled jobs are
Django management commands run by cron on the EC2 (helpdesk_pending_reminder,
email_morning_report, ...). The due/overdue sweep follows that pattern
(`manage.py sweep_task_reminders`). No live-push worker yet: the frontend polls the
notifications endpoint (~30s); Channels can be added later if a worker is stood up.
Reference architecture: Plane — borrow its ideas, not its stack.

## Data model — BUILD ON THE EXISTING `core.OmniTask` (do NOT duplicate)
Omni already ships the task model. Reuse it; this app only adds what's missing.
- **`core.OmniTask`** (existing) — assigner, assignee, title, body, `due_at` (Date),
  priority, `status` (pending/in_progress/done/partial/blocked/cancelled),
  completed_at, seen_at. The mark-done flow sets `status=done` + `completed_at`.
- **`core.OmniTaskComment`** (existing) — task thread + status-transition comments.
- **`core.OnlinePresence`** (existing) — per-user heartbeat; reuse for Phase-3 check-in.
- **NEW `taskboard.Notification`** — recipient, task→OmniTask, type (assign_day/
  due_day/overdue), seen_at, acknowledged. Drives the force-modal.
- **NEW `taskboard.CompletionNote`** (OneToOne OmniTask) — body, interaction_seconds;
  constants `MIN_DWELL_SECONDS=30`, `MIN_NOTE_CHARS=60` (single source of truth).
Deferred to Phase 2: `carry_over_count` (add to OmniTask) + `meeting` FK.
Note: `OmniTask.due_at` is a DATE, so the due-day sweep is day-granular (fires on the
due date) — simpler than the 15-min tick and correct for a "due today" concept.
Not entity-scoped (internal ops tool, not financial postings).

## Reminder engine (the heart)
1. **Assign day** — a post_save signal on OmniTask makes ONE `Notification(assign_day)`
   on create (services.notify_on_assign, idempotent). It waits in the tray until the
   user's next poll. Assign-day = dismissible toast (anti-fatigue).
2. **Due day** — `manage.py sweep_task_reminders` (daily cron, Africa/Gaborone): for
   each task due today & not done with no open due_day notice, create
   `Notification(due_day)`. Frontend renders a **force-action modal**: `aria-modal=true`,
   focus-trap, NO close/X, NO Esc, NO click-outside. Re-shows next load until done.
   Overdue tasks → standing `overdue` notification, same modal.
3. **Complete gate** — `POST /tasks/{id}/complete` with {body, interaction_seconds}.
   Server rejects unless `interaction_seconds ≥ 30` AND `len(body) ≥ 60`. On pass:
   create CompletionNote, set state→default Completed state, stamp completed_at,
   acknowledge the notification. **Never trust the DOM** — the 30s countdown +
   char-min in the UI are UX; the server is the gate.

## API (DRF, `/api/v1/taskboard/`)
- `tasks/` CRUD (+ filters: assignee, state, due range, overdue).
- `tasks/{id}/complete/` (enforced gate above).
- `states/` list/config.
- `notifications/` list unseen + `notifications/{id}/ack/`.
- `reports/completion-rate/?from&to[&user]` → done ÷ assigned per person.

## Frontend (Next.js)
- **My Tasks** — own open tasks, overdue on top.
- **Manager/CFO view** — grouped by person, overdue red, completion-rate column
  vs ~90% benchmark, filters.
- **Force-action modal** — USWDS `data-force-action` pattern; due/overdue only.
- **Completion modal** — 30s disabled-confirm countdown + ≥60-char note.

## Phased task list
- [x] T1 `taskboard` app + models (Notification, CompletionNote on core.OmniTask) + migration + admin
- [~] T2 TaskStates — N/A: reuse core.OmniTask.status enum (no separate configurable state in Phase 1)
- [x] T3 DRF serializers + API views (my-tasks, notifications, ack) + URLs
- [x] T4 complete-gate endpoint + server-side dwell+char validation + unit tests (run in CI)
- [x] T5 due/overdue sweep via `manage.py sweep_task_reminders` (cron) + assign-day post_save hook
- [ ] T6 live push — DEFERRED: no Celery/Channels worker in this repo; frontend polls (~30s)
- [x] T7 completion-rate endpoint (self; manager view DPA-gated)
- [ ] T8 Next.js: My Tasks, Manager view, force-action modal, completion modal  ← NEXT
- [ ] T9 tests green in CI + browser smoke + deploy
- [ ] Legal: staff privacy notice + DPIA BEFORE go-live (separate track — drafting now)

## Guardrails
- CI invariant suite must stay green (this app touches no ledger/posting code).
- Force-modal reserved for due-day + overdue ONLY (NN/g: overuse breeds dismiss-
  on-instinct). All other notices dismissible.
- Completion gate validated server-side (edit-the-DOM cannot bypass).
