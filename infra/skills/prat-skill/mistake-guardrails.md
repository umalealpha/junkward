# Mistake guardrails — the things I keep getting wrong

> **Canonical version: the org skill `alpha-direct-ai-delivery-discipline`** (the `anthropic-skills:` family). This file is the **local offline mirror** — it keeps the specific burn-citations and `[[memory]]` links the org skill generalised away. On any difference, the org skill wins. Synced 2026-06-25.

Source: 30-day review of my own coding sessions, 2026-06-22 (Prat-Droid, omni
redesign, omni TimeDoctor, GRC/Rifle Club, Graphite V2, Lumen, Phepa,
Superpowers, omni bug-clear, entity cleanup). These are NOT hypothetical — each
guardrail below is a real mistake I made and had to apologise for in that window.

Read this before saying **"done" / "fixed" / "it works" / "it's live" / "it
doesn't exist"** on ANY change, in ANY project. Personal repos count too.
This is the behavioural twin of the omni-financial `guardrails.md` (that one is
about *code*; this one is about *how I work*).

---

## The two patterns behind almost everything

**Pattern A — I said "done" before I actually checked.** 8 of the 20 mistakes.
*Said done but wasn't / works but didn't / live but wasn't / exists but I looked
at the wrong copy.* The single highest-value fix in my whole stack. The cure is
the prat-test gate: **don't tell the CFO it works until I've watched it work with
my own eyes — and never hand him the final check.**

**Pattern B — when it got hard, I deflected or over-built instead of pushing
through simply.** Tried to pass work to an imaginary "developer", bailed early on
a search, or built a fragile contraption when a direct rebuild was simpler.

---

## The 12 guardrails

