---
name: fnb
description: >
  How Alpha Direct's FNB banking actually works — the Online Banking Enterprise
  portal (payment approval, dual authorisation, FOREX / Global Payments), the
  omni↔FNB API, and the bulk-upload file. Auto-load whenever Prathap types
  "/fnb", or the task touches: approving/authorising a payment in FNB, a forex
  or international/SWIFT payment, BoP codes, payment cut-off times, FNB payment
  statuses, FNB user profiles/administrators, reconciling omni's payment-request
  queue against the bank, or "is this paid or not". Carries the exact status
  ladder (Authorised ≠ Paid), the 3-step forex flow, the traps, and ADIC's own
  account/profile facts. Companion to `omni` (the ERP) and `Payroll`.
  Keep CURRENT STATE + OPEN ITEMS updated.
---

# FNB — Alpha Direct

## 0. RULE ZERO — four different things get called "FNB". Never conflate them.

| # | Thing | What it is | Does money move here? |
|---|-------|-----------|----------------------|
| 1 | **Omni payment-request queue** (`omni.alphadirect.co.bw/payment-requests`) | Alpha Direct's own internal approval workflow. Ends at "CFO authorisation". | **NO.** Purely a record. |
| 2 | **FNB Online Banking Enterprise portal** (`online.fnbbotswana.co.bw`, CLID **1893471**) | The real bank. Where Prathap actually authorises payments. | **YES.** This is the money gate. |
| 3 | **omni ↔ FNB API** (`fnb` Django app, ISO20022 pain.001) | Machine-to-machine. Auth + statement pull are LIVE. | **Payments: never once accepted.** See [[p-payr-fnb-autopa]]. |
| 4 | **FNB bulk-payment upload file** (Excel/CSV template) | Manual file loaded into the portal. Recipient name is **truncated at 20 chars**. | Only after portal authorisation. |

**THE #1 MISTAKE (made 2026-08-03):** treating omni's queue as evidence of what is unpaid.
Prathap paid the India forex payment directly in FNB; omni still showed it "Pending CFO
authorisation" because nobody clicked **"Done — mark as paid"** in omni. Paying in the bank
does **not** close the omni record — they are two separate systems with no live link.
→ **Never say a payment is outstanding on the strength of omni's queue alone.** Say
"omni still has it open" and ask, or check the bank.

---

## 1. Payment status ladder (Online Banking Enterprise)

Exact labels, in order. **Memorise the two lines in bold — they are where people get it wrong.**

| Status | Means |
|--------|-------|
| `Work In Progress` | Created, not yet submitted for authorisation |
| `Authorisation Requested` | Submitted, nobody has authorised yet |
| `Updating Status` | Temporary, large batch being validated |
| `Partially Authorised` | Some but not all required authorisers have signed |
| **`Authorised`** | **Fully authorised, "ready for payment" — MONEY HAS NOT MOVED** |
| `Submitted for Processing` | Sent to the back end, awaiting response |
| `Pay & Clear Now – Pending` | Real-time batch, awaiting each recipient bank |
| **`Fully Processed`** | **All items processed — this is the only "paid" status** |
| `Partially Processed` | Some items failed (view Failed Items) |
| `Processing Failed` | All items failed |
| `Unsuccessful` | Failed on back-end processing error |
| `Funds Unavailable` | Failed for funds — can be reprocessed |
| `Settlement Limit Exceeded` | Over the online settlement limit; RM must raise the limit |
| `Dated Service – Fully/Partially Processed` | 1- or 2-day service; **check again on action date** |
| `Recurring Payment` | Stays this way until the final instalment |

**`Authorised` ≠ paid. `Fully Processed` = paid.** Same trap as the API's
`HTTP 200 ≠ paid` (there you must read `groupStatus`, not the HTTP code).

---

## 2. Local (BWP) payment approval — the normal flow

1. **Capture** — a user with capture permission creates the payment.
2. **Submit** — Payments tab → Menu → *Submit Payment Instruction*. Status goes
   `Work in Progress` → `Authorisation Requested`.
3. **Authorise** — Payments tab → viewing option **`Authorisation Needed`** → tick the
   payment → **Authorise**. Confirm with Digital Certificate (upload + password) or
   Personal Security Key (plug in + PIN), then accept the review disclaimer.
   - Alternative path: Payments tab → Menu → *Authorise Payment Instruction*.
