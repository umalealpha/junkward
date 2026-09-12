"""core/team_glance_views.py — one glance at my direct reports, for the phone
Team tab (CFO 2026-09-03: "who's in, who's dark, who's on leave, what's overdue").

GET /api/v1/team/glance/  (IsAuthenticated)

    { as_of, reports: [{ employee_id, user_id, name, job_title, on_leave_today,
                         leave_type, online, dark_days_7, open_tasks, overdue_tasks }],
      counts: { in, on_leave, dark, overdue } }

Nothing here is computed fresh from Time Doctor. Every figure is read from the
stores the rest of Omni already writes:
  * on_leave_today  — an APPROVED hris.LeaveRequest spanning today.
  * online          — core.OnlinePresence heartbeat within the same 5-minute
                      window /presence/online/ uses.
  * dark_days_7     — hris.WorkdayJustification rows in the last 7 calendar days
                      whose stored status (the product of hris.workforce
                      .classify_day, written by the daily brief) is not one of
                      the "accounted for" states. The shortfall rule itself is
                      NOT re-implemented here.
  * open/overdue    — core.OmniTask via taskboard.services.is_overdue, approval
                      items excluded exactly as the task dashboard excludes them.

No PII beyond name + job title + status. A user with no reports gets an empty
200, never a 403 — the app uses this as its "do I manage people" probe.
"""
from __future__ import annotations

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

PRESENCE_WINDOW = timedelta(minutes=5)      # same window as presence_online_users
DARK_LOOKBACK_DAYS = 7


def _zero_counts() -> dict:
    return {'in': 0, 'on_leave': 0, 'dark': 0, 'overdue': 0}


def _team_profiles(me):
    """Active, real (non-test) people who line-report to `me` or whom `me`
    co-reviews — the same set the monthly-feedback worklist uses."""
    from hris.models import HRISProfile
    from payroll.models import Employee
    return (HRISProfile.objects
            .filter(manager=me)   # line manager ONLY — a co-manager is a second rater, not a second boss (notebook)
            .exclude(employee=None)
            .exclude(employee__status=Employee.Status.TERMINATED)
            .exclude(employee__is_test_record=True)
            .select_related('employee', 'employee__user')
            .distinct()
            .order_by('employee__full_name'))


def _leave_today(profile_ids, today) -> dict:
    """{profile_id: leave type name} for APPROVED leave that spans today."""
    from hris.models import LeaveRequest
    rows = (LeaveRequest.objects
            .filter(profile_id__in=profile_ids, status=LeaveRequest.Status.APPROVED,
                    start_date__lte=today, end_date__gte=today)
            .select_related('leave_type'))
    return {r.profile_id: (r.leave_type.name if r.leave_type_id else 'Leave') for r in rows}


def _online_user_ids(user_ids) -> set:
    from core.models import OnlinePresence
    cutoff = timezone.now() - PRESENCE_WINDOW
    return set(OnlinePresence.objects
               .filter(user_id__in=user_ids, last_seen__gte=cutoff)
               .values_list('user_id', flat=True))


def _dark_days(profile_ids, today) -> dict:
    """{profile_id: n} — days in the last 7 whose stored classification is still
    a shortfall nobody has accepted (unjustified / never answered / explained but
    not yet reviewed). MET, NOT_REQUIRED and JUSTIFIED are accounted for."""
    from hris.models import WorkdayJustification as WJ
    accounted = (WJ.Status.MET, WJ.Status.NOT_REQUIRED, WJ.Status.JUSTIFIED)
    since = today - timedelta(days=DARK_LOOKBACK_DAYS)
    out: dict = {}
    for pid in (WJ.objects
                .filter(profile_id__in=profile_ids, work_date__gte=since, work_date__lt=today)
                .exclude(status__in=accounted)
                .values_list('profile_id', flat=True)):
        out[pid] = out.get(pid, 0) + 1
    return out


def _task_counts(user_ids) -> dict:
    """{user_id: (open, overdue)} over real tasks (approval items excluded)."""
    from core.models import OmniTask
    from taskboard.cfo_views import _real_tasks
    from taskboard.services import is_overdue
    qs = _real_tasks(OmniTask.objects
                     .filter(assignee_id__in=user_ids)
                     .exclude(status__in=(OmniTask.Status.DONE, OmniTask.Status.CANCELLED)))
    out: dict = {}
    now = timezone.localtime()
    for t in qs.only('id', 'assignee_id', 'status', 'due_at', 'due_time'):
        o, od = out.get(t.assignee_id, (0, 0))
        out[t.assignee_id] = (o + 1, od + (1 if is_overdue(t, now) else 0))
    return out


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def team_glance(request):
    from hris.performance_views import _resolve_employee
    today = timezone.localdate()
    me = _resolve_employee(request.user)
    if me is None:
        return Response({'as_of': today, 'reports': [], 'counts': _zero_counts()})

    profiles = list(_team_profiles(me))
    if not profiles:
        return Response({'as_of': today, 'reports': [], 'counts': _zero_counts()})

    pids = [p.id for p in profiles]
    uids = [p.employee.user_id for p in profiles if p.employee.user_id]
    leave = _leave_today(pids, today)
    online = _online_user_ids(uids)
    dark = _dark_days(pids, today)
    tasks = _task_counts(uids)

    reports = []
    counts = _zero_counts()
    for p in profiles:
        emp = p.employee
        on_leave = p.id in leave
        is_online = bool(emp.user_id) and emp.user_id in online
        dark_n = dark.get(p.id, 0)
        open_n, overdue_n = tasks.get(emp.user_id, (0, 0)) if emp.user_id else (0, 0)
        reports.append({
            'employee_id': str(emp.id),
            # Django user pk (not PII) — the join key to /taskboard/overview/
            # rows, whose `assignee` is the same pk. Null for register-only staff.
            'user_id': emp.user_id,
            'name': emp.full_name,
            'job_title': emp.job_title or '',
            'on_leave_today': on_leave,
            'leave_type': leave.get(p.id),
            'online': is_online,
            'dark_days_7': dark_n,
            'open_tasks': open_n,
            'overdue_tasks': overdue_n,
        })
        counts['in'] += 1 if is_online else 0
        counts['on_leave'] += 1 if on_leave else 0
        counts['dark'] += 1 if dark_n else 0
        counts['overdue'] += overdue_n

    return Response({'as_of': today, 'reports': reports, 'counts': counts})