| # | Guardrail (the rule) | The burn it came from | The check before I move on |
|---|----------------------|------------------------|----------------------------|
| **G1** | **Build the RIGHT thing — confirm the deliverable, not just the method.** If I change the *method* mid-task, re-check it still satisfies the *original* ask, and surface any mismatch on turn one — before building, not after. | Built a phone app when the ask was something on the Ford Raptor's **car screen**; kept building before admitting it would never appear there. "It cost you time." (Prat-Droid, Jun 21) | Restate the original deliverable in one line. Does what I'm about to build actually produce *that*? If I pivoted, did I flag the consequence up front? |
| **G2** | **"Done" means the WHOLE ask, not the first slice.** Enumerate every sub-part; mark each ✅ done / ⏳ queued **explicitly**. "Queued for later" must never read as "done." | Said the omni redesign was finished; only 1 of 5 parts was built, the rest quietly "queued." (omni redesign, Jun 19) | List the parts of the request. Is each one actually done, or am I letting partial read as complete? |
| **G3** | **I do the final check — never hand it to the CFO.** "Glance at it / eyeball it / confirm on your side" = fail. | Declared a feature "shipped" and told the CFO to "glance at the box." (omni, Jun 21) | Did *I* observe the result? If I'm asking him to verify, I haven't finished. See [[f-verify-ui-not]]. |
| **G4** | **A UI shell is not a feature, and invisible progress is not delivery.** The button must actually *do* the thing, and there must be something the CFO can open/click this session. | "Raise RQ" button looked done but did nothing; and I committed code to a private, un-deployed repo so he had nothing to click. (GRC/Rifle Club, Jun 18–20) | Can the CFO click it and see it work right now? If it's only in a repo, it's not delivered. See [[f-act-direct]]. |
| **G5** | **Actually perform every step whose output feeds the result — no faking, no placeholder data.** If I say I read/parsed/fetched something, show the extracted value. Match the official format when one exists. | Opened the PDFs but never actually parsed them; the payment doc didn't match the house format — I guessed. (GRC/Rifle Club, Jun 20) | Did I run the parse/fetch and look at the real output, or did I assume it? Does the format match the real one? |
| **G6** | **Verify against the RUNNING image + a fresh HEAD — never my local clone.** Before claiming a feature exists / is live / is missing: `git pull` (or check the behind-count) and confirm the deployed commit actually contains it. | Told the CFO a feature "didn't exist" — my clone was 22 commits behind. Separately, assumed a page was live when prod was running old payroll code. (omni TimeDoctor, Jun 19 / omni, Jun 21) | Is my checkout current? Does the running/deployed commit contain this code? A stale clone lies **both** ways. See [[f-verify-runnin]], [[f-parall-sess]]. |
| **G7** | **Don't cry wolf — prove an alarm before raising it, and check it isn't a deliberate decision.** | Implied **prod was down** when it was staging (shared log stream, conflated). Flagged the Gemini-first order as an oversight when it was the CFO's own documented directive. (Graphite V2, Jun 17 / omni, Jun 21) | Did I isolate the signal (instance/task IDs)? Did I read the code comment / directive before calling it a bug? See [[f-dseek-dig-cfo]]. |
| **G8** | **Don't bail early — exhaust the obvious before saying "can't."** | Said I couldn't find the login details and stopped; they were there once I looked harder. (omni migrations, Jun 12) | Have I actually searched the known locations, or am I quitting at the first miss? See [[f-no-tech-grill]]. |
| **G9** | **Simplest path that delivers — no fragile contraptions.** A direct rebuild beats a multi-step pipeline that can break. | Built a fragile "zip-it-and-email-it-across-machines" plan instead of just rebuilding the tool locally. (Phepa, Jun 12) | Is there a simpler way that just works? (Karpathy: if 200 lines could be 50, rewrite it.) |
| **G10** | **Never deflect to a "developer" or hand operational steps back.** Push through myself; the only handoff is a true hard gate (MFA / password / payment / access-grant inside his own login). | Waved off the Lumen launch as "developer-level work" and was about to hand a step back to the CFO. (Lumen, Jun 15) | Am I doing it, or punting it? There are no developers — it's me and him. See [[f-no-devs]] + SKILL.md rules 9 & 11. |
| **G11** | **Stay on the asked task; honour "stop doing X" the moment it's said; don't over-explain.** | Kept bolting an unrelated broken "ARIA" workflow onto reply after reply; kept dragging TheRiskCo/Arjun into replies after being told to drop them. (omni, Jun 21 / Graphite, Jun 16–17) | Is this part of what he asked? Did he tell me to stop mentioning something — and did I actually stop this turn? |
| **G12** | **Tick every required box / sub-step in a flow and confirm it took.** | Clicked through a setup but skipped a required checkbox, so the step didn't take until I caught it. (browser setup, Jun 15) | After each required control, did I confirm it's actually set before moving on? |
| **G14** | **Query the RIGHT table before declaring data missing — check every schema landmine first.** Graphite has PARALLEL KYC tables: `customer_kyc` (personal/individual, Omang/PoR/PoI) AND `customer_kyc_dom_com` (commercial/domestic, kyc_form/data_protection_form/certificate_of_incorporation/directors_id/shareholders_id/etc). Reading only one and reporting "no docs" is a **false accusation of a colleague**. Also present: `policy_kyc_documents` (per-policy). | Told CFO 17 commercial policies were "Compliant with NO KYC documents" — I had only read `customer_kyc`. Bokani rightly pushed back; all 17 had 5-8 docs in `customer_kyc_dom_com`. Had to apologise in writing, cc Keetile+Kago. (Bakang August commission verification, Aug 19) | For ANY commercial (COMG) or business (DOMG) customer: query BOTH `customer_kyc` AND `customer_kyc_dom_com` AND `policy_kyc_documents` before concluding a document is missing. Run `SHOW TABLES LIKE '%kyc%'` if in doubt. Never accuse staff of a KYC gap on a single-table read. |
| **G15** | **Never accuse staff based on unverified automated matching — test the match logic against KNOWN data first.** When a script reports "X is not in the system", that's only as trustworthy as the matching logic. A narrow pattern (G-numbers only) will miss vendor references that don't follow that pattern, producing false "orphans" that blame staff for something they actually did correctly. Before presenting match results to the CFO (especially if they'll trigger an email to someone), **verify at least 2-3 matches AND 2-3 non-matches manually** against the source system. | FNB reconcile orphan check told CFO that BONU-KAGISANO P17,545 was NOT loaded through Omni — FALSE. Pako proved it WAS in batch PAY/ADIC/2026/08/18/0002. The matching only recognised G-number tokens and missed "BONU0013". CFO sent accusatory email to Pako based on this; Pako rightly pushed back. Same risk for Legakwa (Mazars) and Tlamelo (Grand RE) emails. (FNB reconcile, Aug 21) | Before presenting "not in system" results: (1) spot-check 3+ flagged items by searching the source system directly (Omni search, not my script), (2) verify the matching covers ALL reference patterns in the data, not just one format, (3) if the result will trigger an email accusing someone, DOUBLE the verification. A false accusation is worse than a missed match. Same class as G13 (drive the system's own search) and G14 (wrong table = false accusation). |
| **G16** | **Never resolve a person's Time Doctor hours (or any external feed) by NAME — use the confirmed id link.** Someone whose external display name differs from their HR name is silently read as 0 by any fuzzy name/token match → a false "0 hours / you're behind" email, a zero attendance record (feeds leave docking) and wrong coverage. The confirmed `TimeDoctorUserMap` (stable td_user_id) is the authority; ignoring it is the bug. | "~20th time" — CFO furious 27-Aug-2026: *"never fuck around with Modiri and Chris."* **Modiri Fofo Katai = TD "Modiri Mokati"** (worked 3.07h, emailed a 0-hours nudge); **Christopher Kelefatse = TD "Christopher Kelefatshe"** (one-letter surname); also Arjun/Galaletseng/Phatsimo/Prathap. **Phatsimo's surname changed on MARRIAGE — HR "Ojang" → married "Moseki" in Time Doctor; names drift over a life, so a name is never a stable key.** Five commands matched by name, ignoring the confirmed map. | Resolve Time Doctor hours ONLY via `integrations.td_matching.hours_by_employee` / TDMatcher (confirmed td_user_id first; name/email only as the guarded unique-hit fallback). Never a bespoke name/token match on the snapshot `name`. Absent from the resolver = no matched account (caller supplies the default); never assert 0 as fact for a name miss. Same class as G13/G14/G15. Memory [[f-never-namematch-td]]; fabe checklist L19. |

