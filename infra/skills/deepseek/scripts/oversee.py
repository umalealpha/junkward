#!/usr/bin/env python3
"""DeepSeek oversight — the extra quality layer over Claude Code.

Sends the WORK Claude just produced (a claim, a diff, an answer, a plan, or an
Omni feature description) to DeepSeek's HIGHEST model (deepseek-reasoner, wired
in the gateway as `builder-reason`) for an independent second opinion. Runs OFF
the Claude subscription via the local gateway on :4000. Never rewrites code and
never touches the Claude subscription.

Reuses the exact gateway auth + client pattern from the `fabe` skill's panel.py
and the SAME DeepSeek key already in C:\\ai-cost-stack\\gateway\\.env (the key
Omni / the cost-stack already use). No new secret is created; nothing is printed.

Run with the gateway venv python:
  C:\\ai-cost-stack\\gateway\\venv\\Scripts\\python.exe oversee.py --work <file> [--ask "..."] [--mode review|omni]

Output: STRICT JSON on stdout:
  {"verdict":"APPROVE"|"REVISE", "confidence":0-100, "issues":[...], "missing":[...],
   "tests":[...], "summary":"...", "model":"deepseek-reasoner"}
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

GW = Path(os.environ.get('AI_GATEWAY_DIR', r'C:\ai-cost-stack\gateway'))
MODEL = 'builder-reason'          # gateway alias -> deepseek/deepseek-reasoner (highest DeepSeek)
MAX_WORK_CHARS = 48000            # reasoner takes a big context; over this we truncate + say so

# Minimal PII / secret guard: this work is about to leave to an EXTERNAL brain.
# Governance: PII (Omang/ID, bank acct, secrets) must NEVER go to the external panel.
PII_PATTERNS = [
    (r'(?i)\b(sk-[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_\-]{20,}|ghp_[A-Za-z0-9]{20,})\b', 'API key / token'),
    (r'(?i)\b(api[_-]?key|secret|password|passwd|bearer)\b\s*[:=]\s*\S+', 'credential assignment'),
    (r'\b\d{9}\b', 'possible Omang / ID number (9 digits)'),
    (r'(?i)\b(account\s*(no|number|#)|acc(t)?\s*[:#])\s*\d{6,}', 'bank account number'),
]


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


def pii_scan(text):
    hits = []
    for pat, label in PII_PATTERNS:
        if re.search(pat, text):
            hits.append(label)
    return sorted(set(hits))


REVIEW_PROMPT = """You are a SENIOR independent reviewer providing an EXTRA layer of oversight over
work produced by another AI assistant (Claude Code) for Alpha Direct Insurance. You are the highest
DeepSeek reasoning model. Be rigorous, skeptical, and specific — your job is to catch what the first
assistant missed, NOT to be agreeable.

Judge the work against these questions:
1. Does it actually do what was asked? (the whole ask, not a slice)
2. Is any claim of "done / works / tested / correct" backed by evidence, or is it asserted?
3. Are there bugs, wrong assumptions, missing edge cases, or unsafe operations?
4. Is it over-engineered (Karpathy: minimum code, nothing speculative)?
5. For numbers/finance: is the maths right and internally consistent?

Return STRICT JSON, nothing else:
{{"verdict":"APPROVE"|"REVISE","confidence":<0-100>,
  "issues":[{{"severity":"CRITICAL"|"HIGH"|"MEDIUM","where":"<file:line or area>","problem":"<one line>","fix":"<one line>"}}],
  "missing":["<part of the ask not covered>"],
  "tests":["<a concrete check that would prove/disprove the work>"],
  "summary":"<one plain-English line for a non-technical CFO>"}}

verdict = REVISE if any CRITICAL or confident HIGH is present, or the ask is not fully met.

=== ORIGINAL REQUEST ===
{ask}

=== WORK UNDER OVERSIGHT ===
{work}
"""

OMNI_PROMPT = """You are a SENIOR QA reviewer for the Alpha Direct "Omni" ERP (omni.alphadirect.co.bw,
Django backend + Next.js frontend, insurance finance/HR/underwriting/claims). You are the highest
DeepSeek reasoning model, giving an EXTRA layer of oversight. Below is a description of (or change to)
an Omni feature. Produce a real test plan and judge whether the feature as described will hold up.

Focus on Omni's known risk areas: entity isolation (no cross-company data leak), IDOR (users reaching
records they shouldn't), journal entries never posted with company=NULL, financial numbers must balance
and reconcile, self-service routes must not leak other staff's pay/PII, and maker/checker (dual-control)
gates must not be weakened.

