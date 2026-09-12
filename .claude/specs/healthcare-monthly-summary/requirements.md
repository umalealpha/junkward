# Healthcare monthly summary + upload dedupe — requirements

Source: Tlamelo Chimidza email thread "OMNI HEALTH DASHBOARD", reply of 2026-06-10 16:23
(forwarded by CFO with instruction "fix respond"). Screenshots in that email are the
confirmed target layouts.

## R1 — Remove duplicate uploads
Same file uploaded 3× on the Revenue tab double-counts revenue (and the pattern applies
to Claims / Treaty). Users need to delete an upload so exactly one remains per month.
- Only the uploader or an admin may delete.
- Deleting removes the upload's totals from the register and the summaries immediately.

## R2 — Month + YTD summary per tab
Each tab (Revenue / Claims / Treaty) shows a month-by-month table built from the
uploads, plus a YTD row for the current financial year (Jul–Jun) and an
inception-to-date row.
- Revenue: lives, GWP excl. VAT, VAT @14%, GWP incl. VAT, MoM% (screenshot 2).
- Claims: lives, charged, paid, loss ratio vs same-month revenue (screenshot 3).
- Treaty: members, 100% premium/claims, 90% quota-share premium/claims, RI net
  (screenshot 4; Oak Tree brokerage NOT deducted in v1).
- Months still containing >1 upload are flagged so the register can be cleaned (R1).

## R3 — One sheet per upload (convention)
Going forward Tlamelo uploads one sheet per file. No code change needed — the parser
already picks the best data sheet; R2's duplicate flag plus R1's delete keep the
register clean. Communicated in the email reply.

## Out of scope (v1)
- Narrative columns (Notes / Primary Driver / Settled status) — manual commentary.
- Brokerage, VAT-on-brokerage, settlement status tracking on treaty.
- A combined Health Care landing page (separate feature, already promised separately).
