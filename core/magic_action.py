"""Omni magic-action links — no-login, one-click ACTIONS from staff emails.

Same trust model as core/ceo_monitor_views.py (escalate) and hris/leave_actions.py:
the signed token IS the gate. NO Omni login is needed and NO session is minted —
the link authorises ONE scoped action for ONE user, then re-checks that user's
normal permission before doing anything. GET is inert (defeats Safe-Links
prefetch); the action happens only on the POST from the Confirm button.

This is the SAFE "focused-page" magic link (CFO decision 2026-08-12): low-risk
actions (dialogue sign-off, leave, tasks) are one-click here; money approvals are
NOT — those use a view-only link + normal sign-in, handled elsewhere.

Add a new action by registering a handler in ACTIONS: describe(user, ctx) for the
confirm page and act(user, ctx) to perform it (must re-check the same permission
the in-app path enforces).
"""
import json
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt

User = get_user_model()

_SALT = "omni-magic-action-v1"
_MAX_AGE = 60 * 60 * 72  # 72h
_BASE = getattr(settings, "PUBLIC_BASE_URL", "https://omni.alphadirect.co.bw").rstrip("/")

NAVY = "#0D1B2A"
ORANGE = "#F4A623"


def make_action_link(user, kind, *, label="", **ctx):
    """Signed no-login link for `user` to perform `kind`. Falls back to a plain
    app link when the recipient is not an active internal user (external-safe)."""
    if not user or not getattr(user, "id", None) or not getattr(user, "is_active", False):
        return f"{_BASE}/dashboard"
    payload = {"u": user.id, "k": kind, "l": (label or "")[:80], "j": uuid.uuid4().hex}
    payload.update({k: v for k, v in ctx.items()})
    return f"{_BASE}/api/magic/{signing.dumps(payload, salt=_SALT)}/"


def _shell(inner, ok=True):
    bar = NAVY if ok else "#C53030"
    return (
        '<!doctype html><html><head><meta charset="utf-8"><title>Omni</title>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"></head>'
        '<body style="font-family:Arial,Helvetica,sans-serif;background:#EEF1F5;margin:0;padding:48px 16px;">'
        '<div style="max-width:480px;margin:0 auto;background:#fff;border-radius:10px;padding:30px;'
        f'border-top:6px solid {bar};box-shadow:0 2px 10px rgba(0,0,0,.06);">'
        f'<div style="font-family:Georgia,serif;font-size:22px;font-weight:bold;color:{NAVY};">Omni</div>'
        f'{inner}</div></body></html>')


def _p(text, color="#1F2A37", size="15px"):
    return f'<p style="color:{color};font-size:{size};line-height:1.55;margin-top:14px;">{text}</p>'


def _confirm(title, detail, token, button):
    return _shell(
        _p(escape(title)) + (_p(escape(detail), "#475467", "13px") if detail else "") +
        f'<form method="post" style="margin-top:20px;"><input type="hidden" name="t" value="{escape(token)}">'
        f'<button type="submit" style="background:{NAVY};color:#fff;border:none;font-size:15px;font-weight:bold;'
        f'padding:12px 26px;border-radius:7px;cursor:pointer;">{escape(button)}</button></form>')


# ---------------------------------------------------------------------------
# Action handlers. Each: describe(user, ctx)->(title, detail, button);
# act(user, ctx)->(ok, message). act MUST re-check the in-app permission.
# ---------------------------------------------------------------------------

def _dd_row(ctx):
    from hris.models import DevelopmentDialogue
    return DevelopmentDialogue.objects.filter(ref=ctx.get("ref", ""), is_current=True).first()


def _dd_describe(user, ctx):
    row = _dd_row(ctx)
    who = (row.name if row and getattr(row, "name", "") else ctx.get("ref", "the dialogue"))
    role = ctx.get("role", "manager")
    verb = "your own review" if role == "employee" else f"{who}'s Development Dialogue"
    return (f"Sign off {verb}?", "A manager sign-off locks the period.", "Confirm & sign")


