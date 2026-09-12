#!/usr/bin/env bash
# eyes-on.sh — the pre-ship EYES-ON gate render step.
#
# Renders a route as a see-everything session AND the restricted staff session,
# at laptop widths 1120 (fixed-sidebar overlap bites here) and 1280, opening any
# pop-ups you name. Catches the two bug classes code review is blind to:
# visual/layout (see-everything) and role-only permission/visibility (staff).
#
# Usage:
#   eyes-on.sh "/internal-audit/findings" [--click "New finding"] [--click "..."]
#   eyes-on.sh "/dashboard"
#
# Sessions (values never printed):
#   see-all = ~/.omni-qa-token       read-only /qa session, self-refreshing from
#                                    ~/.omni-qa-key — no password, no emailed
#                                    code, and the server refuses it on any
#                                    write. Falls back to ~/.omni-e2e-token.
#   staff   = ~/.omni-e2e-token-staff  omni@ finance_manager, non-admin — the
#                                    only leg that feels a low role's denials.
#
# EVERY token is checked against the live API BEFORE rendering. A dead token used
# to render a shell full of 403s and still print "SHOT OK" — a silent false pass
# that cost real verification time. Now a dead leg is skipped loudly.
#
# Output PNGs land in the current dir: eyeson_<role>_<route>_<width>.png
# READ every one.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROUTE="${1:?usage: eyes-on.sh <route> [--click \"Button\"]...}"; shift || true
SAFE="$(printf '%s' "$ROUTE" | tr -c 'A-Za-z0-9' '_' | sed 's/^_//;s/_$//')"
BASE="${OMNI_BASE:-https://omni.alphadirect.co.bw}"
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'

# Is this token actually alive? Cheap authenticated read; prints nothing.
token_alive() {
  local code
  code="$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Token $1" \
           -H "User-Agent: $UA" "$BASE/api/v1/companies/" || echo 000)"
  [[ "$code" == "200" ]]
}

# Top up the read-only QA session if we hold the key (silent, never prints it).
[[ -s "$HOME/.omni-qa-key" ]] && "$HERE/qa-token.sh" >/dev/null 2>&1 || true

# The see-everything leg: QA read-only first, CFO token as fallback.
SEE_ALL=""
for f in "$HOME/.omni-qa-token" "$HOME/.omni-e2e-token"; do
  [[ -s "$f" ]] || continue
  v="$(cat "$f")"
  if token_alive "$v"; then SEE_ALL="$v"; echo "see-all leg: $f (alive)"; break; fi
  echo "  dead token, skipping: $f"
done
[[ -z "$SEE_ALL" ]] && echo "WARNING: no live see-everything session — visual bugs will NOT be caught"

STAFF=""
if [[ -s "$HOME/.omni-e2e-token-staff" ]]; then
  v="$(cat "$HOME/.omni-e2e-token-staff")"
  if token_alive "$v"; then STAFF="$v"; echo "staff leg: ~/.omni-e2e-token-staff (alive)"
  else echo "WARNING: the staff token is DEAD (they expire after 15h) — role-only bugs will NOT be caught this run.
         Refresh it by signing in as omni@alphadirect.co.bw, or accept that this run only covers visual bugs."
  fi
else
  echo "WARNING: no staff token — role-only bugs will NOT be caught this run"
fi

shot() {  # shot <role> <token>
  local role="$1" tok="$2" w out
  [[ -z "$tok" ]] && return 0
  for w in 1120 1280; do
    out="eyeson_${role}_${SAFE}_${w}.png"
    OMNI_TOKEN="$tok" node "$HERE/omni-shot.mjs" "$ROUTE" "$out" --width "$w" "$@" \
      && echo "  -> $out ($role @ ${w}px)"
  done
}

shot seeall "$SEE_ALL" "$@"
shot staff  "$STAFF"   "$@"
echo "EYES-ON done for $ROUTE — now READ every eyeson_*.png with your own eyes before SHIP."
