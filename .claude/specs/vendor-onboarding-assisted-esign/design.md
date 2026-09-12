# Design — Vendor Onboarding: Staff-Assisted Intake + Remote E-Sign

Builds on the existing `healthcare/` app (model `VendorOnboarding`, views
`VendorFieldExtractView` + `VendorOnboardingSubmitView`, `agreement_pdf.build_agreement_pdf`,
Graph email) and the omni FE wizard `/health/vendor-onboarding`. Reuse, don't rebuild.

## Data model changes (`healthcare/models.py`)
`VendorOnboarding` — add:
- `status` choices: `draft | ready | sent | viewed | signed | completed | expired`
  (default `draft`).
- `prepared_by` FK → User (nullable) ; `prepared_at` datetime.
- existing `signature_data_url`, `submitted_by`, `agreement_email_sent` reused.

New model `VendorSignatureRequest`:
- `onboarding` FK → VendorOnboarding
- `token_hash` (sha256 of the raw token; raw never stored), `created_by` FK,
  `created_at`, `expires_at`, `revoked_at` (nullable)
- `sent_to_email`, `viewed_at`, `signed_at`, `used_at` (single-use guard)
- audit: `signer_ip`, `signer_user_agent`, `consent_accepted_at`

## Endpoints
**Staff (authenticated, existing auth):**
- `POST /api/v1/health/vendor-onboarding/draft/` — create/save draft (no signature).
- `PATCH /api/v1/health/vendor-onboarding/<ref>/` — update draft.
- `POST /api/v1/health/vendor-onboarding/<ref>/ready/` — mark ready.
- `POST /api/v1/health/vendor-onboarding/<ref>/send-signature/` — create
  `VendorSignatureRequest`, generate raw token, email the link, set status `sent`.
- `GET  /api/v1/health/vendor-onboarding/?status=` — staff queue.
- Keep `…/submit/` (self-service) AND `…/extract/` (OCR) unchanged.

**Public (NO auth, token-gated, rate-limited):**
- `GET  /api/v1/health/vendor-sign/<token>/` — validate token (exists, not expired,
  not used, not revoked) → return **read-only** prepared data + agreement text; set
  `viewed_at`, status `viewed`.
- `POST /api/v1/health/vendor-sign/<token>/` — body `{consent:true, signature_data_url}`
  → re-validate token → apply signature → `build_agreement_pdf` → email AFA + cc
  doctor → set `used_at`, `signed_at`, status `signed→completed`, write audit.

## Token mechanics
- `raw = secrets.token_urlsafe(32)` ; store `sha256(raw)` only.
- link = `https://omni.alphadirect.co.bw/vendor-sign/<raw>` (token only, no PII).
- Validation: constant-time hash compare; check `expires_at`, `used_at`, `revoked_at`.
- Single-use: set `used_at` atomically on successful sign.

## Frontend
- **Staff mode:** reuse the existing 9-step wizard component, parameterised:
  hide the doctor-signature step, add **Save Draft** + **Send for Signature** actions.
  Lives under the authenticated `(dashboard)/health/vendor-onboarding`.
- **Public sign page:** new route `app/vendor-sign/[token]/page.tsx` **outside** the
  `(dashboard)` auth layout. Read-only review + DPA consent + canvas signature +
  submit. Mobile-first.

## Security / compliance
- Token entropy ≥128-bit, hashed at rest, single-use, 14-day expiry, revocable.
- No PII in URL; HTTPS; rate-limit the two public endpoints (e.g. 10/min/IP).
- DPA consent text already exists in the FE; persist `consent_accepted_at`.
- Audit (IP/UA/timestamps/token) gives evidentiary weight under the Botswana
  Electronic Records (Evidence) Act.
- Self-service path untouched → no regression.

## Deploy
Backend = migration + rebuild (per CLAUDE.md rebuild-on-migration rule). FE =
`build frontend && up -d --no-deps frontend`. Public route must render without auth.
