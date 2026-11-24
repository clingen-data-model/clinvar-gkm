# Docs restructure — progressive disclosure (newcomer → practitioner → expert)

- **Date:** 2026-11-23
- **Status:** Approved (maintainer); skeleton in progress
- **Scope target:** `1.0` branch (the source of the `1.2` docs line, ADR 0011)
- **Primary files:** `zensical.toml` (nav), new pages under `docs/start/`, `docs/build/`,
  `docs/data-access/keep-current.md`, `docs/pipeline/value-provenance.md`; later content edits to existing pages
- **Related:** [ADR 0011](../../docs/decisions/0011-versioned-documentation.md) (versioned docs),
  [ADR 0012](../../docs/decisions/0012-runnable-doc-examples.md) (runnable examples, Prerequisites notes)

## 1. Problem

New readers are overwhelmed, and the readers who stay can't find the workflows they need:

- **The first command is a 4.9 GB download.** The Home page's "Getting Started" opens with the full monthly
  bundle. Nothing smaller — a Parquet table, a delta, the browser console, one example record — comes first.
- **About 80 class pages sit in the sidebar.** The Data Model section under "Understand the Data" lists every
  generated class page (75 of them, plus the index and five group pages). A newcomer opening that tab sees a
  wall of `Clinvar…` names before any explanation.
- **Use cases are buried.** What the data makes possible lives in a slide deck under Reference › Presentations
  ("What It Unlocks"), the last place a newcomer looks.
- **Keep-current and temporal workflows are missing.** Applying weekly deltas to stay current, and comparing
  releases to see how a variant's classification changed, are spread across Weekly Deltas, How Releases Work,
  Build Your Own and the FAQ, with no page that walks either task end to end.
- **The release schedule, directory tree and rollover rules are repeated** on Home, Download and How Releases
  Work, so they drift.

## 2. Goals

- A reader new to ClinVar-GKM gets from the landing page to a first useful result in minutes, without a
  multi-gigabyte download.
- Each tab serves one stage of the reader's path: start, get, build/query, understand, how it's built, reference.
- The generated class reference stays complete, built and searchable, but leaves the sidebar.
- Keep-current and track-change each get one page that owns the workflow.
- One page owns each fact (release schedule, tree, rollover: `data-access/release-model.md`).

## 3. Hard rule: no file moves

**Existing `.md` files are not moved or renamed.** The URL is the file path, and the site is versioned
(ADR 0011): every published line keeps its URLs, announcement emails and bookmarks link deep pages, and
`pin-repo-links.py` and `check-site-links.py` assume stable paths. The restructure is done by **nav placement
only**. New pages get new paths (`docs/start/`, `docs/build/`, and new files beside existing ones).

## 4. Target navigation

Labels may be refined by the content workstreams through the nav owner; every existing page stays reachable.

