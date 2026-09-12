---
name: AriaWindows
description: >-
  Prathap's personal "ARIA" desktop AI on his Windows PC — the full build state,
  how to run/change/package it, and every trap learned. Auto-load whenever Prathap
  types /AriaWindows, says "ARIA" (the Windows app) / "work on ARIA" / "the ARIA
  desktop app", or the task touches: the `javis-clone` repo, ARIA's glowing face /
  HUD / gestures / British-female voice, the Electron shell (`winapp`), ARIA's
  Omni tasks/inbox/calendar cards, business lookups (profit/claim/policy), the
  ARIA installer, or tap-to-approve. Carries architecture, run/build steps, current
  state, reuse patterns and traps so a fresh chat continues where the last left off.
  Companion to `omni` (deploy), `prat-skill` (dev stack). KEEP CURRENT STATE +
  OPEN ITEMS updated as work lands. Fuller history: memory `p-javis-win-app`.
---

# ARIA — Windows desktop AI

ARIA is Prathap's personal AI that runs as a **Windows desktop app** on his PC. Built
from his private repo `Prathap-Alpha/javis` (a JARVIS-style assistant). It shows a
glowing dot-particle **face of ARIA** (a woman), speaks in a **British female voice**,
calls him **"Prat"**, reads his live Omni/Microsoft-365 data, and takes camera gestures.
It reuses the original Python "brain" as-is and wraps it in an Electron shell for Windows.

> He is a **non-coder CFO** — talk plain English, lead with the one thing HE does.
> Say "sir" NEVER — she calls him **Prat** (his 2026-08-18 instruction).

## Where everything lives
| Thing | Path |
|---|---|
| Repo (source of truth) | `C:\Users\PrathapAsus\work\javis-clone` — pushed 4-Sep-2026 to **`Prathap-Alpha/aria-windows`** (private, remote `aria`, branch main). The old `origin` = `Prathap-Alpha/javis` (Mac JARVIS) is left untouched. Commit with `git push aria main`. |
| Android app | `android/` in the same repo (Kotlin + Compose). Build dir `C:\Users\PrathapAsus\work\aria-android` (keystore + `pairing.properties` live there and in `~/.javis/`, git-ignored). Build: `python prat-skill/tools/android_build.py build C:\Users\PrathapAsus\work\aria-android --task :app:assembleRelease` |
| Electron shell | `…\javis-clone\winapp\` (main.js, preload.js, voice-inject.js, presence.js, package.json, assets) |
| Python "brain" | `…\javis-clone\javis\` + `main.py` (FastAPI on 127.0.0.1:8080) |
| The HUD (served) | `…\javis-clone\macapp\Resources\hud.html` + `aria-face.html` + `gestures.js` + `mediapipe/` |
| Installed app copy | `C:\Users\PrathapAsus\JAVIS-App\` (kept out of OneDrive) |
| Desktop installer | `…\Desktop\ARIA Setup.exe` (double-click to install) |
| Local venv | `…\javis-clone\.venv` (lean: fastapi/uvicorn/httpx/openai/pydantic/python-multipart) |

## How to RUN it (dev — this is what Prathap sees)
```bash
cd /c/Users/PrathapAsus/work/javis-clone/winapp && npm start
```
- Kill first if already running: `taskkill //IM electron.exe //F //T` + free port 8080
  (`netstat -ano | grep :8080 | grep LISTENING` → `taskkill //PID <pid> //F //T`).
