#!/usr/bin/env python3
"""One-shot email sender for the CFO mailbox via Microsoft Graph (client-credentials).

Windows parity for the Mac Mini "Prat" manus-graph-sender. Standard library only -
no pip installs required (urllib + json).

Reads Graph app credentials from an env file (never from the command line / chat),
gets an app-only token, and sends mail as the configured sender, saving to Sent Items.

Examples
--------
  # validate the env/creds without sending
  python send_mail.py --check-config

  # send (long bodies: put the text in a file and use --body-file)
  python send_mail.py --to ktshutlhedi@alphadirect.co.bw \
                      --cc btendani@alphadirect.co.bw \
                      --subject "RE: ..." --body-file body.txt
"""
import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import urllib.request
import urllib.parse
import urllib.error

# A body is treated as HTML if it contains a real HTML tag (so rich-formatted emails
# render as HTML even when --html is forgotten). A lone "<" (e.g. "EBITDA < target")
# does NOT trigger it — only a recognised tag does.
_HTML_TAG = re.compile(
    r"<(?:html|body|div|p|br|table|tr|t[dh]|thead|tbody|h[1-6]|ul|ol|li|strong|em|b|i|u|span|a|img|hr|font|style|center)\b[^>]*>",
    re.I,
)

DEFAULT_ENV = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "secrets", "manus-graph-sender.env"
)

# Accept whatever key names the Mac env happens to use.
ALIASES = {
    "tenant": ["TENANT_ID", "AZURE_TENANT_ID", "GRAPH_TENANT_ID", "MS_TENANT_ID", "MICROSOFT_TENANT_ID"],
    "client": ["CLIENT_ID", "AZURE_CLIENT_ID", "GRAPH_CLIENT_ID", "APP_ID", "MS_CLIENT_ID", "MICROSOFT_CLIENT_ID"],
    "secret": ["CLIENT_SECRET", "AZURE_CLIENT_SECRET", "GRAPH_CLIENT_SECRET", "MS_CLIENT_SECRET", "MICROSOFT_CLIENT_SECRET"],
    "sender": ["SENDER", "MAIL_FROM", "FROM", "SENDER_UPN", "GRAPH_SENDER_UPN", "GRAPH_SENDER", "MICROSOFT_SENDER_UPN"],
}


def read_env(path):
    if not os.path.exists(path):
        sys.exit(
            f"ERROR: credentials env file not found: {path}\n"
            f"Drop the Mac's manus-graph-sender.env there (see the .example for keys)."
        )
    data = {}
    # utf-8-sig transparently strips a leading BOM so the first key always parses,
    # whichever editor/OS saved the env file.
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def pick(env, names):
    for n in names:
        if env.get(n):
            return env[n]
    return None


def omni_access_problems(recipients, body):
    """Ask live Omni whether each recipient can reach every Omni page mentioned in
    *body*. Runs `manage.py check_recipient_access` on the production box via AWS
    SSM (read-only). Returns a list of plain-English problems ([] = all fine), or
    None when the check itself could not run. Never raises."""
    import subprocess, tempfile, time
    staff = [r for r in recipients if r and "@" in r
             and not r.lower().startswith(("excoboard@", "omni@", "admin@"))]
    if not staff:
        return []
    try:
        b64 = base64.b64encode(body.encode("utf-8")).decode()
        emails = " ".join(staff)
        shell = (f"echo {b64} | base64 -d > /tmp/_acc_body.html && "
                 f"sudo docker exec -i alpha-finance-backend python manage.py check_recipient_access "
                 f"--email {emails} --body-file /tmp/_acc_body.html 2>/dev/null; rm -f /tmp/_acc_body.html")
        # The body itself may hold the page; the command reads the file inside the container
        # only if the path exists there - so copy it in first.
        shell = (f"echo {b64} | base64 -d > /tmp/_acc_body.html && "
                 f"sudo docker cp /tmp/_acc_body.html alpha-finance-backend:/tmp/_acc_body.html && "
                 f"sudo docker exec alpha-finance-backend python manage.py check_recipient_access "
                 f"--email {emails} --body-file /tmp/_acc_body.html 2>/dev/null; rm -f /tmp/_acc_body.html")
        params = json.dumps({"commands": [shell], "executionTimeout": ["120"]})
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            fh.write(params); pfile = fh.name
        cid = subprocess.run(
            ["aws", "ssm", "send-command", "--profile", "claude-cli", "--region", "af-south-1",
             "--instance-ids", "i-02a5d76a61f4f09a5", "--document-name", "AWS-RunShellScript",
             "--parameters", "file://" + pfile.replace("\\", "/"),
             "--query", "Command.CommandId", "--output", "text"],
            capture_output=True, text=True, timeout=60).stdout.strip()
        if not cid:
            return None
        out = ""
        for _ in range(40):
            time.sleep(3)
            r = subprocess.run(
                ["aws", "ssm", "get-command-invocation", "--profile", "claude-cli", "--region", "af-south-1",
                 "--command-id", cid, "--instance-id", "i-02a5d76a61f4f09a5",
                 "--query", "[Status,StandardOutputContent]", "--output", "json"],
                capture_output=True, text=True, timeout=60)
            try:
                status, out = json.loads(r.stdout or "[]")
            except Exception:
                continue
            if status in ("Success", "Failed"):
                break
        else:
            return None
        line = next((l for l in (out or "").splitlines() if l.strip().startswith("{")), "")
        if not line:
            return None
        data = json.loads(line)
        return [f"{v['email']} -> {v['path']}: {v['reason']}" for v in data.get("verdicts", []) if not v.get("ok")]
    except Exception as exc:  # noqa: BLE001
        print(f"access check skipped: {exc}")
        return None