| Tab | Contents |
| --- | --- |
| **Start Here** | `index.md` (landing, via `navigation.indexes`), Quick Start*, Key Concepts*, Choose Your Data*, What You Can Do*, Set Up Your Tools*, How to Read These Docs, Data Use and Citation, Stay Informed |
| **Get the Data** | `download.md` (landing), Monthly Full, Weekly Full, Weekly Deltas, Keep Your Data Current*, Parquet Files, Previous Releases, How Releases Work |
| **Build & Query** | Query with SQL (`parquet/index.md` landing + Anatomy of a Table, The 20 Tables, Joining Tables, Working at Scale, Beyond DuckDB), Recipes (promoted), Build Your Own Dataset (`build/index.md`* landing + Build Your Own Tables and Mini-Bundles, Your First Dataset*, CLI Reference*), Track Change Over Time*, Working in Python, Parquet for Previous Releases, Moving from 1.1 to 2.0, User Stories (both) |
| **Understand the Data** | Output Format, Variations, SCV/VCV/RCV Statements, ID References, Examples, Mapping & Vocabularies (profiles; its "Propositions" entry renamed **Proposition Types** so it no longer duplicates the Data Model's "Propositions") |
| **How It's Built** | Unchanged, plus Where a Value Comes From* directly after the Pipeline Overview |
| **Reference** | Data Model (`classes/index.md` + the five group pages: Variations, Concepts, Propositions, Statements, Evidence), Roadmap, Versioning & Releases, Changelog, Release Validation, GA4GH Standards, Known Issues, FAQ, Glossary, Presentations |

`*` = new page (stub in the skeleton PR).

### 4.1 Class pages out of the nav

The 75 individual class pages under `docs/output-reference/classes/` are removed from `nav` and stay in
`docs_dir`. Zensical 0.0.59 builds every page in `docs_dir` whether or not the nav lists it, does not warn
about unlisted pages under `--strict` (the ADRs in `docs/decisions/` have always been built this way), and
includes them in `search.json`. No `not_in_nav` option is needed. The pages stay reachable from the five group
pages and from each other (seven of them only through another class page or `output-reference/cat-vrs.md`).

## 5. Workstreams

The skeleton PR lands the nav and the stub pages; it owns `zensical.toml`. Content workstreams then run in
parallel, each on its own branch, and do not edit `zensical.toml` (a label change goes back through the nav
owner).

| Workstream | Pages | Content |
| --- | --- | --- |
| **A — Start Here** | `index.md`, `start/quick-start.md`, `start/concepts.md`, `start/choose-your-data.md`, `start/setup.md`, and duplicate removal in `index.md` / `data-access/download.md` | Rewrite `index.md` to one screen with four task cards; a quick start that needs no large download; key concepts moved out of `index.md`; choose-your-data with live sizes (from `index.json`); shared prerequisites (ADR 0012) pages can link to. Make `data-access/release-model.md` the sole owner of the release schedule, directory tree and rollover; replace the copies with links. |
| **B — Build & Query** | `build/index.md`, `build/first-dataset.md`, `build/cli-reference.md`, `parquet/recipes.md` | A "choose your path" landing (query published Parquet, build tables, cut a mini-bundle); a first-dataset walkthrough; a CLI reference for `gkm-bundle-parquet` 2.0.0; new recipes: gene panel, VRS-keyed harmonization table, conflicts watchlist, submitter dataset, flat analysis table. |
| **C — Keep current + track change** | `data-access/keep-current.md`, `build/track-change.md`, `reference/faq.md` | Applying weekly deltas to a local copy (bundle and Parquet), checking it, recovering from a missed week; comparing releases to follow a variant's or submitter's classifications over time; FAQ entries pointing to both. |
| **D — Gallery** | `start/what-you-can-do.md` | Use-case cards drawn from the "What It Unlocks" presentation, plus new cards, each linking to the page or recipe that does it. |
| **E — Understand + How It's Built** | `output-reference/*-statements.md`, `pipeline/value-provenance.md`, `pipeline/index.md` | Statement pages open with "what this answers"; the VCV layer hierarchy comes before the field tables; glossary links on first use; a page tracing a bundle value back to ClinVar's XML through the procedures; maintainer run commands in `pipeline/index.md` moved into their own sub-section. |

## 6. Constraints for all workstreams

- No file moves or renames (§3).
- `uvx --from zensical==0.0.59 zensical build --clean --strict` clean and
  `python3 src/scripts/check-site-links.py` 0 broken before each PR.
- ADR 0012: every runnable example runs as written and its page states its prerequisites (or links to
  `start/setup.md` once it has content).
- Terminology per `.claude/rules/docs.md` (bundle, GKM vs GKS, Variant/Variation in headers).
- PRs into `1.0`. A docs merge deploys nothing (ADR 0011); the `1.2` line is rebuilt by dispatch after the
  workstreams land.

## 7. Out of scope

- Moving or renaming any existing page; redirects.
- Changes to the generated class pages or their generator.
- Changes to the versioning overlay files or the deploy workflow.
