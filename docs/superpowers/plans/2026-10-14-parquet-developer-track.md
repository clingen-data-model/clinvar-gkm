# Parquet Developer Track Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or
> superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.
> Use the repo's `write-docs` skill for every page created or edited here.

**Goal:** Add a Parquet-focused developer track that teaches someone to go from "never opened a Parquet file"
to "joining across 22 sections confidently" — a learning path, not a file list. Each page opens with something
runnable before any prose about the model.

**Problem being solved:** The JSON/bundle consumer has three whole nav tabs — **Data Guide** (output format,
per-statement-type pages, ID references, examples), **Data Model** (33 class pages), **Pipeline** (how it is
built). The Parquet consumer has *one page*, `data-access/parquet.md`, which sits under **Downloads** and is
organised around distribution mechanics. It does five jobs at once (release browsers, the 22-file table,
prerequisites, query examples, delta reconstruction) and never states the relational model: which columns are
keys, which joins are polymorphic, which ones silently drop rows. Today a Parquet consumer has to reverse-engineer
that. Three of the five join seams cannot be guessed from column names.

**The asymmetry in one line:** JSON consumers are taught a *pointer* model (`#/condition/clinvar.trait:17556`);
Parquet consumers need a *relational* model (tables, keys, prefix-dispatched foreign keys). They are different
mental models, so a Parquet reader cannot simply be redirected to the Data Guide.

**Architecture:** A new top-level nav tab **Query the Data**, sibling to Data Guide, with seven pages ordered by
difficulty. `data-access/parquet.md` **stays exactly where it is** and keeps all its anchors — it becomes the
*distribution* page (release browsers, file table, stable URLs, deltas) and gains a pointer into the new track.
Two new self-contained HTML diagrams live in `docs/assets/diagrams/` and are embedded with `<iframe>`, following
the `bundle-section-map.html` precedent.

**Tech Stack:** Zensical (Material theme, `zensical build --strict`), Markdown with `pymdownx.details`
collapsible call-outs and `admonition`, hand-authored inline-SVG diagrams in standalone HTML (no JS libraries,
CSP-safe), DuckDB CLI as the teaching tool.

**Branch:** `docs/parquet-developer-track` off `main`. Verifies with `zensical build --strict` and
`zensical serve`.

**Conventions:**

- **No SQL ships unrun.** Every query in these pages must be executed against a real downloaded monthly set and
  its output pasted from the actual run. Counts are release-dependent, so each page states its release date
  once and uses figures from that release only.
- Zensical `--strict` builds and validates **every** `.md` regardless of nav, and these pages cross-link each
  other — so a build passes only once all seven exist. Create them all, then build and commit together
  (the same ordering constraint the Downloads redesign hit; see its plan, Chunk 3).
- Preserve existing heading *text* in `data-access/parquet.md` — `Parquet Files`, `Download`, `Query`,
  `Column Reference`, `Applying Deltas (keeping a Parquet set current)` — at least ten inbound links and two
  prior planning docs reference them.
- Terminology per `.claude/rules/docs.md`: **GKM** = the schema set, **GKS** = the workstream; say **bundle**,
  not dictionary; **Variant/Variation** in headers.
- **Remote querying is taught — within a boundary.** `data.clinvar-gkm.org/v1` serves HTTP range requests with
  CORS open, so DuckDB (`httpfs` autoloads) queries `https://.../00-latest/<section>.parquet` directly. Use it as
  the default for **light** work (Start Here, single-table, targeted / `LIMIT` reads); it is zero-friction and
  ~0.5 s. For **heavy** work (joins, full scans on big sections) **download once and query local files** — a
  parallel full-column scan over a big file bursts range requests and trips Cloudflare's rate limiter (HTTP 429).
  Teach that boundary and the `SET threads=1` + `http_retries` throttle as the reason, not a footnote. Never
  teach pointing a query at the old `pub-*.r2.dev` host.

---

## Chunk 0: Source material — what is already verified

No task here; this is the input inventory so implementers do not re-derive it.

A full structural audit of the **14 Oct 2026** release was completed: 22 tables, 90,209,827 rows, 26 foreign-key
edges, 166,889,379 references, **all resolving**. The findings that the track must teach:

