---
name: Payroll
description: >
  Alpha Direct payroll runbook + the hard-won MISTAKE LIST. Auto-load for ANY
  payroll work — running/importing a monthly payroll, computing PAYE, reconciling
  to control totals, adding new hires, building a payslip/net-pay register, or
  emailing payroll figures. Encodes the specific errors made on the July-2026
  ADIC/RSA/Veritas runs (hidden earnings columns, total-row doubling, over-broad
  regex, stale-clone reads, totals-only reconciliation, etc.) so they are NEVER
  repeated. Companion to prat-skill (dev stack), omni (deploy), prat-test / fabe
  (ship gate), deepseek (review). Keep the mistake list growing as new ones appear.
---

# /Payroll — Alpha Direct payroll runbook + mistakes-never-again list

Payroll is money to real people and tax to BURS. Getting it wrong = underpaid
staff, wrong tax, or double-paid GL. This skill is the checklist that stops the
mistakes already made, plus the correct process. **Read §1 before touching any
payroll file.**

---

## 1. MISTAKES MADE — NEVER REPEAT (self-binding)

Every one of these actually happened on a real Alpha Direct payroll run. Each is
now a hard rule.

1. **Hidden / compact earnings columns → can't reconcile.** I emailed a payroll
   register showing only 5 of ~19 earning columns (Basic, Commission, Incentive,
   Allowance, Leave Pay) and hid the rest — so the visible earnings did NOT add
   up to GROSS and Finance couldn't tie it out (Kago, ADIC July 2026).
   → **RULE:** a payroll register MUST show EVERY component that feeds gross
   (Principal Officer Allowance, Health Insurance Allowance, Housing, Vehicle,
   Fuel, Internet, Medical-aid allowance, etc.). Prove that, for EVERY employee,
   the sum of the earnings columns = GROSS, and GROSS − (PAYE + deductions) = NET.
   Only hide a column if it is zero for ALL employees, and say so in a note.

2. **Summary "TOTAL" row ingested as an employee → DOUBLED Basic.** The importer
   swept the file's "TOTAL (72 payslips)" row in as a person, doubling Basic
   (740,087.50 → 1,480,175) and making 73 "payslips". The total-row detector only
   matched an exact "Total".
   → **RULE:** always strip/skip summary rows (Total / Grand Total / Subtotal /
   Sum / "TOTAL (N payslips)"). After parsing, assert **row count == expected
   payslip count** and **sum(Basic) == the file's Basic control total** BEFORE
   creating a batch. A doubled total is the classic tell.

3. **Over-broad "fix" that broke a pre-existing test.** My first total-row regex
   fix (`keyword\b.*`) matched real names ("Total Quality Mgmt", "Sum Chan") and
   broke an existing guard test — because I ran only my NEW test, not the suite.
   → **RULE:** run the FULL relevant test suite (`manage.py test payroll ...`),
   never just the new file. A pattern/rule change needs its KEEP cases (real
   names that must NOT match) as well as its MATCH cases.

4. **Read a stale local clone instead of prod/origin.** Early on I diagnosed from
   a local clone ~60 commits behind and misread the live behaviour.
   → **RULE:** verify against `origin/main` AND the RUNNING prod image/data, not a
   local checkout. Confirm the running code + real payslip data before concluding.

5. **Stated a change from truncated output.** I told the CFO "Moses lost his
   mobile allowance" from a truncated console dump — it was wrong.
   → **RULE:** never assert a figure/change from truncated or partial output.
   Pull the full row and re-verify before stating anything about someone's pay.

6. **Reconciled on TOTALS only, not per-employee.** I claimed "ADIC identical
   across all 71" because the control totals matched — DeepSeek caught that
   matching totals can hide offsetting per-employee changes (5 differed).
   → **RULE:** reconcile BOTH the control totals AND per-employee (gross/net per
   person). Totals matching ≠ every payslip correct.

