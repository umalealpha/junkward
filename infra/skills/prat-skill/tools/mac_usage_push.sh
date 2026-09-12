#!/bin/bash
# Run on the Mac Mini daily (cron/launchd) BEFORE the Windows email fires.
# Writes ccusage JSON to the alpha-finance repo so Windows can pull it.
#
# Install on Mac:
#   1. Copy this file to ~/.claude/scripts/mac_usage_push.sh
#   2. chmod +x ~/.claude/scripts/mac_usage_push.sh
#   3. Add to crontab:  0 6 * * * ~/.claude/scripts/mac_usage_push.sh
#      (runs at 06:00, before the Windows email at 06:30)

set -euo pipefail

REPO="${HOME}/work/alpha-finance"
USAGE_FILE="${REPO}/.claude/usage/mac-daily.json"
DAYS_BACK=8

cd "$REPO"
git pull --rebase --quiet 2>/dev/null || true

mkdir -p "$(dirname "$USAGE_FILE")"

SINCE=$(date -v-${DAYS_BACK}d +%Y%m%d 2>/dev/null || date -d "${DAYS_BACK} days ago" +%Y%m%d)
npx -y ccusage@latest daily --since "$SINCE" --json > "$USAGE_FILE"

git add "$USAGE_FILE"
git diff --cached --quiet && exit 0  # nothing changed

git commit -m "chore: mac daily usage $(date +%Y-%m-%d)" --quiet
git push --quiet
