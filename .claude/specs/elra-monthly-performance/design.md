# Spec — ELRA-2025 Monthly Performance Feedback (omni HRIS)

CFO directive 2026-06-25. Builds the omni-native version of the ELRA-2025
monthly performance-feedback trail (the prior gap analysis), reusing omni's
spine rather than the brief's standalone schema.

## Requirements
1. A monthly, light-touch performance check-in per employee that captures the
   ELRA evidentiary points: known standards (objectives), evidence, strengths,
   concerns, **support provided** (opportunity to improve), employee response +
   acknowledgement, dates, sign-offs.
2. Auto-escalation: ≥2 consecutive low months → `warning_recommended`; ≥3 →
   `pip_triggered` + a linked PIP record. Thresholds are CONFIGURABLE POLICY.
3. Evidentiary guard: a Below / Significantly-below rating MUST carry evidence +
   concerns (no undocumented low ratings).
4. Immutability: after manager + employee sign-off the record locks (addendum-only).
5. DPA-2024: every field is employee personal data → `retention_until` storage
   limit; entity-scoped + HRIS-gated access; immutable audit trail.

## Design (reuse omni's spine — do NOT rebuild)
- `MonthlyCheckIn(AuditableMixin, BaseModel)` + `PerformanceImprovementPlan(AuditableMixin, BaseModel)`
  in a sibling file `hris/performance_feedback_models.py`, re-exported from `hris/models.py`
  (omni's established pattern for new HR blocks).
- FK to **`HRISProfile`** (string ref `'hris.HRISProfile'` — no import cycle), mirroring
  `PerformanceReview`/`OKR`. Employee/company reached via `profile.employee.company`.
- Objectives + improvement actions as **JSON** (omni's competency/okr convention) — no child tables.
- Audit: **reuse `core.AuditLog` via `AuditableMixin`** — the brief's separate AuditLog is dropped.
- Access: **reuse** the HRIS whitelist + unlock (`_deny_if_not_whitelisted`) + entity scope
  (`apply_company_scope` on `profile__employee__company_id`, honouring the HRIS-006 clamp).
- **Feature flag `ELRA_PERF_ENABLED` (default False):** the whole API is DORMANT until a
  DPIA + counsel sign-off. No employee PII can be collected before that.

## Audit / regression notes
- No financial code touched (HR module) → financial invariants unaffected.
- New models + migration 0015 + new endpoints + 1 settings flag + 2 URL lines. No edits to
  existing models/contracts → no name collisions, no override of existing behaviour.
- Escalation creates a PIP idempotently (no duplicate while an open PIP exists).

## Out of scope this cycle (queued, flagged)
- The manager-facing UI form (frontend).
- Finer per-manager row scoping + the employee self-ack UI (v1 is HRIS-tier + entity scope).
- DPIA, counsel ELRA section-map, retention-value sign-off — gate go-live (flag stays off).
