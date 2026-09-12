---
name: Tony
description: Tony Fragrances CRM — Prathap's PERSONAL perfume-retailer CRM app for Tony in Gaborone. Auto-load when Prathap types /Tony, says "Tony Fragrances" / "Tony CRM" / "ScentBook" / "Tony's app" / "the perfume app", or works on the tony-fragrances-crm repo. Covers the Expo/React Native Web PWA, Supabase shared-passcode sync, cross-device merge (mergeData), deploys to Netlify + GitHub Pages, Tony's catalogue, and known traps. This is a PERSONAL project — NOT Alpha Direct; Alpha Direct governance/brand/frozen numbers do NOT apply.
---

# Tony Fragrances CRM

Branded black-and-gold CRM for **Tony Fragrances** — a Botswana perfume retailer run by **Tony** (`letebtony@gmail.com`). Customers, catalogue/stock, sales, invoices (PDF), deliveries, finance. Owner: **Prathap's personal project, NOT Alpha Direct.** Alpha Direct governance, brand (Navy/Orange), DPA intake, and frozen financial numbers do NOT apply.

## Where things are

| | |
|---|---|
| Repo | `github.com/Prathap-Alpha/tony-fragrances-crm` (PUBLIC, `master` = source, `gh-pages` = built site) |
| Local clone | `C:\Users\PrathapAsus\work\tony-fragrances-crm` |
| Stack | Expo SDK 54, React Native Web, TypeScript, NativeWind/Tailwind, exported as a **static PWA** |
| Storage | **Supabase** (nakotech project) — one JSON row per workspace in `tony_crm` table. Passcode-based access. |
| Primary URL | **https://scentbook-453480.netlify.app** (neutral — no GitHub username exposed) |
| Backup URL | https://prathap-alpha.github.io/tony-fragrances-crm/ (GitHub Pages) |

## The real user

**Tony** — uses the app on both his phone and his laptop. Email: `letebtony@gmail.com`. He is NOT technical. Any email to him: plain, friendly, short. Sign off as Prathap (personal capacity, not CFO).

## Storage & sync architecture

**Google Drive was dropped** (19-Aug-2026). The root cause of Tony's "data vanishes between devices" was Google's OAuth token expiring after ~1 hour — the app silently lost its sign-in and stopped syncing while still looking normal.

**Current design — Supabase + shared passcode:**
- Data lives in the `tony_crm` table in Prathap's **nakotech Supabase project** (`xvqnuycevvirmehzbtyj.supabase.co`).
- One JSON row per workspace. The workspace key = `SHA-256("tony-fragrances::" + passcode)`.
- Two devices that type the **same passcode** share the same row → same data.
- A passcode never expires, so the silent-sign-out bug cannot recur.
- **Row Level Security**: the workspace key is sent as `x-workspace` header on every request. RLS only exposes the row whose key matches. Without the passcode, the public anon key sees **nothing**.

**Supabase credentials (nakotech project, shared with Nako Pula):**
- **Project URL:** `https://xvqnuycevvirmehzbtyj.supabase.co`
- **Anon key (legacy JWT):** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh2cW51eWNldnZpcm1laHpidHlqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc5ODE3MDIsImV4cCI6MjA5MzU1NzcwMn0.bXjePI2z21p17GWHbBjKypsMkhjdbkBUIveCodnqFC0`
- **Table:** `tony_crm`
- **Tony's passcode:** `Tony@123`
- The anon key is the legacy JWT format (starts `eyJ…`) — required for the `Authorization: Bearer` pattern the app uses. The new-format keys (`sb_publishable_…`) do NOT work here.

**Build-time config** (env vars baked into the bundle):
- `EXPO_PUBLIC_SUPABASE_URL` = the project URL above
- `EXPO_PUBLIC_SUPABASE_ANON_KEY` = the anon key above (safe to commit; RLS gates real access)
- Both set in `constants/supabase.ts`. When empty, the app still works offline (data stays on-device only).

**Cross-device merge (`mergeData` in `lib/crm-domain.ts`):**
- Every record type (customers, products, invoices, deliveries, payments, expenses) has an `id` field.
- `mergeData(a, b)` unions all arrays by ID — unique records from BOTH sides are kept.
- Same-ID conflicts: the dataset with the higher `updatedAt` wins.
- `updatedAt` on the merged result = `Math.max(a.updatedAt, b.updatedAt)`.

**Merge happens in TWO places (belt and suspenders):**
1. **Save path** (`doSave` in `lib/supabase-sync.ts`): reads latest remote → merges with local → upserts. Logged catch — if remote read fails, saves local as-is (self-healing).
2. **Load path** (`loadFromCloud` in `lib/crm-store.tsx`): reads local AsyncStorage + remote → merges → sets state → pushes merged back only if different from remote.

**Refresh:**
- **15-second polling** while the tab is open.
- **`visibilitychange` listener** — refreshes on tab-focus.
- Guarded by `syncingRef` to prevent concurrent runs.

**Known residual:** no per-record `updatedAt` — a stale tab can revert EDITS to existing records (not adds).

**22-Aug-2026 — the REAL sync killer found and fixed:** `public/sw.js` served every cross-origin GET cache-first, so Supabase polls returned a frozen first snapshot forever (writes passed; reads never refreshed — Tony's "10th time" complaint). Fixed: sw.js v3 never intercepts cross-origin; `loadRemote` adds `&limit=${Date.now()}` so even a stale old SW can't cache-match. Tombstones (`deletedIds` in CRMData + mergeData filter) shipped same day with a Delete-product button.

## AI assistant (22-Aug-2026)

- **"Assistant" on the More tab** (`app/assistant.tsx`, `lib/ai.ts`): Tony asks plain questions ("who owes me?", "what's low in stock?"); answers come from his live cloud data.
- **Relay:** Supabase Edge Function `tony-ai-ask` (DeepSeek `deepseek-chat`; key is a function secret — NEVER in the app bundle). Verifies workspace exists (403 otherwise), loads the row itself server-side.
- **Function source + deploys live in the Nako-Tech repo** (`supabase/functions/tony-ai-ask/` + workflow `deploy-tony-ai.yml`) because that repo holds the `SUPABASE_ACCESS_TOKEN` for the shared project. Nako's old `config.toml` breaks the latest CLI, so the workflow deploys from an isolated workdir — don't touch Nako's config.

## Key files

| File | What it does |
|---|---|
| `lib/crm-domain.ts` | All business logic: types, `emptyCRMData`, `createSaleRecord`, `applyPayment`, `financeSnapshot`, **`mergeData`** |
| `lib/crm-store.tsx` | React context (`CRMProvider` / `useCRM`): state, passcode sign-in/out, persist, `loadFromCloud`, polling + visibility auto-refresh |
| `lib/supabase-sync.ts` | Supabase adapter: passcode→workspace key (SHA-256), `loadRemote`, `saveRemote` (chained + merge), `signIn`/`signOut` |
| `constants/supabase.ts` | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_TABLE` |
| `supabase/tony_crm.sql` | Table creation + RLS policy (run once in Supabase SQL editor) |
| `components/signin-gate.tsx` | Passcode input screen (replaces old Google sign-in button) |
| `lib/invoice-pdf.ts` | HTML invoice template (branded, XSS-escaped) |
| `constants/catalogue.ts` | Tony's 13 Facebook fragrances with BWP prices |
| `tests/crm-domain.test.ts` | 8 tests: finance workflow (3) + mergeData sync (5) |
| `app.config.ts` | Expo config — `EXPO_PUBLIC_BASE_URL` handling (see traps) |

