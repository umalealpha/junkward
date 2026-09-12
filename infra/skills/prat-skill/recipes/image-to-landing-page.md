# Recipe: AI Image → Landing Page (Windows, non-coder edition)

Planned by Fable 5, 2026-08-15. **Verified live end-to-end 2026-08-15 19:49** (Windows, host Prat) — real headshot → real `gpt-image-1` call → real landing page opened. Reference photo + text prompt → AI image via OpenAI `gpt-image-1` → auto-branded Alpha Direct landing page, opened in the browser. Four copy-paste prompts, no code touched by Prathap.

**Verified before writing:**
- OpenAI key lives at `C:\ai-cost-stack\gateway\.env` under `OPENAI_API_KEY` (NOT `C:\Users\PrathapAsus\.claude\.env`).
- The :4000 LiteLLM gateway (`C:\ai-cost-stack\gateway\config.yaml`) is chat-only (deepseek / gemini / gpt-5.5) — **no images route**. Image calls must go direct to `api.openai.com`.

---

## 1. What this does (plain English for Prathap)

Drop one photo of yourself into a folder, paste four prompts into Claude Code one at a time, walk away with (a) a new AI photo built from your real face (e.g. you giving a TED talk) and (b) a polished one-page website with that photo as the hero, headline, subheadline and CTA button, already in Alpha Direct Navy/Orange, opened in your browser. You never touch code, you never re-paste your API key — the script reuses the key already on this PC.

## 2. Folder layout

```
C:\Users\PrathapAsus\ai-design-project\
├── headshot.jpg              ← YOU put this here
├── .env                      ← Claude creates (OPENAI_API_KEY, from the gateway .env, never shown on screen)
├── generate_image.py         ← Claude writes
├── generated_ted_talk.jpg    ← the AI image
└── index.html                ← the landing page
```

Keep it OUTSIDE OneDrive — the "OneDrive - Alpha Direct Insurance" path has spaces + a dash that break many CLI tools.

## 3. Prompt sequence

### Step 0 — you run this in PowerShell once

```powershell
mkdir C:\Users\PrathapAsus\ai-design-project
Copy-Item "C:\path\to\your\photo.jpg" C:\Users\PrathapAsus\ai-design-project\headshot.jpg
cd C:\Users\PrathapAsus\ai-design-project
claude
```

Clear front-facing photo, JPG/PNG, under 20 MB (hard API cap 50 MB, HEIC not supported).

### Prompt 1 — health check

```
Check my setup and fix anything missing. Run these checks:
1. Confirm Python 3.11+ is available (try `py --version` first, then `python --version`).
2. Confirm pip works (`py -m pip --version`).
3. Confirm the file headshot.jpg exists in this folder and tell me its size in MB.
If Python is missing, tell me in one plain sentence what to install and stop. Do not install Python yourself.
```

### Prompt 2 — set up the key

```
My OpenAI API key already exists on this PC in C:\ai-cost-stack\gateway\.env under the variable OPENAI_API_KEY.
Read that file, and create a new file .env in THIS folder containing exactly one line: OPENAI_API_KEY=<that value>.
NEVER print, echo, or display the key value in the chat — not even partially. Just confirm ".env created, key present (sk-... hidden)".
Do NOT point anything at the localhost:4000 gateway — it does not route image requests; the script will call api.openai.com directly.
```

### Prompt 3 — write + run the image generator

```
Create a file generate_image.py with EXACTLY the source code below (do not modify it), then:
1. Install dependencies: py -m pip install --quiet openai python-dotenv
2. Run it: py generate_image.py
3. Confirm generated_ted_talk.jpg exists and tell me its size.
If the API returns an error, show me the error message in plain English with the fix, and never show my API key.

[PASTE THE FULL SCRIPT FROM SECTION 4 BELOW]
```

To change what the image shows, edit the `PROMPT = ...` line in the script (e.g. "keynote at an insurance conference in Gaborone") before pasting.

