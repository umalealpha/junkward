---
name: jenamo
description: Jenamo Abueng / Centric Sure — union insurance distribution deals. Auto-load when Prathap types /jenamo, says "Jenamo", "Centric Sure", "BOPRITU", or "union agreement". Covers the broker relationship, commission structures, agreements built, and what's pending.
---

# Jenamo Abueng — Centric Sure (Pty) Ltd

**Who:** Jenamo Abueng, Director of Centric Sure (Pty) Ltd — an insurance broker/distributor in Botswana.
**Email:** jabueng@centricsure.co.bw
**Relationship:** Introduces trade unions to Alpha Direct for group insurance schemes. He brings the union, Alpha Direct underwrites.

## Products offered through Centric Sure

| Product | Description |
|---|---|
| Mobile Device Insurance | Accidental damage, theft, loss — banded by device value |
| Legal Insurance | Legal expenses cover — panel attorney is **Ms Gape April** (5% fee on legal premium) |
| Hospital Cashback Insurance | Cash per day in hospital, up to BWP 25,000 |

## Key commercial principle — Jenamo's commission is HIDDEN from unions

Jenamo does NOT want unions to know he earns commission. Total cap per product is 15%. So each union deal has TWO agreements:
1. A union-facing agreement (Alpha Direct ↔ Union) showing only the union's fee + attorney fee
2. A confidential commission agreement (Alpha Direct ↔ Centric Sure) showing Jenamo's cut

## Agreements

### 1. Centric Sure Master Distribution Agreement (SUPERSEDED by split approach)
- **Type:** Two-party (Alpha Direct ↔ Centric Sure)
- **Status:** Original DRAFT sent 19-Aug-2026 — now superseded by per-union commission agreements
- **File:** `Desktop\DRAFT - Insurance Distribution Agreement - Centric Sure.docx`

### 2. BOPRITU Scheme — Union Agreement (what BOPRITU sees)
- **Type:** Two-party (Alpha Direct ↔ BOPRITU)
- **Union:** Botswana Primary Teachers Union (BOPRITU)
- **Union address:** Plot 10427, Opp Motovac, along Old Lobatse Rd, P O Box 402923, Gaborone
- **Union signatory title:** Executive Secretary General (name TBC)
- **Status:** DRAFT v2 sent to Jenamo on **24-Aug-2026**
- **File:** `Desktop\DRAFT - Insurance Distribution Agreement - BOPRITU Scheme.docx`
- **Build script:** `scratchpad\build_bopritu_v2.py`
- **Commission visible to union:**

| Product | BOPRITU (collection fee) | Panel Attorney | Total visible |
|---|---|---|---|
| Legal Insurance | 5% | 5% | 10% |
| Mobile Device | 5% | — | 5% |
| Hospital Cashback | 5% | — | 5% |

- Centric Sure mentioned ONCE as "introducing distributor" in preamble — NOT a party, NOT a signatory
- BOPRITU's 5% labelled "collection and administration fee" (not commission) — they're a collection agent, not intermediary

### 3. BOPRITU Scheme — Centric Sure Commission Agreement (CONFIDENTIAL)
- **Type:** Two-party (Alpha Direct ↔ Centric Sure) — Jenamo's private commission
- **Status:** DRAFT sent to Jenamo on **24-Aug-2026** as CONFIDENTIAL
- **File:** `Desktop\DRAFT - Distribution Commission Agreement - Centric Sure - BOPRITU Scheme.docx`
- **Build script:** `scratchpad\build_centric_commission.py`
- **Jenamo's commission:**

| Product | Centric Sure commission |
|---|---|
| Legal Insurance | 5% |
| Mobile Device | 10% |
| Hospital Cashback | 10% |

- Linked to the BOPRITU Agreement — auto-terminates if that ends
- Strictly confidential — terms never disclosed to BOPRITU

### Full commission breakdown (15% cap across both agreements)

| Product | BOPRITU | Gape (attorney) | Jenamo/Centric | Total |
|---|---|---|---|---|
| Legal Insurance | 5% | 5% | 5% | 15% |
| Mobile Device | 5% | — | 10% | 15% |
| Hospital Cashback | 5% | — | 10% | 15% |

### BONU (existing — the original template)
- **Signed:** October 2024 by Arun P. Iyer (CEO) and Peter Motswagole Baleseng (BONU President)
- **Source file:** `Desktop\Archive\15_Uncategorized\BONU.docx`
- **Terms:** BWP 75/month, BWP 80,000 legal cover, 15% admin fee to BONU, 2+5 year auto-renewal

## Timeline
- **Friday 29-Aug-2026:** Executive around for signing
- **Still need from Jenamo:** Centric Sure's physical address/phone, BOPRITU's phone/email, Executive Secretary General's full name

### BONU (existing — the template)
- **Signed:** October 2024 by Arun P. Iyer (CEO) and Peter Motswagole Baleseng (BONU President)
- **Source file:** `Desktop\Archive\15_Uncategorized\BONU.docx`
- **Terms:** BWP 75/month, BWP 80,000 legal cover, 15% admin fee to BONU, 2+5 year auto-renewal, exclusivity, 9,000 member threshold
- **Banking:** FNB account 62403392335

## Panel Attorney
- **Ms Gape April** — legal practitioner on Alpha Direct's panel
- Earns 5% of gross premium on Legal Insurance only
- This is Alpha Direct's cost — separate appointment, not part of the distribution agreement
- Mentioned in BOPRITU agreement Schedule 3 for transparency

## Other deliverables sent to Jenamo
1. **Mobile Device Insurance Proposal** (.docx + .pdf) — pricing, benefits, commission structure
2. **Legal & Healthcare Rate Pack** (.docx + .pdf) — legal and hospital cashback live rates
3. Both built with `brand.py` (Alpha Direct branded Word docs)

## Regulatory citations used in agreements
- Insurance Industry Act (Cap 46:01)
- NBFIRA Act (Cap 46:08)
- Data Protection Act, 2018 (Act No. 32 of 2018) + IDPC
- Financial Intelligence Act (Cap 08:07)
- Trade Unions and Employers' Organisations Act (Cap 48:01)

## Build tools
- **`brand.py`** — Alpha Direct brand helper for python-docx (Navy #1D3270, Orange #F47C20, Calibri, logo)
- **`send_mail_attach.py`** — Graph sender, one attachment per call, always pass `--html`
- **`docx2pdf`** — pip package for Word→PDF conversion
- All agreements reviewed with `/deepseek` (DeepSeek-reasoner via local cost gateway on :4000)

## Pending
- Jenamo to confirm Centric Sure address, BOPRITU contact details, exec name
- Final execution copies once details received
- Financial model email to Jenamo (built but never sent — CONFIDENTIAL internal pricing, needs CFO go-ahead)
- Validate claims assumptions (13.5% frequency, 27.5% severity) against Graphite real data
