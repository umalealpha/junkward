---
name: ManagerTask
description: Alpha Direct's Manager Objectives system — automatic weekly tasks that managers cannot tick "done" themselves, because Omni reads the real number instead. Auto-load whenever Prathap types /ManagerTask, or the task touches making a manager accountable, giving someone a target or objective, the Sunday-midnight task generator, the Wednesday 4pm settle, the quarterly Board/EXCO pack due the 5th, a manager scorecard, or "why is X not being held to anything". Carries the live system, the rules, every person already done and who is next, so a fresh chat continues exactly where the last left off. Companion to `omni` (deploy), `prat-skill` (dev stack), `alphaleave` (hours). KEEP CURRENT STATE + WHO IS NEXT updated as work lands.
---

# ManagerTask — Alpha Direct Manager Objectives

**Talk to Prathap in plain English. Do the whole ask in one run.** Only stop for the hard
lines: moving money, changing someone's access, deleting live data.

> **The one-line summary:** every Sunday at midnight Omni puts ONE task on a manager's
> board listing the numbers they must move. Wednesday 4pm it reads the live data itself
> and either closes the task or leaves it red. Nobody types "done".

Built 9 Sep 2026 on the CFO's own words:

> *"we need to make managers work — currently they are chilling and not being accountable...
> creating new tasks for them automatically system generated on Sunday midnight, and due on
> Wednesday"* · *"ensure board meeting information is send to EXCO 5th of every quarter ending"*

## On load — pull the shared notes first (automatic, never wait to be asked)
1. `bash ~/.claude/read-notebook.sh` — **the notebook beats Omni's own database.**
2. `git -C "C:/Users/PrathapAsus/work/alpha-finance" fetch origin -q && git show origin/main:MACHINE-TALK.md | tail -30` (newest at the BOTTOM).

## 🔴 Read this before touching the repo
**`C:\Users\PrathapAsus\work\alpha-finance` was 2,479 commits stale on 9-Sep-2026.**
Building there produced migration numbers that collided with the Mac's TWICE in one
session — two leaves crash the backend while the site still serves 200. **Always:**
```bash
git -C "C:/Users/PrathapAsus/work/alpha-finance" fetch origin -q
git -C "C:/Users/PrathapAsus/work/alpha-finance" rev-list --count HEAD..origin/main
```
Non-zero → work in a **fresh worktree off `origin/main`** (`~/work/af-objectives` is the
one this was built in). Re-check the leaf after EVERY rebase — `origin/main` moved 27
commits mid-session.

## Where the code lives
| Piece | File |
|---|---|
| The two models | `hris/weekly_objective_models.py` — `WeeklyObjective`, `WeeklyObjectiveRun` |
| The counters | `hris/objective_counters.py` — 21 registered, all read live, never cached |
| Raise + settle | `hris/management/commands/weekly_objectives_cycle.py` |
| Who gets what | `hris/management/commands/seed_manager_objectives.py` |
| The registers | `iso_compliance/aml_models.py` |
| The schedule | `infra/cron/manager-objectives.cron` |

## She must SEE the number moving
Every objective line in the task carries its own history, because a target of 25
against a backlog of 2,627 reads as hopeless when the same figure turns up every
Sunday:

```
Live policies with failed or missing KYC
  Target: clear 25 (backlog now: 2,602).
  Last time: 2,627 to 2,602 - cleared 25, hit.
  Since 14 Sep: cleared 50 of 2,652 (2% done, 2,602 left).
```

Both lines are deliberate — LAST TIME answers "did I hit it?", SINCE answers
"will this ever end?". Built from `WeeklyObjectiveRun`, no new model.

**Honesty rules, each pinned by a test:** the total is measured from the FIRST
baseline ever recorded, never summed across weeks (summing double-counts a week
where the data moved for other reasons); no "Since" line at all until the number
has genuinely moved the right way, because "0% done" reads as failure; silent in
week one; a nil objective says "Clean 2 of the last 3" and never a percentage.

## The four rules that must never be broken
1. **The task closes ITSELF.** Omni's monthly cycles raise tasks and never close them — on
   9-Sep, 14 managers *including the CFO* were chased daily for feedback already filed. A
   weekly cadence on that behaviour is five false nags a week and a board everyone learns
   to ignore. **Never ship a raise without its settle.**
2. **A counter that cannot be READ is never a miss.** Unreachable Graphite is not a manager
   failing. The run records `settle_error`, stays open, and the task stays open with it.
