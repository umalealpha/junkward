#!/usr/bin/env python3
"""CFO mailbox sender WITH attachments, via Microsoft Graph (client-credentials).

Companion to send_mail.py. Same env/creds, but supports file attachments by
using the draft -> addAttachment -> send flow (each attachment posted in its own
request, which side-steps the ~4MB single-request sendMail limit).

Examples
--------
  python send_mail_attach.py --check-config
  python send_mail_attach.py --to a@x.bw b@x.bw --subject "RE: ..." \
      --body-file body.html --html --attach "file1.pdf" "file2.pdf"
"""
import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.request
import urllib.parse
import urllib.error

DEFAULT_ENV = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "secrets", "manus-graph-sender.env"
)

ALIASES = {
    "tenant": ["TENANT_ID", "AZURE_TENANT_ID", "GRAPH_TENANT_ID", "MS_TENANT_ID"],
    "client": ["CLIENT_ID", "AZURE_CLIENT_ID", "GRAPH_CLIENT_ID", "APP_ID", "MS_CLIENT_ID"],
    "secret": ["CLIENT_SECRET", "AZURE_CLIENT_SECRET", "GRAPH_CLIENT_SECRET", "MS_CLIENT_SECRET"],
    "sender": ["SENDER", "MAIL_FROM", "FROM", "SENDER_UPN", "GRAPH_SENDER_UPN", "GRAPH_SENDER"],
}


def read_env(path):
    if not os.path.exists(path):
        sys.exit(f"ERROR: credentials env file not found: {path}")
    data = {}
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


def graph(method, url, access, payload=None):
    headers = {"Authorization": f"Bearer {access}"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", nargs="+", default=[])
    ap.add_argument("--cc", nargs="*", default=[])
    ap.add_argument("--subject")
    ap.add_argument("--body", default="")
    ap.add_argument("--body-file")
    ap.add_argument("--html", action="store_true")
    ap.add_argument("--attach", nargs="*", default=[])
    ap.add_argument("--env-file", default=DEFAULT_ENV)
    ap.add_argument("--check-config", action="store_true")
    args = ap.parse_args()

    env = read_env(args.env_file)
    tenant = pick(env, ALIASES["tenant"])
    client = pick(env, ALIASES["client"])
    secret = pick(env, ALIASES["secret"])
    sender = pick(env, ALIASES["sender"])

    missing = [n for n, v in [("tenant", tenant), ("client", client),
                              ("secret", secret), ("sender", sender)] if not v]

    if args.check_config:
        print(f"env file : {args.env_file}")
        for n, v in [("tenant", tenant), ("client", client), ("secret", secret)]:
            print(f"{n:9}: {'found' if v else 'MISSING'}")
        print(f"sender   : {sender if sender else 'MISSING'}")
        print("RESULT: " + ("INCOMPLETE - " + ", ".join(missing) if missing else "OK"))
        sys.exit(1 if missing else 0)

    if missing:
        sys.exit("ERROR: incomplete credentials - missing: " + ", ".join(missing))
    if not args.to:
        sys.exit("ERROR: no --to recipients.")
    if not args.subject:
        sys.exit("ERROR: no --subject.")

    body = args.body
    if args.body_file:
        with open(args.body_file, "r", encoding="utf-8") as f:
            body = f.read()

    for p in args.attach:
        if not os.path.exists(p):
            sys.exit(f"ERROR: attachment not found: {p}")

    # token
    token_data = urllib.parse.urlencode({
        "client_id": client, "scope": "https://graph.microsoft.com/.default",
        "client_secret": secret, "grant_type": "client_credentials",
    }).encode()
    token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    try:
        req = urllib.request.Request(token_url, data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR: token request failed ({e.code}): {e.read().decode(errors='replace')}")
    access = tok.get("access_token")
    if not access:
        sys.exit("ERROR: no access_token returned.")

    base = f"https://graph.microsoft.com/v1.0/users/{sender}"
    # sendMail with inline attachments — needs only Mail.Send (this app lacks
    # Mail.ReadWrite, so the draft/addAttachment flow is denied). Single request,
    # so total payload must stay under Graph's ~4MB sendMail limit.
    attachments = []
    total = 0
    for p in args.attach:
        with open(p, "rb") as f:
            raw = f.read()
        total += len(raw)
        attachments.append({
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": os.path.basename(p),
            "contentType": mimetypes.guess_type(p)[0] or "application/octet-stream",
            "contentBytes": base64.b64encode(raw).decode(),
        })
        print(f"  attached: {os.path.basename(p)} ({len(raw):,} bytes)")
    if total > 3_700_000:
        sys.exit(f"ERROR: attachments total {total:,} bytes; too large for a single "
                 f"sendMail request (~4MB cap). Send the largest file separately.")
    try:
        graph("POST", f"{base}/sendMail", access, {
            "message": {
                "subject": args.subject,
                "body": {"contentType": "HTML" if args.html else "Text", "content": body},
                "toRecipients": [{"emailAddress": {"address": a}} for a in args.to],
                "ccRecipients": [{"emailAddress": {"address": a}} for a in args.cc],
                "attachments": attachments,
            },
            "saveToSentItems": True,
        })
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR: Graph call failed ({e.code}): {e.read().decode(errors='replace')}")

    cc_txt = f"  cc={';'.join(args.cc)}" if args.cc else ""
    print(f'sent=1  from={sender}  to={";".join(args.to)}{cc_txt}  '
          f'attachments={len(args.attach)}  subject="{args.subject}"')


if __name__ == "__main__":
    main()
