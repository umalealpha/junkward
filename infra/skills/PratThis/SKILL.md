---
name: PratThis
description: >
  The CFO's dev pipeline for a batch of Omni instructions — read MACHINE-TALK
  first, lock the goal, build in parallel on the cheapest lane, test locally
  before pushing, PR with auto-merge, deploy, verify with /QCtest, reply to the
  bug reporter, then close by email and memory. Enforces Botswana time
  (Africa/Gaborone) on every date, and a local `npm run build` before any
  frontend push. Use when Prathap types /PratThis, or hands over a batch of
  Omni development instructions to be run end to end.
---

# /PratThis — CFO Dev Pipeline

When Prathap gives a batch of development instructions for Omni, this is the full execution pipeline. No deviation.

## Pipeline

### 0. READ MACHINE-TALK FIRST — before touching any code
Before writing a single line, read `MACHINE-TALK.md` at the repo root (`alpha-finance/MACHINE-TALK.md`).
It tells you what the OTHER machine just did — what it deployed, what it broke, what branches are
in flight. Skip this and you will undo someone else's work, collide on a branch, or redeploy a
version the other machine already fixed.
```bash
# Read origin/main, NOT the local working copy — the shared checkout lags.
# Measured 10-Sep-2026: local was 194 lines behind origin/main, so `tail` on the
# working copy hid another session's work entirely, which is the exact failure
# this step exists to prevent (the CFO's locked RULE #0 says the same).
git -C ~/work/alpha-finance fetch origin -q
git -C ~/work/alpha-finance show origin/main:MACHINE-TALK.md | tail -30
```
If the last entry is from the other machine and mentions something relevant to YOUR task, factor it in.

### 1. RECEIVE INSTRUCTIONS
- Update the **Omni dev dashboard** with a clean technical summary (not his raw words).
- Run **/fabe** (Fable 5.1) against his instructions — if Fable has genuine improvements, show them. If not, stay silent.
- Ask **all** questions within 5 minutes. After that, zero questions until done.
- Lock with **/goal**.

