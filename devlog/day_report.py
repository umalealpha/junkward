"""
devlog/day_report.py — the end-of-day read (CFO 2026-09-09).

"what i have done for the whole day and what finished and what to finish."

Three bands, in the order he reads them:

  went_live      finished today, and finished means ON PROD
  in_flight      picked up, not live yet
  still_to_do    asked for, nothing built against it yet

Plus a fourth band that most dashboards would hide and this one must not:

  unlinked       deployed today with no request recorded against it

That band is the honesty. Capture only happens through /goal, /code, /lane-b
and /fabe; anything asked in plain conversation is invisible to this table. If
those commits were quietly dropped the page would look complete and be wrong,
and he would find out the first time he went looking for something real. Shown
plainly, the same gap tells him exactly which work never got recorded.

The day is Botswana's, not the server's. The box runs UTC, and a report that
ends at 02:00 local would put the last two hours of a late session on tomorrow.
"""
from __future__ import annotations

import datetime as dt

from django.db import models

# Botswana is UTC+2 all year.
LOCAL_OFFSET = dt.timedelta(hours=2)


def local_day_bounds(day: dt.date) -> tuple[dt.datetime, dt.datetime]:
    """The UTC window covering one Botswana calendar day."""
    start_local = dt.datetime.combine(day, dt.time.min)
    start_utc = (start_local - LOCAL_OFFSET).replace(tzinfo=dt.timezone.utc)
    return start_utc, start_utc + dt.timedelta(days=1)


def today_local(now: dt.datetime | None = None) -> dt.date:
    from django.utils import timezone
    return ((now or timezone.now()) + LOCAL_OFFSET).date()


def _item(i, commits_by_item):
    return {
        'id': str(i.id),
        'who_asked': i.who_asked,
        'requested_by_id': i.requested_by_id,
        'bug': ({'id': str(i.bug_id),
                 'ref': getattr(i.bug, 'reference', '') or str(i.bug_id)[:8],
                 'status': getattr(i.bug, 'status', '')} if i.bug_id else None),
        'asked_text': i.asked_text,
        'title': i.title or (i.asked_text[:110] + ('…' if len(i.asked_text) > 110 else '')),
        'status': i.status,
        'status_label': i.get_status_display(),
        'asked_at': i.asked_at,
        'live_at': i.live_at,
        'machine': i.machine,
        'source': i.source,
        'area': i.area,
        'success_criteria': i.success_criteria,
        'age_hours': None,
        'commits': commits_by_item.get(i.id, []),
    }


def day(day_date: dt.date | None = None, now: dt.datetime | None = None,
        who: str = '', area: str = '', source: str = '',
        only_bugs: bool = False, q: str = '') -> dict:
    """The whole day in one dict.

    The filters narrow the OPEN bands and the live band alike, so a filtered
    view stays internally consistent — filtering "what went live" without
    filtering "what is left" would show him a day that never happened.
    """
    from django.utils import timezone
    from devlog.models import DevCommit, DevDeploy, DevItem

    now = now or timezone.now()
    day_date = day_date or today_local(now)
    start, end = local_day_bounds(day_date)

    commits_by_item: dict = {}
    for c in (DevCommit.objects.filter(item__isnull=False)
              .select_related('deploy')):
        commits_by_item.setdefault(c.item_id, []).append(
            {'sha': c.sha[:8], 'subject': c.subject})

    def narrow(qs):
        if who:
            qs = qs.filter(models.Q(requested_by__username__iexact=who)
                           | models.Q(requested_by__email__iexact=who)
                           | models.Q(requested_by_name__icontains=who))
        if area:
            qs = qs.filter(area__iexact=area)
        if source:
            qs = qs.filter(source__iexact=source)
        if only_bugs:
            qs = qs.filter(bug__isnull=False)
        if q:
            qs = qs.filter(models.Q(asked_text__icontains=q)
                           | models.Q(title__icontains=q))
        return qs.select_related('requested_by', 'bug')

    live = list(narrow(DevItem.objects.filter(status=DevItem.Status.LIVE,
                                              live_at__gte=start, live_at__lt=end)))
    # Everything still open, whenever it was asked — "what to finish" is not
    # limited to today, or a thing asked on Monday vanishes on Tuesday.
    open_items = list(narrow(DevItem.objects.filter(
        status__in=(DevItem.Status.BUILDING, DevItem.Status.WAITING,
                    DevItem.Status.ASKED))))

    in_flight, still = [], []
    for i in open_items:
        row = _item(i, commits_by_item)
        row['age_hours'] = round((now - i.asked_at).total_seconds() / 3600, 1)
        (in_flight if i.status in (DevItem.Status.BUILDING,
                                   DevItem.Status.WAITING) else still).append(row)

    in_flight.sort(key=lambda r: -(r['age_hours'] or 0))
    still.sort(key=lambda r: -(r['age_hours'] or 0))

    unlinked = [
        {'sha': c.sha[:8], 'subject': c.subject, 'author': c.author,
         'at': c.committed_at}
        for c in DevCommit.objects.filter(item__isnull=True,
                                          deploy__deployed_at__gte=start,
                                          deploy__deployed_at__lt=end)
        .select_related('deploy')
    ]

    deploys = list(DevDeploy.objects.filter(deployed_at__gte=start,
                                            deployed_at__lt=end))
    first_ever = DevItem.objects.order_by('asked_at').values_list(
        'asked_at', flat=True).first()

    return {
        'day': day_date,
        'went_live': [_item(i, commits_by_item) for i in live],
        'in_flight': in_flight,
        'still_to_do': still,
        'unlinked_commits': unlinked,
        'deploys': [{'sha': d.sha[:8], 'at': d.deployed_at,
                     'commits': d.commit_count, 'ok': d.ok} for d in deploys],
        'counts': {
            'asked_today': DevItem.objects.filter(asked_at__gte=start,
                                                  asked_at__lt=end).count(),
            'went_live_today': len(live),
            'still_open': len(in_flight) + len(still),
            'deploys_today': len(deploys),
            'shipped_without_a_request': len(unlinked),
        },
        'by_person': _by_person(),
        'filter_options': {
            'people': sorted({i.who_asked for i in DevItem.objects.select_related(
                'requested_by') if i.who_asked != 'not recorded'}),
            # .order_by() with no argument is required before .distinct():
            # the model's Meta ordering (-asked_at) is added to the SELECT, so
            # DISTINCT then applies to (area, asked_at) and every row survives.
            # Without it the dropdown lists "review-engine" nine times.
            'areas': sorted(set(DevItem.objects.exclude(area='').order_by()
                                .values_list('area', flat=True).distinct())),
            'sources': sorted(set(DevItem.objects.exclude(source='').order_by()
                                  .values_list('source', flat=True).distinct())),
        },
        'applied_filters': {'who': who, 'area': area, 'source': source,
                            'only_bugs': only_bugs, 'q': q},
        # Stated on the page. Never backfilled — a reconstructed history is a
        # story, not a record.
        'recording_since': first_ever,
    }


def _by_person() -> list:
    """Open vs live per requester — "who is waiting on me" at a glance."""
    from devlog.models import DevItem

    tally: dict = {}
    for i in DevItem.objects.select_related('requested_by'):
        row = tally.setdefault(i.who_asked, {'who': i.who_asked, 'open': 0, 'live': 0})
        if i.status == DevItem.Status.LIVE:
            row['live'] += 1
        elif i.is_open:
            row['open'] += 1
    return sorted(tally.values(), key=lambda r: (-r['open'], -r['live'], r['who']))
