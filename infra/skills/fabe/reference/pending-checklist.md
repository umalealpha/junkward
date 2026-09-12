# Pending checklist entries — awaiting CFO one-line approval

### H9 — Panel diff completeness
**Severity:** HIGH. Proposed 2026-07-25.
Before the external panel runs, the diff file list must equal the change set's file list (git status vs grep 'diff --git'). Excluding lockfiles is fine; excluding new scripts/tools is an automatic re-run. This round both external brains passed a change whose password-handling script they never saw.

### K6 — Decorative tests - a test CI never runs is not a regression guard
**Severity:** MEDIUM. Proposed 2026-07-25.
New or changed tests must sit inside the CI gate. Confirm the app/module appears in the .github/workflows/ci.yml test command before calling a change 'tested'. Raised by Fable 5 on PR #481: the whole procurement app is absent from the CI list, so the new PO-filter tests AND the CFO's claims-approval guardrail tests (test_claims_po_approver) never run automatically.

### K7 — PowerShell 5.1 encoding trap - ASCII scripts, BOM-less outputs
**Severity:** MEDIUM. Proposed 2026-07-25.
(1) .ps1 files must be pure ASCII: Windows PowerShell 5.1 reads BOM-less files as ANSI, so a single em-dash breaks the parse with a misleading 'string is missing the terminator'. (2) Files written for NON-PowerShell parsers (properties/env/CSV) must be written WITHOUT a BOM: 'Set-Content -Encoding utf8' on 5.1 emits one, and Java Properties.load reads it into the first key name so that key silently returns null. Use [IO.File]::WriteAllLines instead. Check: no bytes >= 0x80 in .ps1; first 3 bytes != EF BB BF on machine-read outputs. Both halves hit the Alpha Nexus signing path on 2026-07-25 - the second was masked by a ?: fallback in build.gradle.

### H10 — Constant set drifted from the documented rule
**Severity:** HIGH. Proposed 2026-07-25.
A gate keyed off a category/status set (frozenset, choices, status list) silently excludes a member the docstrings, seeder or UI copy assume is in it, so the rule never fires and its dashboard tile is a guaranteed zero. Burned 2026-07-25: supplier_recon's claim-authorisation gate was inert across all 31 claim suppliers on prod because the category its own seeder assigns was missing from CLAIM_BACKED_CATEGORIES. Check: every 'X must Y' claim in a docstring has a test pinning the actual CONSTANT, not just the happy-path category.

### L3 — Dead reference on a shipped artifact
**Severity:** HIGH. Proposed 2026-07-25.
Any QR code, URL, or click-path printed on a document, email, or PDF must resolve to an existing route/endpoint in the repo - verify the route exists before shipping the artifact that advertises it. Burned 2026-07-25: the rebuilt payslip footer told banks and embassies to scan the QR to verify the document, but no /api/verify/payslip/<uuid>/ route exists (only the PO one), so a third party would hit a login wall then a 404.

### L4 — Payment-cadence assumption in a months-based non-payment test
**Severity:** HIGH. Proposed 2026-07-26.
Any test of the form 'no payment for N consecutive months' must first establish the billing cadence of each policy. A paid-up ANNUAL or semi-annual policy shows N blank months and is fully covered, so a monthly test flags it as a non-payer. Burned 2026-07-26: 360 semi-annual/annual MIS policies reached a deactivation review list, 174 of which had paid within the previous 12 months (one had paid P8,229 four months earlier, covering it to the following March). Fix pattern: surface premium_freq to the reviewer, flag non-monthly rows, and never include them in a group-confirm block.

### L5 — Hand-typed numbers drift across a multi-part deliverable
**Severity:** HIGH. Proposed 2026-07-26.
Every number quoted in prose - email body, task body, a hardcoded sheet heading, the chat report - must be derived programmatically from the final dataset or pinned by an assertion against it. Each regeneration of the data invalidates every hand-typed copy. Burned 2026-07-26: after two rounds of data fixes one deliverable carried 34,554 / 34,548 / 34,547 in three places and the Summary sheet contradicted its own review tab; the 29-assertion suite passed throughout because it never checked prose. Fix pattern: builder emits figures.json, all prose renders from it, and the verifier greps for superseded values.

