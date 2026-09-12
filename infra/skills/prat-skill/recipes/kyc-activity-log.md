# Recipe — KYC Activity Log (Graphite V2)

**Goal:** enrich a KYC matrix Excel with each policy's complete **KYC activity history** — the chronological review log (document approvals/rejections, compliance changes, overall decisions; with date, reviewer, status, reason). This is the "Activity Log" tab shown on the Graphite KYC review screen.

**Tool:** `tools/kyc_activity_log.py` (companion to `kyc_matrix.py`) · ~10s · Source: Graphite V2 **`kyc_activity_log`** (reviewer ids resolved to names via `users`).

## How to run (Windows laptop only)
```
python "C:\Users\PrathapAsus\.claude\skills\prat-skill\tools\kyc_activity_log.py"
```
- Default input = newest `Desktop\KYC_matrix_*.xlsx`, enriched **in place**. Or `--input <file> [--output <file>]`.
- **Idempotent** — re-running replaces the sheet and reuses the summary columns.

## What it adds
- **"KYC Activity Log" sheet** — every event, chronological per policy: Policy · Customer ID · Date/Time · Section · Activity · Status · Compliance · Performed By · Reason. (Rejections red, approvals green; filters on.)
- **5 columns on the main sheet** — Latest KYC Activity · Latest Status · Latest By · Latest Activity Date · Activity Events (count).

## Find follow-ups
Filter **Latest Status = "Rejected"** or **KYC Compliance = "Non Compliant"**.

## Notes
- KYC activity is **customer-level** (the KYC review is per customer); each event is mapped to every one of that customer's policies in the file, so a shared customer's events appear under each of its policies (Customer ID column makes this clear).
- Prereqs same as `kyc_matrix.py` (SM plugin + `claude-cli` ecs:ExecuteCommand). See memory `r-gph-v2-bulk`.
- **Validated 2026-06-25:** tool output == hand-built file, cross-checked vs the live KYC review screen (Idah Nkhumisang / MIS2024097407: 6 events incl. "Overall KYC Rejected, Naomi Pheko, 22 Jun" — exact match, down to the "sufffice" typo).
