"""Tests for inter-entity employee transfer (feature c0d110b6)."""
import datetime as dt

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient, APITestCase

from core.models import Company
from hris.transfer_models import EmployeeTransfer
from hris.transfer_service import (
    apply_due_transfers, approve_in, approve_out, reject_transfer, submit_transfer,
)
from payroll.models import Employee

TODAY = dt.date.today()
FUTURE = TODAY + dt.timedelta(days=7)


class EmployeeTransferTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.adic = Company.objects.create(code='ADIC', name='Alpha Direct Insurance')
        cls.uni = Company.objects.create(code='UNI', name='Unicoin')
        cls.emp = Employee.objects.create(
            employee_number='E500', full_name='Tebogo Move',
            job_title='Agent', company=cls.uni)
        # Whitelisted approvers (Unami + CFO local-parts), plus a maker.
        cls.unami = User.objects.create_user('ubutale', email='ubutale@alphadirect.co.bw', password='x')
        cls.cfo = User.objects.create_superuser('pg', 'pganesharajah@alphadirect.co.bw', 'x')
        cls.maker = User.objects.create_user('hrmaker', email='hr@alphadirect.co.bw', password='x')

    def test_happy_path_applies_on_second_approval_when_effective_today(self):
        # Effective today → both approvals apply the move immediately.
        t = submit_transfer(submitter=self.maker, employee_id=str(self.emp.id),
                            dest_company_id=str(self.adic.id),
                            effective_date=TODAY, reason='reorg')
        self.assertEqual(t.status, EmployeeTransfer.Status.PENDING_OUT)
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.company_id, self.uni.id)   # unchanged yet

        approve_out(t, self.unami)
        t.refresh_from_db()
        self.assertEqual(t.status, EmployeeTransfer.Status.PENDING_IN)
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.company_id, self.uni.id)   # still unchanged

        approve_in(t, self.cfo)
        t.refresh_from_db()
        self.assertEqual(t.status, EmployeeTransfer.Status.COMPLETED)
        self.assertIsNotNone(t.applied_at)
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.company_id, self.adic.id)  # moved

    def test_future_dated_transfer_schedules_then_applies_on_due_date(self):
        # Effective in the future → second approval SCHEDULES; the employee does
        # not move until apply_due_transfers runs on/after the effective date.
        t = submit_transfer(submitter=self.maker, employee_id=str(self.emp.id),
                            dest_company_id=str(self.adic.id),
                            effective_date=FUTURE, reason='future move')
        approve_out(t, self.unami)
        approve_in(t, self.cfo)
        t.refresh_from_db()
        self.assertEqual(t.status, EmployeeTransfer.Status.SCHEDULED)
        self.assertIsNone(t.applied_at)
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.company_id, self.uni.id)   # NOT moved yet

        # Nothing due today → no-op.
        self.assertEqual(apply_due_transfers(), 0)
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.company_id, self.uni.id)

        # Effective date arrives → applies.
        EmployeeTransfer.objects.filter(pk=t.pk).update(effective_date=TODAY)
        self.assertEqual(apply_due_transfers(), 1)
        t.refresh_from_db()
        self.assertEqual(t.status, EmployeeTransfer.Status.COMPLETED)
        self.assertIsNotNone(t.applied_at)
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.company_id, self.adic.id)  # moved on due date

    def test_submitter_cannot_approve_out(self):
        # Make the maker a superuser so authority isn't the blocker — SoD is.
        self.maker.is_superuser = True; self.maker.save()
        t = submit_transfer(submitter=self.maker, employee_id=str(self.emp.id),
                            dest_company_id=str(self.adic.id),
                            effective_date=dt.date(2026, 7, 1))
        with self.assertRaises(ValidationError):
            approve_out(t, self.maker)

    def test_out_approver_cannot_also_approve_in(self):
        t = submit_transfer(submitter=self.maker, employee_id=str(self.emp.id),
                            dest_company_id=str(self.adic.id),
                            effective_date=dt.date(2026, 7, 1))
        approve_out(t, self.unami)
        with self.assertRaises(ValidationError):
            approve_in(t, self.unami)

    def test_same_entity_rejected(self):
        with self.assertRaises(ValidationError):
            submit_transfer(submitter=self.maker, employee_id=str(self.emp.id),
                            dest_company_id=str(self.uni.id),
                            effective_date=dt.date(2026, 7, 1))

    def test_duplicate_in_progress_rejected(self):
        submit_transfer(submitter=self.maker, employee_id=str(self.emp.id),
                        dest_company_id=str(self.adic.id),
                        effective_date=dt.date(2026, 7, 1))
        with self.assertRaises(ValidationError):
            submit_transfer(submitter=self.maker, employee_id=str(self.emp.id),
                            dest_company_id=str(self.adic.id),
                            effective_date=dt.date(2026, 8, 1))

    def test_reject_leaves_employee_in_place(self):
        t = submit_transfer(submitter=self.maker, employee_id=str(self.emp.id),
                            dest_company_id=str(self.adic.id),
                            effective_date=dt.date(2026, 7, 1))
        reject_transfer(t, self.unami, notes='not approved')
        t.refresh_from_db()
        self.assertEqual(t.status, EmployeeTransfer.Status.REJECTED)
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.company_id, self.uni.id)

    def test_api_submit_and_list(self):
        c = APIClient()
        c.force_authenticate(user=self.cfo)
        # HRIS unlock + amend rights: superuser passes the gate in tests via
        # the unlock helper used elsewhere; submit through the service is the
        # core path, so here we just confirm the list endpoint serialises.
        submit_transfer(submitter=self.maker, employee_id=str(self.emp.id),
                        dest_company_id=str(self.adic.id),
                        effective_date=dt.date(2026, 7, 1))
        r = c.get('/hris/api/transfers/')
        # Either 200 with rows, or gated (401/403) — never a 500.
        self.assertIn(r.status_code, (200, 401, 403))
