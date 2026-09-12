# Commissions module — Design

New Django app **`commissions`**. Standalone (no ledger/payments FK). Mirrors `agent_portal` conventions.

## Data model (all extend `core.models.BaseModel` → UUID pk + created_at/updated_at)

### `CommissionGroup`
The three flows as configuration.
- `key` — slug, unique: `independent` | `in_house` | `bdu`
- `name` — display name
- `withholding_rate` — Decimal(5,4), default `0` (e.g. `0.1000` = 10%)
- `pays_via` — choices `direct_bank` | `payroll`
- `owner_name` — char (Bokani / Tlamelo / TBC)
- `is_active` — bool
Seeded (data migration) with the three rows from requirements.

### `CommissionAgent`
- `name` — char, unique (natural key, matches how the workbooks identify an agent)
- `agent_code` — char, blank
- `group` — FK → CommissionGroup (PROTECT)
- `email` — char, blank (used to match the signed-in user to their own submissions)
- `works_via_company` — bool (CFO 2026-07-15). An independent agent working through
  a company has NO withholding; effective rate = 0 if set, else the group rate.
- `is_active` — bool

### `CommissionBankAccount` (sensitive — server-side, access-gated)
- `agent` — OneToOne → CommissionAgent (related_name `bank`)
- `bank_name`, `account_name`, `branch_code` — char, blank
- `account_number` — char (required to be "ready to pay")
- `updated_by` — FK user (SET_NULL)

### `CommissionSubmission`
- `agent` — FK → CommissionAgent (PROTECT)
- `group` — FK → CommissionGroup (PROTECT) — snapshot of agent.group at create
- `period_label` — char `YYYY-MM`
- `status` — `draft` | `submitted` | `under_review` | `approved` | `rejected` | `paid`
- `submitted_by`, `submitted_at`
- `reviewed_by`, `reviewed_at`, `review_note`
- `gross_commission`, `withholding_rate` (snapshot), `withholding_amount`, `net_payable` — Decimal(18,2)
- **unique_together** `(agent, period_label)`

### `CommissionSubmissionLine`
The per-policy line, exactly the fields the workbooks carry.
- `submission` — FK → CommissionSubmission (CASCADE, related_name `lines`)
- `policy_number` — char, db_index
- `client_name` — char
- `transaction_type` — `new_business` | `renewal` | `endorsement` | `previous_month`
- `amount_collected` — Decimal(18,2)
- `annualised_premium` — Decimal(18,2)
- `commission_rate` — Decimal(7,4)  (percentage as entered)
- `collection_date` — Date, null
- `is_policy_closed` — bool
- `commission_amount` — Decimal(18,2)  (as entered; `computed_commission` helper = amount_collected × rate/100 for a soft cross-check, never overwrites)

## Service (`commissions/service.py`)
- `compute_totals(line_amounts, rate)` — **pure function** (no Django): gross, withholding, net. Unit-testable without a DB.
- `effective_withholding_rate(agent, group)` — 0 if `agent.works_via_company` else `group.withholding_rate`.
- `recompute_submission(sub)` — sums `sub.lines`, applies the agent's **effective** rate, writes the four total fields.
- `submit(sub, user)` — draft/rejected → submitted; snapshot withholding_rate; stamp submitted_by/at; recompute.
- `review(sub, user, approve, note)` — submitted/under_review → approved|rejected; block self-approval; stamp reviewer.
- `payout_rows(group, period)` — approved subs for group+period split into `ready` (bank captured) and `held` (no bank).
- `export_payout_csv(group, period, user)` — CSV of `ready` rows + a PayoutBatch stamp; held reported, never dropped.
- `monthly_summary(group?, period?)` — rollup per agent (count, gross, withholding, net, status).

## API (`commissions/api_views.py`, `serializers.py`, `access.py`)
Dedicated router block appended in `alpha_finance/api_router.py` (same pattern as `agent_portal`, api_router.py:1278):
- `commissions/groups` → `CommissionGroupViewSet` (read-only)
- `commissions/submissions` → `CommissionSubmissionViewSet` (ModelViewSet)
  - default queryset scoped: managers see all; a plain user sees only their own (by matched agent email/name)
  - nested `lines` accepted on create/update (write-through)
  - `@action` `submit`, `review`, `payout-export`, `summary`, `access`, `my-submissions`
- `access.py` — `is_commissions_manager(user)` (Finance titles + group owners by email) + `IsCommissionsManager` permission + `agent_for_user`. Mirrors `agent_portal.access`.
- Bank read/write is an access-logged action on the agent, manager-gated (mirrors `agent_portal` AgentViewSet.bank).

## Frontend (`src/app/(dashboard)/commissions/page.tsx`)
`useTheme()` tokens (light/heavenly/fun), matching agent-portal.
- **Submitter view:** month picker, editable line table (add/remove rows), live totals + withholding + net, Submit.
- **Manager view:** submissions queue for the month, per-submission line detail, Approve/Reject, Export payout (per group).
- API helpers added to `src/lib/api.ts`.
- Nav: entry in `src/components/layout/Sidebar.tsx` + `src/components/CommandPalette.tsx` (group "Accounting").

## What this design must NOT touch
- `agent_portal` (any file) — the UNICOIN engine is independent; do not modify it.
- `ledger`, `payments`, `payroll` models — v1 has no GL/payment coupling.
- Revenue mapping / MA format / dashboard tiles / frozen numbers.
- `alpha_finance/settings.py` beyond appending `'commissions'` to `LOCAL_APPS`.
- `main` branch / prod deploy — work lands on `feat/commissions`; main auto-deploys at 05:09, so the launch stays off main until the CFO says go.
