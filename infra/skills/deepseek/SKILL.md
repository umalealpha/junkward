---
name: deepseek
description: The DeepSeek oversight layer — an extra, independent quality check over Claude Code's work using DeepSeek's HIGHEST model (deepseek-reasoner), OFF the Claude subscription via the local gateway on :4000. Use when Prathap types /deepseek, says "have DeepSeek check this", "deepseek this", "second opinion", "add DeepSeek oversight", or asks to test/verify an Omni feature with DeepSeek. Sends the work Claude just produced (a claim, a diff, an answer, a plan, or an Omni feature) to DeepSeek for a strict verdict + concrete tests. Reuses the existing DeepSeek key (no new secret, nothing in chat). PII/secrets are blocked from leaving. Never rewrites code; returns APPROVE or REVISE with the issues and the tests that would prove it. Lighter than /fabe (which also builds, fixes and deploys) — this is a pure independent-review sanity layer that can run on ANY task.
---

# /deepseek — the DeepSeek oversight layer

**Why this exists.** Prathap wants a second, independent brain checking Claude Code's work on
**every kind of task**, not just code — an extra layer of quality control that argues back instead
of agreeing. This skill sends the work to **DeepSeek's highest model** and returns a strict verdict
plus the concrete tests that would prove or disprove it.

