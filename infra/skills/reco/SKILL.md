---
name: reco
description: Prathap's decision-question style. Use whenever Prathap types "/reco", or asks for "a recommendation" / "give me yes or no" / "recommended answer". While active, EVERY question put to Prathap is a Yes/No popup (AskUserQuestion tool) with the recommended option first and labelled "(Recommended)", and the recommended option is explained IN DETAIL — the No option stays brief. Prathap reads on his phone and wants to decide fast with the full reasoning on the option he should pick.
---

# /reco — how to ask Prathap for a decision

Prathap wants every decision handed to him the same way: **a simple Yes or No, with a clear
recommendation, and the recommended answer explained in full so he can decide without asking back.**

## The rule — apply to every question you put to him

1. **Always use the popup** (AskUserQuestion tool), never a question buried in your message text —
   he misses those.
2. **Offer Yes / No** (two options) unless the decision genuinely has more than two real choices.
3. **The recommended option comes FIRST and is labelled "(Recommended)"** in its title.
4. **Write the recommended option's description IN DETAIL** — this is the point of `/reco`. It should
   cover, in plain English:
   - what will happen if he picks it,
   - why you recommend it (the reasoning / trade-off),
   - any cost, risk, or thing he should know before saying yes.
   Enough that he can decide from the popup alone, without a follow-up question.
5. **Keep the other option (usually "No") short** — one plain sentence on what happens if he declines.
6. **Plain English, no jargon** (Prathap is non-technical). Money in pula, stated plainly.
7. **One decision at a time.** If several decisions are needed, ask the most important one first;
   don't stack four popups at once unless they're truly independent and quick.

## What "in detail" means (example shape)

- **Yes option title:** `Yes — <the action> (Recommended)`
- **Yes option description (detailed):** "This will <what happens>. I recommend it because <reason /
  trade-off>. Note: <cost / risk / thing to know>. After this, <what you'll be able to do>."
- **No option title:** `No, leave it`
- **No option description (brief):** "We don't do it now; <what stays the same>."

## When NOT to force it
- If it's not a decision — just information — don't manufacture a Yes/No popup.
- Hard safety gates (money, access/permission changes, deleting live data, frozen numbers / PII)
  still get a popup, but say plainly it's a safety stop, not a routine choice.

*One line for Prathap: with `/reco` on, I'll always hand you a clean Yes/No, tell you which one I'd
pick, and fully explain the one I'm recommending — so you can decide in one tap.*
