# Recipe — KYC Collection Matrix (Graphite V2)

**Goal:** given a list of policy numbers, produce a branded Excel of which KYC documents each policy has on file (+ agent, compliance, store, cancelled doc, data-protection consent, most-recent document & date).

**Tool:** `tools/kyc_matrix.py` · **Speed:** ~7 seconds for 235 policies · **Source:** Graphite V2 database (authoritative), via ECS exec — no browser, no rate limits.

## How to run (Windows laptop only)
1. Put the policy numbers in **`Desktop\KYC.xlsx`** (first column; a "Policy Number" header is auto-skipped). MIS / DOMG / COMG all work.
2. Double-click **`Desktop\Run KYC Check.bat`** — OR run:
   ```
   python "C:\Users\PrathapAsus\.claude\skills\prat-skill\tools\kyc_matrix.py"
   ```
3. Output lands on the Desktop: **`KYC_matrix_YYYYMMDD.xlsx`**.

Custom files: `python kyc_matrix.py --input "C:\path\list.xlsx" --output "C:\path\out.xlsx"` (input may be .xlsx / .csv / .txt).

## How it works (for a future Claude session)
- Reads policy numbers → builds one PHP query → base64 → `aws ecs execute-command` into `graphite-backend` (cluster `graphite-cluster`, profile `claude-cli`, af-south-1) → `php artisan tinker` → base64 JSON back → styled Excel (openpyxl).
- KYC source of truth = **`customer_kyc`** columns; agent = `users.firstName/lastName` via `policies.agent_id`; store = `stores.name` via `policies.storeID`; last document = most-recent across `policy_attachments` + `policy_documents` + `policy_kyc_documents`, falling back to a `customer_kyc` doc.
- "Y" = document on file; blank = not on file.

## Prerequisites (one-time, done 2026-06-25)
- AWS Session Manager plugin installed (`winget install Amazon.SessionManagerPlugin`).
- `claude-cli` IAM user has `ecs:ExecuteCommand` on the graphite cluster (inline policy `claude-ecs-exec`).
- Graphite must have a running `graphite-prod-backend` task.

## Notes
- **Prefer this over the browser/API pull** — the browser route is slow and had a silent rate-limit (429) trap. See memory `r-gph-v2-bulk`.
- Validated 2026-06-25: tool output == hand-verified file across all 15 data columns, 0 mismatches.
- Read-only (SELECTs). Whoever runs it sees real customer data — DPA-exempt accounts only.
