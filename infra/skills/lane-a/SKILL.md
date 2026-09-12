---
name: lane-a
description: Use when Prathap types "/lane-a" or asks for the all-subscription Cost Lanes build (must-be-right work, no external API keys). Haiku builds, Opus verifies, Fable does the final review — everything runs on the Claude subscription, nothing metered.
---

# Lane A — all-subscription quality gate

Part of the Cost Lanes discipline (see `[[reference_cost_lanes]]` memory). Zero external keys used. Everything runs through the **Workflow** tool on the Claude subscription: Haiku builds each item, Opus verifies (concurrently), Fable does the final review. Fable never rebuilds — it only flags; flagged items go back to Haiku for a fix, then re-review, max 2 rounds.

## When to use

- Prathap types `/lane-a`.
- He asks for work that "must be right" and doesn't mention DeepSeek/Gemini/offline.

## What to ask (one at a time, plain language)

1. **Build instruction** — what should be drafted/built, for each item? (a short instruction, e.g. "Draft a cover note for {item}")
2. **Unit list** — the list of things to run it over (e.g. policy numbers, file names, claim IDs).
3. **Objective check** — how do we know a result is actually right? Must be a plain, checkable fact (e.g. "the numbers must balance to the trial balance", "the policy number must exist in Graphite"), not a vibe.

If Prathap has already given all three in his message, don't re-ask — just confirm your understanding in one line and proceed.

## How to run it

Call the **Workflow** tool with a script built on this pattern (reference: `C:\ai-cost-stack\workflows\cheap-swarm.template.js` — read it for the exact shape, then write a real script substituting the actual build prompt, item list, and check description; do not pass the template's `{{...}}` placeholders literally):

- Phase "Build": `agent(buildPrompt, {model: 'haiku', phase: 'Build'})` per item, via `pipeline()`.
- Phase "Verify": `agent(verifyPrompt, {model: 'opus', phase: 'Verify'})` per item — checks the Haiku draft against the objective check.
- Loop up to 2 rounds: anything Opus flags as FAIL goes back to Haiku with the reviewer notes, then re-verify.
- Phase "Review": one `agent(..., {model: 'fable'})` call doing the final pass over everything that's left, confirming each item meets the objective check.

## The gate itself

The pass/fail line is the objective check Prathap gave you — a fact you can verify (numbers balance, record exists, file matches schema), never "the model said it looks good." If nothing objective was given, say so before running anything, and ask for one.

## Report back to Prathap

Plain language, short: which items passed, which needed a fix-round, and the one thing left for him to decide if anything is still flagged after 2 rounds.

---

## Build Log — record it (CFO instruction, 2026-09-09)

Everything Prathap asks for through this command MUST appear on his Build Log
(omni → Build log). He reads it at the end of a day to see what he asked for,
what went live, and what is still open. If this command does not write there,
his work lands in the "shipped, no request recorded" band and looks like it
was never asked for.

Run this the moment you pick the work up, and again when it is built:

    python C:\Users\PrathapAsus\.claude\scripts\devlog.py         --key cfo-YYYY-MM-DD-<short-slug>         --text "his request, IN HIS OWN WORDS — never a tidied summary"         --title "<short title>" --source lane-a --area <omni area> --status building

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
