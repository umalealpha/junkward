#!/usr/bin/env bash
# qa-token.sh — refresh ~/.omni-qa-token from the read-only QA key.
#
# Why this exists: DRF tokens die after 15 hours, so ~/.omni-e2e-token goes
# stale between sessions and every render fails with "Invalid token" — which
# reads like a broken feature and has burned real verification time. The
# read-only /qa view (core/qa_view_login.py) hands out a token with no password,
# no emailed code and no SSO, so the harness can top itself up.
#
# The token is a READ-ONLY identity: the server refuses it on anything but GET,
# so it can render any page and change nothing.
#
# Usage:  qa-token.sh          # refresh if missing/stale, print length only
#         qa-token.sh --force  # refresh regardless
#
# Never prints the key or the token.
set -euo pipefail

KEY_FILE="$HOME/.omni-qa-key"
TOK_FILE="$HOME/.omni-qa-token"
BASE="${OMNI_BASE:-https://omni.alphadirect.co.bw}"

[[ -s "$KEY_FILE" ]] || { echo "NO_KEY: $KEY_FILE is missing — generate it on prod first" >&2; exit 2; }

# Windows: `python3` is a Microsoft Store stub that exits without running. Fall
# back to `python` when python3 cannot actually execute. (No-op on the Mac.)
PY_BIN=python3
python3 -c '' >/dev/null 2>&1 || PY_BIN=python

# Keep the existing token ONLY if it STILL WORKS. A server-rotated/expired token
# can look "fresh" by file age yet be dead — that used to bounce QC to the /qa
# sign-in gate (a read-only tool should never ask a human to sign in). So we
# probe the token with one lightweight read; if it 200s we reuse it, otherwise
# we fall through and mint a new one silently. No password, no code, no gate.
if [[ "${1:-}" != "--force" && -s "$TOK_FILE" ]]; then
  if "$PY_BIN" - "$BASE" "$TOK_FILE" <<'PROBE' >/dev/null 2>&1
import sys, pathlib, urllib.request, urllib.error
base, tok_file = sys.argv[1], sys.argv[2]
tok = pathlib.Path(tok_file).read_text().strip()
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36')
req = urllib.request.Request(f'{base}/api/v1/companies/',
    headers={'Authorization': f'Token {tok}', 'Accept': 'application/json', 'User-Agent': UA})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
PROBE
  then
    echo "QA token still valid — not refreshed"
    exit 0
  fi
fi

"$PY_BIN" - "$BASE" "$KEY_FILE" "$TOK_FILE" <<'PY'
import json, os, pathlib, sys, urllib.request, urllib.error
base, key_file, tok_file = sys.argv[1], sys.argv[2], sys.argv[3]
key = pathlib.Path(key_file).read_text().strip()
req = urllib.request.Request(
    f'{base}/api/v1/auth/qa-view/',
    data=json.dumps({'key': key}).encode(),
    headers={'Content-Type': 'application/json', 'Accept': 'application/json',
             # Cloudflare blocks the default python user-agent (error 1010).
             'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/140.0.0.0 Safari/537.36'},
    method='POST')
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        tok = json.load(r)['token']
except urllib.error.HTTPError as e:
    body = e.read()[:160].decode(errors='replace')
    print(f'QA_TOKEN_FAILED: HTTP {e.code} {body}', file=sys.stderr)
    sys.exit(3)
p = pathlib.Path(tok_file)
p.write_text(tok)
os.chmod(p, 0o600)
print(f'QA token refreshed ({len(tok)} chars) -> {p}')
PY
