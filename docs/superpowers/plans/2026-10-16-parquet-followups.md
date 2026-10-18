# Parquet Follow-ups Plan

> **Relabelled 1.0.2 → 1.1.0 (2026-10-18).** The release now also carries the proposition reorganization
> (plan PR #155) and is a full rebuild and in-place republish under `/v1/`; see ADR 0006. Version strings below
> were updated; the patch-style backfill steps described here are superseded by the full rebuild in #155.

> **For agentic workers:** each work item below is sized to one PR (or one decision). Items marked **Plan
> first** need their own design plan before code. Steps use checkbox (`- [ ]`) syntax for tracking. Run
> `/catchup` before starting an item; several depend on PRs that may have merged since this was written.

**Goal:** Resolve the issues found while building the Query the Data track (#139) and fixing #132. These were
found by querying the 2026-10 Parquet release end to end. None blocks current users, but several make correct
queries harder than they should be, and three are conformance defects in published data.

**Source:** Every finding below was measured against the 2026-10 monthly Parquet release, the 2026-10-11 delta
bundle, or the `clinvar_2026_10_11_v2_6_0` BigQuery dataset, unless marked *unverified*.

---

## Already in flight

| PR | What | Base | State (2026-10-16) |
| --- | --- | --- | --- |
| #140 | Docs deploy on push to `main` | `main` | merged |
| #141 | Diagram header tint; statement codes as text | `main` | merged |
| #142 | `ClinvarCategoricalVariant` oneOf fix (#132 item 4) + schema 1.1.0 | `1.0` | draft |
| #143 | Parquet: bare ids for `object_therapy` and gene-list `gene`; typed `condition` export | `1.0` | draft |
| #144 | This plan | `main` | open |
| #145 | A1: no `hgvs.?`; ClinVar's invalid HGVS kept as extensions | `1.0` | draft |

**Order constraints:**

- **#142:** after merging, forward-merge `1.0` → `main` and tag **`1.1.0`** so the new w3id `$id`s resolve.
- **#143:** changes typed Parquet content, so the docs follow-up **A2** must land on `main` in the same window
  as the first Parquet export built with #143.

---

## Consolidated data release (one rebuild, one backfill)

Rule: every change that alters published data lands **before** the forward rebuild and the backfill, so each
runs once. Docs move with every PR (paired `main` docs PR for `1.0` changes; `docs/parquet/` exists only on
`main`).

### What changes published data

| Change | JSON bundle | Parquet | Backfill past releases? |
| --- | --- | --- | --- |
| #142 oneOf fix + schema 1.1.0 | `schema_version` label only | — | no |
| B2 bundle `oneOf`, A3 description drift | — | — | no (schema only) |
| #145 A1 `hgvs.?` | 14 `variation` records (monthly fulls only; none appear in any of the 15 deltas) | `variation` | **yes** |
| #143 gene-list ids | — | `variation` values change form | **yes**: a value change mixed across a full and its deltas breaks reconstruction |
| #143 `object_therapy` | — | `vartherapy-proposition` values change form | **yes**, same reason |
| #143 `condition` `data` column | — | new column | no: additive columns mix safely (`UNION ALL BY NAME`) |
| C2 therapy columns, C3 location ranges | — | new columns | no (additive) |
| C1 variant-sorted file | — | new file | no (new artifact starts with the next release) |
| C4 `gene_context_name` on aggregates | ~20 M VCV/RCV propositions | `varcond` / `varcustom` | must be **decided before** the rebuild: populating it later would force a second rebuild |

Confirmed not pending (already merged): the va-spec 2026-09 migration, the ConceptSet iriReference change, and
the VCV EP/PG aggregate refactor.

### Sequence

1. **Settle data decisions first:** C4 (`gene_context_name` on aggregates: keep SCV-only, or populate now).
2. **Finish the `1.0` PRs:**
   - fold B2 and A3 into #142
   - optionally fold C2 into #143 (additive, so optional)
   - review and merge #142 → #143 → #145 into `1.0`
3. **Paired docs PR on `main`** (A2 + docs for #143/#145/C2), merged together with step 4.
4. **Forward-merge `1.0` → `main`; tag `1.1.0`.**
5. **Forward rebuild** (next release, gated):
   - deploy the changed procedures
   - run the variant step in **full mode once** (A1)
   - export with the new Parquet SQL
   - full-vs-incremental and delta-reconstruction oracles at 0,0,0
6. **One backfill of published releases** (live writes, each confirmed):
   - **JSON:** the 14 A1 `variation` records in the monthly fulls (2026-07 … 2026-10, `00-latest`, `/v1/` and flat-root)
   - **Parquet:** re-export `variation` and `vartherapy-proposition` for every monthly set and every delta that
     contains those tables, so A1 and both #143 value changes land in one pass
   - **Then:** purge the CDN for overwritten dated paths, regenerate `index.json`, re-verify reconstruction
     (full + deltas == next full), and validate the patched bundles
   - **Changelog:** record the backfill
7. **After the backfill:** additive items (C1, C3, C2 if not folded in) ship forward-only with any later release.

## Workstream A — Conformance and correctness (do first)

### A1 · Fix `hgvs.?` syntax in variant HGVS lists

**Status:** code done on branch `fix/hgvs-invalid-expressions` (off `1.0`, commit `189f3d9`, not yet pushed).
The release steps and the backfill (option 2) below are still to do.

**Problem.** 14 variants (16 expressions) in the 2026-10 release carry `clinvarHgvsList` entries with
`nucleotideExpression.syntax = "hgvs.?"`. VRS `Expression.syntax` doesn't allow it, so these variants fail
schema validation. They passed the 2026-10-11 delta check only because none was in that delta.

The variants are `clinvar:` 360, 3379, 3572, 4134, 9291, 9874, 10113, 10626, 11219, 635132, 829537, 1319991,
2503493 and 2505466.

**Cause.** In `src/procedures/gkm-catvar-proc.sql`, the `hgvs_items` step that builds the HGVS list falls back
to a literal `?`:

```sql
format('hgvs.%s', IFNULL(REGEXP_EXTRACT(exp.nucleotide, r':([gmcnrp])\\.'), '?'))
```

The 16 expressions come from clinvar-ingest's `variation_hgvs` table: ClinVar's submitted text, with no HGVS
type letter where one belongs (e.g. `NC_000017.10:9481617_9489649del`). For 11 of them, the same upstream
row also holds a valid ClinVar expression for the same accession; for 5 it doesn't. No protein expressions
are affected.

**Decided (2026-10-17).** ClinVar's text is never altered or dropped (project policy). An invalid expression
is no longer listed on its own; it becomes an extension of the listed expression:

| Case | Listed expression | Extensions on it |
| --- | --- | --- |
| Merged (11): ClinVar also supplies a valid expression | ClinVar's valid expression | `invalidClinvarExpression`: submitted text · `expressionMerged`: `true` |
| Repaired (5): no valid one | our repair (type letter restored) | `originalClinvarExpression`: submitted text · `expressionRepaired`: `true` |

The repair rules strip stray leading dots, turn `g(` into `g.(`, move `(g.123` to `g.(123`, or insert the
letter for the accession's HGVS type. ClinVar's own valid copy is always preferred over a repair: repairing
the 11 would have produced two wrong values.

- [x] Change `gkm-catvar-proc.sql` (`hgvs_exprs` / `hgvs_invalid_dups` / `hgvs_items`). The extension struct is
  `{name, value_string, value_boolean}`; the assembler collapses it to `{name, value}`.
- [x] Document the four extensions in the `HgvsListItem` description (source YAML, regenerated JSON and class
  page). VRS `Expression` already allows `extensions`, so there is no shape change.
- [x] Verify on `clinvar_2026_10_11_v2_6_0` (read-only):
  - HGVS-list entries go from 43,162,744 to 43,162,733 (the 11 merged)
  - 0 invalid syntax; 11 merged and 5 repaired
  - the cleaned items validate as `HgvsListItem` in default and strict mode
- [ ] Push and open a draft PR against `1.0`.
- [ ] Release steps (BigQuery, gated per `.claude/rules/sql-procedures.md`):
  - [ ] Deploy the procedure.
  - [ ] **Run the variant step in full (non-incremental) mode for the first release after the fix**, or add
    the 14 ids to `catvar_changed_ids`. Incremental mode recomputes only changed variants (`vfilter_ext`), so
    unchanged ones would keep `hgvs.?` forever.
  - [ ] Full-vs-incremental oracle and delta-reconstruction oracle at 0,0,0. If the one-time full run is
    skipped, the oracle shows exactly these 14 variants as mismatches.
- [ ] **Backfill past releases: option 2, decided 2026-10-17.** Patch only the `variation` section of
  already-published releases, following the conditionSet backfill precedent (see the
  `reference_vcv_conditionset_synthetic` memory). Every live write needs explicit confirmation first.
  - [ ] Per dataset behind a published release: recompute the 14 variants' `gkm_dict_variation` rows with
    the fixed logic. Change no other rows.
  - [ ] Monthly fulls (2026-07 … 2026-10, plus `00-latest`): rewrite those entries in the bundle's `variation`
    section (streaming edit; no other bytes change), and re-export `variation.parquet`.
  - [ ] Weekly deltas: patch only the deltas whose `variation` section (bundle and Parquet) contains any of
    the 14 ids. Deltas without them are untouched.
  - [ ] Republish the changed files under `/v1/` and the flat-root mirror; purge the CDN for every
    overwritten dated path (ADR 0005); regenerate `index.json` sizes.
  - [ ] Verify:
    - delta reconstruction is still exact (a monthly full + its deltas equals the next full)
    - every patched full validates against the bundle schema
    - checksums change only for the patched files
  - [ ] Note it in the changelog and release notes (ADR 0004 stabilization window: corrective fix in place).
- [ ] File an issue on clinvar-ingest about the malformed `variation_hgvs.expr` entries.

**Base:** `1.0` · **Size:** S (SQL, done) + rebuild + backfill (M) · **Depends on:** nothing.

### A2 · Docs follow-up for #143 (time with the next Parquet export)

**Problem.** After #143, `variation.extensions[].value_gene_array[].gene` and
`vartherapy-proposition.object_therapy` hold bare ids. Queries that compare against `'#/gene/' || gene.id`
stop matching. Queries that strip the prefix keep working.

- [ ] **Now, on `main`:** make every query work on both forms. Compare with `replace(gene, '#/gene/', '')`
  instead of building `'#/gene/' || id`. This affects Recipes (gene rollup, PubMed ids for a gene), any
  diagram query, and `docs/llms*.txt` if the tabled AI-guide branch is revived.
- [ ] **After the export:** update the column reference (`docs/parquet/tables.md`), Joining Tables ("Joins
  that lie": the `object_therapy` box) and the rules on the tabled Query with AI page to describe bare ids.
  Drop the prefix-stripping advice that is no longer needed.
- [ ] Re-run every query in the track against the new export (the docs convention: no SQL ships unrun).

**Base:** `main` · **Size:** S · **Depends on:** #143 merged; second half waits for the export.

### A3 · Fold the `ClinvarScvStatement` description drift into the next schema change

**Problem.** Regenerating `clinvar-statement-source.yaml` changes one description in
`json/ClinvarScvStatement` (`"clinvar.traitset:123"` in quotes vs. bare). The committed JSON and the source
disagree, so every regeneration shows a spurious diff.

- [ ] Pick one form, put it in the source YAML, regenerate, and commit. Ride along with the next schema PR
  (B1 or C2); not worth its own release.

**Base:** with B1/C2 · **Size:** XS.

---

## Workstream B — Schema tooling

### B1 · Strict-mode validation fails every record — **Plan first**

**Problem.** With `validate-schema-conformance.py --no-relax`, every statement and variant record fails with
`Additional properties are not allowed` or `Unevaluated properties are not allowed`, even on ordinary fields
like `classification` and `id`. Default mode passes.

On the 2026-10-11 delta, strict mode fails variation 15,758, varcustom-proposition 40, scv 11,647,
vcv 18,797 and rcv 24,926 records. That's identical before and after #142, so it is a generator issue, not a
data issue.

**Likely cause.** The generated schemas compose classes with `allOf` and also set `additionalProperties:
false` inside individual `allOf` branches (or `unevaluatedProperties: false` alongside refs that don't count
as evaluated). That rejects properties another branch defines. The fix belongs in **gkm-metaschema**
(`source_proc.py`), not in hand-edits to `json/`.

- [ ] Write a plan in gkm-metaschema covering:
  - where `additionalProperties: false` is emitted
  - whether only the outermost class should close the object, using `unevaluatedProperties: false`
  - the test case: a minimal `allOf` of two classes
- [ ] In the same change, make output deterministic: `sort_keys=True` at `source_proc.py:482`. This is the
  deferred fix that stops the random `$defs` reordering.
- [ ] Regenerate `schema/clinvar-gkm/`; strict mode should then pass the 2026-10-11 delta.

**Repo:** gkm-metaschema, then a regen PR here · **Size:** M · **Depends on:** nothing.

### B2 · Bundle schema: validate `variation` with the fixed `oneOf`

**Problem.** `clinvar-gkm-bundle.schema.json` validates each `variation` entry with `anyOf` over five variant
schemas. Before #142 that hid the `oneOf` defect; after #142 the `anyOf` is redundant.

- [ ] Replace the `anyOf` with a single `$ref` to `ClinvarCategoricalVariant`, which now discriminates
  correctly.
- [ ] Verify: the 2026-10-11 delta passes, and a deliberately malformed variant (allele constraint with no
  allele) now fails.

**Base:** `1.0` · **Size:** XS · **Depends on:** #142 · **Version:** fold into the same release as #142 if it
hasn't been tagged yet; otherwise this is a PATCH.

---

## Workstream C — Data products and export (additive)

### C1 · Variant-sorted statement × proposition Parquet — **Plan first**

**Problem.**
- **No variant column on statements:** `scv.parquet` has no variant column, and no published table is sorted
  by a lookup key. A one-variant question reads every row group.
- **Remote queries rate-limited:** over HTTPS that trips the CDN rate limit (HTTP 429), so per-variant queries
  can't run in the live console. Working at Scale currently teaches building this join locally.

**Measured prototype:** `scv_by_variant` is SCV plus its proposition's subject, object and qualifiers plus
PubMed ids, sorted by `variant_id`. It came to 107 MB, and a single-variant lookup read 1 of 55 row groups.

- [ ] Plan the design:
  - which tables: SCV only, or also VCV and RCV
  - columns, naming, and sort keys (variant; object?)
  - row-group size
  - delta handling: rebuild it whole each release, or apply deltas
  - where it sits in the R2 layout and `index.json`
  - whether it carries `schema_version`
- [ ] Build it from the typed Parquet in `export-gkm-dicts.sh` (or as an `EXPORT DATA` query).
- [ ] Docs: a Recipes section, a console example (one-variant PubMed lookup), and the Working at Scale
  materialize section pointing to the published file.

**Size:** M · **Depends on:** #143 (so it inherits bare ids).

### C2 · Typed columns for `therapy` and `therapyGroup`

**Problem.** Both tables are key/value only. Names and group members exist only inside the JSON `value`, so
every therapy query needs JSON parsing.

- [ ] Add columns without removing `key`/`value`:
  - `therapy`: `name`, `concept_type`
  - `therapyGroup`: `membership_operator` and `members` (bare `clinvar.therapy:` ids)
- [ ] Verify against the 38 therapies and 10 groups.

**Base:** `1.0` · **Size:** XS · **Depends on:** #143.

### C3 · Uncertain-range locations

**Problem.** About 72,000 `location` rows have NULL `loc_start` or `loc_end` because the coordinate is a VRS
`Range`; the range exists only in `data`. Window queries silently skip them.

- [ ] Add `loc_start_min/max` and `loc_end_min/max` (keep `loc_start`/`loc_end` for definite coordinates).

**Base:** `1.0` · **Size:** XS · **Priority:** low.

### C4 · Decisions (no code until decided)

- [ ] **`gene_context_name` on aggregates.** It is filled in only on SCV propositions
  (`gkm-scv-statement-proc.sql` builds `geneContextQualifier` per SCV); it is NULL on every VCV and RCV
  proposition. Either populate it for aggregates, or keep it SCV-only. Keeping it SCV-only is already
  documented as a trap on Joining Tables.
- [ ] **`condition` column names.** `condition.parquet` keeps camelCase (`conceptType`, `primaryCoding`) while
  every other table is snake_case. Renaming breaks consumers, so defer to the next MAJOR line (ADR 0004) and
  record it there.

---

## Workstream D — Distribution and operations

### D1 · Reconcile the CDN rate limit with ADR 0005

**Problem.** ADR 0005 documents `300 requests / 1 minute per IP, block 10 minutes`. Observed on 2026-10-15:
single-threaded DuckDB scans got HTTP 429 after about 55 requests in about 10 seconds, and blocks lifted within
about 90 seconds. Cloudflare's Free plan allows only a 10-second counting period, so the live rule likely
differs from the ADR.

- [ ] Read the live rule (Security → WAF → Rate limiting rules) and record the real period, threshold and
  mitigation time.
- [ ] Decide whether it is right for the live console and the documented remote-query boundary, then update
  ADR 0005 to match. Working at Scale and the console's error hints don't quote numbers, so they need no
  change.

**Owner:** maintainer with Cloudflare access · **Size:** XS (ADR edit).

### D2 · R2 spend alert

- [ ] Set up a Cloudflare Custom Alert on R2 Class B operations and storage. There is no dedicated R2 alert
  type on the Free plan and no hard spend cap, so this is the only safety net. Record the threshold in ADR 0005.

**Owner:** maintainer with Cloudflare access · **Size:** XS (no PR).

### D3 · Console: live release list, cacheable default

**Problem.**
- **Hardcoded release list:** `docs/assets/duckdb-console.html` lists its releases in the HTML (`00-latest`,
  `2026-10` … `2026-07`), so it goes stale every month.
- **Uncached default:** it defaults to `00-latest`, which bypasses the CDN cache, so every console read hits
  R2.

- [ ] Populate the Release dropdown from `https://data.clinvar-gkm.org/v1/index.json` (CORS is open), keeping
  the hardcoded list as a fallback.
- [ ] Default to the newest **dated** release (cacheable) and label it as the latest.
- [ ] Verify in headless Chromium: the list loads, the default is dated, and a query runs.

**Base:** `main` · **Size:** S · **Depends on:** nothing.

---

## Workstream E — Docs site

### E1 · Link and anchor check in the deploy workflow

**Problem.** `zensical build --strict` doesn't check `#anchor` fragments or links inside raw HTML (iframes,
diagram boxes, the console). Every check of those in the Query the Data work was done by a one-off script.

- [ ] Add `src/scripts/check-site-links.py` (built-site internal `href`/`src` and `#fragment` checker) and run
  it after the build in `deploy-docs.yml`. It should fail the deploy on a broken link.

**Base:** `main` · **Size:** S.

### E2 · Point docs at the live domain

- [ ] The site now serves from `dataexchange.clinicalgenome.org/clinvar-gkm/`; `github.io` 301-redirects.
  Update `site_url` in `zensical.toml` and the README link so canonical URLs, the sitemap and search use the
  live domain.

**Base:** `main` · **Size:** XS · **Check first:** that the custom domain is permanent.

### E3 · Backlog (separate plans when picked up)

- **Query with AI:** built and tested, then tabled; local branch `docs/ai-query-guide` (commit `82b5f3f`).
  Needs a design review before revival; see the commit message.
- **Data Model "Profiles" naming:** rename to something like "Mapping & Vocabularies", and fix "Propositions"
  appearing twice in that nav.
- **Orphaned pages:** `data-access/index.md`, `data-access/output-files.md`, `getting-started.md` and
  `output-reference/index.md` are reachable only by direct link.
- **Release-figure drift:** every count in the track is from the 2026-10 release. Generating figures at build
  time from a committed metrics file would end the manual banner updates.
- **Starter-kit page** and **docs links that follow the release branch:** existing backlog items.

---

## Suggested order

Data-changing work follows the consolidated release sequence above; this order covers everything else.

1. **A1** (`hgvs.?`, code done; release steps + option 2 backfill) and **B2** (bundle `oneOf`), on `1.0`, alongside
   #142. Same release, if possible.
2. **A2 part 1** (form-agnostic queries) now, on `main`, before #143's first export.
3. **D1** and **D2** (Cloudflare checks); quick and unblock nothing else, but close the operational gaps.
4. **E1** (link checker), so the remaining docs work is protected.
5. **D3** (console release list) and **C2** (therapy columns): small, independent.
6. **B1** (strict mode, gkm-metaschema) and **C1** (variant-sorted Parquet): the two items that need a plan
   first.
7. **C3**, **C4** decisions, **E2**, **E3** as capacity allows.
