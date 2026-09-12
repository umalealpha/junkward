# Agent Portal × Graphite Aware — verification wiring (requirements)

**CFO brief (2026-07-07):** "in the backend we need to wire this to graphite aware
we created — plan the task."

## Problem
The commission module pays on what agents SUBMIT (pasted/uploaded rows). The SOP's
protection — "cross-check against the All-Policy list / paygate exports" — is still a
manual finance step. An agent could type `Activated` / `Approved` / a higher premium
and the engine would believe it. The company already owns the antidote: **Graphite
Aware's guarded read-only line into Graphite_live** (SELECT-only, PII-masked,
audit-logged) with the policy/KYC/claims lookups built.

## What "wired" means (user stories)
1. As finance, when a cycle's reports are in, I click **Verify against Graphite** and
   every commission line gets an independent verdict from the live policy system:
   policy exists · status really Activated · premium matches (±0.01) · KYC really
   approved · inception date matches (drives the conversion 3-month rule).
2. As finance, the Pay run shows a **Graphite** column per line: ✓ verified, or a
   plain mismatch reason ("Graphite says policy cancelled", "premium differs:
   submitted 99.00, Graphite 79.00", "not found in Graphite").
3. As the CFO, I cannot **Approve** a cycle that still has unresolved mismatches
   (subject to Decision D2 below), so nothing gets paid on unverified say-so.
4. Every verification run is logged (when, who, cycle, lines checked, mismatches).

## Explicitly OUT of scope (this task)
- No writes to Graphite, ever (read-replica, SELECT-only — inherits Aware's guards).
- No change to the SOP arithmetic — rates/gates stay exactly Motlatsi's. Graphite is
  a second witness, not a new judge (until D2 says otherwise).
- The /aware chat UI + its email whitelist are untouched — we reuse the CONNECTION
  layer (`aware.engine.run_select`), not the assistant.
- No personal data pulled: policy status/premium/dates/KYC flags only.

## Open decisions for the CFO
- **D1 — Scope of truth:** premium + status + KYC + inception from Graphite are
  Phase 1. Paygate ("client actually paid") depends on where RealPay/DPO truth
  lives (Phase 0 finding: omni's realpay app stores monthly reports + raw
  transaction payloads; Graphite may also hold receipts). Include paygate
  verification in Phase 3 once the best source is confirmed?
- **D2 — Mismatch behaviour:** Phase 1 default = FLAG ONLY (warning chips + banner);
  approving a cycle with mismatches requires ticking "I have reviewed the
  mismatches". Alternative = hard block. CFO to choose after seeing real mismatch
  rates on one cycle.
- **D3 — Liberty book:** UNI-prefix policies may not live in Graphite_live (MIS/
  DOMG/COMG confirmed; UNI unknown). If absent, Liberty streams stay manual-check
  and the UI says so honestly. Confirmed in Phase 0.

## Acceptance criteria
- Verify runs over a real cycle in < 60s for ~1,000 lines (batched IN queries).
- Zero PII columns in any verification SQL (reuses Aware's masking-safe fields).
- Unit tests: match, each mismatch type, policy-not-found, replica-down (graceful
  "verification unavailable", never blocks ingest), batching.
- Live proof: a seeded cycle with known-good + known-bad rows shows correct chips
  on the Pay run tab in production.
