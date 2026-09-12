# Requirements — Vendor Onboarding: Staff-Assisted Intake + Remote E-Sign

**Owner:** CFO (Prathap) · **Field owners:** Alana, Medu · **Date:** 2026-06-05
**Decision (CFO 2026-06-05):** e-sign mechanism = **in-house tokenized link** (data
stays in Botswana / DPA-clean; reuse existing signature + PDF + Graph email).

## Problem
Today `omni /health/vendor-onboarding` is a 9-step **self-service** wizard: the
doctor fills every field themselves and signs in-app, in one session. That is the
"hardship" we want to remove. We want a **two-phase** flow.

## Components

### Component 1 — Staff-assisted intake (we fill, the doctor does not)
- **R1.1** Authenticated Alpha staff (Alana / Medu / onboarding role) can create a
  `VendorOnboarding` record on a doctor's behalf and fill all fields, using the
  documents the staff already hold + the existing OCR/DeepSeek extract.
- **R1.2** Staff can **save as draft without a signature** (today submit *requires*
  `signature_data_url` — must change). Draft is editable.
- **R1.3** Staff can mark a completed record **"ready for signature."**
- **R1.4** A staff queue lists records by status (draft / ready / sent / viewed /
  signed / completed / expired).
- **AC1:** A doctor never has to type anything in phase 1; staff complete it end to
  end and the record persists with no signature.

### Component 2 — Remote e-sign via link
- **R2.1** From a "ready" record, staff generate a **single-use, expiring,
  unguessable** link and send it to the doctor's email (SMS optional later).
- **R2.2** The doctor opens the link with **no login**, sees a **read-only** summary
  of their prepared details + the AFA Network Agreement — **no form filling**.
- **R2.3** The doctor gives DPA consent and signs (canvas), then submits.
- **R2.4** On sign: build the agreement PDF (doctor signature applied), email AFA +
  cc the doctor, set status `signed → completed`, and record the e-sign audit
  (token id, IP, user-agent, timestamps, consent).
- **AC2:** The doctor's only action is review → consent → sign → done.

## Non-functional / compliance
- **R3.1** Token ≥128-bit entropy, single-use, expiring (default 14 days), revocable.
- **R3.2** Link carries the **token only — never PII**. Store the token **hashed**;
  the raw token exists only in the emailed link.
- **R3.3** Public sign endpoints are HTTPS-only + rate-limited.
- **R3.4** Retain DPA consent + a tamper-evident e-sign audit trail (Botswana
  Electronic Records (Evidence) Act / ECT admissibility). Simple electronic
  signature + audit trail is sufficient for a commercial vendor agreement.
- **R3.5** No regression to the existing self-service path (keep it working).

## Out of scope (this phase)
Qualified/advanced signatures, third-party e-sign providers, SMS delivery,
counter-signature workflow by AFA inside omni (AFA still counter-signs the PDF).
