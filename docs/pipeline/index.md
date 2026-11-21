# Pipeline Overview

The ClinVar-GKM pipeline transforms ClinVar XML release data into the GKM (Genomic Knowledge Model) schema set (VRS, Cat-VRS, VA-Spec) through a series of BigQuery stored procedures with an external VRS Python processing step.

The two most expensive stages — [Variation Identity](variation-identity/index.md) and [VRS Processing](vrs-processing.md) — run **incrementally**: they recompute only the variations that changed since the prior release and carry the rest forward, driven by the release-to-release diff (`dataset_diff_on`). The downstream `gkm_*` procedures also have incremental wrappers, but from 1.1.0 the weekly run builds them in full (`run-release.sh <date> --full-procs`). The incremental wrappers proved no cheaper (about 0.22 TiB billed per dataset, against about 0.20 TiB for a full build) and fell back to a full build without saying so; [ADR 0007](../decisions/0007-pipeline-principles-and-simplification.md) workstream 3 decides their future.

## Pipeline Steps

The pipeline executes in the following order. Each step is a BigQuery stored procedure unless otherwise noted.

```
┌──────────────────────────────┐
│ 1. Variation Identity        │  variation_identity[_incremental]
│    Extract & normalize       │  → variation_identity table
│    variant data              │
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│ 2. VRS Processing            │  Upstream: vrs-python
│    Export → cloud vrsify →   │  (clinvar-ingest)
│    Import back to BigQuery   │  → gkm_vrs table
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│ 3. Cat-VRS Generation        │  gkm_catvar_proc
│    Canonical alleles &       │  → gkm_catvar table
│    categorical variants      │
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│ 4. Conditions & Traits       │  gkm_scv_condition_proc
│    Map traits, build         │  → condition mapping &
│    conditions & condition    │    condition set tables
│    sets                      │
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│ 5. SCV Statements            │  gkm_scv_statement_proc
│    Build SCV records,        │  → gkm_dict_scv table
│    propositions & statements │
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│ 6. VCV Statements            │  gkm_vcv_proc +
│    Aggregate SCVs into       │  gkm_vcv_statement_proc
│    variant-level statements  │  → gkm_dict_vcv table
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│ 7. RCV Statements            │  gkm_rcv_proc +
│    Aggregate SCVs into       │  gkm_rcv_statement_proc
│    condition-level statements│  → gkm_dict_rcv table
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│ 8. Change log + deltas       │  gkm_change_log +
│    A/U/D per dict + delta     │  gkm_delta_build
│    payloads for publishing    │  → gkm_change_log, delta_<dict>
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│ 9. Export & Distribute       │  release-gkm.sh (fulls),
│    Export NDJSON to GCS,     │  release-gkm-delta.sh,
│    assemble JSON bundles,    │  release-gkm-parquet.sh
│    upload to R2; build the   │  (gkm-bundle-parquet)
│    Parquet from the bundle   │  → R2 public bucket
└──────────────────────────────┘
```

## Running the Pipeline

### Single-command run

