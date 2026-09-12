#!/usr/bin/env python3
"""Fable deploy (Windows-native) — deploy omni to prod via AWS SSM.

This is the Windows deploy path. There is no Instance-Connect SSH and no omni-ssm.sh here;
prod code runs via `aws ssm send-command` as the `claude-cli` profile (see r-omni-ssm-exec).

The change must ALREADY be on origin/main before you call this (the AI lands it with a
worktree cherry-pick — never a rebase of the shared checkout, never a force-push). This script
only pulls that main onto the box and (re)builds:

  On the box, as ubuntu:
    git -C /opt/alpha-finance fetch origin main && reset --hard origin/main
    docker compose --env-file /etc/alpha-finance/.env build
        --build-arg GIT_SHA=<HEAD> --build-arg BUILD_AT=<now> [backend] [frontend --no-cache]
    docker compose --env-file /etc/alpha-finance/.env up -d
    (backend auto-migrates on start — migrations REBUILD the image, never just restart)

SAFETY:
  * Refuses to do anything without --confirm. A dry run (default) prints the exact remote
    script and exits — so you can eyeball it first.
  * --expect-sha <sha>: after deploy, asserts the box HEAD == that sha; mismatch = non-zero exit.
  * Never force-pushes, never rebases, never rolls back. It deploys the main you already landed.

Usage:
  python deploy_ssm.py --backend --frontend --no-cache --expect-sha <sha> --confirm
  python deploy_ssm.py --backend --expect-sha <sha>          # DRY RUN (prints, does nothing)
"""
import argparse
import json
import subprocess
import sys
import time

PROFILE = 'claude-cli'
REGION = 'af-south-1'
INSTANCE = 'i-02a5d76a61f4f09a5'
REPO = '/opt/alpha-finance'
ENVFILE = '/etc/alpha-finance/.env'
# One box-wide deploy lock so two deploys never interleave a git-reset / docker
# build (e.g. many chats deploying at 8pm). Every deploy through this script
# waits its turn on the SAME lock. See remote_script().
LOCKFILE = '/tmp/omni-deploy.lock'
LOCK_WAIT_S = 1200          # wait up to 20 min for our turn before giving up


def remote_script(build_backend, build_frontend, no_cache):
    # The deploy body (git reset + build + up). Wrapped below in an exclusive
    # flock so concurrent deploys serialise instead of corrupting each other.
    body = [
        f'sudo -u ubuntu git -C {REPO} fetch origin main',
        f'sudo -u ubuntu git -C {REPO} reset --hard origin/main',
        f'cd {REPO}',
    ]
    if build_backend:
        # Stamp the image with the commit it is. Without these the health
        # endpoint answers "commit": "unknown" and the drift check — the alarm
        # for "merged but never live" — gives up before it can compare. Only
        # the blue/green script passed them; this path is the CFO's own machine
        # and did not, so the live image on 11-Sep could not name itself.
        body.append(
            f'sudo docker compose --env-file {ENVFILE} build '
            f'--build-arg GIT_SHA="$(sudo -u ubuntu git -C {REPO} rev-parse HEAD)" '
            f'--build-arg BUILD_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)" '
            f'backend')
    if build_frontend:
        fe = 'build --no-cache frontend' if no_cache else 'build frontend'
        body.append(f'sudo docker compose --env-file {ENVFILE} {fe}')
    body += [
        f'sudo docker compose --env-file {ENVFILE} up -d',
        # Record the release in the CFO Build Log. This path does NOT run
        # infra/host/deploy-zero-downtime.sh, so while the call lived only in
        # that script the Build Log's "Finished today" band stayed empty for
        # every deploy from this machine — the CFO's own master seat. Same one
        # implementation both paths use; it can never fail a deploy (exits 0).
        f'sudo RR_DC="docker compose --env-file {ENVFILE}" '
        f'bash {REPO}/infra/host/record-release.sh || true',
        f'echo DEPLOYED_SHA=$(sudo -u ubuntu git -C {REPO} rev-parse HEAD)',
    ]
    # Serialise ALL deploys on one box-wide lock: hold it for the whole
    # reset+build+up so two simultaneous deploys (many chats at 8pm) queue
    # rather than interleave. fd 9 auto-releases when the shell exits. If we
    # can't get our turn within LOCK_WAIT_S, abort cleanly (deploy nothing).
    lines = [
        'set -e',
        f'exec 9>{LOCKFILE}',
        f'echo "waiting for the deploy lock ({LOCKFILE}) - another deploy may be running..."',
        f'flock -w {LOCK_WAIT_S} 9 || {{ echo DEPLOY_LOCK_TIMEOUT; exit 3; }}',
        'echo "deploy lock acquired - this deploy has the box to itself"',
        *body,
    ]
    return '\n'.join(lines)


