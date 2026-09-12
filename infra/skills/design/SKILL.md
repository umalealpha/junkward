---
name: design
description: Prathap's /design command — build or restyle any screen (Omni page, dashboard, module UI, artifact, landing page, deck slide) using Anthropic's frontend-design plugin skill PLUS his house rules. Auto-load whenever Prathap types /design, says "design this", "front end design", "make it look good", "restyle", "polish the UI", or asks for a page / dashboard / screen to be built or made to look right. Alpha Direct brand by default; personal projects (Nako, GRC, Tony, ACCA, KgareTrack) keep their own skill's brand.
---

# /design — front-end design, Prathap's way

`/design` = the Anthropic **frontend-design** plugin skill, wrapped in Prathap's standing rules.
It does not duplicate that skill — it calls it.

## Run order (every time)

1. **Design-instruction review gate** (prat-skill §0b, CFO directive 2026-07-17) — Alpha Direct work only.
   Analyse his brief, list 🟢 optional improvements, ask plainly "Can I add these too?", wait for yes/no.
   Skip the gate for personal projects and when he says "just build it".
2. **Invoke the plugin skill** via the Skill tool: `frontend-design:frontend-design`.
   Follow its two-pass process: token plan (colour / type / layout / principles) → review against the brief → build.
3. **Brand constraints override the plugin's free choices:**
   - Alpha Direct / Omni: Navy `#1D3270`, Orange `#F47C20`, Montserrat (see [[r-org-skill]]). Finance documents: Book Antiqua, Dark Navy `#0D1B2A`, Orange `#F4A623`.
   - Omni keeps its existing theme — restyle within it, never a new look per page ([[p-omni-pro-theme]]).
   - Personal projects: load that project's skill (`nako`, `grc`, `Tony`, `acca`, `KgareTrack`) and use its brand instead.
4. **Motion + spacing standing order:** Emil Kowalski-style motion (answers the user's action, one orchestrated moment max), mathematical spacing scale, no generic-framework look.
5. **Prove it** — render it (Browser pane / qc.sh + QC account for Omni), screenshot, look at it, fix, then show him the screenshot. BUILD SUCCEEDED is not evidence.

## Not this skill

- A hand-tweakable mockup canvas (Claude Design artboards) is a different tool — say "design canvas" for that.
- Charts and dashboards' data marks: also load `dataviz` before drawing any chart.
