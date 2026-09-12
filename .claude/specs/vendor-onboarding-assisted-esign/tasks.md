# Tasks — Vendor Onboarding: Staff-Assisted Intake + Remote E-Sign

Order matters; each task ends "tested + verified" before the next. No "done" on
build-green alone (CFO rule). Spec-workflow: this spec is reviewed/approved before code.

## Backend
1. **Model + migration** — `VendorOnboarding.status / prepared_by / prepared_at`;
   new `VendorSignatureRequest`. Migration + rebuild backend.
2. **Draft path** — `draft/` create + `PATCH` update; relax submit so a record can
   persist WITHOUT `signature_data_url` when `status=draft/ready`. Keep self-service
   submit intact.
3. **Token util** — `secrets.token_urlsafe(32)`, sha256 store, constant-time verify,
   expiry/used/revoked checks. Unit-tested.
4. **Send-signature endpoint** — create request + raw token + Graph email with the
   link; status→`sent`. Email template (house HTML).
5. **Public GET sign endpoint** — token-gated read-only payload; set viewed.
6. **Public POST sign endpoint** — re-validate, apply signature, `build_agreement_pdf`,
   email AFA + cc doctor, finalize status, write audit. Single-use atomic.
7. **Rate-limit + throttle** the two public endpoints; HTTPS-only.

## Frontend
8. **Staff mode** in the existing wizard — hide signature step; add Save Draft +
   Send for Signature; show generated-link confirmation.
9. **Staff queue view** — list by status with actions (edit / send / resend / revoke).
10. **Public sign page** `app/vendor-sign/[token]/` outside `(dashboard)` — read-only
    review + consent + canvas signature + submit + success state. Mobile-first.

## Verify (each, with evidence)
11. Staff create→draft→ready→send: link emailed, token row created (hashed).
12. Open link in a clean session (no auth): read-only data renders, no form fields.
13. Sign → PDF generated with signature, AFA email sent, status=completed, audit row
    populated (IP/UA/timestamps).
14. Token re-use blocked; expired token blocked; revoked token blocked; tampered
    token 404.
15. Self-service path still works (regression).
16. Browser smoke (Chrome MCP) of staff mode + public sign page; screenshot + console.

## Rollout
17. Draft PR with this spec FIRST (approved) → implement → deploy (backend rebuild +
    FE no-deps) → verify on prod → brief Alana + Medu.
