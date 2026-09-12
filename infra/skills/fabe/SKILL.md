---
name: fabe
description: The Fable 5.1 test (Windows build machine) — a consensus quality gate that TESTS, then FIXES, then safely DEPLOYS omni + Graphite changes. Use when Prathap types /fabe, or asks to "run the fable test", "fable-check this", or "ship this safely". Deterministic tripwires + the real build/tests are hard gates; a weighted off-subscription panel (DeepSeek 25% + Gemini 30% + OpenAI 30% via the C:\ai-cost-stack gateway :4000, plus a free local Ollama judge 15%) reviews; Fable 5.1 does its own independent pass, reads the weighted panel, and makes the FINAL call. If FIX, /fabe applies the ordered fixes surgically and re-tests to green, then deploys to prod via AWS SSM without clashing with parallel sessions (worktree cherry-pick, never rebase/force-push). Pauses for the CFO on frozen numbers / PII / journal-GL.
---

# /fabe — the Fable 5.1 test (test → fix → deploy) · WINDOWS build machine

> 🚫 **OMNI NEVER MOVES MONEY — never call an Omni change "money-critical" / "money movement" (CFO angry directive 2026-08-31, ~100th correction).** Omni moves ZERO money. The CFO authorises every real payment himself **in the FNB app, with 2-factor**. An Omni "payment / authorise / approve / mark-as-paid" is a WORKFLOW RECORD only — it never debits an account. So a payment-workflow change reviewed here is ordinary record/workflow code (a wrong record is a data bug — real, fix it — but NOT money moving); never frame it to him or in a verdict as money-critical. The "never move funds" hard-line below is about the ASSISTANT never executing a transfer, and about frozen numbers / PII / posted-GL — it is NOT a claim that Omni moves money. Real money egress = FNB + 2FA, by a human. See [[p-fnb-is-sandbox]].

**Why this exists.** Claude Code keeps repeating the same mistakes. This gate catches them BEFORE
they ship, using a panel that must agree with Fable 5.1 as the final decision maker — then it fixes
what's wrong and deploys it safely, and proves the live app survived.

> **ASK WITH A POPUP, never in the reply body (CFO directive 2026-08-07).** If at any point in the
> test → fix → deploy run you are confused, unsure, or hit a pause point (frozen numbers / PII /
> journal-GL, or an ambiguous fix), DO NOT bury the question in your message and wait. Use the
> **AskUserQuestion tool (the popup)**: state it plainly, offer clear options — usually **Yes / No** —
> with the **first option your recommended answer, labelled "(Recommended)"**.

> **🔴 DEPLOY CAREFULLY — CFO directive 2026-08-12. This is the top rule of the deploy step.**
> When you deploy, you carry two duties above shipping the change:
> 1. **Do not disturb anyone else's work.** Others share the same code checkout and push to the same
>    live system. Land your change on the LATEST main via a throwaway copy + cherry-pick — never rebase
>    the shared checkout, never force-push, never commit another session's uncommitted files. If the push
>    is rejected, re-fetch and retry cleanly — never force it.
> 2. **Do not crash the system.** Omni is a live insurance system people are using. Dry-run the deploy
>    first, deploy only a change that reached SHIP, then PROVE the site is still up (routes answer, error
>    window quiet) before calling it done. If anything looks down or spiking → **STOP and alert the CFO;
>    never auto-rollback a live database migration** — a human decides. When in doubt, pause and ask.