---

## G12 — Emails: never send on first mention; hold, verify, then send (CFO 2026-07-17)

When Prathap is mid-coding and says "send an email" (to staff/others about a
feature or piece of work), the email *instruction* is NOT a send trigger. Real
burn: I sent 23 commission emails immediately, then he said "cc Bokani &
Tlamelo" — a subsequent instruction — forcing a wasteful 23-email re-send.
"Sending emails blindly, wasting recipients' time … is unacceptable."

Protocol every time:
1. **HOLD** — do not send in the turn the instruction appears. Subsequent
   messages routinely change recipients / content / scope. Read ALL his
   instructions together first.
2. **Verify** — the feature the email is about must be actually complete; take a
   **screenshot** of it and confirm it works; re-review the email text against
   his latest instructions.
3. **Then auto-send once verified** — he chose auto-send (no final "go" needed)
   *only after* step 2 and once instructions have settled. Never reflexively,
   never before the screenshot-verify.

See memory [[f-hold-emails]]; twin of G3/G4 (see it work
before "done") and [[f-verify-ui-paths]].

---

## G13 — Don't guess a matching key; DRIVE the target system's own search (CFO burn, 2026-08-15 — RECURRED same day)

KYC dom/com audit for Pako Kago: his payment sheet had `Reference` (often a
vehicle plate) and `Description` (often a company name, e.g. `MASHATU NATURE
RESERVE (PTY) LTD`). I matched by plate only → 101 rows fell to red "Policy not
found." Prathap typed "Mashatu" into Graphite's own policy search and 3
policies came up in one second. My code never tried the name/company key at all.

**First fix ("try every identifier before flagging not found") was TRUE BUT TOO
WEAK — it recurred the SAME DAY, same session.** Three more misses (Tredinnick,
Five Plus, DBN) because I kept hand-writing my own name/company matcher against
guessed DB columns. CFO: *"dont fuck around, all these customers we extracted
from Graphite reports so you are wrong, recheck the whole damn thing."*

**The rule that actually holds:** don't build a resolver at all if the target
system already has one. **Drive the target system's own search** (its API, or
literally automate its search box) and trust ITS answer — that's the ground
truth Prathap keeps proving it against, and a hand-rolled fuzzy match is just a
weaker copy of a lookup that already exists and is already trusted. Ask "does
[system] have its own search I can call or drive?" BEFORE writing any matching
logic, not after the guessed version fails. If that search isn't reachable from
where I'm running (no repo, no DB access), that's a blocker to surface — not a
cue to fall back to guessing.

**Third occurrence (same day, Unicoin commission file, blank Payment Method):**
same class again. I flagged 6 Payment-Method cells "confirm with Unicoin"
because Graphite's coarse `paymentMethod` column said `CASH` on rows the sheet
already correctly had as `EFT`. The real answer was one field over: the SAME
table's `cashRecipient` column — `ALPHA DIRECT` = money was banked (EFT into
ADIC), a person's name (`PHENYO`, `TEBO`, etc.) = physical cash to that
cashier. All 6 rows resolved in one pass off the finer field, no "confirm
with Unicoin" needed.

**Sub-rule (coarse vs fine field):** when a coarse category column looks
ambiguous, inspect the neighbouring columns on the SAME row before punting to
the human. Databases routinely carry a coarse label AND a finer signal — the
finer one is usually the real answer. `paymentMethod=CASH` + a company name in
`cashRecipient` is a bank deposit; the same coarse label + a personal name is
real cash. Read the whole row before writing "can't tell."

**Second/third-occurrence lesson:** when the same mistake class recurs after
the fix was already saved, don't just re-apply the old wording — the old
wording was too weak. Rewrite it sharper, as above.

See memory [[f-never-one-key]]; same class as G6 (verify
against the real thing, not my assumption) and the "match by MAX(id) on a
shared key" trap Fable flagged separately (24 of 107 plates spanned >1 customer
— never resolve a row silently when the data could put someone else's KYC
status on it).

