"""
Regression tests for the company code-vs-UUID bug class (CFO 2026-07-28).

The frontend's apiFetch injects the globally selected company on every GET as
its UUID *id* (``?company=<uuid>``). A view that resolves the company by CODE
only therefore never matches, and either errors loudly or — much worse — fails
silently. The Intelligence Summary page errored; two other live pages were
failing silently when this was written:

  * the Adoption Scoreboard showed ZERO staff (prod: 80 → 0 for ADIC), and
  * the CoA label picker served ADIC's balance-sheet labels to every entity,
    so a templated entity (ADIPL, ADSA, …) could be mapped to the wrong
    financial-statement lines with no error shown.

Each test below sends the UUID id — the form the app actually sends — and
asserts the endpoint resolves it. Two more assert that the mirror case (a code
on an id-only filter) no longer raises a UUID ValidationError → 500.

Companion static gate: ``audit_company_param.py`` at the repo root, wired into
CI so this class cannot ship again.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.mixins import resolve_company
from core.models import Company, Currency

User = get_user_model()


def _company(code: str, name: str) -> Company:
    Currency.objects.get_or_create(code='BWP', defaults={'name': 'Pula'})
    return Company.objects.create(code=code, name=name, base_currency_id='BWP')


class ResolveCompanyTests(TestCase):
    """The one shared resolver every company-filtered view must go through."""

    @classmethod
    def setUpTestData(cls):
        cls.co = _company('ADIC', 'Alpha Direct Insurance Company')

    def test_resolves_by_code_case_insensitively(self):
        self.assertEqual(resolve_company('ADIC').id, self.co.id)
        self.assertEqual(resolve_company('adic').id, self.co.id)

    def test_resolves_by_uuid_id_the_form_the_frontend_sends(self):
        self.assertEqual(resolve_company(str(self.co.id)).id, self.co.id)

    def test_unknown_value_returns_none_and_never_raises(self):
        self.assertIsNone(resolve_company('NOPE'))
        self.assertIsNone(resolve_company('11111111-1111-4111-8111-111111111111'))
        self.assertIsNone(resolve_company(''))
        self.assertIsNone(resolve_company(None))


class AdoptionScoreboardCompanyScopeTests(TestCase):
    """core.adoption.compute() — silently returned zero staff for a UUID."""

    @classmethod
    def setUpTestData(cls):
        from payroll.models import Employee

        cls.adic = _company('ADIC', 'Alpha Direct Insurance Company')
        cls.other = _company('ADSA', 'Alpha Direct SA')
        Employee.objects.create(employee_number='E-ADIC-1', full_name='A Adic',
                                company=cls.adic, hire_date=date(2025, 1, 1))
        Employee.objects.create(employee_number='E-ADSA-1', full_name='B Adsa',
                                company=cls.other, hire_date=date(2025, 1, 1))

    def _total(self, company):
        from core.adoption import compute
        return compute(days=30, company=company)['summary']['total']

    def test_uuid_id_scopes_to_that_company(self):
        # The regression: this was 0 because the filter was company__code=<uuid>.
        self.assertEqual(self._total(str(self.adic.id)), 1)

    def test_code_still_scopes_to_that_company(self):
        self.assertEqual(self._total('ADIC'), 1)

    def test_no_company_rolls_up(self):
        self.assertEqual(self._total(None), 2)

    def test_unknown_company_shows_nothing_rather_than_every_entity(self):
        self.assertEqual(self._total('NOT-A-COMPANY'), 0)


class FsLineOptionsCompanyScopeTests(TestCase):
    """ledger fs-line-options — a UUID silently fell back to ADIC's labels."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username='coa-tester', email='coa@example.com', password='x')  # nosec B106
        cls.adic = _company('ADIC', 'Alpha Direct Insurance Company')
        cls.tpl_co = _company('ADIPL', 'Alpha Direct Properties')

    def setUp(self):
        self.client.force_login(self.user)

    def _labels(self, company: str | None):
        qs = f'?company={company}' if company else ''
        res = self.client.get(f'/api/v1/accounts/fs-line-options/{qs}')
        self.assertEqual(res.status_code, 200, res.content[:300])
        return {opt for g in res.json()['groups'] for opt in g['options']}

    def test_uuid_and_code_return_the_same_labels(self):
        from reporting.entity_bs_templates import get_template
        if not get_template('ADIPL'):
            self.skipTest('ADIPL has no balance-sheet template in this build')
        # The regression: the UUID form returned ADIC's labels instead.
        self.assertEqual(self._labels('ADIPL'), self._labels(str(self.tpl_co.id)))

    def test_templated_entity_does_not_get_adic_labels(self):
        from reporting.entity_bs_templates import get_template
        tpl = get_template('ADIPL')
        if not tpl:
            self.skipTest('ADIPL has no balance-sheet template in this build')
        own = {ln['label'] for s in tpl['sections'] for ln in s['lines']}
        self.assertTrue(own & self._labels(str(self.tpl_co.id)),
                        'entity got someone else\'s balance-sheet labels')


class IdOnlyFilterAcceptsCodeTests(TestCase):
    """nbfira + salvage filtered company_id directly → a code 500'd on the cast."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username='scope-tester', email='scope@example.com', password='x')  # nosec B106
        cls.adic = _company('ADIC', 'Alpha Direct Insurance Company')

    def setUp(self):
        self.client.force_login(self.user)

    def test_nbfira_returns_accepts_both_forms(self):
        for value in ('ADIC', str(self.adic.id)):
            res = self.client.get(f'/api/v1/nbfira/returns/?company={value}')
            self.assertEqual(res.status_code, 200, f'{value} → {res.status_code}')

    def test_salvage_recoveries_summary_accepts_both_forms(self):
        for value in ('ADIC', str(self.adic.id)):
            res = self.client.get(f'{self._salvage_url()}&company={value}')
            self.assertEqual(res.status_code, 200, f'{value} → {res.status_code}')

    @staticmethod
    def _salvage_url():
        today = date.today()
        return ('/api/v1/salvage/external/recoveries-summary/'
                f'?from={today - timedelta(days=30)}&to={today}')

    def test_both_forms_resolve_to_the_same_company(self):
        """A code and the UUID must land on the SAME entity, not merely both 200."""
        by_code = self.client.get(f'{self._salvage_url()}&company=ADIC').json()
        by_uuid = self.client.get(f'{self._salvage_url()}&company={self.adic.id}').json()
        self.assertEqual(by_code['company_id'], str(self.adic.id))
        self.assertEqual(by_code['company_id'], by_uuid['company_id'])

    def test_unknown_company_returns_nothing_not_everything(self):
        """The dangerous failure mode: an unresolvable value quietly widening
        scope to every entity. Both endpoints must return an EMPTY result."""
        from salvage.models import SalvageItem

        # A salvage item that WOULD be counted if the filter were dropped.
        SalvageItem.objects.create(company=self.adic, asking_price=1000,
                                   item_code='SALV-SCOPE-1', part_name='Test part')

        res = self.client.get(f'{self._salvage_url()}&company=NOT-A-COMPANY')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Decimal(res.json()['total_asking_price']), Decimal('0'))

        # …and the same value IS counted when the entity resolves, so the
        # assertion above is proving the filter, not an empty table.
        res = self.client.get(f'{self._salvage_url()}&company=ADIC')
        self.assertEqual(Decimal(res.json()['total_asking_price']), Decimal('1000'))

        res = self.client.get('/api/v1/nbfira/returns/?company=NOT-A-COMPANY')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['count'], 0)
