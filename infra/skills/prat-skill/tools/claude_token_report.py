"""Combined daily Claude token-usage email for Prathap.

Reads local Claude Code usage on this Windows PC via ccusage,
PLUS the Mac Mini's usage (pushed to the repo as mac-daily.json),
and combines them into one email.

Covers: ALL accounts on BOTH machines (Windows PC + Mac Mini).
"""

import json
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEND_MAIL = HERE / "send_mail.py"
NPX = r"C:\Program Files\nodejs\npx.cmd"
PYTHON = sys.executable
TO = "pganesharajah@alphadirect.co.bw"

REPO = Path(r"C:\Users\PrathapAsus\work\alpha-finance")
MAC_USAGE = REPO / ".claude" / "usage" / "mac-daily.json"

NAVY = "#0D1B2A"
ORANGE = "#F4A623"


def fetch_windows_usage(days_back: int = 8):
    since = (date.today() - timedelta(days=days_back)).strftime("%Y%m%d")
    out = subprocess.run(
        [NPX, "-y", "ccusage@latest", "daily", "--since", since, "--json"],
        capture_output=True, text=True, timeout=600,
    )
    if out.returncode != 0:
        raise RuntimeError(f"ccusage failed: {out.stderr[:500]}")
    return json.loads(out.stdout)["daily"]


def fetch_mac_usage():
    """Pull latest repo and read the Mac's usage JSON if it exists."""
    try:
        subprocess.run(
            ["git", "pull", "--rebase", "--quiet"],
            cwd=str(REPO), capture_output=True, timeout=30,
        )
    except Exception:
        pass
    if not MAC_USAGE.exists():
        return []
    try:
        data = json.loads(MAC_USAGE.read_text(encoding="utf-8"))
        return data.get("daily", [])
    except Exception:
        return []


def combine_usage(win_daily, mac_daily):
    """Merge per-day totals from both machines. Returns combined + per-machine dicts."""
    win_by_day = {d["period"]: d for d in win_daily}
    mac_by_day = {d["period"]: d for d in mac_daily}
    all_days = sorted(set(win_by_day) | set(mac_by_day))

    combined = []
    for day in all_days:
        w = win_by_day.get(day)
        m = mac_by_day.get(day)
        w_tok = w["totalTokens"] if w else 0
        w_cost = w["totalCost"] if w else 0.0
        m_tok = m["totalTokens"] if m else 0
        m_cost = m["totalCost"] if m else 0.0
        combined.append({
            "period": day,
            "win_tokens": w_tok, "win_cost": w_cost,
            "mac_tokens": m_tok, "mac_cost": m_cost,
            "totalTokens": w_tok + m_tok,
            "totalCost": w_cost + m_cost,
        })
    return combined


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:,.0f}M"
    if n >= 1_000:
        return f"{n / 1_000:,.0f}k"
    return str(n)


def build_email(combined, has_mac: bool):
    today = date.today()
    yesterday = today - timedelta(days=1)
    by_day = {d["period"]: d for d in combined}

    rows = []
    week_tokens = week_cost = 0
    week_win_tok = week_mac_tok = 0
    for i in range(7, 0, -1):
        d = today - timedelta(days=i)
        key = d.strftime("%Y-%m-%d")
        rec = by_day.get(key, {})
        tokens = rec.get("totalTokens", 0)
        cost = rec.get("totalCost", 0.0)
        w_tok = rec.get("win_tokens", 0)
        m_tok = rec.get("mac_tokens", 0)
        week_tokens += tokens
        week_cost += cost
        week_win_tok += w_tok
        week_mac_tok += m_tok

        hl = ' style="background:#FDF3DC;font-weight:bold"' if d == yesterday else ""
        machine_col = ""
        if has_mac:
            machine_col = (
                f"<td style='padding:6px 12px;border-bottom:1px solid #ddd;text-align:right;color:#888;font-size:12px'>"
                f"{fmt_tokens(w_tok)} + {fmt_tokens(m_tok)}</td>"
            )
        rows.append(
            f"<tr{hl}>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #ddd'>{d.strftime('%a %d %b')}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #ddd;text-align:right'>{fmt_tokens(tokens)}</td>"
            f"{machine_col}"
            f"<td style='padding:6px 12px;border-bottom:1px solid #ddd;text-align:right'>${cost:,.2f}</td></tr>"
        )

    y_rec = by_day.get(yesterday.strftime("%Y-%m-%d"), {})
    y_tokens = y_rec.get("totalTokens", 0)
    y_cost = y_rec.get("totalCost", 0.0)

    subject = f"Claude usage {yesterday.strftime('%d %b')}: {fmt_tokens(y_tokens)} tokens (~${y_cost:,.0f} value)"

    machine_header = ""
    machine_total = ""
    if has_mac:
        machine_header = "<th style='padding:6px 12px;text-align:right'>PC + Mac</th>"
        machine_total = (
            f"<td style='padding:6px 12px;text-align:right;color:#888;font-size:12px'>"
            f"{fmt_tokens(week_win_tok)} + {fmt_tokens(week_mac_tok)}</td>"
        )

    scope = "all accounts, both machines (Windows PC + Mac Mini)" if has_mac else "all accounts, this PC only (Mac data not yet available)"

    body = f"""
<div style="font-family:Segoe UI,Arial,sans-serif;color:{NAVY};max-width:620px">
<h2 style="color:{NAVY};border-bottom:3px solid {ORANGE};padding-bottom:6px">Claude daily usage &mdash; combined</h2>
<p><b>Yesterday ({yesterday.strftime('%A %d %b')}):</b> {fmt_tokens(y_tokens)} tokens used,
worth about <b>${y_cost:,.2f}</b> if paid per-token.</p>
<table style="border-collapse:collapse;width:100%">
<tr style="background:{NAVY};color:#fff">
<th style="padding:6px 12px;text-align:left">Day</th>
<th style="padding:6px 12px;text-align:right">Tokens</th>
{machine_header}
<th style="padding:6px 12px;text-align:right">Value (USD)</th></tr>
{''.join(rows)}
<tr style="font-weight:bold;background:#f2f2f2">
<td style="padding:6px 12px">Last 7 days</td>
<td style="padding:6px 12px;text-align:right">{fmt_tokens(week_tokens)}</td>
{machine_total}
<td style="padding:6px 12px;text-align:right">${week_cost:,.2f}</td></tr>
</table>
<p style="font-size:12px;color:#666">Notes: You pay a fixed subscription, so the dollar figure is not a bill &mdash;
it shows what the same work would cost if paid per-token (a measure of how hard Claude worked for you).
Most tokens are "cache reads" (Claude re-reading the conversation), which are cheap.
This report covers {scope}.</p>
</div>
"""
    return subject, body


def main():
    win_daily = fetch_windows_usage()
    mac_daily = fetch_mac_usage()
    has_mac = len(mac_daily) > 0
    combined = combine_usage(win_daily, mac_daily)
    subject, body = build_email(combined, has_mac)

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(body)
        body_file = f.name

    r = subprocess.run(
        [PYTHON, str(SEND_MAIL), "--to", TO, "--subject", subject,
         "--body-file", body_file, "--html"],
        capture_output=True, text=True, timeout=120,
    )
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
