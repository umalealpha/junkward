# Healthcare Vendor Onboarding — Design

## Integration points (verified in repo 2026-06-04)
| Need | Use | Location |
|---|---|---|
| AI extraction | `deepseek_complete(user_prompt, system_prompt, response_format='json_object', timeout)` + `DeepSeekUnavailable` | `core/ai_assist.py:141` |
| Email (Graph) | `send_html_with_cfo_cc(subject, html, to, attachments=[(fn, bytes, mime)], cc=...)` — auto-CCs `MANDATORY_CFO_CC` (excoboard@) | `core/notifications.py:165` |
| PDF | `reportlab>=4.0.0` | requirements.txt |
| Access gate | allowlist of `@alphadirect.co.bw` local-parts | mirror `core/hris_access.py` |
| Route registration | `__import__('healthcare.x', fromlist=[...]).View.as_view()` | `alpha_finance/api_router.py:444` |

## Components (all under `healthcare/`)
- **models.py** → `VendorOnboarding` (first model in the app → migration `0001`).
  Fields: reference_number(unique), entity (company_name, registration_number,
  registration_date, registered_address, tin, vat_number), directors(JSON),
  practitioner (name, council_type, council_registration_number, discipline,
  practice_address), banking (bank_name, branch_name, branch_code,
  account_holder, account_number), services (service_category, services_offered),
  agreement (trading_name, representative_name, representative_capacity,
  principal_place_of_business, effective_date, contact_tel, contact_email,
  agreement_accepted, agreement_accepted_at), consent (consent_version,
  consent_at), declaration (signatory_full_name, signed_at, signature_data_url),
  status, submitted_by(FK user, null), agreement_email_sent, agreement_emailed_to,
  deepseek_used, payload(JSON), created_at.
- **permissions.py** → `IsVendorOnboarder` (Ankete-only allowlist; superuser ok).
- **vendor_extract.py** → `extract_vendor_fields(text, doc_type)` via DeepSeek;
  strict-JSON `{fields:[{path,value,confidence}]}`; never fabricates; regex
  fallback. PII note: only OCR text is sent.
- **agreement_text.txt** → full verbatim agreement (copied from the PWA; single
  source). **agreement_pdf.py** → `build_agreement_pdf(record) -> bytes` via
  reportlab (AFA maroon/orange headings, filled tokens, signature image,
  Schedule A).
- **vendor_views.py** →
  - `VendorFieldExtractView` POST (file|raw_text + doc_type) → DeepSeek fields.
  - `VendorOnboardingSubmitView` POST (payload JSON) → validate → persist →
    build agreement PDF → `send_html_with_cfo_cc(..., to=[ankete, mtlagae],
    attachments=[agreement.pdf])` → return `{reference_number}`.
  Both `permission_classes=[IsAuthenticated, IsVendorOnboarder]`.
- **api_router.py** → register `health/vendor-onboarding/extract/` and
  `health/vendor-onboarding/submit/`.

## Frontend (deploy phase)
Add an omni Healthcare → "Vendor Onboarding" page calling the two endpoints;
multi-step form mirroring the PWA. Built + browser-smoke-tested on deploy per
`post-deploy-checklist.md` (cannot be verified in this dev box without the omni
stack).

## Out of scope (this module)
No GL/PO/payroll posting; no financial-chain writes. Pure intake + document.
