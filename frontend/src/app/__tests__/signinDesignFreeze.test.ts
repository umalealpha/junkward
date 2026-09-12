/**
 * The sign-in design freeze.
 *
 * The CFO supplied the finished sign-in page on 2026-09-08 ("Omni Amendments —
 * FINAL pack", Omni Sign-in.html) and confirmed the same day: "you have the
 * design sent by Claude Design, use the same thing". Amendment 4 of that pack
 * says the page is then LOCKED — no restyling, no recolouring, no
 * "harmonising" to the house brand.
 *
 * A freeze that lives only in a comment is not a freeze, so it is asserted
 * here. Two things are guarded:
 *   1. the design itself — the script wordmark, the type metrics, the legacy
 *      navy, the pinned logo; and
 *   2. the two LOCKOUT-RECOVERY links, which the design does not show but which
 *      two earlier CFO directives put on this page on purpose (2026-07-09 and
 *      the catch-22 fix of 2026-08-07). Applying a picture must never quietly
 *      delete the only way a locked-out person can ask for help.
 *
 * Read as source rather than rendered: the sign-in page pulls in MSAL, which
 * cannot be constructed in a test process.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

const root = join(__dirname, '..')
const shell = readFileSync(join(root, '_components/AccessPortalShell.tsx'), 'utf8')
/** The same file with comments stripped. The negative colour assertions below
 *  have to read CODE only — a comment that names the forbidden brand navy in
 *  order to forbid it would otherwise fail the test that enforces it. */
const shellCode = shell.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '')
const login = readFileSync(join(root, 'login/page.tsx'), 'utf8')
const layout = readFileSync(join(root, 'layout.tsx'), 'utf8')

describe('Omni sign-in — the CFO’s design, frozen', () => {
  it('carries the script wordmark from the design', () => {
    expect(shell).toContain('oap-signin-wordmark')
    expect(shell).toContain('font-size: 120px')
    expect(shell).toContain('line-height: 0.82')
    expect(shell).toContain('font-weight: 600')
  })

  it('does not reuse the navy panel’s wordmark class, which would restyle it', () => {
    // .oap-wordmark is already the small white "Omni" beside the mono logo. The
    // sign-in wordmark had to take its own class, or that label silently became
    // 120px navy script. Both rules must still be here, side by side.
    expect(shellCode).toContain('.oap-wordmark {')
    expect(shellCode).toContain('.oap-signin-wordmark {')
    expect(shellCode).toContain('font-size: 17px')      // the navy panel's label
    expect(shellCode).toContain('font-size: 120px')     // the sign-in wordmark
  })

  it('self-hosts Caveat through next/font, so there is no runtime call to Google', () => {
    expect(layout).toContain("import { Caveat } from 'next/font/google'")
    expect(layout).toContain("variable: '--font-caveat'")
    expect(shell).toContain('var(--font-caveat)')
  })

  it('pins the logo top-right of the white panel, as the design does', () => {
    expect(shell).toContain('top: 28px')
    expect(shell).toContain('right: 32px')
    expect(shell).toContain('height: 42px')
  })

  it('keeps the design’s type metrics on the heading and the line under it', () => {
    expect(shell).toContain('line-height: 1.25')   // h1
    expect(shell).toContain('line-height: 1.6')    // sub
    expect(shell).toContain('margin: 0 0 30px')    // sub
  })

  it('keeps the legacy navy and does NOT harmonise to the house brand', () => {
    expect(shellCode).toContain("'#0D1B2A'")
    expect(shellCode).not.toContain('#1D3270')
    expect(shellCode).not.toContain('#F47C20')
  })

  it('uses the design’s own words under the heading', () => {
    expect(login).toContain('One source of truth for Alpha Direct')
    expect(login).toContain('Microsoft is here too')
  })

  it('STILL offers both ways out for someone who is locked out', () => {
    // Neither of these is in the design. Both were put here by earlier CFO
    // directives and must survive any restyle.
    expect(login).toContain('Microsoft sign-in stuck?')
    expect(login).toContain('Still cannot get in?')
    expect(login).toContain('NO_LOGIN_REPORT_URL')
  })
})
