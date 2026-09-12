---
name: code
description: Prathap's one-command coding workflow. Use whenever Prathap types "/code", or says "code this", "build this properly", "let's code X". It FIRST reads the notebook, machine-talk and memory, then runs his coding stack in order — prat-skill (system understanding + design), Karpathy (coding discipline), lane-b (cheap off-subscription build), fabe (test + fix ONLY) — and STOPS at "tested and ready". It does NOT deploy / go live — Prathap has a separate deploy command for that. This is a meta-skill: it invokes the underlying skills, it does not duplicate them.
---

# /code — Prathap's one-command coding workflow

> 🚫 **OMNI NEVER MOVES MONEY — never call Omni payment work "money-critical" (CFO angry directive 2026-08-31, said ~100 times).** Omni moves ZERO money. The CFO authorises every real payment himself **in the FNB app, with 2-factor**. An Omni "payment / authorise / approve / mark-as-paid" is a WORKFLOW RECORD only — it never debits an account. So nothing built in Omni is "money-critical", "money movement" or "moves funds"; never describe it that way to him or in a review. Omni payment code is ordinary record/workflow code (a wrong record is a data bug, not money moving). The only real money egress is FNB + 2FA, done by a human. See [[p-fnb-is-sandbox]].

**What this is.** A single handle that first reads what is already known (the notebook, machine-talk,
memory) and then runs the four skills Prathap normally types one by one before/around a coding task,
in the correct order. Instead of `/prat-skill` then `/Karpathy` then `/lane-b` then `/fabe`, he types
`/code` once and gets the read-first step plus all four.

**This is a wrapper. It does NOT re-explain or replace the four skills — it invokes them.**
Always call the real skills (via the Skill tool) so their latest content is used; never copy their
rules in here (they change, this must not go stale).

---

## 🔴 Step −1 — IS THIS ACTUALLY A BUG? (10 seconds, before anything else)

`/code` is the heavy lane: four skills, then five models voting in `/fabe`. That is correct for a
new module. On a small bug it turned a 10-minute job into an hour — Prathap's own words,
2026-09-09: *"a bug can't take one hour to fix and that's the case now."*

**So route first:**

| The job is… | Lane |
|---|---|
| Repairing existing behaviour — a crash, a wrong number on screen, a button that does nothing, a failing test — and it plausibly touches ≤3 files | **`/bug`** (fast lane). Stop reading this skill and invoke `bug`. |
| Building something new, a batch of items, a redesign, a migration, or anything touching frozen numbers / GL mapping / personal data | **stay in `/code`** (below) |
| Started as `/bug` but the fix grew past 3 files, or root cause wasn't found in ~15 min | it escalated up to here — carry on with `/code` |

Do not run the full chain below on a one-line fix. That is the exact waste this gate exists to stop.

---

## The order — read first, then run these four, in this sequence

### 0. READ FIRST — the notebook, machine-talk, and reference (before ANY task)
Before touching anything, load what is already known so you don't re-ask settled facts, clash
with the other machine, or repeat a fixed mistake. Do this FIRST, every `/code` run:
- **The notebook** — run `bash ~/.claude/read-notebook.sh` (seamless, ~2s). It is the single
  source of settled facts and **beats Omni's own database** if they disagree.
- **MACHINE-TALK.md** (top level of the alpha-finance repo) — what the other seat (Windows / Mac)
  has been doing before you touch anything shared (prod, repo, credentials, cron).
- **MEMORY.md** (this workspace's auto-memory index) + any linked memories relevant to the task.
- If a fact from any of these bears on the task, act on it. Don't proceed until you've read them.

### 1. `prat-skill` — understand the system + design first
Invoke the **prat-skill** skill.
- Loads the system knowledge (omni / alpha-finance / Graphite), the reuse-first rule
  ("search for an existing skill or module before building — hidden ≠ missing"), the design
  conventions (brand Navy `#1D3270` / Orange `#F47C20`; delegate visual design to Stitch), and the
  CFO communication + run-to-completion rules.
- If the session already auto-loaded prat-skill, don't reload it — just carry on.
- **If the task is visual/design**, honour prat-skill's design-review gate (suggest 🟢 improvements,
  ask "Can I add these too?", wait) BEFORE coding.