- main.js maximises the window, clears the Electron cache each launch (HUD changes were
  being cached — DON'T remove `session.defaultSession.clearCache()`), spawns the backend,
  loads `http://127.0.0.1:8080/hud/hud.html`, injects voice-inject.js + presence.js.
- Health: `curl -s http://127.0.0.1:8080/health` → `{"status":"ok","app":"ARIA"}`.
- **HUD / face / gestures / mediapipe are SERVED FROM THE REPO** (`macapp/Resources` via
  `findRepoRoot`), so editing them updates the app WITHOUT re-packaging. Only main.js /
  preload / voice-inject / presence are bundled into the installer.

## How to PACKAGE (Desktop installer)
```bash
cd …/winapp && npm run dist    # -> dist/ARIA Setup 0.1.0.exe + portable
```
⚠️ **electron-builder's winCodeSign extraction needs symlink privilege** → fails with
"A required privilege is not held" UNLESS **Windows Developer Mode is ON** (Settings →
Privacy & security → For developers). Prathap turned it on 2026-08-18; if a fresh machine
fails, that's the fix. Clear `%LOCALAPPDATA%\electron-builder\Cache\winCodeSign` and retry.

## Architecture
- **Electron shell** (`winapp/main.js`): spawns the Python backend (venv python `main.py`,
  env injected — see keys below), maximises a frameless-ish window, tray (Show/Open Chrome/
  Open Claude/Screenshot/System Status/Quit), grants camera+mic, injects the renderer scripts,
  opens external links (payment cards) in the DEFAULT browser via `shell.openExternal`.
- **Face** = ARIA's REAL renderer: `aria-face.html` (fetched from `omni.alphadirect.co.bw/
  aria-face.html`, her baked face + dot-particle glow) EMBEDDED as an `<iframe id="facef">`.
  Lip-sync driven by `facef.contentWindow.ARIAFace.setAmplitude(level)` inside `speak()`.
  Her own orange chrome (.aria-hud/.aria-live/.aria-word) is hidden for a cohesive blue HUD.
- **HUD** (`hud.html`): 3-column — left rail (GABORONE clock + PENDING·OMNI tasks + INBOX·PRATHAP),
  centre (ARIA face + "ALL SYSTEMS GREEN" pill + status + mic), right (webcam+gesture legend /
  ARIA·STATUS / NEEDS YOU / TODAY / CALENDAR). Blue palette `--accent #7fb0ff`, green `--ok
  #5ef2a4`, professional Segoe UI font.
- **Brain** = `javis/` FastAPI. Intent router (`actions/intent.py`) → allowlisted actions
  (`actions/registry.py`). Persona (`persona.py`) = calm British woman, addresses him "Prat",
  light Setswana dropped on serious topics.

## Keys / models (this PC)
main.js injects into the backend env from `C:\ai-cost-stack\gateway\.env`:
`LITELLM_MASTER_KEY`, `OPENAI_API_KEY`, `GATEWAY_URL=http://localhost:4000/v1`,
`JAVIS_MODEL_CODE=worker-cheap`, `JAVIS_MODEL_GENERAL=reviewer-gemini`. Voice = OpenAI
**gpt-4o-mini-tts, voice 'sage'** (British female) called DIRECT (gateway has no audio route);
falls back to Windows speechSynthesis. Never put a key in the repo.

## Current features (ALL LIVE + PROVEN)
- **Face**: ARIA's glowing dot-portrait, centred, lip-syncs when speaking.
- **Voice**: British female (sage), says "Prat"; morning brief; proactive alerts (payment
  >P100k / overdue) spoken once each.
- **Business Q&A** (`integrations/business.py`, cached): "profit for July 2026"
  (`reporting.ma_pl.build_ma_pl` — ties to frozen MA numbers), "claim status <no>"
  (`integrations.GraphiteClaim`), "policy status <no>" (`aware.engine.run_select`).
- **Instant frozen figures** (`integrations/frozen.py`) offline; **local memory**
  (`memory.py`, ~/.javis/history.jsonl); **screen awareness** (`look_screen`).
- **MY Omni tasks only** — panel filters `assignee__email=pganesharajah@` (CFO = User id 2);
  Alpha Brain excluded. ~15 tasks (payments, sign-offs, feedback).
- **Live Inbox + Calendar** (`integrations/inbox.py`) via Omni's Graph reader
  (`auto_reply_omni_mail._reader_token`, Mail.Read fenced to pganesharajah@, Calendars already
  consented). **Inbox is DeepSeek-triaged** (`_triage`, gateway worker-cheap) → only important
  mail addressed to him; heuristic fallback. Brief reuses both.
- **Email → reply flow (fixed + added 2026-08-18):** `read_last_email` was Mac-only (osascript)
  and threw FileNotFoundError → "file not found" on the 1-finger YES. Now cross-platform:
  Windows reuses `integrations/inbox.recent_emails()` (the SAME live M365 inbox the HUD card shows;
  `mail._read_last_email_windows`). After reading, ARIA offers **3=draft a reply** / 2=skip
  (`mail.draft_reply`, DeepSeek `worker-cheap`, in Prathap's point-form style), then **1=open it
  ready to send** (`mail.open_reply` → pre-filled Outlook-web compose, NO send-scope, Prathap taps
  Send) / 2=cancel. `inbox.py` now also returns `from_addr` (reply-to). Confirm box in `gestures.js`
  is now options-driven (point=1, two=2, three=3; `showConfirm(q, [{pose,label,cb}])`); nod=the "1"
  option, shake=the "2". All three actions PROVEN live on the real backend (read + draft returned
  real content; open_reply URL verified). NOT physically tested: the camera hand-gesture itself and
  the actual compose-window pop (proven one layer below).
- **Humanization + fixes pass (2026-08-18, Fable-5 ideas):**
  - **OVERLAP BUG FIXED:** `window.speak()` had no guard → a payment alert spoke over the
    email reading. Now a single serialized QUEUE in `hud.html` (`_runSpeakQueue`, `_speakQ`,
    `_curSrc`); one utterance at a time, backlog capped at 4. `voice-inject.js` no longer speaks
    in parallel (it was a 2nd voice). `window.stopSpeaking()` clears/cuts (also = barge-in).
  - **Barge-in (#4):** pressing talk (`startRec`) calls `stopSpeaking()` — she stops so he can talk.
  - **Expressive voice (#3):** `tts.py` `STYLES{warm,brisk,gentle,calm,sing}` + `_resolve_style`;
    `assistant.py` sets `speak_style` per action (numbers→brisk, email/greeting→warm, frozen→brisk);
    threaded through `say(text,style)` in voice-inject + gestures + presence.
  - **Varied acknowledgments (#13):** `ACKS[]` rotation in gestures (thumbs-up no longer always "Noted").
  - **Presence (#2/#9):** time-of-day greeting (`greetLine`, Dumela+morning/afternoon/evening),
    end-of-day nudge past 19:00 (`endOfDayCheck`, once/day) in `presence.js`.
  - **Weather:** `integrations/weather.py` (Open-Meteo, KEYLESS, Gaborone, cached 20min) →
    `/assistant/weather`; HUD tile under the clock (`#wx`); rain/big-wind (>45km/h gusts) spoken
    once/day via `alerts.py`.
  - **CEO red alert:** email from Mr Arun Iyer (`aiyer@`, NOT `arjuniyer@`) → red pulsing banner
    `#redalert` + red inbox row + spoken once (`alerts._ceo_email_alerts`, uses `inbox` `from_addr`).
  - **Clickable cards:** CALENDAR (`#calcard`→OWA calendar) + INBOX (`#inboxcard`→OWA mail) +
    red banner→mail. Shared `.opencard` style.
  - **Removed the duplicate "NEEDS YOU" card** (repeated the left payment tasks) — CFO's call.
  - **Meeting scheduler (#15, like Thusa):** `actions/meetings.schedule_meeting` — voice → LLM parse
    (UTC+2 fixed offset, NO zoneinfo/tzdata — that crashed on Windows) → resolves attendee emails
    from Omni's user table (never guessed) → opens a pre-filled OWA calendar invite; Prat sends.
  - **NOT done — conflicts with CFO 2026-06-10 directive:** breathing scale / auto-blink / head
    motion (he wanted "only hair, eyes, mouth move"; auto-blink removed as "a scar"). Life comes
    from colour, not motion. Face-colour left alone (his sensitivity).
  - **STAGED (built later / need his camera+mic):** wake word (#5), memory-of-yesterday (#7),
    meeting-prep auto-offer (#8), conversational follow-ups (#10), full graceful-degrade line (#14).
- **2nd pass (2026-08-18 later):**
  - **CALENDAR/INBOX/red-alert click FIXED PROPERLY:** `window.open` is unreliable in the Electron
    shell (a tap silently did nothing → Prat: "calendar unable to click still"). Now taps POST to a
    new backend `/assistant/open` (loopback + host allowlist outlook.office.com / omni.alphadirect.co.bw)
    which uses `os.startfile` — the same reliable path as the email-reply window. `window.open` kept
    only as fallback. Proven live: endpoint opens a real tab on his PC, rejects non-allowlisted (400).
    Each tap also shows an "Opening your …" cue so a click never feels dead.
  - **ARIA·STATUS card → "ARIA · TOP 5 TO DO":** `advice.py` + `/assistant/todo` ask **DeepSeek**
    (worker-cheap) over his live Omni tasks + important inbox + calendar for the 5 most important
    actions + one line of advice; rendered in `#seesbody` (setState no longer overwrites it), 15-min
    cache, polled 15-min. Proven live (real curated 5 + advice).
    - ⚠️ **DeepSeek v4-flash/pro REASON-UNTIL-EMPTY** on non-trivial output (documented in
      `C:\ai-cost-stack\gateway\config.yaml` worker-cheap notes — "this is the MODEL, not LiteLLM").
      So `advice._ask` tries **worker-cheap → reviewer-gemini → reviewer-openai** in order; first
      non-empty wins (`by` reports which). #14 graceful degrade to the raw task list if all blank.
  - **STILL STAGED after this pass:** wake word, memory-of-yesterday (in the brief), meeting-prep
    auto-offer, and the "say YES on a top-5 item → draft the reply via DeepSeek" voice linkage.
  - **/fabe gate (2026-08-18):** panel too-large (113KB > 24KB) → Fable-5-only. Verdict FIX → 5 fixes
    applied + verified: (1) `#redalert` now `display:none` by default (was a permanent false alarm if
    inbox fetch errored); (2) CEO banner gated on `e.unread`; (3) `presence.pollAlerts` skips during
    call-mode so muted alerts are HELD not consumed by `pop_new`; (4) `meetings._resolve_attendees`
    treats a multi-match as unresolved (Pako Kago vs Kago Tshutlhedi — never guess); (5) `_playNeural`
    aborts on a `_speakGen` bump so a barge-in mid-synth can't play over him. Tripwires clean
    (no secrets/frozen/PII). ARIA is local — no omni SSM deploy, no omni ledger entry.
- **3rd pass (2026-08-18 later) — /fabe SHIP (Fable-only, panel too-large):**
  - **Calendar "can't click" REAL fix:** the click WAS registering (hit-test confirmed the card is on
    top) and `/assistant/open` DID open a tab — but the browser opened BEHIND ARIA's maximized window,
    so it read as "nothing happened". Added a send-only IPC `aria-step-aside` (`preload.js` →
    `main.js` `ipcMain.on(... win.minimize())`); `openExt()` calls `window.javis.stepAside()` so ARIA
    minimises and the browser is revealed. This also DIAGNOSES: tap → ARIA minimises = click fired.
  - **Thusa box:** `#thusacard` in the HUD right column → opens `https://prathap-alpha.github.io/thusa/`
    (repo `Prathap-Alpha/thusa`, his meeting-maker). Host added to the `/assistant/open` allowlist.
  - **Male British voice:** `config.TTS_VOICE` `sage` → **`ballad`**; `tts.py` STYLE de-gendered
    ("British woman" → "British voice"). Persona/face unchanged.
  - **Middle-finger gesture:** only-middle-up → ARIA says "Prathap is busy, please go away." (cheeky
    do-not-disturb; 4s cooldown; ignored inside confirm prompts).
  - Fable confirmed the IPC is safe (send-only, minimises own window, null-guarded), allowlist is
    exact-hostname (no suffix bypass), and the new pose doesn't shadow `point`/`two`.
- **4th pass (2026-08-18) — "showed 1, then nothing" fix:** the 4→1 email read WORKED but the live
  inbox fetch (SSM→Graph→DeepSeek triage) takes ~24s COLD with no sound → felt dead. Root cause was
  latency + silence, not a break. Fixes: (1) `doReadEmail`/`doDraftReply` in `gestures.js` speak an
  immediate "One moment, Prat — fetching your inbox." and `doReadEmail` now voices a failure instead
  of going silent; (2) `inbox._TTL` 120→180 so the HUD's 120s poll refreshes the cache before expiry.
  PROVEN: cold read 23.7s, warm read **0.09s** (instant) — reads are near-instant in steady use.
- **5th pass (2026-08-18) — 🤙 quick-meeting gesture (frequent contacts):** new pose `callme`
  (`pky && thumbOut && !idx && !mid && !rng`) → `quickMeetingFlow()` shows a 1/2/3 picker of a FIXED
  regulars list (starter: Arun `aiyer@` / Arjun `arjuniyer@` / Unami `ubutale@` — emails verified from
  Omni, Arun≠Arjun) → `meetings.quick_meeting` opens a pre-addressed OWA invite (no time guessed; Prat
  sets it) + `stepAside`. Legend shows "🤙 meeting". Fixed list lives in `gestures.js` `REGULARS` —
  swap names on request. Self-contained in ARIA (doesn't touch/deploy his Thusa PWA; Thusa has no
  request deep-link — only setup params). PROVEN: `quick_meeting` opened Arun's invite live.
- **6th pass (2026-08-18) — clean email read (/fabe SHIP):** `mail._clean_email_body` strips banner
  boilerplate (external-sender / CAUTION / do-not-click / confidentiality footer / do-not-process-
  payments / beware-fraud / automated) AND trims the quoted reply chain (`_QUOTE`). Reads only the
  LATEST received email (`inbox._recent`=raw[0]; preview 160→500), framing "Your last email is from X.
  Subject: Y. <clean body>" — no "N emails" summary. `offerReply` reworded. **/fabe FIX→SHIP:** Fable
  caught 3 OVER-strip bugs (ate "do not process payments to Kgare — we suspect fraud", "external
  auditor", salary after "confidential"); fixed by bounding each banner to one sentence + requiring
  real banner form. PROVEN both ways: banners strip, real payment/salary/auditor content preserved.
- **7th pass (2026-08-18) — the 4 staged features (/fabe SHIP):**
  - **Wake word "ARIA"** (`voice-inject.js`): a 2nd continuous `SpeechRecognition` (`wake`) beside
    push-to-talk; hears aria/arya/area → "Yes, Prat?" → `startRec()`. Hands the mic over cleanly
    (stopWake + 250ms) and `send()`'s finally now `startWake()`s (Fable fix — else wake died after
    one command). NEEDS his mic to confirm.
  - **Remembers yesterday** (`memory.recent_prior_day()` + `brief.py`): brief appends "Yesterday you
    were asking about …" — only when a real prior-day memory exists (never fabricates).
  - **Meeting-prep** (`alerts._meeting_prep_alerts()`): once-only nudge ~10 min before a calendar
    event ("…in about N minutes. Want the numbers or your inbox up?"). Unit-proven (fires 10-min,
    ignores 3-hour).
  - **Respond is GESTURE-ONLY** (CFO 2026-08-18): the reply flow uses fingers — offerReply prompt
    "Do you want to respond?" → 3=REPLY(draft)/2=leave → 1=open ready. The spoken-"yes" hook
    (`__ariaConfirmSay` + voice-inject routing) was ADDED then REMOVED at his request — do not
    reinstate voice answering of the confirm prompts.
  - /fabe: tripwires clean, Fable-only (diff>24KB), FIX(2)→SHIP.
- **8 gestures** (`gestures.js`, MediaPipe hand+face, offline in `Resources/mediapipe/`):
  4=INSTANT email read + reply offer (see 9th pass), 2=my day, 3=the numbers, ☝️point=describe screen, 👍=noted, ✊fist=Call-mode
  (mute: sets `window.__ariaCallMode`), head-shake=stop. **Confirm = BIG on-screen 1/2 prompt**
  (1 finger=YES, 2 fingers=NO) — replaced the flaky nod (nod is a backup only).
- **Tap-to-approve**: payment cards + NEEDS YOU lines open `omni.alphadirect.co.bw/
  payments/approvals` in Chrome (signed in) to approve in Omni's real flow.
- **OSINT username lookup (Sherlock, added 2026-08-25):** action `find_accounts(username, full)`
  → `integrations/osint.py` → repo-root `sherlock_search.py` (clean JSON wrapper over Sherlock
  v0.16.0). Say "find accounts for the handle jsmith" (add "everywhere" for a full ~400-site scan;
  default = a fast curated core list). For lawful footprint/fraud-due-diligence checks — reads public
  pages only, writes nothing. **Install:** `uv tool install sherlock-project` (isolated at
  `~/.local/bin/sherlock.exe`, NOT in ARIA's lean venv). `sherlock_search.py` resolves the exe via a
  PATH fallback so ARIA's venv finds it. Sherlock's own `--json` flag is for *loading* data — structured
  output is `--csv` (cols: username,name,url_main,url_user,exists,http_status,response_time_s), which the
  wrapper parses. `exists`=Claimed means found. Proven via ARIA's venv: registered + real matches returned.

## Reuse patterns (how to extend — reuse, don't rebuild)
- **Read Omni prod data**: `integrations/prod_query.run_snippet(code, "JV=")` — SSM →
  docker exec → `manage.py shell`, READ-ONLY. Same for inbox/calendar/business/approve.
  AWS at `C:\Program Files\Amazon\AWSCLIV2`, user claude-cli, instance i-02a5d76a61f4f09a5.
- **Read his mail/calendar**: Omni's `_reader_token()` + Graph GET (see inbox.py).
- **Approve a payment (SAFE path, if ever unblocked)**: `taskboard.services.complete_task(
  task, cfo, note, 0)` — flips PaymentRequest PENDING_CFO→PAID, CompletionNote author=CFO,
  dual-control held, NO money moves (FNB separate). NO dry-run in Omni; PAID is terminal.
- **Cheap off-subscription LLM**: the gateway :4000 (worker-cheap=deepseek, reviewer-gemini).

- **9th pass (2026-09-04) — THE INSTANT INBOX (CFO: "email loading is very slow… create a cache…
  suggest a response… ask me should ARIA respond… JARVIS speed"):**
  - **Root cause:** every read went SSM → Omni container → Django boot (~9-11s) → Graph → DeepSeek
    reasoning triage (10-30s). **Fix:** `javis/integrations/mailcache.py` mints Omni's Graph READER
    token ONCE via SSM (memory only, ~50 min, never on disk — test-guarded) and reads the inbox
    **directly from the PC (0.4s measured)** every 60s in the background. Keeps only mail with the CFO in
    **To** (CC/BCC out), drops noise, LLM-triages (worker-cheap → reviewer-gemini, **max_tokens 2000 —
    at 400 BOTH return empty**, reasoning eats the budget), **pre-writes a ≤60-word reply** in his style,
    **pre-makes two voice clips** per email (read + "I'd reply… Shall I respond?"). Persists to
    `~/.javis/inbox_cache.json` + `~/.javis/clips/` → warm from second zero on restart (proven 2.6 ms).
  - `inbox.recent_emails()`, `inbox.calendar()` (direct Graph, 0.3s) and `mail.read_last_email` all answer
    from the cache when warm → HUD card, alerts, brief and top-5 are fast too. `omni.py` tasks now go via
    `prod_query` (tries both blue-green container names — it hard-coded the non-green one).
    `alerts.py` was missing `import datetime` (health/contact nudges silently never fired) — fixed.
  - Endpoints (loopback): `/assistant/inbox/next?i=`, `/assistant/inbox/audio?id=&kind=read|draft`,
    `POST /assistant/inbox/reply {id}` (pre-filled OWA compose; ARIA never sends), `/assistant/inbox/status`,
    `POST /assistant/inbox/refresh`.
  - **Gesture flow:** 4 fingers → she reads the top important email IMMEDIATELY (the "shall I read?"
    prompt is gone) → speaks her pre-written reply → **"Shall I respond?" 1=open ready to send, 2=next
    email, 3=leave.** Answering cuts her off. Prompt stays 90s (`showConfirm(q, opts, ttl)`).
    `window.__ariaReadInbox(i)` drives the flow without a camera; `window.queueClip(url)` queues a clip
    behind current speech (no barge-in). HUD inbox rows show ✍ when a draft is ready. MediaPipe init was
    moved AFTER the flow definitions so the flow exists even if the camera fails.
  - **Tests:** `tests/test_mailcache.py` — 18 pass (`.venv/Scripts/python -m pytest tests -q`; pytest +
    pytest-asyncio installed in the venv). 3 wiring tests proven RED with the fix reverted.
  - **Measured:** cold boot → cache ready 40-75s, clips ~1 min later; gesture answers ≤3 ms after that.
    Browser-driven proof: "You have 6 important emails." → read clip → draft clip → 1/2/3 prompt rendered.
    NOT physically tested: his camera hand-pose and audible playback inside Electron (same clip path as the
    proven interview clips).

- **10th pass (2026-09-04) — FAST VOICE (CFO picked it from the speed menu):**
  - `javis/actions/shortcuts.py`: zero-wait regex shortcuts run BEFORE the LLM router — email/inbox/mail →
    `read_last_email` (from the cache, + "hold up four fingers and I'll offer my reply"), my day / what's on
    today / brief me → `brief.compose()`, weather, time. Outbound words (send/draft/schedule/…) and long
    sentences (>120 chars) fall through to the router, so "send an email to Kago" is never mis-read.
  - `intent.route` now asks **worker-cheap FIRST** (measured 1.6-5.4s vs reviewer-gemini 6-12s) and falls
    back to `MODEL_GENERAL` only when it returns empty/faults. `look_screen` (vision) still uses Gemini.
  - Tests `tests/test_voice_fast.py` (19) — shortcut hook proven RED when disabled. Suite total 37 green.

- **11th pass (2026-09-04 evening) — JARVIS pass (CFO picked ALL FOUR from the menu):**
  - **EARS (`javis/voice/ears.py`):** always-on, on-device listening in the backend — sounddevice mic →
    Silero VAD → faster-whisper `small.en` int8 on CPU (Core Ultra 9, 16 cores: warm model load 2.7s,
    ~2.3s per short phrase). Wake word "ARIA" (+ arya/area/ariah + a consonant-skeleton match so "Oreos,
    read my emails" still works — Whisper mishears the name across a room). `VOCAB` initial_prompt steers
    names (Kago not "Cargo"). Feedback guard: HUD POSTs `/assistant/voice/speaking` around every utterance
    so she never answers herself; a wake-word phrase while she speaks = barge-in ("ARIA stop"). Events via
    `/assistant/voice/poll?since=`, consumed by voice-inject.js every 400ms; the browser wake word now
    starts ONLY if `/assistant/voice/status` says ears are off. `JAVIS_LOCAL_EARS=0` disables.
    Installed in the venv: faster-whisper, sounddevice, numpy (model cached in HF hub dir, ~480MB).
  - **Conversation memory (`javis/context.py`):** last 8 turns (15-min TTL) fed to the intent router as
    prior chat; a FOCUS (the email in hand). `context.resolve` maps "send it" / "next" / "the second one" /
    "open it" / "read it again" to actions with NO LLM (shortcuts check it first).
  - **She SENDS (`mail.send_reply`):** Graph sendMail as pganesharajah@ using the SAME app-only sign-in the
    CFO's `prat-skill/tools/send_mail.py` uses (`prat-skill/secrets/manus-graph-sender.env`; CFO 4-Sep:
    "permission is already there"). Only the armed draft, only to the original sender, saved to Sent Items;
    `mailcache.mark_replied` drops it from the ready list. Gesture prompt is now **1=SEND, 2=NEXT,
    3=EDIT (opens Outlook)**; voice: "send it". Endpoint `POST /assistant/inbox/send {id}` (409 without draft).
  - **Approve in Omni (`actions/approve.py` + `POST /assistant/approve`):** tap a payment row → 1=APPROVE /
    2=open Omni / 3=cancel → runs Omni's own `taskboard.services.complete_task` for ONE payment_request
    task assigned to the CFO (guards inside the container). Workflow record only — FNB + 2FA still moves
    the money. NOT exercised on prod (never write-test on prod); unit-tested with a mocked bridge.
  - **Anticipate:** mail poll 60→20s (`POLL_SECONDS`); calendar now carries `attendees`; meeting-prep
    says who is coming + what they last wrote (`alerts.meeting_prep_text`, uses `mailcache.last_mail_from`);
    end-of-day wrap-up spoken once from 17:30 on weekdays (`alerts._end_of_day_alert` → `debrief.compose`).
    `_warm_loop` keeps Omni tasks (2 min) + HR (6 min) warm; `omni.CACHE_TTL` 400.
  - **FACE RECOGNITION (built same night, CFO: "you can build facial recognition"):** `macapp/Resources/
    faces.js` + vendored `vendor/faceapi/` (@vladmandic/face-api 1.7.15: tiny detector + 68 landmarks +
    128-d recognition net, ~8MB, OFFLINE). Every ~1.2s it face-prints everyone in the webcam frame and
    matches against the roster (`~/.javis/faces.json` — 128 numbers per sample, NEVER a picture), then
    POSTs `{faces, names, unknown}` to `/assistant/presence`. `javis/presence.py` = roster + rules:
    company = a stranger or any known non-owner (only once the OWNER is enrolled; before that 2+ faces);
    greets known people by name once/10 min ("Dumela, Kago. Good morning."); never greets the owner.
    **Voice:** "ARIA, this is Kago" / "remember my face as X" / "meet X" → pending enrol → HUD captures 4
    prints of the ONE visible face → "Got it, I'll know Kago from now on." · "who is here?" · "forget
    Kago's face". Endpoints: `/assistant/faces/roster|enrol|forget`. Match threshold 0.55.
    **Prathap is ENROLLED (3 samples from his ID photos, headless via
    `prat-skill/e2e/aria-enrol-faces.mjs`); cross-photo proof: passport 0.475, work permit 0.424 → both
    "Prathap".** Live webcam samples ("ARIA, this is Prathap") will sharpen it. Temp photos deleted.
    ⚠️ face-api in the in-app Browser pane times out (throttled) — use the Playwright script instead.
  - **True instant-Omni (API key) NOT built:** no read-only API scope covers the taskboard; it needs an
    Omni-side endpoint + deploy. Warm loop is the stand-in.
  - Tests: 66 green (`tests/test_jarvis.py`, `tests/test_approve.py` added). Loop-back proof: the ears
    heard real room audio (her own greeting → correctly ignored).

- **12th pass (2026-09-04 night) — GitHub + Android:**
  - Whole Windows build committed (winapp had NEVER been committed) and pushed to the new private repo
    `Prathap-Alpha/aria-windows`. Secrets scan clean; node_modules / dist / keystores git-ignored.
  - **Phone access:** backend now listens on `0.0.0.0:8080` (main.js `JAVIS_HOST`). A middleware refuses any
    NON-loopback request without header `X-ARIA-Key` = `~/.javis/mobile.key` (auto-generated; never logged);
    all 34 inline loopback checks became `_trusted()` (loopback OR paired phone). `/assistant/pair` (loopback
    only) prints the PC's LAN url + key; `/assistant/inbox/list` = all important mail for the phone.
    PROVEN from the LAN address: no key 403, key 200. First inbound connection from another device may
    trigger the Windows Firewall "Allow?" prompt — Prathap clicks Allow (I never change firewall settings).
    PC Wi-Fi IP was 10.101.14.191 on 4-Sep (DHCP — may change; the app's Pair screen edits it).
  - **Android app `android/`** (`bw.co.alphadirect.aria`, minSdk 26, AGP 8.11 / Kotlin 2.0.21 / Compose BOM
    2024.10.01 — same toolchain as Alpha Nexus): native particle FACE (Canvas), push-to-talk (Android
    SpeechRecognizer en-GB) → `/assistant/ask` → her PC voice (mp3 from `/assistant/speak`) with Android
    en-GB TTS fallback; Inbox (hear clip / SEND / edit via mailto), Omni tasks (Approve with confirm / open
    Omni), My day (brief, calendar, weather, top-5), Pair screen (server + key, test). Defaults baked from
    `pairing.properties` (BuildConfig). Signed release keystore `aria-release.keystore` alias `aria`
    (passwords in `keystore.properties`, backup in `~/.javis/aria-android-keystore.properties`).
  - **Face on the phone = THE SAME `aria-face.html`** (CFO: "copy the same face which I have created for the
    Windows" — my hand-drawn Canvas face was rejected). Bundled at `android/app/src/main/assets/face/`,
    rendered in a WebView (opaque background — a transparent WebView hides WebGL on Android), driven with
    `ARIAFace.setAmplitude/setMood('fun'|'heavenly')` exactly like hud.html. Console → logcat tag `ARIAFace`
    ("particles: 330165" = built OK). ⚠️ The Android EMULATOR cannot draw it (swiftshader AND -gpu host both
    show only the black orb; Chrome on the emulator shows the same) — verify on a REAL phone. `/hud/` static
    files are exempt from the phone key-gate (UI only; data routes stay gated).

- **13th pass (2026-09-09) — MEETING QUESTIONS + HIS 23 REGULARS + the Mac's faces:**
  - **Meeting Mode was never committed** until now (built 8-Sep: record -> PyAV compress ->
    faster-whisper -> DeepSeek/Gemini minutes -> Graph email -> Omni tasks; `javis/meeting/`).
  - **The two questions (CFO: "when we open the app it should ask what is this meeting about,
    who is in the room"):** `#meetsetup` card in hud.html opens BY ITSELF 2.5s after launch
    (once; NOT NOW dismisses for the session) and again on every tap of the meeting card.
    Two fields + tappable name chips. `manager.start(subject, attendees)` seeds the attendee
    list from what he TYPED; `note_faces` only ADDS recognised people, never replaces them.
    `minutes.build_minutes(..., subject)` puts the subject in the extract prompt as title/
    context ONLY, with an explicit "never report it as something that was said". Names are
    split on commas/;/and/newline, emails and `<...>` stripped, de-duped, capped at 20.
    `POST /assistant/meeting/start` now takes `{subject, attendees}` (empty body still works).
    `window.__ariaMeetingSetup(speak)` drives it with no camera. PROVEN live end-to-end.
  - **`javis/regulars.py` — his 23 regular people** (CFO: "ARIA is connected to Omni thus it
    should know the common people I meet"), each with the REAL address: the 19 in the 29-Jun
    staff snapshot plus 4 queried LIVE off Omni's user table (Bernard Balikani `bbalikani@`,
    Motlatsi Molefe `mmolefe@insurance.co.bw`, Unopa Male `umale@`, Modiri Katai `ceooffice@`).
    Nicknames he uses: Boss/Alpha Male=Arun, Demon=Motlatsi, Pablo=Tlamelo, LT=Legakwa,
    KT=Keetile, Medu=Meduduetso. **Kago=ktshutlhedi@ vs Pako=pkago@** and **Arun=aiyer@ vs
    Arjun=arjuniyer@** are pinned with tests so they can never be crossed. `find()` is EXACT
    match only — a surname alone ("Iyer") returns nothing rather than guessing.
    `meetings._resolve_attendees` checks the regulars FIRST and only asks Omni about anyone
    else (so it still resolves them when SSM/Omni is down, and Omni's ambiguity rule is
    untouched for everyone else). `GET /assistant/regulars` feeds the meeting chips and the
    🤙 quick-meeting picker (three flagged `quick` = Arun/Arjun/Unami; old hardcoded trio is
    now only the fetch-failure fallback).
  - **The Mac's 43 known faces — CFO OVERRODE and chose the Mac's option 1 (send photographs),
    "user is the same".** The Macs prints are 512 numbers from a different model, Windows uses
    128 from face-api — they are NOT interchangeable, and `tools/import_shared_faces.py` only
    accepts a 128-number roster. So: the Mac pushes the 58 PHOTOGRAPHS to `shared/faces_photos/
    <Full Name>/<x>.jpg` in the private `aria-windows` repo (one face per photo — a group photo
    is reported and skipped), and **`tools/enrol_from_photos.mjs`** (Playwright over the running
    HUD, the same face-api build the camera uses; `--dry-run` reports only) makes this machine's
    own prints into `~/.javis/faces.json`, <=12 samples each, and deletes the copies it served.
    Full spec committed at `shared/README.md`; the instruction to the Mac is the 9-Sep line in
    MACHINE-TALK.md. PROVEN: 3 frames from a real meeting recording -> 3 prints -> roster; test
    person then forgotten. Playwright is resolved from `prat-skill/e2e/node_modules`, not ARIA's tree.
  - Tests 114 pass / 1 skipped (`tests/test_meeting_setup.py` 8, `tests/test_regulars.py` 10);
    every new test red-proved by reverting its fix.
  - ⚠️ **Pushes to `aria-windows` (e362b94) and MACHINE-TALK were made LOCALLY only — the PC's
    Wi-Fi and Ethernet were both disconnected that afternoon.** Check `git push aria main` and
    the machine-talk sparse clone actually landed.

- **14th pass (2026-09-09) — LEARN A FACE BY TYPING THE NAME + why the Mac's photos failed:**
  - **CFO: "click a picture and a box appears so I type the name, sometimes you will struggle
    understanding Setswana names."** New HUD card **LEARN A FACE · TYPE THE NAME** (`#learnfacecard`
    → `#facelearn` panel): tap → ARIA takes the picture immediately, shows it back, and opens a
    name box. Type + SAVE/Enter; RETAKE re-shoots; CANCEL/Escape/click-away closes. The box has a
    `<datalist>` of his 23 regulars + everyone already known, so a long surname can be picked.
    Speech is not in this path at all. `faces.js`: `__ariaSnapFace()` grabs up to 4 prints from
    STILLS of the current frame (not the live `<video>` element — face-api returned 0 faces on a
    video element that a canvas snapshot of the same frame detected fine) and measures the
    UNMIRRORED copy while showing the mirrored one (prints are not mirror-proof); ladder
    416→512→640 because a deliberate photo can afford a slower look. Returns `looksLike` so a
    second picture tops that person up instead of making a duplicate.
    `__ariaSaveSnappedFace(name)` enrols under the typed spelling. `window.__ariaLearnFacePanel`
    = {open, save, close} for testing. PROVEN live: "Test Keotlhoboge" typed → 4 prints saved
    under that exact spelling → re-snap pre-filled the name → blank name refused → forgotten.
  - **The Mac's 55 photographs are UNUSABLE and it is the pictures, not the transfer.** They are
    100-300px thumbnails (Unami 103x152, the CFO 118x152). Old settings found a face in only 14 of
    40 people; padding recovers more, but MEASURED against ARIA's 5 genuine prints of the CFO
    (which sit 0.32-0.51 apart), prints made from HIS OWN thumbnail land **0.656 / 0.785** — over
    the 0.55 threshold — while colleagues' land 0.62-0.73. No separation → ARIA would hand out
    names at random. `enrol_from_photos.mjs` now has a **quality gate** (same rule as the roster
    guard: >5% of cross-person pairs inside 0.55, or a known person unrecognisable → writes
    NOTHING and says why). Roster still holds Prathap alone.
  - **Other sources checked and closed:** M365 profile photos are 401 — the `manus-graph-sender`
    app has only Calendars.Read / Mail.Read / Mail.Send, no `User.Read.All` (would need an Azure
    grant from him). Omni holds NO staff photos (only salvage + nexus trip images).
  - **USE A PICTURE (same panel):** a file picker feeds a photo off his PC through the same box —
    `__ariaFaceFromFile(file)`, same padding ladder. **A face under 120px across is REFUSED**
    (calibrated: ~140px webcam face prints 0.528 from his best sample; the Mac's crops 0.66-0.79).
    Saving under a name already held whose face does NOT match warns and writes nothing; SAVE again
    overrides. `__ariaSnappedMatches(name)` asks the SAME matcher the camera uses —
    ⚠️ **face-api's FaceMatcher compares against the MEAN of a person's samples, not the closest**,
    so 0.528 to his best sample still read "unknown" at 0.587 mean. That is why his ID-photo prints
    alone do not recognise him on camera: live samples are needed, which is what this card is for.
  - 🔴 **BUG FIXED: `presence.clean_name` filtered to `[A-Za-z]`, so "Mmoloki Ntshékáng" was stored
    as "Mmoloki Ntshkng"** — deleting letters from a name he typed, inside the feature built to stop
    mangled names. Now keeps any letter of any alphabet, still drops digits/symbols.
  - So the live route is the one that works: take a picture in the room (or feed a decent photo),
    type the name.

## Traps (don't rediscover)
- Electron caches the HUD → keep `clearCache()` in main.js; served HUD updates need it.
- `worker-cheap` is a REASONING model → returns EMPTY on long full-file codegen; use
  `builder-reason` with big max_tokens for that, or keep triage prompts SHORT.
- My GDI screenshots come out DPI-skewed / off-centre — Prathap's own screenshots are the
  truth (the layout IS centred on his screen). Don't "fix" centring off my captures.
- winCodeSign symlink block → needs Developer Mode (above).
- A payment-authorising WRITE file (`approve.py`) is BLOCKED by the Claude Code auto-mode
  classifier — cannot be saved in auto mode; needs an interactive session + permission.

## Open items
- **In-ARIA 1-click approve** (calls complete_task): CFO wants it; blocked by the classifier.
  Either he unlocks it in an interactive session, or keep the tap-to-Omni deep-link (shipped).
- **Live-tune the gestures** on Prathap's camera (thresholds in gestures.js: hold times,
  finger `upY` deltas, nod/shake travel). Confirm the 4→1/2-finger flow fires for him.
- Ideas backlog (Fable): head-shake=no (done), presence-pause greeting, meeting-prep brief,
  "Hey ARIA" wake word, draft-email-reply.
- **The Mac's photographs ARRIVED (92e1eb2) and were REFUSED — they are 100-300px thumbnails
  and cannot identify anyone (see the 14th pass for the measurements).** Do not retry them.
  Either ask the Mac for the ORIGINALS behind `~/Aria/biometric`, or use the new
  LEARN A FACE card in the room. `shared/faces_photos/` still holds them.
- **Face-api on a `<video>` element can return 0 faces where a canvas snapshot of the SAME
  frame returns 1.** Always detect on a still. (Cost half an hour on 9-Sep.)
- **The Browser pane caches `faces.js`** — a change appears not to have taken. `fetch('./faces.js',
  {cache:'reload'})` then reload. The Electron app clears its cache each launch, so this bites
  only the test harness.
