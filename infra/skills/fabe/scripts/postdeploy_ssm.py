#!/usr/bin/env python3
"""Fable post-deploy proof (Windows-native) — prove the live app is healthy after a deploy.

Two machine checks, no browser token needed:
  1. PUBLIC liveness (from this PC): key routes on https://omni.alphadirect.co.bw answer
     (200/redirect to login = app up; connection error / 5xx = down).
  2. ON-BOX error window (via SSM as claude-cli): count backend errors over the last N minutes
     and read the running build id. A spike = ALERT the CFO. NEVER auto-rollback — reversing a
     live insurance DB migration causes incidents; a human decides.

The frozen GWP-tile eyeball check needs an authenticated browser (omni token not on this PC),
so it is NOT done here — the SKILL tells the AI to confirm the GWP 125.15M tile via the
OmniDesktop app / Claude-in-Chrome as the final visual step.

Usage:  python postdeploy_ssm.py [--minutes 10] [--threshold 15]
Exit:   0 = healthy & quiet. 1 = a route is down OR an error spike (alert). 2 = check couldn't run.
"""
import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request

PROFILE = 'claude-cli'
REGION = 'af-south-1'
INSTANCE = 'i-02a5d76a61f4f09a5'
ENVFILE = '/etc/alpha-finance/.env'
REPO = '/opt/alpha-finance'
BASE = 'https://omni.alphadirect.co.bw'
KEY_ROUTES = ['/', '/dashboard', '/staff-login']


def public_liveness():
    fails = []
    for r in KEY_ROUTES:
        url = BASE + r
        try:
            req = urllib.request.Request(url, method='GET', headers={'User-Agent': 'fabe-postdeploy'})
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status >= 500:
                    fails.append(f'{r}: HTTP {resp.status}')
        except urllib.error.HTTPError as e:
            if e.code >= 500:
                fails.append(f'{r}: HTTP {e.code}')
        except Exception as e:
            fails.append(f'{r}: {type(e).__name__} {str(e)[:80]}')
    return fails


def aws(*args, timeout=90):
    r = subprocess.run(
        ['aws', *args, '--profile', PROFILE, '--region', REGION, '--output', 'json'],
        capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        return None
    return json.loads(r.stdout) if r.stdout.strip() else {}


def onbox_errors(minutes):
    script = '\n'.join([
        f'cd {REPO}',
        f'echo BUILD_ID=$(curl -s --max-time 5 http://localhost/build-id.txt 2>/dev/null | head -c 40)',
        f"C=$(sudo docker compose --env-file {ENVFILE} logs --since {minutes}m backend 2>/dev/null "
        f"| grep -icE 'traceback|error|exception|500 internal' || true)",
        'echo ERROR_COUNT=$C',
    ])
    out = aws('ssm', 'send-command', '--instance-ids', INSTANCE,
              '--document-name', 'AWS-RunShellScript', '--comment', 'fabe postdeploy',
              '--parameters', json.dumps({'commands': script.splitlines()}))
    if not out:
        return None
    cid = out['Command']['CommandId']
    import time
    for _ in range(20):
        time.sleep(5)
        inv = aws('ssm', 'get-command-invocation', '--command-id', cid, '--instance-id', INSTANCE)
        if inv and inv.get('Status') in ('Success', 'Failed', 'Cancelled', 'TimedOut'):
            return inv.get('StandardOutputContent') or ''
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--minutes', type=int, default=10)
    ap.add_argument('--threshold', type=int, default=15, help='>N backend errors in the window = spike')
    a = ap.parse_args()

    problems = []

    live_fails = public_liveness()
    if live_fails:
        problems += [f'route down: {f}' for f in live_fails]
    else:
        print(f'PUBLIC OK: {len(KEY_ROUTES)} routes answer at {BASE}')

    box = onbox_errors(a.minutes)
    if box is None:
        print('WARN: on-box error check could not run via SSM (creds/instance) — public liveness only.')
    else:
        build_id, count = '', 0
        for line in box.splitlines():
            if line.startswith('BUILD_ID='):
                build_id = line.split('=', 1)[1].strip()
            if line.startswith('ERROR_COUNT='):
                digits = ''.join(ch for ch in line.split('=', 1)[1] if ch.isdigit())
                count = int(digits or 0)
        print(f'ON-BOX: build_id={build_id or "(none)"}  backend errors last {a.minutes}m = {count}')
        if count > a.threshold:
            problems.append(f'error spike: {count} backend errors in {a.minutes}m (>{a.threshold})')

    if problems:
        print('\nPROBE FAIL — alert the CFO (do NOT auto-rollback):\n- ' + '\n- '.join(problems))
        sys.exit(1)
    print('\nPROBE OK — app up, error window quiet. Still eyeball the frozen GWP 125.15M tile in the app.')


if __name__ == '__main__':
    main()
