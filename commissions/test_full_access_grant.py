"""The five people the CFO granted unlimited commission access (2026-09-08).

Pinned by EMAIL, never by first name: "Pako" and "Kago" are two different
people — Pako Kago and Kago Tshutlhedi — and the CFO confirmed he means both.
"""
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase

from commissions.access import (
    FINAL, PAYROLL, STAGE1, STAGE2,
    can_export, can_review_stage, is_payroll, is_reviewer,
)

GRANTED = [
    ('rmokgware@alphadirect.co.bw', 'Rose Mokgware'),
    ('kmokhendo@alphadirect.co.bw', 'Keetile Mokhendo'),
    ('pkago@alphadirect.co.bw', 'Pako Kago'),
    ('ktshutlhedi@alphadirect.co.bw', 'Kago Tshutlhedi'),
    ('bmakosha@alphadirect.co.bw', 'Bokani Makosha'),
]


def _user(email, name):
    User = get_user_model()
    first, _, last = name.partition(' ')
    return User(username=email.split('@')[0], email=email,
                first_name=first, last_name=last, is_active=True)


class FullAccessGrantTests(SimpleTestCase):
    def test_each_granted_person_has_every_stage_payroll_and_export(self):
        for email, name in GRANTED:
            u = _user(email, name)
            with self.subTest(person=name):
                self.assertTrue(can_review_stage(u, STAGE1), f'{name} missing 1st review')
                self.assertTrue(can_review_stage(u, STAGE2), f'{name} missing 2nd review')
                self.assertTrue(can_review_stage(u, FINAL), f'{name} missing final approval')
                self.assertTrue(can_review_stage(u, PAYROLL), f'{name} missing payroll')
                self.assertTrue(is_payroll(u), f'{name} not payroll')
                self.assertTrue(is_reviewer(u), f'{name} not a reviewer')
                self.assertTrue(can_export(u), f'{name} cannot export')

    def test_the_username_is_not_the_email(self):
        """Rose signs in as 'rose.mokgware' but her address is 'rmokgware@'.
        Granting on a username-shaped address gives her nothing."""
        self.assertFalse(is_reviewer(_user('rose.mokgware@alphadirect.co.bw', 'Rose Mokgware')))
        self.assertTrue(is_reviewer(_user('rmokgware@alphadirect.co.bw', 'Rose Mokgware')))

    def test_the_grant_is_by_email_not_by_first_name(self):
        """A different Pako must NOT inherit Pako Kago's access."""
        other = _user('pmampane@insurance.co.bw', 'Pako Mampane')
        self.assertFalse(is_reviewer(other))
        self.assertFalse(can_export(other))

    def test_an_unrelated_signed_in_user_still_has_nothing(self):
        self.assertFalse(is_reviewer(_user('nobody@alphadirect.co.bw', 'No Body')))
        self.assertFalse(can_export(_user('nobody@alphadirect.co.bw', 'No Body')))

    def test_the_cfo_keeps_final_approval(self):
        cfo = _user('pganesharajah@alphadirect.co.bw', 'Prathap Ganesharajah')
        self.assertTrue(can_review_stage(cfo, FINAL))
        self.assertTrue(can_export(cfo))
