#!/usr/bin/env bash
# qc-nightly.sh — the scheduled overnight robot.
#
# Runs from Task Scheduler at midnight (Botswana time). It:
#   1. tops up the read-only /qa token (no password),
#   2. sweeps the main omni pages in BOTH the normal and dark look,
#   3. emails cfo@ + excoboard@ the result — ALL CLEAR, or the screens to fix.
#
# Read-only throughout: the server refuses this identity on anything but a read.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TOOLS="$HERE/../tools"
OUT="$HERE/nightly-out"
mkdir -p "$OUT"
cd "$OUT"

# Windows: python3 is a Store stub; fall back to python.
PYBIN=python3; python3 -c '' >/dev/null 2>&1 || PYBIN=python

# 1. refresh the read-only token
bash "$HERE/qc-token.sh" --force >/dev/null 2>&1 || true

# 2. sweep (writes qc-nightly-report.html + qc-nightly-manifest.json here)
rm -f qcn_*.png qc-nightly-report.html qc-nightly-manifest.json 2>/dev/null
node "$HERE/qc-nightly.mjs" >qcn.log 2>&1
RC=$?

# 3. email the report to the two exec inboxes
if [[ ! -s qc-nightly-report.html ]]; then
  echo "no report produced (see qcn.log) — not sending" >&2
  exit "$RC"
fi
SUBJECT=$("$PYBIN" -c "import json;print(json.load(open('qc-nightly-manifest.json'))['subject'])" 2>/dev/null)
[[ -z "$SUBJECT" ]] && SUBJECT="Omni overnight check — report"
ATTACH=$("$PYBIN" -c "import json;print(' '.join(json.load(open('qc-nightly-manifest.json')).get('attachments',[])))" 2>/dev/null)

"$PYBIN" "$TOOLS/send_mail.py" \
  --to cfo@alphadirect.co.bw excoboard@alphadirect.co.bw \
  --subject "$SUBJECT" \
  --body-file "$OUT/qc-nightly-report.html" \
  ${ATTACH:+--attach $ATTACH}
exit "$RC"
