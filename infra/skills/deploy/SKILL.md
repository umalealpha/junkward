---
name: deploy
description: Prathap's go-live command — the partner to /code. Use whenever Prathap types "/deploy", or says "deploy this", "put it live", "ship it", "make it live". It takes code that is already built and tested (normally by /code) and puts it live SAFELY, following the Deploy rules — pick the right lane, don't clash with other chats, near-zero downtime, and prove the live site survived. It reuses the fabe ship-gate for the actual deploy; it does not reinvent deployment. /code builds and tests and STOPS; /deploy is the deliberate step that takes it live.
---

# /deploy — take tested code live, safely

**The pair:** `/code` builds and tests, then stops at "ready". `/deploy` is the separate, deliberate
step that puts it live. Keeping them apart is on purpose — going live is never automatic.

**This is a wrapper. It reuses the real deploy machinery (fabe) and the Deploy rules — it does not
duplicate them.** Always invoke the underlying skills so their latest content is used.

---

## Before you deploy — pick the lane

Read `Deploy/README.md` + `Deploy/RELEASE-CHECKLIST.md` in the alpha-finance repo and choose:

- 🟢 **Normal lane** — features / tidy-ups / non-urgent fixes. Go live on their own or in a small
  planned batch, at a quiet time (ideally after hours). Never ride live next to another chat's
  unfinished work.
- 🔴 **Emergency lane** — a live payment / payroll / money problem right now. **The fix goes out
  ALONE** (nothing else bundled with it), immediately, and is undo-able in seconds.

If it's unclear which lane, ask Prathap with a **popup** (Yes/No, recommended first — see `/reco`).

## The steps

### 1. Load context
Invoke **prat-skill** (if not already loaded) for the system + deploy knowledge, and read the two
Deploy docs above.

### 2. Declare it
Add / update the row in `Deploy/CHANGE-LIST.md` so other chats know a go-live is happening. If
another chat is `building`/`waiting` on the **same area**, STOP and coordinate first.

### 3. Deploy via the fabe ship-gate
Invoke the **fabe** skill and run its **full** test → fix → **deploy** path (this is the part `/code`
skips). fabe already does the safe deploy correctly, so reuse it:
- hard gates: tripwires + real build/tests; weighted off-subscription panel; Fable 5.1's final call;
- lands the change on the **latest** main via a throwaway copy + cherry-pick — **never** rebase the
  shared checkout, **never** force-push, **never** commit another chat's files;
- deploys to prod (EC2 via AWS SSM); remember the traps:
  - front-end change → rebuild front-end with `--no-cache frontend` (deploy script does backend only);
  - migration / model change → the backend **image must be rebuilt**, not just restarted;
  - never restart prod Caddy blind.
- run fabe's **Task-Completion QC (step 6c)** as part of the gate — the independent, free audit that
  restates every task from Prathap's original instruction and adversarially proves each one DONE /
  partial / not done against the live system. `/deploy` does not re-implement this; fabe owns it.

### 4. Prove it's live (never say "done" without this)
- Health-check the site is up; scan for a 5xx / error spike.
- Open the changed page in the browser and confirm the change is really there — check the **served
  page**, not the code. Re-do the exact thing that was asked and watch it work (use eyes-on / qc).
- If anything looks down or spiking → **STOP and alert Prathap. Never auto-rollback a live database
  migration** — a human decides.
- Close out with fabe's **Task-Completion box** (one row per task Prathap asked for: Done? / how it
  was proven / tested via /fabe?) and hand Manus the **QC runbook** fabe produced, so Manus can
  independently re-test and feed back. A close-out without the box is not a close-out.
- Update / remove the `Deploy/CHANGE-LIST.md` row.

---

## Hard stops (always pause and ask Prathap with a popup)
- Frozen numbers / MA-format / journal-GL changes, or any PII.
- Access / permission changes, credentials, moving money — I do NOT execute these even with deploy
  authority; hand the exact action to the person with authority.
- A live migration that looks wrong after deploy — never auto-rollback; ask.

## When NOT to use
- Nothing new to ship → don't deploy.
- Code not yet tested → run `/code` first; `/deploy` assumes it's already built and green.
- Personal projects (Nako Pula, Tony, GRC, ACCA) → their own deploy paths, not this one.

*One line for Prathap: type `/deploy` after `/code` and I'll put the tested change live the safe
way — right lane, no clashes, seconds of downtime, and proof the site is still up.*

---

## Build Log — record it (CFO instruction, 2026-09-09)

Prathap reads omni → Build log at the end of a day. This command must keep it
honest: mark work **waiting** once it is built and tested, and let the DEPLOY
record be the only thing that ever says "live".

    python C:\Users\PrathapAsus\.claude\scripts\devlog.py         --key cfo-YYYY-MM-DD-<slug>   # the SAME key /code, /goal or /lane-b used --status waiting

**Never pass --status live.** omni refuses it and downgrades to waiting,
because a command claiming "live" without a release behind it is the exact lie
this log exists to stop.

### Link the commit so the release can claim it
A deploy attaches commits to a build item ONLY by an explicit trailer. Put this
line at the end of the commit message, above the Co-Authored-By line:

    Dev-Item: cfo-YYYY-MM-DD-<slug>

There is deliberately no matching on words: a wrong link invents a finished
piece of work nobody did.

### 🔴 KNOWN GAP (2026-09-09) — "Finished today" cannot fill yet
`devlog_deploy` is written and tested, but **nothing calls it.**
`infra/host/deploy-zero-downtime.sh` never runs it, and neither does the
Windows path `fabe/scripts/deploy_ssm.py`. Until one of them does, every
release goes unrecorded and the top band of the dashboard stays empty no matter
how much ships. The script also does not capture the previous commit before the
git reset, so that has to be captured by the caller. Do not paper over this by
letting a skill write "live" — fix the deploy path.