### Prompt 4 — build + open the landing page

```
Create index.html with EXACTLY the template below (do not modify the design), then open it in my default browser by running this PowerShell command: start .\index.html
Confirm the browser opened.

[PASTE THE FULL HTML FROM SECTION 5 BELOW]
```

## 4. `generate_image.py` — full source

API facts baked in (Jan 2026):
- Endpoint: `POST https://api.openai.com/v1/images/edits`
- Model id: `gpt-image-1`
- Wire format: `multipart/form-data` (reference photo uploaded as file part)
- Fields used: `model`, `image`, `prompt`, `size` (`1536x1024` landscape for hero), `quality=high`, `input_fidelity=high` (keeps the face recognisable), `output_format=jpeg`
- Response: JSON `{"data":[{"b64_json":"..."}], ...}` — gpt-image-1 always returns base64, never a URL
- SDK: `openai` Python v1.x → `client.images.edit(...)`

```python
"""
generate_image.py — image-to-image with OpenAI gpt-image-1.
Takes headshot.jpg + a text prompt, saves generated_ted_talk.jpg.
Reads OPENAI_API_KEY from ./.env, falling back to the cost-stack
gateway env at C:\\ai-cost-stack\\gateway\\.env. Never prints the key.
"""
import base64
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

HERE = Path(__file__).resolve().parent
REFERENCE = HERE / "headshot.jpg"
OUTPUT = HERE / "generated_ted_talk.jpg"

PROMPT = (
    "A highly professional photo of this person giving a TED talk on a large "
    "stage, standing confidently mid-presentation, dramatic warm stage "
    "lighting, red TED-style circular carpet, large dark auditorium with a "
    "blurred audience, big presentation screen behind them, photorealistic, "
    "shot on a professional DSLR, keep the person's face and likeness "
    "exactly as in the reference photo."
)

# --- Load the API key (project .env first, then the cost-stack gateway) ---
load_dotenv(HERE / ".env")
if not os.getenv("OPENAI_API_KEY"):
    load_dotenv(r"C:\ai-cost-stack\gateway\.env")

if not os.getenv("OPENAI_API_KEY"):
    sys.exit(
        "ERROR: OPENAI_API_KEY not found in ./.env or "
        r"C:\ai-cost-stack\gateway\.env. Ask Claude Code to recreate .env."
    )

# --- Sanity-check the reference photo ---
if not REFERENCE.exists():
    sys.exit(f"ERROR: {REFERENCE.name} not found in {HERE}. Copy your photo "
             "into this folder and name it headshot.jpg.")
size_mb = REFERENCE.stat().st_size / (1024 * 1024)
if size_mb > 50:
    sys.exit(f"ERROR: {REFERENCE.name} is {size_mb:.1f} MB — the API limit "
             "is 50 MB. Use a smaller photo.")

# NOTE: talks to api.openai.com directly. The local :4000 gateway is
# chat-only and does not route /v1/images/edits.
client = OpenAI()  # picks up OPENAI_API_KEY from the environment

print(f"Generating image from {REFERENCE.name} ({size_mb:.1f} MB)... "
      "this takes 30-90 seconds.")

with open(REFERENCE, "rb") as image_file:
    result = client.images.edit(
        model="gpt-image-1",
        image=image_file,
        prompt=PROMPT,
        size="1536x1024",       # landscape, ideal for a hero banner
        quality="high",
        input_fidelity="high",  # preserves the face from the reference photo
        output_format="jpeg",
    )

image_bytes = base64.b64decode(result.data[0].b64_json)
OUTPUT.write_bytes(image_bytes)
print(f"Done. Saved {OUTPUT.name} ({len(image_bytes) / 1024:.0f} KB).")
```

## 5. `index.html` — Alpha Direct branded template