def aws(*args, timeout=60):
    # Force UTF-8 on the aws CLI (itself a Python app) AND on our decode: a build
    # log can contain non-ASCII (e.g. a ▲ from npm) and on a Windows cp1252 pipe
    # the aws CLI would crash encoding its own JSON, which used to read as a
    # phantom "deploy failed" even though the remote deploy succeeded.
    import os
    env = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}
    r = subprocess.run(
        ['aws', *args, '--profile', PROFILE, '--region', REGION, '--output', 'json'],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        env=env, timeout=timeout)
    if r.returncode != 0:
        sys.exit(f'aws error: {r.stderr.strip() or r.stdout.strip()}')
    return json.loads(r.stdout) if r.stdout.strip() else {}


def send_and_wait(script, wait_s=900):
    out = aws('ssm', 'send-command',
              '--instance-ids', INSTANCE,
              '--document-name', 'AWS-RunShellScript',
              '--comment', 'fabe deploy',
              '--parameters', json.dumps({'commands': script.splitlines(),
                                          'executionTimeout': [str(wait_s)]}))
    cid = out['Command']['CommandId']
    print(f'SSM CommandId: {cid}  (waiting up to {wait_s}s)')
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        time.sleep(6)
        inv = aws('ssm', 'get-command-invocation',
                  '--command-id', cid, '--instance-id', INSTANCE)
        status = inv.get('Status')
        if status in ('Success', 'Failed', 'Cancelled', 'TimedOut'):
            print(f'--- status: {status} ---')
            print('STDOUT:\n' + (inv.get('StandardOutputContent') or '')[-4000:])
            err = (inv.get('StandardErrorContent') or '').strip()
            if err:
                print('STDERR:\n' + err[-2000:])
            return status, inv.get('StandardOutputContent') or ''
        print(f'  ...{status}')
    sys.exit('TIMEOUT waiting for SSM command')


def main():
    # Never let printing a build log (which may hold non-ASCII) crash the deploy
    # on a Windows cp1252 console — the deploy already ran on the box by then.
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:            # noqa: BLE001 — older streams; best effort
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument('--backend', action='store_true', help='rebuild backend image (needed for any migration)')
    ap.add_argument('--frontend', action='store_true', help='rebuild frontend')
    ap.add_argument('--no-cache', action='store_true', help='frontend build --no-cache (bundle staleness)')
    ap.add_argument('--expect-sha', default='', help='assert box HEAD equals this sha after deploy')
    ap.add_argument('--confirm', action='store_true', help='actually deploy (omit = dry run)')
    a = ap.parse_args()

    script = remote_script(a.backend, a.frontend, a.no_cache)
    print('=== remote script (runs on prod as claude-cli via SSM) ===')
    print(script)
    print('==========================================================')
    if not a.confirm:
        print('DRY RUN -- nothing sent. Re-run with --confirm to deploy.')
        return

    # Allow for waiting on the box-wide deploy lock (up to LOCK_WAIT_S) PLUS the
    # actual build, so a queued deploy at a busy window (8pm) isn't cut off early.
    status, stdout = send_and_wait(script, wait_s=LOCK_WAIT_S + 900)
    if status != 'Success':
        if 'DEPLOY_LOCK_TIMEOUT' in (stdout or ''):
            sys.exit('DEPLOY_LOCK_TIMEOUT — another deploy held the lock too long. '
                     'Nothing was deployed; re-run in a few minutes.')
        sys.exit(f'DEPLOY {status} — investigate. Nothing rolled back (never auto-rollback).')

    if a.expect_sha:
        deployed = ''
        for line in stdout.splitlines():
            if line.startswith('DEPLOYED_SHA='):
                deployed = line.split('=', 1)[1].strip()
        if not deployed.startswith(a.expect_sha[:12]) and not a.expect_sha.startswith(deployed[:12]):
            sys.exit(f'SHA MISMATCH: box HEAD={deployed}, expected {a.expect_sha}. Verify before trusting.')
        print(f'OK: box HEAD {deployed} matches expected {a.expect_sha}.')
    print('DEPLOY OK.')


if __name__ == '__main__':
    main()
