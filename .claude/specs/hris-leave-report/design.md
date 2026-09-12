# HRIS-002 Leave Report — design

## Backend

One new function view `leave_report` in `hris/feature_views.py` (follows the
established feature-pack pattern: `@api_view(['GET'])` + `_gate()`), registered
in `hris/urls.py` as `api/leave-report/`.

```
GET /hris/api/leave-report/?company=<id|code>&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
                           &leave_type=annual,sick&department=<name>&employee=<uuid>
```

- Gate: `_gate(request, capability='view_team')` (whitelist + unlock + role).
- Scope: `view_all` → all HRISProfiles in company; else direct reports of the
  caller's Employee (+ self).
- Two aggregate passes over APPROVED LeaveRequests of the leave year, grouped
  in Python by (profile, lowercased type code): taken_before / taken_in.
- Per row computation per requirements.md semantics; floats rounded 1dp.
- Response:

```json
{
  "date_from": "...", "date_to": "...", "leave_year": 2026, "clamped": false,
  "rows": [{"employee_id", "employee_name", "department", "leave_type",
            "leave_type_code", "opening_balance", "accrued" /*|null*/,
            "taken", "closing_balance"}],
  "summary": {"headcount_active", "total_days_taken", "avg_days_per_employee"},
  "count": N
}
```

## Frontend

New page `frontend/src/app/(dashboard)/hris/leave/report/page.tsx`:
- Gates: `useHrisAccess()` redirect + `useHrisCan('view_team')` redirect.
- Filter bar card; leave-type chips (toggle, All); department select built from
  distinct departments in the unfiltered-by-department response; employee text
  search applied client-side.
- Summary cards ×3, then table grouped by employee with per-employee subtotal
  rows and a grand-total footer row.
- CSV export = client-side blob from visible rows (itw8 downloadCsv pattern).
- Edit `hris/leave/page.tsx`: header row gains a right-aligned "Leave Report"
  link guarded by `useHrisCan('view_team')`.

## Tests — `hris/tests/test_leave_report.py`

- Fixtures: company, 2 employees + HRISProfiles (one managed-by the other),
  annual + sick LeaveTypes, approved requests across two types in/before the
  period, superuser (report consumer) + plain employee user (denied), unlock
  via `UserProfile.hris_unlocked_until`.
- Asserts: math of opening/accrued/taken/closing for annual + sick; ess → 403;
  mgr sees only direct reports; APPROVED-only counting (pending excluded);
  company-scope param respected.
