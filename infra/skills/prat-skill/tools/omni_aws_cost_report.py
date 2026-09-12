#!/usr/bin/env python3
"""Monthly AWS cost-analysis email for Alpha Direct (omni account 623467544388).

Self-contained: pulls fresh figures from AWS Cost Explorer via the local `claude-cli`
profile, builds a branded rich-HTML report, and sends it via the local Graph sender
(send_mail.py). No secrets are embedded. Designed to run unattended from Windows Task
Scheduler at 06:00 on the 25th of each month.

Reports the PREVIOUS COMPLETE calendar month (final, fully-billed figures).

Usage:
  python omni_aws_cost_report.py --dry-run     # build HTML only, print recipients, no send
  python omni_aws_cost_report.py --test        # send ONLY to the CFO, subject prefixed [TEST]
  python omni_aws_cost_report.py               # live: send to the full distribution list
"""
import argparse
import calendar
import datetime
import json
import os
import subprocess
import sys
import tempfile

# Local runs use the claude-cli profile; on the omni server set OMNI_COST_AWS_PROFILE=
# (empty) so the EC2 instance role is used instead.
PROFILE = os.environ.get("OMNI_COST_AWS_PROFILE", "claude-cli")
SEND_MAIL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "send_mail.py")
# Optional override for the Graph credentials env file (server uses omni's own creds).
GRAPH_ENV = os.environ.get("OMNI_COST_GRAPH_ENV", "")
NAVY, ORANGE = "#1D3270", "#F47C20"

# Resolved 2026-06-29 from omni-staff-directory.md (never guess addresses).
RECIPIENTS = [
    "pbisen@theriskco.com",        # Pramod Bisen (TheRiskCo)
    "arjuniyer@alphadirect.co.bw", # Arjun Iyer
    "aiyer@alphadirect.co.bw",     # Arun Iyer (exec)
    "lntabeni@alphadirect.co.bw",  # Legakwa Ntabeni
    "pkago@alphadirect.co.bw",     # Pako Kago (Financial Controller)
    "ktshutlhedi@alphadirect.co.bw", # Kago Tshutlhedi (Finance Manager)
]
CFO = "pganesharajah@alphadirect.co.bw"


def aws_json(args):
    """Run an aws-cli command with the claude-cli profile and return parsed JSON."""
    cmd = ["aws"] + args + ["--output", "json"]
    if PROFILE:
        cmd += ["--profile", PROFILE]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError("aws failed: " + " ".join(args) + "\n" + out.stderr[:500])
    return json.loads(out.stdout)


def prev_month_window(today):
    """Return (report_start, report_end, label, trend_start) for the previous full month."""
    first_this = today.replace(day=1)
    report_end = first_this                                   # exclusive
    last_prev = first_this - datetime.timedelta(days=1)
    report_start = last_prev.replace(day=1)
    # trend: 4 months ending at the report month
    y, m = report_start.year, report_start.month
    tm = m - 3
    ty = y
    while tm <= 0:
        tm += 12
        ty -= 1
    trend_start = datetime.date(ty, tm, 1)
    label = report_start.strftime("%B %Y")
    return report_start, report_end, label, trend_start


def fmt(n):
    return "${:,.0f}".format(n)


def classify_rds(usage_type):
    u = usage_type
    if "Bytes" in u:
        return "Data transfer"
    if "Backup" in u or "Snapshot" in u:
        return "Backup / snapshots"
    if "Storage" in u or "PIOPS" in u:
        return "Storage (SSD)"
    if "InstanceUsage" in u or "Multi-AZUsage" in u:
        return "DB instance compute"
    return "Other"


def bar(pct, color):
    pct = max(0.4, min(100.0, pct))
    return ('<div style="background:%s;height:18px;width:%.1f%%;border-radius:3px;">'
            '</div>' % (color, pct))


