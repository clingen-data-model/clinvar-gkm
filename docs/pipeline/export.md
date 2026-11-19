# Export & Distribute

The final pipeline step exports the `gkm_dict_*` tables from BigQuery, assembles them into a single keyed JSON bundle, and uploads to Cloudflare R2 for public distribution. A last step builds the single latest Parquet set from the published bundle with [gkm-bundle-parquet](https://github.com/clingen-data-model/gkm-bundle-parquet).

The `gkm_dict_*` tables **are** the published product — they are built directly by the statement procedures (steps 5–7) and the change-log step (step 8). The retired `gkm_json_proc` is not part of this path; its inlined JSON-render tables were never published. See [Retired: gkm_json_proc](#retired-gkm_json_proc).

Distribution follows a **full + delta** model:

- A **weekly full bundle** (JSON) is published for every release via `release-gkm.sh --weekly` / `upload-gkm-to-r2.sh --weekly`, into `weekly/`.
- The **official monthly full bundle** (JSON) is published once a month. `run-release.sh` normally makes it a server-side copy of its source release's weekly full (`upload-gkm-to-r2.sh --month-label=YYYY-MM --from-weekly`), and re-exports it with `release-gkm.sh --month-label=YYYY-MM` when that weekly full is gone.
- A **weekly delta** — added and updated records plus a change manifest — is published for every release via `release-gkm-delta.sh` / `upload-gkm-delta-to-r2.sh`.
- The **latest Parquet** — one table per bundle section — is built from every release's published weekly full by [gkm-bundle-parquet](https://github.com/clingen-data-model/gkm-bundle-parquet) via `release-gkm-parquet.sh` / `upload-gkm-parquet-to-r2.sh`. It is not kept per release. BigQuery exports no Parquet.
- Every bundle gets a `<file>.sha256` sidecar.

---

## Workflow

The export and distribution process has five steps. `release-gkm.sh` runs Steps 1–3 for a full bundle, `release-gkm-delta.sh` runs Step 4, and `release-gkm-parquet.sh` runs Step 5. `run-release.sh` calls all three for every release (Steps 1–4 are its stage 5, Step 5 its stage 6). Each step can also be run on its own.

### Step 1: Export Dictionaries to GCS

`export-gkm-dicts.sh` exports the dictionary and statement tables from BigQuery to Google Cloud Storage as sharded, gzip-compressed NDJSON for bundle assembly (`gkm-dicts/`). Most tables use `bq extract`; `variation`, `conditionSet`, `evidenceLine`, `scv` and the proposition sections use `EXPORT DATA` queries, which filter rows, keep `INT64` values numeric, or collapse the typed extension values to `value`. BigQuery exports no Parquet: the Parquet set is built from the published bundle (Step 5).

```bash
./src/scripts/export-gkm-dicts.sh <dataset> <gcs_bucket> [prefix] [--delta]
```

```bash
# What release-gkm.sh runs
./src/scripts/export-gkm-dicts.sh clinvar_2026_10_18_v2_6_0 clinvar-gkm gkm-dicts
```

`--delta` reads the `delta_gkm_dict_*` tables instead (what `release-gkm-delta.sh` runs).

The three proposition tables are exported as the four proposition sections. `clinvar_ingest.gkm_proposition_section(type)` names each row's section, and the export first asserts that every proposition maps to one of them, so an unmapped type fails the export instead of dropping rows. The script writes these 22 outputs:

| Source table | NDJSON output |
| --- | --- |
| `gkm_dict_sequence_reference` | `sequenceReference-*.ndjson.gz` |
| `gkm_dict_location` | `location-*.ndjson.gz` |
| `gkm_dict_allele` | `allele-*.ndjson.gz` |
| `gkm_dict_copy_number_count` | `copyNumberCount-*.ndjson.gz` |
| `gkm_dict_copy_number_change` | `copyNumberChange-*.ndjson.gz` |
| `gkm_dict_gene` | `gene-*.ndjson.gz` |
| `gkm_dict_variation` | `variation-*.ndjson.gz` |
| `gkm_dict_condition` | `condition-*.ndjson.gz` |
| `gkm_dict_condition_set` | `conditionSet-*.ndjson.gz` (sets with 2 or more members) |
| `gkm_dict_therapy` | `therapy-*.ndjson.gz` |
| `gkm_dict_therapygroup` | `therapyGroup-*.ndjson.gz` |
| `gkm_dict_submitter` | `submitter-*.ndjson.gz` |
| `gkm_dict_evidence_line` | `evidenceLine-*.ndjson.gz` |
| `gkm_dict_proposition`, `gkm_dict_vcv_proposition`, `gkm_dict_rcv_proposition` | `propositionPathogenicity-*`, `propositionOncogenicity-*`, `propositionSomaticClinicalImpact-*`, `propositionClinvarCustom-*.ndjson.gz` |
| `gkm_dict_vcv_evidence_line` | `vcv_evidenceLine-*.ndjson.gz` |
| `gkm_dict_rcv_evidence_line` | `rcv_evidenceLine-*.ndjson.gz` |
| `gkm_dict_scv` | `scv-*.ndjson.gz` |
| `gkm_dict_vcv` | `vcv-*.ndjson.gz` |
| `gkm_dict_rcv` | `rcv-*.ndjson.gz` |

BigQuery shards large tables across multiple files automatically.

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

#### Record Text

Every record — in a full bundle and in a delta — passes through the same cleanup and serialization in the
assembler, so an unchanged record has the same bytes in every release:

- **Cleanup** — null and empty fields are dropped, and typed extension values (`value_<type>`) collapse to `value`
- **Canonical lists** — the arrays whose order carries no meaning and has been seen to change between releases are
  sorted by each element's compact, key-sorted JSON text; today that is `condition` `aliases` (the trait's
  alternate names). The list is `UNORDERED_ARRAYS` in `gkm_json_cleanup.py`, and an array enters it only when
  every schema marks it `ordered: false`. All other arrays keep the pipeline's order
- **Text** — each record is one line of compact JSON (no insignificant whitespace, raw UTF-8) with its object keys
  **sorted at every depth**, independent of the column order of the BigQuery tables
- **Layout** — `schema_version` is the first top-level key, followed by the sections in the fixed order above

`orjson` writes this text, so the assembler requires it and stops without it:

```bash
pip install orjson
```

`release-gkm.sh` then validates every record of the assembled full bundle with `validate-bundle.sh --engine rs` and stops before upload if any fails (see [Strict validation stops the release](#step-4-publish-the-weekly-delta)).

### Step 3: Upload the Weekly and Monthly Fulls to R2

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

The R2 layout mirrors NCBI's ClinVar XML folder (ADR 0009). Under the line folder `v1/1.2/`:

- **top level** — official monthly fulls for the current year (`clinvar-gkm_yyyy-mm.json.gz`) plus a stable `clinvar-gkm_00-latest.json.gz`, each with a `.sha256` sidecar
- **`weekly/`** — a weekly full bundle for every release of the current month (`clinvar-gkm_yyyy-mmdd.json.gz`) plus a stable `clinvar-gkm_00-latest_weekly.json.gz`
- **`archive/{yyyy}/`** — monthly fulls from prior years, and their deltas under `archive/{yyyy}/deltas/{yyyy-mm}/`

Rollovers are done by `r2-rollover.sh <release_date>`, which `run-release.sh` runs before the weekly uploads and again after any monthly is published; it is idempotent, so a run with nothing to move does nothing. **New month** (the first release dated in a new month): the finished month's deltas move into `deltas/{yyyy-mm}/` and its weekly fulls are deleted, except the newest, which is kept until the new month's official monthly is published (the monthly's source candidate) and deleted by the run that publishes it. **New year:** the finished year's monthlies and delta folders move into `archive/{yyyy}/`. Each move or delete is followed by a CDN purge of the old paths. After upload, `generate-r2-index.sh` regenerates the line's `index.json`, which lists the monthlies (with their sha256 and `source_release`, the release each was built from), the weekly fulls, the deltas wherever they now sit, the `archive` years and the Parquet dataset.

### Step 4: Publish the Weekly Delta

`release-gkm-delta.sh` publishes the per-release delta for every ClinVar release. It exports the `delta_<dict>` change tables produced by step 8 of the pipeline, assembles a delta bundle (added + updated records, same section structure as the full), builds the delta manifest, and uploads them to R2. Deltas carry no Parquet.

```bash
./src/scripts/release-gkm-delta.sh <export_date> <dataset_version> [--start-step=N] [--dry-run]
```

```bash
# Publish the weekly delta for a release
./src/scripts/release-gkm-delta.sh 2026-07-06 v2_5_0
```

The internal steps are: export delta tables to GCS, assemble and strictly validate the delta bundle, then build the manifest (`build-delta-manifest.py`) and upload (`upload-gkm-delta-to-r2.sh`).

!!! warning "Strict validation stops the release"
    Every delta record is validated with the GA4GH [GKM Toolkit](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/) by `validate-bundle.sh` before upload. `run-release.sh` does this at the start of stage 5, so a failing delta stops the release with R2 untouched; the bundle stays in `STAGE_DIR` for inspection. The check needs [`uv`](https://docs.astral.sh/uv/) and the `va-spec` submodule (`git submodule update --init --recursive`), and `run-release.sh` confirms both at startup.

    `--start-step=3` publishes the staged bundle without validating it again, so only use it on a bundle that passed.

    Every full bundle is validated too: `release-gkm.sh` validates each full it assembles, the weekly full and any re-exported monthly, before upload, and `run-release.sh` builds the weekly full with the delta, so a failing full also stops the release with R2 untouched. The GKM Toolkit takes hours on a full, so fulls are validated with [jsonschema-rs](https://github.com/Stranger6667/jsonschema) instead (`validate-bundle.sh --engine rs`): the same bundle schema, the same `schema/` registry and the same document for each record, in minutes. jsonschema-rs is not the GKM Toolkit. Its verdicts are tested against the toolkit's: both engines must name the same failing records in a bundle with planted violations (`src/scripts/tests/test_validate_bundle_rs.py`). It reads only the one-record-per-line layout the assembler writes and stops on any other. Run `./src/scripts/validate-bundle.sh <bundle.json.gz>` (the toolkit, the default) on a full by hand when the official validator's verdict is needed, as for a version release.

The uploader writes:

- **`deltas/`** — the delta bundle (`clinvar-gkm-delta_<yyyy-mmdd>.json.gz`), its `.sha256` sidecar, and its manifest (`clinvar-gkm-delta_<yyyy-mmdd>.manifest.json`); the current month's deltas sit here, earlier months in `deltas/<yyyy-mm>/`

`build-delta-manifest.py` derives each section's `added` / `updated` counts and `deleted` primary-key list from the dataset's `gkm_change_log`, and records `baseline_release`, `compare_release`, `pipeline_version`, and `counts`. The uploader then completes the manifest: `checkpoint_full` (`{path, release, month, sha256}`, the newest official monthly whose `source_release` is on or before the delta's `baseline_release`, with `release` set to that `source_release`) so a consumer knows which monthly the delta chain replays onto, plus `schema_version`, `bundle` (`{name, path, size, sha256}`) and `sha256`. It also checks the chain: a delta whose `baseline_release` is not the release of the newest delta already in the line is refused (`--allow-gap` overrides). Monthlies are therefore published before the deltas that follow them. See [Weekly Deltas](../data-access/weekly-deltas.md) for the manifest shape and the consumer replay model.

### Step 5: Build and Publish the Latest Parquet

One Parquet set is published per version line, at `v1/1.2/parquet/`, and overwritten every release (ADR 0009). It is
built from the **published weekly full** of the newest release by
[gkm-bundle-parquet](https://github.com/clingen-data-model/gkm-bundle-parquet), a separate, independently versioned
tool for any GKM bundle, installed from [PyPI](https://pypi.org/project/gkm-bundle-parquet/2.0.0/) and pinned to
**2.0.0**. BigQuery exports no Parquet: every table and value is derived from the bundle, so the bundle stays the
record and the Parquet set is a convenience that can be regenerated from it.

`run-release.sh` runs this step as its stage 6, after stage 5 has uploaded the weekly full; `--skip-parquet` skips it
and leaves the previous set in place. It can also be run on its own for a release that is already published:

```bash
./src/scripts/release-gkm-parquet.sh <export_date> <dataset_version> [--start-step=N] [--dry-run] [--no-upload] [--purge]
```

#### What It Builds

The tables are the tool's **default column set, generated from the bundle schema**: no column set is kept in this
repo. For the bundle schema of the assembler's `SCHEMA_VERSION`
(`https://w3id.org/clingen/schema/clinvar-gkm/<SCHEMA_VERSION>/clinvar-gkm-bundle.schema.json`), the tool makes one
table per bundle section (20 tables) and one column for every property the section's record schema allows, read the
way the schema says: `#/<section>/<id>` pointers become ids and declared foreign keys, nested objects become
`STRUCT`s, and lists become lists of `STRUCT`s. See the tool's
[generate](https://github.com/clingen-data-model/gkm-bundle-parquet/blob/main/docs/generate.md) page for the rules.
A schema change in this repo therefore changes the tables with no Parquet-specific work. The table and column
reference is in [Parquet Tables](../parquet/tables.md).

#### How It Runs

1. **Find the bundle.** The input is `<line>weekly/clinvar-gkm_<yyyy-mmdd>.json.gz` at its public URL, with the
   sha256 from its published `.sha256` sidecar. A release with no weekly full — the release that starts a new
   version line with `run-release.sh --bootstrap-monthly` publishes only its checkpoint monthly — is read from the
   monthly that the line's `index.json` lists with this release as its `source_release` (never `00-latest`), with the
   sha256 the index gives. With neither, the step stops.
2. **`gkm-bundle-parquet build`** streams the bundle from that URL, checks its sha256, and writes the tables:

    ```bash
    uvx gkm-bundle-parquet@2.0.0 build --full <bundle URL> --sha256 <sha256> \
      --bundle-schema https://w3id.org/clingen/schema/clinvar-gkm/<SCHEMA_VERSION>/clinvar-gkm-bundle.schema.json \
      --version-property schema_version --out <dir> --work-dir <dir>.work
    ```

    The build rebuilds every record from the tables and compares it with its source, and records a records sha256 of
    the bundle in its `manifest.json`.
3. **`gkm-bundle-parquet verify --bundle-recompute`** reads the bundle again and checks every table's id sets and
   values against it.
4. **`gkm-bundle-parquet verify --roundtrip`** rebuilds the bundle's records from the tables and checks them against
   the records sha256: the set is **record-identical** to the bundle (every record by key, JSON-equal; key order,
   array order and whitespace don't count). See the tool's
   [round trip](https://github.com/clingen-data-model/gkm-bundle-parquet/blob/main/docs/round-trip.md) page.
5. **Upload** (`upload-gkm-parquet-to-r2.sh`) overwrites each table and `table-spec.json` in `parquet/`, then writes
   `parquet/manifest.json`: the tool's manifest (tool version, table spec version, the source bundle and its sha256,
   the records sha256, the files) plus what only this repo knows (`source_release`, `dataset`, `build_date`, the
   ClinVar attribution, disclaimer and license). It refuses a manifest another builder wrote, a release or schema
   version that differs from this release's, and files that differ from the ones the tool wrote. It then deletes any
   file in `parquet/` that is no longer produced, regenerates `index.json`, and with `--purge` (which `run-release.sh`
   passes) purges the folder from the CDN.

A failure in steps 1–4 stops before anything on R2 changes. After stage 5, a failure is non-fatal to the release:
`parquet/` keeps the previous set, and its manifest and the index keep saying which release it was built from.

#### Options and Resources

- **`--no-upload`** stops after the verify steps and keeps the build in `STAGE_DIR` (default `/tmp`) for inspection;
  `--start-step=3` publishes it later. **`--dry-run`** prints the commands and uploads nothing.
- **`PARQUET_TOOL_CMD`** replaces the pinned tool command, e.g. to test an unpublished checkout:
  `PARQUET_TOOL_CMD="uvx --from /path/to/gkm-bundle-parquet gkm-bundle-parquet"`. The pin is bumped deliberately,
  because the output depends on the tool version.
- **`PARQUET_MEMORY_LIMIT`** sets DuckDB's memory limit (e.g. `32GB`); the tool's default is half the machine's
  memory. A lower limit spills more to the work directory.
- **Disk and memory:** leave about 25 GB free in `STAGE_DIR` for the set and DuckDB's spill files. The full-size check
  of 2.0.0 on a weekly full took 38 minutes and used about 65 GB of memory on a 128 GB machine.

To check a bundle against its schema with the same tool, see its
[validate](https://github.com/clingen-data-model/gkm-bundle-parquet/blob/main/docs/validate.md) page.

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
- **Python 3** — for the assembly script, with `orjson` (required: it writes the bundle text)
- **[uv](https://docs.astral.sh/uv/)** — `uvx` runs the pinned [`gkm-bundle-parquet` 2.0.0](https://pypi.org/project/gkm-bundle-parquet/2.0.0/) for the Parquet set (Step 5)
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

The export and assembly can also be run individually; use `--start-step` to resume `release-gkm.sh` from a specific step (1 export, 2 assemble, 3 upload). Build the latest Parquet from the published weekly full with `./src/scripts/release-gkm-parquet.sh 2026-06-14 v2_5_0` (Step 5).

```bash
# 1. Export dictionary tables to GCS (bundle NDJSON)
./src/scripts/export-gkm-dicts.sh clinvar_2026_06_14_v2_5_0 clinvar-gkm gkm-dicts

# 2. Assemble NDJSON into a single JSON bundle
python3 ./src/scripts/assemble-gkm-dicts.py \
  gs://clinvar-gkm/gkm-dicts/ \
  2026-06-14

# 3. Upload to R2
./src/scripts/release-gkm.sh 2026-06-14 v2_5_0 --start-step=3
```
