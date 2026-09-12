#!/usr/bin/env python3
"""
queue_manus_qc.py — RETIRED 9-Sep-2026. DO NOT USE. Kept only to read history.

MANUS QC IS STOPPED. Decided 9-Sep-2026 and recorded in MACHINE-TALK and memory
`p-omni-ux-qc`; QC is now run on the machine that ships, with `qc.sh`,
`eyes-on.mjs` and `a11y-names.mjs` in prat-skill/e2e, BEFORE the close-out.

This script refuses to run. It is not deleted because old rows on the bug board
were created by it and their shape needs explaining. The refusal is here, in the
script itself, rather than only in the /fabe skill text, because on 9-Sep-2026 I
filed three rows by following the skill — the last one 23 minutes after the stop
was logged. An instruction can be missed; a script that refuses cannot.

Filing a `qc_requested=True` row now is worse than doing nothing: it asks a
service that no longer polls, so the row sits open on the CFO's board and emails
him, and it reads like the change has an independent check waiting on it when
none is coming. A false assurance is worse than no assurance.

--- what it used to do, for reading old rows ------------------------------
CFO 2026-08-30 (standing convention, now ended). Every /fabe run that reaches SHIP +
DEPLOY OK creates one BugReport row on Omni's bug board with qc_requested=True,
so Manus polls it via its scoped `qc-manus` key and posts an independent QC
finding onto the same row (see hris/bug_report_views.py). This closes the loop:
fabe ships, Manus verifies, the finding lands where the CFO already sees his
bug board. No new channel, no chat scrollback dependency.

Cross-machine: Windows PC and the Mac Mini M4 both call this helper; they
share the same convention so it does not matter which machine shipped.

Behaviour
---------
- Runs a small Django-shell script on prod via AWS SSM (profile `claude-cli`,
  region af-south-1, instance i-02a5d76a61f4f09a5) that:
    * resolves the CFO user (`pganesharajah@alphadirect.co.bw`)
    * creates a BugReport(reporter=CFO, qc_requested=True, qc_requested_by=CFO)
    * stamps qc_requested_at = now
    * prints the row id + human URL
- Prints the row URL back to the fabe runner so it can be included in the
  CFO close-out ("QC row: <url>").

Usage
-----
    python queue_manus_qc.py \
        --title "fabe: <short deploy label>" \
        --body-file /tmp/fabe_deploy_summary.md \
        --sha <MAINSHA>
    python queue_manus_qc.py --title "..." --body "inline text" --sha <sha>
    python queue_manus_qc.py ... --dry-run    # print, do not create

The body should be a short Markdown description: what shipped, which routes/
files, one or two "test scenarios: ..." lines telling Manus what to prove. It
gets prefixed with "[fabe-QC] <title>" so a QC row is trivially distinct from
a real user-filed bug on the board.

Never accepts a key in stdin; never prints or logs a key; SSM handles the
auth end-to-end.
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import textwrap
from pathlib import Path

INSTANCE_ID = 'i-02a5d76a61f4f09a5'
REGION      = 'af-south-1'
PROFILE     = 'claude-cli'
OMNI_HOST   = 'https://omni.alphadirect.co.bw'
CFO_EMAIL   = 'pganesharajah@alphadirect.co.bw'


def _shell(title: str, body: str, sha: str) -> str:
    """The Django-shell script that runs on prod inside the backend container.

    Split as ONE fenced source we base64 into SSM — no interpolation on the
    shell side so quotes and newlines in `body` can't break the command."""
    inner = textwrap.dedent(f"""
        from django.contrib.auth.models import User
        from django.utils import timezone
        from core.models import BugReport

        TITLE = {title!r}
        BODY  = {body!r}
        SHA   = {sha!r}

        cfo = User.objects.filter(email__iexact={CFO_EMAIL!r}).first()
        assert cfo, 'CFO user not found on prod — cannot own the QC row.'

        header = f'[fabe-QC] {{TITLE}}'
        # Deploy SHA + omni convention: the description carries what shipped
        # and what Manus should prove. Manus reads it, works, posts the
        # finding back onto qc_result_note.
        desc = f'{{header}}\\n\\nDeployed prod SHA: {{SHA}}\\n\\n{{BODY}}'

        br = BugReport.objects.create(
            reporter=cfo,
            reporter_email={CFO_EMAIL!r},
            description=desc,
            page_url='(fabe ship — multi-page, see body)',
            status='new',
            qc_requested=True,
            qc_requested_by=cfo,
        )
        br.qc_requested_at = timezone.now()
        br.save(update_fields=['qc_requested_at'])
        print(f'QC_ROW_ID: {{br.id}}')
        print(f'QC_ROW_URL: {OMNI_HOST}/bug-reports/{{br.id}}')
    """).strip()
    return inner


