#!/usr/bin/env python3
"""Fable run ledger — append-only history so repeat offences become visible.

Fable reads the last N entries during review ("this exact H5 was flagged 2 runs ago,
same file"). Also the audit trail behind every /fable deploy, and the feed for the
learning loop.

  ledger.py log --diff-hash X --verdict SHIP|FIX --system Omni \
      --issues '["H6","C6"]' --fixes '["payroll.py:15 remove except:pass"]' \
      --deploy-sha abc123 --postdeploy OK|FAIL|n/a --note "..."
  ledger.py tail [N]        # last N entries (default 5) as JSON, newest last
"""
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

LEDGER = Path(__file__).resolve().parent.parent / "runs.jsonl"

def do_log(a):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "system": a.system, "diff_hash": a.diff_hash, "verdict": a.verdict,
        "issues": json.loads(a.issues) if a.issues else [],
        "fixes": json.loads(a.fixes) if a.fixes else [],
        "deploy_sha": a.deploy_sha, "postdeploy": a.postdeploy, "note": a.note,
    }
    with LEDGER.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"logged: {entry['verdict']} {entry['diff_hash']} ({len(entry['issues'])} issues)")

def do_tail(n):
    if not LEDGER.exists():
        print("[]"); return
    lines = [l for l in LEDGER.read_text().splitlines() if l.strip()]
    rows = [json.loads(l) for l in lines[-n:]]
    print(json.dumps(rows, indent=2))

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    lg = sub.add_parser("log")
    for f in ("diff-hash", "verdict", "system", "issues", "fixes", "deploy-sha", "postdeploy", "note"):
        lg.add_argument(f"--{f}", default="")
    tl = sub.add_parser("tail")
    tl.add_argument("n", nargs="?", type=int, default=5)
    a = ap.parse_args()
    if a.cmd == "log":
        a.diff_hash = a.__dict__["diff_hash"]; a.deploy_sha = a.__dict__["deploy_sha"]
        do_log(a)
    else:
        do_tail(a.n)

if __name__ == "__main__":
    main()
