# Taskboard + Reminder Engine — Requirements

**Phase 1 of the meeting-discipline programme.** The backbone the Monday/Friday
meetings, the "I'm working" check-in, and the recording→action-items pipeline all
feed into.

## Plain summary (for the CFO)
An in-Omni task list, like Asana, that actually makes people finish things:
- You (or a meeting) assign a task to a person, with a deadline.
- On the **day it's assigned** they get **one** gentle alert — no nagging.
- On the **deadline day**, if it's still not done, a box pops up that **won't
  close** until they mark it done — no X, no Esc, no click-away.
- To mark it done they must **type what they did** (min ~60 characters) and the
  confirm button stays locked for **30 seconds** — no rubber-stamping. Checked on
  the server, so nobody can trick it.
- You get a dashboard: every person, their open tasks, overdue in red, and each
  person's **completion rate** (target ~90%).

## User stories
1. As a manager, I create/assign a task with owner + due date so work is tracked.
2. As an assignee, I get exactly one alert on assign day (no fatigue).
3. As an assignee, on the due date I get a non-dismissible modal until I complete
   or the day passes; overdue tasks re-show the modal daily.
4. As an assignee, marking done requires a real completion note (≥60 chars) and a
   30-second dwell — both enforced server-side.
5. As the CFO, I see per-person completion rate over any date range vs the ~90%
   benchmark, with overdue highlighted.
6. As the system, unfinished tasks carry forward (carry_over_count++) and escalate
   to Red after 2 misses (consumed by the Phase-2 meeting layer).

## Acceptance criteria (Phase-1 "done")
- A task can be created and assigned; assignee gets ONE assign-day notification.
- A due-day sweep raises a `due_day` notification; the frontend renders a
  force-action modal (no X / no Esc / no click-outside) that blocks until done.
- "Mark done" is rejected by the API unless `interaction_seconds ≥ 30` AND
  `len(note) ≥ 60`. On success the task flips to a Completed state, `completed_at`
  is stamped, and the notification is acknowledged.
- CFO dashboard shows completion rate per person.

## Legal gate (Botswana DPA 2024) — blocks GO-LIVE, not the build
Per-person completion rates + dwell-time = **employee monitoring / profiling**,
which the Data Protection Act No. 18 of 2024 treats as high-risk.
Before this ships to staff:
- Publish a **staff privacy notice** (what we track, why, lawful basis).
- Complete a **DPIA** (impact assessment); lawful basis = **legitimate interest /
  contractual necessity**, NOT employee consent.
- Data minimisation: keep only the note, timestamps, dwell seconds needed.
Fines up to BWP 50M / 4% turnover. Draft notice + DPIA are a separate deliverable.

## Non-goals (Phase 1)
Meeting agendas (Phase 2), IP check-in (Phase 3), recording pipeline (Phase 4).
The `Task.meeting` FK and `source=meeting` value are reserved for Phase 2.