Self-contained, responsive, respects system dark mode, Navy `#1D3270` + Orange `#F4A623` by default. Change `--navy` to `#0D1B2A` if matching Finance letterhead spec.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Talk Everyone Will Remember</title>
<style>
  :root {
    --navy: #1D3270;
    --orange: #F4A623;
    --bg: #f7f8fc;
    --surface: #ffffff;
    --text: #1a2238;
    --muted: #5a6480;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0c1226;
      --surface: #16204a;
      --text: #eef1fa;
      --muted: #9aa5c8;
    }
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
    background: var(--bg); color: var(--text);
    -webkit-font-smoothing: antialiased;
  }
  .hero {
    min-height: 100vh; display: flex; align-items: center;
    padding: 48px 24px;
    background:
      radial-gradient(1200px 600px at 85% -10%,
        rgba(244, 166, 35, 0.18), transparent 60%),
      linear-gradient(160deg, var(--navy) 0%,
        color-mix(in srgb, var(--navy) 70%, black) 100%);
  }
  .hero-inner {
    max-width: 1100px; margin: 0 auto; display: grid;
    grid-template-columns: 1fr 1fr; gap: 56px; align-items: center;
  }
  .eyebrow {
    display: inline-block; color: var(--orange);
    font-size: 0.8rem; font-weight: 700; letter-spacing: 0.18em;
    text-transform: uppercase; margin-bottom: 18px;
  }
  h1 {
    color: #ffffff; font-size: clamp(2rem, 4.5vw, 3.4rem);
    line-height: 1.12; letter-spacing: -0.02em; margin-bottom: 20px;
  }
  h1 .accent { color: var(--orange); }
  .sub {
    color: rgba(255, 255, 255, 0.82);
    font-size: clamp(1rem, 1.6vw, 1.2rem);
    line-height: 1.65; margin-bottom: 34px; max-width: 46ch;
  }
  .cta {
    display: inline-block; background: var(--orange); color: #1a1300;
    font-weight: 700; font-size: 1.05rem; text-decoration: none;
    padding: 16px 38px; border-radius: 999px;
    box-shadow: 0 8px 28px rgba(244, 166, 35, 0.38);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }
  .cta:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 34px rgba(244, 166, 35, 0.5);
  }
  .hero-media img {
    width: 100%; display: block; border-radius: 18px;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.45);
    border: 1px solid rgba(255, 255, 255, 0.12);
  }
  .credit {
    text-align: center; color: rgba(255, 255, 255, 0.45);
    font-size: 0.8rem; margin-top: 14px;
  }
  @media (max-width: 820px) {
    .hero { padding: 64px 20px; }
    .hero-inner { grid-template-columns: 1fr; gap: 36px; }
    .hero-media { order: -1; }
  }
</style>
</head>
<body>
  <section class="hero">
    <div class="hero-inner">
      <div>
        <span class="eyebrow">Live on stage</span>
        <h1>Ideas that move an <span class="accent">industry</span> forward.</h1>
        <p class="sub">Join Prathap Ganesharajah for a talk on how AI, discipline,
        and first-principles finance are rewriting what an insurance company
        can be — from Gaborone to the world.</p>
        <a class="cta" href="#book">Reserve Your Seat</a>
      </div>
      <div class="hero-media">
        <img src="generated_ted_talk.jpg"
             alt="Prathap Ganesharajah delivering a TED talk on stage">
        <p class="credit">Image generated with OpenAI gpt-image-1</p>
      </div>
    </div>
  </section>
