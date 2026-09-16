---
layout: home
title: Omni
---

# Omni

Omni is the internal ERP of **Alpha Direct Insurance Company (Pty) Ltd**, Botswana.
It runs premium billing, claims payments, broker commissions, payroll, HRIS,
bank reconciliation, IFRS 17 reporting and the integrations with the Graphite
policy system.

| Layer | Technology |
|---|---|
| Backend | Python 3.13, Django 5.2, Django REST Framework |
| Database | PostgreSQL 16 |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Deployment | Docker Compose, blue/green cut-over |

## Documentation

- [FNB Botswana banking integration](fnb-integration.md)
- [Graphite ⇄ Omni payment-transaction feed](graphite-omni-payment-integration.md)
- [Salvage Portal operating manual](salvage-portal.md)
- [ADI vs ADIC entity disambiguation](ADI-vs-ADIC-disambiguation.md)
- [Source-to-Ledger Reconciliation Hub spike findings](Source_to_Ledger_Recon_Hub_Spike_Findings.md)
- [HRIS amendments how-to](hris-amendments-howto.html)
- [Bug-fix report, 7 June 2026](bug-fix-report-2026-06-07.html)

## Running the system

1. Copy `.env.example` to `.env` at the repo root and fill in your own values.
2. Run `docker compose up`.
3. Read `DOCKER-SETUP.md` at the repo root for the full walkthrough.

## Building this site locally

Ruby 3.x is required.

```bash
cd docs
bundle install
bundle exec jekyll serve
```

The site is then at `http://localhost:4000/`. On GitHub the site is built and
published automatically by the **Pages** workflow on every push to `main` that
touches `docs/`.