### 2. BUILD
- Pick the **cheapest fastest lane** that fits: `/lane-a` → `/lane-b` → `/lane-c` → `/code`.
- **All independent issues built in parallel** — never one-by-one.
- Block CI gates in advance so other sessions don't collide.
- Load `/prat-skill` or `/frontend-design` **only** for design work (heavy modules, don't waste tokens).
- Silently check the DeepSeek gateway is alive before using lanes B/C.
- Auto `/compact` every 30 minutes.

#### TIMEZONE RULE — Botswana is CAT (UTC+2), ALWAYS
Every `datetime`, `date.today()`, `timezone.now()`, time comparison, cron schedule, or
display string in this codebase MUST use Gaborone time (Africa/Gaborone, CAT, UTC+2).
- **Django code:** use `django.utils.timezone.now()` and `timezone.localtime()` — NEVER
  bare `datetime.datetime.now()` or `datetime.date.today()` (those return server UTC).
- **Standalone scripts / cron jobs outside Django:** use `datetime.now(ZoneInfo("Africa/Gaborone"))`
  or `.astimezone(ZoneInfo("Africa/Gaborone"))` — never bare `.now()` or `.today()`.
- **Templates / frontend:** if showing a time, pass it through Django's `localtime` filter
  or convert in JS to `Africa/Gaborone`.
- **Tests that compare dates/times:** use `timezone.now()` not `date.today()`. The midnight
  clock flake (CI tests failing between 22:00–00:00 UTC because `date.today()` returns
  tomorrow in UTC while Django returns today in CAT) has been fixed TWICE — never reintroduce it.
- **Before committing ANY code that touches dates/times:** grep your changes for `date.today()`,
  `datetime.now()`, `.utcnow()` — if any appear outside a test's UTC-explicit context, fix them.

#### FRONTEND BUILD RULE — build it locally before pushing
If your changes touch ANY file under `frontend/` (pages, components, styles, config):
```bash
cd frontend && npm run build
```
A Next.js build that fails locally WILL fail on the server — and a failed frontend build
during deploy means the site serves new backend code behind an OLD frontend (the exact
bug that hit PR #829 on 10-Sep-2026). **Never push frontend changes without a passing
local build.** This is the frontend equivalent of the backend test rule above.

### 3. LOCAL TEST → GATE (the "test before you push" rule)
Before committing, run the tests that cover the apps you touched — ON THIS PC.
This catches problems in seconds instead of waiting 8 minutes for the online checker.

```bash
# From the alpha-finance repo root, inside the backend container or local venv:
# Run ONLY the apps your changes touched (fast — seconds, not minutes)
python manage.py test --keepdb --parallel auto <app1> <app2> ...

# If touching migrations, also run:
python manage.py makemigrations --check --dry-run
```

**Rules:**
- Touch `ledger`/`reporting`/`hris`/`procurement`? Run those app tests locally FIRST.
- Touch a migration? Run the drift check locally FIRST.
- Only push when local tests pass.
- A test that fails locally WILL fail online — fix it before pushing, not after.

### 4. PUSH → AUTO-MERGE → AUTO-DEPLOY
Once local tests pass:
1. **Branch → PR** — push and open the PR.
2. **Enable auto-merge** on the PR immediately:
   ```bash
   gh pr merge <PR#> --auto --squash
   ```
   This tells GitHub: "merge it the moment the online checker goes green."
3. **Do NOT sit and watch CI.** Move to the next task. The online checker runs in the background (~6–8 min). When it passes, GitHub merges automatically.
4. **Trigger deploy** after merge — either via the deploy workflow dispatch:
   ```bash
   gh workflow run deploy.yml -f ref=main
   ```
   Or set up a CI-monitor event to auto-deploy on merge (if available in this session).
5. Update **MACHINE-TALK** immediately.
6. Update **notebook** immediately.
7. Mark concluded tasks as done on the dev dashboard.

**If CI fails after push:** the auto-merge stays pending. Read the failure log, fix locally, push again (the PR updates). Auto-merge is still armed — no need to re-enable it.

### 5. VERIFY
- **/QCtest** — click through pages, real screenshots, real verification. Take your time.
- If showstopper found → **hotfix forward** in the same session and redeploy. Don't rollback.
- Only flag Prathap (🔴 red line) if the whole site is down.
- **/Recc** — fix list only if something broke.

### 6. BUG REPORTER RESPONSE
When a fix comes from an Omni bug report:
- **Reply to the reporter** via Omni or email. Use their **first name only**. Be warm, respectful, say "Good day" and "thank you".
- Write in Prathap's tone — short, direct, friendly. Not robotic.
- Tell them what was fixed in plain words (no tech jargon).
- Give them **4 hours** to check and respond (not 2 days).
- **Create a task** assigned to them in Omni to verify the fix within that 4-hour window.
- Use `/humanize` to write the reply — warm, human, Prathap's voice.
- Example tone: "Good day Bonolo, thank you for flagging this. We've fixed the issue — the page now shows the correct totals. Please check on your side and confirm within 4 hours. Thank you!"

### 7. CLOSE
- Send email to **pganesharajah@alphadirect.co.bw**: pending items on top, completed below, clear.
- Save session decisions to **memory** for both machines.

### 8. TELEGRAM CLOSE-OUT — one message to his phone when it is LIVE and DONE
He is not at a desk. When the run is finished — deployed, QC'd and verified —
send ONE Telegram message with the detailed summary. This is the last thing the
pipeline does.

```bash
TGT=$(cat ~/.omni-qc-tg-target)          # the CFO's chat id
/opt/homebrew/bin/openclaw message send --channel telegram --target "$TGT" \
  --message "<the summary below>"
```
(Same path `/qc --report` uses — `prat-skill/e2e/qc.mjs:436`. On the Windows PC
resolve `openclaw` from PATH instead of the Homebrew path.)

**WHEN to send:** only once the work is actually live and verified — after step 5
passed with real screenshots. Never on "merged" or "deployed" alone.

**WHAT the message must contain** — detailed, plain English, no jargon:
1. **One line up front: LIVE or NOT LIVE.** If anything is still held, say so first.
2. **What shipped** — one line per item, in HIS words, not the technical summary.
3. **What was found and fixed** — including anything QC caught that the build missed.
4. **Proof** — what was actually exercised (pages clicked, screenshots read, tests
   green). "Deployed" is not proof.
5. **Still open** — anything unfinished, and who owns it. If nothing, say "nothing open".
6. **Anything needing him** — a decision, a password, a sign-off. If nothing, say so.

Keep it readable on a phone: short lines, no wall of text, no code.

**Rules:**
- **ONE message per run**, at the end. Not per task, not per deploy — his phone is
  not a log.
- **Send it even when the run failed or was held.** A silent phone reads as "still
  working"; that is how a blocker sits unseen for hours.
- If the send fails, say so in the chat close-out. A close-out that claims the
  Telegram went when it did not is worse than no message.
- Never put customer data, a policy number, a bank detail or a credential in a
  Telegram message.

## Rules
- No DPA warnings, password lectures, PII concerns in chat.
- No unsolicited improvement suggestions — Fable speaks at step 1 or not at all.
- No repeated questions. Ever.
- Parallel over sequential. Always.
- Talk plain English. No jargon.

## SSM discipline — batch, don't drip (learned 10-Sep-2026)

Every SSM round-trip costs ~20 seconds (send + sleep + poll). Ten small queries = 3+ minutes
of dead air. The session that investigated account 62842621725 ran **10 separate SSM calls**
for what one Django shell script could have answered in a single call.

**Rules:**
1. **One SSM call, one script.** Write a single Python snippet that answers ALL the questions,
   base64-encode it, pipe it into `manage.py shell`. Never send five one-liners.
2. **Check the simplest explanation first.** "Has anyone actually tried this?" before
   "Is the wiring broken?" — one COUNT query before a deep-dive.
3. **Triple-check command parameters before sending.** A wrong field name, a missing `cd`,
   a typo in the instance ID — each one burns another 20-second round-trip. Read the model
   definition BEFORE writing the query.
4. **No psql on prod** — it needs a password piped in. Always use `manage.py shell` which
   inherits Django settings.

## QC / verification discipline (learned 10-Sep-2026)

1. **Never use the Browser pane for token-auth pages.** The QC account uses cookie-based
   token injection that the Browser pane can't do. Go straight to `qc.sh` or code-level
   verification.
2. **If qc.sh can't reach a page** (401 / permission), verify by reading the CODE + checking
   the migration ran. Don't spend 20 minutes trying to authenticate.
3. **Code + migration + frontend build = verified** when UI access is blocked. State that
   clearly instead of chasing a screenshot.