### 2. `Karpathy` — coding discipline
Invoke the **Karpathy** skill.
- Think before coding; state assumptions; simplest solution that works; surgical changes only
  (touch nothing you weren't asked to); define the success check and verify against it.
- Applies to the design AND the build in steps 3–4.

### 3. `lane-b` — build it cheaply (cost control)
Invoke the **lane-b** skill.
- The bulk of the building runs off the Claude subscription (cheap models through the local
  gateway), with the real-check repair loop for code (build/tests must pass, not a model's opinion).
- **Builder + parallelism (updated 2026-09-09):** `swarm.py` now runs **10 items at once** by
  default and takes `--builder`. For CODE that must be right, use **`--builder builder-reason`**
  (DeepSeek v4-pro, the high engine) — measured 10 items built in parallel, **10/10 passing their
  real tests in 41 seconds**. For bulk work at zero cost use **`--builder worker-free-code`**
  (local Ollama). The paid second-opinion call is now skipped automatically on any item whose real
  `--check` passed (`--verify on-fail`, the new default). See the lane-b skill for the full table.
- If it's a one-off small change rather than a batch, lane-b's own guidance on when to use it
  applies — follow what lane-b says; don't force the batch tooling onto a trivial fix.

### 4. `fabe` — test + fix ONLY (do NOT deploy) — 🔴 MANDATORY, NON-SKIPPABLE
Invoke the **fabe** skill, but use it as the **test-and-fix gate only**. **This step is not
optional and cannot be substituted.** For ANY change that touched code, you MUST actually call the
`fabe` skill (Skill tool) and let it run — tripwires + real build/tests, the weighted
off-subscription panel (or Fable-only when tripwires/size force it), and Fable 5.1's independent review.
- 🔴 **CI passing, your own local run, a syntax check, or "it obviously works" are NOT the fabe gate
  and never replace it.** If you cannot run the real tests locally (no DB, no gateway), you still run
  `fabe` — it decides how to test (container / CI / Fable-only) and returns the verdict. Skipping fabe
  and calling the work "tested" is the exact failure this workflow exists to stop.
- If Fable 5.1 says FIX, apply the ordered fixes surgically and re-test to green (fabe's 2-round cap).
- **STOP at a SHIP verdict. Do NOT run fabe's deploy step.** Leave the change committed and
  tested, ready to go live.
- Report the fabe verdict to Prathap in plain English (SHIP / what was fixed), and never say
  "tested and ready" unless fabe actually returned SHIP.
- 🔴 **`/code` never deploys / never pushes to the live system.** Deploying is a separate,
  deliberate step Prathap runs with his own deploy command. Hand the tested change over to that.
- Do fill in `Deploy/CHANGE-LIST.md` (in the alpha-finance repo) while coding, so other chats
  know what you're touching — but the actual go-live (`Deploy/RELEASE-CHECKLIST.md`) belongs to
  the deploy step, not to `/code`.

---

## Fan out when the work splits — the good idea borrowed from ruflo (2026-08-31)

Ruflo's one genuinely useful trick is doing many things at once (a "swarm"). `/code` gets that
speed-up two ways: **the built-in agents are the default** (they run on the Claude subscription — no
metered spend, no keys, simplest), and **ruflo is now a live option** — DeepSeek, Gemini and OpenAI
keys were wired into ruflo from the cost-stack/omni secrets and live-tested working on 2026-08-31.
Prefer the built-in agents; reach for ruflo only when you deliberately want a big fan-out to run
**off-subscription on the cheap metered models** (same cost-saving spirit as `lane-b`). Either way this
changes only the PACE of the run; every rule below still holds. Ruflo caveats unchanged: its
cost-router does NOT auto-route by task difficulty (you target a model explicitly), and never install
ruflo plugins through its failed-signature marketplace. See [[r-ruflo]].

- **Default sequential; go parallel only when the parts are truly independent.** If the job splits
  into pieces that don't touch each other — several separate files/modules to build, several pages to
  screenshot, several subsystems to read, several checks to run — do them side by side. A single
  feature that must be built in order stays sequential; forcing parallelism there just risks clashing
  edits.
- **How to fan out:** a few independent pieces → the **Agent tool** (spawn them in one message so they
  run together). Many pieces, or a build→verify pipeline → the **Workflow tool**. Both are built in.
- **Parallel file EDITS must be isolated** so two agents don't fight over the same checkout — give each
  its own `git worktree` (matches prat-skill's parallel-session rule). Parallel READS/CHECKS need no
  isolation.
- **Biggest win is the checking stage.** At step 4, verify independent claims/files/pages with several
  checkers at once (this is already prat-skill §13's Fable-5 verification sweep and `fabe`'s review
  panel — lean on them, don't hand-roll). Cheap mechanical checks get low-effort agents; save the
  heavy models for the financial / prod ones.
- **Still non-negotiable:** `fabe` (step 4) stays mandatory, `/code` still STOPS before deploy, and
  reuse-first still applies. Fanning out never skips a gate — it just runs the gates' independent parts
  together. See [[r-ruflo]].

---

## Rules for the whole run

- **Run to completion — then STOP before deploy.** `/code` is one job: the four steps end at
  "tested and ready to go live." Don't stop between the steps to ask "shall I continue?" — but
  do NOT cross into deploying; that's a separate command. Only stop earlier for a real hard gate
  (money, access/permission change, deleting live data, frozen numbers / MA-format / PII) — and
  then ask with a **popup** (AskUserQuestion), recommended option first.
- **Reuse before building** (from prat-skill): before writing anything new, check for an existing
  skill / omni module / repo that already does it.
- **Plain English to Prathap** throughout — he's non-technical. Lead with what it means for him and
  the one thing he must do.
- **Prove it before "done"** — exercise the real running thing (screenshot / test output), never
  claim done off a green build alone.
- **"Tested and ready" = fabe returned SHIP.** The job is not finished, and you may not tell Prathap
  it is tested, until the `fabe` gate (step 4) has actually run and reached SHIP. No exceptions for
  "small" or "obvious" changes — a code change always goes through fabe.

## When NOT to use the whole chain
- **Pure question / no code change** → just answer; don't spin up lane-b or fabe.
- **A live emergency fix (payment/payroll down)** → skip lane-b's batch tooling; go Karpathy-minimal
  fix + fabe test/fix, then hand to the **deploy command's emergency lane** (one change, alone) —
  `/code` still doesn't deploy it itself.
- **Personal projects** (Nako Pula, Tony, GRC, ACCA) → those have their own skills and their own
  rules; `/code`'s Alpha Direct conventions don't apply there.

---

*One line for Prathap: type `/code` and I'll understand the system, keep the work disciplined and
cheap, then test it — and stop, ready for you to deploy with your deploy command.*

---

## Build Log — record it (CFO instruction, 2026-09-09)

Everything Prathap asks for through this command MUST appear on his Build Log
(omni → Build log). He reads it at the end of a day to see what he asked for,
what went live, and what is still open. If this command does not write there,
his work lands in the "shipped, no request recorded" band and looks like it
was never asked for.

Run this the moment you pick the work up, and again when it is built:

    python C:\Users\PrathapAsus\.claude\scripts\devlog.py         --key cfo-YYYY-MM-DD-<short-slug>         --text "his request, IN HIS OWN WORDS — never a tidied summary"         --title "<short title>" --source code --area <omni area> --status building

    # when the code is built and tested, before it goes live:
    python C:\Users\PrathapAsus\.claude\scripts\devlog.py         --key cfo-YYYY-MM-DD-<short-slug> --status waiting

Rules:
- **--key must be the same every time** for one request. Same key = one row.
  A new key for the same ask shows as two outstanding jobs.
- **--text is his words, untouched.** A paraphrase is where "that is not what
  I asked for" starts.
- **NEVER --status live.** Only a recorded deploy may say live; omni refuses it
  and downgrades to waiting. Do not try to work around that — the refusal is
  the entire point of the log.
- If logging fails it prints a warning and exits 0. **Never let it stop the
  build** — bookkeeping is not worth losing his work over.

### Link the commit so the release can claim it
Put this trailer at the end of every commit message for this work, above the
Co-Authored-By line — a deploy links commits to a build item ONLY by this line,
never by matching words:

    Dev-Item: <the same key you used above>