</body>
</html>
```

## 6. Open the page

```powershell
start .\index.html
```

Claude Code runs this in Prompt 4. If running it yourself, be in the project folder first (`cd C:\Users\PrathapAsus\ai-design-project`). Git Bash equivalent: `explorer.exe index.html`.

## 7. Failure modes → plain-English fix

| What you see | What it means | Fix |
|---|---|---|
| `'python' is not recognized` / `'py' is not recognized` | Python isn't installed or not on PATH | Install Python 3.12 from python.org and **tick "Add python.exe to PATH"**. Close+reopen PowerShell. |
| `No module named openai` after installing | pip installed into a different Python than the one running | Always `py -m pip install openai python-dotenv` and run with `py generate_image.py` — `py -m` guarantees they match. |
| `ERROR: OPENAI_API_KEY not found` | `.env` missing or in wrong folder | Re-run Prompt 2. `.env` must sit alongside `generate_image.py`. Script auto-falls back to `C:\ai-cost-stack\gateway\.env`. |
| `model_not_found` or 403 `You must be verified to use gpt-image-1` | OpenAI org not identity-verified | One-time: platform.openai.com → Settings → Organization → Verify. Then re-run. |
| `400 Bad Request` mentioning the image | Photo too large (>50 MB) or unsupported (e.g. HEIC from iPhone) | Use JPG/PNG under ~20 MB. Windows Photos → "Save as" JPG. |
| Hangs then `Connection error` | Firewall/VPN blocking api.openai.com, or aimed at :4000 | Do NOT use localhost:4000 for this. Off VPN. |
| Hero image = broken icon in browser | `generated_ted_talk.jpg` missing / renamed | Re-run Prompt 3; filenames must match exactly. |
| Paths-with-spaces break commands | Project created inside OneDrive folder | Keep at `C:\Users\PrathapAsus\ai-design-project` (outside OneDrive). Quote paths if you must: `cd "C:\folder with spaces"`. |
| Generated face doesn't look like Prathap | `input_fidelity` dropped, or low-quality reference | Keep `input_fidelity="high"`. Use sharp, front-facing, well-lit photo. |

## 8. Alpha Direct fit

- **Model routing:** DeepSeek carve-out does NOT apply — image gen. OpenAI `gpt-image-1` is the sanctioned tool. Reuses the existing `OPENAI_API_KEY` from `C:\ai-cost-stack\gateway\.env` — no new secret, no chat paste. Key stays on disk, passed only to the local Python subprocess (allowed pattern).
- **Gateway note:** image calls go direct to api.openai.com; :4000 gateway has no images route so these calls **will NOT appear in the cost-stack ledger**. Roughly USD 0.20-0.30 per high-quality image, 30-90s per generation.
- **Cost control (added 2026-08-15, verified live):** every call appends one row to `C:\ai-cost-stack\image-costs.csv` (timestamp, model, size, est_$, output_kb, prompt-summary, project-folder). Before each call the script sums this month's CSV rows, prints the running spend, and **hard-aborts** if this call would push the month over `IMAGE_MONTHLY_CAP_USD` (default 20). Raise for a specific run: `set IMAGE_MONTHLY_CAP_USD=50 && py generate_image.py`. Estimate hard-coded at USD 0.20 per landscape 1536x1024 high-quality call (conservative vs the published ~USD 0.19). This is the ONLY visibility into image spend — nothing on the OpenAI dashboard is broken down by project. Karpathy-clean: gate runs before the API call so a misconfig never leaks money.
- **Brand default:** template ships Navy `#1D3270` / Orange `#F4A623` as CSS vars — Alpha Direct on-brand out of the box. Two-line change for other palettes.
- **DPA:** headshot = personal data. CFO/EXCO exemption applies for Prathap's own photo. If sharing this recipe with other staff, add one line to Prompt 3: only use photos of yourself or with written consent.

---

**Critical files:**
- `C:\ai-cost-stack\gateway\.env` — verified `OPENAI_API_KEY` source
- `C:\ai-cost-stack\gateway\config.yaml` — proves :4000 has no images route (forces direct api.openai.com)
- `C:\Users\PrathapAsus\ai-design-project\generate_image.py` — the gpt-image-1 script
- `C:\Users\PrathapAsus\ai-design-project\index.html` — branded landing template
- `C:\Users\PrathapAsus\ai-design-project\.env` — per-project key copy with gateway fallback
