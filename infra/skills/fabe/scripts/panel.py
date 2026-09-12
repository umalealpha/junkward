#!/usr/bin/env python3
"""Fable panel (Windows-native) — the off-subscription second-opinion panel (4 judges).

DeepSeek (`worker-cheap`), Gemini (`reviewer-gemini`) and OpenAI (`reviewer-openai`) review via
the local gateway on :4000; Ollama (`llama3.1:8b`) reviews via the LOCAL Ollama endpoint. All four
are OFF the Claude subscription, IN PARALLEL, against the Omni/Graphite common-mistakes checklist +
Karpathy. Weighted DeepSeek 25 / Gemini 30 / OpenAI 30 / Ollama 15. Fable 5.1 (on the subscription)
reads this + the diff and makes the FINAL call.

This script never touches the Claude subscription and never rewrites code.

Run with the gateway venv python:
  C:\\ai-cost-stack\\gateway\\venv\\Scripts\\python.exe panel.py --diff <file> --system Omni
Output: JSON {deepseek, gemini, openai, ollama, agree, weighted, panel_error[, too_large]} on stdout.
"""
import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

GW = Path(os.environ.get('AI_GATEWAY_DIR', r'C:\ai-cost-stack\gateway'))
# Gateway role aliases (all non-Anthropic, all off-subscription). Each is a distinct,
# deterministic single model so the gateway judges never collide.
DEEPSEEK, GEMINI, OPENAI = 'worker-cheap', 'reviewer-gemini', 'reviewer-openai'
# Ollama = the free, LOCAL 4th judge (CFO 2026-08-31). It runs OFF the gateway, straight to
# the local Ollama OpenAI-compatible endpoint — no key, no cloud, nothing leaves the PC.
OLLAMA_MODEL = 'llama3.1:8b'
OLLAMA_BASE = 'http://localhost:11434/v1'
# Panel weights (CFO-set 2026-08-31). The four share 100% of the external opinion; Fable 5.1
# reads their weighted verdict, does its own independent pass, and makes the FINAL call.
WEIGHTS = {'deepseek': 25, 'gemini': 30, 'openai': 30, 'ollama': 15}
MAX_DIFF_CHARS = 24000                           # over this -> panel skips, caller runs Fable-only


def load_key():
    env = GW / '.env'
    if not env.exists():
        sys.exit(f'FATAL: gateway .env not found at {env} — is C:\\ai-cost-stack\\gateway present?')
    for line in env.read_text(encoding='utf-8', errors='replace').splitlines():
        if line.startswith('LITELLM_MASTER_KEY='):
            v = line.split('=', 1)[1].strip()
            if v:
                return v
    sys.exit('FATAL: LITELLM_MASTER_KEY missing/empty in gateway .env.')


PROMPT = """You are a SENIOR reviewer of Alpha Direct {system} code. Review the change below.
Judge it ONLY against (A) the COMMON-MISTAKES checklist and (B) the Karpathy discipline items in it.
Do not invent new rules. Be strict but flag a false positive as such.

Return STRICT JSON, nothing else:
{{"verdict":"PASS"|"FAIL","issues":[{{"id":"<checklist id e.g. C1/H4/K2>","severity":"CRITICAL"|"HIGH"|"MEDIUM","where":"<file:line or area>","problem":"<one line>","fix":"<one line>"}}],"summary":"<one line>"}}

verdict FAIL if any CRITICAL or confident HIGH is tripped. MEDIUM alone = PASS with issues listed.

=== COMMON-MISTAKES CHECKLIST ===
{checklist}

=== CHANGE UNDER TEST ===
{diff}
"""