**Highest level of DeepSeek** = `deepseek-reasoner` (DeepSeek's top reasoning model), wired in the
gateway as the alias `builder-reason`. This skill always uses that model.

**Off the Claude subscription.** The call goes through the local cost gateway on `:4000`
(`C:\ai-cost-stack\gateway`), so it does **not** spend Claude quota. It reuses the **same DeepSeek
key already in the gateway** (the one Omni / the cost-stack already use) — **no new secret is created,
and no key is ever asked for or shown in chat.**

## Relationship to /fabe
- **/fabe** is the full ship gate for Omni/Graphite *code*: tripwires + real build/tests + a
  DeepSeek+Gemini+Fable panel, then it **fixes and deploys** to prod.
- **/deepseek** (this skill) is the lightweight, always-available **review-only** layer for **any**
  task (an email, an analysis, a number, a plan, an answer, a diff, an Omni feature). It never builds,
  never fixes, never deploys — it just gives an independent DeepSeek verdict + tests. Reach for /fabe
  when the thing needs shipping; reach for /deepseek for a fast independent sanity check.

---

## Preconditions
1. **Gateway present + up on :4000.** Check:
   `curl -s -o /dev/null -w "%{http_code}" http://localhost:4000/health/liveliness` → expect `200`.
   If not `200`, start it (background): `powershell -File "C:\ai-cost-stack\gateway\run.ps1"`, then re-check.
2. **DeepSeek key present.** The gateway `.env` must have a non-empty `DEEPSEEK_API_KEY`
   (already set — reused from the cost-stack / Omni). If it is empty, tell Prathap in plain words to
   paste it at `http://127.0.0.1:8787` (run `python C:\ai-cost-stack\gateway\keyentry.py` first if that
   page isn't up). **Never accept a key in chat.**

## What to feed it
Write the thing under oversight to a text file, then run the script. It can be:
- **A claim / answer / analysis** — did Claude actually get it right?
- **A code diff** — `git diff > work.txt`.
- **A plan** — will it actually meet the ask?
- **An Omni feature or change** — use `--mode omni` to get a real Omni test plan (entity isolation,
  IDOR, journal/company-NULL, balancing numbers, self-service PII, dual-control).

## Run it (gateway venv python)
```bash
"/c/ai-cost-stack/gateway/venv/Scripts/python.exe" \
  "$HOME/.claude/skills/deepseek/scripts/oversee.py" \
  --work /tmp/work.txt --ask "<the original request>" --mode review --round 1
```
- `--mode omni` → Omni-QA framing + a concrete step-by-step Omni test plan.
- `--ask "..."` → the original request, so DeepSeek can check the **whole** ask was met.
- `--round N` → which loop pass this is (see the loop below); each pass is appended to
  `%TEMP%\deepseek_loop.log` so the whole cycle can be reported.

**Output is strict JSON:**
```
{"verdict":"APPROVE"|"REVISE", "confidence":0-100,
 "issues":[{"severity","where","problem","fix"}],
 "missing":[...], "tests":[...], "summary":"...", "model":"deepseek-reasoner"}
```
- `verdict:"BLOCKED_PII"` → the work contained secrets or personal data and was **NOT** sent out.
  Redact and re-run, or review with Fable only.

---

## Steps when Prathap invokes /deepseek
1. **Confirm the gateway is up** (precondition 1). Start it if needed.
2. **Gather the work** into a file. Default = the work I just produced this turn (the claim/diff/answer).
   If a PR or files are named, use those (`gh pr diff <n>` / `git diff`). Fresh-start the loop log:
   `rm -f "$TEMP/deepseek_loop.log"` (or `del %TEMP%\deepseek_loop.log`).
3. **Run the LOOP** (this is the "like /fabe" fix-and-recheck cycle) — see below.
4. **Report to Prathap in PLAIN ENGLISH** (he is not a coder — global RULE #1):
   - Lead with the final verdict as one plain sentence ("DeepSeek agrees it's right, after N checks" /
     "DeepSeek still isn't happy — here's what's left").
   - The issues fixed and any still open, as plain one-liners, most serious first.
   - Say how many rounds it took (paste/summarise `%TEMP%\deepseek_loop.log`).
   - One line: this ran on DeepSeek, off the Claude subscription — no extra Claude cost.

---

## The loop (bounded fix-and-recheck — like /fabe)

Mirrors `/fabe` step 4: review → if REVISE, fix surgically → re-review → until APPROVE, **capped**.

```
round = 1
loop:
  run oversee.py --work <current work> --ask "..." --mode <review|omni> --round <round>
  verdict = result.verdict

  APPROVE      -> STOP. Done. Report "approved after <round> round(s)".
  BLOCKED_PII  -> STOP. Do NOT send. Redact or switch to Fable-only; tell Prathap what was found.
  ERROR        -> STOP. Panel/gateway failed; never treat an error as approval. Say so plainly.
  REVISE       -> if round == MAX_ROUNDS (=3): STOP. Report the still-open CRITICAL/HIGH items;
                    do NOT claim it passed.
                  else: fix ONLY the CRITICAL + confident-HIGH issues myself, surgically
                    (Karpathy K3 — touch only the lines the fix names, nothing else),
                    re-write the work file, round += 1, and loop again.
```

**Hard rules for the loop (do not violate):**
- **Bounded: `MAX_ROUNDS = 3`.** Never loop forever. Not APPROVE after 3 rounds → stop and report what's
  still open; the CAPS "I TESTED IT, IT WORKS PERFECTLY" line is NOT allowed while any CRITICAL/HIGH is open.
- **DeepSeek advises; I fix.** The fixes are mine, applied between rounds, so the work stays coherent.
  DeepSeek never edits code and never runs unattended.
- **Only fix CRITICAL + confident HIGH between rounds.** MEDIUM/LOW notes are reported, not chased in the
  loop (avoids churn and over-engineering).
- **Frozen numbers / journal-GL / PII flagged mid-loop → STOP and pause for the CFO.** Do not "fix" a frozen
  figure or a posted journal to make DeepSeek happy.
- **An ERROR is never a pass.** A dead gateway or unparseable reply stops the loop with a plain-English note.

---

## Rules (do not violate)
- **Highest DeepSeek only** — always `deepseek-reasoner` (`builder-reason`). Never silently downgrade.
- **Off-subscription** — always via the gateway on :4000. Never spend Claude quota to run DeepSeek.
- **Reuse the existing key** — the DeepSeek key in `C:\ai-cost-stack\gateway\.env`. Never create a new
  secret and never ask for or print a key in chat.
- **PII/secrets never leave** — the built-in guard blocks Omang/ID, bank accounts, and keys/passwords
  from being sent. Do not use `--allow-pii` to override it without a clear reason.
- **Review only** — DeepSeek advises; I do any fixing myself so the work stays coherent (Karpathy K3).
  This skill never builds, deploys, or edits prod.
- **Frozen numbers / journal-GL** — if DeepSeek flags a change to a frozen figure or a posted journal,
  that pauses for the CFO; do not "fix" it away.
- **Report in plain English** — lead with what it means and the one thing (if any) Prathap must decide.
