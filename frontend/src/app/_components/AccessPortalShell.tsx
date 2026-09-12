'use client'

/**
 * AccessPortalShell — the CFO's "Omni Access Portal" sign-in shell.
 *
 * A presentational two-panel layout ONLY. It carries no auth logic: the three
 * sign-in surfaces (/staff-login, / and /login) each keep their own real auth
 * calls and drop their step content in as {children}.
 *
 *   LEFT  (white)  — logo + whatever the page passes as children (the form).
 *   RIGHT (navy)   — what Omni does: a constellation of the real modules and
 *                    the flows the AI runs through them, three capabilities in
 *                    plain words, and the security promise as a trust strip.
 *
 * Redesigned 2026-09-07 (CFO brief: "professional, enterprise level, a company
 * that has AI capability"). The left panel and every exported class name are
 * unchanged so the three pages compile and behave exactly as before.
 *
 * Design: navy #0D1B2A, orange #F07F00. Book Antiqua serif headings, system
 * sans body. Fixed brand surface — no dark-mode inversion. Panels stack on
 * mobile with the navy panel below the form.
 *
 * Motion: ONE orchestrated moment on load — the constellation lights up along
 * the two real flows (bank feed → payments → ledger → reporting; inbox → CEO
 * brief → tasks), then rests. Reduced-motion users get the final state.
 *
 * No CDN fonts, no external assets — the two logos ship in /public/brand.
 */
import type { ReactNode } from 'react'

const NAVY = '#0D1B2A'
const ORANGE = '#F07F00'
export const OAP_SERIF =
  "'Book Antiqua','Palatino Linotype',Palatino,Georgia,serif"
export const OAP_SANS =
  "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
// The sign-in wordmark's face, fixed by the CFO's supplied design (2026-09-08).
// Loaded through next/font in the root layout, so it is SELF-HOSTED at build
// time — the "no Google Fonts fetch" rule is about a runtime call to Google,
// and there is none. The stack still degrades to a handwriting face if the
// variable is ever missing.
export const OAP_SCRIPT =
  "var(--font-caveat),'Caveat','Segoe Script','Bradley Hand',cursive"

export type SecurityPoint = { title: string; body: string }

// Security promise. Rendered as the trust strip at the foot of the right
// panel — titles visible, bodies available to screen readers and on hover.
const DEFAULT_POINTS: SecurityPoint[] = [
  {
    title: 'Named accounts only',
    body: 'Every sign-in is tied to a real Alpha Direct staff account. There are no shared or anonymous logins.',
  },
  {
    title: 'Two steps, every time',
    body: 'Your password is only the first step. A one-time code sent to your work inbox confirms it is really you.',
  },
  {
    title: 'Sign-ins are logged',
    body: 'Sign-ins are recorded and reviewed. Never sign in on a shared or public machine, and never share your credentials.',
  },
]

// What Omni's AI actually does today. Each line is a live capability, not a
// promise: FNB statement auto-reconciliation, the CEO Monitor morning brief,
// and the overnight Watchdog that feeds the Exceptions board.
const CAPABILITIES: { title: string; body: string }[] = [
  {
    title: 'Reads the bank statement every morning',
    body: 'Matches what FNB says has cleared against every open payment and closes the ones that are paid.',
  },
  {
    title: 'Writes the morning brief',
    body: 'Reads the inbox overnight, drafts the 7am brief and turns loose ends into tasks with an owner.',
  },
  {
    title: 'Checks every module while you sleep',
    body: 'Runs the overnight checks across finance, people and claims and lists what needs a human by 8:30.',
  },
]

// Shared control styling. Exported as className constants so the three pages
// render identical inputs/buttons; the CSS itself is injected once by the shell.
export const OAP = {
  field: 'oap-field',
  label: 'oap-label',
  primaryBtn: 'oap-btn oap-btn-primary',
  msBtn: 'oap-btn oap-btn-ms',
  linkBtn: 'oap-linkbtn',
  notice: 'oap-notice',
  error: 'oap-error',
  pwWrap: 'oap-pw-wrap',
  pwToggle: 'oap-pw-toggle',
  orModule: 'oap-or',
} as const

// Inline "four squares" Microsoft mark — no external image.
export function MicrosoftMark() {
  return (
    <span className="oap-ms-mark" aria-hidden="true">
      <i style={{ background: '#F25022' }} />
      <i style={{ background: '#7FBA00' }} />
      <i style={{ background: '#00A4EF' }} />
      <i style={{ background: '#FFB900' }} />
    </span>
  )
}

