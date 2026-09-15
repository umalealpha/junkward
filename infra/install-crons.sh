#!/usr/bin/env bash
# Install / refresh the host cron jobs from the repo so they survive an
# instance rebuild. Runs on the omni EC2 HOST (not inside a container) — cron
# fires on the host and shells into the backend container.
#
# Source of truth: infra/cron/<name>.cron  ->  /etc/cron.d/<name>
#   (dotless target, 0644, root:root).  cron.d / run-parts ignores any file
#   with a dot in the name, which is why the target drops the ".cron" suffix.
#
# Three lists drive it, and every infra/cron/*.cron file must appear in exactly
# one of them (the installer WARNs about any that appears in none):
#   ENABLED   — installed and kept active.
#   DISABLED  — the schedule is version-controlled but held OFF: the installer
#               removes any active /etc/cron.d/<name> and writes a
#               <name>.DISABLED marker. This captures the operator's on/off
#               decision in the repo so a rebuild reproduces it (previously the
#               .DISABLED marker lived only on the mutable host -> a rebuild
#               silently re-enabled the job).
#   EXCLUDED  — deliberately not managed here (kept only as documented below).
#
# Safety:
#   * Must run as root (writes /etc/cron.d) — guarded below.
#   * Idempotent — safe to run on every deploy; a clean run is a no-op.
#   * Atomic per-file writes (temp + mv) so cron never reads a half-written file.
#   * The ONLY delete it performs is removing an active file for a DISABLED job.
#   * Ensures the shared log dir exists so redirected jobs actually run.
#
# Invoked by golive.sh on each deploy; also safe to run by hand:
#   sudo bash /opt/alpha-finance/infra/install-crons.sh
# Dry run (report drift, change nothing, non-zero exit on drift):
#   sudo bash /opt/alpha-finance/infra/install-crons.sh --check
set -uo pipefail

CHECK=0
[ "${1:-}" = "--check" ] && CHECK=1

if [ "$(id -u)" -ne 0 ]; then
    echo "install-crons.sh: must run as root (writes /etc/cron.d)" >&2
    exit 1
fi

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/cron" && pwd)"
DST_DIR="/etc/cron.d"
LOG_DIR="/var/log/alpha-finance"

# Canonical production cron set (keep in sync with /etc/cron.d on the omni EC2).
ENABLED=(
    # Intraday hours reminders. Held OFF here since build, "until the CFO
    # approves go-live" — approved 2026-09-09 once the Time-Doctor hours floor
    # shipped, so it belongs in ENABLED now.
    #
    # THIS LINE IS WHY THE FILE KEPT SWITCHING ITSELF OFF. It sat in DISABLED
    # below, and step 2 of this script deletes the active file and re-lays the
    # .DISABLED marker on EVERY run — and deploy-zero-downtime.sh runs this
    # script on every deploy. Someone restored the file by hand on 30 August and
    # the next deploy removed it again the following night. The watchdog emailed
    # the CFO nine times and the cause was read as "nobody knows what does it";
    # it was this list all along, doing exactly what it was told.
    hours-reminders
    realpay-reconcile
    monthly-feedback
    underwriting-adoption
    alpha-finance-backup
    backup-watch
    aware-reports
    release-drift
    devlog-digest
    bug-triage
    compliance-brain
    presummarise-claims
    consolidated-ops-digest
    discretionary-leave-report
    dpo-checklist
    duplicate-account-watch
    exceptions-report
    exec-provider-dashboard
    finance-monitoring
    fnb-email-autoclose
    fnb-sync
    graphite-claims-sync
    helpdesk-reminder
    leave-digest
    late-reminder
    cfo-brief
    m365-license-sync
    premium-refund-import
    manager-accountability
    manager-objectives
    morning-brief
    omni-leave-excuse
    omni-push
    omni-recurring-incentives
    omni-watchdog
    pin-access
    purge-old-cvs
    task-incentive
    task-confirm-digest
    row-watchdog
    snapshot-provider-counts
    staff-loan-rate
    staff-loan-repayments
    task-reminders
    stuck-work-sweep
    td-enforce
    td-reconcile
    timedoctor-token-check
    timedoctor-pull
    timedoctor-healthcheck
    welcome-back-digest
    workforce-daily-brief
    workforce-offboarding
)