async def ask(client, model, prompt):
    # temperature is sent only when the backend accepts it. The `verifier` role is a
    # weighted route (80% Gemini / 20% OpenAI) and the OpenAI leg rejects any value
    # other than the default with a 400 — which silently turned 1 run in 5 into a
    # dead judge. Retry once without it rather than lose the vote.
    for kwargs in ({'temperature': 0}, {}):
        try:
            r = await client.chat.completions.create(
                model=model, messages=[{'role': 'user', 'content': prompt}], **kwargs)
            return r.choices[0].message.content or ''
        except Exception as e:
            if 'temperature' in str(e) and kwargs:
                continue
            return json.dumps({'verdict': 'ERROR', 'issues': [],
                               'summary': f'{model} call failed: {e}'})


def parse(raw):
    m = re.search(r'\{.*\}', raw, re.S)
    if not m:
        return {'verdict': 'ERROR', 'issues': [], 'summary': 'no JSON in reply', 'raw': raw[:300]}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {'verdict': 'ERROR', 'issues': [], 'summary': 'unparseable JSON', 'raw': raw[:300]}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--diff', required=True, help='path to the change/diff text under test')
    ap.add_argument('--system', default='Omni', help='Omni or Graphite')
    ap.add_argument('--checklist',
                    default=str(Path(__file__).resolve().parent.parent / 'reference' / 'omni-graphite-mistakes.md'))
    a = ap.parse_args()

    raw_diff = Path(a.diff).read_text(encoding='utf-8', errors='replace')
    if len(raw_diff) > MAX_DIFF_CHARS:
        print(json.dumps({
            'too_large': True, 'diff_chars': len(raw_diff), 'limit': MAX_DIFF_CHARS,
            'note': 'diff exceeds panel limit — external panel SKIPPED; run Fable-only on the full diff.',
        }, indent=2))
        return

    checklist = Path(a.checklist).read_text(encoding='utf-8', errors='replace')
    prompt = PROMPT.format(system=a.system, checklist=checklist, diff=raw_diff)

    try:
        from openai import AsyncOpenAI
    except ImportError:
        sys.exit('FATAL: openai not installed. Use the gateway venv python (see SKILL.md).')

    client = AsyncOpenAI(base_url='http://localhost:4000', api_key=load_key())
    # The local judge talks straight to Ollama (not the gateway); dummy key, 120s cap so a
    # slow/cold local model can never hang the panel — on error it just drops out and the
    # remaining weights renormalise.
    ollama = AsyncOpenAI(base_url=OLLAMA_BASE, api_key='ollama', timeout=120)
    ds_raw, gm_raw, oa_raw, ol_raw = await asyncio.gather(
        ask(client, DEEPSEEK, prompt),
        ask(client, GEMINI, prompt),
        ask(client, OPENAI, prompt),
        ask(ollama, OLLAMA_MODEL, prompt),
    )
    ds, gm, oa, ol = parse(ds_raw), parse(gm_raw), parse(oa_raw), parse(ol_raw)
    judges = {'deepseek': ds, 'gemini': gm, 'openai': oa, 'ollama': ol}

    verdicts = {k: v.get('verdict') for k, v in judges.items()}
    valid = {k: verdicts[k] for k in judges if verdicts[k] in ('PASS', 'FAIL')}
    panel_error = not valid                       # all three errored
    agree = len(set(valid.values())) == 1 and len(valid) == len(judges)

    # Weighted verdict across the judges that answered (weights renormalised over them).
    fail_w = sum(WEIGHTS[k] for k, v in valid.items() if v == 'FAIL')
    total_w = sum(WEIGHTS[k] for k in valid) or 1
    weighted = {
        'weights': WEIGHTS,
        'fail_pct': round(100 * fail_w / total_w),
        'verdict': 'FAIL' if fail_w * 2 > total_w else 'PASS',  # >50% weight says FAIL -> FAIL
    }

    out = {'deepseek': ds, 'gemini': gm, 'openai': oa, 'ollama': ol,
           'agree': agree, 'weighted': weighted, 'panel_error': panel_error}
    if panel_error:
        out['note'] = 'all external judges errored — treat as Fable-only.'
    elif len(valid) < len(judges):
        out['note'] = (f'only {len(valid)}/{len(judges)} external judges answered '
                       f'({", ".join(sorted(valid))}) — weighted over those; Fable decides.')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
