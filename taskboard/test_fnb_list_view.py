"""View tests for payment_request_reconcile_fnb_list — the "Close paid (FNB list)"
endpoint (CFO directive 2026-09-06).

Runs against the CI Postgres test DB (not Windows sqlite). The PDF parser is mocked
(it has its own unit tests in fnb/test_fnb_list_reconcile.py); this exercises the
VIEW: role gate, preview-writes-nothing, SoD skip, status scoping (EXCEPTION /
PENDING_FINANCE / DRAFT never touched), race/failed accounting, and parser-error path.
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import NoReverseMatch, reverse
from rest_framework.test import APIClient

from taskboard import payment_views as pv
from taskboard.models import PaymentRequest

User = get_user_model()
S = PaymentRequest.Status
ENTRIES = [{'name': 'ON LIST LTD 000777 (O)', 'amount': '100.00', 'onum': '000777'}]
PARSE = 'fnb.fnb_list_reconcile.parse_fnb_pending_list'


def _url():
    try:
        return reverse('v1-payment-request-reconcile-fnb-list')
    except NoReverseMatch:
        return '/api/v1/payment-requests/reconcile-fnb-list/'


class FnbListViewTests(TestCase):
    def setUp(self):
        def mk_user(u, e):
            return User.objects.create_user(username=u, email=e, password='x')
        self.cfo = mk_user('pganesharajah', 'pganesharajah@alphadirect.co.bw')
        self.pako = mk_user('pkago', 'pkago@alphadirect.co.bw')
        self.kago = mk_user('ktshutlhedi', 'ktshutlhedi@alphadirect.co.bw')
        self.clerk = mk_user('clerk', 'clerk@alphadirect.co.bw')

        def mk(ref, status, total, approver=None, payee='Some Vendor'):
            return PaymentRequest.objects.create(
                ref=ref, subject=ref, payee=payee, total=Decimal(total), status=status,
                first_approver=approver, entity='ADIC', created_by=self.clerk)
        self.exc = mk('PAY/T/0001', S.EXCEPTION, '50.00', self.pako)
        self.fin = mk('PAY/T/0002', S.PENDING_FINANCE, '60.00')
        self.draft = mk('PAY/T/0003', S.DRAFT, '70.00')
        self.own = mk('PAY/T/0004', S.PENDING_CFO, '80.00', self.pako)      # Pako signed this off
        self.other = mk('PAY/T/0005', S.PENDING_CFO, '90.00', self.kago)
        self.onlist = mk('PAY/T/0006', S.PENDING_CFO, '100.00', self.kago, payee='ON LIST LTD')
        self.c = APIClient()

    def _post(self, user, mode, entries=ENTRIES, raise_exc=None):
        self.c.force_authenticate(user)
        f = SimpleUploadedFile('fnb.pdf', b'%PDF-1.4 not really a pdf', content_type='application/pdf')
        kw = {'side_effect': raise_exc} if raise_exc else {'return_value': entries}
        with patch(PARSE, **kw):
            return self.c.post(_url(), {'file': f, 'mode': mode}, format='multipart')

    def _st(self, p):
        return PaymentRequest.objects.get(pk=p.pk).status

    def _non_queue_rows_untouched(self):
        self.assertEqual(self._st(self.exc), S.EXCEPTION)
        self.assertEqual(self._st(self.fin), S.PENDING_FINANCE)
        self.assertEqual(self._st(self.draft), S.DRAFT)
        self.assertEqual(self._st(self.onlist), S.PENDING_CFO)

    # -- gate --------------------------------------------------------------------
    def test_clerk_refused_403(self):
        r = self._post(self.clerk, 'apply')
        self.assertEqual(r.status_code, 403, r.content)
        self._non_queue_rows_untouched()
        self.assertEqual(self._st(self.own), S.PENDING_CFO)
        self.assertEqual(self._st(self.other), S.PENDING_CFO)

    # -- preview -----------------------------------------------------------------
    def test_preview_scope_counts_and_no_writes(self):
        r = self._post(self.cfo, 'preview')
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        self.assertEqual(d['mode'], 'preview')
        self.assertEqual(d['entries_read'], 1)
        self.assertEqual(d['keep_count'], 1)
        self.assertEqual(d['close_count'], 2)          # CFO exempt from SoD
        self.assertEqual(d['skipped_count'], 0)
        self.assertEqual(d['close_total'], '170.00')
        self.assertEqual(d['not_loaded_in_close'], 2)
        self.assertEqual(d['rejected_in_close'], 0)
        self.assertEqual({x['ref'] for x in d['would_close']}, {'PAY/T/0004', 'PAY/T/0005'})
        self.assertEqual({x['ref'] for x in d['would_keep']}, {'PAY/T/0006'})
        self.assertTrue(all(x['not_loaded'] for x in d['would_close']))
        self.assertEqual(d['would_close'][0]['currency'], 'BWP')
        # wrote nothing
        self.assertEqual(self._st(self.own), S.PENDING_CFO)
        self.assertEqual(self._st(self.other), S.PENDING_CFO)
        self._non_queue_rows_untouched()

    def test_preview_sod_for_approver(self):
        d = self._post(self.pako, 'preview').json()
        self.assertEqual(d['skipped_count'], 1)
        self.assertEqual(d['close_count'], 1)
        self.assertEqual({x['ref'] for x in d['skipped_own']}, {'PAY/T/0004'})
        self.assertEqual({x['ref'] for x in d['would_close']}, {'PAY/T/0005'})

    # -- apply -------------------------------------------------------------------
    def test_approver_apply_skips_own_signoff_never_touches_exception(self):
        r = self._post(self.pako, 'apply')
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        self.assertEqual(d['mode'], 'apply')
        self.assertEqual(d['skipped_count'], 1)
        self.assertEqual(d['closed_count'], 1)
        self.assertEqual(d['closed_total'], '90.00')
        self.assertEqual(d['kept_count'], 1)
        self.assertEqual(d['not_loaded_closed'], 1)
        self.assertEqual([x['ref'] for x in d['closed']], ['PAY/T/0005'])
        self.assertNotIn('failed_count', d)
        self.assertEqual(self._st(self.other), S.PAID)
        self.assertEqual(self._st(self.own), S.PENDING_CFO)   # SoD: left for CFO / other approver
        self._non_queue_rows_untouched()
        notes = PaymentRequest.objects.get(pk=self.other.pk).decision_notes
        self.assertIn('upload FNB list', notes)
        self.assertIn('Reversible', notes)

    def test_cfo_apply_closes_all_not_on_list_and_is_idempotent(self):
        r = self._post(self.cfo, 'apply')
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        self.assertEqual(d['closed_count'], 2)
        self.assertEqual(d['closed_total'], '170.00')
        self.assertEqual(d['skipped_count'], 0)
        self.assertEqual(self._st(self.own), S.PAID)
        self.assertEqual(self._st(self.other), S.PAID)
        self._non_queue_rows_untouched()
        r2 = self._post(self.cfo, 'apply').json()
        self.assertEqual(r2['closed_count'], 0)
        self.assertEqual(r2['closed_total'], '0.00')
        self.assertEqual(r2['kept_count'], 1)

    def test_row_that_left_queue_is_failed_not_closed_and_not_overwritten(self):
        real = pv._mark_paid_from_bank

        def racing(p, user, reason, **kw):
            if p.pk == self.other.pk:   # another action moved it a moment before us
                PaymentRequest.objects.filter(pk=p.pk).update(status=S.CANCELLED)
            return real(p, user, reason, **kw)

        with patch.object(pv, '_mark_paid_from_bank', side_effect=racing):
            r = self._post(self.cfo, 'apply')
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        self.assertEqual(d['closed_count'], 1)
        self.assertEqual(d['closed_total'], '80.00')            # not 170
        self.assertEqual(d.get('failed_count'), 1)
        self.assertEqual(d['failed'][0]['ref'], 'PAY/T/0005')
        self.assertIn('cancelled', d['failed'][0]['error'])
        self.assertEqual(self._st(self.other), S.CANCELLED)     # NOT overwritten to PAID

    def test_helper_exception_raised_mid_loop_is_recorded_and_others_still_close(self):
        real = pv._mark_paid_from_bank

        def boom(p, user, reason, **kw):
            if p.pk == self.own.pk:
                raise RuntimeError('db hiccup')
            return real(p, user, reason, **kw)

        with patch.object(pv, '_mark_paid_from_bank', side_effect=boom):
            d = self._post(self.cfo, 'apply').json()
        self.assertEqual(d['closed_count'], 1)
        self.assertEqual(d['failed_count'], 1)
        self.assertEqual(d['failed'][0]['ref'], 'PAY/T/0004')
        self.assertEqual(self._st(self.own), S.PENDING_CFO)
        self.assertEqual(self._st(self.other), S.PAID)

    # -- parser failure paths ----------------------------------------------------
    def test_unreadable_file_400_closes_nothing(self):
        r = self._post(self.cfo, 'apply',
                       raise_exc=ValueError('3 line(s) in that PDF look like payments but could not be read'))
        self.assertEqual(r.status_code, 400)
        self.assertIn('could not be read', r.json()['detail'])
        self.assertEqual(self._st(self.own), S.PENDING_CFO)
        self.assertEqual(self._st(self.other), S.PENDING_CFO)

    def test_pdf_lib_crash_400_closes_nothing(self):
        r = self._post(self.cfo, 'apply', raise_exc=RuntimeError('pdfplumber exploded'))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self._st(self.own), S.PENDING_CFO)

    # -- the underlying close helper's own guard ---------------------------------
    def test_helper_refuses_non_pending_cfo_directly(self):
        self.assertIsNone(pv._mark_paid_from_bank(self.exc, self.cfo, 'x'))
        self.assertEqual(self._st(self.exc), S.EXCEPTION)
        self.assertIsNone(pv._mark_paid_from_bank(self.fin, self.cfo, 'x'))
        self.assertEqual(self._st(self.fin), S.PENDING_FINANCE)