| Fact | Why a reader needs it |
| --- | --- |
| Four polymorphic FKs dispatch on **id prefix** | `object_condition_id`, `proposition_id`, `variation.members[]`, `evidence_items[]`. Joining one branch silently drops the rest. |
| `variation.members[]` reads as a broken FK (98 %) until split by VRS prefix | `VA.`→allele, `CN.`→copyNumberCount, `CX.`→copyNumberChange, each 100 %. |
| `proposition_id` is **1:1**, not 1:N | Unique within each statement table and across all three combined. A proposition is a side-table of its statement. |
| `gene_context_name` joins `gene.name`, which is **not unique** | And is NULL on ~76 % of rows. Two reliable gene-id edges exist instead. |
| SCVs are **always leaves** in evidence-line branching | Measured: zero SCV ids ever appear as the parent of an evidence edge. |
| Aggregate tiers are **forests**, depth ≤ 2, and no edge crosses an accession | Which is why the SCV↔aggregate mapping needs no recursion. |
| `object_therapy` is stored **JSON-quoted** | Matches `therapy.key` 0 % raw, 100 % unwrapped. |
| The `data` column is most of the file | `scv.data` alone is ~15 GB uncompressed of a ~20 GB table. Column pruning is the whole performance story. |

An existing interactive version of these diagrams is at
<https://claude.ai/artifact/TGKVvDkbH7FhE3xvYnu89v> — use it as the **content** source for the two new diagram
files, not as a drop-in asset (it carries its own palette; see Task 2).

---

## Chunk 1: Diagrams

### Task 1: Create `docs/assets/diagrams/parquet-section-map.html`

**Files:** Create `docs/assets/diagrams/parquet-section-map.html`

**Background:** `docs/assets/diagrams/bundle-section-map.html` is the precedent: a standalone HTML file,
`<!DOCTYPE html>` + `<title>` + inline `<style>` + hand-authored inline SVG, embedded from Markdown with an
`<iframe>` (see `docs/output-reference/classes/index.md:13`). It defines its palette as CSS custom properties on
`:root`, overrides them under `:root[data-theme="dark"]`, and again under
`@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])` — so it follows the docs
theme toggle. Match that structure exactly.

- [ ] **Step 1: Reuse the repo palette, not the source artifact's**

  Copy the `:root` / `:root[data-theme="dark"]` / `@media (prefers-color-scheme: dark)` token block verbatim from
  `bundle-section-map.html` (`--bg --ink --ink-soft --line --line-strong --box --hdr --accent --id`). Map the
  source artifact's semantic edge colours onto it so the two diagrams read as one system:

  | Meaning | Token to use |
  | --- | --- |
  | verified 1:1 / 1:N edge | `--line-strong` |
  | polymorphic (prefix-dispatched) edge | `--accent` |
  | natural-key join (not a PK) | `--line`, dotted |
  | id / key text | `--id` |

- [ ] **Step 2: Draw the six areas and the seams**

  Content: the overview map (Variant · Condition & therapy → Proposition → SCV / RCV / VCV) plus the per-area
  detail for Areas 1–4. Keep each area readable on its own; this file is the "map", Task 2 is the "joins".

- [ ] **Step 3: Verify geometry before committing**

  Diagrams drawn by hand drift: labels land on top of boxes and arrows terminate 1 px off an edge. Run a
  collision check rather than eyeballing — flatten every path to sampled points, bound every `<text>` from its
  font metrics, and assert zero rect/rect, text/rect, text/text, path/rect and path/text overlaps, plus that
  every arrow endpoint sits on an edge of its named box.

**Verification:** open in a browser at light, dark and system theme; confirm no clipping at 400 px width; the
collision check reports zero issues.

### Task 2: Create `docs/assets/diagrams/parquet-join-seams.html`

**Files:** Create `docs/assets/diagrams/parquet-join-seams.html`

Same structure and palette as Task 1. Content: the five join seams, one strip each —

- [ ] **Step 1:** Seam A · Variant → Proposition (four tables, one target, 100 %)
- [ ] **Step 2:** Seam B · Proposition → Condition / ConditionSet (three prefixes, two target tables)
- [ ] **Step 3:** Seam C · Proposition → Statements (the `proposition_id` fan; label it **1:1**)
- [ ] **Step 4:** Seam D · Aggregate nesting (root → child → SCV leaves; mark SCV as terminal)
- [ ] **Step 5:** Seam E · SCV ↔ aggregate accession (the single-pass mapping)

**Verification:** as Task 1.

