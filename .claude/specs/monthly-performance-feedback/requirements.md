# Requirements — Monthly Manager Performance Feedback (omni HRIS)

**CFO directive 2026-07-20.** Labour-Act (ELRA-2025) record-keeping: every manager gives a short
monthly performance feedback to each direct report. Distinct from the 6-monthly Development Dialogue.

## Reuse mandate
Build on the EXISTING spine — do NOT create a 4th performance silo. The record IS `MonthlyCheckIn`
(hris/performance_feedback_models.py). Manager→report chains already exist in `HRISProfile.manager`
(verified prod: Gosego→Medu; Kago/Pako→CFO). The 6-monthly deep review is DevelopmentDialogue.

## Functional requirements
1. **Monthly feedback, per direct report.** A manager records, once a month, for each person who
   reports to them, three short notes:
   - what they did **well**
   - what they did **not do well**
   - areas to **improve**
   Recorded on the manager's dashboard / task list (a prompt, not a hunt).
2. **Standing monthly target from the job description.** Each employee can carry a monthly target
   (e.g. Gosego Makone: BWP 30,000 new sales/month). At month-end the feedback prompt shows the
   target and asks the manager to confirm **achieved / not achieved** (+ actual + note). Recorded.
3. **Decision panel** shown to the manager per employee, so feedback is fact-based, not guesswork:
   - Time Doctor tracked hours (the month)
   - days of absence / did-not-track
   - leave taken, and **sick** leave specifically
   - previously assigned tasks: how many completed, how many **on time**
4. **Non-compliance escalation.** Any manager who has NOT given feedback for the month is listed in
   the **C-suite morning debrief** and the **team debrief** as a pending item, automatically.
5. **Gather missing job descriptions** — the daily HR email asks HR to supply job descriptions /
   targets for employees who have none. (Replaces asking for banking info — DPA-positive.)

## v1 enhancements (CFO chose all four)
- **Pre-fill from facts** — the 3 boxes are auto-drafted from Time Doctor hours, task on-time %, and
  target result; the manager edits rather than writes from scratch.
- **Auto-pull the actual number** — for number targets (e.g. new sales), pull the real figure from
  the source system so "did they hit it?" is half-answered; manager confirms.
- **3-month trend + decline flag** — per employee, show rating / target-hit trend; flag early decline.
- **Manager league table** — monthly view of which managers gave feedback and which did not.

## Non-functional / compliance
- ELRA-2025 evidentiary: a low/negative note carries evidence; records lock after sign-off;
  `retention_until` set (DPA-2024). Reuse existing MonthlyCheckIn escalation → warning → PIP.
- Access: reuse the performance module's tiered scope (manager sees only own reports; C-suite/HR full).
- No customer PII to any external service (AD-POL-AI-GOV-001). Targets/actuals are internal figures.
- Multi-entity safe (entity-scoped like the rest of the module).

## Out of scope (v1)
- Replacing DevelopmentDialogue (6-monthly) — untouched.
- Company-wide OKR cascades; peer/360 feedback.
