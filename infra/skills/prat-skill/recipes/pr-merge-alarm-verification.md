# PR merge-alarm verification (added 2026-06-11, Smart UW / PR #1107 incident)

When ANYONE (TheRiskCo, a reviewer, another AI session) claims a PR "would
revert/delete recent work" or is "dangerously stale" — verify direction FIRST,
debate second. Two reversed-diff disputes were resolved this week by one command.

## The 30-second neutral check

```bash
gh pr view <N> --repo <org>/<repo> --json additions,deletions,changedFiles,mergeable,state
```

GitHub's PR stats are ALWAYS the three-dot diff (merge-base -> head) — the
branch's own changes, nothing else. If it says `deletions: 0`, the PR deletes
nothing, full stop.

## How the false alarm happens

A branch forked N commits ago. Reviewer diffs from the branch's side toward
main (`git diff feature...main`, or checks out the branch and compares), sees
main's own N commits of files as "missing", and reads that as "this PR removes
them". The mirror numbers are the tell: PR #1107 was +1,672/-0/18 files, the
alarm said "356 files, -3,834" — i.e. main's recent work viewed backwards.
Being behind is cosmetic; a normal merge keeps both sides.

## Genuine danger DOES exist when…

- The PR diff ITSELF shows deletions of files the branch never touched
  (snapshot-commit from a stale clone — the whole working tree was committed).
- A merge of main into the branch was resolved with `-X ours` / wholesale
  "keep mine" conflict resolution.
Check: `git diff --stat $(git merge-base origin/main HEAD) HEAD` — if that
shows the deletions too, the alarm is real.

## Fix-forward playbook (what worked)

1. Rebase the branch onto origin/main (purely-additive branches rebase with
   zero conflicts) -> `git push --force-with-lease`.
2. **GitHub will NOT reopen a closed PR after a force-push to its head** —
   don't fight it; open a superseding PR that references the old number.
3. Reply with evidence, not blame: quote GitHub's own stats, explain the
   mirror-image numbers, link the new PR. Email via omni@ Graph backend,
   cc CFO + EXCO.

## Root-cause prevention (our side)

- Multiple parallel Claude sessions sharing one clone = branch races and
  snapshot commits. EVERY session takes its own `git worktree add` — that is
  what kept the SOP Bank branch clean while 6 forks ran.
- Never commit from a stale OneDrive copy of a repo; fresh clone or worktree.
