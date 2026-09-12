---
name: ruflo
description: "Ruflo AI agent orchestration setup, MCP wiring, per-project init, and kill switch on Prathap's Windows PC. Activate whenever the user mentions Ruflo, ruflo init, ruflo swarm, agent orchestration, hive-mind, or wants to scaffold an agent swarm into a project. Includes the install verification flow, the wizard answers Prathap chose, the curated plugin allow-list / skip-list, and the cost budget defaults."
license: MIT
metadata:
  version: 1.0.0
  author: Prathap Ganesharajah
  category: developer-tooling
  updated: 2026-05-10
---

# Ruflo — Prathap's working notes

Ruflo is an AI agent orchestration platform (a fork/successor of `claude-flow` by ruvnet). It runs hierarchical agent swarms inside any project folder and exposes itself to Claude Code via MCP. Prathap uses it for solo builds (Nako Pula, Javis, future ERP) where one architect agent delegates to coder/tester workers.

**Always read this skill end-to-end before running any Ruflo command for Prathap.** Skip the recall and you'll re-do work that's already done.

---

## 1. Install state — verify before anything else

Ruflo CLI was installed globally on **2026-05-10**. Before running `npm install -g ruflo` again, **check first**:

```bash
ruflo --version                          # expect: ruflo v3.7.0-alpha.20 or newer
npm list -g --depth=0 | grep -i ruflo    # expect: a single ruflo line
```

If both succeed, **do not reinstall**. If either fails, install with:

```bash
npm install -g ruflo@latest
```

Binary lives at: `C:\Users\PrathapAsus\AppData\Roaming\npm\ruflo.cmd` (plus `.ps1` and bash variants in same folder).

---

## 2. MCP registration (already done — do not redo)

Ruflo is wired into Claude Code at **user scope** so it's available in every Claude Code session on this machine, in any project. The entry is in `C:\Users\PrathapAsus\.claude.json` under `mcpServers`:

```json
"ruflo": {
  "command": "C:\\Users\\PrathapAsus\\AppData\\Roaming\\npm\\ruflo.cmd",
  "args": ["mcp", "start"],
  "type": "stdio"
}
```

**Verify after a Claude Code restart** with `/mcp` — `ruflo` should appear connected.

If MCP entry is missing, edit `C:\Users\PrathapAsus\.claude.json` (back it up first to `.claude.json.bak.<reason>`), add the block above next to the existing `memory` MCP server, validate JSON parses, then restart Claude Code.

---

## 3. Per-project setup — the init wizard

Ruflo's CLI install is one-time. **Each project Prathap wants to use Ruflo in needs its own `ruflo init`.**

```bash
cd /path/to/project
npx ruflo@latest init wizard
```

**Wizard answers Prathap has decided on (use these unless he says otherwise):**

| Wizard prompt | Answer | Why |
|---|---|---|
| Provider | **Anthropic only** | AD-POL-AI-GOV-001 + Prathap's preference. Never propose Gemini, OpenRouter, or multi-provider. |
| Enable federation? | **No** | Opens network ports, no benefit for solo builds. |
| Enable telemetry? | **No** | Personal preference; nothing leaves the machine he didn't authorise. |
| Topology | **Hierarchical** | One queen agent, workers below. Simpler than mesh. |
| Max agents | **6** | Plenty for solo work. More agents = more tokens + more chaos. |
| Memory backend | **Local (default)** | Stays on Windows PC. |
| Cost tracking | **Yes** | Prathap is CFO — token spend visible by default. |

After init, commit `.claude-flow/`, `CLAUDE.md`, and any generated config to git on a feature branch — never main.

---

## 4. Plugin curation — install allow-list

Ruflo has a large plugin marketplace. **Only install these** for any of Prathap's projects:

```bash
npx ruflo@latest plugins marketplace add ruvnet/ruflo
npx ruflo@latest plugins install ruflo-core
npx ruflo@latest plugins install ruflo-swarm
npx ruflo@latest plugins install ruflo-adr
npx ruflo@latest plugins install ruflo-ddd
npx ruflo@latest plugins install ruflo-testgen
npx ruflo@latest plugins install ruflo-cost-tracker
```

**Explicitly do NOT install** (and the reason — flag any of these if Prathap asks for them):

