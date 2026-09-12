# eyes-on — the omni screenshot / QA toolkit (Windows)

Photographs any omni screen exactly as an ordinary staff member sees it, so layout
problems and "you're not allowed" errors show up in a picture instead of being found
by Oprah.

**The rule it enforces:** no screen ships until it has been photographed and eyeballed —
every page and every pop-up, at laptop width, as an admin **and** as the non-admin
staff test account.

## First time only — save the two logins

Nothing here types a password. You sign in once by hand and the browser session is
saved to `sessions/` (locked to your Windows account, git-ignored, never printed).

Double-click, in this folder:

1. **`Save login - staff.cmd`** → sign in as `omni@alphadirect.co.bw` (the non-admin
   finance-manager test account), including the 6-digit code that gets emailed.
2. **`Save login - admin.cmd`** → sign in with your own Microsoft account.

Then press Enter in the black window. Re-run either one if screenshots start coming
back looking signed out (roughly every few weeks).

## The commands

Run these from this folder.

```bash
# One command - shoots a screen as BOTH admin and staff, at 1120 and 1280,
# and opens a pop-up if you name a button:
node eyes-on.mjs "/internal-audit/findings" --click "New finding"

# A single screenshot of one screen:
node omni-shot.mjs "/commissions" out.png --width 1120 --as staff

# A whole step-by-step flow as one picture:
node omni-journey.mjs journey.json

# Old vs new side by side:
node omni-compare.mjs "/dashboard" --a https://omni.alphadirect.co.bw --b http://localhost:3000

# Page health sweep (32 key pages, or every route in the repo):
node omni-healthboard.mjs --as staff
node omni-healthboard.mjs --from-repo C:/Users/PrathapAsus/work/alpha-finance
```

`eyes-on.cmd` and `eyes-on.sh` are the same thing as `node eyes-on.mjs`, for cmd and
Git Bash respectively.

## What the verdicts mean

| Verdict | Meaning |
|---|---|
| `OK` | Page rendered with real content, no console errors |
| `OK*` | Rendered, but the browser logged console errors |
| `BLOCKED` | A permission wall — the role can't get in |
| `BLANK` | Rendered nothing |
| `SPINNING` | Still loading when the shot was taken |
| `BROKEN` | 404, 500, or an error message on screen |

`eyes-on` and the healthboard exit non-zero when something is BROKEN or BLANK, so they
can gate a deploy.

## Files

| File | What it is |
|---|---|
| `lib.mjs` | Shared plumbing: sessions, screenshots, verdicts, picture-stitching |
| `omni-login.mjs` | One-time interactive sign-in that saves a session |
| `eyes-on.mjs` | Both roles × both widths → one picture |
| `omni-shot.mjs` | Single screenshot |
| `omni-journey.mjs` | Multi-step flow → one picture |
| `omni-compare.mjs` | Two environments side by side |
| `omni-healthboard.mjs` | Sweep many pages, flag the bad ones |
| `pages.json` | The default 32-page sweep list |
| `sessions/` | Saved logins — **never commit or share** |
| `shots/` | Output pictures |

## Notes

- Pictures are stitched by rendering them into a plain HTML page and screenshotting it,
  so the only dependency is Playwright.
- `omni-login.mjs` also saves `sessionStorage`, which is where the Microsoft sign-in keeps
  its token; Playwright's normal session save leaves that out and the admin session would
  silently come back signed out.
- Point at a different environment with `OMNI_BASE`, e.g.
  `OMNI_BASE=http://localhost:3000 node omni-shot.mjs "/dashboard"`.
