---
name: lane-b
description: Use when Prathap types "/lane-b" or asks for the default cheap-volume Cost Lanes build. DeepSeek builds and a verifier (80% Gemini / 20% OpenAI GPT-5.5) checks, off the Claude subscription through the local gateway, then Opus + Fable do the final on-subscription quality gate.
---

# Lane B — cheap volume (default lane)

> 🚫 **OMNI NEVER MOVES MONEY — never call Omni payment work "money-critical" (CFO angry directive 2026-08-31, ~100th correction).** Omni moves ZERO money. The CFO authorises every real payment himself **in the FNB app, with 2-factor**. An Omni "payment / authorise / approve / mark-as-paid" is a WORKFLOW RECORD only — it never debits an account. So nothing built in Omni is "money-critical", "money movement" or "moves funds"; never describe it that way. Omni payment code is ordinary record/workflow code (a wrong record is a data bug, not money moving). Real money egress = FNB + 2FA, by a human. See [[p-fnb-is-sandbox]].

Part of the Cost Lanes discipline (see `[[reference_cost_lanes]]` memory). Bulk of the work happens off-subscription and cheap (DeepSeek builds + a verifier through the local gateway — the gateway sends 80% of verify calls to Gemini and 20% to OpenAI GPT-5.5 for a second flavour of second-opinion); the Claude subscription is only spent on the final quality gate (Opus verify + Fable review).

## When to use

- Prathap types `/lane-b`, or asks for volume work without saying "must be right" (→ lane-a) or "offline/survival" (→ lane-c).
- This is the **default** lane when he just says "build this" for a batch of items.

## What to ask (one at a time, plain language)

