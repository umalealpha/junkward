---
name: bug
description: Prathap's FAST LANE for fixing a bug. Use whenever he types "/bug", or says "fix this bug", "this is broken", "why is X not working", "this page errors", "wrong number on screen" — anything that is repairing existing behaviour rather than building something new. Target 5-15 minutes, not an hour. Deliberately skips the heavy /code chain (lane-b batch build, the 5-model fabe panel) and instead does: reproduce -> find the exact line with Serena -> smallest possible change -> a test that goes RED without the fix -> targeted test run + tripwires. Escalates to /code + /fabe when the change turns out to be big or touches a hard gate. Does NOT deploy.
---

# /bug — the fast lane

**Why this exists.** `/code` runs four skills and asks five models to vote. That is right for a new
module. On a one-line bug it turned 10 minutes into an hour (measured, 2026-09-09). `/bug` is the
small-job lane. Same discipline, a tenth of the ceremony.

> 🚫 **OMNI NEVER MOVES MONEY.** An Omni "payment / authorise / approve / mark-as-paid" is a
> WORKFLOW RECORD only — it never debits an account. Real money egress is FNB + 2FA, by a human.
> So Omni payment code is ordinary record/workflow code and a bug in it is a data bug, never
> "money movement". Never describe it that way. See [[p-fnb-is-sandbox]].

---

## Step 0 — the size gate (10 seconds, do it first)

Answer these before touching anything:

| Question | Yes → |
|---|---|
| Does it touch a frozen number, the MA/revenue format, or GL mapping? | 🛑 **STOP** — popup to Prathap, then `/code` |
| Does it touch real personal data (Omang, bank details, addresses, medical)? | 🛑 **STOP** — popup, then `/code` |
| Is it an access/permission change, a data deletion, or a schema migration? | 🛑 **STOP** — popup, then `/code` |
| Is this actually a NEW feature dressed up as a bug? | → `/code`, not here |
| Will the fix plausibly touch more than ~3 files? | → `/code`, not here |

Everything else: stay in `/bug`. **Read the notebook only if the bug is about a FACT or a figure**
(`bash ~/.claude/read-notebook.sh`) — not for a broken button or a crash. That read is the right
habit for `/code`; on a fast fix it is dead time.

---

## Step 1 — reproduce it, in one command (do not skip)

Get the bug to happen in front of you: the failing test, the error in the log, the wrong value on
the page. **A bug you have not seen fail is a bug you cannot prove you fixed.**

- Omni page / screen → drive it in the browser (`preview_start` / the QC account per
  [[f-qc-acct-for-shots]]). Never trust a description of the symptom.
- Backend → the actual traceback, from the actual log, not a guess at it.
- Wrong figure → the query that returns the wrong figure.

If you genuinely cannot reproduce it in ~3 minutes, say so in one line and ask Prathap for the
one thing you need (the screen, the policy number, the exact time it happened) with a popup.

## Step 2 — find the line with Serena, NOT with grep (this is the big time saver)

This is where the hour usually goes. Use the code-search tools that jump straight to the symbol:

- `mcp__serena__find_symbol` — the function/class by name
- `mcp__serena__find_referencing_symbols` — everything that calls it
- `mcp__serena__get_symbols_overview` — the shape of a file without reading all of it
- `mcp__serena__get_diagnostics_for_file` — the language server's own errors

Only fall back to `Grep` for strings that aren't symbols (a bit of UI text, a settings key).
**Never read a whole large file to "get oriented".** Read the function, its caller, its test.

## Step 3 — root cause, not symptom

Invoke the **systematic-debugging** skill's Iron Law: *no fix without root cause first.* One
sentence, out loud, before you edit: **"It breaks because ___, at `file:line`."**

If you cannot finish that sentence, you are guessing. Keep reading. Two symptom-fix attempts in a
row means stop and escalate to `/code`.

## Step 4 — smallest possible change

Karpathy discipline (already always-on): surgical. Change only the lines that trace to the root
cause. No tidying, no renaming, no "while I'm in here". If the fix wants to be a refactor, that is
a `/code` job — fix the bug now, and flag the refactor separately with `spawn_task`.

## Step 5 — prove it RED then GREEN (non-negotiable, his rule, violated 17 times)

1. Write or point to the test that covers the bug.
2. **Revert the fix. Run the test. Watch it FAIL.** Paste the failure.
3. Re-apply the fix. Run the test. Watch it PASS.
4. Run the surrounding test file too, so you know you broke nothing next door.

A test that passes both with and without the fix proves nothing and does not count.

## Step 6 — the cheap safety net (seconds, not a panel)

Instead of the five-model `/fabe` panel, run the deterministic scanner on your own diff:

```
git diff > "%TEMP%\bugfix.diff"
python "C:\Users\PrathapAsus\.claude\skills\fabe\scripts\tripwires.py" "%TEMP%\bugfix.diff"
```

- **Exit 0** → done. Report and stop.
- **Exit 2** (a frozen number, personal data, or a secret in your added lines) → 🛑 hand the whole
  thing to `/fabe` and popup Prathap. Do not talk yourself past a tripwire.

Also run the project's linter/formatter if the repo has one wired (respect
[[f-ruff-skip-exist]] — don't reformat files you didn't touch).

## Step 7 — hand over, don't deploy

`/bug` **never** puts anything live — same rule as `/code`. Leave the fix committed and proven.
Deploying is Prathap's separate `/deploy` step. Fill in `Deploy/CHANGE-LIST.md` so other chats know
what you touched.

---

## When to bail out to the slow lane

Say it in one plain line and switch — bailing out early is cheap, an hour of thrash is not:

- Root cause not found after ~15 minutes of real searching.
- The fix has grown past ~3 files, or is turning into a redesign.
- Two attempted fixes did not hold.
- A tripwire fired, or a Step 0 gate turned out to be true after all.

## What to report to Prathap

Four short lines, plain English, no jargon:

1. **What was broken** — in his words, what he would have seen on screen.
2. **Why** — one sentence.
3. **Proof** — "the test failed before the fix, passes after" (+ the screenshot if it's a screen).
4. **What's next** — "ready for /deploy", or the one thing you need from him.

Never say "fixed" without Step 5's red-then-green in hand.

---

## Build Log — record it (CFO instruction, 2026-09-09)

Everything Prathap asks for through this command MUST appear on his Build Log
(omni → Build log). He reads it at the end of a day to see what he asked for,
what went live, and what is still open. If this command does not write there,
his work lands in the "shipped, no request recorded" band and looks like it
was never asked for.

Run this the moment you pick the work up, and again when it is built:

    python C:\Users\PrathapAsus\.claude\scripts\devlog.py         --key cfo-YYYY-MM-DD-<short-slug>         --text "his request, IN HIS OWN WORDS — never a tidied summary"         --title "<short title>" --source bug --area <omni area> --status building

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