/* ── Constellation ─────────────────────────────────────────────────────────
 * Omni's real modules as nodes; the edges are the two flows the AI runs
 * through them each day. Order (`t`) is the lighting sequence, so the
 * animation is the data flow itself, not decoration. Coordinates are in a
 * 440×190 box; labels sit where they will not collide at that size.
 */
type Node = { id: string; label: string; x: number; y: number; t: number; anchor?: 'start' | 'end' }
const NODES: Node[] = [
  { id: 'bank', label: 'Bank feed', x: 34, y: 144, t: 0 },
  { id: 'pay', label: 'Payments', x: 126, y: 110, t: 1 },
  { id: 'ledger', label: 'Ledger', x: 226, y: 137, t: 2 },
  { id: 'report', label: 'Reporting', x: 340, y: 158, t: 3 },
  { id: 'inbox', label: 'Inbox', x: 58, y: 42, t: 4 },
  { id: 'brief', label: 'CEO brief', x: 176, y: 26, t: 5 },
  { id: 'tasks', label: 'Tasks', x: 296, y: 49, t: 6 },
  { id: 'claims', label: 'Claims', x: 262, y: 89, t: 7 },
  { id: 'payroll', label: 'Payroll', x: 124, y: 170, t: 8 },
  { id: 'people', label: 'People', x: 388, y: 94, t: 9, anchor: 'end' },
]
const EDGES: [string, string][] = [
  ['bank', 'pay'],
  ['pay', 'ledger'],
  ['ledger', 'report'],
  ['inbox', 'brief'],
  ['brief', 'tasks'],
  ['claims', 'ledger'],
  ['payroll', 'ledger'],
  ['people', 'report'],
  ['tasks', 'claims'],
]

function Constellation() {
  const byId = Object.fromEntries(NODES.map((n) => [n.id, n]))
  return (
    <svg
      className="oap-sky"
      viewBox="0 0 440 190"
      role="img"
      aria-label="Omni's modules and the flows its AI runs through them: bank feed to payments to ledger to reporting, and inbox to CEO brief to tasks."
    >
      {EDGES.map(([a, b]) => {
        const A = byId[a]
        const B = byId[b]
        const t = Math.max(A.t, B.t)
        return (
          <line
            key={`${a}-${b}`}
            className="oap-edge"
            x1={A.x}
            y1={A.y}
            x2={B.x}
            y2={B.y}
            style={{ animationDelay: `${0.25 + t * 0.22}s` }}
          />
        )
      })}
      {NODES.map((n) => (
        <g key={n.id} className="oap-node" style={{ animationDelay: `${0.2 + n.t * 0.22}s` }}>
          <circle className="oap-node-halo" cx={n.x} cy={n.y} r="9" />
          <circle className="oap-node-dot" cx={n.x} cy={n.y} r="3.2" />
          <text
            className="oap-node-label"
            x={n.anchor === 'end' ? n.x - 12 : n.x + 12}
            y={n.y + 4}
            textAnchor={n.anchor ?? 'start'}
          >
            {n.label}
          </text>
        </g>
      ))}
    </svg>
  )
}