**This is the Windows-native build.** The AI stack lives at `C:\ai-cost-stack\gateway` (not the Mac's T7),
prod deploys via **AWS SSM** as the `claude-cli` profile (not Instance-Connect SSH), and every helper is
Python (no bash / `python3`-on-PATH assumptions). All scripts live in `scripts/` beside this file.

## How the verdict is weighted
- **Tripwires + machine check** — HARD GATES, not votes. A secret / frozen-number / PII grep hit, or a red
  build/test, ends it. No model argues with a grep or a failing test.
- **Off-subscription panel — four weighted judges** (none on the subscription):
  - **DeepSeek — 25%** (gateway :4000)
  - **Gemini — 30%** (gateway :4000)
  - **OpenAI — 30%** (gateway :4000)
  - **Ollama — 15%** (free LOCAL model `llama3.1:8b`, direct to Ollama — no key, nothing leaves the PC)
  They share 100% of the external opinion; `panel.py` reports each verdict plus the weighted result
  (>50% of the answering weight voting FAIL → panel says FAIL). If a judge errors, its weight is
  dropped and the rest renormalise.
- **Fable 5.1 — the final decision maker** (ON the subscription). Fable does its OWN independent full pass
  over the diff against `reference/omni-graphite-mistakes.md` + Karpathy, THEN reads the four weighted
  panel verdicts and adjudicates. Fable makes the final SHIP/FIX call and can override the panel. ONE
  pass, never looped, never builds.
- Consensus rule: **all judges should agree.** When they don't, the weighted panel result + Fable's
  independent finding settle it, and the split is reported so the CFO sees it.

---

## Preconditions
1. **Gateway present:** `C:\ai-cost-stack\gateway\` exists.
2. **Gateway up on :4000:** `curl -s -o /dev/null -w "%{http_code}" http://localhost:4000/health/liveliness`.
   If not `200`, start it: `powershell -File "C:\ai-cost-stack\gateway\run.ps1"` (background), then re-check.
   If a review key is empty in `C:\ai-cost-stack\gateway\.env` (`DEEPSEEK_API_KEY` / `GEMINI_API_KEY`), tell
   Prathap in plain words to paste it at `http://127.0.0.1:8787` (run `python C:\ai-cost-stack\gateway\keyentry.py`
   first if that page isn't up). **Never accept a key in chat.**
3. **Deploy creds:** `aws sts get-caller-identity --profile claude-cli` returns `user/claude-cli` (only needed at the deploy step).

## Input — what to test
Default = **current uncommitted changes** in the omni repo `C:\Users\PrathapAsus\work\alpha-finance`.
Also accepts a PR number, a branch diff, or named files. Graphite has its own repo.
If nothing is staged and nothing is named, ask the ONE thing: *what change do you want tested?*

---

## Steps

### 1. Gather the change + TRIPWIRES + machine check (FREE, deterministic — the hard gate)
```bash
cd /c/Users/PrathapAsus/work/alpha-finance
git fetch origin -q
git diff origin/main...HEAD > /tmp/fable_change.diff     # or: git diff (uncommitted), or gh pr diff <n>
```
**Tripwires FIRST (greps are truth):**
```bash
python "$HOME/.claude/skills/fabe/scripts/tripwires.py" /tmp/fable_change.diff   # exit 2 = hard pause
```
Emits `{hard_pause, hits:{secrets,frozen,pii,h5}}`:
- **secrets (H8)** → STOP. Never proceed with a key/password in the diff; get it removed + rotated.
- **frozen (C4)** → STOP + 🔴 NEED YOU (CFO sign-off). Do NOT deploy. (FY25 GWP 125.15M / PAT 0.292M; FY26 9M GWP 96.18M / PAT 0.950M.)
- **pii (C5)** → do NOT send the diff to the external panel; run **Fable-only**. 🔴 if it would deploy.
- **h5** (view without `permission_classes`) → advisory; feed it to Fable, not a hard stop.

Then the machine check (truth, not opinion), in the repo:
- models touched → `python manage.py makemigrations --check --dry-run` (must say "No changes detected")
- backend → import/build check + `pytest -q` on affected tests
- frontend → build (`--no-cache` if bundle staleness matters)

Record PASS/FAIL + actual output. **Red machine check = automatic FIX — skip the panel, report the failure.**

### 2. Off-subscription panel — DeepSeek 25% + Gemini 30% + OpenAI 30% + Ollama 15% (parallel, OFF subscription)
Skip this leg and go Fable-only if the PII tripwire fired.
```bash
"/c/ai-cost-stack/gateway/venv/Scripts/python.exe" \
  "$HOME/.claude/skills/fabe/scripts/panel.py" \
  --diff /tmp/fable_change.diff --system Omni
```
Emits `{deepseek, gemini, openai, ollama, agree, weighted, panel_error}`. All four judge against
`reference/omni-graphite-mistakes.md`. `weighted.verdict` is the 25/30/30/15 blend (>50% of the answering
weight voting FAIL → FAIL); an errored judge is dropped and the rest renormalise (so if the local
Ollama judge is slow or down, the three cloud judges still decide).
- `too_large: true` → diff over the panel limit; external leg skipped → run **Fable-only** on the full diff.
- `panel_error: true` → all external judges errored → treat as **Fable-only** and say so. Never let a dead panel pass as agreement.

### 3. Fable 5.1 — independent 50% review + FINAL verdict (SUBSCRIPTION, ONE pass, decision maker)
Pull recent history so Fable can spot repeat offences:
```bash
python "$HOME/.claude/skills/fabe/scripts/ledger.py" tail 5
```
Spawn ONE subagent with the **Agent tool, `model: fable`** (Fable 5.1 = `claude-fable-5-1`). Give it the FULL diff,
the machine-check result, both panel verdicts, the tripwire hits, and the ledger tail. Prompt:

> Senior review of an Alpha Direct {Omni|Graphite} change. You are the DECISION MAKER and make the FINAL call.
> The off-subscription panel is advisory and weighted DeepSeek 25% / Gemini 30% / OpenAI 30% / Ollama 15% (its weighted verdict
> is in `weighted`). FIRST do your OWN independent full pass over the diff against the common-mistakes checklist
> [paste `reference/omni-graphite-mistakes.md`] + the Karpathy guidelines — form your verdict before you trust anyone
> else's. THEN read the four external reviews (respect the 25/30/30/15 weighting when they disagree) and the machine-check
> result; where they disagree with each other or with you, adjudicate and say why — you may override the panel. Add anything both external brains missed; drop their
> false positives. If any issue is a class NOT already in the checklist (or a repeat you see in the ledger tail), name
> it and propose a one-line new checklist entry for the CFO to approve. Do NOT rewrite code. Return **SHIP** or **FIX**;
> if FIX, the exact ordered fixes (file:line + one-line fix); whether all judges agreed; any proposed new entry; and
> any item deferred to the human (C4 frozen / C5 PII / C6 journal-GL).

### 4. FIX — apply Fable's ordered fixes, re-test to green (only if verdict = FIX)
STOP and do NOT fix if any pending item is **C4 frozen numbers / C5 PII / C6 journal-GL** — those go to the CFO first
(🔴 NEED YOU). Otherwise:
- Apply Fable's ordered fixes **surgically** (Karpathy K2 — only the lines the fix names; touch nothing else).
- Small precise fixes on the main thread; a large mechanical batch → `/lane-b`.
- **Re-run steps 1→3** on the fixed diff. Bounded: **max 2 fix rounds.** Must reach **SHIP**.
- Still not SHIP after 2 rounds → stop, do NOT deploy, report what's still red.

### 5. DEPLOY — via AWS SSM, without clashing with parallel sessions (only when SHIP)
The `alpha-finance` checkout is SHARED — another session also pushes to `origin/main`. **Never rebase the shared
checkout; never force-push.** Land your fix on the LATEST main via a throwaway worktree + cherry-pick:
```bash
cd /c/Users/PrathapAsus/work/alpha-finance
git add -p && git commit -m "fix: <what Fable fixed>"
git fetch origin -q
FIXSHA=$(git rev-parse HEAD)
git worktree add /tmp/fabe-land origin/main
cd /tmp/fabe-land && git cherry-pick "$FIXSHA"          # resolve conflicts HERE, not in the shared tree
git push origin HEAD:main                                # fast-forward; if REJECTED → re-fetch, re-cherry-pick, retry (never --force)
MAINSHA=$(git rev-parse HEAD)
cd /c/Users/PrathapAsus/work/alpha-finance && git worktree remove /tmp/fabe-land
```
Then deploy that main to prod (EC2 `i-02a5d76a61f4f09a5`, af-south-1) via SSM. **Dry-run first** (prints the exact
remote script, sends nothing), then `--confirm`:
```bash
python "$HOME/.claude/skills/fabe/scripts/deploy_ssm.py" --backend --expect-sha "$MAINSHA"            # DRY RUN
python "$HOME/.claude/skills/fabe/scripts/deploy_ssm.py" --backend --expect-sha "$MAINSHA" --confirm  # go
```
- Migration changed → keep `--backend` (rebuilds the image; entrypoint auto-migrates — never just restart).
- Frontend changed → add `--frontend` (`--no-cache` if the bundle can be stale).

### 6. Prove it live (machine, not prose)
```bash
python "$HOME/.claude/skills/fabe/scripts/postdeploy_ssm.py" --minutes 10 --threshold 15
```
- Public routes answer + on-box backend error window is quiet → healthy.
- A route down or an error spike → 🔴 alert the CFO. **NEVER auto-rollback** a live insurance DB migration; a human decides.
- The frozen **GWP 125.15M tile** needs an authenticated browser (no omni token on this PC): confirm it visually via
  the OmniDesktop app or Claude-in-Chrome as the final step, and report what you saw.

### 6b. Role QA — prove it works for the REAL PERSON who uses it (CFO directive 2026-08-22, mandatory)
A green deploy + quiet error window proves the app is *up*, NOT that the change does what the affected
staff member needs. So after step 6, ALWAYS verify the change **as the real role that uses it** — the
last mile that keeps catching us (Bokani's "buttons gone"). Do the smallest honest version of:
1. **Whose feature is this?** Name the role/person the change is for (a reviewer, a payroll clerk, an agent…).
2. **Confirm their live access + state**, read-only, on prod via SSM Django shell: does their account resolve
   to the right role/stage/permission, and is there real data for them to act on right now? (e.g. `user_stages`,
   `can_*`, their queue counts.) The notebook/access model is the source of truth.
3. **See it through their eyes** where a session exists: `e2e/eyes-on.mjs "<route>"` (admin vs non-admin) or
   `e2e/qc.sh "<route>"` (read-only) — screenshot the changed screen and the pop-ups it opens, and LOOK.
4. **State plainly what that role can and cannot see/do** — and if a control legitimately isn't showing
   (empty queue, nothing at their stage), say so, don't call it a bug. **Never write test data to prod** to
   force a control to appear; explain the precondition instead.
Report the Role-QA finding in the close-out. If the feature can only be seen by clicking as that exact person
and no session exists, say what was verified (access + data by query) and what still needs their own click.

### 6c. Task-Completion QC — independent, free (the "half-done" catcher, CFO directive 2026-08-26)
The CFO's biggest complaint: work reported "done" that is half done. This step is an INDEPENDENT,
ADVERSARIAL audit of completion — it does NOT trust anything the main agent said, including its own
step-6/6b claims. It costs no Claude quota: deterministic tools + the off-subscription panel only.

1. **Restate the task list.** Go back to the CFO's ORIGINAL instruction (his message, not the plan
   that was derived from it) and parse it into a numbered list of every distinct thing he asked for,
   in his words. No merging, no dropping, no "implied by". Half-done work hides in a shortened list —
   the list comes first so it can't.
2. **Adversarially test each task.** For each item, actively try to prove it is NOT done, using only
   free evidence from the LIVE running thing — never code reading, never the agent's own report:
   - the machine check (makemigrations --check, `pytest -q` on affected tests, frontend build);
   - `e2e/qc.sh "<route>"` on every screen the task touches (render, JS errors, failed calls, a11y, speed, write-refused);
   - `e2e/eyes-on.mjs "<route>"` where the task is role-visible (admin vs real staff view);
   - read-only prod probes via SSM Django shell where the task is data/behaviour (does the record/flag/queue actually exist now?);
   - the served bundle/DOM, never git HEAD.
   Evidence = an exit code, a screenshot, or a query result. "I implemented it" is not evidence.
3. **Cross-examine off-subscription.** Feed the numbered task list + the collected evidence (never
   PII) to the weighted panel via `panel.py --system Omni` with one question: *"For each task, does
   the evidence prove completion — which tasks lack proof?"* DeepSeek/Gemini/OpenAI answer off the
   subscription; a task the panel can't see proof for is PARTIAL at best.
4. **Verdict per task:** **DONE** (evidence in hand) / **PARTIAL** (some proof, gaps named) /
   **NOT DONE** — plus whether the task went through this fabe run's gates. A verdict with no
   evidence line is invalid; downgrade it.
5. **Consequences.** Any PARTIAL/NOT DONE → back to step 4 (FIX, same 2-round bound) or reported
   honestly as unfinished at the TOP of the close-out — never buried, never rounded up to "done".
   Log the per-task verdicts to the ledger (`ledger.py`). Emit the **side-by-side box** (step 7) and
   the **re-test runbook** — this runbook IS the Rule-12 evidence, extended per task; don't
   write a second one.

### 6d. Independent QC — RUN IT HERE. Do NOT queue Manus. (CFO, 9-Sep-2026)

> 🚫 **MANUS QC IS STOPPED.** Decided 9-Sep-2026, recorded in MACHINE-TALK and in memory
> `p-omni-ux-qc`. **Do not run `scripts/queue_manus_qc.py`.** Filing a `qc_requested=True`
> row now asks a service that no longer polls, so the row sits open on the CFO's bug board
> for ever, emails him, and — worst of all — reads like the change has an independent check
> waiting on it when nothing is coming. That is a false assurance, which is worse than no
> assurance. The helper script is kept only so old rows can be understood; it is not to be
> called. (Burn: 9-Sep-2026, three rows filed across three deploys, the last one 23 minutes
> after the change was logged, because this section still said "mandatory".)

**What replaced it: the QC is done HERE, on this machine, by this run.** The Mac Mini M4 and
the Windows PC both already carry the tools, and they are stronger than the old loop because
they run BEFORE the close-out rather than hours later:

```bash
cd "$HOME/.claude/skills/prat-skill/e2e"
bash qc.sh "/the/changed/route"          # render, JS errors, failed calls, axe, speed, write-refused
node eyes-on.mjs "/the/changed/route"    # the same screen as admin AND as ordinary staff
node a11y-names.mjs /route1 /route2      # WHICH controls have no name, not just how many
```

Then **READ the screenshots** — a verdict you have not looked at is not evidence (rule 12).

**The close-out must carry the QC EVIDENCE, not a QC promise.** Where the old close-out
printed a row URL for a finding that would "land later", print what you actually saw: the
`qc.sh` verdict per changed screen, what the screenshots showed, and the live probes you ran.
If a check could not be run, say which and why — never imply someone else will catch it.

**If the CFO wants a genuinely independent second pair of eyes**, that is Fable at step 3, or
a fresh session briefed to disprove the work. Both are real. A queued row to a stopped service
is not.

### 7. Record + learn + report
**Ledger (audit trail + repeat-offence memory):**
```bash
python "$HOME/.claude/skills/fabe/scripts/ledger.py" log --system Omni \
  --diff-hash "$MAINSHA" --verdict SHIP --issues '["H6"]' \
  --fixes '["payroll.py:15 remove except:pass"]' --deploy-sha "$MAINSHA" --postdeploy OK --note "..."
```
**Learning loop — if Fable proposed a NEW mistake class:** queue it for a one-line CFO yes.
```bash
python "$HOME/.claude/skills/fabe/scripts/checklist.py" propose --id L1 --severity HIGH --title "..." --detail "..."
# CFO approves → lands forever:  python .../checklist.py approve L1
```

**Task-Completion box — REQUIRED in every /fabe close-out, above everything except a 🔴 line.**
One row per task from the CFO's original message, his words in column 1. Plain English only.

| # | You asked for | Done? | Proven by | Tested via /fabe? |
|---|---|---|---|---|
| 1 | (task, in his words) | ✅ / 🟡 partial / ❌ | (one plain line of evidence) | ✅ / ❌ |

Worked example:

| # | You asked for | Done? | Proven by | Tested via /fabe? |
|---|---|---|---|---|
| 1 | "Add the refund button for claims staff" | ✅ | Clicked it live as claims staff — refund request appeared in the queue | ✅ |
| 2 | "Email me when a refund is over P10,000" | 🟡 partial | The email rule exists, but a live test refund of P12,000 sent nothing | ✅ |
| 3 | "Take the old refund page down" | ❌ | Old page still opens on the live site | ❌ |

Rules for the box: 🟡 and ❌ rows say in the "Proven by" cell exactly what is missing; a ✅ is only
allowed with real evidence (a click, a screenshot, a query, a green test) — never "code was written".

**Re-test runbook — write it for the NEXT person or session, not for Manus** (extends Rule 12;
ONE runbook per fabe run, ONE section per task — do not write a second). Manus QC is stopped
(9-Sep-2026); this is now a hand-over so a fresh session, the Mac seat, or the CFO can re-run
every check independently. Keep it exact enough that somebody who was not here can follow it:

```
# Re-test runbook — independent check
Run: <date, Botswana time> · System: <Omni | Graphite> · Deployed commit: <sha> · fabe verdict: <SHIP/FIX>

You are the independent checker. Do NOT trust this runbook's verdicts — re-run every test
yourself and report what YOU saw. Read-only: never write, change or delete live data.

## Task <n>: "<the CFO's task, in his words>"
- Where it lives: <exact URL/route on the live site, or module/screen name> (and the role that should see it)
- What changed: <one plain sentence — what should now exist/behave differently>
- Steps to test:
  1. <exact click-path or command, one action per step>
  2. <inputs to try — one normal case AND one edge case (empty, too big, wrong role)>
- Expected result (pass looks like): <exactly what should appear/happen, incl. exact text/numbers>
- Fail looks like: <the old/broken behaviour, so a regression is recognisable>
- fabe's own evidence: <screenshot name, qc.sh exit 0 on <route>, query result>
- Your verdict: PASS / FAIL / BLOCKED (+ what you saw, screenshot if possible)

## Feedback
Send results back to Prathap: one line per task (PASS/FAIL + what you saw), failures first.
If every task passed, say so in one line. If anything was BLOCKED, say what blocked you — don't guess.
```

**Report to the CFO — PLAIN ENGLISH (he is not a coder; global RULE #1):**
- **What happened:** tested → (fixed N things) → deployed + verified, or where it stopped and why.
- **Verdict:** ✅ SHIP or 🔧 FIX(ed) — fixes as plain one-liners, most important first.
- **Agreement:** "all agreed" or "panel split — weighted 25/30/30/15 said X, Fable ruled Y because…". Note Fable-only runs (PII / too-large / dead panel).
- **Live proof:** routes up, error window quiet, GWP 125.15M tile confirmed.
- **Role QA (step 6b):** what the real person this is for can now see/do, confirmed on prod — and any precondition (e.g. nothing at their stage yet) stated plainly.
- **QC evidence (step 6d):** what you actually SAW — the qc.sh verdict per changed screen, what the screenshots showed, the live probes run. NOT a promise that somebody will check later. Manus QC is stopped (9-Sep-2026); never file a qc_requested row.
- **Clash note:** was main behind? landed via cherry-pick without disturbing the other session.
- One line: the panel ran off-subscription; only Fable's single pass used Claude quota.
- If anything hit C4/C5/C6 → 🔴 **NEED YOU** line at the TOP (frozen number / PII / journal — your sign-off), and it was NOT deployed.

---

## Rules (do not violate)
- **🔴 DEPLOY CAREFULLY (CFO 2026-08-12):** never disturb another person's work (no rebase/force-push on the
  shared checkout, no committing others' files — land via worktree + cherry-pick on latest main) and never
  crash the live system (dry-run first, prove the site is up after, alert-not-rollback on any problem, pause when unsure).
- **Fable makes the final call.** The panel is advisory, weighted DeepSeek 25% / Gemini 30% / OpenAI 30% / Ollama 15% (the last a free local judge). All judges should agree; if not, the weighted panel + Fable's independent finding settle it, the call stands, and the split is reported. Fable may override the panel.
- **Role QA is mandatory after every deploy (CFO 2026-08-22).** A green deploy is not "done" — step 6b verifies the change works for the REAL role/person who uses it (confirm their live access + data, see it through their eyes where a session exists, state plainly what they can/can't do). Never force a control to appear by writing test data to prod; explain the precondition instead.
- **Task-Completion QC is mandatory (CFO 2026-08-26).** Step 6c is an INDEPENDENT, FREE, adversarial audit that restates every task from the CFO's ORIGINAL message and tries to prove each one is NOT done from live evidence — it never trusts the main agent's own "done" claim. Every close-out carries the side-by-side Task-Completion box (task / Done? / proven-by / tested via fabe?) and hands over the re-test runbook. A ✅ needs real evidence; PARTIAL/NOT-DONE tasks are reported at the TOP, never rounded up to "done".
- **Tripwires + machine check are truth**, never a model's opinion. A secret / frozen-number / PII hit, or a red test, is a hard stop.
- **test → fix → deploy**, but deploy ONLY a change that reached SHIP, and NEVER one with a pending C4/C5/C6 — those pause for CFO sign-off.
- **Never clash a parallel session:** land via a fresh worktree + cherry-pick onto latest `origin/main`; never rebase the shared checkout, never force-push. Deploy via SSM (`claude-cli`); migrations REBUILD the backend image.
- **Off-subscription panel only.** DeepSeek + Gemini + OpenAI via :4000. Only Fable's one pass touches Claude quota.
- **PII never leaves to the external panel.** Frozen numbers / journal entries → defer to CFO.
- **Never auto-rollback.** Post-deploy problems ALERT a human.
- **The checklist grows only with CFO approval** (learning loop); capped, pruned quarterly.
- **Keys stay in `gateway\.env`;** never in chat, never in this file.
- **Report to Prathap in plain English** — lead with what it means and the one thing he must decide.

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

### CLOSED (2026-09-11) — the deploy now records its own release
`devlog_deploy` shipped 9-Sep with a docstring claiming the deploy called it;
nothing did, so "Finished today" could never fill. #780 wired it into
`infra/host/deploy-zero-downtime.sh` — **and that fixed only half of it**, because
THIS Windows path does not run that script at all: `deploy_ssm.py` does its own
git reset + compose build + up over SSM. The guard tests watched the one caller
they knew about and stayed green while most of the CFO's own releases went
unrecorded.

Now both paths call one shared script, `infra/host/record-release.sh`. If you ever
add a THIRD deploy route, it must call that script too — the previous commit is
kept in `/var/lib/alpha-finance/last-deployed-sha` because every caller has already
reset the repo by then, and recording can never fail a deploy (it exits 0 always).

Still true, and the reason this log is trustworthy: **never pass `--status live`
from a skill.** Only a recorded release may say something is live.
