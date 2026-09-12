# Internal Audit Module — Design (Phase 1)

## App
New Django app `internal_audit`. Models subclass core `(AuditableMixin, BaseModel)`
so every write emits an immutable AuditLog row with the acting user — the
tamper-evident trail behind the function's independence.

## Data model
- **Engagement** (stub, expands in Phase 2): reference (unique), title, type,
  status, lead_auditor, period.
- **Finding**: engagement FK; five elements (criteria, condition,
  evidence_reference, root_cause[forced choices], effect_category, effect_detail);
  likelihood, impact -> rating (auto in `save()`); rating_justification; fraud_flag
  (auto-true when effect=fraud); regulatory_tag + nbfira_reference; status. Rules
  in `clean()`.
- **ManagementResponse** (1:1 Finding): response, action, owner, target_date, agreed.
- **FollowUp** (many/Finding): status, evidence_reference, next_retest_date
  (defaults from rating), notes; `is_overdue` derived property.

## Access (independence layer) — `internal_audit/access.py`
Two email rosters, both env-extendable (`INTERNAL_AUDIT_EDITOR_EMAILS`,
`INTERNAL_AUDIT_VIEWER_EMAILS`):
- EDITORS: Internal Auditor (omogomotsi@). Full write. Superuser is NOT an editor.
- VIEWERS: CEO, COO, CFO, EXCO/board. Read-only.
DRF `InternalAuditAccess`: SAFE methods -> can_view; writes -> is_editor only.

## API — `/api/v1/internal-audit/...` (dedicated DRF router)
- `engagements/`, `findings/`, `responses/`, `followups/` (ModelViewSets;
  writes stamp audit_user).
- `dashboard/` (function view) — live KPIs from Findings + Follow-up; each tile
  carries its `source` module.

## Frontend — `/internal-audit` (Next.js App Router, `(dashboard)` group)
- `layout.tsx` route guard on `me.can_view_internal_audit`.
- `page.tsx` dashboard; `findings/` register + enforced create form (+ quick
  engagement create); `follow-up/` tracking.
- Sidebar: dedicated "Internal Audit" module, shown only when
  `me.can_view_internal_audit`. Edit controls gated on `me.can_edit_internal_audit`.
- Two computed flags added to the profile (`/me`) serializer.

## Verification
15 backend tests (rating bands, five-element enforcement, forced taxonomy,
response-before-agreed, follow-up evidence, derived overdue, and the four
independence outcomes: auditor 201 / CFO 403+read / superuser 403 / staff 403).
