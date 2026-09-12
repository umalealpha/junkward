---
name: acca
description: >
  Quick-start context for the ACCA Botswana members' website (a.k.a. the "BCAT
  Member Portal") at www.bcat.africa. Auto-load whenever Prathap types "/acca",
  says "work on the ACCA site" / "the BCAT website" / "the panel page", or the
  task touches: the Meet-Your-Panel committee page, committee member photos,
  bcat.africa, the bcat-portal repo, or deploying/changing that site. Loads the
  current build state, the committee list, the photo-cropping recipe, and the
  open items so a fresh chat continues exactly where the last session left off.
  Complements prat-skill (full dev stack) and the p-bcat-portal memory.
  Keep "current state" and "open items" updated as work lands.
---

# acca — ACCA Botswana members' website quick-start

**Talk to Prathap (CFO) in plain English — he is not a coder.** Lead with what a
change means for him and the one thing he must do. Do the whole ask in one run;
only stop for the hard lines: **going live / pushing** (a push can auto-publish
the public site), changing access, or deleting live data. Full working
conventions live in **prat-skill**; this is the site-specific starting context.

## What this site is
- The **ACCA Botswana members' website**. The code brands it **"BCAT — Botswana
  Certified Accountants Trust"** (the org started as an ACCA-Botswana build and was
  renamed). **PERSONAL / separate from Alpha Direct** (like Nako Pula, Lumen).
- **Live:** https://www.bcat.africa (hosted on **Railway**, deploys from GitHub).
- **Repo:** `github.com/Prathap-Alpha/bcat-portal` (PRIVATE, gh = `Prathap-Alpha`).
- **Local working copy:** `C:\Users\PrathapAsus\Downloads\bcat-portal-extracted\acca-botswana-portal`.
- **Stack:** React 19 + Vite + TypeScript, Tailwind, wouter routing / Express + tRPC + Drizzle (MySQL).
- **Full handover doc in the repo:** `ACCA.md` (read it first — richest detail).

## How to preview (for the AI)
The full app needs MySQL, but the pages we usually touch (e.g. `/panel`) are
**public static routes** — preview the built client with no backend:
```
cd <repo>;  npx vite build          # → dist/public
# serve dist/public statically (python -m http.server) and open /panel
```
Backend/tRPC calls error on a static host — expected, harmless for static pages.
Preview note (seen 20 Jun 2026): the in-app browser-preview renderer can break
(screenshots/evals hang, images read 0×0 though HTTP 200). If so, verify image
crops **offline with Pillow** by masking into a circle instead of a live shot.

## How to deploy (ONLY on Prathap's explicit go-ahead)
Railway builds from the GitHub repo: push → `pnpm install` + `pnpm build` → start
`pnpm start`; `preDeployCommand` runs `drizzle-kit migrate`. **Do not push without
his yes** — a push can trigger an auto-deploy to the live public site, and the
active branch `feat/oauth-providers-admin-vault` also carries unmerged OAuth work.
Railway project **thorough-harmony**, service **bcat-portal**. Custom domain via
GoDaddy DNS (CNAME `www` → Railway target).

## Current state (as of 2026-06-20 — update as work lands)
- **"Meet Your Panel" page** (`client/src/pages/Panel.tsx`) now shows the **real
  ACCA Botswana Members Panel 2024/25** — 9 members with roles, credentials,
  positions, bios (was fictional placeholders). Source: Prathap's
  `Downloads\ACCA_Botswana_Panel_Committee_Package.zip`.
- **Photos:** 8 headshots in `client/public/panel/*.jpg`, served at `/panel/<name>.jpg`.
  Round avatars enlarged to `w-28 h-28` (112px), `object-cover object-center`,
  initials fallback when no photo. Stat updated to "9 Elected Members".
- **NOT deployed.** All of the above is **uncommitted** on branch
  `feat/oauth-providers-admin-vault`; www.bcat.africa still shows the old page.
- **Login already live** (earlier session): Google + Microsoft sign-in; admin
  AI-key vault at `/admin/settings`. See `p-bcat-portal` memory.

## The committee (page order)
1 Prathap Ganesharajah — Chairman · 2 Kempho Tsheko — Vice Chairman · 3 Paphane
Mpapho Botlhale · 4 Iwani Bonyo-Tlhalerwa · 5 Galegake Onna · 6 Mokgethoa Molotsi
· 7 Reabetswe Ponyane · 8 **Kethamile Thuto Mazwiduma (no photo yet — "KM")** ·
9 Fabia Seile. (Full titles/bios in `ACCA.md` and `Panel.tsx`.)

## Photo gotcha (why the round photos needed fixing)
Package photos are **not plain headshots** — each is a portrait already cropped
into a **circle inside a square**, with white corners + slivers of neighbouring
members' circles bleeding in at the edges (cut from the summary-PDF grid). Raw,
they show stray arcs and off-centre faces in a round avatar. Fix = **re-crop to a
face-centred square with Pillow**, then `object-cover object-center`. Crop boxes
used `(left, top, size)` on the 400×400 originals, resized back to 400×400:
`prathap (60,18,292)` · `paphane (78,44,252)` · `galegake (60,14,292)` ·
`mokgethoa (70,30,270)` · `reabetswe (132,24,128, was full-body → head+shoulders)`.
Kempho / Iwani / Fabia were already fine. Verify by masking into a circle before shipping.

## Open items (needs Prathap / next session)
1. **Kethamile Thuto Mazwiduma's photo** → save `client/public/panel/kethamile-mazwiduma.jpg`
   and add `photo: "/panel/kethamile-mazwiduma.jpg"` to member 8 in `Panel.tsx`.
2. **Branding wording** — panel copy says "elected by BCAT members". Decide BCAT vs ACCA Botswana.
3. **Deploy** — commit + push once (1) and (2) are settled, on his go-ahead.

## Deeper context
Repo `ACCA.md` (fullest), and auto-memory `p-bcat-portal`. Load **prat-skill**
for the full dev/deploy/quality stack.
