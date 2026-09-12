#!/usr/bin/env bash
# eyes-on.sh "/internal-audit/findings" --click "New finding"
# Shoots a screen as admin AND as the staff test account, at 1120 and 1280.
set -euo pipefail
cd "$(dirname "$0")"
exec node eyes-on.mjs "$@"