export default function AccessPortalShell({
  children,
  securityPoints = DEFAULT_POINTS,
}: {
  children: ReactNode
  securityPoints?: SecurityPoint[]
}) {
  return (
    <main className="oap-root">
      {/* LEFT — white form panel */}
      <section className="oap-left">
        {/* Plain <img>: these are static brand PNGs in /public; Next/Image
            buys nothing here and adds optimizer indirection. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/brand/logo-full-color.png"
          alt="Alpha Direct Insurance"
          className="oap-logo"
        />
        <div className="oap-left-inner">
          {/* The wordmark from the CFO's supplied design (2026-09-08). FROZEN —
              see the note on .oap-signin-wordmark below. */}
          <div className="oap-brand">
            <span className="oap-signin-wordmark">Omni</span>
          </div>
          {children}
        </div>
      </section>

      {/* RIGHT — navy story panel */}
      <aside className="oap-right" aria-label="About Omni">
        <div className="oap-right-inner">
          <div className="oap-right-top">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/brand/logo-monotone-white.png"
              alt="Alpha Direct"
              className="oap-logo-mono"
            />
            <span className="oap-wordmark">Omni</span>
          </div>

          <Constellation />

          <h2 className="oap-right-title">
            One system that reads, checks and remembers.
          </h2>
          <p className="oap-right-lede">
            Omni runs Alpha Direct&rsquo;s finance, people and claims records.
            Its AI does the reading, so the team does the deciding.
          </p>

          <ul className="oap-caps">
            {CAPABILITIES.map((c) => (
              <li key={c.title} className="oap-cap">
                <div className="oap-cap-title">{c.title}</div>
                <div className="oap-cap-body">{c.body}</div>
              </li>
            ))}
          </ul>

          <div className="oap-right-foot">
            <ul className="oap-trust-strip" aria-label="How access is protected">
              {securityPoints.map((p) => (
                <li key={p.title} className="oap-trust-item" title={p.body}>
                  <span className="oap-trust-mark" aria-hidden="true" />
                  {p.title}
                  <span className="oap-sr">. {p.body}</span>
                </li>
              ))}
            </ul>
            <div className="oap-place">Alpha Direct Insurance, Gaborone, Botswana</div>
          </div>
        </div>
      </aside>

      <style>{CSS}</style>
    </main>
  )
}