4. **De-Authorise** exists — reverts to `Work in Progress` so it can be corrected.
   Only authorisers can de-authorise.

**Dual control:**
- Up to **9** authorisers can be required; FNB recommends a minimum of two.
- **A & B signatory levels.** At least one **'A' level** authoriser must be involved in
  authorising Folders, Payments, Once-Off Payments, Collections and Transfers.
- The administrator sets how many authorisers a site needs.
- Full audit trail / Event Log on every action; rejection reasons are recorded and shown
  wherever the Authorisation Audit Trail appears.

---

## 3. FOREX / Global Payments — THREE steps, not two

This is the part that differs most from local payments, and the part Prathap asked about.
Path: **Forex tab → Global Payments sub-tab**.

### Step A — Capture the application
Once-off view, or pay a saved Global Beneficiary. Captures: settlement account, currency,
amount, references, **charge option** (who pays the SWIFT charges) and the account to
debit those charges to, beneficiary type (Individual / Business), beneficiary details.

### Step B — Regulatory reporting (BoP) — mandatory
- Select a **Balance of Payments (BoP) Category**, then a **BoP Code**. Searchable by
  category code or keyword.
- Extra fields may appear depending on the code: **Exchange Control Authority**, BoP
  specific details, **third-party details**.
- **Split reporting:** if the payment needs multiple BoP codes, multiple **Movement
  Reference Numbers (MRN)** or invoice numbers, or has multiple third parties, capture
  each BoP code separately. **The amounts across all codes must sum exactly to the
  payment total.**
- Then accept the **Regulatory Declaration** + Terms and Conditions.
- **Document upload:** depending on the BoP code, Exchange Control may require supporting
  documents. Forex tab → **Document Upload** sub-tab. PDF/JPEG/TIFF/GIF only, **max 4MB
  per file**. Documents only reflect once FNB/RMB has processed them. If docs are
  outstanding, History shows status **`Documents Required`**.

### Step C — Authorise, then **PROCESS** (this extra step is forex-only)
1. **Authorise:** viewing option `Authorisation Needed` → tick → **Authorise**
   (Digital Certificate or PSK). Status → `Partially Authorised` → **`Fully Authorised`**.
   Reject requires a typed reason, which is stored on the audit trail.
2. **Process:** only once **Fully Authorised**, a user with **Process Forex Application**
   permission goes to the **`Process Payment`** viewing option → **Get Quote**.
   - **You have 120 seconds (2 minutes) to Accept or Decline the quote.**
   - Decline → you must give a reason (statistical) and the application is parked back in
     **Create + Maintain**.
   - Accept → submitted for processing, appears under **History**.
3. If a rate was **pre-booked** with an FNB/RMB dealer, a **Deal Allocation** step appears
   instead — allocate amounts across deals; unallocated amounts get the spot rate at
   time of quoting.

### FOREX TRAPS — all four are real and all four bite
1. **No name/account validation.** FNB explicitly does **no** validation of the beneficiary
   account *name* against the account *number* on forex payments. A wrong account number
   pays a stranger and there is no safety net. Local payments are not this exposed.
2. **Funds leave immediately; the beneficiary waits 2–4 days.** The debit hits your
   account at once, but the transaction takes 2 to 4 days to process. So "it's gone from
   my account" does **not** mean "they've received it" — and vice versa, a supplier
   chasing after 1 day is normal.
3. **A converted BWP figure is not the booked figure.** The BWP amount on an internal
   request is an estimate. Whatever rate FNB gives on the day is what hits the ledger.
   If they differ, the FX difference must be posted. **Never reconcile a forex payment on
   the BWP number from the request form.**
4. **The liquidity check on omni's request form points at a BWP account.** For a forex
   payment out of a forex account, that check is meaningless and will throw a false
   **✗ INSUFFICIENT**. Ignore it for forex; do not raise it as a finding. (This is a real
   defect in the omni payment-request template — see OPEN ITEMS.)

### Currencies
- **Botswana Global Payments (per the July 2026 Botswana guide): AUD, EUR, GBP, JPY,
  USD, ZAR.** **INR is NOT on that list.** So an India payment almost certainly goes in
  **USD** via SWIFT, not rupees. Confirm before assuming currency on any India payment.
- Global *Accounts* (a different product, and the guide scopes it to SA residents) cover
  AUD, GBP, CAD, CNY, EUR, INR, CHF, AED, USD — do not confuse the two lists.

