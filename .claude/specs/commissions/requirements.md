# Commissions module — Requirements

**Status:** draft for EXCO review · re-derived on the Mac from the Windows handover note (2026-07-15). The detailed 5-phase plan lived only in the Windows memory store and did not sync; this spec reconstructs it from the handover + a live read of the existing `agent_portal` module.

## Problem

Independent agents, in-house (payroll) agents, and the BDU domestic sales team each submit their monthly commission by **emailing Excel workbooks**. Three separate flows, three owners, manual consolidation, no audit trail. We want **one online form** in omni where an agent enters their per-policy lines for the month; the numbers total automatically (including the 10% withholding where it applies); an owner reviews and approves; and Finance exports a clean payout file.

## Scope (v1)

Standalone submit → review → approve → export tool. **No GL posting, no payments coupling, no automated tax payment** — same deliberate boundary the CFO set for `agent_portal` (compute + export a file; sign-off and money movement stay manual finance controls).

Out of scope for v1: automatic payment, GL journal entries, live Graphite policy verification, back-loading historical workbooks (that bulk load is a later, separate job).

## Commission groups (the three flows, made configuration not code)

| Group | Withholding | Paid via | Owner |
|---|---|---|---|
| Independent agents | **10% if working directly for us; 0% if working through a company** | Direct bank | Bokani Makosha |
| In-house / payroll agents | 0% | Payroll | Tlamelo Chimidza |
| BDU domestic sales team (10 named agents) | 0% (taxed through payroll, not this withholding) | Payroll | Tlamelo Chimidza |

Pay-route + base withholding are **per-group configuration rows**. The independent
direct-vs-through-a-company split is a **per-agent flag** (`works_via_company`):
effective withholding = 0 if the agent works through a company, else the group
rate. (CFO 2026-07-15 — resolves the earlier BDU open question.)

## User stories

1. **As an agent**, I enter my monthly commission as per-policy lines (policy number, client, transaction type, amount collected, annualised premium, commission rate, collection date, whether the policy is closed, commission amount) and submit them, instead of emailing a spreadsheet.
2. **As an agent**, I see my running total, the withholding deducted (if my group has it), and my net payable — before I submit.
3. **As a group owner (Bokani / Tlamelo)**, I see every submission for my group for the month, review the lines, and approve or reject with a reason.
4. **As Finance**, I export the approved submissions for a group + month as a payout file (agent, bank, gross, withholding, net).
5. **As the CFO**, the module never moves money or touches the GL on its own — the export is handed to the existing manual payment control.

## Acceptance criteria

- A submission belongs to exactly one agent + one month (`YYYY-MM`); re-submitting the same month updates the draft, never creates a duplicate.
- Gross commission = Σ line commission amounts. Withholding = round(gross × group rate, 2). Net = gross − withholding. In-house group → withholding is 0.00 and net = gross.
- A submission moves draft → submitted → (under_review) → approved | rejected. Only an owner/manager may approve/reject; an agent may not approve their own.
- Agent bank details are sensitive: stored server-side, access-gated, never returned to a non-owner, never sent to any external service. (Agents are payees, not policyholders — this is the same treatment `agent_portal`/payroll already give payee bank data.)
- The payout export lists only approved submissions with bank details captured; those approved-but-no-bank are reported as "held", not silently dropped.
- Totals recompute whenever lines change; the withholding rate in force is snapshotted onto the submission at submit time (so a later config change never silently rewrites a signed-off number).

## Resolved (CFO 2026-07-15)

- **BDU** is taxed through payroll — no 10% withholding of this kind; `bdu` group = payroll / 0%.
- **Independent** is not a flat 10%: a direct independent agent has 10% withheld; one working **through a company** has none. Modelled as the per-agent `works_via_company` flag.

## Reuse

- `core.models.BaseModel` (UUID + timestamps) — base for all models.
- Follows `agent_portal` conventions exactly: manager-gated viewsets, sensitive-bank access log, per-cycle export CSV, `useTheme()` FE page, dedicated API router block, Sidebar + Command-Palette entries.
- Distinct app from `agent_portal` because the population (independent/in-house/BDU vs UNICOIN agents) and the flow (self-declared lines vs an 8-stream compute engine over paygate data) are different.
