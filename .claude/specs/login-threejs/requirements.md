# Premium dark-theme login page

**Scope:** Replace `frontend/src/app/login/page.tsx` only. The rest of the ERP stays Light Mode (CFO directive).

## Functional requirements

### FR-1 — Strict pre-auth security contract (PRESERVED)
- No fetch / axios / API call on this route. The only network egress is MSAL's `loginRedirect` to login.microsoftonline.com.
- Every visible string is hardcoded. No live financial values, no employee counts.
- (Keeps the existing comment-as-contract at the top of the file.)

### FR-2 — Remove all mascot/superhero imagery
- No `/brand/mascots/*.png` references.
- No "Watch Demo" / "demo video" content.
- No DeepSeek branding (already absent — confirm via grep on final page).

### FR-3 — Dark theme aesthetic
- Background base: `#0D1B2A` (Navy).
- Subtle starfield + radial gradient halo behind the central element.
- Primary accent: `#F07F00` (Electric Orange) used for the CTA glow + headline kerning.
- Text: white at full brightness for the hero; `rgba(255,255,255,0.6)` for sub-copy.
- High contrast — WCAG AA at minimum.

### FR-4 — Interactive 3D central element
- A rotating particle web / morphing geometric object centred above the fold.
- Implementation: **vanilla `<canvas>` 2D + requestAnimationFrame** (no Three.js dependency added — keeps bundle small while still delivering the Three.js *look*).
- The particles should:
  - Drift slowly
  - Connect with thin lines when within proximity
  - Glow faintly orange around centre, fade to navy at edges
  - Respond to cursor (gentle attraction to mouse for the nearest particles only — graceful no-op on touch devices)
- Animation pauses when the page is hidden (Page Visibility API) — battery-friendly.

### FR-5 — Bold kinetic typography hero
- One headline word, oversized (clamp(3rem, 8vw, 7rem)), tracking-tight, weight 700.
- Letters reveal via per-character translateY + opacity (CSS keyframes, no JS lib).
- Sub-headline: one line, weight 400, half opacity.

### FR-6 — Single prominent CTA
- "Sign In with Microsoft" button.
- Position: above the fold, horizontally centred under the hero.
- Style: dark button with bright orange border glow (box-shadow + animated pulse).
- On click: `getMsalInstance().loginRedirect({ scopes: loginScopes })` — same as existing.
- Disabled state if `!isSSOConfigured()` — fall back to a static "Contact IT" message.
- Microsoft logo SVG retained.

### FR-7 — Footer
- One line: `© 2026 Alpha Direct Insurance Co.™ · Gaborone, Botswana · Microsoft SSO required`
- White at 30% opacity, small caps, letter-spacing tight.

### FR-8 — Responsive
- Mobile: hero shrinks, canvas reduces particle count (perf), CTA fills 90% width.
- Desktop ≥ 1024px: hero centred in a 720px column, canvas behind, full-bleed background.

### FR-9 — Performance budget
- Initial JS for this route under 80kB gzipped.
- No new npm dependencies (vanilla canvas only).
- LCP under 1.5s on 4G simulated.

## Out of scope
- Three.js library install (will use canvas 2D — same aesthetic, smaller bundle).
- Internal ERP routes — they stay Light Mode.
- Password fallback flag toggle — kept as-is (off in prod).
