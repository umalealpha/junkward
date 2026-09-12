# Rebuilding Prathap's brain on a bare machine

Use this **only** when the skills, standing orders and memory are genuinely missing —
a new computer, a wiped profile, or a Claude install that comes up knowing nothing.

**On his current Windows PC nothing needs installing.** The skills, standing orders,
memory and notebook live on the machine, not in the Claude account, so they already work
on the new `cfo@alphadirect.co.bw` licence. Do not "restore" over a working setup.

---

## The source pack

**`CFO ZIP.zip`** — on his Desktop
(`C:\Users\PrathapAsus\OneDrive - Alpha Direct Insurance\Desktop\CFO ZIP.zip`).

It holds five things:

| Inside the zip | What it is |
|---|---|
| `brain/CLAUDE.md` | His standing orders — all 41, in his own words. The single most important file. |
| `brain/memory/` | ~460 memory notes plus `MEMORY.md`, the index that loads every session. |
| `skills/` | One folder per skill, each with its `SKILL.md` (66 skills). |
| `BRIEF-last-10-days.md` | Day-by-day summary of 29 Aug – 8 Sep 2026 — what he asked, what was decided, what is open. |
| `full-chat-last-10-days.md` | Every word typed over those 10 days (~10 MB). Never paste this into a chat — add it to a Project's knowledge if full-detail search is wanted. |

**Deliberately left out:** every password and key (correctly — never put a secret in an
uploaded file), and the heavy code libraries bundled inside `prat-skill` (~395 MB).

---

## Restoring it (Windows)

Unpack, then copy the three pieces into place. `$HOME` is his user folder.

```bash
# 1. standing orders
cp brain/CLAUDE.md "$HOME/.claude/CLAUDE.md"

# 2. memory (index + notes)
mkdir -p "$HOME/.claude/projects/<project-key>/memory"
cp -r brain/memory/. "$HOME/.claude/projects/<project-key>/memory/"

# 3. skills
mkdir -p "$HOME/.claude/skills"
cp -r skills/. "$HOME/.claude/skills/"
```

`<project-key>` is the working directory with slashes turned into dashes — on this PC it is
`C--Users-PrathapAsus-OneDrive---Alpha-Direct-Insurance-Gods-Eye`. If the new machine uses a
different working folder, the key changes with it.

**Restart Claude Code once** so the skills register.

---

## What the pack does NOT bring back — set these up separately

| Missing piece | How to get it working |
|---|---|
| **The notebook key** | The read-only key at `~/.claude/omni-notebook.key` is a secret and is not in the pack. Mint a notebook-scoped key in Omni's API-key console and save the plaintext to that file (chmod 600, never printed, never committed). Setup detail is in `CLAUDE.md` RULE #0. Without it, `read-notebook.sh` returns 403. |
| **The alpha-finance repo** | Clone fresh from `github.com/alphadirectinsurance/alpha-finance`. Never work in the OneDrive copy — it is a stale snapshot and OneDrive syncing a repo's internals risks corrupting it. |
| **`MACHINE-TALK.md`** | Comes with the repo clone. It is append-only, one line per session, newest at the bottom — never rewrite, reorder or trim it. |
| **The prat-skill code libraries** | The reference repos (~395 MB) were left out. Re-clone only the ones a job actually needs; the inventory is in `prat-skill` §6. |
| **Machine-local tools** | The screenshot/QC toolkits, the ETA tracker, the cost gateway and ARIA are all machine-local runtimes. Rebuild per `prat-skill` §14–17 on the machine that needs them. |

---

## After restoring — prove it took

Do not report the restore done on "the files copied". Check it:

1. Start a fresh chat and type **`/CFO`** — the board must come up with the right frozen
   numbers (FY25 GWP 125,148,692 BWP).
2. Type **`/note`** — the notebook must actually fetch. A 403 means the key step above was skipped.
3. Type **`/pending`** — confirms the instruction tracker is loaded.

Any of those three failing means the restore is not finished. Say which one failed and why.