**Deleted files** (no longer used): `lib/google-drive.ts`, `constants/google.ts`.

## Deploy

**Pre-requisite (once):** Run `supabase/tony_crm.sql` in the nakotech Supabase project's SQL Editor to create the table + RLS policy.

**GitHub Pages (primary after Supabase swap):**
```bash
cd C:\Users\PrathapAsus\work\tony-fragrances-crm
EXPO_PUBLIC_SUPABASE_URL="https://xvqnuycevvirmehzbtyj.supabase.co" \
EXPO_PUBLIC_SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh2cW51eWNldnZpcm1laHpidHlqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc5ODE3MDIsImV4cCI6MjA5MzU1NzcwMn0.bXjePI2z21p17GWHbBjKypsMkhjdbkBUIveCodnqFC0" \
bash scripts/deploy-pages.sh
```

**Netlify:** Set `EXPO_PUBLIC_SUPABASE_URL` and `EXPO_PUBLIC_SUPABASE_ANON_KEY` in Netlify → Site settings → Environment variables, then trigger a deploy from master.

**Tests:**
```bash
npx vitest run
```
All 8 must pass before shipping.

## Setting Tony up

1. Pick a passcode for Tony (e.g. a word + 4 digits). Give it to him.
2. He types it once on his phone and once on his laptop. Both now share the same data.
3. **First device creates the workspace** — type it on the device that already holds his real data first, so it uploads.

## Traps (hard-won — do not repeat)

1. **MSYS path conversion:** On Windows Git Bash, a leading `/` in env vars gets mangled to a Windows path. Pass `EXPO_PUBLIC_BASE_URL` WITHOUT a leading slash in the env; `app.config.ts` adds it back.
2. **React Compiler + dark theme:** `use-color-scheme.web.ts` must read from ThemeProvider context, not a per-component hydration flag — otherwise dark theme breaks.
3. **NativeWind cache:** First web export can fail on `.cache/web.css` SHA mismatch — retry clears it.
4. **dist-\* in .gitignore:** Build output directories (`dist-pages`, `dist-root`, `dist-test`) should NOT be committed.
5. **Google Drive token expiry was the REAL sync killer** — not just the merge logic. A token expired silently after ~1 hour, making the app look normal while sync was dead. That's why the architecture was replaced, not just patched.

## Google OAuth (RETIRED — kept for reference)

The old Google Cloud project "Tony Fragrances CRM" (id `tony-fragrances-crm`, owned by `prathap.bb@gmail.com`) is still active but the app no longer uses it. Web client ID was `196234648247-sbmaderc4hua2klnslj6cmvh4dmpicib.apps.googleusercontent.com`. Can be disabled/deleted when convenient.

## Standing rules

- This is Tony's app for his business. Keep it simple — he is a small retailer, not an enterprise.
- **No Alpha Direct branding, no Navy/Orange** — the design is black and gold (Tony's brand).
- Email Tony as Prathap in personal capacity. Friendly, plain English, short.
- The Supabase project is the **nakotech** one (shared with Nako Pula) — don't create a separate project.
- Never fabricate "synced" / "working" claims — verify on the live site that data actually round-trips.