---

## Chunk 2: The seven pages

**Ordering note:** create all seven, then build `--strict` and commit together. They cross-link, and Zensical
validates every `.md` whether or not it is in the nav.

### Task 3: Create `docs/parquet/index.md` — "Start Here"

**Files:** Create `docs/parquet/index.md`

**Audience:** someone who has never opened a Parquet file and may not write code. This page must produce a
real answer from real ClinVar data in about five minutes, with **no joins and no genomics knowledge**.

- [ ] **Step 1: One small file, chosen deliberately**

  Use `condition.parquet` — ~2 MB, 23,162 rows, and its `name` column holds plain disease names. It is the only
  section that is simultaneously tiny, human-readable, and free of VRS identifiers. Do not open with `scv` or
  `variation`.

- [ ] **Step 2: Three queries, in this order**

  ```sql
  -- 1. How many conditions are there?
  SELECT count(*) FROM 'condition.parquet';

  -- 2. What do they look like?
  SELECT id, name FROM 'condition.parquet' LIMIT 10;

  -- 3. Find one you care about
  SELECT id, name FROM 'condition.parquet' WHERE name ILIKE '%marfan%';
  ```

- [ ] **Step 3: A no-install option — VERIFY BEFORE PUBLISHING**

  Offer the DuckDB Web Shell (<https://shell.duckdb.org>) with the downloaded file dragged in, so a reader needs
  no terminal at all. **This is unverified.** Before writing it as instructions, confirm by hand that a local
  `condition.parquet` can be dropped into the shell and queried. If it cannot, cut the step — do not ship a
  guess. Do not instead point the shell at the R2 URL; R2 is not a query endpoint.

- [ ] **Step 4: An escape hatch to a spreadsheet**

  Many non-technical readers want the answer in Excel or Sheets, which cannot open Parquet. One line:

  ```bash
  duckdb -c "COPY (SELECT id, name FROM 'condition.parquet') TO 'conditions.csv' (HEADER)"
  ```

- [ ] **Step 5: Close with a map, not a lecture** — one paragraph on what the other 21 files are, linking to
  the section map, and a "where to next" list pointing at the remaining pages by the question each answers.

**Verification:** `zensical build --strict`; run all three queries plus the CSV export against a fresh download.

### Task 4: Create `docs/parquet/first-queries.md` — "One Section at a Time"

**Files:** Create `docs/parquet/first-queries.md`

Still single-table — no joins. Teach the shape of a GKM Parquet section.

- [ ] **Step 1:** `DESCRIBE SELECT * FROM '<file>'` as the primary way to read a schema; show it on
  `condition.parquet` (flat) and on `scv.parquet` (nested `STRUCT`s).
- [ ] **Step 2:** The two columns every section has — `id` and `data` — and that `data` is the full JSON object
  as a string. Introduce `json_extract` / `->>` for reaching into it.
- [ ] **Step 3:** Reading a `STRUCT` column with dotted access (`classification.name`), which is the single most
  common first stumble: `classification` is a MappableConcept, not a string.
- [ ] **Step 4: The one hard warning, early** — never `SELECT *` on a large section and never load one whole into
  pandas. Give the arithmetic: `scv.parquet` is ~3 GB on disk and ~20 GB uncompressed, of which the `data`
  column alone is ~15 GB. Name the symptom (machine swaps or the process is killed) and the fix (name your
  columns).
- [ ] **Step 5:** A worked single-table analysis — classification counts on `scv.parquet` reading only the
  `classification.name` leaf. Note that this leaf costs ~140 MB where the whole table costs ~20 GB, and that
  the values are not case-normalised (44 distinct, including `pathogenic` alongside `Pathogenic`).

**Verification:** `zensical build --strict`; every query run; confirm the quoted leaf-vs-table sizes against
`parquet_metadata` on the current release.

### Task 5: Create `docs/parquet/section-map.md` — "The 22 Sections"

**Files:** Create `docs/parquet/section-map.md`

- [ ] **Step 1:** Embed `parquet-section-map.html` by `<iframe>`, matching the attributes used at
  `docs/output-reference/classes/index.md:13`.
- [ ] **Step 2:** Group the 22 sections into the six areas with one line each on *what question it answers*.
  Do **not** duplicate the file-description table from `data-access/parquet.md`; link to it.
- [ ] **Step 3:** The id shapes, as a table — `clinvar:<n>`, `ga4gh:VA.*` / `CN.*` / `CX.*`, `clinvar.trait:<n>`,
  `clinvar.traitset:<n>`, `clinvar.conditionset:vcv-<md5>`, `ncbigene:<n>`, `clinvar.submission:SCV*`,
  `RCV*-<stmt>`, `VCV*-<stmt>`, `SQ.*`. Readers meet these before any join, and the prefix *is* the dispatch key.
- [ ] **Step 4:** State which sections are leaves (`condition`, `therapy`, `submitter`, `sequenceReference`) so
  readers know where a traversal ends.

**Verification:** `zensical build --strict`; the iframe renders in both themes; every id shape confirmed present
in the current release.

### Task 6: Create `docs/parquet/joining.md` — "Joining Sections"

**Files:** Create `docs/parquet/joining.md`

The core technical page. Embed `parquet-join-seams.html`, then one section per seam: the diagram strip, the
runnable join, and the trap.

- [ ] **Step 1:** Seam A — Variant → Proposition. Four tables spell the subject column differently
  (`subject_variant_id` vs `subject_id`); `UNION ALL` them once into a `prop` CTE and reuse it.
- [ ] **Step 2:** Seam B — Proposition → Condition / ConditionSet. Branch on prefix: `clinvar.trait:` →
  `condition`, and **both** `clinvar.traitset:` and `clinvar.conditionset:` → `conditionSet`. `LEFT JOIN` both
  and keep a `resolved_via` flag so losses are visible rather than silent.
- [ ] **Step 3:** Expanding a set to member *names* — the trap worth its own callout. `conditionSet.concepts[]`
  holds **ids**, so `array_to_string(concepts, …)` prints `clinvar.trait:2965`, not a disease name. `unnest` and
  re-join to `condition`. Two further points: `membershipOperator` (`AND`/`OR`) changes what the set asserts and
  must travel as its own column, because `array_to_string` requires a **constant** separator; and a minted set
  can nest a `clinvar.traitset:` member, so expansion is one level deeper than it looks.
- [ ] **Step 4:** Seam C — Proposition → Statements. Label it **1:1** explicitly and show the three-table
  `UNION ALL`, noting each tier's shares sum to its exact row count.
- [ ] **Step 5:** Seam D — the aggregate group. Root cites children, children cite SCVs, SCVs are leaves.
- [ ] **Step 6:** Seam E — the efficient SCV ↔ aggregate mapping. The accession in the citing statement's own id
  names the group, so one pass over `has_evidence_lines` ⋈ `evidence_items` yields every pair with no recursion.
  Keep `statement_id` as well as the accession — it is what distinguishes `-CP` from `-NOCP` from `-EP`.
- [ ] **Step 7: A "joins that lie" summary box** — the four prefix-dispatched columns, `gene_context_name` on a
  non-unique natural key, and `object_therapy` needing `trim(…, '"')` plus prefix stripping.

**Verification:** `zensical build --strict`; every join run with its real output pasted; each "trap" demonstrated
by showing the wrong result next to the right one.

### Task 7: Create `docs/parquet/recipes.md` — "Recipes"

**Files:** Create `docs/parquet/recipes.md`

Task-indexed, not table-indexed. Each recipe: the question in plain language, the query, the real output, and
one line on cost. Seed set — confirm against the roadmap and GitHub Discussions before fixing the list:

- [ ] **Step 1:** Everything ClinVar says about one variant (by `clinvar:<n>`, and by HGVS via `allele`).
- [ ] **Step 2:** All variants asserted for one condition, with classification counts.
- [ ] **Step 3:** One submitter's whole footprint — cross-link `user-story-audit.md`, which already tells this
  story for the bundle.
- [ ] **Step 4:** Conflicting classifications for a variant across submitters (uses Seam E).
- [ ] **Step 5:** Variants in a genomic window (`location.loc_start` / `loc_end` + `sequence_reference_id`).
- [ ] **Step 6:** Gene-level rollup — using the reliable gene-id edge, *not* `gene_context_name`.
- [ ] **Step 7:** Export a filtered slice to CSV/Parquet for another tool.

**Verification:** `zensical build --strict`; every recipe run end to end; each one's wall-clock and peak memory
noted so a reader knows what to expect.

### Task 8: Create `docs/parquet/performance.md` — "Working at Scale"

**Files:** Create `docs/parquet/performance.md`

- [ ] **Step 1:** Column pruning as the one idea that matters, with the `scv.parquet` per-column byte table from
  `parquet_metadata` showing `data` dominating.
- [ ] **Step 2:** Row-group targeting — read one row group rather than a whole column when you need a single
  record.
- [ ] **Step 3:** DuckDB settings that matter on a laptop: `threads`, `memory_limit`,
  `preserve_insertion_order=false`, and what the spill-to-disk error looks like when a `GROUP BY` on
  high-cardinality strings exhausts temp space.
- [ ] **Step 4:** Reserved words that bite in real queries — `rows`, `target`, `role`, `type`, `order`, `end`
  all fail as bare column aliases. This is a frequent, confusing first error.
- [ ] **Step 5:** `duckbox` escapes control characters, so an embedded newline prints as `\n`. The data is fine;
  use `.mode line`, or emit one row per member. Worth stating because the natural fix (a newline-joined label)
  looks broken in the CLI.
- [ ] **Step 6:** Persisting a `.duckdb` database with materialised join tables when you will query repeatedly.

**Verification:** `zensical build --strict`; reproduce each error message quoted.

### Task 9: Create `docs/parquet/other-tools.md` — "Beyond DuckDB"

**Files:** Create `docs/parquet/other-tools.md`

One short, runnable section per tool, each doing the *same* small task so they are comparable.

- [ ] **Step 1:** Python — `pyarrow` for schema/metadata and column-pruned reads; `pandas` with an explicit
  `columns=` and the warning that omitting it loads everything; `polars` `scan_parquet` for lazy predicate
  pushdown.
- [ ] **Step 2:** R — `arrow::open_dataset()` with `dplyr` verbs.
- [ ] **Step 3:** Spark / cloud warehouses — Parquet reads directly; BigQuery external tables and Athena over a
  bucket copy. Note that `STRUCT` and `LIST` columns survive, and the `data` column is a string everywhere.
- [ ] **Step 4:** GUI and spreadsheet users — convert a filtered slice to CSV first; do not suggest opening a
  multi-GB section in a spreadsheet.
- [ ] **Step 5:** A one-paragraph "which tool when" close.

**Verification:** `zensical build --strict`; run at least the Python, polars and R snippets.

---

## Chunk 3: Wiring

### Task 10: Add the Parquet tab to `zensical.toml`

**Files:** Modify `zensical.toml`

- [ ] **Step 1:** Insert a new top-level group **after** `Downloads` and **before** `User Stories`, using the
  repo's bare-index pattern (first entry a plain string, as the Data Model group does):

  ```toml
    { "Query the Data" = [
      "parquet/index.md",
      { "One Section at a Time" = "parquet/first-queries.md" },
      { "The 22 Sections"       = "parquet/section-map.md" },
      { "Joining Sections"      = "parquet/joining.md" },
      { Recipes                 = "parquet/recipes.md" },
      { "Working at Scale"      = "parquet/performance.md" },
      { "Beyond DuckDB"         = "parquet/other-tools.md" },
    ] },
  ```

- [ ] **Step 2:** Confirm `navigation.indexes` is already in `theme.features` so the bare index entry renders as
  the group's landing page. It is — do not add it again.

**Verification:** `zensical build --strict`; the tab appears between Downloads and User Stories; the group lands
on `parquet/index.md`.

### Task 11: Cross-link the distribution page and the track

**Files:** Modify `docs/data-access/parquet.md`

- [ ] **Step 1:** Add a pointer near the top — one admonition, directing readers who want to *query* rather than
  *download* into `../parquet/index.md`.
- [ ] **Step 2:** Leave every existing heading and anchor intact. Do **not** move the delta reconstruction
  content; it is distribution mechanics and at least ten inbound links and two planning docs point at it.
- [ ] **Step 3:** Decide the fate of the `### Query` / `### Column Reference` / cross-section example blocks,
  which the new track supersedes. Default: **keep them in place** and add a line pointing to the fuller
  treatment. Removing them breaks anchors for no benefit.

**Verification:** `zensical build --strict`; `grep` the built HTML to confirm the referenced anchors still exist.

### Task 12: Link in from the existing entry points

**Files:** Modify `docs/index.md`, `docs/output-reference/overview.md`

- [ ] **Step 1:** `docs/index.md` — add Parquet to whatever "where to start" routing the home page offers, so a
  reader who wants tables rather than JSON is sent down the right path from the first screen.
- [ ] **Step 2:** `docs/output-reference/overview.md` already has a `## Parquet Output` section — point it at the
  new track.
- [ ] **Step 3:** Do **not** touch `docs/reference/roadmap.md`'s generated region.

**Verification:** `zensical build --strict`.

---

## Chunk 4: Close-out

### Task 13: Full verification pass

- [ ] **Step 1:** `zensical build --strict` clean from a clean tree.
- [ ] **Step 2:** `zensical serve` and walk the track start to finish as a new reader: every code block
  copy-pasteable, every link live, both diagrams rendering in light, dark and system theme.
- [ ] **Step 3:** Re-run every query in the track against a freshly downloaded monthly set and diff the pasted
  outputs. Any figure that moved is release drift — fix the page and note the release date it reflects.
- [ ] **Step 4:** Check the track at 400 px width; the two iframes must not clip.
- [ ] **Step 5:** Open the PR. Per `CLAUDE.md`, no Claude attribution in the commit messages.

---

## Decisions this plan takes, and what it declines

**A new tab, not a subsection of Downloads.** Downloads was deliberately reshaped six days ago
(`2026-10-08-downloads-approachable-redesign.md`) into a distribution hub with four scoped child pages. A
seven-page learning track nested inside it would fight that design and bury the beginner entry point three
levels deep. The parallel to draw is **Data Guide**, which is exactly this for JSON consumers.

**`data-access/parquet.md` is not dismantled.** It is new, it is linked from ten places, and its job —
browsers, file table, stable URLs, deltas — is genuinely distribution. The new track links to it for "how do I
get the files" and never duplicates the file table.

**Deltas stay on the distribution page.** Keeping a set current is a release-mechanics problem, not a query
problem, and the existing content is good. The track cross-links it.

**Not proposed here:** moving the orphaned `data-access/index.md`, `data-access/output-files.md`,
`getting-started.md` and `output-reference/index.md` into the nav. They are reachable only by direct link today.
That is a real finding from this survey but it is a separate concern, and `CLAUDE.md` says touch only what the
request covers — worth raising as its own issue.

## Open questions — resolved at review (2026-10-14)

1. **Nav label → "Query the Data".** Chosen over "Parquet" to describe the reader's intent rather than the file
   format, and to cover future non-Parquet query paths. The tab label is **Query the Data**; the page directory
   stays `docs/parquet/` (URLs unchanged) and the content remains Parquet-specific. Task 10's TOML group key is
   `"Query the Data"`.
2. **The no-install beginner path is real.** The DuckDB Web Shell (<https://shell.duckdb.org>) loads a local
   file by drag-and-drop or the **Import** button / `.pick` command; the file registers in browser-local memory
   and the filename-without-extension becomes a view (`condition.parquet` → `FROM condition`). Because the CDN
   sets `access-control-allow-origin: *` (verified), the browser shell can **also query the `https://` URL
   directly** — no download, no drag. Task 3 Step 3 ships; the exact in-shell wording is pinned when Task 3 is
   written.
3. **Recipe list stays as inferred.** The 11 `roadmap authorized` GitHub Discussions are *feature* ideas
   (temporal analytics, submitter tooling, weekly Parquet, functional-data capture) — none is a query recipe.
   Task 7's seven recipes stand as the working set, refined at review rather than blocking on a Discussions source.
4. **Release-figure drift → release-date banner per page (option a).** Each page states "figures reflect the
   YYYY-MM-DD release" once; hard counts are kept minimal because the *structure* (polymorphic FKs, prefix
   dispatch, 1:1 proposition) is release-independent. Monthly refresh is accepted manual toil. Build-time
   generation from a committed metrics JSON (option c) is a possible follow-up, not done here.

### Added at review: remote querying is now taught (reverses convention #5)

The custom domain **`data.clinvar-gkm.org/v1`** (PR #138, CDN) serves **HTTP range requests**
(`accept-ranges: bytes`) with **CORS open** (`access-control-allow-origin: *`), and DuckDB **autoloads httpfs**
for `https://` paths. Verified against the 14 Oct release:

| Operation (remote) | Result |
| --- | --- |
| `count(*)`, `DESCRIBE`, schema | footer-only, ~0.5 s even on 3 GB `scv.parquet` |
| Small sections; targeted / `LIMIT` reads on big files | fast (~0.5 s) |
| Full-column scan / `GROUP BY` on a big file, default threads | **HTTP 429** — burst of parallel range requests (scv = 55 row groups, varcond = 223) trips Cloudflare's limiter |
| Same scan with `SET threads=1` + retry/backoff | completes (~18.5 s for the scv classification rollup) |

**Resolution — hybrid presentation.** Remote (`FROM 'https://data.clinvar-gkm.org/v1/datasets/parquet/00-latest/<section>.parquet'`)
is the default for **light** work — Start Here, single-table, targeted lookups — where it is zero-friction and
genuinely fast. **Heavy** work — the joins on *Joining Sections*, the big scans in *Recipes* — downloads once and
queries local files. The range-request model, the **429 boundary**, and the `SET threads=1` + `http_retries`
throttle are taught explicitly (in *The 22 Sections* / *Working at Scale*) as the *reason* for the split, not
hidden. Base URL path: `v1/datasets/parquet/00-latest/` (stable "latest"); dated pins at `v1/datasets/parquet/<YYYY-MM>/`.

### Added at review: a live in-browser query console

Because the CDN sets `access-control-allow-origin: *`, a **DuckDB-Wasm** console embedded in the docs runs a
reader's SQL against `data.clinvar-gkm.org` directly — no install, no download. It is built and lives at
`docs/assets/duckdb-console.html` (theme-aware, same palette as the diagrams), embedded by `<iframe>` as the
**centerpiece of Start Here** (Task 3): a reader queries real ClinVar data in their first 30 seconds. Guardrails:
`SET threads=1`, a client-side **one-query-per-10 s** cooldown (greyed Run button + countdown), and example
queries chosen to be light/reliable (the heavy full-scan lesson stays in prose). Errors are humanized
(plain-language headline + what-to-do hint + collapsible raw details).

**Runtime is vendored, not CDN-loaded** (review decision). The `eh` bundle lives in `docs/assets/vendor/duckdb/`
(~35 MB: `duckdb-eh.wasm` + the eh worker verbatim, plus an esbuild-bundled `duckdb-browser.bundled.js` with
apache-arrow inlined — the package ESM has an unresolvable bare `import "apache-arrow"`). Plain committed files
(Git LFS can't be used — GitHub Pages serves the LFS pointer, not the file). The bundle is named `.js` not `.mjs`
(GitHub Pages has served `.mjs` with a MIME type that breaks ESM imports). Provenance + the reproducible rebuild
command are in that directory's `README.md`.

**Cost (verified against the 14 Oct release):** this is cheap by design — R2 egress is $0; the only
query-driven cost is Class B reads ($0.36 / million, 10 M/month free), fenced by the console cooldown and the
WAF rate-limit rule in ADR 0005. Big sections (>512 MB) never cache (`BYPASS`); `00-latest` is set to bypass
cache while **dated** paths cache (`MISS`→`HIT`) — a possible follow-up is to default the console to the newest
dated release so small-section reads serve from the edge. No native hard spend cap exists, so a usage alert is
the safety net (Cloudflare has no dedicated R2-ops alert type on the Free plan — a Custom Alert is the route).

### Added at review: per-table column reference + linkable diagram boxes

- **Complete per-table column reference.** Today's docs only partially cover Parquet columns — the distribution
  page's "Column Reference" does statements + propositions; the Data Model class pages describe the schema
  *classes*, not the flattened Parquet columns. Fold a complete reference into *One Section at a Time* /
  *The 22 Sections*: for each of the 22 tables, **definition + every column + type + description**. Generate
  name+type from `DESCRIBE` on the real release, carry over the descriptions that already exist, and give each
  table a **stable anchor** (e.g. `#variation`) so diagrams can link to it.
- **Linkable diagram table-boxes (sequenced AFTER the reference exists).** Each SVG box that names a Parquet
  table/section (`variation`, `allele`, `condition`, `conditionSet`, `scv`, …) becomes
  `<a href="../../parquet/<page>/#<table>" target="_top">` wrapping its `rect`+`text`, navigating to that table's
  reference section — the `bundle-section-map.html` linkable-box precedent (`target="_top"` to escape the iframe).
  Applies to all three diagrams; re-run svgcheck + the viewBox-bounds check after.
