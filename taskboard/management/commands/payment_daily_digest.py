"""One email a day: every payment request, summarised.

CFO 2026-08-09: *"every day I need a cron somewhere around nine thirty AM,
summarising all the payment requests. everything... and email to me one email...
I have more than seven accountants requesting for payments, and it is too much
overwhelming for me to go and check everything."*

    python manage.py payment_daily_digest
    python manage.py payment_daily_digest --dry-run     # print, send nothing
    python manage.py payment_daily_digest --to me@x.com

Sends EVERY day, including "nothing is waiting on you". A digest that only
arrives when there is news cannot be told apart from one that has silently
stopped — which is how the 07:00 manager report died six times unnoticed.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils.html import escape


def _money(cur, v):
    return f'{escape(cur)} {v:,.2f}'


def _rows_table(rows, *, show_age=True, limit=40):
    if not rows:
        return '<p style="margin:0 0 14px;color:#6B7280;font-size:14px;">None.</p>'
    head = ('<tr style="background:#F9FAFB;">'
            '<td style="padding:6px 9px;border:1px solid #EEF0F3;font-weight:600;">Reference</td>'
            '<td style="padding:6px 9px;border:1px solid #EEF0F3;font-weight:600;">Payee</td>'
            '<td style="padding:6px 9px;border:1px solid #EEF0F3;font-weight:600;">Amount</td>'
            '<td style="padding:6px 9px;border:1px solid #EEF0F3;font-weight:600;">Loaded by</td>'
            + ('<td style="padding:6px 9px;border:1px solid #EEF0F3;font-weight:600;">Days</td>'
               if show_age else '') + '</tr>')
    body = ''
    for r in rows[:limit]:
        age = (f'<td style="padding:6px 9px;border:1px solid #EEF0F3;'
               f'{"color:#B91C1C;font-weight:700;" if r["age_days"] >= 3 else ""}">'
               f'{r["age_days"]}</td>') if show_age else ''
        body += (f'<tr><td style="padding:6px 9px;border:1px solid #EEF0F3;">{escape(r["ref"])}'
                 f'<br><span style="color:#6B7280;font-size:12px;">{escape(r["entity"])}</span></td>'
                 f'<td style="padding:6px 9px;border:1px solid #EEF0F3;">{escape(str(r["payee"])[:44])}</td>'
                 f'<td style="padding:6px 9px;border:1px solid #EEF0F3;white-space:nowrap;">'
                 f'{_money(r["currency"], r["total"])}</td>'
                 f'<td style="padding:6px 9px;border:1px solid #EEF0F3;">{escape(str(r["loader"])[:26])}</td>'
                 f'{age}</tr>')
    more = ''
    if len(rows) > limit:
        more = (f'<p style="margin:6px 0 14px;color:#6B7280;font-size:13px;">'
                f'Showing {limit} of {len(rows)} — the rest are on the screen.</p>')
    return ('<table style="width:100%;border-collapse:collapse;font-size:13.5px;'
            f'margin:0 0 10px;">{head}{body}</table>{more}')


def build_html(d, narrative_text, source, base_url):
    cur_lines = ' · '.join(f'{k} {v:,.2f}' for k, v in sorted(d['by_currency'].items())) or '—'
    uncounter = [o for o in d['overrides'] if not o['countersigned']]

    h = (
        '<div style="margin:0;background:#F3F4F6;font-family:\'Book Antiqua\','
        'Palatino,Georgia,serif;color:#1F2937;padding:20px 12px;">'
        '<div style="max-width:720px;margin:0 auto;background:#fff;border-radius:14px;'
        'overflow:hidden;box-shadow:0 6px 24px rgba(13,27,42,.08);">'
        '<div style="background:#0D1B2A;padding:20px 26px;">'
        '<div style="font-size:12px;color:#FFD98A;letter-spacing:.06em;text-transform:uppercase">'
        'Alpha Direct &middot; Payments</div>'
        '<div style="color:#F4A623;font-size:19px;font-weight:700;margin-top:3px;">'
        f'{d["open_count"]} payment request'
        f'{"" if d["open_count"] == 1 else "s"} open</div>'
        f'<div style="font-size:13px;color:#C7D2E0;margin-top:3px;">'
        f'{d["generated_at"]:%A %d %B %Y, %H:%M}</div></div>'
        '<div style="padding:22px 26px;font-size:15px;line-height:1.6;">'
    )

    # The AI's read of the day, first — this is what he asked for.
    h += ('<div style="background:#F8FAFC;border-left:4px solid #0D1B2A;border-radius:6px;'
          'padding:14px 16px;margin:0 0 18px;">'
          f'{escape(narrative_text)}'
          f'<div style="margin-top:8px;font-size:11px;color:#9CA3AF;">'
          f'Written by {escape(source)} from the figures below. '
          f'Every number here is calculated by Omni, never by the AI.</div></div>')

    # 🔴 Uncountersigned duplicate overrides — the control that failed on 7 Aug.
    if uncounter:
        h += ('<div style="background:#FEF2F2;border-left:4px solid #B91C1C;border-radius:6px;'
              'padding:14px 16px;margin:0 0 18px;">'
              f'<b style="color:#B91C1C;">{len(uncounter)} duplicate override(s) with no '
              f'second signature</b><br><span style="color:#7F1D1D;">')
        for o in uncounter[:6]:
            h += (f'{escape(o["ref"])} — {_money(o["currency"], o["total"])} to '
                  f'{escape(str(o["payee"])[:40])}, loaded by {escape(str(o["loader"])[:26])}<br>')
        h += '</span></div>'

    h += (f'<p style="margin:0 0 6px;"><b>Waiting on you — {len(d["waiting_cfo"])}, '
          f'{d["total_waiting_cfo"]:,.2f}</b></p>')
    h += _rows_table(d['waiting_cfo'])

    h += (f'<p style="margin:14px 0 6px;"><b>Still with finance — {len(d["waiting_finance"])}, '
          f'{d["total_waiting_finance"]:,.2f}</b></p>')
    h += _rows_table(d['waiting_finance'])

    # With the exception committee (a changed bank account). Not blocked —
    # waiting on three sign-offs. Was invisible here (Fable 5.1 audit, M2).
    if d.get('waiting_committee'):
        h += (f'<p style="margin:14px 0 6px;"><b>With the exception committee — '
              f'{len(d["waiting_committee"])}, {d["total_waiting_committee"]:,.2f}</b></p>')
        h += _rows_table(d['waiting_committee'])

    # Who is asking, so seven accountants become one line each.
    if d['by_loader']:
        h += '<p style="margin:14px 0 6px;"><b>Who has requests open</b></p>'
        h += '<table style="width:100%;border-collapse:collapse;font-size:13.5px;margin:0 0 14px;">'
        for k, v in sorted(d['by_loader'].items(), key=lambda kv: -kv[1]['total']):
            h += (f'<tr><td style="padding:5px 9px;border:1px solid #EEF0F3;">{escape(k)}</td>'
                  f'<td style="padding:5px 9px;border:1px solid #EEF0F3;">{v["count"]}</td>'
                  f'<td style="padding:5px 9px;border:1px solid #EEF0F3;white-space:nowrap;">'
                  f'{v["total"]:,.2f}</td></tr>')
        h += '</table>'

    if d['by_entity']:
        h += '<p style="margin:14px 0 6px;"><b>By company</b></p>'
        h += '<table style="width:100%;border-collapse:collapse;font-size:13.5px;margin:0 0 14px;">'
        for k, v in sorted(d['by_entity'].items(), key=lambda kv: -kv[1]['total']):
            h += (f'<tr><td style="padding:5px 9px;border:1px solid #EEF0F3;">{escape(k)}</td>'
                  f'<td style="padding:5px 9px;border:1px solid #EEF0F3;">{v["count"]}</td>'
                  f'<td style="padding:5px 9px;border:1px solid #EEF0F3;white-space:nowrap;">'
                  f'{v["total"]:,.2f}</td></tr>')
        h += '</table>'

    h += (f'<p style="margin:14px 0 4px;font-size:13.5px;color:#6B7280;">'
          f'Open by currency: {escape(cur_lines)} · '
          f'settled in the last 24 hours: {len(d["settled_24h"])} · '
          f'open with no due date: {len(d["no_due_date"])}</p>')

    h += (f'<p style="margin:18px 0 6px;text-align:center;">'
          f'<a href="{base_url}/payment-requests" style="display:inline-block;background:#0D1B2A;'
          f'color:#F4A623;text-decoration:none;font-weight:700;font-size:14px;padding:12px 24px;'
          f'border-radius:9px;">Open payment requests &rarr;</a></p>')
    h += ('<p style="margin:14px 0 0;">Regards,<br><b>Omni</b><br>'
          '<span style="color:#6B7280;">Alpha Direct</span></p></div></div></div>')
    return h


class Command(BaseCommand):
    help = "Email the CFO one daily summary of every payment request."

    def add_arguments(self, parser):
        parser.add_argument('--to', dest='to')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        from django.conf import settings
        from taskboard import payment_digest

        d = payment_digest.collect()
        text, source = payment_digest.narrative(d)
        base = getattr(settings, 'PUBLIC_BASE_URL',
                       'https://omni.alphadirect.co.bw').rstrip('/')
        html = build_html(d, text, source, base)

        waiting = len(d['waiting_cfo'])
        uncounter = len([o for o in d['overrides'] if not o['countersigned']])
        flag = f'🔴 {uncounter} unsigned override · ' if uncounter else ''
        subject = (f'{flag}Payments — {waiting} waiting on you '
                   f'({d["total_waiting_cfo"]:,.0f}), {d["open_count"]} open')

        to = opts.get('to') or getattr(settings, 'PAYMENT_DIGEST_TO', '') \
            or 'pganesharajah@alphadirect.co.bw'

        if opts.get('dry_run'):
            self.stdout.write(f'DRY RUN — "{subject}" to {to}')
            self.stdout.write(f'narrative ({source}): {text}')
            return

        from django.core.mail import EmailMultiAlternatives
        msg = EmailMultiAlternatives(
            subject=subject,
            body=f'{text}\n\nOpen {base}/payment-requests',
            to=[a.strip() for a in to.split(',') if a.strip()],
        )
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=False)
        self.stdout.write(self.style.SUCCESS(
            f'sent to {to}: {waiting} waiting, {d["open_count"]} open, narrative by {source}'))
