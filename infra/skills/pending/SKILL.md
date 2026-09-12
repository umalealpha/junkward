---
name: pending
description: Prathap's "did you do everything I asked?" check. Use whenever Prathap types "/pending", or says "recap", "what did you miss", "did you do all of it", "where are we on my list", or when a job with several instructions is being wrapped up. Scans the whole conversation, pulls out every instruction Prathap gave, and shows a clear tick-box of asked vs done vs missed, then a Fable 5.1 pop-up recommending what to do about anything still open. Also runs live mid-job to stop instructions being forgotten.
---

# /pending — catch every instruction, prove what got done

**The problem this fixes:** Prathap gives ten instructions, five get done, five get quietly
forgotten. `/pending` makes that impossible to hide. It reads the whole chat, lists every single
thing he asked for, and marks each one Done / Half / Not done in one clear box — with the receipts.

There are two ways this runs. Do both when you can.

## Auto-run (ON by default — Fable 5.1's call, approved 2026-08-31)

`/pending` is not only a command Prathap types. It runs **automatically**:

- **Turn it on at the start of every session** (it is auto-loaded via CLAUDE.md), and switch on live
  tracking (section A) immediately.
- **Run the recap box (section B) on your own** whenever you finish a batch of Prathap's work or the
  job is being wrapped up — without waiting for him to type `/pending`. The sessions where he'd forget
  to ask are exactly the ones where something got dropped.
- **Stay quiet when there were no real instructions.** If the session was just a question or chit-chat
  with nothing to track, do NOT show an empty checklist. No box, say nothing about it.

Prathap can still type `/pending` any time to force it — mid-job, or to re-check.

## A. Live tracking (prevents the drop)

The moment `/pending` is active, treat every instruction Prathap gives as a tracked item:

1. When he sends a message with tasks in it, **immediately put each task into your TodoWrite list as
   a separate numbered item** — even the small ones, even the "oh and also…" at the end of a message.
2. Split a multi-part message into multiple items. "Build X, fix Y and email Z" = three items, not one.
3. Tick each item off only when it is **actually done AND verified** (file written, page seen working,
   email sent) — never when you merely intend to do it.
4. Never close the job while any item is still open without saying so out loud.

This is the real fix — the box at the end only *reports* drops; live tracking *prevents* them.

## B. The recap box (proves it)

Whether asked mid-job or at the end, scan the **entire conversation from the start** and rebuild the
full list of what Prathap asked for. Then show this box.

**What counts as an instruction:** any explicit ask, request or task from Prathap — "build…", "fix…",
"add…", "send…", "check…", "also do…", "make it…". Split multi-part asks. **Do not** count questions
he asked purely for information, or chit-chat.

**Status — be strict and honest:**
- ✅ **Done** — finished *and* verified with your own eyes (saw it work / file saved / message sent).
- ⚠️ **Half** — started, partly done, OR done but not yet verified. Say what's left.
- ❌ **Not done** — never actioned, or started and dropped. Say where it slipped.

**The box format** (headline line first, then the table):

> **You asked for N things. ✅ X done · ⚠️ Y half · ❌ Z not done.**

| # | What you asked for | Status | Note (only for ⚠️ and ❌) |
|---|--------------------|--------|---------------------------|
| 1 | … | ✅ Done | |
| 2 | … | ⚠️ Half | what's left, in one line |
| 3 | … | ❌ Not done | why it slipped, in one line |

Rules for the box:
- **List every item, done ones included** — he wants to see the whole picture, not just failures.
- **Put the ❌ and ⚠️ rows at the top** so the misses hit him first (his "lead with what doesn't work").
- **Plain English, no jargon.** Money in pula. One line per note, no essays.
- **No claiming done without proof.** If you can't point to evidence it worked, it is ⚠️, not ✅.

## C. The Fable 5.1 pop-up recommendation

After the box, if anything is ⚠️ or ❌:

1. **Hand the open items to Fable 5.1 to make the call.** Spawn a subagent with `model: "fable"`
   (Agent tool), give it the list of not-done / half-done items plus one line of context each, and ask
   it for **one recommended next action** and a one-sentence why. Fable makes the final call — same as
   Prathap's normal "Fable does the final review" pattern.
2. **Show that recommendation as a pop-up** (AskUserQuestion tool), recommended option first and
   labelled "(Recommended)", following the `/reco` style — the recommended option explained in full,
   the "No / not now" option kept short. One tap and he decides.
   - Typical shape: *"3 items still open. Want me to finish them now?"* → **Yes, finish them now
     (Recommended)** vs **No, leave it for now.**
3. If **everything is ✅**, skip the pop-up. Just say so plainly — "All N done and checked, nothing open."

## D. Survive a cut-off (memory)

If any item is still ❌ or ⚠️ when the box is shown, **write the open items to memory** so they aren't
lost if the chat ends or gets summarised. One memory file, `project` type, listing the open items and
which session they came from. Update or clear it when they're later done. This means a fresh session can
pick up exactly what was left hanging.

## Quick reference

| When | Do |
|------|----|
| `/pending` typed early / mid-job | Turn on live TodoWrite tracking (A), then show the box so far (B) |
| `/pending` typed at the end | Scan whole chat, show the box (B), Fable pop-up (C), save open items (D) |
| Everything done | Show the all-✅ box, say "nothing open", no pop-up |
| Something open | ❌/⚠️ rows on top, Fable recommends, pop-up asks to finish now |

## Common mistakes to avoid
- **Marking ✅ without proof.** "I wrote the code" is not "I saw it work." That's ⚠️.
- **Merging several asks into one row** so a dropped one hides inside a done one. Split them.
- **Only listing failures.** He wants the full picture with ticks, not just a problem list.
- **Burying the recommendation in your message text.** It must be the pop-up, or he'll miss it.
- **Forgetting the tiny "and also…" ask** at the tail of a long message — those are the ones that drop.

*One line for Prathap: type `/pending` any time and I'll show you every single thing you asked for in
this chat, tick off what's really done, flag what I missed, and hand you a one-tap choice to finish
the rest.*