3. **An emptied backlog counts as MET.** Otherwise "clear 25 a week" becomes a permanent
   miss the moment the job is finished — punishing the person who did the work.
4. **A self-declared "done" proves nothing.** Every counter measures the *thing*, not a
   status field. A report marked "sent" with no document attached does not count. A DPIA
   with `status='approved'` and no signatures does not count.

## Commands
```bash
# see what Sunday will produce — writes nothing
python manage.py weekly_objectives_cycle --raise --cadence=weekly --period=2026-09-14
# add or update someone's objectives (idempotent)
python manage.py seed_manager_objectives --email=<addr> --commit
```
`--commit` writes; without it everything is a dry run. `--period` is testing only.

## The schedule (live in `/etc/cron.d/manager-objectives`)
| When (UTC) | Gaborone | What |
|---|---|---|
| Sat 22:00 | **Sunday 00:00** | raise the week's numbers |
| Wed 14:05 | Wednesday 16:05 | settle — 5 min after the 4pm cut-off |
| Daily 05:10 | 07:10 | the quarterly EXCO pack (raises once, settles the moment it lands) |

⚠️ **`infra/install-crons.sh` drives off an explicit `ENABLED` list.** Shipping a `.cron`
file does NOT arm it — the name must be added to that list or the deploy correctly skips it.

## Cadences
- **weekly** — raised Sunday, due Wednesday 4pm.
- **quarterly** — raised on day 1 of the new quarter, reports on the quarter that just
  ENDED, due the **5th**. `week_of` is deliberately left null so it never lands in a
  weekly plan.
- **annual** — financial year starts **1 July**; `due_days` per objective, default 90.

## Directions
| Direction | Met when |
|---|---|
| `reduce` | backlog fell by the target, **or** the backlog is now zero |
| `increase` | count rose by the target |
| `nil` | the number is zero (zero tolerance) |

Never give a `reduce` objective a target of 0 — it closes itself on day one and proves
nothing. There is a test pinning this.

## Graphite traps — all three already cost real credibility
- **KYC lives in THREE tables.** Read `customer_kyc` **and** `customer_kyc_dom_com`.
  Reading only the individual table falsely flagged 17 commercial policies on 19-Aug.
- **Claim money is in `claim_reserves`, NOT `new_claims.paid_amount`** — that column is
  populated on 29 rows in the whole database and a counter on it reads zero forever.
- **"Paid but never issued" needs `policyActivatedDate IS NULL`.** `status = 0` alone
  includes 44,401 policies that were live at some point.

Omni reads Graphite through the read replica (`integrations.graphite_age._config`),
session forced READ ONLY. `hris/objective_counters._graphite_scalar` is the only door.

---

# CURRENT STATE (keep updated)

## ✅ Kakale Botana — AML/CFT Officer, 5 reports. LIVE 9-Sep.
Before: **two tasks in her entire Omni history**, both auto-raised monthly-feedback.
13 objectives. First fire **Sunday 13-Sep-2026** (CFO chose the date).

| Objective | Target | Baseline 9-Sep |
|---|---|---|
| Live policies, failed/missing KYC | −25/wk | 2,627 · **P 12,091,734.61** premium |
| Paid for but never issued | −15/wk | 729 · **P 4,816,736.95** |
| Claims paid to a KYC-failed customer | nil | 0 this week (32 in 12m, **P 1,154,006**) |
| Suppliers screened | +5/wk | **0 ever** |
| Parties screened against sanctions lists | +20/wk | 0 |
| Confirmed matches not reported to the FIA | nil | 0 |
| PEP question unanswered | nil | 0 |
| Suspicious transactions not filed | nil | 0 |
| Risks with an owner and a plan | +5/wk | 0 |
| Open regulatory breaches | nil | 0 |
| Complaints past 30 days | nil | 0 |
| Staff with no AML training in 12m | −10/wk | **161** |
| Quarterly compliance report to EXCO | nil, due the 5th | first **Mon 5-Oct-2026** |

## ✅ Oratile Ria Tlhomelang — Data Protection Officer, no reports. LIVE 9-Sep.
**NOT the same case — say so before anyone reads her zeros as neglect.** She was given
ten tasks in July and closed nine, marking the tenth honestly partial. The registers read
zero because the ROPA register, policy library and vendor register were **deployed the
morning of 9-Sep** — she'd had them four hours. Her problem was that nothing she did was
checkable. 8 objectives, **no new models** — every register already existed.

