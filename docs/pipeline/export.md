# Export & Distribute

The final pipeline step exports the `gkm_dict_*` tables from BigQuery, assembles them into a single keyed JSON bundle, and uploads to Cloudflare R2 for public distribution. A separate step rebuilds the single latest Parquet set from every release.

The `gkm_dict_*` tables **are** the published product — they are built directly by the statement procedures (steps 5–7) and the change-log step (step 8). The retired `gkm_json_proc` is not part of this path; its inlined JSON-render tables were never published. See [Retired: gkm_json_proc](#retired-gkm_json_proc).

Distribution follows a **full + delta** model:

- A **weekly full bundle** (JSON) is published for every release via `release-gkm.sh --weekly` / `upload-gkm-to-r2.sh --weekly`, into `weekly/`.
- The **official monthly full bundle** (JSON) is published once a month. `run-release.sh` normally makes it a server-side copy of its source release's weekly full (`upload-gkm-to-r2.sh --month-label=YYYY-MM --from-weekly`), and re-exports it with `release-gkm.sh --month-label=YYYY-MM` when that weekly full is gone.
- A **weekly delta** — added and updated records plus a change manifest — is published for every release via `release-gkm-delta.sh` / `upload-gkm-delta-to-r2.sh`.
- The **latest Parquet** — derived from the bundle, one typed file per section — is rebuilt from every release's dataset via `release-gkm-parquet.sh` / `upload-gkm-parquet-to-r2.sh`. It is not kept per release.
- Every bundle gets a `<file>.sha256` sidecar.

---

## Workflow

The export and distribution process uses four steps, executed in sequence. The `release-gkm.sh` wrapper runs all four automatically, or each step can be run individually.

### Step 1: Export Dictionaries to GCS

`export-gkm-dicts.sh` exports all dictionary and statement tables from BigQuery to Google Cloud Storage in two formats:

- **NDJSON** — sharded, gzip-compressed files for JSON bundle assembly (`gkm-dicts/`)
- **Parquet** — Snappy-compressed files exported natively via `bq extract` (`gkm-dicts-parquet/`)

```bash
./src/scripts/export-gkm-dicts.sh <dataset> <gcs_bucket> [prefix] [--parquet-only]
```

```bash
# Export both NDJSON and Parquet
./src/scripts/export-gkm-dicts.sh clinvar_2026_06_14_v2_5_0 clinvar-gkm gkm-dicts

# Export Parquet only (skip NDJSON)
./src/scripts/export-gkm-dicts.sh clinvar_2026_06_14_v2_5_0 clinvar-gkm gkm-dicts --parquet-only
```

The script exports the following 19 tables:

| Table | NDJSON Output | Parquet Output |
| --- | --- | --- |
| `gkm_dict_sequence_reference` | `sequenceReference-*.ndjson.gz` | `sequenceReference.parquet` |
| `gkm_dict_location` | `location-*.ndjson.gz` | `location.parquet` |
| `gkm_dict_allele` | `allele-*.ndjson.gz` | `allele.parquet` |
| `gkm_dict_copy_number_count` | `copyNumberCount-*.ndjson.gz` | `copyNumberCount.parquet` |
| `gkm_dict_copy_number_change` | `copyNumberChange-*.ndjson.gz` | `copyNumberChange.parquet` |
| `gkm_dict_gene` | `gene-*.ndjson.gz` | `gene.parquet` |
| `gkm_dict_variation` | `variation-*.ndjson.gz` | `variation.parquet` |
| `gkm_dict_condition` | `condition-*.ndjson.gz` | `condition.parquet` |
| `gkm_dict_condition_set` | `conditionSet-*.ndjson.gz` | `conditionSet.parquet` |
| `gkm_dict_submitter` | `submitter-*.ndjson.gz` | `submitter.parquet` |
| `gkm_dict_proposition` | `proposition-*.ndjson.gz` | `proposition.parquet` |
| `gkm_dict_evidence_line` | `evidenceLine-*.ndjson.gz` | `evidenceLine.parquet` |
| `gkm_dict_vcv_proposition` | `vcv_proposition-*.ndjson.gz` | `vcv_proposition.parquet` |
| `gkm_dict_vcv_evidence_line` | `vcv_evidenceLine-*.ndjson.gz` | `vcv_evidenceLine.parquet` |
| `gkm_dict_rcv_proposition` | `rcv_proposition-*.ndjson.gz` | `rcv_proposition.parquet` |
| `gkm_dict_rcv_evidence_line` | `rcv_evidenceLine-*.ndjson.gz` | `rcv_evidenceLine.parquet` |
| `gkm_dict_scv` | `scv-*.ndjson.gz` | `scv.parquet` |
| `gkm_dict_vcv` | `vcv-*.ndjson.gz` | `vcv.parquet` |
| `gkm_dict_rcv` | `rcv-*.ndjson.gz` | `rcv.parquet` |

BigQuery `EXTRACT` shards large NDJSON tables across multiple files automatically. Parquet files are exported as single files per table; BigQuery may auto-shard very large tables with numeric suffixes.

### Step 2: Assemble Bundle

`assemble-gkm-dicts.py` reads all NDJSON shard files and assembles them into a single keyed JSON bundle file.

```bash
python3 ./src/scripts/assemble-gkm-dicts.py <source> <date> [--keep-source] [--copy-to-gcs]
```

`<source>` is a local path or `gs://` URI containing the NDJSON shards. `<date>` is the ClinVar release date (`YYYY-MM-DD`); the output path is derived as `/tmp/clinvar-gkm-{date}.json.gz`. By default, source files are deleted after assembly; use `--keep-source` to retain them.

```bash
python3 ./src/scripts/assemble-gkm-dicts.py \
  gs://clinvar-gkm/gkm-dicts/ \
  2026-06-14
```

The script assembles 20 bundle sections in a fixed order: `sequenceReference`, `location`, `allele`, `copyNumberCount`, `copyNumberChange`, `gene`, `variation`, `condition`, `conditionSet`, `therapy`, `therapyGroup`, `submitter`, `propositionPathogenicity`, `propositionOncogenicity`, `propositionSomaticClinicalImpact`, `propositionClinvarCustom`, `evidenceLine`, `scv`, `vcv`, `rcv`. The `therapy` / `therapyGroup` sections hold content-addressed (deduplicated) drug therapies referenced by `VariantTherapeuticResponseProposition.object` via `#/therapy/` and `#/therapyGroup/`. Each section is a keyed object where the key is the record's unique identifier. Propositions from SCV, VCV, and RCV are delivered in **four sections grouped by meaning** — `propositionPathogenicity`, `propositionOncogenicity`, `propositionSomaticClinicalImpact` (clinical significance, diagnostic, prognostic, therapeutic response), `propositionClinvarCustom` (the `Clinvar*` types) — split by the one canonical function `clinvar_ingest.gkm_proposition_section(type)`, which fails the export on an unmapped type; evidence line shards are merged into a single `evidenceLine` section.

Install `orjson` for best performance:

```bash
pip install orjson
```

### Step 3: Rebuild the Latest Parquet

Parquet is derived from the bundle and regenerated each release; one dataset is published, at
`v1/1.1/parquet/`, and overwritten every release (ADR 0009).
`release-gkm-parquet.sh` builds it from a dataset (`run-release.sh` runs it on every release, after the weekly
delta):

```bash
./src/scripts/release-gkm-parquet.sh <export_date> <dataset_version> [--start-step=N] [--dry-run] [--no-upload] [--purge]
```

1. `export-gkm-dicts.sh --parquet-only` exports the full dict tables as typed Parquet to GCS.
2. The shards are downloaded and merged into one file per section with DuckDB.
3. `upload-gkm-parquet-to-r2.sh` overwrites each section in `parquet/`, writes `manifest.json` (`build_date`,
   `source_release`, `dataset`, `builder`, `table_spec_version`, `schema_version`, and each file's `name`, `size`
   and `sha256`), deletes any file that is no longer produced, and regenerates `index.json`. With `--purge`
   (which `run-release.sh` passes) it also purges the folder from the CDN.

The 22 tables and their columns are in [The 22 Tables](../parquet/tables.md); see
[Parquet Files](../data-access/parquet.md) for the download URL.

### Step 4: Upload the Weekly and Monthly Fulls to R2

`upload-gkm-to-r2.sh` uploads a full bundle and its `.sha256` sidecar to Cloudflare R2, as one of two kinds:

- **`--weekly`** — the weekly full of `<export_date>`, written to `weekly/clinvar-gkm_yyyy-mmdd.json.gz`; when it is the newest weekly full it is also copied to `weekly/clinvar-gkm_00-latest_weekly.json.gz`. A weekly full older than the line's current month is refused.
- **`--month-label=YYYY-MM`** — the official monthly, published **once a month, aligned to ClinVar's own monthly VCV releases**: when a new `ClinVarVCVRelease_YYYY-MM.xml.gz` appears at ClinVar's [XML index](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/), `run-release.sh` publishes our `clinvar-gkm_YYYY-MM` full from the most recent weekly release **before** ClinVar's monthly cut datetime (ADR 0002). `<export_date>` is that source release, so the month slot is set independently of it (e.g. the `2026-07` full is built from our `2026-06-27` release, the last one before ClinVar's `_2026-07` cut). With `--from-weekly` the monthly is a server-side copy of `weekly/clinvar-gkm_<export_date>.json.gz` and no local bundle is needed (pass `-`). When it is the newest monthly it is also copied to `clinvar-gkm_00-latest.json.gz`, and the index records `<export_date>` as the monthly's `source_release`.

