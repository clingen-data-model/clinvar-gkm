# `gks_ → gkm_` BigQuery Rename — Implementation Plan

> **For agentic workers:** internal-only rename of the BigQuery compute layer. No consumer/R2 impact —
> R2 bundle section names are already clean (`allele`, `scv`, `varcond-proposition`, …). Steps use
> checkbox (`- [ ]`) syntax.

**Goal:** Rename every BigQuery `gks_*` procedure/table identifier (and the `gks`-named SQL/script files)
to `gkm_*`, deploy the renamed procs, migrate the already-built release datasets, and resume the pipeline
producing `gkm_*` natively — with zero change to the published `clinvar-gkm` R2 output.

**Architecture:** The `gks_*` procs live in the `clinvar_ingest` dataset and write `gks_dict_*` / `gks_vrs` /
`gks_change_log` / `delta_gks_dict_*` / `gks_pipeline_version` / `gks_scv_condition_sets` tables into each
per-release dataset (`clinvar_YYYY_MM_DD_v2_5_0`). Renaming is three coordinated layers: (1) code
(`src/procedures/*.sql` + all scripts that CALL procs or read those tables), (2) deployed procs in
`clinvar_ingest`, (3) the produced tables in each built release dataset.

**Tech Stack:** BigQuery stored procedures (dynamic SQL), bash pipeline scripts, Python assemble/manifest.

---

## Scope + guards

- **In scope:** the `gks_` identifier prefix (with underscore) everywhere it names a proc or a
  pipeline-produced table, plus `gks`-named filenames (`gks-*-proc.sql`, `export-gks-dicts.sh`,
  `upload-gks-to-r2.sh`, `upload-gks-delta-to-r2.sh`, `gks-change-log-proc.sql`, etc.).
