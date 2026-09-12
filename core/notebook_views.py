"""The shared notebook — CFO 2026-07-25. Write-from-Claude-Code added 2026-08-15.

Four endpoints:

  GET  /api/v1/notebook/raw/          plain text, no JSON wrapper. This is the
                                      one Claude reads at the start of every
                                      session, so it must be FAST and boring.
                                      Machine access via a scoped API key
                                      (`notebook` scope, read-only).
  PUT  /api/v1/notebook/raw/          plain text in, plain text confirmation
                                      out. This is how Claude Code updates the
                                      page headlessly — no browser sign-in.
                                      Needs the CFO/EXCO session OR a key
                                      carrying the separate `notebook-write`
                                      scope (deliberately not the same key as
                                      the read one, so a leaked read-only key
                                      still cannot change the page).
  GET  /api/v1/notebook/              JSON, for the browser page.
  PUT  /api/v1/notebook/              save. Browser page (session auth) —
                                      also now accepts `notebook-write`.

Why plain text on the raw endpoint: Claude reads/writes it with a single
fetch/PUT and no parsing. Measured against the alternative that was almost
built instead — a file in OneDrive — Omni wins because both machines and his
phone see the same text with no sync delay.

Who may see it: the CFO, EXCO, superusers, and anything holding an API key with
the `notebook` scope. It carries staff facts, not secrets — passwords and keys
belong in the Secrets Vault (VaultSecret), and the model docstring says so.

Who may CHANGE it: the CFO, EXCO, superusers, and anything holding an API key
with the `notebook-write` scope. Same size cap as the "keep it one page" rule
this page has always asked of its human editor (NOTEBOOK_MAX_CHARS below) —
enforced here too so a runaway script can't turn one page into ten.
"""
from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import (api_view, authentication_classes,
                                       permission_classes)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import NotebookPage

DEFAULT_SLUG = 'main'

# Rule 2 in the page's own text is "keep it to one page." The cap exists so a
# script bug can't quietly grow the page past the point a human — or Claude —
# will actually read it.
#
# Raised from 24,000 to 60,000 with the CFO's approval, 19-Aug-2026. The old
# figure had stopped being a guard and become a lock: the real page reached
# 51,759 characters, so EVERY headless save was refused while the browser page
# (which never had a cap) went on saving happily. A limit that only blocks the
# automated path pushes edits to the un-capped one — the opposite of the point.
# 60,000 sits above today's page with room to add, and still refuses a runaway.
NOTEBOOK_MAX_CHARS = 60_000

STARTER = """# NOTEBOOK — the shared world between Prathap and Claude

Claude reads this before its first reply, every session, on every machine.

**Rule 1 — this page beats Omni.** If Omni's database disagrees with a line
here, this page is right. Never re-ask Prathap to confirm anything written here.

**Rule 2 — keep it to one page.** The moment it sprawls it stops being read.

**Rule 3 — what belongs here.** Company numbers are wanted, not avoided: GWP,
PAT, PO totals, the month-end position, what we are building. They live here so
a question is answered in one read instead of a long query.

**Never here:** passwords, keys, bank account numbers, Omang/ID numbers, and
individual staff salaries. A shared login exposed staff pay on 25 July 2026 —
that is the one thing this page must not repeat. Company figures yes, per-person
pay no.
"""


def _editors() -> set[str]:
    raw = getattr(settings, 'NOTEBOOK_EDITORS', None) or (
        'pganesharajah@alphadirect.co.bw', 'excoboard@alphadirect.co.bw')
    return {(a or '').strip().lower() for a in raw}


def _key_has_notebook_scope(request) -> bool:
    """True when the caller authenticated with an ApiKey carrying `notebook`."""
    api_key = getattr(request, 'auth', None)
    if api_key is None or not hasattr(api_key, 'allowed_scopes'):
        return False
    scopes = list(api_key.allowed_scopes or [])
    return 'notebook' in scopes or 'admin' in scopes


def _key_has_notebook_write_scope(request) -> bool:
    """True when the caller authenticated with an ApiKey carrying `notebook-write`.

    Deliberately a different check to `_key_has_notebook_scope` above — the
    read-only `notebook` scope must NEVER satisfy this. `notebook-write` is
    also outside READ_ONLY_SCOPES (core.api_key_auth), so it clears the
    authentication-layer gate before this even runs.
    """
    api_key = getattr(request, 'auth', None)
    if api_key is None or not hasattr(api_key, 'allowed_scopes'):
        return False
    scopes = list(api_key.allowed_scopes or [])
    return 'notebook-write' in scopes or 'admin' in scopes


def _may_read(request) -> bool:
    """Who may READ the notebook.

    DeepSeek review 2026-07-26 caught this and it was a real live hole: the raw
    endpoint originally carried only IsAuthenticated, so ANY logged-in account
    could read the page — proved on prod with `pbisen@theriskco.com`, an external
    platform partner, pulling all 5,517 characters including the GWP and PAT
    figures. The JSON endpoint was gated but the plain-text one was not, and the
    test only covered anonymous access, so nothing caught it.

    Reading is now exactly the same gate as editing, plus a scoped API key for
    headless reads. A key that can WRITE the page (`notebook-write`) can also
    read it — a write-only key that can save but never see what it just saved
    would be a strange, unusable shape, and the safe append pattern (GET
    current body, add to it, PUT the result back) needs the read half anyway.
    """
    return (_may_edit(getattr(request, 'user', None))
            or _key_has_notebook_scope(request)
            or _key_has_notebook_write_scope(request))


def _may_edit(user) -> bool:
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    if (getattr(user, 'email', '') or '').strip().lower() in _editors():
        return True
    profile = getattr(user, 'profile', None)
    return (getattr(profile, 'title', '') or '').lower() in ('cfo', 'ceo')