| Skip | Reason |
|---|---|
| `ruflo-federation` | Network exposure, no benefit |
| `ruflo-ruvllm` | Local LLM routing, debugging nightmare |
| `ruflo-aidefence` | Overkill for personal dev |
| `ruflo-neural-trader`, `ruflo-iot-cognitum`, `ruflo-market-data` | Wrong domain (insurance/accounting/ERP only) |
| `ruflo-jujutsu` | Prathap uses git, not jj |
| `ruflo-browser` | Add later if/when building a PWA |
| `ruflo-migrations` | Drizzle handles migrations natively |

---

## 5. ADR indexing into shared memory

If a project has an Architecture Decision Record, **index it before kicking off any swarm work** so every agent starts with that context:

```bash
npx ruflo@latest adr index ./docs/adr/
npx ruflo@latest memory store \
  --key "architecture/v1" \
  --value "$(cat docs/adr/ADR-001-*.md)" \
  --namespace <project-name>
```

Existing ADRs already on disk:
- `C:\dev\nako-pula\docs\adr\ADR-001-foundational-architecture.md` — Nako Pula (Nako Tech, personal venture; double-entry accounting domain). **Status: pre-staged. Repo not yet `git init`d. Do not assume Phase 0 has run.**

---

## 6. Cost budget — set before walking away

Always set a daily token cap before starting a swarm session. Prathap is the CFO and asks about spend.

```bash
npx ruflo@latest cost set-budget --daily 500000 --alert-at 0.75
```

500k tokens/day ≈ a few USD on Sonnet. Alert at 75%. If a swarm runs away overnight, it stops itself.

---

## 7. Kill switch (when something is going sideways)

Memorise these so they're not improvised under pressure:

```bash
npx ruflo@latest daemon stop                    # stop the background worker
npx ruflo@latest cleanup                        # remove project artefacts (current dir)
# Edit C:\Users\PrathapAsus\.claude.json and remove the "ruflo" mcpServers entry
npm uninstall -g ruflo                          # nuke the CLI globally
rm -rf <project>/.claude-flow <project>/.claude # nuke project-level Ruflo state
```

`.claude.json.bak.pre-ruflo` (created 2026-05-10) restores the pre-Ruflo MCP config.

---

## 8. Governance posture by project type

Prathap operates two distinct compliance regimes — **identify which one before scaffolding**:

| Project type | Examples | Posture |
|---|---|---|
| **Alpha Direct work** | Anything touching Graphite, RealPay, policy/claims/banking data, customer PII | AD-POL-AI-GOV-001 applies. Anthropic only. NO Gemini ever. PII anonymised in any prompt. Repo lives in a managed location with work git identity. |
| **Nako Tech / personal** | Nako Pula, personal experiments | Prathap's own choices apply. Gemini OK for Nako Tech specifically (per memory `f-nako-tech.md`). Personal Gmail in git config. Repos in `C:\dev\` or `C:\Users\PrathapAsus\`. |

**Default question to ask before init wizard:** "Is this Alpha Direct work or Nako Tech / personal?" — that one answer determines repo location, git identity, and AI vendor allow-list.

(Prathap may say "governance doesn't apply to me" for his own AI tooling install — that's fine for *his personal use of Ruflo on personal projects*. It does NOT override AD-POL-AI-GOV-001 for code or data that touches Alpha Direct production.)

---

## 9. The Tomorrow-Prathap rule

Whatever Ruflo produces in a session: **do not merge to main the same night.** Always work on a feature branch, push to a private GitHub backup, and let tomorrow-Prathap diff-review with fresh eyes before any merge. This is non-negotiable for agent-generated code.

---

## 10. Quick decision tree

When Prathap mentions Ruflo:

1. **"Is Ruflo installed?"** → Run §1 verification. Don't reinstall if present.
2. **"Set up Ruflo on project X"** → Verify §2 MCP entry → Ask governance posture (§8) → Run §3 init wizard with the canonical answers → Install §4 curated plugins → If ADR exists, run §5 indexing → Set §6 cost budget → Confirm with Prathap before any agent kickoff.
3. **"Ruflo is broken / acting weird"** → Check `ruflo doctor` first → Then `ruflo daemon status` → Last resort, §7 kill switch.
4. **"Use Ruflo to build X"** → This is a swarm kickoff. Pre-flight: ADR exists? Cost budget set? Working on feature branch (not main)? Then issue the swarm prompt with explicit Phase boundaries — never "build the whole thing".