| Objective | Target | Baseline 9-Sep |
|---|---|---|
| ROPA entries confirmed with a lawful basis | +15/wk | **0 of 141** |
| Real policies, not placeholders | +3/wk | **0 of 29** (2 flagged gaps) |
| Vendors with a signed data agreement | +3/wk | 0 |
| DPIAs still unsigned | −1/wk | **2, neither signed** (her task named 4) |
| Data-subject requests past 30 days | nil | 0 (also 0 ever logged) |
| Reportable breaches past 72h not notified | nil | 0 |
| Staff who acknowledged the procedures | +10/wk | **5 against 229 documents** |
| Quarterly data-protection report to EXCO | nil, due the 5th | first **Mon 5-Oct-2026** |

**The collision that was nearly shipped:** `ComplianceReport` was unique on
(year, quarter), so Kakale filing her pack would have silently discharged Oratile's duty.
Fixed with `ComplianceReport.kind` (`aml` | `data_prot`); unique is now
(kind, year, quarter). Red-proved.

## Scope decisions the CFO made — do not re-raise
- **ROPA is Oratile's, not Kakale's** — data protection, not AML.
- **NBFIRA returns are Kago Tshutlhedi + Paul Beka's** — off both women's lists.
- **The 229 procedure acknowledgements went to Oratile**, over the stated objection that
  chasing 160 people is arguably Unami's job. Recorded in the seed note.
- **Sunday 13-Sep start, no soft launch.** Asked whether she should hear it from a person
  first; answer: *"dont worry about arun and I, we are putting this control so we make her
  work."*

## The registers built 9-Sep (none existed before)
`iso_compliance/aml_models.py` — `ComplianceReport`, `SanctionsScreening` (UNSC + PEP on
one row), `SuspiciousTransactionReport`, `RegulatoryBreach`, `AMLTrainingRecord`,
`CustomerComplaint`. All in Django admin so they're writable from day one; the **runs are
read-only** there (no add, no delete) — a verdict that can be typed over is an opinion again.

**`RegulatoryBreach` is NOT `core.BreachIncident`.** The latter is the DPO's data-breach
register on the 72-hour IDPC clock. A late NBFIRA return and a leaked customer list are
different incidents, different regulators, different owners.

## Reused, not rebuilt
`iso_compliance.Risk` (existed, 0 rows), `RopaEntry`, `InternalPolicy`, `VendorRegister`,
`DPIA`, `core.DataSubjectRequest`, `core.BreachIncident`, `SOPAcknowledgement`,
`procurement.VendorKYC`, `core.OmniTask` (already had `week_of`, `due_time`,
`completion_pct`), `taskboard.CompletionNote`.

---

# WHO IS NEXT (the CFO's queue)
1. **Kago Tshutlhedi** — Manager, Finance & Planning · 9 reports · reports to the CFO.
   Owns **NBFIRA returns filed on time** with Paul Beka. Nothing seeded yet.
2. **Paul Beka** — Operations Manager · 2 reports · reports to Arun. Same NBFIRA duty.
3. The other ~11 people-managers. 14 in total carry reports; only 2 have objectives.

**SETTLED 9-Sep — do not re-raise.** Kakale's 2,627-policy backlog at 25/week is roughly
two years. Asked whether her five reports should carry the same numbers. CFO: *"its ok she
will take a team and fix the 2627 polices weekly until then it will put tasks for her, and
she can see how the numbers are reducing."* The backlog stays HER objective; she resources
it herself. That answer is what produced the progress line above.

---

# Known limits — state them, never hide them
- **SOP acknowledgements count "at least one".** Omni has no role-to-procedure mapping, so
  that is the strongest honest test available. It cannot be gamed by one person signing
  everything (it counts people, not signatures), but tighten it once a mapping exists.
- **No purpose-built screens yet.** The registers are usable through Django admin only.
  Proper Omni screens are the obvious next build if the counters start moving.
- **Data-subject requests baseline 0 is meaningless** until requests are actually logged —
  a nil objective on an empty register passes trivially.

# Discipline
Prove it by RUNNING it, never by asking a model. Verify the **served** thing, not git HEAD.
Every new rule gets a test that goes RED without its fix — revert and watch it. One
migration leaf on merged main before deploying. Deploy only via
`infra/host/deploy-zero-downtime.sh`. Log every change to `MACHINE-TALK.md`.
