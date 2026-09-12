---
name: lane-c
description: Use when Prathap types "/lane-c" or says the subscription is exhausted, Anthropic/Claude is down, or he's offline and needs a build anyway. Ollama + DeepSeek only — no Claude involved at all, works fully offline.
---

# Lane C — survival mode

Part of the Cost Lanes discipline (see `[[reference_cost_lanes]]` memory). No Claude at all — this lane exists so Prathap can keep working when the subscription is exhausted, Anthropic is down, or there's no internet. Runs entirely on local Ollama models on this PC, with DeepSeek (through the gateway) as an optional cheap cross-check when a connection is available.

## When to use

- Prathap types `/lane-c`.
- He says something like "Claude's not working", "I'm offline", "the subscription is maxed out", or "I just need something built right now, don't wait."

## What to ask (one at a time, plain language)

1. **Build instruction** — the instruction to run per item.
2. **Unit list** — the items to run it over.

(No Opus/Fable gate exists in this lane — skip the objective-check question; just tell Prathap this lane is quick-and-local, not the full quality gate, and should be re-run through lane-a or lane-b later once the subscription/internet is back.)

## How to run it

```
C:\ai-cost-stack\gateway\venv\Scripts\python.exe C:\ai-cost-stack\workflows\lane_c.py --build "<build instruction>" item1 item2
```

Add `--offline` if Prathap says there's no internet at all, or if you already know the gateway/DeepSeek is unreachable — this skips the network entirely and cross-checks using a second local model instead.

This writes `C:\ai-cost-stack\workflows\candidates_c.json` with each item's build output and its (local or DeepSeek) cross-check.

## Report back to Prathap

Plain language: what got built, and a one-line reminder that this was the offline/survival lane — worth a quick re-check through `/lane-a` or `/lane-b` once he's back on the subscription.

---

## Build Log — record it (CFO instruction, 2026-09-09)

Everything Prathap asks for through this command MUST appear on his Build Log
(omni → Build log). He reads it at the end of a day to see what he asked for,
what went live, and what is still open. If this command does not write there,
his work lands in the "shipped, no request recorded" band and looks like it
was never asked for.

Run this the moment you pick the work up, and again when it is built:

    python C:\Users\PrathapAsus\.claude\scripts\devlog.py         --key cfo-YYYY-MM-DD-<short-slug>         --text "his request, IN HIS OWN WORDS — never a tidied summary"         --title "<short title>" --source lane-c --area <omni area> --status building

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
