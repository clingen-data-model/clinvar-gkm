---
description: Brief me on what changed in the repo since I last synced, focused on the files I'm about to touch.
---

You are catching a contributor up on repo changes since they last synced. Produce a tight briefing, not a
changelog dump. The moving picture is derived from git + GitHub — never from a hand-maintained doc.

Steps:

1. `git fetch --tags origin` and establish the range. If the user named a range or area, use it. Otherwise
   default to merged work in the last two weeks: `git log --oneline --since="2 weeks ago" origin/main`.
2. List merged PRs in range:
   `gh pr list --state merged --base main --limit 50 --json number,title,mergedAt,url,files` and keep those
   whose `mergedAt` is in range.
3. Read the bodies of the PRs that touch the **files or subsystem the user is about to work on** (ask what
   that is if they didn't say): `gh pr view <n>` for the description and the relevant commits.
4. Read anything new or changed under `docs/decisions/` (ADRs) and any changed `.claude/rules/*.md` or
   `CLAUDE.md` — convention changes matter most.
5. Summarize, in a few bullets:
   - what landed and why (from the PR body / ADR),
   - what it means for the files the user named,
   - any **convention or interface changes** they need to adopt,
   - open follow-ups called out in those PRs.

Keep it short. Link PRs/ADRs by number so they can drill in.