7. **Sloppy rounding prose.** Claimed "0.02 total / byte-identical" in the same
   breath (contradiction) and once used Python `round()` (banker's) instead of
   half-up.
   → **RULE:** PAYE and money round HALF-UP to 2 dp (Excel convention), not
   Python's `round()`. Be precise about sub-cent differences; call them rounding,
   not "identical".

8. **New hires imported via the payroll file.** Letting the import create
   employees risks attaching pay to omni's blank-shell DUPLICATE employee rows
   (name-match landmine) and minting HR master data.
   → **RULE:** HR creates new employees in the HR module FIRST (real employee
   numbers, no duplicate shells); payroll imports against clean IDs. Flag missing
   master fields (Omang, start date, employment type, fund enrolment) — never
   guess them.

9. **Nearly finalised before clearing exceptions / master data.** Was about to
   import before the 3 new hires existed and before Shane-zero / loan-consent /
   large-commission were confirmed.
   → **RULE:** HOLD import until master data is in and every exception is cleared
   or explicitly signed off. An import creates DRAFT payslips; it never pays.

10. **Operational slips:** SSM JSON broke on a `\|` escape (deploy silently
    didn't run); a leave-batch load failed silently because the label exceeded the
    60-char DB field; big diagnostic dumps got truncated at ~24 KB.
    → **RULE:** validate JSON escapes; respect DB field lengths; keep diagnostic
    output compact (or gzip) so nothing is silently truncated; after any deploy,
    confirm the change is actually live (grep the running image + HTTP 200).

**Pre-send / pre-finalise gate (answer YES to all):** columns show everything
that feeds gross and reconcile per-employee? · total/summary rows stripped and
count == expected? · totals AND per-employee tie? · PAYE half-up, medical not
deducted, funds capped at 15%? · no negative nets? · new hires created in HR,
missing fields flagged? · full test suite green (for code) · /deepseek + /fabe
run? · nothing paid without a different-manager approval + CFO sign-off?

---

## 2. BOTSWANA PAYROLL RULES (the maths)

- **Taxable income = gross earnings − employee PENSION − employee PROVIDENT**
  (approved fund contributions, deductible up to **15% of income** — cap it).
  **Medical aid EE is NOT deductible.**
- **PAYE — resident annual bands** (annualise monthly taxable ×12, apply, ÷12,
  round HALF-UP): first 48,000 @ 0% · next 36,000 @ 5% · next 36,000 @ 12.5% ·
  next 36,000 @ 18.75% · excess @ 25%. (Income Tax Act Cap 52:01, 4th Schedule.)
- **TOTAL DEDUCTIONS = PAYE + loans + housing tax + housing + medical EE +
  pension EE + provident EE** (absolute values). **NET = GROSS − TOTAL DED.**
- **CTC = GROSS + employer medical + pension + provident.**
- **Deductions are stored NEGATIVE** in the file → take magnitude; a negative
  never inflates gross.
- **Housing salary-sacrifice** is a NEGATIVE EARNING that nets gross down ONCE
  (e.g. Housing Allowance −14,000). On a roll-forward it must NOT be re-added to
  gross or re-taxed — an unchanged employee's pay must equal last month exactly.
- **Employment Act:** loan/voluntary deductions need written consent and must not
  leave a negative/unreasonable net. Suspending a loan (favouring the employee)
  is fine — keep the written instruction on file.

---

## 3. PROCESS (import → pay)

1. **Receive** the final workbook (CFO 28+-col layout). Note new hires, loan
   suspensions, one-off instructions.
2. **Pre-checks:** strip summary rows; row count == expected; sum each earnings
   column, GROSS, and Loans == the file's control totals (flag ANY variance).
3. **Compute** per §2. Recompute GROSS from earnings and reconcile to the file.
4. **Reconcile** totals AND per-employee vs last month; flag movers.
5. **Legal check** (§2 + Employment Act). Verdict LEGAL / LEGAL-WITH-NOTES.
6. **Exception report** (always): unmatched names; new hires (name/gross/PAYE +
   funds status); gross mismatches; negative nets; zero payslips; loan
   suspensions confirmed; largest commission & PAYE as a note.
7. **New hires:** HR creates them in the HR module first; flag missing fields.
8. **Gate:** /deepseek review + /fabe audit. For code changes: full test suite.
9. **Load** via omni preview → a DIFFERENT manager approves → commit (DRAFT
   payslips). **Payment is separately CFO-gated** at 09:00 cut-off.
10. **Deliverable:** an Alpha-Direct-branded register (Navy #1D3270 / Orange
    #F47C20, Montserrat) showing every earnings + deduction column, GROSS, PAYE,
    TOTAL DED, **NET (highlighted)**, employer contribs, CTC, and a TOTAL row —
    reconciling line by line.

---

## 4. REUSABLE MONTHLY PROMPT

```
OMNI — [MONTH YEAR] PAYROLL RUN ([ENTITY])

INPUTS: workbook [file], sheet "Payroll [YYYY-MM]"; new hires with no Employee
No (HR must create in the HR module FIRST) [names/none]; loans suspended this
month (show 0.00, don't reinstate) [names/none]; other Finance instruction [/none].

IMPORT: match by Employee No then exact name (flag unmatched); earnings = Basic
Salary..Non-Cash Benefits, deductions = Loans/Housing Tax/Housing/Medical EE/
Pension EE/Provident EE (stored negative); IGNORE the file's TOTAL DEDUCTIONS
(recompute); STRIP summary/"TOTAL (N payslips)" rows; assert count == expected
and sum(Basic) == file Basic total.

COMPUTE (per employee): taxable = gross − pension EE − provident EE (approved,
cap 15%; medical NOT deductible). PAYE = annualise ×12, bands 0/5/12.5/18.75/25%
at 48k/84k/120k/156k, ÷12, round HALF-UP. TOTAL DED = PAYE + all deductions
(abs). NET = GROSS − TOTAL DED. CTC = GROSS + employer contribs.

RECONCILE: every earnings column shown; per-employee earnings sum == GROSS;
totals == the file's control totals to the thebe; compare per-employee vs last
month.

CHECKS: no negative nets; flag zero payslips; loans > ~1/3 gross need consent;
low/part-month = joiner/leaver only; all rows one entity.

OUTPUT: exception report + an Alpha-Direct-branded register showing ALL columns,
GROSS, PAYE, TOTAL DED, NET, CTC + TOTAL row.

FINALISE: only after HR/Finance clear every exception → preview → a DIFFERENT
manager approves → commit → CFO pays. Never pay from a draft; never hide columns.
```

---

## 5. Relationship to other skills
- **prat-skill** — dev stack + CFO comms rules (plain English to the CFO).
- **omni** — deploy path (SSM to prod EC2).
- **prat-test / fabe** — ship gate for any code change (full suite, then deploy).
- **deepseek** — independent numbers/legal review, off-subscription.
- **alpha-direct-governance / exco-ca4-cfo-copilot** — org governance + brand;
  they win on any conflict.
