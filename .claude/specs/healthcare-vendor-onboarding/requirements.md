# Healthcare Vendor Onboarding — Requirements

**Owner:** Alana + Medu (AD Healthcare). **Access:** Ankete only.
**Origin:** standalone PWA (`~/work/ad-healthcare-vendor-onboarding`) rebuilt
natively inside omni (alpha-finance) under the existing `healthcare` app, per
CFO/EXCO directive 2026-06-04.

## Goal
Replace the 17-page printed AFA/healthcare vendor intake with an omni-native,
OCR-assisted, human-confirmed onboarding flow that produces a structured vendor
record + a filled, branded **AFA Service Provider Network Agreement** PDF, and
emails the signed agreement to AFA.

## Functional requirements
1. **OCR-assist, human-confirms-everything.** OCR/AI may pre-fill fields; the
   user confirms each before submit. Nothing is silently committed.
2. **DeepSeek field extraction.** Reuse omni's existing `core.ai_assist.
   deepseek_complete` (already prod-configured for the health quick-quote) to
   parse OCR'd CIPA / company-extract text into structured fields. Graceful
   regex fallback when DeepSeek is unavailable.
3. **AFA Service Provider Network Agreement.** Capture the agreement blanks
   (trading name, representative, capacity, principal place, effective date,
   domicilia tel/email), present the FULL clause text, accept + sign.
4. **Email on sign-off.** On submit, generate the filled agreement PDF and email
   it via omni's Microsoft Graph backend (`core.notifications.
   send_html_with_cfo_cc`) to **ankete@alphadirect.co.bw + mtlagae@alphadirect.co.bw**
   (EXCO auto-CC'd by the helper). No SMTP — omni sends.
5. **Banking** is manual-only, never OCR; masked in UI + PDF.
6. **Persist** the vendor record (`healthcare.VendorOnboarding`) with status
   `pending_review`, consent version/time, signature, agreement email status.

## Non-functional / constraints
- **Access control:** portal endpoints restricted to Ankete's M365 identity via
  a permission class (allowlist of `@alphadirect.co.bw` local-parts), mirroring
  `core/hris_access.py`. Login uses the existing omni SSO — no new Azure app.
- **DPA (Botswana DPA No. 18 of 2024):** DeepSeek receives only OCR text and is a
  cross-border sub-processor — recorded in the DPA register; CFO accepted the
  cross-border transfer 2026-06-04. No PII in logs. Banking masked.
- **Deploy:** AWS omni EC2 (`i-02a5d76a61f4f09a5`, af-south-1), under
  `/api/v1/health/vendor-onboarding/…`, surfaced in the omni Healthcare section.
- Respect the 7 chain-integrity steering rules — this module touches NO financial
  chain (no GL/PO/payroll posting); it is an intake + document module only.