const CSS = `
.oap-root {
  min-height: 100dvh;
  display: flex;
  background: #ffffff;
  color: ${NAVY};
  font-family: ${OAP_SANS};
}
/* LEFT panel */
/* ⛔ FROZEN DESIGN — the CFO supplied the finished sign-in page on 2026-09-08
 * ("Omni Amendments — FINAL pack", Omni Sign-in.html) and confirmed on the day:
 * "you have the design sent by Claude Design, use the same thing". Every number
 * from here to .oap-sub is the design's own. Do not restyle, and do not
 * "harmonise" the legacy navy #0D1B2A to house brand #1D3270 — the design uses
 * the legacy navy on purpose. */
.oap-left {
  position: relative;               /* the logo pins to this panel */
  flex: 0 0 46%;
  min-width: 340px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: #ffffff;
  overflow-y: auto;
}
.oap-left-inner { width: 100%; max-width: 380px; }
.oap-brand { margin-bottom: 34px; }
.oap-logo {
  position: absolute;
  top: 28px;
  right: 32px;
  height: 42px;
  width: auto;
  display: block;
}
/* NOT .oap-wordmark — that class is already the small white "Omni" label in the
 * navy panel, and reusing it here silently restyled it to 120px script. */
.oap-signin-wordmark {
  display: block;
  font-family: ${OAP_SCRIPT};
  font-weight: 600;
  font-size: 120px;
  line-height: 0.82;
  color: ${NAVY};
  width: 310px;
  height: 130px;
  text-align: center;
}

.oap-h1 {
  font-family: ${OAP_SERIF};
  font-size: 27px;
  line-height: 1.25;
  font-weight: 700;
  margin: 0 0 10px;
  color: ${NAVY};
}
.oap-sub {
  font-size: 13.5px;
  line-height: 1.6;
  color: #55657a;
  margin: 0 0 30px;
  text-wrap: pretty;
}

/* The wordmark is the one place the panel can overflow a short phone screen. */
@media (max-width: 560px) {
  .oap-signin-wordmark { font-size: 84px; height: 92px; width: 100%; }
  .oap-brand { margin-bottom: 22px; }
}

/* WHY THIS EXISTS, and why it needs !important.
 * globals.css carries a blanket theme override —
 *   html.theme-professional *:not(.font-mono-nums):not([class*="mono"]):not(code)
 *   :not(pre):not(kbd) { font-family: var(--font-sans) !important; }
 * — put there to flatten components that hardcode a serif. It also flattened
 * this wordmark, so the handwritten "Omni" the CFO signed off rendered as plain
 * Inter. Caveat was loading correctly the whole time; the cascade was eating it.
 * That blanket rule scores (0,3,4), so a plain .oap-signin-wordmark cannot win
 * even with !important — specificity decides between two !important rules. Four
 * classes beat its three, hence the long selector. Do not shorten it. */
.oap-root .oap-left .oap-brand .oap-signin-wordmark {
  font-family: ${OAP_SCRIPT} !important;
}

.oap-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: #35485c;
  margin-bottom: 6px;
}
.oap-field {
  width: 100%;
  box-sizing: border-box;
  padding: 11px 13px;
  border: 1px solid #d6dee7;
  border-radius: 9px;
  background: #fbfcfe;
  color: ${NAVY};
  font-size: 14px;
  font-family: ${OAP_SANS};
  outline: none;
  transition: border-color .15s ease, box-shadow .15s ease, background .15s ease;
}
.oap-field::placeholder { color: #9aa8b8; }
.oap-field:focus {
  border-color: ${ORANGE};
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(240,127,0,0.15);
}

/* Password field with a show/hide toggle */
.oap-pw-wrap { position: relative; }
.oap-pw-wrap .oap-field { padding-right: 62px; }
.oap-pw-toggle {
  position: absolute;
  top: 50%;
  right: 8px;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  color: #55657a;
  font-size: 12px;
  font-weight: 600;
  font-family: ${OAP_SANS};
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 6px;
}
.oap-pw-toggle:hover { color: ${NAVY}; background: #eef2f6; }

/* "Trust this device" */
.oap-trust {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-top: 14px;
  font-size: 13px;
  color: #35485c;
  cursor: pointer;
  user-select: none;
}
.oap-trust input {
  width: 16px; height: 16px;
  accent-color: ${ORANGE};
  cursor: pointer;
}

/* Buttons */
.oap-btn {
  width: 100%;
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 12px 14px;
  border-radius: 9px;
  font-size: 14px;
  font-weight: 600;
  font-family: ${OAP_SANS};
  cursor: pointer;
  text-decoration: none;
  transition: background .15s ease, border-color .15s ease, transform .05s ease, opacity .15s ease;
}
.oap-btn:active { transform: translateY(1px); }
.oap-btn-primary {
  border: 1px solid ${NAVY};
  background: ${NAVY};
  color: #ffffff;
}
.oap-btn-primary:hover { background: #16293c; }
.oap-btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
/* The primary CTA is an <a> on the root landing. globals.css paints links per
   theme (html.theme-professional a { color }) at higher specificity than
   .oap-btn-primary, which turned the button text blue. Pin it to white. */
.oap-root a.oap-btn-primary,
.oap-root a.oap-btn-primary:hover,
.oap-root a.oap-btn-primary:visited { color: #ffffff; }
.oap-btn-ms {
  border: 1px solid #d6dee7;
  background: #ffffff;
  color: ${NAVY};
}
.oap-btn-ms:hover { background: #f4f7fa; border-color: #c4cfda; }
.oap-btn-ms:disabled { opacity: 0.6; cursor: not-allowed; }

.oap-ms-mark {
  width: 15px; height: 15px; flex: 0 0 15px;
  display: grid; grid-template-columns: 1fr 1fr; gap: 2px;
}
.oap-ms-mark i { display: block; border-radius: 1px; }

/* "or" separator */
.oap-or {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 16px 0;
  color: #8494a5;
  font-size: 12px;
}
.oap-or::before, .oap-or::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #e4eaf0;
}

/* Text link button */
.oap-linkbtn {
  display: inline-block;
  border: none;
  background: none;
  padding: 0;
  color: #55657a;
  font-size: 12.5px;
  font-family: ${OAP_SANS};
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.oap-linkbtn:hover { color: ${ORANGE}; }

/* Notices */
.oap-notice {
  margin-top: 16px;
  padding: 10px 12px;
  border-radius: 9px;
  font-size: 12.5px;
  line-height: 1.45;
  background: rgba(240,127,0,0.08);
  border: 1px solid rgba(240,127,0,0.35);
  color: #8a4b00;
}
.oap-error {
  margin-top: 16px;
  padding: 10px 12px;
  border-radius: 9px;
  font-size: 13px;
  line-height: 1.45;
  background: #fdecee;
  border: 1px solid #f2b8bd;
  color: #b0121f;
}

/* RIGHT panel */
.oap-right {
  flex: 1 1 54%;
  background:
    radial-gradient(90% 70% at 85% 10%, #16304a 0%, rgba(22,48,74,0) 60%),
    linear-gradient(180deg, #102238 0%, ${NAVY} 100%);
  color: #eef3f8;
  display: flex;
  align-items: center;
  padding: 36px 52px;
}
.oap-right-inner { width: 100%; max-width: 520px; margin: 0 auto; }
.oap-right-top {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 14px;
}
.oap-logo-mono { height: 28px; width: auto; display: block; opacity: 0.95; }
.oap-wordmark {
  font-family: ${OAP_SERIF};
  font-size: 17px;
  font-weight: 700;
  color: #ffffff;
  border-left: 1px solid rgba(255,255,255,0.22);
  padding-left: 14px;
  line-height: 1;
}

/* Constellation */
.oap-sky {
  display: block;
  width: 100%;
  height: auto;
  margin: 0 0 8px;
  overflow: visible;
}
.oap-edge {
  stroke: rgba(255,255,255,0.28);
  stroke-width: 1;
  stroke-dasharray: 400;
  stroke-dashoffset: 400;
  animation: oap-draw 0.7s ease-out forwards;
}
.oap-node { opacity: 0; animation: oap-appear 0.45s ease-out forwards; }
.oap-node-dot { fill: ${ORANGE}; }
.oap-node-halo { fill: rgba(240,127,0,0.16); }
.oap-node-label {
  font-family: ${OAP_SANS};
  font-size: 10.5px;
  fill: #c3d0de;
  letter-spacing: 0.01em;
}
@keyframes oap-draw { to { stroke-dashoffset: 0; } }
@keyframes oap-appear { from { opacity: 0; transform: translateY(2px); } to { opacity: 1; transform: none; } }

.oap-right-title {
  font-family: ${OAP_SERIF};
  font-weight: 700;
  font-size: 31px;
  line-height: 1.14;
  letter-spacing: -0.005em;
  margin: 0 0 10px;
  color: #ffffff;
  max-width: 15ch;
}
.oap-right-lede {
  font-size: 14px;
  line-height: 1.55;
  color: #b7c6d6;
  margin: 0 0 18px;
  max-width: 44ch;
}

.oap-caps { list-style: none; margin: 0; padding: 0; border-top: 1px solid rgba(255,255,255,0.1); }
.oap-cap {
  padding: 10px 0 10px 18px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  position: relative;
}
.oap-cap::before {
  content: '';
  position: absolute;
  left: 0;
  top: 16px;
  width: 8px;
  height: 2px;
  background: ${ORANGE};
}
.oap-cap-title {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 2px;
}
.oap-cap-body {
  font-size: 12.8px;
  line-height: 1.5;
  color: #a9bbcf;
  max-width: 52ch;
}

.oap-right-foot { margin-top: 18px; }
.oap-trust-strip {
  list-style: none;
  margin: 0 0 10px;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 18px;
}
.oap-trust-item {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: #c3d0de;
  cursor: help;
}
.oap-trust-mark {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: ${ORANGE};
  flex: 0 0 6px;
}
.oap-sr {
  position: absolute;
  width: 1px; height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
.oap-place {
  font-size: 11px;
  letter-spacing: 0.02em;
  color: #6d8199;
}

/* Short laptop screens (1366×768 and the like): tighten so the trust strip
   stays on screen without scrolling. Same content, smaller rhythm. */
@media (min-width: 861px) and (max-height: 820px) {
  .oap-right { padding: 26px 44px; }
  .oap-right-top { margin-bottom: 8px; }
  .oap-sky { max-width: 400px; margin-bottom: 4px; }
  .oap-right-title { font-size: 27px; margin-bottom: 8px; }
  .oap-right-lede { font-size: 13px; margin-bottom: 12px; }
  .oap-cap { padding: 8px 0 8px 18px; }
  .oap-cap::before { top: 14px; }
  .oap-cap-title { font-size: 13.5px; }
  .oap-cap-body { font-size: 12.3px; }
  .oap-right-foot { margin-top: 12px; }
}

/* Stack on mobile: form first, navy panel below */
@media (max-width: 860px) {
  .oap-root { flex-direction: column; }
  .oap-left { flex: none; padding: 36px 22px 30px; }
  .oap-right { flex: none; padding: 34px 22px 40px; }
  .oap-right-inner { max-width: 440px; }
  .oap-right-title { font-size: 26px; }
  .oap-sky { margin-bottom: 4px; }
}

@media (prefers-reduced-motion: reduce) {
  .oap-btn, .oap-field, .oap-pw-toggle, .oap-linkbtn { transition: none; }
  .oap-edge { animation: none; stroke-dashoffset: 0; }
  .oap-node { animation: none; opacity: 1; }
}
`
