# /qctest — run the Omni QC checker

Two modes: **fast** (the mechanical robot) and **smart** (AI eyes that test like a human).

## Usage

- `/qctest dashboard` — fast check on one screen (photos + pass/fail)
- `/qctest dashboard claims payroll/payslips` — fast check on several screens
- `/qctest` — fast sweep of every screen the robot knows
- `/qctest smart dashboard` — **AI-powered check**: opens the page, looks at it like a real person, and reports what is wrong
- `/qctest smart dashboard --click "Refresh"` — AI clicks a button and judges the result
- `/qctest /hris/leave --click "Team Leave Report"` — fast check with a button click

## When to use which

| Mode | Best for | Speed | Cost |
|---|---|---|---|
| **Fast** (default) | Did the page load, crash, or break? Mechanical pass/fail. | ~10s per screen | Free |
| **Smart** (`smart`) | Does the page LOOK right? Is the data sensible? Would a human tester flag this? | ~30-60s per screen | ~$0.01 per screen (GPT-4o-mini) |

**Default is fast.** Use smart when you need human-like judgement — after a big change,
before a release, or when fast says CLEAN but something still feels off.

## How to run it (for Claude)

### Fast mode (mechanical checks)

```bash
# Token refresh (silent, always do first)
cd "C:/Users/PrathapAsus/.claude/skills/prat-skill/e2e"
bash qc-token.sh 2>/dev/null

# Make an output folder for this run
OUTDIR="$(mktemp -d)/qc-run"
mkdir -p "$OUTDIR"

# Run the check — replace the args with whatever the user asked
cd "$OUTDIR"
bash "C:/Users/PrathapAsus/.claude/skills/prat-skill/e2e/qc.sh" "/dashboard"
```

Photos land in `$OUTDIR`. Read them (the .png files) and read `qc-report.json`
for the structured verdict.

### Smart mode (AI human-like check)

```bash
# Token refresh first
cd "C:/Users/PrathapAsus/.claude/skills/prat-skill/e2e"
bash qc-token.sh 2>/dev/null

# Make an output folder
OUTDIR="$(mktemp -d)/qc-smart"
mkdir -p "$OUTDIR"
cd "$OUTDIR"

# Run the smart check — it opens a real browser and has AI look at the page
python "C:/Users/PrathapAsus/.claude/skills/prat-skill/e2e/qc-smart.py" "/dashboard"
```

The AI writes a plain-English verdict + bullet points of what it found.
Report saved to `qc-smart-report.json` in the output folder.

## Rules

- **Always refresh the token first** — it expires after 15 hours.
- **Fast mode: always READ the photos** before reporting — never say "looks good" without looking.
- **Smart mode: read the AI's verdict** and relay it in plain English.
- **Plain English verdict** to Prathap: which screens passed, which broke, and what broke.
- If anything is PROBLEMS, say so up front — lead with what is broken.
- Send the photos to Prathap (SendUserFile) so he can see them himself.
- If no screen is specified and mode is fast, run the full sweep (`qc.sh` with no args).
- **Smart mode uses GPT-4o-mini** via the OpenAI key in the cost stack. No paid Anthropic key used.
