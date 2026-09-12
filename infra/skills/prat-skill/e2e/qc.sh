#!/usr/bin/env bash
# qc.sh — run the Quality Controller's full battery on one (or several) omni pages.
#
# Refreshes the read-only /qa session first (no password, no code), then runs the
# six-check battery per route. Reads every route through the locked read-only
# identity — it can never change anything.
#
# Usage:
#   qc.sh "/payroll/payslips"
#   qc.sh "/hris/leave" --click "Team Leave Report"
#   qc.sh "/dashboard" "/claims" "/reports/balance-sheet"     # several at once
#
# Screenshots + qc-report.json land in the current directory. READ the shots.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

# Top up the read-only QA token if we hold the key (silent; never prints it).
[[ -s "$HOME/.omni-qa-key" ]] && "$HERE/qc-token.sh" >/dev/null 2>&1 || \
  "$HERE/qa-token.sh" >/dev/null 2>&1 || true

# Split args into routes and pass-through flags (--click ...).
routes=(); passthru=()
seen_flag=0
for a in "$@"; do
  if [[ "$a" == --* ]]; then seen_flag=1; fi
  if [[ $seen_flag -eq 1 ]]; then passthru+=("$a"); else routes+=("$a"); fi
done
[[ ${#routes[@]} -eq 0 ]] && { echo 'usage: qc.sh "/route" [more routes] [--click "Button"]'; exit 2; }

rc=0
for r in "${routes[@]}"; do
  echo "── QC $r ──"
  node "$HERE/qc.mjs" "$r" ${passthru[@]+"${passthru[@]}"} || rc=1
done
exit $rc
