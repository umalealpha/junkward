---
name: largepayment
description: >
  Alpha Direct's "Large Payment Authorisation" workflow — pull real claim detail
  live from the Graphite V2 database, and turn it into the exact CEO-approval
  payment-authorisation document Finance already uses (Bontle Tendani's format),
  then email it to the CEO for sign-off. Auto-load whenever Prathap types
  "/largepayment", says "large payment request" / "payment authorisation for
  Arun" / "claims payment brief for the CEO", or the task is: filter FNB/Omni
  payment batches down to claims, pull those claims from Graphite, and prepare
  or send a CEO authorisation email. Companion to graphite-v2 (the DB access
  method) and fnb (the payment-batch data this starts from).
---

# Large Payment Authorisation — quick-start

Two things happen in this workflow: **(1)** pull real claim facts out of the live
Graphite database so nothing in the request is guessed, and **(2)** lay them out
in the exact document format Finance already uses, then send it to the CEO.

## Reusable template

**Desktop\Largepayment\Large Payment Authorisation Template.docx** — the blank,
reusable Word version of the format below. Fill it in per run rather than
rebuilding the structure from scratch.

## Step 1 — Filter the payment batch down to claims

Given a pasted FNB/Omni "Authorisation Requested" batch list, a **claim payment**
is any line whose reference starts with a Graphite claim number: `G20xxxxxxxx`,
`DOMG20xxxxxxxx`, or `MIS20xxxxxxxx`. Everything else (attorney retainers with no
claim number, reinsurance, provident fund, utilities, payroll) is NOT a claim
payment for this purpose — leave it out unless Prathap says otherwise. Apply
whatever amount threshold he gives (he has asked for >20,000 and >15,000 in past
runs — always confirm the cut-off, never assume the last one used still applies).

## Step 2 — Pull the real claim facts from Graphite (never guess these)

Use the same ECS-exec + `php artisan tinker` method as **graphite-v2** (AWS
profile `claude-cli`, region `af-south-1`, cluster `graphite-cluster`, container
`graphite-backend`). Get the running task ARN first:

```
aws ecs list-tasks --cluster graphite-cluster --service-name graphite-prod-backend --profile claude-cli --region af-south-1 --output text
```

Then run (edit `$nums` to the claim numbers you're pulling):

```php
error_reporting(0);
$nums = ['G2026005105','G2026004941']; // <- edit
$rows = [];
foreach ($nums as $n) {
    $c = \DB::table('claims')->where('claim_number',$n)->first();
    $nc = \DB::table('new_claims')->where('claim_number',$n)->first();
    $customerName = null; $businessName = null;
    if ($c && $c->policy_id) {
        $pol = \DB::table('policies')->where('id',$c->policy_id)->first();
        if ($pol) {
            $businessName = $pol->business_name ?? null;
            if (isset($pol->customer_id)) {
                $cust = \DB::table('customer')->where('id',$pol->customer_id)->first();
                if ($cust) $customerName = trim(($cust->firstName ?? '').' '.($cust->lastName ?? ''));
            }
        }
    }
    $rows[] = [
        'claim_number'=>$n,'business_name'=>$businessName,'customer'=>$customerName,
        'policyNumber'=>$pol->policyNumber ?? null,
        'status'=>$c->status ?? null,'sub_status'=>$c->claim_sub_status ?? null,
        'nc_date_of_loss'=>$nc->date_of_loss ?? null,
        'nc_description'=>$nc->description_of_loss ?? null,
        'nc_reserve'=>$nc->reserve_amount ?? null,'nc_paid'=>$nc->paid_amount ?? null,
        'invoice'=>$c->invoice ?? null,
    ];
}
echo "##ZZ##".base64_encode(json_encode($rows))."##ZZ##";
```

Wrap as base64 → pipe into tinker (see graphite-v2 for the full `sh -c` incantation
and PsySH gotchas). Decode the `##ZZ##...##ZZ##` marker to get the JSON.

**Schema landmines specific to this pull (verified 1-Sep-2026):**
- Customer table is named **`customer`** (singular), columns **`firstName`/`lastName`**
  (camelCase) — NOT `customers`, NOT `first_name`/`last_name`. Querying the wrong
  name/casing silently returns null, not an error, on the `??` fallback — you will
  get a blank "Insured Name" and not notice unless you check.
- `claims.invoice`, `claims.incident_date`, `claims.incident_description` are
  routinely **null** even on real claims — the loss narrative usually lives in
  `new_claims.description_of_loss` instead. Check both before saying "no data".
- `new_claims.reserve_amount` / `paid_amount` are often **null or 0** even on
  claims that are actually being paid — do not read a null/zero reserve as "no
  money involved". See [[r-gph-clm-tables]] for the fuller claims
  schema map (the `claim_reserves` misnamed-table trap etc.)
- **Never force a narrative onto a mismatch.** On 1-Sep-2026, claim G2026005105
  ("KOMAROV EX-GRATIA" in the FNB batch) turned out to be registered against a
  *different* named party (Boipuso Pelo, a thumb injury) — Komarov was only the
  policyholder. Flag this kind of thing explicitly in the request rather than
  quietly making the names agree.
- If a claim has no reliable insured/claim data at all (e.g. name comes back as
  a placeholder like "Tbc Tbc"), **leave it out of the CEO request** and say so
  in an NB line — don't guess a name to fill the row.

## Step 2b — Bank balances

Prathap will usually paste an FNB "Day To Day" balances screenshot (Claims
Account, Current Account — Balance and Available Balance columns). Use the
**Available Balance**, not the raw Balance, when checking whether an account
covers the run. Balance After = Available Balance − payments in that section.
State plainly whether it's SUFFICIENT FUNDS or a SHORTFALL (and if a shortfall,
by how much, and what transfer or re-routing would close the gap) — never leave
this unstated.

## Step 3 — The exact document format (CRITICAL — read this before sending anything)

**[[f-copy-fmt-verbatim]] — the single most important
rule in this skill.** On 1-Sep-2026 Prathap was furious when the email carried
a short summary table with the full detail only in an attachment. **The whole
document below goes VERBATIM in the EMAIL BODY** (as HTML tables) — an attached
Word copy can go alongside it, but the body must stand alone as the complete
document. Never shorten, merge columns, or drop a section to make it more
"readable" unless he explicitly asks for a shorter version.

```
Alpha Direct Insurance Company
Payment Authorisation
To: Mr Arun Iyer – Chief Executive Officer
Date: [DD Month YYYY]
Subject: Payment Approval – [Current Account & ]Claims Payments

Mr Iyer,
Please find below the payment authorisation request for your review and
approval. All payments have been loaded and verified in the banking platform.

Section A: Current Account Payments Loaded & Verified   <- only if there are any
[table: Payment Reference | Amount (BWP) | Invoice No. | Invoice Date |
 Insured Name | Reason | Inputer | Verified By]
Total Current Account Payments (n)   BWP x

Section B: Claims Account Payments Loaded & Verified
[same 8 columns]
Total Claims Payments (n)   BWP x

Summary of Requested Payments for Approval
[table: Payment Category | Amount (BWP)]

Bank Position
[table: Account | Balance Before (BWP) | Total Payments (BWP) | Balance After (BWP)]

SUFFICIENT FUNDS: ... / SHORTFALL: ... [state clearly, with any transfer/re-routing option]

Declarations
Senior Accountant Declaration: "..."
Finance Manager Declaration: "..."

Prepared & Submitted By
Name: [who prepared it]     Date: [date]     Signature: ___________________

Verified By (Finance Manager)
Name: [name, or "Pending Finance verification" if not actually checked]     Date:     Signature:

CEO Approval
Name: __________________     Date: __________________     Signature: __________________

Alpha Direct Insurance Company  |  Confidential  |  For Internal Use Only
```

Never put a name against "Verified By" or a Declaration unless that person
actually reviewed the figures — write "Pending Finance verification" rather
than fabricate a sign-off.

## Step 4 — Send it

**Only via the Graph sender** — never a Gmail-style tool (see
[[f-never-gmail]]). Use `send_mail_attach.py` (see
[[r-win-graph]] for the exact path/flags):

```
python <prat-skill>/tools/send_mail_attach.py \
  --to aiyer@alphadirect.co.bw \
  --cc pbeka@alphadirect.co.bw pkago@alphadirect.co.bw ktshutlhedi@alphadirect.co.bw \
  --subject "Payment Authorisation Request – Claims Payments – [date]" \
  --body-file body.html --html \
  --attach "Desktop\Largepayment\Large Payment Authorisation - [date].docx"
```

`--cc` takes every address after ONE flag — repeating `--cc` silently drops
earlier recipients. Read the `sent=1 ... cc=...` echo line to confirm who
actually got it.

**Always show Prathap the full draft first and wait for an explicit "send"** —
this is a CEO-facing payment authorisation with real money and real people's
names in it; never fire it on assumption, even though he is the CFO and can
authorise it himself.

## Step 4b — Exceptions / data-quality flags go to Wangu & Kago, NOT the CEO

Any Graphite findings (status mismatches, placeholder names, invoice date
discrepancies, missing AOLs, salvage not confirmed, one-thebe changes, etc.)
do NOT go in the CEO email. Instead, send a **separate urgent email** to:
- **To:** Wangu Moses (wmoses@) and Kago Tshutlhedi (ktshutlhedi@)
- **Cc:** Paul Beka (pbeka@)
- **Subject:** "URGENT: Claims queries before payment release – [date]"
listing the specific questions per claim, with a deadline. Also raise an Omni
task for each person. The CEO email stays clean — just the tables, bank position,
funds statement, declarations, and signatures.

## Standing cc list for these requests

Arun Iyer (aiyer@, CEO, approver — the TO) · **CC always:** Paul Beka (pbeka@) ·
Bontle Tendani (btendani@) · Kago Tshutlhedi (ktshutlhedi@, Finance Manager) ·
Pako Kago (pkago@, Financial Controller) · Wangu Moses (wmoses@, Claims Manager).
Updated 10-Sep-2026 by CFO directive — all five are cc'd on EVERY large-payment
email going forward.

## Pulling payment data from Omni (added 10-Sep-2026)

When Prathap gives FNB batch references (e.g. "MOTOR HOLDINGS HAVAL 000159 (O)")
without amounts or claim numbers, look them up in **Omni's PaymentRequest model**
(app=`taskboard`, model=`PaymentRequest`). Key fields: `subject` (contains claim
number + payee), `total`, `status`, `category` (claim/vendor/other), `line_items`
(JSON array with `claim_number`, `invoice_number`, `invoice_date`, `amount`).

Query via SSM → `docker exec alpha-finance-backend python manage.py shell` with a
base64-encoded script. Search by `subject__icontains` for the payee name. The FNB
batch reference numbers (000159 etc.) are sequential FNB numbers, not stored in Omni.

Relevant statuses: `pending_cfo` = awaiting CFO sign-off (the ones to include),
`paid` = already released, `exception` = held for review, `cancelled` = withdrawn.

## Deeper context

[[p-pay-loadin]] (payment-raising window rules) ·
[[r-gph-clm-tables]] (fuller claims schema) ·
[[f-copy-fmt-verbatim]] · Load **graphite-v2** for the
full ECS-exec/tinker mechanics and **fnb** for how the payment batch data itself
should be read.

## Learned 4-Sep-2026 (second run) — reuse, don't rediscover
- **Builder script:** `build_request.py` in this folder writes the .docx (Book Antiqua, navy/orange) AND the
  full HTML email body from the same row lists. Edit the `secA` / `secB` / `bank` / `nbs` lists, run it, done.
  `pull_claims.php` is the tinker pull (edit `$nums`).
- **Insured COMPANY name** is NOT on `policies.business_name` (null on COMG policies). It is
  `customer.company_id` → **`companies.name`**. `customer.firstName/lastName` is the contact person, not the insured.
- **Payee names:** `claim_reserves.payee` → **`suppliers.id` / `supplierName`** (e.g. 299 Optimum Panel Beaters,
  778 Nors Botswana, 337 Motor Liquidators = assessor, 88 Motor Centre).
- **Amounts:** `claim_reserves_coverages.reserve_id` = `claim_reserves.id`; columns `payment_amt`, `reserve_amt`,
  `balance`, `salvage_reserve`, `write_off` (1 = vehicle written off). `claim_reserves.transaction_type`
  86 = claim registered, 42 = reserve raised, 43 = payment/invoice, 44 = balance released (no payee), 91 = salvage reserve.
- **Approval trail** lives in **`claim_review_notes`** (`created_by_name`, `note`) — Wangu Moses recommends,
  Paul Beka / Lindani Mababa say PROCEED; the settlement arithmetic (SI, valuation, excess, betterment) is in the note text.
  Compare the approved figure there to the amount Finance loaded — on 4-Sep two trailers were approved at 111,592.89
  and loaded at 88,099.65 with no note explaining the difference.
- **`customer.category_reason`** carries the fraud/frequency flags ("80 claims in 18 months", "Total received amount 994%").
- **Watch for one-thebe changes** (88,099.65 vs 88,099.64) on same-payee same-day payments — it defeats the duplicate check.
- **Do NOT query `transactions` or `vehicle` by policy_id in tinker** — no index, the ECS session hangs past 3 minutes.
- Finance's own request now carries a 6-column Bank Position (with Transfer columns). Keep their columns when they exist.
