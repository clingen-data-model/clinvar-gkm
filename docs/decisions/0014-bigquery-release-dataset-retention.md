# 0014 — Retention of BigQuery release tables

- **Status:** Proposed
- **Date:** 2026-11-24
- **Script:** [`src/scripts/prune-release-datasets.sh`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/src/scripts/prune-release-datasets.sh)

## Context

Every ClinVar release gets its own BigQuery dataset in `clingen-dev`, `clinvar_<yyyy>_<mm>_<dd>_<version>`. No rule
says what to keep in it. The 2026-11-22 dataset holds 101 tables and about 130 GB (logical bytes). Five sources write
into each dataset:

| Source | Tables (2026-11-22) | Size |
| --- | --- | --- |
| clinvar-ingest: the ingested ClinVar XML and its by-products (`variation`, `clinical_assertion`, `scv_summary`, …) | 21 | 62.4 GB |
| clinvar-ingest, using this repo's procedures: `diff_*` (`dataset_diff_on`) and `variation_identity`, `_loc`, `_hgvs`, `_xref` | 18 | 16.3 GB |
| This release, step 2: `gkm_vrs`, `gkm_dict_*`, the carried-forward intermediates | 29 | 50.5 GB |
| This release, the delta and its record: `gkm_change_log`, `delta_gkm_*`, the changed-id sets, `gkm_pipeline_version` | 32 | 0.1 GB |
| One-offs this repo does not create (`backup_rcv_accession_classification`; older datasets also hold `*_before_backfill`) | 1 | 0.7 GB |

Older datasets also hold tables that are no longer built: the pre-rename `gks_*` tables (2023-09 to 2026-06), the
retired `gkm_json` outputs (`gkm_catvar`, `gkm_{scv,rcv,vcv}_statement`), and `temp_*` tables left by debug runs.
Measured on 2026-11-24 (`bq show`, logical bytes), the datasets dated before 2026-10-31 hold:

| Tables | Count | Size |
| --- | --- | --- |
| Pre-rename `gks_*` | 1,041 | 5,217 GB |
| `temp_*`, `stg_*` (989 GB of it `temp_variation`, in 52 datasets) | 115 | 1,139 GB |
| `gkm_dict_*`, `gkm_vrs` and the intermediates, in 18 GKM-built datasets | 522 | 839 GB |
| Retired `gkm_json` outputs | 16 | 130 GB |
| clinvar-ingest working state (`diff_*`, `variation_identity` and its three tables; kept, see below) | 641 | 904 GB |

[ADR 0008](0008-bundles-are-the-public-record.md) made the published JSON bundles the public record. The monthly
fulls and deltas on R2 are immutable, and any past week can be rebuilt exactly from them. So no BigQuery table is
the record of a release. We need a rule for which tables to keep, and why.

## Decision

### A table is kept only if it does one of three jobs

1. **A later build or check reads it.** Only the next release and the checks on the newest one read another
   dataset:
    - `gkm_change_log` compares the new `gkm_dict_*` with the baseline's.
    - The delta oracle (`oracle-delta-reconstruction.sh`) rebuilds the new release from the baseline's `gkm_dict_*`.
    - `vrs-to-bq-table.sh` seeds `gkm_vrs` by cloning the baseline's.
    - `variation_identity_incremental` (run by clinvar-ingest) copies the baseline's `variation_*` tables forward.
    - The procedures' incremental wrappers carry the baseline's `gkm_*` tables forward. Weekly runs use
      `--full-procs` from 1.1.0, so today only the first four apply.

    The baseline is the newest dataset before the release (`clinvar_ingest.schema_on`).
2. **A product that is not yet published needs it.** `run-release.sh` builds a monthly full from its source
   release's weekly full, or re-exports it from that dataset's `gkm_dict_*` when the weekly full is gone
   ([ADR 0002](0002-monthly-full-anchored-to-clinvar-index.md)). A new version line starts from a checkpoint monthly
   rebuilt in full with the new procedures (ADR 0008, 1.2.0 decision D1: 2026-10-31 for `v1/1.2/`). The rebuild
   reads that dataset's ingest tables and `gkm_vrs`, and the checkpoint is the newest monthly source or a later
   release.
3. **It is the build's own record and costs almost nothing to keep.** `gkm_pipeline_version` names the code that
   built the dataset, and `run-release.sh` uses it to tell a GKM-built dataset from a raw one. `gkm_change_log`,
   `delta_gkm_*`, `gkm_scv_change_audit` and the changed-id sets record what changed in the release and why, in
   SQL. Together they are about 0.1 GB per dataset.