### Forex contacts (FNB Botswana)
- **Business forex: +267 370 6440 / businessforex@fnbbotswana.co.bw** ← use this one
- Consumer: +267 370 6443 / onlinedocs@fnbbotswana.co.bw
- FNB Wealth: +267 370 6691 / fx@fnbbotswana.co.bw

---

## 4. Cut-off times (FNB Botswana, Online Banking)

| When | To FNB accounts | To other banks |
|------|-----------------|----------------|
| Mon–Fri | **20h00** | **13h30** |
| Saturday | 20h00 | Next business day |
| Sun / public holidays | Next business day | Next business day |

- Submission is anytime; anything after cut-off is processed the next business day.
- Clearing: FNB→FNB up to **12 hours**; FNB→other banks up to **2 business days**.
- Posting to the recipient happens within 2 business days; the date on the recipient's
  statement is the date *their* bank processed it.
- Daily limits are **cumulative across the App, Cellphone Banking and Online Banking** —
  a payment on the app reduces what's left online the same day.
- FNB reserves the right to delay payments for fraud screening.
- **Alpha Direct's own internal 09:00 payment cut-off is stricter than FNB's** and is a
  house rule, not a bank constraint. Don't cite FNB as the reason for it.
- Cross-border into Namibia/Eswatini/Lesotho **rejects** on public holidays.
- For dated (1-day/2-day) batches, cleared funds must be in the account by **05h00 on the
  release date**, i.e. one day before action date.

---

## 5. ADIC's own FNB facts

- **Portal:** `online.fnbbotswana.co.bw`, **CLID 1893471**.
- **Only two administrators: Arun P Iyer (CEO) and Prathap Ganesharajah (CFO).** Everyone
  else is Role = "User".
- **Profile changes are dual-control too.** The admin who *captures* a user change cannot
  authorise it. A captured change sits as **`Work in Progress`** (new/amended) or
  **`Delete Requested`** (removal) until the *other* administrator clicks **Authorise**.
  → **Never tell Prathap he can finish an FNB access change on his own.**
  → Arun can authorise from the **FNB Banking App on his phone** — offer that route first.
- **Main BWP account:** 62403392335 (FNBB CHEQ), branch **287867**, BIC **FIRNBWGX**,
  account name "Alpha Direct Insurance".
- **Other real accounts:** Call 62407809485, Claims 62493282265, Investment Income
  62493292264, **USD 63167551382**, and 62477854999 (the account omni's payment-request
  form checks liquidity against).
- 63001966639 / branch 250655 is a **sandbox**, inactive. Never use it.
- **FNB/RMB contacts:** Christopher Marumo `Christopher.Marumo@fnbbotswana.co.bw`
  (Commercial), Boitumelo Matsheng `bmatsheng@fnbbotswana.co.bw` (RM),
  Kabelo Sekoto `Kabelo.Sekoto@rmb.co.bw` (RMB, payment-rejection debugging).

---

## 6. Hard boundaries — do not cross these

1. **Never enter FNB credentials, PINs, PSK PINs or certificate passwords.** Not ever, not
   "to test", not if asked directly. Prathap keys those himself.
2. **Never click Authorise / Reject / Accept Quote on a real payment.** That is the money
   gate and it is his signature, not mine.
3. **Never run a real EFT batch through the API to "test the pipe"** — `submit_eft_batch`
   POSTs real money.
4. **Never grant, change or delete FNB user access.** Produce the change-spec for the
   named authoriser instead.
5. Reading balances, statements and payment statuses is fine and encouraged — that's how
   you verify instead of guessing.

---

## 7. How to actually read FNB in a browser session

The Chrome extension can only see tabs **inside its own Claude tab group**. Prathap's
logged-in FNB tab normally sits outside it, so it is invisible.
- **Do not** try to reach online banking by guessing URLs in a fresh tab — the hosts
  `online.fnbbotswana.co.bw` and `www.onlinebanking.fnbbotswana.co.bw` both returned
  error pages from a cold tab on 2026-08-03, and a fresh login could kill his live session.
- **Ask him to add the tab instead:** right-click the FNB tab → *Add tab to group* →
  choose the Claude group. Then read it read-only.

---

## 8. Source confidence — be honest about which is which