The whole release can be run end-to-end with the `run-release.sh` orchestrator, which chains six stages: variation identity and the GCS export (stages 1–2, which run upstream and are skipped unless `--with-upstream-stages`), a check of the upstream cloud vrsification, the transform/load/procedures step (`vrs-to-bq-table.sh`), the export/publish step (`release-gkm.sh`, `release-gkm-delta.sh`), and the Parquet step (`release-gkm-parquet.sh`), which builds the latest Parquet set from the published weekly full with [gkm-bundle-parquet](https://github.com/clingen-data-model/gkm-bundle-parquet) ([PyPI](https://pypi.org/project/gkm-bundle-parquet/2.0.0/), pinned to 2.0.0):

```bash
./src/scripts/run-release.sh YYYY-MM-DD              # incremental (default); starts at the stage-3 check
./src/scripts/run-release.sh YYYY-MM-DD --full-procs # only the gkm procs full (the weekly mode after 1.1.0)
./src/scripts/run-release.sh YYYY-MM-DD --with-upstream-stages   # also run stages 0-2 here (start step 1)
./src/scripts/run-release.sh YYYY-MM-DD --full --with-upstream-stages  # full stages 1-2, then stop at stage 3
./src/scripts/run-release.sh YYYY-MM-DD --start-step 4 --allow-unchecked-vrs  # load without the check (local fallback)
./src/scripts/run-release.sh YYYY-MM-DD --dry-run    # run everything but skip the R2 publish (stages 5 and 6)
./src/scripts/run-release.sh YYYY-MM-DD --skip-parquet   # leave parquet/ as it is (skip stage 6)
./src/scripts/run-release.sh YYYY-MM-DD --start-step 5   # resume from a stage (1-6); 6 runs only the Parquet step
```

Stages 0–2 (`dataset_diff_on`, `variation_identity_incremental` and the incremental export) run upstream in clinvar-ingest for every release, so `run-release.sh` starts at stage 3 by default. Running them here again could race the upstream export, and a rewritten `vi.jsonl.gz` with new content no longer matches the cloud translation, which runs once per release; `--with-upstream-stages` runs them anyway (`--start-step 1` and `2` need it). `--full` **stops at stage 3**, because a full re-translation needs an upstream run first: with `--with-upstream-stages` it rebuilds `variation_identity` in full and writes the full export, then stops; without it, it stops at once. After the upstream full translation, continue with `--full-procs --start-step 4` (see the [version-invalidation note](vrs-processing.md#step-4-transform-load-run-procedures)). `--full-procs` builds only the stage-4 gkm procedures full (catvar, SCV, RCV, VCV): variation identity, the export, vrsification and the `gkm_vrs` load stay incremental, so only the changed variations are re-normalized. Weekly runs after 1.1.0 use `--full-procs` until [ADR 0007](../decisions/0007-pipeline-principles-and-simplification.md) workstream 3 decides on the incremental procedures, which were seen to fall back to full builds without saying so. `--dry-run` runs the build stages but has the release stages only print what they would upload — use it for test runs. vrs-python runs upstream, in clinvar-ingest's `clinvar-ingest-vrsify` Cloud Run job, so no stage needs local services. Stage 3 only checks that the job's output, `vi-vrs-python.jsonl.gz`, is the translation of the release's current `vi.jsonl.gz`, and stops the release at once otherwise (it does not wait); run the release again once it is (see [Checking the cloud output](vrs-processing.md#checking-the-cloud-output)). `--start-step 4` runs the same check before loading `gkm_vrs`; `--allow-unchecked-vrs` skips it, for the [local fallback](vrs-processing.md#local-vrsify-fallback).

The individual stages are documented below.

### Step 1: Variation Identity

From the BigQuery console — incremental by default, full rebuild when reseeding (see [Incremental Rebuild](variation-identity/index.md#incremental-rebuild)):

```sql
-- default: recompute only changed variations, carry the rest forward
CALL `clinvar_ingest.variation_identity_incremental`(CURRENT_DATE(), FALSE);

-- full rebuild: first release, or after a variation_identity transform change
CALL `clinvar_ingest.variation_identity`(CURRENT_DATE(), FALSE);
```

### Step 2: VRS Processing

Export, translate with vrs-python upstream (the `clinvar-ingest-vrsify` Cloud Run job), and load back — incremental by default (only changed variations are vrsified; unchanged `gkm_vrs` results carry forward). See [VRS Processing](vrs-processing.md).

### Step 3: Cat-VRS through the Change Log

`vrs-to-bq-table.sh` runs these after loading `gkm_vrs`. The full builds, in the order it calls them, from the BigQuery console:

```sql
CALL `clinvar_ingest.gkm_catvar_proc`(CURRENT_DATE(), FALSE);
CALL `clinvar_ingest.gkm_scv_condition_proc`(CURRENT_DATE(), FALSE);
CALL `clinvar_ingest.gkm_scv_statement_proc`(CURRENT_DATE(), FALSE);
CALL `clinvar_ingest.gkm_rcv_proc`(CURRENT_DATE(), FALSE);
CALL `clinvar_ingest.gkm_rcv_statement_proc`(CURRENT_DATE(), FALSE);
CALL `clinvar_ingest.gkm_vcv_proc`(CURRENT_DATE(), FALSE);
CALL `clinvar_ingest.gkm_vcv_statement_proc`(CURRENT_DATE(), FALSE);
CALL `clinvar_ingest.gkm_change_log`(CURRENT_DATE());
CALL `clinvar_ingest.gkm_delta_build`(CURRENT_DATE());
-- NOTE: gkm_json_proc is retired (Plan 4) — its JSON-render tables were unpublished;
-- the gkm_dict_* tables are the published product and are built by the procs above.
```

The statement procedures name each proposition's bundle section with the UDF `clinvar_ingest.gkm_proposition_section(type)`, which must be deployed with them. The script also runs `gkm_scv_changed` and `gkm_rcvvcv_changed`, which build the changed-id sets, before the SCV and RCV/VCV procedures; without `--full-procs` it calls each procedure's `_incremental` wrapper instead of its full build.

### Step 4: Export & Distribute

The `gkm_dict_*` tables are the published product. Full bundles, deltas and the latest Parquet are published by separate scripts; the Parquet set is built from the published weekly full, not from BigQuery:

```bash
# Weekly full bundle (export NDJSON, assemble, upload to weekly/)
./src/scripts/release-gkm.sh 2026-10-18 v2_6_0 --weekly

# Weekly delta (added + updated records + change manifest)
./src/scripts/release-gkm-delta.sh 2026-10-18 v2_6_0

# Latest Parquet (gkm-bundle-parquet builds it from the published weekly full, verifies it, overwrites parquet/)
./src/scripts/release-gkm-parquet.sh 2026-10-18 v2_6_0
```

The full and delta scripts validate every record of their bundle strictly before upload, with jsonschema-rs, and stop if any fails. The GA4GH GKM Toolkit gives the same verdicts but takes hours where jsonschema-rs takes minutes; it cross-checks a sample at each version release ([Release Validation](../reference/release-validation.md)). See [Export & Distribute](export.md#step-4-publish-the-weekly-delta), and [Step 5](export.md#step-5-build-and-publish-the-latest-parquet) there for the Parquet build and its checks.

`release-gkm.sh` exports bundle NDJSON (`export-gkm-dicts.sh`), assembles and validates it, and uploads the bundle; it writes no Parquet. Its steps can be run individually, and `--start-step` resumes it from a step:

```bash
# 1. Export dictionary tables to GCS (bundle NDJSON)
./src/scripts/export-gkm-dicts.sh clinvar_2026_10_18_v2_6_0 clinvar-gkm gkm-dicts

# 2. Assemble NDJSON into JSON bundle
python3 ./src/scripts/assemble-gkm-dicts.py gs://clinvar-gkm/gkm-dicts/ 2026-10-18

# 3. Upload to R2
./src/scripts/release-gkm.sh 2026-10-18 v2_6_0 --weekly --start-step=3
```

See [Export](export.md) for details on each step.

## Documentation Tracks

The pipeline documentation serves two audiences:

- **Pipeline** (this section) — documents how data flows through BigQuery stored procedures, including internal table schemas, transformation logic, and step-by-step workflows. Each step is tagged as <span class="role-badge badge-pipeline">Pipeline table</span>, <span class="role-badge badge-artifact">JSON artifact</span>, or <span class="role-badge badge-internal">Internal</span> to indicate its role
- **[Output Reference](../output-reference/index.md)** — documents the JSON output files from a consumer perspective, covering record structure, field meanings, and usage guidance

---

## Detailed Documentation

Each pipeline step has its own documentation page:

- [Variation Identity](variation-identity/index.md) — variant extraction, normalization, VRS class assignment
- [VRS Processing](vrs-processing.md) — external VRS Python step
- [Cat-VRS](cat-vrs/index.md) — categorical variant generation
- [Conditions & Traits](conditions-and-traits/index.md) — condition mapping, traits, condition sets
- [SCV Statements](scv-statements/index.md) — SCV records, propositions, final statements
- [VCV Statements](vcv-statements/index.md) — aggregate variant-level VCV statements
- [RCV Statements](rcv-statements/index.md) — aggregate condition-level RCV statements
- [Export & Distribute](export.md) — export to GCS, assemble bundle, upload to R2
