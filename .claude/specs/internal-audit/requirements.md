# Internal Audit Module — Requirements

Source: "Internal Audit Function — Build Reference for OMNI Platform" (Internal
Auditor, 24 Jul 2026). A full audit-management system (TeamMate+ equivalent),
built in the spec's phased order. This doc covers **Phase 1**.

## Scope — Phase 1 (this build)
Findings register (Module 5) + Follow-up tracking (Module 7) + Dashboard
(Module 10) — the originally requested dashboard, but on a real data source.

## Independence (non-negotiable — GIAS 2.1/2.2, 5.1/5.2)
- Internal Audit holds EXCLUSIVE create/edit/approve rights over audit content.
- CEO, COO, CFO and the Audit Committee / EXCO: VIEW-ONLY (issued content + dashboard).
- Platform/superuser: may READ for support; may NOT edit audit content.
- Enforced by an email-roster access layer, extendable without a deploy.

## Enforced controls (structural, not discipline)
1. A Finding cannot be saved without all five elements: criteria, condition,
   root cause, effect, rating (+ rating justification).
2. Condition must reference supporting evidence.
3. Root cause is a forced taxonomy; "human error" / "oversight" are not
   selectable. "Other" requires written justification.
4. Rating is auto-computed from Likelihood (1-5) x Impact (1-5); never typed.
5. A Finding cannot reach "agreed" without an agreed management response.
6. A follow-up cannot close as "Implemented" without evidence.
7. Overdue is derived (target date passed, not yet implemented) — never a manual flag.
8. Re-test cadence follows the rating: High/Critical quarterly, Medium semi-annual, Low annual.

## Dashboard tiles (all traceable to a source module)
Open findings by rating; open findings ageing (0-30/31-60/61-90/90+); overdue
follow-up %; open fraud-flagged; open regulatory (NBFIRA); audit plan completion.
Every tile labelled with its source module.

## Out of scope (later phases)
- Phase 2: Engagement planning + electronic workpapers (Modules 3, 4).
- Phase 3: Audit universe, Fraud register, QA gate (Modules 1, 8, 9).