- **NOT in scope / must not change:**
  - `gks-core` (a real upstream GA4GH schema id; hyphen, not `gks_`).
  - Bare "GKS" / "GA4GH GKS" / "Genomic Knowledge Standards" prose (that's the separate terminology pass).
  - Upstream ingest tables the procs READ (`variation`, `clinical_assertion`, `diff_*`, `rcv_mapping`,
    `schema_on`, `dataset_diff_on`, …) — these are not `gks_`-named and are owned by the ingest project.
  - Consumer-facing R2 layout (already `clinvar-gkm`, section names already clean).
- **Replacement precision:** target the token `gks_` (underscore) for identifiers and `gks-`/`gks.` in the
  specific filenames. A blanket `gks` replace is forbidden — it would hit `gks-core`, `GKS`, `clinvar-gkm`
  (no) etc. Verify with a dry `git grep` diff before applying.

## Design decisions (RECOMMENDED — confirm on review)

- **D1 — Rename filenames too (recommended: YES).** `gks-*-proc.sql → gkm-*-proc.sql`,
  `export-gks-dicts.sh → export-gkm-dicts.sh`, `upload-gks-*.sh → upload-gkm-*.sh`. Full consistency;
  costs `git mv` + updating the ~handful of scripts that source/call them by path. (Alternative: keep
  filenames, rename only in-file identifiers — less churn but leaves `gks` in filenames.)
- **D2 — Migrate built datasets by in-place table RENAME (recommended), not rebuild.** BigQuery
  `ALTER TABLE <ds>.gks_x RENAME TO gkm_x` per table (metadata-only, instant, no recompute). Applies to
  each already-built dataset (06-27, 07-06, 07-15, plus any other datasets whose `gks_*` outputs the
  pipeline still reads). (Alternative: rebuild under `gkm_` procs — clean but slow and redundant.)
- **D3 — Do this BEFORE resuming build-forward (recommended).** So 07-20/27 + the Aug releases are built
  natively as `gkm_*`, and only 06-27/07-06/07-15 need the table rename.
- **D4 — Cutover order:** deploy `gkm_*` procs alongside old `gks_*`, migrate tables, verify, THEN drop the
  old `gks_*` procs — so nothing is half-broken mid-migration.

---

## Chunk 1: Code rename (branch `chore/rename-gks-procs-gkm`)

- [ ] **1.1 Inventory** — `git grep -n 'gks_' -- src/ ':(exclude)docs/superpowers/*'` and classify each
  hit: proc name, produced-table name, or a false-positive (comment/upstream ref). Save the distinct
  identifier list (expect ~82) for the verification step.
- [ ] **1.2 Rename in-file identifiers** — `gks_ → gkm_` across `src/procedures/*.sql`,
  `src/scripts/*.sh`, `src/scripts/parquet-schemas/*.sql`, `src/scripts/build-delta-manifest.py`,
  `src/scripts/assemble-gks-dicts.py`, oracle scripts. Exclude any line referencing an upstream ingest
  table (none should match `gks_` anyway — verify).
- [ ] **1.3 `git mv` filenames** (D1): `gks-*-proc.sql → gkm-*`, `export-gks-dicts.sh → export-gkm-dicts.sh`,
  `upload-gks-to-r2.sh → upload-gkm-to-r2.sh`, `upload-gks-delta-to-r2.sh → upload-gkm-delta-to-r2.sh`,
  `assemble-gks-dicts.py → assemble-gkm-dicts.py`. Update every path reference (run-release.sh,
  release-gks*.sh → release-gkm*.sh, deploy scripts, docs).
- [ ] **1.4 Deploy script** — whatever deploys `src/procedures/*.sql` to `clinvar_ingest` now creates
  `gkm_*` procs. Confirm it reads the renamed files.
- [ ] **1.5 Verify** — `bash -n` all scripts; `shellcheck -S warning`; `mkdocs build --strict`;
  `git grep -c 'gks_' -- src/` returns only the intended-zero (or documented upstream refs).
- [ ] **1.6 Commit + PR.**

## Chunk 2: Deploy renamed procs to `clinvar_ingest`

- [ ] **2.1** Deploy all `gkm_*` procs (create alongside the existing `gks_*` — do NOT drop yet).
- [ ] **2.2** Verify via `INFORMATION_SCHEMA.ROUTINES` that all expected `gkm_*` procs exist (count ==
  the gks_* count).

## Chunk 3: Migrate built release datasets (D2, in-place rename)

- [ ] **3.1** Enumerate datasets to migrate: every `clinvar_*_v2_5_0` that holds `gks_*` outputs still in
  the active chain — at minimum 2026-06-27, 2026-07-06, 2026-07-15 (07-15 finishes on `gks_` first).
  (Also any release whose `gks_dict_*` a later incremental run carries forward from.)
- [ ] **3.2** For each dataset, `ALTER TABLE` rename every `gks_*` table → `gkm_*` and `delta_gks_dict_* →
  delta_gkm_dict_*` (script the list from `INFORMATION_SCHEMA.TABLES WHERE table_name LIKE 'gks\\_%' OR
  LIKE 'delta_gks_%'`). Include `gks_vrs`, `gks_change_log`, `gks_pipeline_version`, `gks_scv_condition_sets`.
- [ ] **3.3** Verify each dataset has the `gkm_*` set and no residual `gks_*`.

## Chunk 4: End-to-end verification

- [ ] **4.1** Re-run the delta-reconstruction oracle (now `gkm-`named) on 06-27 → 07-06 → expect
  `0,0,0` (a pure rename must not change output).
- [ ] **4.2** Re-publish (or dry-run) 07-06 delta from the renamed scripts → confirm identical
  manifest/bundle vs what's live in `clinvar-gkm` (rename is output-neutral).

## Chunk 5: Cutover + resume

- [ ] **5.1** Drop the old `gks_*` procs from `clinvar_ingest`.
- [ ] **5.2** Merge Chunk-1 PR to main.
- [ ] **5.3** Resume build-forward: 07-20 → 07-27 (now on `gkm_` procs; 07-15 already migrated), then the
  Aug releases (after their vrsify runs).

---

## Risks / notes
- **Pure rename must be output-neutral** — Chunk 4's oracle is the guard. If it's not `0,0,0`, a
  reference was missed (a proc still writing/reading a `gks_`-named table).
- **In-flight 07-15** finishes on `gks_*`; it gets migrated in Chunk 3 like 06-27/07-06.
- **Upstream `dataset_diff_on` / `variation_identity` / `gks_vrs` load**: `gks_vrs` is produced by
  `vrs-to-bq-table.sh`'s load step (rename to `gkm_vrs` in both the script and the migrated datasets);
  `variation_identity` and `diff_*` are upstream (not renamed).
- **`clinvar_ingest` is shared** — deploying `gkm_*` alongside `gks_*` is additive/safe; only Chunk 5.1
  (drop old) is destructive, and only after verification.
