# Skill router — "I want to do X" → the skill that already does it

66 skills are installed. **Check here before building anything.** Reuse and extend what
is there. Hidden is not the same as missing.

Type the name with a slash (`/omni`), or invoke it with the Skill tool. Uppercase names
are typed exactly as written (`/Payroll`, `/KgareTrack`, `/AriaWindows`, `/Karpathy`, `/Tony`).

---

## Start here — the everyday four

| Want | Skill |
|---|---|
| Boot a blank chat into "working for Prathap" mode | **`/CFO`** (this one) |
| The full working stack — conventions, prod paths, quality gates | **`/prat-skill`** (auto-loads every session) |
| Did I do everything he asked? tick-box of asked vs done vs missed | **`/pending`** |
| Read the shared notebook — settled facts, who's who, frozen numbers | **`/note`** |

## Writing code

| Want | Skill |
|---|---|
| Build something properly, end to end, stopping at "tested and ready" | **`/code`** — runs notebook → prat-skill → Karpathy → lane-b → fabe |
| Put tested code live, safely | **`/deploy`** |
| Test, fix, then deploy with a consensus quality gate | **`/fabe`** (the ship gate) |
| The coding-discipline guardrails — no over-engineering, surgical changes | **`/Karpathy`** |
| An independent second opinion on work just produced | **`/deepseek`** |
| Debug a bug properly instead of guessing at fixes | `/systematic-debugging` |
| Write the test first | `/test-driven-development` |
| Prove it works before claiming done | `/verification-before-completion` |
| Plan a multi-step job before touching code | `/writing-plans` → `/executing-plans` |
| Explore intent and requirements before building | `/brainstorming` |
| Get code reviewed / handle review feedback | `/requesting-code-review` · `/receiving-code-review` |
| Run independent tasks in parallel | `/dispatching-parallel-agents` · `/subagent-driven-development` |
| Keep parallel sessions from clashing on one repo | `/using-git-worktrees` |
| Merge / wrap up a finished branch | `/finishing-a-development-branch` |
| Build or fix a skill itself | `/writing-skills` |
| — | `/using-superpowers` is installed but deliberately not routed. It is an aggressive dispatcher that wants a skill invoked before every reply; `prat-skill` §12 says delete it if sessions feel sluggish. Do not reach for it. |
| Agent swarm orchestration on the Windows PC | `/ruflo` |

### Which model lane to build on

| Want | Skill |
|---|---|
| Must-be-right work, all on the Claude subscription | **`/lane-a`** |
| Default cheap-volume build, off the subscription | **`/lane-b`** |
| Subscription exhausted, Claude down, or offline | **`/lane-c`** |

## The Alpha Direct systems

| Want | Skill |
|---|---|
| Anything in the Omni ERP | **`/omni`** |
| Policies, claims, premium, KYC in Graphite V2 | **`/graphite-v2`** |
| Approve/authorise a payment, forex, "is this paid or not" | **`/fnb`** |
| A CEO payment-authorisation brief from real claim data | **`/largepayment`** |
| Run or reconcile a payroll, PAYE, payslips | **`/Payroll`** |
| Leave and productive-hours accountability (the current one) | **`/alphaleave`** (supersedes `/leave`) |
| Catch the Time Doctor frozen-screen trick | `/time-doc-cheaters` |
| The CEO's inbox daily/weekly executive brief | **`/aruninbox`** |
| A whistleblower / speak-up matter | `/whistleblow` |
| Union insurance distribution — Jenamo, Centric Sure, BOPRITU | `/jenamo` |
| The BURS domestic-tax bid and Lekgetho AI concept | `/burs` |
| Alpha Direct's own delivery-discipline rules (the 12 guardrails) | `/alpha-direct-ai-delivery-discipline` |

## Writing and talking to people

| Want | Skill |
|---|---|
| Make writing sound human — kill the dashes and the AI words | **`/humanize`** (run on EVERY email and LinkedIn post) |
| Hand him a decision as a yes/no with a recommendation | **`/reco`** |
| Edit or improve existing copy | `/copy-editing` |
| Write marketing copy for a page | `/copywriting` |
| Take a topic from blank page to published piece | `/content-production` |
| Apply or document brand guidelines | `/brand-guidelines` |
| His personal details — bank, vehicles, family, quals | `/personal-info` |

## Board, strategy, finance advisory

| Want | Skill |
|---|---|
| Build a board or investor deck | `/board-deck-builder` |
| Prepare for a board meeting | `/board-prep` |
| Run a structured multi-perspective board deliberation | `/board-meeting` |
| Ratio analysis, DCF, variance, rolling forecast | `/financial-analyst` |
| Financial modelling, unit economics, cash management | `/cfo-advisor` |
| An adversarial thinking partner to stress-test a plan | `/executive-mentor` |
| How long is this going to take / where are we | `/task-eta` |

## Design and front end

| Want | Skill |
|---|---|
| Build or restyle any screen, page, dashboard, deck slide | **`/design`** |
| Design tokens, components, developer handoff | `/ui-design-system` |
| Apple platform design guidance | `/apple-hig-expert` |

## The project brain (per-project knowledge)

| Want | Skill |
|---|---|
| Set up a project brain | `/brain-setup` → `/brain-bootstrap` |
| Read or write brain pages | `/brain-page` |
| Digest a conversation or document into the brain | `/brain-ingest` |

## His PERSONAL projects — Alpha Direct rules do NOT apply

Alpha Direct governance, brand (Navy/Orange) and frozen numbers must never bleed into these.
Load the project's own skill and leave `prat-skill` out.

| Project | Skill |
|---|---|
| Nako Pula / Nako Tech — SME accounting + patient app | **`/nako`** |
| Gaborone Rifle Club treasury + app | **`/grc`** |
| ACCA Botswana / BCAT member portal | **`/acca`** |
| Tony Fragrances CRM | **`/Tony`** |
| KgareTrack — Botswana government fleet tender demo | **`/KgareTrack`** |
| ARIA — his Windows desktop AI | **`/AriaWindows`** |

---

## If nothing here fits

Say so plainly and build the simplest thing that works. Then write the skill for it
(`/writing-skills`) so it is not hand-rolled a second time.
