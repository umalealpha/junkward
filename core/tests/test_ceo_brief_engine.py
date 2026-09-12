"""CEO daily-brief engine — the two faults the CFO reported on 11-Sep-2026.

1. A courtesy "Thanks boss" sitting on top of a quoted payment request was read
   as the request itself and printed as a HIGH customer complaint, recommending
   Wangu phone a customer. Only what the sender wrote today is news.
2. With a single matter, "The One Thing Today" box and the card below it were
   word-for-word the same — the CEO read the same issue twice.

The engine lives in infra/ceo-monitor/ (a host-cron script, not an app), so it
is loaded by path. No LLM and no network here on purpose: the classifier's own
output is the INPUT, because the guard has to hold whatever the model says.

Run: python manage.py test core.tests.test_ceo_brief_engine
"""
import importlib.util
from pathlib import Path

from django.test import SimpleTestCase

_ENGINE = (Path(__file__).resolve().parents[2]
           / "infra" / "ceo-monitor" / "ceo_engine.py")


def _load_engine():
    spec = importlib.util.spec_from_file_location("ceo_engine_under_test", _ENGINE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


E = _load_engine()

#: Exactly the shape Outlook hands us: two words of new text sitting on top of
#: the whole quoted request, amounts and all.
_REPLY = (
    "Payment Authorisation Request for Current Account & Claims Payments"
    " -- Thanks boss\n"
    "\n"
    "From: Prathap Ganesharajah <pganesharajah@alphadirect.co.bw>\n"
    "Sent: 10 September 2026 16:42\n"
    "To: Arun P. Iyer\n"
    "Subject: Payment Authorisation Request\n"
    "\n"
    "Dear Arun, please authorise the attached payment run for current account\n"
    "and claims payments totalling BWP 1,809,400 covering 68 claim settlements."
)


def _item(**kw):
    """The real 11-Sep item: the CFO thanking the CEO for approving a run."""
    defaults = dict(
        id=1,
        title="Payment Authorisation Request for Current Account & Claims "
              "Payments dated 10 September 2026",
        from_addr="pganesharajah@alphadirect.co.bw",
        category="complaint",          # what DeepSeek actually labelled it
        summary=_REPLY,
        confirmed=True,
    )
    defaults.update(kw)
    it = E.QueueItem(**defaults)
    it.severity = "High"
    it.party = "Payment Authorisation Request"
    it.polished_matter = defaults["title"]
    it.polished_why = ("It is a courtesy acknowledgement of an already-approved "
                       "payment run with no new amount, dispute or escalation.")
    return it


class QuotedReplyChainTests(SimpleTestCase):
    def test_new_text_keeps_only_what_the_sender_wrote(self):
        self.assertNotIn("1,809,400", E.new_text(_REPLY))
        self.assertIn("Thanks boss", E.new_text(_REPLY))

    def test_a_pure_forward_is_not_emptied(self):
        fwd = "From: someone@example.test\nThe insured disputes BWP 900,000."
        self.assertIn("900,000", E.new_text(fwd))


class CourtesyAcknowledgementTests(SimpleTestCase):
    def test_thanks_boss_over_a_quoted_request_is_dropped(self):
        """The fault exactly as it reached the CEO on 11-Sep-2026."""
        it = _item()
        E.extract_facts(it)
        E.score_item(it)
        self.assertEqual(it.amount_bwp, 0.0,
                         "an amount inside the quote is not a new amount")
        self.assertEqual(it.score, 0, "a thank-you must score nothing")
        self.assertEqual(it.severity, "Watch")
        # Only matters scoring 40+ are printed, so this never reaches the CEO.
        self.assertLess(it.score, 40)

    def test_thanks_with_a_real_complaint_still_counts(self):
        it = _item(summary=(
            "Thanks, but the client is still not happy and has asked for the "
            "Ombudsman's details.\n\nFrom: someone@example.test\nquoted history"))
        E.extract_facts(it)
        E.score_item(it)
        self.assertGreaterEqual(it.score, 40, "a real complaint must survive")

    def test_thanks_followed_by_an_ask_still_counts(self):
        it = _item(summary="Thanks. Please confirm the NBFIRA return today.")
        E.extract_facts(it)
        E.score_item(it)
        self.assertGreaterEqual(it.score, 40)

    def test_a_long_mail_that_merely_opens_with_thanks_is_not_an_ack(self):
        body = ("Thank you for your email. " + "The insured disputes the "
                "settlement figure and has instructed attorneys. " * 3)
        it = _item(summary=body)
        self.assertFalse(E.is_courtesy_ack(it))


class OneThingDuplicationTests(SimpleTestCase):
    def _digest(self, n):
        d = E.Digest(date="Friday, 11 September 2026", raw_count=n, distinct_count=n)
        for i in range(n):
            it = _item(id=i, summary="The insured disputes BWP 750,000 and has "
                                     "instructed attorneys.")
            it.title = f"Matter {i}"
            it.polished_matter = f"Matter {i}"
            E.extract_facts(it)
            E.score_item(it)
            E.recommend(it)
            d.items.append(it)
        return d

    def test_single_matter_is_printed_once(self):
        html = E.render_html(self._digest(1))
        self.assertNotIn("The One Thing Today", html,
                         "one matter must not be printed as both box and card")
        self.assertIn("Matter 0", html)

    def test_the_box_still_appears_when_there_are_several(self):
        html = E.render_html(self._digest(3))
        self.assertIn("The One Thing Today", html)
