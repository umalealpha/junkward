# Morning Ops — Prevention Rules

Dated entries only. Each entry: the mistake, the plain-English rule to stop it happening again, and the one command that catches it. Written by the 4am cloud ops check, from commit messages and the MACHINE-TALK.md shared log.

---

## 2026-09-11

**Source window:** MACHINE-TALK.md lessons from the last two weeks, plus every commit on `main` dated 2026-09-10 (this clone's own git history only goes back to 2026-09-10, so commit-message mining could not cover a full 14 days — see the morning report for that day).

### 1. A button that looks fine but is quietly dead (hand-built login header)
**What keeps happening:** Someone writes a direct web request from scratch instead of using the shared "how do I talk to the server" helper, and hand-types the login header on it. The header is subtly wrong — it works for some logins but not others (for example, single-sign-on users). Nothing in the automated tests catches this, because the tests don't check real logins. The button then sits on the live site looking completely normal and does nothing when pressed.
**Seen again:** Yes — twice in two days. Once on 10 September (the "I'm running late" button), and again on 11 September (a new pop-up message feature).
**Prevention rule:** Never hand-type the login header on a request. Always use the shared helper that already knows how to log every kind of user in correctly.
**One command to catch it:** `grep -rn "Authorization.*Bearer\|Authorization.*Token" frontend/src --include="*.ts" --include="*.tsx" | grep -v "lib/api.ts"` — any hit outside the shared helper file is a hand-built header and needs fixing before it ships.

### 2. A save that doesn't tell the page what it just saved (missing id)
**What keeps happening:** A new record gets created, but the response sent back to the screen leaves out the record's own reference number. The screen doesn't know what it just made, sends the user to a broken page, and — because the flow depends on that reference number — the record never reaches the person who was supposed to approve it.
**Seen again:** Yes — on 10 September this broke Purchase Orders for everyone: a new purchase order saved, but never reached its approver. The same day it was found lurking in three more places (Petty Cash, Fixed Assets, Goods Receipts) before anyone pressed the button and noticed.
**Prevention rule:** Every "create a new record" screen must get the record's reference number back immediately, and that must be checked before the code ships, not discovered by a user hitting a dead page.
**One command to catch it:** `python manage.py test core.tests.test_create_serializers_return_id` — this test already exists in the repository and walks every "create" screen checking the reference number comes back; run it before every deploy.

### 3. A date read as UTC when it should be Botswana's date
**What keeps happening:** Code asks the computer's clock for "today's date" using the international standard clock (UTC) instead of Botswana's own clock. Botswana is two hours ahead, so for two hours every night (22:00 to midnight UTC), the computer's idea of "today" is wrong — it still thinks it's yesterday. Anything that checks "did this happen today" turns falsely red in that window.
**Seen again:** Yes — a large fix went out on 10 September (232 lines across 140 files), and the same mistake still caused fresh problems on 11 September in a different corner of the code, including a safety check that was silently looking at the wrong date and could never have caught the bug it was built to catch.
**Prevention rule:** Never ask the computer's own clock for "today" when the answer needs to be Botswana's today. Always go through the one shared "Botswana date" function.
**One command to catch it:** `python manage.py test core.tests.test_botswana_clock` — the repository's own clock guard test; run it, and also re-run the full test suite once between 22:00 and 23:59 UTC specifically, since that is the only window the bug shows itself in.

### 4. Treating "the code is on the server" as "the change is live"
**What keeps happening:** The updated code is pulled onto the live server, but the running program itself (the "image") is never rebuilt from that code. The old, unfixed version keeps running. Everyone believes the fix shipped because the file is visibly there — it just isn't being used.
**Seen again:** Yes — on 10 September, a reporting page was fixed in the code but the running program was never rebuilt, so the page kept failing in production until someone rebuilt it properly during a later deploy.
**Prevention rule:** "The file is on the server" is not proof of anything. A change only counts as live once you have checked the actual working page or a live web address and watched it behave correctly with your own eyes (or a screenshot).
**One command to catch it:** `curl -s -o /dev/null -w "%{http_code}\n" https://<live-site>/<the-changed-page-or-api>` immediately after any deploy — confirm it returns success (200), not a routing error (404), against the real live address.

---

*This file is appended to by the automated 4am ops check. Each new day's findings go in a new dated section above this line.*