def build_html(today):
    rs, re, label, ts = prev_month_window(today)
    s, e = rs.isoformat(), re.isoformat()

    # --- pulls ---
    by_service = aws_json(["ce", "get-cost-and-usage", "--time-period",
        "Start=%s,End=%s" % (s, e), "--granularity", "MONTHLY", "--metrics", "UnblendedCost",
        "--group-by", "Type=DIMENSION,Key=SERVICE"])
    svc = [(g["Keys"][0], float(g["Metrics"]["UnblendedCost"]["Amount"]))
           for g in by_service["ResultsByTime"][0]["Groups"]]
    svc = sorted(svc, key=lambda x: -x[1])
    total = sum(v for _, v in svc)

    by_region = aws_json(["ce", "get-cost-and-usage", "--time-period",
        "Start=%s,End=%s" % (s, e), "--granularity", "MONTHLY", "--metrics", "UnblendedCost",
        "--group-by", "Type=DIMENSION,Key=REGION"])
    reg = [(g["Keys"][0], float(g["Metrics"]["UnblendedCost"]["Amount"]))
           for g in by_region["ResultsByTime"][0]["Groups"]]
    reg = sorted([r for r in reg if r[1] > 0.5], key=lambda x: -x[1])

    rds_ut = aws_json(["ce", "get-cost-and-usage", "--time-period",
        "Start=%s,End=%s" % (s, e), "--granularity", "MONTHLY", "--metrics", "UnblendedCost",
        "--filter", '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Relational Database Service"]}}',
        "--group-by", "Type=DIMENSION,Key=USAGE_TYPE"])
    rds_cat = {}
    rds_total = 0.0
    for g in rds_ut["ResultsByTime"][0]["Groups"]:
        amt = float(g["Metrics"]["UnblendedCost"]["Amount"])
        rds_total += amt
        rds_cat[classify_rds(g["Keys"][0])] = rds_cat.get(classify_rds(g["Keys"][0]), 0) + amt

    trend = aws_json(["ce", "get-cost-and-usage", "--time-period",
        "Start=%s,End=%s" % (ts.isoformat(), e), "--granularity", "MONTHLY", "--metrics", "UnblendedCost"])
    months = [(t["TimePeriod"]["Start"], float(t["Total"]["UnblendedCost"]["Amount"]))
              for t in trend["ResultsByTime"]]

    rds_share = (rds_total / total * 100) if total else 0
    prior = months[-2][1] if len(months) >= 2 else None
    mom = ((total - prior) / prior * 100) if prior else None

    # --- HTML ---
    def svc_rows():
        rows = ""
        top = svc[:6]
        other = sum(v for _, v in svc[6:])
        maxv = svc[0][1] if svc else 1
        for name, v in top:
            rows += ('<tr><td width="150" style="padding:5px 0;font-size:13px;">%s</td>'
                     '<td style="padding:5px 8px;">%s</td>'
                     '<td width="120" align="right" style="padding:5px 0;font-weight:700;font-size:13px;">%s &middot; %.1f%%</td></tr>'
                     % (name, bar(v / maxv * 100, NAVY), fmt(v), v / total * 100))
        if other > 0:
            rows += ('<tr><td style="padding:5px 0;font-size:13px;color:#6b7280;">All other services</td>'
                     '<td style="padding:5px 8px;">%s</td>'
                     '<td align="right" style="padding:5px 0;font-weight:700;font-size:13px;color:#6b7280;">%s &middot; %.1f%%</td></tr>'
                     % (bar(other / maxv * 100, "#c4cce4"), fmt(other), other / total * 100))
        return rows

    def reg_rows():
        rows = ""
        for name, v in reg[:8]:
            nm = name if name not in ("NoRegion", "global") else name + " (tax/global)"
            rows += ('<tr><td style="padding:6px 12px;font-size:13px;">%s</td>'
                     '<td align="right" style="padding:6px 12px;font-size:13px;font-weight:700;">%s</td>'
                     '<td align="right" style="padding:6px 12px;font-size:13px;">%.1f%%</td></tr>'
                     % (nm, fmt(v), v / total * 100))
        return rows

    def rds_rows():
        order = ["DB instance compute", "Storage (SSD)", "Backup / snapshots", "Data transfer", "Other"]
        rows = ""
        for k in order:
            if rds_cat.get(k, 0) <= 0:
                continue
            v = rds_cat[k]
            rows += ('<tr><td style="padding:8px 12px;font-size:13px;font-weight:600;">%s</td>'
                     '<td align="right" style="padding:8px 12px;font-size:13px;font-weight:700;">%s</td>'
                     '<td align="right" style="padding:8px 12px;font-size:13px;">%.0f%%</td></tr>'
                     % (k, fmt(v), v / rds_total * 100 if rds_total else 0))
        return rows

    def trend_bars():
        maxv = max(v for _, v in months) if months else 1
        cells_top, cells_bot = "", ""
        shades = ["#9aa9d6", "#6c7fc0", "#3a57a8", NAVY]
        for i, (mon, v) in enumerate(months):
            h = int(40 + (v / maxv) * 90)
            color = shades[i] if i < len(shades) else NAVY
            mlabel = datetime.date.fromisoformat(mon).strftime("%b")
            cells_top += ('<td align="center" width="%d%%"><div style="background:%s;width:46px;height:%dpx;'
                          'margin:0 auto;border-radius:4px 4px 0 0;"></div></td>' % (100 // max(1, len(months)), color, h))
            cells_bot += ('<td align="center" style="padding-top:6px;font-size:12px;">%s<br><strong>%s</strong></td>'
                          % (mlabel, fmt(v)))
        return cells_top, cells_bot

    top_cells, bot_cells = trend_bars()
    mom_txt = ("up %.1f%% vs prior month" % mom) if (mom and mom > 0) else \
              ("down %.1f%% vs prior month" % abs(mom)) if mom else ""
    biggest = svc[0][0] if svc else "n/a"

    html = """<div style="margin:0;padding:0;background:#eef0f4;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1a2236;">
<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" style="background:#eef0f4;padding:18px 0;"><tr><td align="center">
<table role="presentation" width="680" cellpadding="0" cellspacing="0" style="width:680px;max-width:680px;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,0.08);">
<tr><td style="background:%(navy)s;padding:24px 30px;border-bottom:4px solid %(orange)s;">
  <div style="font-size:12px;letter-spacing:2px;color:#9fb0d8;text-transform:uppercase;font-weight:600;">Alpha Direct Insurance &middot; Finance / IT</div>
  <div style="font-size:22px;color:#fff;font-weight:700;margin-top:6px;">AWS Cost Analysis &mdash; %(label)s</div>
  <div style="font-size:13px;color:#cdd7ee;margin-top:7px;">Account 623467544388 &middot; previous-month actuals from AWS Cost Explorer &middot; automated monthly report</div>
</td></tr>
<tr><td style="padding:22px 30px 6px 30px;">
  <table role="presentation" width="100%%" cellpadding="0" cellspacing="0" style="background:#fbf3ec;border-left:4px solid %(orange)s;border-radius:6px;"><tr><td style="padding:15px 18px;font-size:14px;line-height:1.6;color:#3a2a1a;">
  <strong style="color:%(navy)s;">%(label)s total: %(total)s</strong> &mdash; %(mom)s. The largest service is <strong>%(biggest)s</strong>. Databases (RDS) account for <strong>%(rdss).0f%% of the bill (%(rdst)s)</strong>.
  </td></tr></table>
</td></tr>
<tr><td style="padding:20px 30px 4px 30px;"><div style="font-size:16px;font-weight:700;color:%(navy)s;border-bottom:2px solid #e6e9f0;padding-bottom:7px;">1 &nbsp;Where the money goes</div></td></tr>
<tr><td style="padding:10px 30px 6px 30px;"><table role="presentation" width="100%%" cellpadding="0" cellspacing="0">%(svc)s</table></td></tr>
<tr><td style="padding:20px 30px 4px 30px;"><div style="font-size:16px;font-weight:700;color:%(navy)s;border-bottom:2px solid #e6e9f0;padding-bottom:7px;">2 &nbsp;RDS (databases) &mdash; %(rdst)s</div></td></tr>
<tr><td style="padding:10px 30px 6px 30px;"><table role="presentation" width="100%%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
  <tr style="background:%(navy)s;color:#fff;"><th align="left" style="padding:8px 12px;font-size:13px;">Category</th><th align="right" style="padding:8px 12px;font-size:13px;">$/mo</th><th align="right" style="padding:8px 12px;font-size:13px;">%%</th></tr>
  %(rds)s
</table></td></tr>
<tr><td style="padding:20px 30px 4px 30px;"><div style="font-size:16px;font-weight:700;color:%(navy)s;border-bottom:2px solid #e6e9f0;padding-bottom:7px;">3 &nbsp;Cost by region</div></td></tr>
<tr><td style="padding:10px 30px 6px 30px;"><table role="presentation" width="100%%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
  <tr style="background:#f6f7fb;"><th align="left" style="padding:6px 12px;font-size:12px;color:#6b7280;">Region</th><th align="right" style="padding:6px 12px;font-size:12px;color:#6b7280;">$/mo</th><th align="right" style="padding:6px 12px;font-size:12px;color:#6b7280;">share</th></tr>
  %(reg)s
</table></td></tr>
<tr><td style="padding:20px 30px 4px 30px;"><div style="font-size:16px;font-weight:700;color:%(navy)s;border-bottom:2px solid #e6e9f0;padding-bottom:7px;">4 &nbsp;Trend</div></td></tr>
<tr><td style="padding:14px 30px 6px 30px;"><table role="presentation" width="100%%" cellpadding="0" cellspacing="0">
  <tr valign="bottom" style="height:140px;">%(topc)s</tr><tr style="border-top:2px solid %(navy)s;">%(botc)s</tr>
</table></td></tr>
<tr><td style="padding:20px 30px 26px 30px;"><div style="border-top:1px solid #e6e9f0;padding-top:14px;font-size:11px;color:#9098a8;line-height:1.6;">
  Automated report generated %(gen)s from AWS Cost Explorer unblended actuals for %(label)s, account 623467544388. USD; scales with tax. Sent monthly on the 25th to Finance + IT + TheRiskCo. Questions: reply to this mail.
</div></td></tr>
</table></td></tr></table></div>""" % dict(
        navy=NAVY, orange=ORANGE, label=label, total=fmt(total), mom=mom_txt or "month-over-month n/a",
        biggest=biggest, rdss=rds_share, rdst=fmt(rds_total), svc=svc_rows(), rds=rds_rows(),
        reg=reg_rows(), topc=top_cells, botc=bot_cells, gen=today.isoformat())
    return html, label, total, rds_total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test", action="store_true")
    # --today lets a test pin the run date; live runs use the real date.
    ap.add_argument("--today", help="YYYY-MM-DD override for testing")
    args = ap.parse_args()

    today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
    html, label, total, rds_total = build_html(today)

    recips = [CFO] if args.test else RECIPIENTS
    subject = ("[TEST] " if args.test else "") + "Alpha Direct - AWS Cost Analysis - " + label

    if args.dry_run:
        fn = os.path.join(tempfile.gettempdir(), "omni_cost_%s.html" % label.replace(" ", "_"))
        with open(fn, "w", encoding="utf-8") as f:
            f.write(html)
        print("DRY-RUN ok")
        print("month=%s total=%s rds=%s" % (label, fmt(total), fmt(rds_total)))
        print("recipients=%s" % ", ".join(recips))
        print("html=%s (%d bytes)" % (fn, len(html)))
        return

    bf = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8")
    bf.write(html)
    bf.close()
    cmd = [sys.executable, SEND_MAIL, "--to"] + recips + ["--subject", subject, "--html", "--body-file", bf.name]
    if GRAPH_ENV:
        cmd += ["--env-file", GRAPH_ENV]
    r = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    os.unlink(bf.name)
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