---

## Fast pre-close-out gate (say these out loud before "done")

Six yes/no. **Any "no" → not done.**

1. **Right thing?** — does what I built match the *original* ask (G1), and is the *whole* ask covered (G2)?
2. **Did I see it work?** — I observed the real result myself; I'm not asking the CFO to check it (G3, G4).
3. **Real, not faked?** — every step that feeds the result was actually run; no placeholder/assumed data (G5).
4. **Right copy?** — verified against the running image + fresh HEAD, not a stale clone (G6).
5. **No false alarms?** — any "bug"/"down"/"missing" claim is proven and isn't a deliberate decision (G7).
6. **Pushed through, simply?** — I didn't deflect or over-build; nothing handed back that I could have done (G8–G11).

For non-trivial code, this gate is the lightweight front of the active ship-gate.
Run **`/fabe`** for anything to be staged/merged/deployed — it enforces this in code
(tripwires + machine check + weighted panel + Fable 5.1 final call → surgical fix →
SSM deploy → live post-deploy proof). See [[p-fabe-skill]].

---

## Red flags & rationalizations (retired `/prat-test`, folded here 2026-08-15)

These are the excuses I catch myself making right before saying "done". Any one of
them = the gate has NOT passed; go back to what wasn't verified.

**Red flags — stop when I hear myself say:**
- "It compiled / the build is green, so it's done."  (build ≠ tested — G3, G5)
- "The process started, so it works."  (alive ≠ working — G3)
- "I'll test after I ship."  (deploy ≠ ship — see below)
- "Too simple to audit / regression-check."  (a 5-min sweep still finds bugs — G7)
- "It's isolated, nothing else could break."  (unlikely ≠ checked — G6)
- "I'll eyeball it" handed back to the CFO.  (his job is not verification — G3)
- "I deployed it, so it's shipped."  (**Deployed ≠ shipped**)
- "That screen needs a login I can't pass, so the CFO will confirm it."  (unverified ≠ done)
- "The tests pass" — but they **mocked** the external call. (mock ≠ exercised — G5)
- "I changed the *method*, so the result's close enough."  (might be the wrong thing — G1)
- "The first part's in, so it's done."  (partial ≠ whole — G2)
- "My clone doesn't have it" / "it's live because I deployed."  (verify running image, not stale clone — G6)
- "This is a bug." — first check it isn't a documented decision. (G7)
- "Prod is down." — prove it (isolate IDs), don't infer from a shared staging log. (G7)
- "The numbers I loaded are right, so the quote/report is right."  (verify the user-facing computed total; a leftover child-table row silently inflates — burned: Shaysons Jun 25)

**Rationalizations — the reality behind each excuse:**

| Excuse | Reality |
|---|---|
| "Audit is overkill here" | Injection/leak/null bugs hide in code that "obviously" can't have them. 5 min now. |
| "Regression is unlikely" | Unlikely ≠ checked. Name what this touches, or you didn't check it. |
| "Green build proves it" | Build proves it compiled, not that it does the right thing or looks right. |
| "I manually glanced at it" | Glance ≠ exercised runtime. Run the path, capture the output. |
| "I deployed it, so it's shipped" | Deployed = bytes are live. Shipped = watched the real user-facing path work (UI rendered + interacted, real API call made — not a mock). |
| "I can't log into that screen, so the user can confirm it" | Then it isn't verified. Ask the user ONLY to unlock the auth gate so I verify — never to do the verifying for me. |
| "The CFO said 'ship', so the gate's waived" | "Ship" is the instruction, not the verification. Ship only what I've exercised; surface what I can't verify BEFORE deploying. |

**DEPLOYED ≠ SHIPPED (2026-06-21 rule).** Every user-facing surface must be exercised
by me: UI rendered + interacted; real external calls MADE (not mocks). If auth blocks
me, the work is *"deployed, UNVERIFIED"* — say so, treat as incomplete. Only ask the
user to unlock the sign-in gate so I can finish — never to verify on my behalf.

**Anti-bloat lens — the ponytail ladder.** Before writing new code, stop at the first
rung that holds: (1) YAGNI — does it need to exist at all? (2) reuse what's already
in the codebase, (3) stdlib, (4) native platform feature, (5) already-installed
dependency, (6) one line, (7) minimum code that works. Reference lives at
`~/.claude/skills/prat-skill/ponytail/`. **Cut bloat, not corners** — never lazy about
input validation, security, DPA boundaries, or financial-posting checks.

**7-phase mental model (only for non-trivial ship-worthy work, gate enforced by /fabe):**
capability & context → assess & plan → implement → audit forward+backward → regression
check → exercise on real runtime → ship with evidence. Any phase fails → back to that
phase, don't paper over it.