### L7 — Presence-only control that should later validate against source of truth
**Severity:** MEDIUM. Proposed 2026-07-29.
PAY-CLM-02 (proposed follow-up, NOT yet built): the claim-number requirement on claims payments (PAY-CLM-01, live 2026-07-29) checks only that a non-empty string was typed — 'x' passes. It does not confirm the claim exists in Graphite or that its reserve/status supports the payment. This is deliberately scoped as a separate feature (the CFO's fraud cross-check idea via Alpha Brain/DeepSeek). Rule: when a presence-only control guards money, log the source-of-truth validation as a named follow-up so presence-only does not silently become the permanent standard.

### L9 — Arrears live on the ACCOUNT, not the receipt stream
**Severity:** HIGH. Proposed 2026-08-03.
Before naming any customer a non-payer, cross-check the all-time ledger balance. A zero-or-NEGATIVE balance (prepayment, credit note, unallocated cash) defeats 'no receipt in window' - the customer is ahead, not behind. Found 2026-08-03: 57 of 408 policies on a Domestic non-payment list were in credit (P339,905 total), 3 inside the tier labelled 'chase or cancel first, there is no argument', one 36.6 months prepaid. Corollary: prose may never claim a sensitivity result broader than the one actually measured (a 443-policy zero-receipt pool is not a 408-policy list; 5 rules tested is not 4).

### L10 — Identity allow-list keyed on a non-unique attribute
**Severity:** HIGH. Proposed 2026-08-03.
An allow-list gate matched on the email local-part with the domain stripped. Django emails are NOT unique, so anyone able to create a user could set pganesharajah@anything.com and pass a confidentiality gate. Check: any identity allow-list must key on a UNIQUE attribute (username or user id) or a full verified email INCLUDING the domain, compared with rpartition so a suffix domain like alphadirect.co.bw.evil.com is refused; never a non-unique field and never a stripped local-part. Companion to L6 - L6 is about HOW you compare, this is about WHICH FIELD you compare. Found by Fable 5 on PR 583, 2026-08-03.

### L11 — Infra/config files ship live on deploy regardless of a code feature flag
**Severity:** HIGH. Proposed 2026-08-05.
A code change gated behind a feature flag can still change prod immediately via config files a deploy applies unconditionally (cron schedules through install-crons.sh, nginx/Caddy, compose env). A dormant change must keep every schedule/config file at its CURRENT value and register any NEW cron in install-crons.sh; else the flag-OFF deploy is not dormant. Burned 2026-08-05: retimed morning-brief/exceptions crons would have moved staff reports before the 08:30 settle pull on a flag-OFF deploy. Found by Fable 5 on the consolidated-email change.

### L8 — json_object mode guarantees valid JSON, not a JSON object
**Severity:** MEDIUM. Proposed 2026-07-29.
Any endpoint that parses LLM output with response_format='json_object' and promises graceful degradation MUST shape-check before use: isinstance(parsed, dict) before .get(), and coerce a supposed list field to [] when it is not a list, before slicing/iterating. A cheap cascade tier (Ollama/Gemini) can legally return a top-level array or scalar. The no-500 test battery must include a top-level array, a top-level scalar, and a dict-where-a-list-was-expected. Proven live on the payment smart-fill endpoint 2026-07-29: [] and 123 and {lines:{}} each 500'd until fixed.

### L16 — One-shot UI: async action busy/disabled state never reset on success
**Severity:** MEDIUM. Proposed 2026-08-17.
An async action's busy/disabled flag is reset only on the error path, so a still-mounted modal/button stays dead after the first successful use until a full page refresh. Reset busy on the SUCCESS path too. Found by Fable 5 on the subrogation record-payment modal 2026-08-17.

### L17 — Withholding with no remittance path
**Severity:** HIGH. Proposed 2026-08-17.
Any new tax withheld from a payee (PAYE/WHT) must show WHERE the withheld amount enters the statutory remittance figure. A deduction with no route into the BURS payment understates the liability and strands the employee's tax credit. Found by Fable 5 on 2026-08-17: leave-encashment PAYE is withheld and snapshotted on the HRIS row, but nothing carries tax_amount into the payroll period's PAYE remittance total - the approval email tells Finance to remit it manually.

### L19 — File download as a bare <a href> against a header-authenticated API
**Severity:** HIGH. Proposed 2026-08-17.
An anchor carries no Authorization header, so a download link 401s for every Bearer/Token user in production while an APITestCase download test stays green (the test client is authenticated). Downloads must go authedFetch -> blob -> saveBlob. Found by Fable 5 2026-08-17 on the NBFIRA filed-return download; both external judges missed it. See r-pdf-downlo.

### L1 — N+1 claims must name the missing prefetch
**Severity:** LOW. Proposed 2026-08-22.
Before accepting an N+1 finding on a loop over related rows, check the loader for prefetch_related/select_related and whether the loop reads only plain columns. A prefetched plain-column loop is not N+1 - cite the loader line either way.

### L21 — Stamped identifier breaks its own round-trip
**Severity:** HIGH. Proposed 2026-08-22.
Decorating an outbound identifier (e.g. the (O) marker on FNB endToEndId) requires stripping the decoration at every place the counterparty echoes it back (statement recon exact-match, status polling, dup checks), or a high-confidence match silently degrades. Burned 2026-08-22: the (O) marker broke banking recon Rule 1 until _match_line stripped it.

### L22 — Guard on create but the guarded field is rewritable on update
**Severity:** HIGH. Proposed 2026-08-31.
A create-time gate keyed on a payload field (location/company/account/title) must be re-applied on every update/partial_update path that can rewrite that field. A DRAFT edit is a second front door. Fable 5, Unicoin petty-cash ring-fence 2026-08-31: can_input_for_location ran only in create(); update reused the create-serializer with a writable location, so a draft on an open tin could be PATCHed onto the ring-fenced tin. Check: grep update/partial_update serializers for the gated field; a regression test PATCHes it and expects refusal.

### L20 — Credential-bearing signed-action-token email sent via a mandatory-CC/shared-mailbox helper
**Severity:** HIGH. Proposed 2026-08-18.
A per-recipient email carrying a signed action token (login-free approve/decline) must send with cc_cfo=False or the default shared-mailbox CC hands one reader valid tokens for every slot, defeating per-recipient token privacy. Seen recruitment authority emails 2026-08-18 + latent incentive notify_submitted cc-to-maker. Check: any email containing an action token goes to exactly one owner, no CC/BCC.

### L31 — A guard that names ONE caller cannot see a second caller that skips the work
**Severity:** HIGH. Proposed 2026-09-11.
When the rule is 'every X must do Y' (every deploy records its release; every writer goes through one reader), the test must DISCOVER the Xs by what they do - scan for the behaviour, e.g. anything running 'docker compose ... up -d' - never by a hard-coded list of known files. Burned 9->11-Sep-2026: #780's tests guarded deploy-zero-downtime.sh and stayed green for two days while the CFO's own SSM path and .github/workflows/deploy.yml deployed without recording; prod showed 53 build items and 1 marked live. Corollary: strip comments before matching, or a file that merely MENTIONS the right call is excused by its own comment.


### L32 — Two pipes joined on an idempotency key, and the slower pipe still says do-it-by-hand
**Severity:** HIGH. Proposed 2026-09-11.
When a live route and a batch route both handle the same item: (a) the key must have the same source AND the same column width on both sides, or a long value DataErrors into a best-effort catch and the join silently never happens; (b) any manual-action task the batch route raises must first check whether the live route already did the action. Burned 11-Sep-2026: the midnight importer would task Keetile to key into FNB a refund the direct route had already loaded.