# Version-controlled but held OFF (nexus tester reminders were switched off by
# the operator; keep them off across rebuilds).
DISABLED=(
    nexus-reminder
    # FNB health watch — switched OFF by the CFO 2026-08-23. Both alerts it sent
    # (bank link up/down, and "EFT batch unconfirmed for >2h") were judged noise:
    # Omni never receives a clean "paid" confirmation back from FNB (the CFO
    # authorises separately on the bank), so the stuck-batch alert is guaranteed
    # to fire for legitimate batches and cannot tell "stuck" from "fine". Held
    # OFF in the repo so a rebuild reproduces the decision. Re-enable only on an
    # explicit CFO request (move back to ENABLED).
    fnb-health-watch
)

# In the repo for reference but intentionally NOT auto-managed:
#   manual-update — the nightly "What's New" user-manual updater
#     (infra/cron/manual-update.sh: read-only `git log ... | update_user_manual`,
#     dedupes by sha). It is not currently deployed on the host; enable it
#     deliberately (move to ENABLED) if the manual should refresh nightly.
EXCLUDED=(
    manual-update
)

if [ ! -d "$LOG_DIR" ]; then
    if [ "$CHECK" -eq 1 ]; then
        echo "DRIFT log dir missing: $LOG_DIR"
    else
        mkdir -p "$LOG_DIR" && echo "MKDIR $LOG_DIR"
    fi
fi

installed=0; disabled=0; failed=0; drift=0; warned=0

in_list() { local x="$1"; shift; local e; for e in "$@"; do [ "$e" = "$x" ] && return 0; done; return 1; }

# 0) the deploy-window-safe runner every record-writing job calls (2026-09-04)
install -o root -g root -m 0755 "$SRC_DIR/../host/omni-manage.sh" /usr/local/bin/omni-manage

# 1) install / refresh the ENABLED jobs
for name in "${ENABLED[@]}"; do
    src="$SRC_DIR/$name.cron"
    if [ ! -e "$src" ]; then
        echo "MISS  $name (no $src in repo)"; warned=$((warned + 1)); continue
    fi
    dst="$DST_DIR/$name"
    if [ -e "$dst" ] && cmp -s "$src" "$dst"; then
        continue                                   # already current — no-op
    fi
    if [ "$CHECK" -eq 1 ]; then
        echo "DRIFT $name (would install/update)"; drift=$((drift + 1)); continue
    fi
    tmp="$(mktemp "$DST_DIR/.$name.XXXXXX")"
    if install -o root -g root -m 0644 "$src" "$tmp" && mv -f "$tmp" "$dst"; then
        echo "OK    $name"; installed=$((installed + 1))
    else
        rm -f "$tmp"; echo "FAIL  $name"; failed=$((failed + 1))
    fi
done

# 2) enforce DISABLED: remove any active file, ensure the .DISABLED marker
for name in "${DISABLED[@]}"; do
    active="$DST_DIR/$name"
    marker="$DST_DIR/$name.DISABLED"
    if [ "$CHECK" -eq 1 ]; then
        { [ -e "$active" ] || [ ! -e "$marker" ]; } && { echo "DRIFT $name (should be disabled)"; drift=$((drift + 1)); }
        continue
    fi
    [ -e "$active" ] && rm -f "$active" && echo "OFF   $name (removed active file)"
    if [ ! -e "$marker" ]; then
        src="$SRC_DIR/$name.cron"
        [ -e "$src" ] && install -o root -g root -m 0644 "$src" "$marker" || : > "$marker"
        echo "MARK  $name.DISABLED"
    fi
    disabled=$((disabled + 1))
done

# 3) warn about any repo cron file not accounted for in a list
for src in "$SRC_DIR"/*.cron; do
    [ -e "$src" ] || continue
    n="$(basename "$src" .cron)"
    if ! in_list "$n" "${ENABLED[@]}" && ! in_list "$n" "${DISABLED[@]}" && ! in_list "$n" "${EXCLUDED[@]}"; then
        echo "WARN  $n is in infra/cron/ but not in ENABLED/DISABLED/EXCLUDED"; warned=$((warned + 1))
    fi
done

if [ "$CHECK" -eq 1 ]; then
    echo "--- cron check: $drift drift, $warned warning(s) ---"
    [ "$drift" -eq 0 ] || exit 2
    exit 0
fi

echo "--- cron sync: $installed installed, $disabled disabled, $failed failed, $warned warning(s) ---"
[ "$failed" -eq 0 ] || { echo "CRON-SYNC FAILED ($failed job(s))" >&2; exit 1; }