```bash
./src/scripts/upload-gkm-to-r2.sh <export_date> <dataset_version> <bundle_file|-> \
  [--weekly | --month-label=YYYY-MM [--from-weekly]] [--dry-run] [--purge]
```

```bash
# A release's weekly full (+ sha256 sidecar)
./src/scripts/upload-gkm-to-r2.sh 2026-10-18 v2_6_0 /tmp/clinvar-gkm-2026-10-18.json.gz --weekly

# The 2026-10 official monthly, as a server-side copy of the weekly full of its source release, 2026-09-28
./src/scripts/upload-gkm-to-r2.sh 2026-09-28 v2_6_0 - --month-label=2026-10 --from-weekly

# Preview without uploading
./src/scripts/upload-gkm-to-r2.sh 2026-10-18 v2_6_0 /tmp/clinvar-gkm-2026-10-18.json.gz --weekly --dry-run
```

The R2 layout mirrors NCBI's ClinVar XML folder (ADR 0009). Under the line folder `v1/1.1/`:

- **top level** — official monthly fulls for the current year (`clinvar-gkm_yyyy-mm.json.gz`) plus a stable `clinvar-gkm_00-latest.json.gz`, each with a `.sha256` sidecar
- **`weekly/`** — a weekly full bundle for every release of the current month (`clinvar-gkm_yyyy-mmdd.json.gz`) plus a stable `clinvar-gkm_00-latest_weekly.json.gz`
- **`archive/{yyyy}/`** — monthly fulls from prior years, and their deltas under `archive/{yyyy}/deltas/{yyyy-mm}/`