Return STRICT JSON, nothing else:
{{"verdict":"APPROVE"|"REVISE","confidence":<0-100>,
  "issues":[{{"severity":"CRITICAL"|"HIGH"|"MEDIUM","where":"<route/model/area>","problem":"<one line>","fix":"<one line>"}}],
  "missing":["<gap in the feature>"],
  "tests":["<a concrete step-by-step check to run in Omni, with expected result>"],
  "summary":"<one plain-English line for a non-technical CFO>"}}

=== OMNI FEATURE / CHANGE UNDER OVERSIGHT ===
{work}
"""


def parse(raw):
    m = re.search(r'\{.*\}', raw, re.S)
    if not m:
        return {'verdict': 'ERROR', 'summary': 'no JSON in DeepSeek reply', 'raw': raw[:400]}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {'verdict': 'ERROR', 'summary': 'unparseable JSON from DeepSeek', 'raw': raw[:400]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True, help='path to the work/claim/diff/feature text under oversight')
    ap.add_argument('--ask', default='(not supplied)', help='the original request Claude was given')
    ap.add_argument('--mode', default='review', choices=['review', 'omni'])
    ap.add_argument('--round', type=int, default=1, help='which loop round this is (1-based); echoed + logged')
    ap.add_argument('--allow-pii', action='store_true', help='override the PII/secret guard (NOT advised)')
    a = ap.parse_args()

    work = Path(a.work).read_text(encoding='utf-8', errors='replace')
    truncated = False
    if len(work) > MAX_WORK_CHARS:
        work = work[:MAX_WORK_CHARS]
        truncated = True

    hits = pii_scan(work + ' ' + a.ask)
    if hits and not a.allow_pii:
        print(json.dumps({
            'verdict': 'BLOCKED_PII',
            'pii_found': hits,
            'summary': ('This work looks like it contains secrets or personal data '
                        '(' + ', '.join(hits) + '). It was NOT sent to DeepSeek. '
                        'Redact it and re-run, or review it with Fable only.'),
        }, indent=2))
        return

    tmpl = OMNI_PROMPT if a.mode == 'omni' else REVIEW_PROMPT
    prompt = tmpl.format(ask=a.ask, work=work)

    try:
        from openai import OpenAI
    except ImportError:
        sys.exit('FATAL: openai not installed. Use the gateway venv python (see SKILL.md).')

    client = OpenAI(base_url='http://localhost:4000', api_key=load_key())
    try:
        # DeepSeek v4 charges its hidden reasoning against max_tokens, in the same
        # budget as the answer, and the amount it burns is VARIABLE. Measured on
        # this exact 25KB review prompt: 13,691 reasoning tokens on one run and
        # 18,361 on the next. Whenever it hits the ceiling it does not error, it
        # returns content="" with finish_reason="length" - which this script used
        # to report as "no JSON in DeepSeek reply".
        #
        # So: give it real headroom, send reasoning_effort per request (the same
        # setting in the gateway's litellm_params does not reach the provider),
        # and treat a blank answer as retryable rather than as a verdict.
        # Diagnosed 2026-09-07, replacing the 2026-08-17 note that blamed the model.
        content = ''
        for budget in (32000, 48000):
            r = client.chat.completions.create(
                model=MODEL, temperature=0,
                max_tokens=budget, reasoning_effort='low',
                messages=[{'role': 'user', 'content': prompt}])
            content = (r.choices[0].message.content or '').strip()
            if content:
                break
            print(f'[oversee] empty answer at max_tokens={budget}, retrying higher',
                  file=sys.stderr)
        if not content:
            raise RuntimeError(
                'DeepSeek spent its whole token budget on hidden reasoning twice and '
                'returned nothing. Review a smaller slice of the work.')
        out = parse(content)
    except Exception as e:
        out = {'verdict': 'ERROR', 'summary': f'DeepSeek call failed: {e}'}

    out['model'] = 'deepseek-reasoner'
    out['round'] = a.round
    if truncated:
        out['note'] = f'work truncated to {MAX_WORK_CHARS} chars before sending'

    # Append one line per pass to a loop log so the whole cycle can be reported.
    try:
        log = Path(os.environ.get('TEMP', '/tmp')) / 'deepseek_loop.log'
        n = len(out.get('issues', [])) if isinstance(out.get('issues'), list) else 0
        with log.open('a', encoding='utf-8') as fh:
            fh.write(f"round {a.round} [{a.mode}] -> {out.get('verdict')} "
                     f"(conf {out.get('confidence', '?')}, {n} issues)\n")
    except Exception:
        pass

    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
