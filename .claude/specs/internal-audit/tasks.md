# Internal Audit Module — Tasks

## Phase 1 — DONE (this build, local only, not deployed)
- [x] `internal_audit` app: models, rating, access, permissions, serializers, views, admin
- [x] Independence access layer (editor/viewer rosters; superuser read-not-write)
- [x] Migration `0001_initial`
- [x] Wire settings INSTALLED_APPS + dedicated router in api_router.py
- [x] Profile serializer: `can_view_internal_audit` / `can_edit_internal_audit`
- [x] Frontend: layout guard, dashboard, findings register (+ create), follow-up
- [x] Sidebar module gated to viewers
- [x] 15 tests passing (enforcement + independence)

## Before go-live (when CFO approves deploy)
- [ ] Confirm the viewer roster with CFO (CEO/COO/CFO/board emails) + auditor roster
- [ ] `npm install` + `next build` type-check the frontend
- [ ] Browser smoke on prod: menu appears for auditor+execs, hidden for staff;
      create a finding as auditor; confirm CFO is view-only
- [ ] Deploy (SSM) — backend auto-migrates on start

## Phase 2 (next)
- [ ] Engagement planning memo + scope + work programme (Module 3)
- [ ] Electronic workpapers + evidence attachments (Module 4)
- [ ] Link finding evidence -> live omni records (the ERP-native advantage)

## Phase 3
- [ ] Audit universe + risk-based 3-year plan (Module 1)
- [ ] Fraud risk register incl. management-override question (Module 8)
- [ ] QA checklist gate on reporting + conflict-of-interest declaration (Module 9)
