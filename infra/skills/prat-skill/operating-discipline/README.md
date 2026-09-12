# operating-discipline/ — portable source for the §12 add-ons

Vendored 2026-06-16. This folder is the **portable, self-contained source** for the two
operating-discipline add-ons documented in `SKILL.md` §12. It is NOT the active copy —
it exists so the prat-skill bundle is self-contained and can be re-installed or carried to
the Mac Mini without re-cloning from the internet.

## What's here

| Path | What it is | Where the ACTIVE copy lives |
|---|---|---|
| `karpathy-CLAUDE.md` | Verbatim ruleset from `forrestchang/andrej-karpathy-skills` (MIT). Single file, zero executable code. | Pasted into `%USERPROFILE%\.claude\CLAUDE.md` (machine-local global). That's what's actually enforced. |
| `superpowers-skills/` | The 14 skill folders from `obra/superpowers` v5.1.0 (MIT). | Copied to `%USERPROFILE%\.claude\skills\<name>\` — that top-level location is what registers them as invocable skills. |

## Re-install / new machine (e.g. the Mac, or a fresh Windows box)

1. **Karpathy** — append the contents of `karpathy-CLAUDE.md` into that machine's
   `~/.claude/CLAUDE.md` (under a clear heading). Active immediately, every project.
2. **Superpowers** — copy each folder inside `superpowers-skills/` into
   `~/.claude/skills/` (top level — NOT nested, or they won't register). Restart Claude Code.
   - On a machine running the Claude Code **CLI** (not the app) you can instead use the
     real plugin: `/plugin marketplace add obra/superpowers-marketplace` then
     `/plugin install superpowers@superpowers-marketplace`. The app has no `/plugin`.

## Drift warning

These are pinned snapshots. If you ever edit the ACTIVE copies (global CLAUDE.md /
`~/.claude/skills/*`), this vendored source does NOT auto-update — re-copy if you want
the bundle to stay current. Upstream: github.com/forrestchang/andrej-karpathy-skills,
github.com/obra/superpowers.