def main():
    ap = argparse.ArgumentParser(description="Send mail as the CFO via Microsoft Graph.")
    ap.add_argument("--to", nargs="+", default=[], help="recipient address(es)")
    ap.add_argument("--cc", nargs="*", default=[], help="cc address(es)")
    ap.add_argument("--subject")
    ap.add_argument("--body", default="")
    ap.add_argument("--body-file", help="read the body from this file (overrides --body)")
    ap.add_argument("--attach", nargs="*", default=[], help="file(s) to attach (e.g. a screenshot)")
    ap.add_argument("--html", action="store_true", help="force body as HTML (HTML is also auto-detected)")
    ap.add_argument("--text", action="store_true", help="force plain Text (override HTML auto-detect)")
    ap.add_argument("--env-file", default=DEFAULT_ENV)
    ap.add_argument("--check-config", action="store_true",
                    help="validate env/creds only; do NOT send")
    ap.add_argument("--skip-access-check", action="store_true",
                    help="send even if a recipient cannot reach an Omni page the body points to "
                         "(CFO 2026-09-05: by default such a mail is BLOCKED and the reason shown)")
    args = ap.parse_args()

    env = read_env(args.env_file)
    tenant = pick(env, ALIASES["tenant"])
    client = pick(env, ALIASES["client"])
    secret = pick(env, ALIASES["secret"])
    sender = pick(env, ALIASES["sender"])

    missing = [name for name, val in [
        ("tenant id", tenant), ("client id", client),
        ("client secret", secret), ("sender", sender),
    ] if not val]

    if args.check_config:
        print(f"env file : {args.env_file}")
        print(f"tenant id: {'found' if tenant else 'MISSING'}")
        print(f"client id: {'found' if client else 'MISSING'}")
        print(f"secret   : {'found' if secret else 'MISSING'}")
        print(f"sender   : {sender if sender else 'MISSING'}")
        if missing:
            print("RESULT: INCOMPLETE - missing: " + ", ".join(missing))
            sys.exit(1)
        print("RESULT: OK - config complete, ready to send.")
        sys.exit(0)

    if missing:
        sys.exit("ERROR: incomplete credentials in env file - missing: " + ", ".join(missing))
    if not args.to:
        sys.exit("ERROR: no --to recipients.")
    if not args.subject:
        sys.exit("ERROR: no --subject.")

    body = args.body
    if args.body_file:
        if not os.path.exists(args.body_file):
            sys.exit(f"ERROR: body file not found: {args.body_file}")
        with open(args.body_file, "r", encoding="utf-8") as f:
            body = f.read()

    # 0. CFO control (2026-09-05): never ASK someone to do something in Omni
    #    they cannot get to. If the body links to an Omni page, every recipient
    #    is checked on the live system first; anyone who cannot sign in or
    #    cannot open that page blocks the send, and the reason is printed.
    if not args.skip_access_check and "omni.alphadirect.co.bw" in body:
        problems = omni_access_problems(args.to + list(args.cc or []), body)
        if problems is None:
            print("WARNING: could not run the Omni access check (offline?) - sending anyway.")
        elif problems:
            print("BLOCKED - this email asks people to act in Omni, but:")
            for line in problems:
                print("  - " + line)
            print("Fix their access first, or re-run with --skip-access-check if the email is only informational.")
            sys.exit(3)
        else:
            print("access check: every recipient can reach the Omni page(s) in this email.")

    # 1. app-only token (client-credentials)
    token_data = urllib.parse.urlencode({
        "client_id": client,
        "scope": "https://graph.microsoft.com/.default",
        "client_secret": secret,
        "grant_type": "client_credentials",
    }).encode()
    token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    try:
        req = urllib.request.Request(
            token_url, data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR: token request failed ({e.code}): {e.read().decode(errors='replace')}")
    access = tok.get("access_token")
    if not access:
        sys.exit("ERROR: no access_token returned.")

    # 2. build + send message
    # Rich-text emails: send as HTML when forced (--html) OR auto-detected, unless --text forces plain.
    is_html = (args.html or bool(_HTML_TAG.search(body))) and not args.text
    content_type = "HTML" if is_html else "Text"
    msg = {
        "message": {
            "subject": args.subject,
            "body": {"contentType": content_type, "content": body},
            "toRecipients": [{"emailAddress": {"address": a}} for a in args.to],
            "ccRecipients": [{"emailAddress": {"address": a}} for a in args.cc],
        },
        "saveToSentItems": True,
    }
    if args.attach:
        atts = []
        for path in args.attach:
            if not os.path.exists(path):
                sys.exit(f"ERROR: attachment not found: {path}")
            with open(path, "rb") as fh:
                content = base64.b64encode(fh.read()).decode()
            ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
            atts.append({
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": os.path.basename(path),
                "contentType": ctype,
                "contentBytes": content,
            })
        msg["message"]["attachments"] = atts
    send_url = f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail"
    try:
        req = urllib.request.Request(
            send_url, data=json.dumps(msg).encode(),
            headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR: sendMail failed ({e.code}): {e.read().decode(errors='replace')}")

    cc_txt = f"  cc={';'.join(args.cc)}" if args.cc else ""
    print(f'sent=1  from={sender}  to={";".join(args.to)}{cc_txt}  body={content_type}  subject="{args.subject}"')


if __name__ == "__main__":
    main()
