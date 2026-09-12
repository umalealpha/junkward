# Healthcare Vendor Onboarding — Tasks

## Backend (this session — code written, syntax-validated; NOT live-tested)
- [x] `healthcare/models.py` — `VendorOnboarding`
- [x] `healthcare/migrations/0001_initial.py` (hand-written; prod entrypoint runs `migrate`)
- [x] `healthcare/permissions.py` — `IsVendorOnboarder` (Ankete-only)
- [x] `healthcare/vendor_extract.py` — DeepSeek field extraction (reuses `deepseek_complete`)
- [x] `healthcare/agreement_text.txt` + `healthcare/agreement_pdf.py` (reportlab)
- [x] `healthcare/vendor_views.py` — extract + submit views
- [x] `alpha_finance/api_router.py` — register the two routes
- [x] `py_compile` all new modules

## Deploy phase (Manus runbook — needs prod MFA / EC2)
- [ ] Branch + commit; push; EC2 Instance Connect → `git pull`
- [ ] `docker compose build backend && up -d` (entrypoint runs `migrate` → applies 0001)
- [ ] Confirm `DEEPSEEK_API_KEY` present in `/etc/alpha-finance/.env` (already used by quick-quote)
- [ ] Set `VENDOR_ONBOARDING_ALLOWED_LOCALPARTS=ankete` (default already ankete)
- [ ] `manage.py check` green; health probe
- [ ] **Live test:** Ankete logs in via SSO → opens Vendor Onboarding → submits a
      test vendor → confirm `pending_review` row + agreement email lands at
      ankete@ + mtlagae@ (EXCO CC). Non-allowlisted user → 403.
- [ ] Browser smoke (Chrome MCP) of the Healthcare → Vendor Onboarding page

## Frontend (deploy phase)
- [ ] omni Healthcare → "Vendor Onboarding" React page (multi-step, calls the
      two endpoints); browser-smoke-tested on the live deploy.

## Verification honesty
Backend code is syntax-validated only. Live behaviour (DeepSeek call, Graph
email, SSO gate, migration apply) is verified on the EC2 during deploy — it
cannot be exercised from the dev Mac (no omni stack/DB/secrets here).