Rollovers are done by `r2-rollover.sh <release_date>`, which `run-release.sh` runs before the weekly uploads and again after any monthly is published; it is idempotent, so a run with nothing to move does nothing. **New month** (the first release dated in a new month): the finished month's deltas move into `deltas/{yyyy-mm}/` and its weekly fulls are deleted, except the newest, which is kept until the new month's official monthly is published (the monthly's source candidate) and deleted by the run that publishes it. **New year:** the finished year's monthlies and delta folders move into `archive/{yyyy}/`. Each move or delete is followed by a CDN purge of the old paths. After upload, `generate-r2-index.sh` regenerates the line's `index.json`, which lists the monthlies (with their sha256 and `source_release`, the release each was built from), the weekly fulls, the deltas wherever they now sit, the `archive` years and the Parquet dataset.

### Step 5: Publish the Weekly Delta

`release-gkm-delta.sh` publishes the per-release delta for every ClinVar release. It exports the `delta_<dict>` change tables produced by step 8 of the pipeline, assembles a delta bundle (added + updated records, same section structure as the full), builds the delta manifest, and uploads them to R2. Deltas carry no Parquet.

```bash
./src/scripts/release-gkm-delta.sh <export_date> <dataset_version> [--start-step=N] [--dry-run]
```

```bash
# Publish the weekly delta for a release
./src/scripts/release-gkm-delta.sh 2026-07-06 v2_5_0
```

The three internal steps are: export delta tables to GCS, assemble the delta bundle, then build the manifest (`build-delta-manifest.py`) and upload (`upload-gkm-delta-to-r2.sh`). The uploader writes:

- **`deltas/`** — the delta bundle (`clinvar-gkm-delta_<yyyy-mmdd>.json.gz`), its `.sha256` sidecar, and its manifest (`clinvar-gkm-delta_<yyyy-mmdd>.manifest.json`); the current month's deltas sit here, earlier months in `deltas/<yyyy-mm>/`

`build-delta-manifest.py` derives each section's `added` / `updated` counts and `deleted` primary-key list from the dataset's `gkm_change_log`, and records `baseline_release`, `compare_release`, `pipeline_version`, and `counts`. The uploader then completes the manifest: `checkpoint_full` (`{path, release, month, sha256}`, the newest official monthly whose `source_release` is on or before the delta's `baseline_release`, with `release` set to that `source_release`) so a consumer knows which monthly the delta chain replays onto, plus `schema_version`, `bundle` (`{name, path, size, sha256}`) and `sha256`. It also checks the chain: a delta whose `baseline_release` is not the release of the newest delta already in the line is refused (`--allow-gap` overrides). Monthlies are therefore published before the deltas that follow them. See [Weekly Deltas](../data-access/weekly-deltas.md) for the manifest shape and the consumer replay model.

---

## R2 bucket CORS policy

The release browsers on the Downloads pages — the [Monthly Full Bundles](../data-access/monthly-full.md), [Weekly Full Bundles](../data-access/weekly-full.md), [Weekly Deltas](../data-access/weekly-deltas.md), and [Parquet Files](../data-access/parquet.md) child pages, plus the Downloads hub's Latest Release view — each do a cross-origin `fetch()` of `index.json` from the docs site. That only works if the public R2 bucket serves a CORS policy allowing `GET` from other origins — otherwise the browsers block the read and can't populate (they then show a network/CORS message with a `curl` fallback).

The policy is checked in at [`src/scripts/r2-cors.json`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/src/scripts/r2-cors.json) (`GET`/`HEAD` from `*` — appropriate for public, read-only data). It is **not** applied by the release scripts, because their object-scoped `r2` upload token cannot read or write bucket configuration (`PutBucketCors` → `AccessDenied`). Apply it once with an **Admin Read & Write** R2 token:

```bash
# after configuring an admin token as an aws profile (default name: r2admin)
./src/scripts/apply-r2-cors.sh            # or: ./src/scripts/apply-r2-cors.sh <profile>
```

Or paste `r2-cors.json`'s rules into the Cloudflare dashboard: **R2 → clinvar-gkm → Settings → CORS Policy**. It only needs to be re-applied if the bucket is recreated or the policy is cleared.

---

## Retired: gkm_json_proc

`gkm_json_proc` previously rendered the statement and dictionary tables into inlined JSON columns. Those render tables were **never published** — the export assembles the bundle directly from the `gkm_dict_*` tables — so the procedure has been retired from the hot path. The null/empty stripping it used to perform is now applied during assembly (`assemble-gkm-dicts.py`), matching the old `remove_empty` cleanup. `gkm_json_proc` is not a live pipeline step and not a downstream consumer of the dictionary tables.

---

## Prerequisites

- **Google Cloud SDK** — `bq` and `gsutil` commands for BigQuery export and GCS operations
- **AWS CLI** — configured with an `r2` profile for Cloudflare R2 access
- **Python 3** — for the assembly script; `orjson` (faster JSON) recommended
- **DuckDB CLI** — for merging Parquet shards into single files per section
- **BigQuery access** — read access to the target dataset in `clingen-dev`

---

## Full Example

Publish the monthly full bundle for June 14, 2026:

```bash
./src/scripts/release-gkm.sh 2026-06-14 v2_5_0
```

This runs export to GCS, assembly of the JSON bundle, and the upload of the monthly full to R2.

Publish the weekly delta for the same release:

```bash
./src/scripts/release-gkm-delta.sh 2026-06-14 v2_5_0
```

The export and assembly can also be run individually; use `--start-step` to resume `release-gkm.sh` from a specific step (1 export, 2 assemble, 3 upload). Rebuild the latest Parquet with `./src/scripts/release-gkm-parquet.sh 2026-06-14 v2_5_0`.

```bash
# 1. Export dictionary tables to GCS (bundle NDJSON only)
./src/scripts/export-gkm-dicts.sh clinvar_2026_06_14_v2_5_0 clinvar-gkm gkm-dicts --ndjson-only

# 2. Assemble NDJSON into a single JSON bundle
python3 ./src/scripts/assemble-gkm-dicts.py \
  gs://clinvar-gkm/gkm-dicts/ \
  2026-06-14

# 3. Upload to R2
./src/scripts/release-gkm.sh 2026-06-14 v2_5_0 --start-step=3
```