Every other table is working state. Once the releases that read it are published, its content is in the
bundles.

### The retention floor

The **retention floor** is the earlier of:

- the `source_release` of the line's newest published monthly (the next monthly's source is a later dataset),
- the baseline of the line's newest published delta (`latest_release` in the line's `index.json`).

A dataset dated **on or after** the floor is left whole. That window always contains the newest release, its
baseline, every candidate source of the next monthly, and the next line's checkpoint. On 2026-11-24 the floor is
2026-10-31 and the window holds four datasets: 10-31, 11-08, 11-15 and 11-22.

### What happens to each table below the floor

| Class | Tables | Below the floor |
| --- | --- | --- |
| Build record | `gkm_pipeline_version`, `gkm_change_log`, `gkm_scv_change_audit`, `delta_gkm_*`, `scv_changed_ids`, `scv_removed_ids`, `rcv_impacted_ids`, `vcv_impacted_ids`, `variation_vrs_changed`, `variation_vrs_removed`, `vi_extract` | **Keep forever** |
| Release working state | `gkm_dict_*`, `gkm_vrs`, `gkm_scv_condition_sets`, `gkm_{rcv,vcv}_{classification_agg,priority_agg,aggregate_contribution}` | **Drop** |
| Retired or leftover | `gks_*` (pre-rename), `gkm_catvar`, `gkm_{scv,rcv,vcv}_statement` (retired `gkm_json` outputs), `temp_*`, `stg_*` | **Drop** |
| Written by clinvar-ingest | the ingested ClinVar tables, `diff_*`, `variation_identity`, `variation_loc`, `variation_hgvs`, `variation_xref` | **Out of scope, never dropped here.** clinvar-ingest decides; the `variation_*` tables go back to 2023, before this pipeline, so other consumers may read them |
| Not ours | `backup_*`, `*_before_backfill`, `gc_scv_obs*`, anything else not named above | **Out of scope, never dropped here** |

### How the rule is applied

- `prune-release-datasets.sh` applies the table above. It reads the floor from the line's public `index.json`,
  prints its plan by default, and drops only with `--apply`. It refuses to plan if the index cannot be read or
  names a release that has no dataset. It has no option to drop anything clinvar-ingest writes.
- **Release datasets only.** The script touches only datasets named exactly
  `clinvar_<yyyy>_<mm>_<dd>_v<n>_<n>_<n>`, and checks the name again before each drop. `clinvar_ingest` (the
  shared procedures, functions and translation tables), `clinvar_curator*`, scratch and `_recon` datasets and
  every other dataset are never touched.
- Run it after a release is published, not during one. Never run it while a build or oracle is in progress.
- **Drop tables, never datasets.** The procedures take the newest *existing* dataset before a release as its
  baseline. A deleted dataset would make the next change log and delta cover two releases, which breaks the chain
  of contiguous deltas that consumers replay.
- A dropped table can be restored within its dataset's time-travel window (7 days by default):
  `bq cp <dataset>.<table>@-<ms> <dataset>.<table>`.

## Consequences

- **Storage.** The first run drops 1,694 tables and about 7.3 TB (logical), about $70 a month at the long-term
  logical storage list price. The bill depends on the project's
  storage billing model, so the dollar figure is an estimate. After that, each release that falls below the
  floor sheds about 50 GB and keeps about 0.1 GB of record.
- **Rebuilding is cheaper than keeping.** Rebuilding one dataset's `gkm_*` tables costs about 0.2 TiB of queries,
  roughly $1.25 on demand. Keeping its 50 GB of working state for a year costs about $6.
- **No SQL access to old releases' `gkm_dict_*`.** Questions about a past release are answered from its
  bundles (a monthly plus deltas), as for any consumer. The full-vs-incremental oracles and development checks need a pair of
  datasets at or above the floor, or a full rebuild first.
- **No rebuild below the floor without a full VRS translation.** With no baseline `gkm_vrs`, `vrs-to-bq-table.sh`
  falls back to a full load from a staging file that holds only the changed variations, which would leave
  `gkm_vrs` nearly empty. Rebuilding a release below the floor therefore needs a full re-translation upstream and
  `INCREMENTAL=false`. ADR 0008 already sends corrections to a new line from a checkpoint, so no such rebuild is
  planned.
- **Follow-ups.** The 0.9 TB of clinvar-ingest working state and the one-off tables (`backup_*`,
  `*_before_backfill`) are for clinvar-ingest and their owners to decide; this policy leaves them alone.
