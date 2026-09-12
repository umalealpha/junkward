#!/usr/bin/env python3
"""Fable learning loop — the checklist grows itself, with CFO approval.

When a run catches a NEW mistake class (or prod breaks after a SHIP), Fable proposes a
checklist entry. It waits in a pending queue for a one-line CFO yes. On approval it lands
in the LEARNED section of omni-graphite-mistakes.md — so /fable catches tomorrow's mistakes,
not only yesterday's.

Guardrails (Fable): CFO approval per entry; capped; prune quarterly.

  checklist.py propose --id L1 --severity HIGH --title "..." --detail "..."
  checklist.py pending                       # show queue for CFO review
  checklist.py approve <id>                   # move one pending entry into the LEARNED section
  checklist.py reject  <id>                   # drop a pending entry
"""
import argparse, re, sys
from datetime import date
from pathlib import Path

REF = Path(__file__).resolve().parent.parent / "reference"
MAIN = REF / "omni-graphite-mistakes.md"
PENDING = REF / "pending-checklist.md"
CAP = 30  # learned-entry cap; warn past this, prune quarterly
MARK = "## LEARNED (CFO-approved, auto-grown)"

def read(p): return p.read_text() if p.exists() else ""

def blocks(text):
    """Parse '### <id> — ...' blocks into {id: full_block_text}."""
    out, cur, cid = {}, [], None
    for line in text.splitlines():
        m = re.match(r"^### (\S+)", line)
        if m:
            if cid: out[cid] = "\n".join(cur).rstrip()
            cid, cur = m.group(1), [line]
        elif cid:
            cur.append(line)
    if cid: out[cid] = "\n".join(cur).rstrip()
    return out

def do_propose(a):
    entry = f"### {a.id} — {a.title}\n**Severity:** {a.severity}. Proposed {date.today()}.\n{a.detail}\n"
    existing = blocks(read(PENDING))
    if a.id in existing or a.id in blocks(read(MAIN)):
        sys.exit(f"id {a.id} already exists (pending or checklist) — pick another.")
    with PENDING.open("a") as f:
        if not read(PENDING): f.write("# Pending checklist entries — awaiting CFO one-line approval\n\n")
        f.write("\n" + entry + "\n")
    print(f"proposed {a.id} → pending. CFO approves with: checklist.py approve {a.id}")

def do_pending(_):
    t = read(PENDING)
    print(t if t.strip() else "(no pending entries)")

def do_approve(a):
    pend = blocks(read(PENDING))
    if a.id not in pend: sys.exit(f"no pending entry {a.id}")
    main_txt = read(MAIN)
    if MARK not in main_txt:
        main_txt = main_txt.rstrip() + f"\n\n{MARK}\n"
    main_txt = main_txt.rstrip() + "\n\n" + pend[a.id] + "\n"
    MAIN.write_text(main_txt)
    # remove from pending
    remaining = "\n\n".join(v for k, v in blocks(read(PENDING)).items() if k != a.id)
    header = "# Pending checklist entries — awaiting CFO one-line approval\n"
    PENDING.write_text(header + ("\n" + remaining + "\n" if remaining.strip() else "\n"))
    total = len(re.findall(r"^### ", main_txt.split(MARK, 1)[1], re.M)) if MARK in main_txt else 0
    warn = f"  ⚠️ {total} learned entries — past cap {CAP}, prune soon." if total > CAP else ""
    print(f"approved {a.id} → checklist LEARNED section.{warn}")

def do_reject(a):
    pend = blocks(read(PENDING))
    if a.id not in pend: sys.exit(f"no pending entry {a.id}")
    remaining = "\n\n".join(v for k, v in pend.items() if k != a.id)
    header = "# Pending checklist entries — awaiting CFO one-line approval\n"
    PENDING.write_text(header + ("\n" + remaining + "\n" if remaining.strip() else "\n"))
    print(f"rejected {a.id} — dropped from pending.")

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("propose")
    for f in ("id", "severity", "title", "detail"): p.add_argument(f"--{f}", required=True)
    sub.add_parser("pending")
    for name in ("approve", "reject"):
        s = sub.add_parser(name); s.add_argument("id")
    a = ap.parse_args()
    {"propose": do_propose, "pending": do_pending, "approve": do_approve, "reject": do_reject}[a.cmd](a)

if __name__ == "__main__":
    main()