def _dd_act(user, ctx):
    from django.utils import timezone
    from hris.talent_cockpit_views import _scope
    row = _dd_row(ctx)
    if row is None:
        return False, "Dialogue not found — it may have moved to a new period."
    role = ctx.get("role", "manager")
    ref = ctx.get("ref", "")
    email = (getattr(user, "email", "") or "").strip().lower()
    # Re-check the SAME permission the in-app sign endpoint enforces.
    if role == "employee":
        if (row.email or "").lower() != email:
            return False, "You can only sign your own review."
    else:
        scope = _scope(user)
        if scope is None or (scope != "all" and ref not in scope):
            return False, "This dialogue is out of your scope."
    who = (getattr(user, "get_full_name", lambda: "")() or email or "user")
    payload = dict(row.payload or {})
    signoff = dict(payload.get("signoff") or {})
    signoff[role] = {"by": who, "at": timezone.now().isoformat(timespec="minutes")}
    payload["signoff"] = signoff
    row.payload = payload
    if role in ("manager", "moderator"):
        row.locked = True
    row.save(audit_user=user)
    try:
        from core import notifications
        if role == "employee":
            notifications.notify_dialogue_submitted(row, user)
        else:
            notifications.close_dialogue_review_tasks(row, signer=user)
    except Exception:
        pass
    return True, "Signed. Thank you — it is recorded on the dialogue."


def _ping_describe(user, ctx):
    return ("Magic-link self-test.",
            "Confirms the no-login link works. It performs NO action.",
            "Confirm test")


def _ping_act(user, ctx):
    who = (getattr(user, "get_full_name", lambda: "")() or user.get_username())
    return (True, f"It works. You opened this with no password as {who}. No action was performed.")


def _tc_task(ctx):
    from core.models import OmniTask
    return (OmniTask.objects.select_related("assignee")
            .filter(id=ctx.get("task_id")).first())


def _tc_describe(user, ctx):
    t = _tc_task(ctx)
    who = (t.assignee.get_full_name() or t.assignee.username) if (t and t.assignee_id) else ""
    title = t.title if t else "this task"
    detail = (f"Confirms {who} finished it. It then counts toward their Alpha League "
              f"score and monthly reward." if who else "")
    return (f"Confirm done: “{title}”?", detail, "Confirm done")


def _tc_act(user, ctx):
    """One-tap manager confirmation of a finished task (no login). Re-checks the
    SAME rule the dashboard enforces: only the manager who assigned it (or an
    admin) may confirm, and the confirmation is a non-assignee TaskFeedback — the
    exact row the anti-gaming reward counts. Idempotent."""
    from core.models import OmniTask, TaskFeedback
    t = _tc_task(ctx)
    if t is None:
        return False, "Task not found — it may have been removed."
    if not (user.is_superuser or t.assigner_id == user.id):
        return False, "Only the manager who assigned this task can confirm it."
    if t.status != OmniTask.Status.DONE:
        return False, "This task isn't marked done yet — ask them to finish it first."
    # Already manager-confirmed (a non-assignee left feedback)? Idempotent.
    if t.feedback.exclude(from_user_id=t.assignee_id).exists():
        return True, "Already confirmed — thank you. It counts toward their league."
    TaskFeedback.objects.create(task=t, from_user=user, to_user_id=t.assignee_id,
                                body="Confirmed done ✓ (one-tap)")
    who = (t.assignee.get_full_name() or t.assignee.username) if t.assignee_id else "them"
    return True, f"Confirmed. It now counts toward {who}'s Alpha League score + reward."


ACTIONS = {
    "dd_sign": {"describe": _dd_describe, "act": _dd_act},
    "ping": {"describe": _ping_describe, "act": _ping_act},
    "task_confirm": {"describe": _tc_describe, "act": _tc_act},
}


@csrf_exempt
def magic_action(request, token):
    token = request.POST.get("t") or token
    try:
        data = signing.loads(token, salt=_SALT, max_age=_MAX_AGE)
    except signing.SignatureExpired:
        return HttpResponseBadRequest(_shell(_p("This link has expired — open the latest email."), ok=False))
    except signing.BadSignature:
        return HttpResponseBadRequest(_shell(_p("This link is invalid."), ok=False))

    user = User.objects.filter(id=data.get("u"), is_active=True).first()
    if user is None:
        return HttpResponseBadRequest(_shell(_p("Account not found or inactive."), ok=False))

    handler = ACTIONS.get(data.get("k"))
    if handler is None:
        return HttpResponseBadRequest(_shell(_p("Unknown action."), ok=False))

    # GET = inert confirm page (Safe-Links safe): NO side effect.
    if request.method != "POST":
        title, detail, button = handler["describe"](user, data)
        return HttpResponse(_confirm(title, detail, token, button))

    # POST = the human clicked Confirm. Single-use, then act (with its own re-check).
    jti = data.get("j") or ""
    if jti:
        ck = f"magic_act_used:{jti}"
        if cache.get(ck):
            return HttpResponse(_shell(_p("This link was already used."), ok=False))
        cache.set(ck, 1, _MAX_AGE)

    ok, message = handler["act"](user, data)
    return HttpResponse(_shell(_p(escape(message), "#1B7A3B" if ok else "#C53030"), ok=ok))
