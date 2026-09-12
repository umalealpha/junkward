# Manus Runbook — Deploy Healthcare Vendor Onboarding to omni

**For: Manus AI.** Target: omni prod EC2 `i-02a5d76a61f4f09a5` (af-south-1),
`omni.alphadirect.co.bw` / 13.245.255.206. Code at `/opt/alpha-finance`.
Goal: ship the `healthcare` vendor-onboarding backend (Ankete-only), apply the
new migration, and live-verify the agreement email to AFA.

## 0. Pre-flight (local, by the developer)
Branch + commit the new files, push, open PR:
```
cd ~/work/alpha-finance
git checkout -b feat/healthcare-vendor-onboarding
git add healthcare/ alpha_finance/api_router.py .claude/specs/healthcare-vendor-onboarding/
git commit -m "feat(healthcare): Ankete-only vendor onboarding + AFA agreement email via omni Graph"
git push -u origin feat/healthcare-vendor-onboarding
```
New files: `healthcare/{models,permissions,vendor_extract,agreement_pdf,vendor_views,admin}.py`,
`healthcare/agreement_text.txt`, `healthcare/afa-logo.png`,
`healthcare/migrations/0001_initial.py`, router edit.

## 1. Deploy on EC2 (Manus — needs Instance Connect)
```
# EC2 Instance Connect to i-02a5d76a61f4f09a5
cd /opt/alpha-finance && sudo -u ubuntu git fetch && sudo -u ubuntu git checkout feat/healthcare-vendor-onboarding && sudo -u ubuntu git pull
sudo docker compose --env-file /etc/alpha-finance/.env build backend
sudo docker compose --env-file /etc/alpha-finance/.env up -d
# entrypoint auto-runs migrate -> applies healthcare/0001_initial
```

## 2. Confirm config (EC2)
```
# DeepSeek already used by the health quick-quote — confirm key present:
grep -q DEEPSEEK_API_KEY /etc/alpha-finance/.env && echo "DEEPSEEK ok" || echo "MISSING DEEPSEEK_API_KEY"
# Ankete-only allowlist defaults to {ankete}. To broaden, add to .env:
#   VENDOR_ONBOARDING_ALLOWED_LOCALPARTS=ankete
# Graph mail (MicrosoftGraphEmailBackend) already live — no SMTP needed.
sudo docker compose exec backend python manage.py check        # must be clean
sudo docker compose exec backend python manage.py showmigrations healthcare  # 0001 [X]
```

## 3. LIVE verification (this is the real test — do all)
1. **Access gate:** as a NON-allowlisted @alphadirect.co.bw user, POST to
   `/api/v1/health/vendor-onboarding/submit/` → expect **403**.
2. **Ankete path:** Ankete logs in via SSO (her email creds), then submit a
   test vendor payload to `/submit/`:
   - expect `201 {reference_number, agreement_email_sent:true}`
   - a `VendorOnboarding` row exists with status `pending_review`
   - the **agreement PDF email lands at ankete@ + mtlagae@** (EXCO auto-CC'd),
     attachment `agreement-<ref>.pdf` opens = full AFA agreement, blanks filled.
3. **DeepSeek extract:** POST a CIPA PDF/text to `/extract/` → returns
   `{fields:[…], deepseek_used:true}` (or `false` + regex fallback if the key is
   down — both acceptable, never 500).
4. Tail logs: `sudo docker compose logs backend | grep vendor-onboarding`.

## 4. Email Alana the how-to (on go-live)
Alana = Alana Nkete = `ankete@alphadirect.co.bw` (same person who has portal
access). Send the ready-made how-to (`alana-howto-email.html`) via omni Graph:
```
sudo docker compose exec backend python manage.py shell -c "
from core.notifications import send_html_with_cfo_cc
html = open('/opt/alpha-finance/.claude/specs/healthcare-vendor-onboarding/alana-howto-email.html').read()
print(send_html_with_cfo_cc(
    subject='Your new Vendor Onboarding portal — how to use it',
    html=html, to=['ankete@alphadirect.co.bw'], cc=['mtlagae@alphadirect.co.bw']))
"   # expect 1; excoboard@ auto-CC'd
```
Send only AFTER §3 live tests pass (don't tell her it's ready before it is).

## 5. Frontend (next build session, with the omni React stack)
Add omni **Healthcare → Vendor Onboarding** page (multi-step form mirroring the
PWA: consent → entity → tax → directors → credentials → banking → services →
AFA agreement (full text) → declaration/sign → review). Calls `/extract/` and
`/submit/`. Browser-smoke-test per `post-deploy-checklist.md` before sign-off.
Gate the menu item to Ankete (same allowlist).

## Rollback
`git checkout main` on the EC2, rebuild backend, up -d. Migration `0001` only
ADDS a table (`healthcare_vendoronboarding`) — safe; drop the table if a full
revert is required.
```
