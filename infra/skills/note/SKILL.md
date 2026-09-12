---
name: note
description: Open the shared CFO/Claude notebook (the "read me first" page from omni). Use when Prathap types /note, says "show the notebook", "open the note", "what's in the notebook", or wants to read/check the settled facts, frozen numbers, or who's-who page.
---

# /note — open the shared notebook

The single source of truth Prathap and Claude share (who's who, frozen GWP/PAT,
what's been built, the traps). It lives in omni and BEATS omni's own database.

## What to do

1. Fetch it in one authenticated call:

   ```bash
   bash ~/.claude/read-notebook.sh
   ```

   This uses the local read-only, notebook-only key at `~/.claude/omni-notebook.key`.
   It returns the page as plain text (~2s).

2. Show Prathap the notebook content. If he just typed `/note` with nothing else,
   print the page. If he asked a specific question ("what's Bharath's title?"),
   answer from the page directly and quote the relevant line.

3. If the helper errors (missing key / non-200), say so plainly and point to the
   setup in `~/.claude/CLAUDE.md` RULE #0 — do not guess the notebook's contents.

## Editing

Read-only here. Prathap edits it in the browser at
https://omni.alphadirect.co.bw/notebook (only the CFO/EXCO/superusers can save).
The key this command uses cannot edit — by design.
