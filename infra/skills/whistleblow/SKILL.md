---
name: whistleblow
description: >-
  Alpha Direct Speak-Up whistleblowing system — full project context and the
  non-negotiable working rules. Load this whenever the user types /whistleblow,
  or mentions Speak-Up, the whistleblowing / ethics / fraud-reporting portal,
  anonymous staff reporting, the KPMG fraud line (fraud@kpmg.co.bw), the
  `alpha-direct-speakup` or `alpha-direct-speakup-demo` repos, the reporting
  demo, or asks to deploy, change, present, or explain that system. Use it
  BEFORE touching any Speak-Up code, the demo, or writing about how the
  anonymity works — it carries what is built, where it lives (paths, repos,
  live URL), the anonymity rules that must never be weakened, and the open
  go-live decisions, so context isn't rebuilt and anonymity isn't accidentally
  broken.
---

# Alpha Direct Speak-Up — whistleblowing system

Confidential channel for Alpha Direct staff to report fraud, mismanagement,
sexual abuse/harassment and other serious concerns. Reports are handled
**independently by KPMG** (`fraud@kpmg.co.bw`), never by Alpha Direct
management. The reporter stays anonymous and can still have a two-way
conversation with KPMG via a one-time receipt code.

The user is **Prathap, the CFO — non-technical**. Talk to him in plain English
(see the global CFO layman rule). Technical detail belongs in tool calls and in
this file, not in his face.

---

## Current state (as of 2026-06-24)

Two separate things exist:

| | Demo (for presenting) | Real system (production) |
|---|---|---|
| What | Clickable mock-up, fake sample cases | The actual working software |
| Online | **Yes** — https://prathap-alpha.github.io/alpha-direct-speakup-demo/ | Not yet (needs hosting) |
| Repo | `Prathap-Alpha/alpha-direct-speakup-demo` (**public**) | `Prathap-Alpha/alpha-direct-speakup` (**private**, `main` @ `63d9237`) |
| Windows path | `C:\Users\PrathapAsus\work\alpha-direct-speakup-demo` | `C:\Users\PrathapAsus\work\alpha-direct-speakup` |
| Data | Fake only | Real, encrypted |

- Demo version shown on screen: `v1.0.0`. Sample track code: **`DEMO-1234`**.
- Real system: prat-test gate passed, **22 pytest tests green**, not deployed anywhere.
- Neither is wired into omni / alpha-finance. This is a standalone project.

---

## The anonymity design — DO NOT WEAKEN

These are the whole point. A whistleblowing tool that leaks identity is worse
than none, so treat any change that touches these as high-risk and preserve them:

- **No account, no PII.** No name, email or phone is ever requested from a reporter.
- **No IP, no cookies.** The app never reads/stores the reporter's IP; reporters
  get no cookie (sessions exist only for KPMG investigators).
- **No third-party requests.** Strict CSP; nothing loads from a CDN/analytics, so
  a reporter's browser only ever talks to the server.
- **Encrypted at rest.** Report content is Fernet-encrypted; the key lives in the
  environment, not the database.
- **Receipt code = the only thread back.** Stored only as a SHA-256 hash; a lost
  code is unrecoverable by design. It gives two-way, still-anonymous follow-up.
- **Content-free alerts.** KPMG's email notification carries only a reference +
  category, never report content or anything about the reporter.

**Telegram was deliberately rejected** — a bot always exposes the user's identity
to whoever runs it, so it can't be truly anonymous. Do not re-propose a Telegram
bot as the anonymous channel. A web form (optionally over Tor) is the design.

---

## Guardrails for any future change

- **Never let the demo be mistaken for the real line.** The public demo must keep
  its prominent "DEMONSTRATION — not a live channel" banner, or a real abuse
  report could be typed into a mock-up.
- **Keep the production repo private.** It should not be visible to TheRiskCo or
  other org admins. Only fake data goes in the public demo repo.
- **Never put real reports / secrets in the public demo repo.**
- **Verify, don't claim.** Before "done": for the app, `python -m pytest` green +
  exercise the flow; for the demo, load the live URL and click through; for an
  email, send via Graph and confirm it in Sent Items. (prat-test gate applies.)

---

## Present the demo (3 clicks)

1. Open https://prathap-alpha.github.io/alpha-direct-speakup-demo/
2. **Report a concern** → pick a category, type anything → **Submit** → it shows a one-time code.
3. **Track a report** → paste that code, or use **`DEMO-1234`** → show the two-way KPMG thread.
   Then **KPMG console** → the investigator side (sample cases, statuses, stats).

Update the demo: edit `index.html`, push to `main`, GitHub Pages rebuilds in ~1 min.

---

## Tech (real system)

- **Stack:** Python Flask + SQLite + Jinja, no JS framework, no build step. Single
  `app.py`; templates in `templates/`; brand CSS in `static/style.css`.
- **Run locally:** `flask --app app run` after `flask --app app gen-keys` → `.env`,
  `flask --app app init-db`, `flask --app app add-investigator <user> "<name>"`.
- **Production:** `docker compose up` (gunicorn; access log omits client IP).
- **`SECURITY.md`** in the repo has the go-live hardening checklist — the reverse
  proxy must ALSO not log IPs; optional Tor onion address for max anonymity.
- **Tests:** `python -m pytest` (22 tests, all green — anonymity, encryption,
  two-way, CSRF/lockout, XSS, SQLi, EXIF strip, decompression-bomb, decrypt).
- Brand: navy `#0D1B2A`, orange `#F4A623`, Book Antiqua headings.

---

## Open decisions before go-live

1. **Where to host** the real system (its own small server, separate from omni, recommended).
2. **KPMG's login** — who at KPMG holds the reviewer account.
3. **Move the private repo into the `alphadirectinsurance` org?** (Kept personal/private on purpose.)
4. **Email alerts** — plug SMTP details into `.env` so KPMG gets the "new report" notification.
5. **Security review** before it takes real reports.

---

## People & comms

- **Kakale Botana** — Compliance Manager, requested the system. `kbotana@alphadirect.co.bw`.
- **Oprah Mogomotsi** — `omogomotsi@alphadirect.co.bw`. **Unami Butale** — HR, `ubutale@alphadirect.co.bw`.
- 2026-06-24: sent Kakale (cc Oprah, Unami) the base-build + anonymity explanation email.
- Email as CFO: `prat-skill/tools/send_mail.py --to --cc --subject --body-file` (sends as pganesharajah@).

---

## Pointers

- **Source-of-truth doc:** `Desktop\whistleblow.md` (plain-English project record).
- **Auto-memory:** `p-speaku`. **Cross-machine log:** `Gods Eye\MACHINE-SYNC.md`.
- This skill is a context loader — keep it in sync when the project moves (new repo
  home, deployed URL, KPMG onboarded, etc.).
