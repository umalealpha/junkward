#!/usr/bin/env python3
"""Fable tripwires (Windows-native) — deterministic scans that run BEFORE the AI panel.

Greps are truth; models are fuzzy. This turns the three non-waivable pauses
(frozen numbers C4, PII C5, secrets H8) from "a model noticed" into "a machine proved".
Scans ONLY added lines of a unified diff (leading '+', excluding '+++' headers).

Usage:   python tripwires.py <diff-file>
Output:  JSON {hard_pause, hits:{secrets,frozen,pii,h5}} on stdout.
Exit:    2 if hard_pause (secret / frozen-number / PII), else 0. (H5 is advisory.)

No third-party deps, no bash, no `python3`-on-PATH assumption — runs anywhere Python 3 does.
"""
import json
import re
import sys
from pathlib import Path

# --- patterns ---------------------------------------------------------------
SECRET_RE = re.compile(
    r'AKIA[0-9A-Z]{16}'
    r'|-----BEGIN [A-Z ]+PRIVATE KEY-----'
    r'|(?:secret|password|passwd|api[_-]?key|token)\s*[:=]\s*["\'][^"\' ]{8,}',
    re.IGNORECASE,
)
# C4 frozen ADIC numbers + the revenue/MA/dashboard mapping keywords that touch them.
FROZEN_RE = re.compile(
    r'125\.15|96\.18|0\.292|0\.950'
    r'|gross[_ ]?written[_ ]?premium|\bGWP\b|management[_ ]?account'
    r'|revenue[_ ]?map|dashboard.*(?:gwp|revenue|premium)|(?:gwp|revenue|premium).*tile',
    re.IGNORECASE,
)
# C5 Botswana PII: Omang/id/passport, +267 / 7xxxxxxx mobiles, long bank-digit runs, IBAN-ish.
PII_RE = re.compile(
    r'omang|\bid[_ ]?number\b|passport'
    r'|\+267[0-9]{7,8}|\b7[0-9]{7}\b|\b[0-9]{10,}\b'
    r'|[A-Z]{2}[0-9]{2}[A-Z0-9]{11,}',
    re.IGNORECASE,
)
VIEW_RE = re.compile(r'class .*\((?:APIView|ViewSet|ModelViewSet|GenericAPIView|generics\.)')


def added_lines(diff_text):
    """Return [(orig_lineno_in_added_stream, text)] for '+' lines, excluding '+++' headers."""
    out, n = [], 0
    for line in diff_text.splitlines():
        if line.startswith('+') and not line.startswith('+++'):
            n += 1
            out.append((n, line[1:]))
    return out


def scan(added, rx):
    return [f'{n}:{text}' for n, text in added if rx.search(text)][:20]


def main():
    if len(sys.argv) < 2:
        sys.exit('usage: python tripwires.py <diff-file>')
    diff_path = Path(sys.argv[1])
    if not diff_path.is_file():
        print(f'FATAL: diff file not found: {diff_path}', file=sys.stderr)
        sys.exit(3)

    added = added_lines(diff_path.read_text(encoding='utf-8', errors='replace'))

    secrets = scan(added, SECRET_RE)
    frozen = scan(added, FROZEN_RE)
    pii = scan(added, PII_RE)

    # H5 advisory: a view class added without any permission_classes anywhere in the added block.
    has_view = any(VIEW_RE.search(t) for _, t in added)
    has_perm = any('permission_classes' in t for _, t in added)
    h5 = scan(added, VIEW_RE) if (has_view and not has_perm) else []

    hard = bool(secrets or frozen or pii)
    print(json.dumps({
        'hard_pause': hard,
        'hits': {'secrets': secrets, 'frozen': frozen, 'pii': pii, 'h5': h5},
    }, indent=2))
    sys.exit(2 if hard else 0)


if __name__ == '__main__':
    main()