1. **Build instruction** — the instruction to run per item (e.g. "Draft a cover note for {item}").
2. **Unit list** — the list of items to run it over.
3. **Objective check** — a plain, checkable fact that proves a result is right (not a model's opinion).

Skip re-asking anything Prathap already gave in his message.

## How to run it

1. **Make sure the gateway is up — and test it the RIGHT way.**

   🔴 **A bare `curl http://localhost:4000/...` returns HTTP 500 even when the gateway is perfectly
   healthy.** Every call needs `Authorization: Bearer <LITELLM_MASTER_KEY>` from
   `C:\ai-cost-stack\gateway\.env`; without it LiteLLM's own error handler crashes and you get a 500,
   not a 401. **A 500 here means MISSING KEY, not a dead gateway.** `/health/liveliness` returning
   200 does not mean completions work either. The only real test is a completion *with* the key —
   see [[r-cost-gw-needs]]. Never report the gateway dead on a keyless 500; that false alarm was
   raised again on 2026-09-09.

   Correct test:
   ```
   cd /c/ai-cost-stack/gateway && KEY=$(grep -m1 '^LITELLM_MASTER_KEY' .env | cut -d= -f2- | tr -d '"')
   curl -s -m 20 http://localhost:4000/v1/chat/completions -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"worker-cheap","messages":[{"role":"user","content":"Reply PONG"}],"max_tokens":16000}'
   ```
   All six lanes — worker-free, worker-cheap, builder-reason, verifier, reviewer-gemini,
   reviewer-openai — were verified answering on 2026-09-09.

   If it really is down, start it with **`C:\ai-cost-stack\gateway\run-gateway.cmd`** — NOT `run.ps1`.
   The bare `.ps1` is blocked by the PowerShell execution policy; the `.cmd` wrapper exists to get
   past exactly that. Run only ONE supervisor or instances fight over port 4000 ([[r-cost-stack-gw]]).
   If any of the DeepSeek/Gemini/OpenAI keys aren't set yet (`C:\ai-cost-stack\gateway\.env` has an empty `DEEPSEEK_API_KEY` / `GEMINI_API_KEY` / `OPENAI_API_KEY`), tell Prathap in plain language: "Open this page in your browser and paste the missing key(s) in: `http://127.0.0.1:8787`" — run `python C:\ai-cost-stack\gateway\keyentry.py` first if that page isn't already running. Never ask him to paste keys into chat. A missing OpenAI key only breaks ~1 in 5 verify calls — Lane B can still run on Gemini alone if he wants to proceed without it.

2. **Run the cheap build+verify pass:**
   ```
   C:\ai-cost-stack\gateway\venv\Scripts\python.exe C:\ai-cost-stack\workflows\swarm.py --build "<build instruction>" item1 item2 item3
   ```
   **Items now run 10 at a time by default** (was 5). `--workers N` changes it.

   **Pick the builder with `--builder` (added 2026-09-09 — it used to be hardcoded to the cheap one):**

   | `--builder` | What actually runs | Cost | Use when |
   |---|---|---|---|
   | `worker-cheap` *(default)* | DeepSeek v4-flash | cheap, metered | ordinary volume work |
   | `builder-reason` | **DeepSeek v4-pro — the high engine** | dearer, metered | code that must be right first time |
   | `worker-free-code` | local Ollama qwen3:8b | **free** | bulk code, zero spend |
   | `worker-free-reason` | local Ollama deepseek-r1:7b | **free** | bulk reasoning |
   | `worker-free` | local Ollama llama3.1:8b | **free** | bulk prose |

   The `worker-free*` lanes cost nothing but are slower per item and weaker — use them for volume
   where a real `--check` catches the misses. Measured 2026-09-09, 10 items built at once with
   `--builder builder-reason`: **10 of 10 passed their real tests, 41 seconds wall clock, zero repair rounds.**

   ⚠️ **Curly braces in `--build` crash the whole run before a single build starts.** The prompt goes
   through Python `.format()`, so a literal `{` or `}` (JSON inside a prompt, an f-string example)
   raises `KeyError`. Double them: `{{` and `}}`.
   This writes `C:\ai-cost-stack\workflows\candidates.json` — each item with its DeepSeek build and a verifier critique (`verify_model` says whether Gemini or OpenAI did it; the gateway splits 80/20).

   **For CODE work, always use the real-check repair loop — this is the single biggest accuracy lever:**
   ```
   ...swarm.py --build "Write ... solving {item}. Return only code." \
     --write "build/{item}.py" \
     --check "C:\ai-cost-stack\gateway\venv\Scripts\python.exe -m pytest tests/test_{item}.py -q" \
     --max-repairs 2 \
     task1 task2
   ```
   - `--write` saves each build to a real file (code fences auto-stripped) so the check can actually run it.
   - `--check` is a shell command that must exit 0. When it fails, its **exact error output is fed straight back to the builder for a repair, and it re-runs — up to `--max-repairs` times** (default 2; research shows rounds 1–2 capture ~75% of the gain, so don't go higher without reason). This is the "loop" — models fix errors they can *see* far better than they avoid them (proven: an underspecified slugify task failed round 1, passed after 1 repair).
   - Each candidate now records `rounds`, `check_passed`, and `check_output`. The end-of-run summary prints how many passed the real check and how many needed a repair.
   - **`--verify` (added 2026-09-09) now defaults to `on-fail`:** the paid second-opinion call is
     SKIPPED for any item whose real `--check` passed. A runnable check outranks a model's opinion,
     so that call bought nothing while costing ~8s and a metered request on every passing item.
     `--verify always` restores the old behaviour, `--verify never` turns it off entirely.
   - The real `--check` is the source of truth, NOT the model verifier's opinion. (In the proof run the verifier wrongly warned the passing code "might fail" — that's exactly why a runnable check outranks an opinion.)

3. **Run the Claude quality gate** — call the **Workflow** tool: read `candidates.json`, then for each candidate run `agent(..., {model: 'opus'})` to check it against the objective check Prathap gave you, looping flagged items back through one more DeepSeek build (re-run swarm.py for just those items) and re-verify, max 2 rounds. Finish with one `agent(..., {model: 'fable'})` call doing the final review pass over everything that survived. Items that already passed a real `--check` need far less scrutiny here — focus Claude's budget on the still-failing ones.

## The gate itself

Pass/fail is the objective check — a fact you can verify, never a model's opinion. If Prathap didn't give one, ask before running anything.

## Report back to Prathap

Plain language: how many items passed, how many needed a redo, and anything still flagged after 2 rounds for him to decide.

---

## Build Log — record it (CFO instruction, 2026-09-09)

Everything Prathap asks for through this command MUST appear on his Build Log
(omni → Build log). He reads it at the end of a day to see what he asked for,
what went live, and what is still open. If this command does not write there,
his work lands in the "shipped, no request recorded" band and looks like it
was never asked for.

Run this the moment you pick the work up, and again when it is built:

    python C:\Users\PrathapAsus\.claude\scripts\devlog.py         --key cfo-YYYY-MM-DD-<short-slug>         --text "his request, IN HIS OWN WORDS — never a tidied summary"         --title "<short title>" --source lane-b --area <omni area> --status building

    # when the code is built and tested, before it goes live:
    python C:\Users\PrathapAsus\.claude\scripts\devlog.py         --key cfo-YYYY-MM-DD-<short-slug> --status waiting

Rules:
- **--key must be the same every time** for one request. Same key = one row.
  A new key for the same ask shows as two outstanding jobs.
- **--text is his words, untouched.** A paraphrase is where "that is not what
  I asked for" starts.
- **NEVER --status live.** Only a recorded deploy may say live; omni refuses it
  and downgrades to waiting. Do not try to work around that — the refusal is
  the entire point of the log.
- If logging fails it prints a warning and exits 0. **Never let it stop the
  build** — bookkeeping is not worth losing his work over.

### Link the commit so the release can claim it
Put this trailer at the end of every commit message for this work, above the
Co-Authored-By line — a deploy links commits to a build item ONLY by this line,
never by matching words:

    Dev-Item: <the same key you used above>
