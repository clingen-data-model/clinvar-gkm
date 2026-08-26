# 0003 — Roadmap generated from label-authorized discussions

- **Status:** Accepted
- **Date:** 2026-08-26

## Context

The docs Roadmap should reflect community priorities without hand-editing a page for every idea, and without a
hand-maintained list that goes stale. GitHub Discussions already provide proposals, comments, and a built-in
**upvote** signal.

## Decision

The Roadmap table (`docs/reference/roadmap.md`, between `<!-- ROADMAP:START/END -->` markers) is
**auto-generated** from GitHub Discussions carrying the **`roadmap authorized`** label, ordered by upvote count
(desc). `src/scripts/generate-roadmap.py` produces it; the `deploy-docs` workflow runs it on discussion
events + a daily schedule + release/dispatch, then `mkdocs gh-deploy`.

- Governance: a community member opens an Ideas discussion; a maintainer **authorizes** it by adding the label
  (removing the label drops it). Status comes from an optional `status: <x>` label.
- Voting uses the **built-in Upvote** button (no emoji reactions, no downvote).

## Consequences

- Adding/removing/reordering roadmap items is done on the discussions, not in the repo — the site self-updates.
- Build-time generation only: the **live site** is always current; the committed `roadmap.md` table is a
  snapshot that can lag (a commit-back step could close that gap if the repo file view must match exactly).
- Upvote changes don't fire workflow events, so ordering refreshes on the daily schedule.
