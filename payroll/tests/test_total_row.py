"""payroll/tests/test_total_row.py — spreadsheet TOTAL/summary rows must never be
ingested as employees. Bug (ADIC final run 2026-07-24): the label
"TOTAL (72 payslips)" slipped past the exact-word pattern and doubled Basic.
"""
from django.test import SimpleTestCase
from payroll.importer import _is_total_row


class TotalRowDetectionTests(SimpleTestCase):
    def test_total_rows_are_detected(self):
        for label in ['TOTAL (72 payslips)', 'Total', 'totals', 'GRAND TOTAL',
                      'Sub-total', 'Subtotal (x)', 'Sum', 'total for June',
                      'TOTAL - 72 payslips', 'Totals:']:
            self.assertTrue(_is_total_row(label), f'{label!r} should be a total row')

    def test_real_names_are_not_total_rows(self):
        for label in ['Bernard Balikani', 'Arun Iyer', 'Aobakwe Angel Morris',
                      'Sumaya Khan', 'Summertime Ltd', 'Sunday Phiri', '', None]:
            self.assertFalse(_is_total_row(label), f'{label!r} must NOT be a total row')
