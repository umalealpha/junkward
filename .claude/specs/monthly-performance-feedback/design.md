# Design — Monthly Manager Performance Feedback

**Reuse the existing spine. Do NOT invent a parallel performance model.**

## What already exists (verified on origin/main)
- `MonthlyCheckIn(AuditableMixin, BaseModel)` (hris/performance_feedback_models.py) — `unique_together(profile, period_month, period_year)` = one per report per month. `strengths`=did-well, `concerns`=not-well, `support_provided`+`improvement_actions`=improve, `objectives` JSON, `overall_rating`, escalation→warning→PIP, lock+`retention_until`. **"Manager gave feedback this month" == a MonthlyCheckIn row exists for that profile+month.**
- Manager→reports: `HRISProfile.manager` (FK payroll.Employee, related_name `direct_reports`). Prod-verified: Gosego→Medu, Kago/Pako→CFO.
- Perf API `/hris/api/performance/*` + `_perf_scope` (self/manager/full) + `_feature_off()` gate on `ELRA_PERF_ENABLED` (True on prod).
- `OmniTask` (core/models.py:1288): assigner/assignee=User, title, body, priority, status, due_at, `source` tag. Creating one to a manager auto-surfaces on `/tasks`, the my-tasks API, AND the morning brief (workforce_brief.pending_tasks) — **no new task UI needed**.
- Persisted decision-panel data: `WorkdayJustification.tracked_hours` + `.status=UNJUSTIFIED` (absence); `LeaveRequest` (leave; sick = `leave_type__code='sick'`); `OmniTask` (on-time computed). All nightly-safe.
- Auto-pull actual: health new-sales = `healthcare.HealthQuote` by `created_by`/`submitted_by`, status in {approved, invoiced}, month → `SUM(total_incl)`. Gosego = Health Insurance Associate → her example auto-pulls. Generic Graphite sales NOT mappable to staff yet → manual.

## New models (hris, migration 0041)
- **`PerformanceTarget`** — standing target from the JD. `profile`, `metric`, `target_value`, `unit`(BWP/count/%), `cadence`(monthly default), `source`(manual|health_quotes), `active`, `note`, `created_by`.
- **`PerformanceTargetResult`** — monthly outcome per target. `target`, `period_year`, `period_month`, `target_value` snapshot, `actual_value`, `achieved`, `source_used`, `note`, `checkin`(→MonthlyCheckIn, nullable), `recorded_by`. `unique(target, year, month)`. Powers trend + league + auto-pull cache.

## New backend
- `perf_target_source.py::pull_actual(target, year, month)` — health_quotes → SUM(total_incl); manual → None.
- `perf_panel.py::employee_month_panel(emp, year, month)` — {tracked_hours, absent_days, leave_days, sick_days, tasks_assigned/completed/on_time} from the persisted stores + target lines with pulled actuals + a 3-month rating/target-hit trend + a pre-filled feedback draft.
- Views `perf_monthly_views.py` (respect `_feature_off` + `_perf_scope`):
  - `GET /hris/api/performance/monthly/` — manager's reports, each with panel + targets(+actual) + this-month checkin status + trend + draft.
  - `GET /hris/api/performance/monthly/league/` — C-suite: per-manager reports-count vs feedback-given.
  - target CRUD (HR/full tier) + `POST .../monthly/<profile>/confirm-target/`.
  Feedback save reuses existing checkin create/PATCH.
- `management/commands/monthly_feedback_cycle.py` — idempotent; for each manager with reports missing this-month checkin → ONE HIGH OmniTask (source `monthly_feedback`, due +3 working days); refresh PerformanceTargetResult actuals. Called from `hris_daily_data_tasks` (fires once on the 1st working day).
- Exceptions report: add "Managers who have NOT logged monthly feedback" section → C-suite (`WORKFORCE_EXCEPTIONS_TO`).
- HR daily email (`hris_daily_data_tasks`): add "employees with no job description / target" chase line (replaces bank-detail asks).
- `seed_performance_targets` — seed Gosego = New sales / 30000 / BWP / health_quotes (the CFO's example).

## Frontend
- `/hris/monthly-feedback` — manager view: card per report (decision panel + target/actual/achieved + pre-filled 3 boxes + trend sparkline + save). League table for C-suite. Navy `#0D1B2A` / orange `#F4A623`, Emil-Kowalski motion.

## Compliance
ELRA evidentiary + lock + retention inherited from MonthlyCheckIn. Manager-tier scope. No customer PII externally; actuals are internal figures. Entity-scoped.
