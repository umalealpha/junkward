# Healthcare monthly summary + upload dedupe — design

## Backend (healthcare/upload_views.py)
- `HealthcareUploadDetailView.delete(pk)` — 403 unless `request.user.is_staff` or
  uploader; hard delete (totals live on the row; no related rows to cascade).
- `HealthcareSummaryView` (`GET /api/v1/health/summary/`) — single endpoint returning
  all three kinds so Claims can join Revenue months client-side:
  `values('kind','period_year','period_month').annotate(uploads=Count, lives/rows/gross/paid=Sum)`
  over PARSED uploads, ordered by year, month. `uploads > 1` = duplicate flag.
- Route added in `alpha_finance/api_router.py` (same `__import__` style as siblings).

## Frontend (frontend/src/app/(dashboard)/healthcare/_tracker.tsx)
- `SummaryPanel` renders per-kind monthly table + `YTD FY{n}` row (FY = Jul–Jun, named
  by ending year) + inception-to-date row. Derivations client-side:
  - revenue: parsed gross is the Incl.-VAT total (parser priority) → excl = gross/1.14.
  - claims: loss ratio = paid ÷ same-month revenue excl-VAT.
  - treaty: 90% QS columns = 0.9 × parsed totals; RI net = 0.9 × (premium − claims).
- Delete button (Trash2) per upload row → window.confirm → `DELETE /health/uploads/{id}/`
  via apiFetch (Bearer-safe) → refresh list + summary.
- Duplicate badge (amber "n uploads") on summary months with uploads > 1.

## Notes
- All API calls go through `apiFetch` (MSAL Bearer) — per feedback_msal_bearer_not_token.
- No model/migration changes.
