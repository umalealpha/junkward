# Agent Portal × Graphite Aware — design + phased plan

## Architecture (reuse, don't rebuild)
```
agent_portal (commission lines)
      │  policy_refs per cycle
      ▼
agent_portal/graphite_check.py       ← NEW: deterministic verification service
      │  batched SELECTs (no LLM, no chat, no whitelist)
      ▼
aware.engine.run_select()            ← EXISTING: guarded read-only replica line
      ▼                                 (SELECT-only gate, LIMIT, PII mask,
Graphite_live read replica              audit-logged)
```
- The LLM/agentic path in `aware.engine` is NOT used — verification is fixed SQL
  against known tables (`policies`, `v_policy_kyc_status`), chunked `IN (...)`
  lookups of the cycle's policy numbers.
- `/aware` access whitelist (`aware/access.py`) does NOT gate this — that list
  protects the chat UI. The verification endpoint lives under agent-portal auth.
  (Flagged explicitly so nobody assumes the whitelist applies.)

## Data model (additive only — no changes to existing rows)
- `CommissionLine` + three fields (migration 0005, all nullable):
  `graphite_status` (ok / mismatch / not_found / unavailable / skipped),
  `graphite_note` (plain reason, ≤200), `graphite_checked_at`.
- NEW `VerificationRun`: cycle FK, run_by, started/finished, lines_checked,
  ok_count, mismatch_count, not_found_count — the audit row per click.

## Verification rules (per line, from Graphite)
| Check | Source field | Mismatch note example |
|---|---|---|
| Policy exists | policies.policyNumber | "not found in Graphite" |
| Status Activated | policies.status = 1 | "Graphite says policy not active" |
| Premium matches | policies.premium ±0.01 | "premium differs: submitted 99.00, Graphite 79.00" |
| KYC approved | v_policy_kyc_status | "Graphite KYC: pending" |
| Inception (conversion streams) | policies.created_at | "Graphite inception 2026-05-20 — inside 3 months" |
Streams without a policy number (incentives) → `skipped`. Replica unreachable →
`unavailable` (ingest/pay-run never crash on it).

## Phases (each gated — prat-test style)
- **Phase 0 — Discovery (read-only, no code on prod).** On the replica via the
  existing engine: (a) confirm field semantics for a sample of REAL policy numbers
  from Motlatsi's July extract; (b) do UNI/Liberty policies exist? (D3);
  (c) premium field vs her tool's Premium column (monthly vs annual freq);
  (d) inspect one realpay `raw_payload` to judge the paygate source (D1).
  → Verify gate: a one-page findings note; field mapping frozen.
- **Phase 1 — Verification service + storage.** `graphite_check.py` (batched,
  deterministic), migration 0005, `VerificationRun`; unit tests incl. fake-cursor
  mismatch matrix. → Gate: 23-test suite + new tests green; `manage.py check` clean.
- **Phase 2 — Wire the flow + UI.** `POST /cycles/{id}/verify-graphite/` endpoint +
  "Verify against Graphite" button on Pay run; Graphite chip column on
  approved/rejected tables; banner "X mismatches — review before approving";
  approve gate per D2 (default: reviewed-checkbox). → Gate: live cycle on prod
  seeded with known-good/bad rows shows correct chips (screenshots).
- **Phase 3 — Paygate cross-check (after D1).** Verify "client paid ≥ premium"
  against the confirmed source (realpay raw payloads or Graphite receipts) for
  RealPay-sourced rows; DPO source TBD. → Gate: same evidence pattern.
- **Phase 4 — Hardening.** Auto-verify on cycle-approve attempt if stale; nightly
  re-verify of open cycles (cron mgmt command, same pattern as sweep jobs);
  memory + runbook update.

## Risks / honest unknowns
- **Liberty (UNI) coverage in Graphite unknown** → D3; UI must never fake a ✓.
- **Premium semantics** (monthly vs annual vs pro-rata endorsements) — Phase 0
  freezes the comparison rule before any chip renders.
- **Replica load**: batched (500 refs per IN) + LIMIT; ~2 queries per 500 lines.
- **Two sessions, one prod**: all work in the `alpha-finance-ap` worktree; deploy
  via the runbook in [[reference_omni_ssm_exec]].
