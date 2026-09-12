"""
Management command: pull_fnb_statements

Pull the FNB statement for one or all bank accounts over a period.

  python manage.py pull_fnb_statements --account 62123456789 --days 7
  python manage.py pull_fnb_statements --all --days 31
"""
import datetime

from django.core.management.base import BaseCommand, CommandError

from banking.models import BankAccount
from fnb.client import FNBNotConfigured, FNBAPIError
from fnb.statements import pull_statement
from django.utils import timezone


class Command(BaseCommand):
    help = 'Pull recent bank statements from FNB Botswana via API.'

    def add_arguments(self, parser):
        parser.add_argument('--account', help='BankAccount.account_number to pull for.')
        parser.add_argument('--all', action='store_true',
                            help='Pull for every active BankAccount with bank_code=FNB.')
        parser.add_argument('--days', type=int, default=7,
                            help='Days back from today (default 7).')

    def handle(self, *args, **options):
        to_d   = timezone.localdate()
        from_d = to_d - datetime.timedelta(days=options['days'])

        if options['all']:
            # BUG-6 fix 2026-06-10: most BankAccount rows carry the bank in
            # `account_name` ("FNBB 62403392335 CHEQ A/C") while `bank_name`
            # is the "(unset — edit in /bank-accounts)" placeholder — so the
            # bank_name-only filter matched ZERO accounts and --all silently
            # pulled nothing. Match either field, and require a real (non-0)
            # account number since the FNB API needs one.
            from django.db.models import Q
            qs = (BankAccount.objects
                  .filter(is_active=True)
                  .filter(Q(bank_name__icontains='FNB')
                          | Q(account_name__icontains='FNB'))
                  .exclude(account_number__in=('', '0')))
        elif options.get('account'):
            qs = BankAccount.objects.filter(account_number=options['account'])
        else:
            raise CommandError('Pass --account <number> or --all.')

        if not qs.exists():
            raise CommandError('No matching BankAccount(s).')

        total = 0
        for ba in qs:
            try:
                stmt = pull_statement(ba, from_date=from_d, to_date=to_d)
            except FNBNotConfigured as e:
                raise CommandError(f'FNB not configured: {e}')
            except FNBAPIError as e:
                self.stdout.write(self.style.ERROR(
                    f'  ! {ba.account_number}: HTTP {e.status_code} {e.body[:200]}'
                ))
                continue
            n = stmt.lines.count() if hasattr(stmt, 'lines') else stmt.bankstatementline_set.count()
            self.stdout.write(self.style.SUCCESS(
                f'  ✓ {ba.account_number} ({ba.account_name}): {n} lines, '
                f'closing {stmt.closing_balance} {ba.currency_code_id}'
            ))
            total += n

        self.stdout.write(self.style.SUCCESS(
            f'\nTotal statement lines imported: {total} '
            f'({from_d.isoformat()}..{to_d.isoformat()})'
        ))