def _may_write_raw(request) -> bool:
    """Who may WRITE via the plain-text endpoint: a logged-in editor, or a key
    carrying `notebook-write`. Never satisfied by the read-only `notebook`
    scope — see _key_has_notebook_write_scope."""
    return _may_edit(getattr(request, 'user', None)) or _key_has_notebook_write_scope(request)


def _page(slug: str = DEFAULT_SLUG, *, create: bool = True) -> NotebookPage | None:
    """The page, or None when it does not exist and `create` says don't make one.

    `create=False` is what a read passes, because reading must never write. It
    used to: an unknown ?slug= went straight into get_or_create, so merely
    GETting a slug seeded a fresh STARTER page. That happened on prod on
    2026-08-15 — `claude-code-live-proof` (833 chars) appeared beside the real
    `main` (41,507 chars) and, being the newer row, anything reaching for the
    notebook by recency or `.first()` picked up the near-empty page and believed
    it was the notebook. This page is the documented source of truth that beats
    Omni's database, so a phantom copy is a correctness bug, not clutter.

    DEFAULT_SLUG still bootstraps on a read, so a fresh install has a notebook
    on day one without anyone having to save one first.
    """
    if not create and slug != DEFAULT_SLUG:
        return NotebookPage.objects.filter(slug=slug).first()
    page, created = NotebookPage.objects.get_or_create(
        slug=slug, defaults={'title': 'Notebook', 'body': STARTER})
    return page


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def notebook_raw(request):
    """Plain text. Deliberately no JSON, no envelope — one fetch/PUT, zero parsing."""
    slug = request.GET.get('slug') or DEFAULT_SLUG

    if request.method == 'PUT':
        if not _may_write_raw(request):
            return HttpResponse('This notebook is restricted.\n',
                                content_type='text/plain; charset=utf-8', status=403)
        # Fetched after the gate, and only here: saving may create a page,
        # reading may not, and a refused save must not create one either.
        page = _page(slug)
        body = request.body.decode('utf-8', errors='replace')
        if len(body) > NOTEBOOK_MAX_CHARS:
            return HttpResponse(
                f'Refused: {len(body):,} chars is over the {NOTEBOOK_MAX_CHARS:,}-char '
                f'one-page limit. Trim it before saving — this page only works if it '
                f'stays short enough to actually read.\n',
                content_type='text/plain; charset=utf-8', status=400)
        page.body = body
        page.updated_by = request.user if getattr(request.user, 'is_authenticated', False) else None
        page.save(update_fields=['body', 'updated_by', 'updated_at'])
        resp = HttpResponse(f'OK - saved {len(body):,} chars.\n',
                            content_type='text/plain; charset=utf-8')
        resp['X-Notebook-Updated'] = page.updated_at.isoformat() if page.updated_at else ''
        resp['Cache-Control'] = 'no-store'
        return resp

    if not _may_read(request):
        return Response({'detail': 'This notebook is restricted.'},
                        status=status.HTTP_403_FORBIDDEN)
    # Gate first, then existence, so an outsider learns nothing about which
    # pages exist. Plain text on the 404 too — this endpoint promises no JSON.
    page = _page(slug, create=False)
    if page is None:
        return HttpResponse('No such notebook page.\n',
                            content_type='text/plain; charset=utf-8', status=404)
    resp = HttpResponse(page.body or '', content_type='text/plain; charset=utf-8')
    # So a caller can tell whether it changed without re-reading the whole thing.
    resp['X-Notebook-Updated'] = page.updated_at.isoformat() if page.updated_at else ''
    resp['Cache-Control'] = 'no-store'
    return resp


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def notebook_detail(request):
    slug = (request.GET.get('slug') or request.data.get('slug')
            if request.method == 'PUT' else request.GET.get('slug')) or DEFAULT_SLUG

    if request.method == 'GET':
        if not _may_read(request):
            return Response({'detail': 'This notebook is restricted.'},
                            status=status.HTTP_403_FORBIDDEN)
        page = _page(slug, create=False)
        if page is None:
            return Response({'detail': 'No such notebook page.'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({
            'slug': page.slug,
            'title': page.title,
            'body': page.body,
            'updated_at': page.updated_at,
            'updated_by': getattr(page.updated_by, 'get_full_name', lambda: '')()
                          or getattr(page.updated_by, 'username', ''),
        })

    if not _may_edit(request.user):
        return Response({'detail': 'You may not edit the notebook.'},
                        status=status.HTTP_403_FORBIDDEN)

    page = _page(slug)
    body = request.data.get('body')
    if body is None:
        return Response({'detail': 'body is required.'},
                        status=status.HTTP_400_BAD_REQUEST)
    # The SAME cap the plain-text endpoint enforces. It used to live only there,
    # so the limit bound the headless caller and left the browser — the path a
    # human actually types into — free to grow the page without bound. A guard on
    # one write path to a field is not a guard; it just moves the traffic.
    if len(body) > NOTEBOOK_MAX_CHARS:
        return Response(
            {'detail': f'Refused: {len(body):,} chars is over the '
                       f'{NOTEBOOK_MAX_CHARS:,}-char one-page limit. Trim it before saving — '
                       f'this page only works if it stays short enough to actually read.'},
            status=status.HTTP_400_BAD_REQUEST)
    page.body = body
    if request.data.get('title'):
        page.title = request.data['title'][:140]
    page.updated_by = request.user
    page.save(update_fields=['body', 'title', 'updated_by', 'updated_at'])
    return Response({'slug': page.slug, 'updated_at': page.updated_at,
                     'chars': len(page.body)})
