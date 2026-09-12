---
name: time-doc-cheaters
description: Time Doctor cheat check — opens the Screen Integrity Monitor in Omni. Catches the frozen-screen / weight-on-a-key trick. Trigger on /time-doc-cheaters or "check time doctor cheaters".
---

# /time-doc-cheaters — Screen Integrity Monitor

Catches staff who fake Time Doctor productive hours by holding down a key or leaving a frozen screen while appearing to work.

## What the detector does

Two catchers, both running from data the daily Time Doctor pull already fetches — no new PII, no titles stored:

1. **Frozen-screen catcher (the real one):** Keys ≥ 40 tapped on a screen that never changes (same pixel hash). Flags 'suspicious' when ≥25% of intervals AND ≥2 hours. Jiggler-proof — real typing MUST change something on screen.

2. **Session-block catcher (backstop):** One unbroken 3h+ block with ≤1 idle break AND ≤2 distinct windows open. Catches the held-key variant. Safe — never fires on a busy multi-window worker.

Both flag for human "explain your day" review. **Neither auto-docks leave.**

## How to use this skill

When triggered, do the following:

### 1. Open the Screen Integrity Monitor in Omni
Navigate to: **People (HRIS) → Screen Integrity**
URL: `https://omni.alphadirect.co.bw/hris/screen-integrity/`

### 2. Run a date sweep from the server (if a specific date is needed)

```bash
# Frozen-screen sweep for all staff on a date
ssh-ssm prod "cd /opt/alpha-finance && python manage.py detect_frozen_screen --date YYYY-MM-DD"

# One person, 90-day back-scan (for a hearing)
ssh-ssm prod "cd /opt/alpha-finance && python manage.py detect_frozen_screen --user 'Full Name' --date YYYY-MM-DD --days 90"

# Weight-on-key backstop sweep
ssh-ssm prod "cd /opt/alpha-finance && python manage.py detect_fake_activity --date YYYY-MM-DD"
```

Replace `YYYY-MM-DD` with the date to check. The frozen-screen command is the primary one.

### 3. Interpret the output

| Flag | Meaning | Action |
|------|---------|--------|
| **SUSPICIOUS** | ≥25% frozen intervals, ≥2h | Trigger explain-your-day, preserve evidence |
| **WATCH** | Borderline — mouse moving, below gate | Monitor for a week, no action yet |
| *(no flag)* | Clean day | Nothing to do |

### 4. If a hearing is needed (CFO authorises)
1. Run the 90-day back-scan for the person
2. Preserve the output (do NOT auto-dock leave yet)
3. CC Unami Butale on all HR actions
4. CFO authorises the formal step

## Known confirmed cheaters (as of 2026-09-01)
- **Meduduetso Tlagae** — SUSPICIOUS 95%, 3.8h, 8 days in 90-day scan. Held auto-repeating key.
- **Kago Tshutlhedi (Finance Manager)** — SUSPICIOUS 60%, 2.2h. Second confirmed cheat.
- CFO forgave both "for now" pending the deterrence announcement.

## What this skill does NOT catch
- The SESSION-BLOCK detector (`detect_fake_activity`) **misses** the frozen-screen pattern — the frozen-screen command is the one that works.
- Multi-monitor capture needs real-world verification before any hearing.

## Morning brief integration
The frozen-screen flags appear automatically in every manager's 9AM Morning Brief under "Time-tracking integrity". Green = nobody flagged. Amber = flags to review.

## Files in alpha-finance (read-only reference)
- `integrations/td_screenshot_integrity.py` — frozen-screen detector
- `integrations/td_integrity.py` — session-block detector
- `integrations/td_integrity_alert.py` — morning brief integration
- `integrations/management/commands/detect_frozen_screen.py` — the command
- `integrations/management/commands/detect_fake_activity.py` — backstop command
