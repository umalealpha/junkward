---
name: task-eta
description: >
  Report progress, an approximate ETA (EWMA-smoothed, with confidence band),
  and countdown/stall status for the currently running Claude Code task.
  Trigger when Prathap asks "how long", "ETA", "where are we", "is it stuck",
  "progress", or invokes /task-eta.
---

# Task ETA & Progress

Run the reader and show its output to Prathap (it is already written in plain
English):

```bash
python "C:/Users/PrathapAsus/.claude/prat-eta/eta-check.py"
```

Live countdown (tell Prathap to run this in a separate terminal window; it
refreshes every 3 seconds until he presses Ctrl+C):

```bash
python "C:/Users/PrathapAsus/.claude/prat-eta/eta-check.py" --watch
```

## Accuracy model (say this plainly if asked)
- Per-step time is smoothed with an Exponentially Weighted Moving Average
  (EWMA, alpha = 2/(N+1)). Recent steps weigh more, so the estimate adapts when
  the agent speeds up or slows down — better than a flat average.
- Before 2 live steps finish, it falls back to the MEDIAN per-step time from
  past runs of the SAME project (history.jsonl), so a number appears at once.
- Output is a fast..slow band from the observed spread, not false precision.
- History is built automatically: each completed run appends one line keyed by
  project directory. The more a given task type runs, the better the baseline.

## Caveats to state honestly
- Needs the task tracked as a to-do list. No list -> action count only, ETA n/a.
  Break work into a to-do plan first for an estimate.
- A single huge final step (e.g. a long deploy) after many small ones makes the
  point estimate optimistic — the "slow" end of the band covers this; mention it.
- The tracker only sees activity after the hook is installed and Claude Code has
  been restarted once.
