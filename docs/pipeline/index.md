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
│ 2. VRS Processing            │  External: vrs-python
│    Export → VRS Python →     │  → gkm_vrs table
│    Import back to BigQuery   │
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
│    upload to R2; rebuild     │  → R2 public bucket
│    the latest Parquet        │
└──────────────────────────────┘
```

## Running the Pipeline

### Single-command run

The whole release can be run end-to-end with the `run-release.sh` orchestrator, which chains five stages: variation identity, the GCS export, vrsification, the transform/load/procedures step (`vrs-to-bq-table.sh`), and the export/publish step (`release-gkm.sh`):

```bash
./src/scripts/run-release.sh YYYY-MM-DD              # incremental (default)
./src/scripts/run-release.sh YYYY-MM-DD --full       # full rebuild / reseed
./src/scripts/run-release.sh YYYY-MM-DD --full-procs # only the gkm procs full (the weekly mode after 1.1.0)
./src/scripts/run-release.sh YYYY-MM-DD --dry-run    # run everything but skip the R2 publish (stage 5)
./src/scripts/run-release.sh YYYY-MM-DD --start-step 5   # resume from a stage (1-5)
```

`--full` propagates version-invalidation across stages 1–2; use it for the first release or after a `variation_identity` transform change or a vrsify-pin bump. `--full-procs` builds only the stage-4 gkm procedures full (catvar, SCV, RCV, VCV): variation identity, the export, vrsification and the `gkm_vrs` load stay incremental, so only the changed variations are re-normalized. Weekly runs after 1.1.0 use `--full-procs` until [ADR 0007](../decisions/0007-pipeline-principles-and-simplification.md) workstream 3 decides on the incremental procedures, which were seen to fall back to full builds without saying so. `--full` implies `--full-procs`. `--dry-run` runs the build stages but has the final release stage only print what it would upload — use it for test runs. The vrsify stage (stage 3) requires local SeqRepo and gene-normalizer services and a reachable UTA database — see [VRS Processing](vrs-processing.md#running-vrsify) and [`src/vrsify/README.md`](https://github.com/clingen-data-model/clinvar-gkm/tree/main/src/vrsify) — so on hosts without them, run the BigQuery-side stages with `--start-step` and run vrsify separately.

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

Export, process externally with vrs-python, and load back — incremental by default (only changed variations are vrsified; unchanged `gkm_vrs` results carry forward). See [VRS Processing](vrs-processing.md).

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

The `gkm_dict_*` tables are the published product. Full bundles, deltas and the latest Parquet are published by separate scripts:

```bash
# Weekly full bundle (export NDJSON, assemble, upload to weekly/)
./src/scripts/release-gkm.sh 2026-10-18 v2_6_0 --weekly

# Weekly delta (added + updated records + change manifest)
./src/scripts/release-gkm-delta.sh 2026-10-18 v2_6_0

# Latest Parquet (typed EXPORT DATA, merge shards, overwrite parquet/)
./src/scripts/release-gkm-parquet.sh 2026-10-18 v2_6_0
```

`release-gkm.sh` exports bundle NDJSON only (`export-gkm-dicts.sh --ndjson-only`), assembles it and uploads the bundle; it writes no Parquet. Its steps can be run individually, and `--start-step` resumes it from a step:

```bash
# 1. Export dictionary tables to GCS (bundle NDJSON only)
./src/scripts/export-gkm-dicts.sh clinvar_2026_10_18_v2_6_0 clinvar-gkm gkm-dicts --ndjson-only

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