| Fact | Source | Confidence |
|------|--------|-----------|
| Cut-off times, clearing, limits | FNB **Botswana** Payment Cut-Off Times (Mar 2020) | Botswana-specific |
| Forex tab, Global Payments, BoP capture, 120s quote, no name validation, 2–4 day settlement, BW currency list, forex phone numbers | FNB **Botswana** Online Banking User Guide (Jul 2026, 302pp) | Botswana-specific |
| Payment status ladder, A&B signatories, 9 authorisers, Authorise/De-Authorise menu paths, 3-step forex Capture→Authorise→Process, Process Forex Application permission | FNB **South Africa** Online Banking Enterprise guide (Feb 2017) | ⚠️ **SA guide — FNB publishes no Botswana OBE guide.** Same platform, so the model holds, but **verify labels against the live BW screen before quoting them to FNB or in a control document.** |
| CLID, administrators, ADIC accounts, contacts | Live verification + CFO, Jun–Jul 2026 | Verified |

⚠️ **One known regional difference:** the SA guide says BoP reporting goes to the **South
African Reserve Bank (SARB)**. In Botswana the reporting authority is the **Bank of
Botswana**. The mechanism (BoP category + code, exchange-control docs) is confirmed in the
Botswana guide; the regulator name is not interchangeable. **Never write SARB in an Alpha
Direct document.**

Guides (re-download rather than trusting these notes if precision matters):
- Botswana user guide: `https://www.online.fnb.co.za/rhelp_0_55/OB_BOTSWANA_Downloads/Downloads/User_Guides/OB_Botswana.pdf`
- Botswana cut-off times: `https://www.online.fnb.co.za/rhelp_0_55/OB_BOTSWANA_Downloads/Downloads/Cut-Off_Times/OB-BW-Pay-Cut-Off-Times.pdf`
- Botswana downloads index: `https://www.online.fnb.co.za/rhelp_0_55/OB_BOTSWANA_Downloads/Downloads.htm`
- SA OBE guide: `https://www.online.fnb.co.za/rhelp_0_15/Downloads/User_Guide/South_Africa.pdf`
- PDFs are binary — extract with `pypdf` before searching; WebFetch alone cannot read them.

---

## CURRENT STATE (2026-08-03)

- **Portal payments: working, and the only route that has ever actually paid.** Prathap
  authorises in FNB directly.
- **API: auth + statements LIVE** (OAuth every 30 min from `15.240.20.178`; 06:00 daily
  statement pull, all 7 accounts). **API payments have NEVER settled** — 10 instructions
  since May 2026, all `groupStatus RJCT`, zero settled. Not an IP problem. Awaiting FNB's
  answer on the real rejection reason and whether client ID **R1G66R** is entitled to
  payment execution on LIVE vs test.
- **Omni's payment-request queue is out of sync with the bank.** As at 2026-08-03 it showed
  11 pending; the India one (PAY/RSA/2026/07/29/0001, BWP 295,240.26, forex) was already
  paid. **The other 10 have not been bank-verified.**

## OPEN ITEMS

1. **Reconcile omni's queue against the bank** and close the ones already paid. 10 requests,
   BWP 789,126.85 nominal, unverified.
2. **Fix the omni payment-request template for forex:** it runs the liquidity check against
   a BWP account and stamps a false ✗ INSUFFICIENT on every foreign payment. It should
   check the settlement account actually being used, or skip the check for forex.
3. **Close the omni↔bank gap properly.** Either a "mark as paid" prompt driven off the daily
   statement pull (auth + statements already work), or accept the queue is advisory only.
   Manual clicking will keep drifting.
4. **Get FNB's answer on API payment rejections** (Christopher Marumo / Boitumelo Matsheng,
   cc Kago Tshutlhedi, Pako Kago, Arun Iyer). Do **not** resubmit blind against a live account.
5. **Verify the SA-sourced labels** in §1–§3 against the live Botswana screen next time the
   portal is open, and mark them Botswana-confirmed.

## Settled 2026-09-04 — the API's "HTTP 425 Too Early. Retry-After 120 seconds"
It is **not a rate limit**. FNB answers 425 on the batch-status (retrieveReport) call for any
instruction it has **not processed yet** — normally a batch still awaiting authorisation on the
bank — because there is no status report to return. A settled batch answers 200 on every poll;
a waiting one answers 425 until the moment it is processed, then exactly one 200. Omni's
`poll_fnb_batches` (*/5 min) counts these as "not yet processed by FNB", not errors. Do NOT add
sleep/retry/back-off or stop-on-425 to that sweep (tried 4-Sep, made it read fewer batches).
