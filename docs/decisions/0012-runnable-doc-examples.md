# 0012 — Documentation examples must run, and say what they need

- **Status:** Proposed
- **Date:** 2026-11-21

## Context

The docs carry about 120 runnable code blocks (shell, Python, SQL, R) across about 25 pages: downloading
bundles and Parquet, querying with DuckDB, reading records with the GA4GH Python libraries, building Parquet with
`gkm-bundle-parquet`, and running the release pipeline. Readers copy them as written. Nothing checked them: an
example could break when a URL moved between data lines, a column was renamed, a package changed, or an earlier
block it relied on was edited, and the page gave no sign. Some examples also assumed tools the page never named
(a DuckDB extension, a Python package, a GNU-only command on macOS), so a new reader couldn't tell what to install.

Two pages already open with a `!!! note "Prerequisites"` admonition; most don't.

## Decision

1. **Every runnable example runs as written** against the published data of the docs line it belongs to (the
   `v1/{major}.{minor}/` folder the page describes), on macOS and Linux, in a clean environment set up the way
   the page says. A block that isn't meant to run as written (a fragment, pseudocode, a template with
   placeholders) is fenced as `text`, or says so in the sentence that introduces it.
   Examples use URLs that keep working: a stable name (`…_00-latest…`), a file that never moves, or a dated file
   looked up in the line's `index.json`. A path that moves (a current-month delta, which moves to its month's
   folder when the month ends; a weekly full, which is deleted at rollover; ADR 0009) is not written into a
   command. `curl` runs with `-f`, so a missing file fails instead of being saved as an error page.
2. **Every page with a runnable example states its prerequisites** before the first example, in a
   `!!! note "Prerequisites"` admonition, or links to the page that does. It names:
    - each tool and package, with its install command or a link to its install page;
    - the language or tool version the examples were tested with (Python, DuckDB, R, `gkm-bundle-parquet`), and
      the minimum when one is known;
    - the data each example reads, with a link to where to download it;
    - access the reader must already have (a GCP project, `bq` auth, R2 credentials), on maintainer pages;
    - expected download size, disk, memory and run time when they exceed what a laptop handles in a minute or
      two (a full bundle is about 5 GB compressed and must be streamed, not loaded).
3. **Dependencies between blocks are stated.** A block that uses a variable, view, macro, file or function made
   by an earlier block says which one ("continues from *Load the bundle* above").
4. **Platform differences are handled in the example.** Use a portable command or show both forms
   (`sha256sum` / `shasum -a 256`); don't use GNU-only flags without a macOS note.
5. **Examples that cost money or write somewhere say so.** Maintainer commands that run billable BigQuery jobs,
   write to GCS or R2, or execute Cloud Run jobs carry a warning and name the access they need. Reader-facing
   examples never need credentials.
6. **Shown output matches the current release.** `text` output blocks and prose that describe results (column
   names, counts, shapes) are refreshed when the data line changes; counts may be marked as approximate.
7. **Verification.** The examples on a page are run when the page changes, and every runnable example on the
   latest line is run before a minor release's docs are published. Frozen older lines (ADR 0008) are not
   retrofitted; their pages already say they aren't current.

## Consequences

- Writing an example now includes running it from a clean environment and filling in the page's
  Prerequisites note. Reviewers can ask for both.
- Release prep gains a step: run the latest line's examples before its docs publish (ADR 0011). Until it is
  automated this is a manual pass; a follow-up should add a script that extracts the fenced blocks and runs them
  against a small fixture (a delta bundle, a Parquet sample) in CI, with the release-time pass covering the
  full-size data.
- Pages pin the versions they were tested with, so a dependency release that breaks an example shows up as a
  version mismatch rather than a silent failure.
- The 2026-11-21 audit that prompted this ADR, and the fixes it led to, are recorded in the pull request that
  adds it.
