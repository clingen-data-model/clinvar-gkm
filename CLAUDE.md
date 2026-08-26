# CLAUDE.md

Project-wide invariants for ClinVar-GKM. Keep this file short (< ~200 lines) and limited to things that are
true across the whole repo. Path-specific conventions live in `.claude/rules/` (loaded only when working on
matching files); one-off decisions live in `docs/decisions/` (ADRs). This file is shared context — change it
via PR review.

## General Rules

- Only modify files explicitly requested by the user. Do not proactively edit test files, SQL files, or other
  files beyond the scope of the current request without asking first.
- Don't assume. Don't hide confusion. Surface tradeoffs.
- Minimum code that solves the problem. Nothing speculative.
- Touch only what you must. Clean up only your own mess.
- Define success criteria. Loop until verified.

## Project Context

ClinVar-GKM transforms ClinVar XML releases into the GKM (Genomic Knowledge Model) schema set — VRS, Cat-VRS,
VA-Spec — curated by the GA4GH GKS (Genomic Knowledge Standards) workstream. BigQuery SQL stored procedures in
`src/procedures/` do the heavy lifting; release orchestration is in `src/scripts/`. Output is a JSON bundle plus
typed Parquet, distributed via Cloudflare R2. Documentation lives in `docs/` (MkDocs Material).

## Git Conventions

- Default branch is `main`. Do work on a branch; land changes via PR review.
- Do NOT include "Generated with Claude Code" or "Co-Authored-By: Claude" in commits.
- Keep commit messages clean and focused on the changes.

## Where the rest lives

- **Path-specific conventions** — `.claude/rules/*.md`, auto-loaded when working on matching paths:
  - [`sql-procedures.md`](.claude/rules/sql-procedures.md) — dynamic SQL, BigQuery gotchas, naming,
    oracle-gating (`src/procedures/**`)
  - [`scripts.md`](.claude/rules/scripts.md) — bash 3.2, R2/Cloudflare, `bq`/`gh` gotchas
    (`src/scripts/**`, `src/vrsify/**`)
  - [`docs.md`](.claude/rules/docs.md) — MkDocs `--strict`, terminology, roadmap generation (`docs/**`)
- **Architectural decisions** — [`docs/decisions/`](docs/decisions/) (ADRs, one per decision). Fuller design
  specs are in `docs/superpowers/specs/`.
- **What changed since you last looked** — run `/catchup` (`.claude/commands/catchup.md`): it diffs `git log`,
  reads merged PR bodies + new ADRs, and briefs you on changes relevant to the files you're about to touch.
  Don't hand-maintain a "team memory" doc — derive the moving picture from git + GitHub.