def _ssm_run(script: str) -> str:
    """Send the script to prod through AWS SSM; return combined stdout."""
    b64 = base64.b64encode(script.encode('utf-8')).decode('ascii')
    remote = (
        f'echo {b64} | base64 -d > /tmp/fabe_qc.py && '
        f'cd /opt/alpha-finance && sudo docker compose --env-file /etc/alpha-finance/.env '
        f'exec -T backend python manage.py shell < /tmp/fabe_qc.py'
    )
    params = json.dumps({'commands': [remote]})

    # send-command
    send = subprocess.run(
        ['aws', 'ssm', 'send-command',
         '--profile', PROFILE, '--region', REGION,
         '--instance-ids', INSTANCE_ID,
         '--document-name', 'AWS-RunShellScript',
         '--parameters', params,
         '--query', 'Command.CommandId', '--output', 'text'],
        capture_output=True, text=True, check=True,
    )
    cmd_id = send.stdout.strip()

    # poll
    import time
    for _ in range(30):
        time.sleep(2)
        r = subprocess.run(
            ['aws', 'ssm', 'get-command-invocation',
             '--profile', PROFILE, '--region', REGION,
             '--command-id', cmd_id,
             '--instance-id', INSTANCE_ID,
             '--output', 'json'],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            continue                             # invocation not registered yet
        data = json.loads(r.stdout)
        status = data.get('Status')
        if status in ('Success', 'Failed', 'Cancelled', 'TimedOut'):
            out = (data.get('StandardOutputContent') or '') + (data.get('StandardErrorContent') or '')
            if status != 'Success':
                sys.stderr.write(f'\nSSM failed ({status}):\n{out}\n')
                sys.exit(1)
            return out
    sys.stderr.write('SSM invocation did not complete within 60s.\n')
    sys.exit(1)


def main() -> int:
    ap = argparse.ArgumentParser(description='Queue a Manus QC row on the Omni bug board after a /fabe ship.')
    ap.add_argument('--title', required=True, help='Short title (e.g. "dark-streak threshold + oversight fallback")')
    body = ap.add_mutually_exclusive_group(required=True)
    body.add_argument('--body', help='Body text (Markdown). Include "test scenarios: ..." lines.')
    body.add_argument('--body-file', help='Path to a file whose contents are the body.')
    ap.add_argument('--sha', required=True, help='Deployed prod SHA (from step 5 of /fabe).')
    ap.add_argument('--dry-run', action='store_true', help='Print what would be created; send nothing.')
    args = ap.parse_args()

    body_text = args.body
    if args.body_file:
        body_text = Path(args.body_file).read_text(encoding='utf-8')
    body_text = body_text.strip()
    if not body_text:
        sys.stderr.write('Body is empty — refuse to create an empty QC row.\n')
        return 2

    script = _shell(args.title.strip(), body_text, args.sha.strip())
    if args.dry_run:
        print('--- dry run: would run on prod via SSM ---')
        print(script)
        return 0

    out = _ssm_run(script)
    # Surface only the two named lines the fabe runner cares about
    for line in out.splitlines():
        if line.startswith('QC_ROW_'):
            print(line)
    if 'QC_ROW_URL' not in out:
        sys.stderr.write('\nQC row was NOT created — full SSM output:\n' + out + '\n')
        return 1
    return 0


def _refuse_retired():
    """Stop before touching prod. See the module docstring."""
    import sys
    sys.stderr.write(
        'REFUSED: Manus QC was stopped on 9-Sep-2026 and this helper is retired.\n'
        'Filing a qc_requested row asks a service that no longer polls, and it reads\n'
        'like an independent check is coming when none is. Run the QC HERE instead:\n'
        '    cd ~/.claude/skills/prat-skill/e2e\n'
        '    bash qc.sh "/changed/route"\n'
        '    node eyes-on.mjs "/changed/route"\n'
        '    node a11y-names.mjs /route1 /route2\n'
        'then put what you SAW in the close-out. See memory f-no-manus-qc.\n')
    sys.exit(2)


if __name__ == '__main__':
    _refuse_retired()

# --- retired below this line ---
if False:
    sys.exit(main())
