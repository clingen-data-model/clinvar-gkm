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

## Prerequisites

The commands on this page are maintainer commands. They run from the root of a clone of this repository, use the
project's Google Cloud resources, and publish to the public R2 bucket. The [Pipeline Overview](index.md) and
[VRS Processing](vrs-processing.md) pages need the same setup.

!!! warning "Billed, and published to the live line"
    - **BigQuery bills the export.** The `EXPORT DATA` queries of Step 1 scan about 55–60 GB per full export
      (`bq extract` is not billed). The procedures that build the `gkm_dict_*` tables bill about 0.2 TiB per full
      build ([Pipeline Overview](index.md)).
    - **GCS.** Steps 1 and 2 write NDJSON to `gs://clinvar-gkm/`, and the assembler deletes the prefix it read
      (unless `--keep-source`). `gkm-dicts/` and `gkm-deltas/` are the release scripts' staging prefixes; a hand
      run uses a prefix of its own.
    - **R2.** Steps 3–5 write to the **live** version line (`R2_LINE`, default `v1/1.2/`) and regenerate its
      `index.json`, which every reader sees. `--dry-run` prints the writes instead, and `--no-upload` stops before R2.

- **Repository** — a clone with its submodules (`git submodule update --init --recursive`); validation reads the
  schemas of the `va-spec` submodule. Run every command from the repository root.
- **Google Cloud SDK** — `bq`, `gsutil` and `gcloud`, signed in with `gcloud auth login`, with the default project
  set: `gcloud config set project clingen-dev`. `export-gkm-dicts.sh` names its tables without a project, so it runs
  in gcloud's default project; `run-release.sh` and `check-cloud-vrsify.sh` read `PROJECT_ID` (default
  `clingen-dev`). The scripts call only these CLIs, so Application Default Credentials are not needed.
- **Google Cloud access** in `clingen-dev` — to run queries and procedures and write tables (for example the
  BigQuery Job User and BigQuery Data Editor roles), to write and delete objects in `gs://clinvar-gkm` (Storage
  Object Admin), and, for the VRS transform, to execute Cloud Run jobs.
- **AWS CLI with an `r2` profile** — an R2 API token with Object Read & Write on the `clinvar-gkm` bucket, stored
  with `aws configure --profile r2` (the token's access key ID and secret, region `auto`). The scripts add the R2
  endpoint themselves. `--dry-run` lists the bucket too, so it also needs the profile.
- **Cloudflare purge credentials** — `CF_ZONE_ID` and `CF_PURGE_TOKEN`, in the environment or in
  `~/.config/clinvar-gkm/cloudflare.env` (`CF_ENV_FILE` sets another path). `--purge` and the month rollover use
  them to clear the CDN copy of overwritten, moved or deleted files. Without them the purge is skipped with a
  warning, and the CDN can serve the old copy until it expires.
- **Python 3.12 with `orjson`** — the release scripts use `venv/3.12/bin/python3` when it exists, and `python3`
  otherwise. `orjson` is required (Step 2) and is in the project requirements. `make venv/3.12` creates the environment (it
  needs `python3.12` on the `PATH`); then install the requirements into it:

    ```bash
    make venv/3.12
    venv/3.12/bin/pip install -r .requirements.txt
    ```

- **[uv](https://docs.astral.sh/uv/)** — `validate-bundle.sh` builds its validation environment with uv, and `uvx`
  runs the pinned [`gkm-bundle-parquet` 2.0.0](https://pypi.org/project/gkm-bundle-parquet/2.0.0/) (Step 5).
  `./src/scripts/validate-bundle.sh --check-setup --engine rs` confirms that uv, the environment and the schema
  tree are ready.
- **`curl` and `shasum`** — installed on macOS; on Linux, `shasum` comes with Perl.
- **Environment variables** (all optional):
    - `R2_LINE` — the version line written (default `v1/1.2/`)
    - `STAGE_DIR` — where bundles and the Parquet build are staged (default `/tmp`); a full bundle is about 5 GB,
      and the Parquet build needs about 25 GB free
    - `PROJECT_ID` — the GCP project of `run-release.sh` and `check-cloud-vrsify.sh` (default `clingen-dev`)
    - `GKS_FULL`, `INCREMENTAL` — `vrs-to-bq-table.sh` only; see
      [VRS Processing](vrs-processing.md#step-4-transform-load-run-procedures)
    - `PARQUET_TOOL_CMD`, `PARQUET_MEMORY_LIMIT` — Step 5; see [Options and Resources](#options-and-resources)

---

## Workflow

The export and distribution process has five steps. `release-gkm.sh` runs Steps 1–3 for a full bundle, `release-gkm-delta.sh` runs Step 4, and `release-gkm-parquet.sh` runs Step 5. `run-release.sh` calls all three for every release (Steps 1–4 are its step 3, Step 5 its step 4). Each step can also be run on its own.

### Step 1: Export Dictionaries to GCS

`export-gkm-dicts.sh` exports the dictionary and statement tables from BigQuery to Google Cloud Storage as sharded, gzip-compressed NDJSON for bundle assembly (`gkm-dicts/`). Most tables use `bq extract`; `variation`, `conditionSet`, `evidenceLine`, `scv` and the proposition sections use `EXPORT DATA` queries, which filter rows, keep `INT64` values numeric, or collapse the typed extension values to `value`. BigQuery exports no Parquet: the Parquet set is built from the published bundle (Step 5).

```text
./src/scripts/export-gkm-dicts.sh <dataset> <gcs_bucket> [prefix] [--delta]
```

`release-gkm.sh` clears `gs://clinvar-gkm/gkm-dicts/` and then runs the script on the release's dataset,
`clinvar_<yyyy>_<mm>_<dd>_<version>`. The script itself doesn't clear its prefix, so shards an earlier run left
there would be assembled too. By hand, export to a prefix of your own and clear it first (the `EXPORT DATA` queries
are billed, about 55–60 GB scanned):

```text
gsutil -m rm -r gs://clinvar-gkm/gkm-dicts-<user>/ 2>/dev/null || true
./src/scripts/export-gkm-dicts.sh clinvar_<yyyy>_<mm>_<dd>_<version> clinvar-gkm gkm-dicts-<user>
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

```text
venv/3.12/bin/python3 ./src/scripts/assemble-gkm-dicts.py <source> <date> [--keep-source] [--copy-to-gcs] [--output PATH]
```

`<source>` is a local path or `gs://` URI containing the NDJSON shards. `<date>` is the ClinVar release date (`YYYY-MM-DD`); the output path is `/tmp/clinvar-gkm-{date}.json.gz` unless `--output` names another. By default, source files are deleted after assembly; use `--keep-source` to retain them.

Continuing from the export above, assemble the bundle, then validate it strictly as `release-gkm.sh` does:

```text
venv/3.12/bin/python3 ./src/scripts/assemble-gkm-dicts.py gs://clinvar-gkm/gkm-dicts-<user>/ <yyyy-mm-dd>
./src/scripts/validate-bundle.sh /tmp/clinvar-gkm-<yyyy-mm-dd>.json.gz --engine rs
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

`orjson` writes this text, so the assembler requires it and stops without it. Install it in the environment the
release scripts use (see [Prerequisites](#prerequisites)):

```bash
venv/3.12/bin/pip install orjson
```

`release-gkm.sh` then validates every record of the assembled full bundle with `validate-bundle.sh --engine rs` and stops before upload if any fails (see [Strict validation stops the release](#step-4-publish-the-weekly-delta)).

### Step 3: Upload the Weekly and Monthly Fulls to R2

`upload-gkm-to-r2.sh` uploads a full bundle and its `.sha256` sidecar to Cloudflare R2, as one of two kinds:

- **`--weekly`** — the weekly full of `<export_date>`, written to `weekly/clinvar-gkm_yyyy-mmdd.json.gz`; when it is the newest weekly full it is also copied to `weekly/clinvar-gkm_00-latest_weekly.json.gz`. A weekly full older than the line's current month is refused.
- **`--month-label=YYYY-MM`** — the official monthly, published **once a month, aligned to ClinVar's own monthly VCV releases**: when a new `ClinVarVCVRelease_YYYY-MM.xml.gz` appears at ClinVar's [XML index](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/), `run-release.sh` publishes our `clinvar-gkm_YYYY-MM` full from the most recent weekly release **before** ClinVar's monthly cut datetime (ADR 0002). `<export_date>` is that source release, so the month slot is set independently of it (e.g. the `2026-07` full is built from our `2026-06-27` release, the last one before ClinVar's `_2026-07` cut). With `--from-weekly` the monthly is a server-side copy of `weekly/clinvar-gkm_<export_date>.json.gz` and no local bundle is needed (pass `-`). When it is the newest monthly it is also copied to `clinvar-gkm_00-latest.json.gz`, and the index records `<export_date>` as the monthly's `source_release`.

```text
./src/scripts/upload-gkm-to-r2.sh <export_date> <dataset_version> <bundle_file|-> \
  [--weekly | --month-label=YYYY-MM [--from-weekly]] [--dry-run] [--purge]
```

```text
# A release's weekly full (+ sha256 sidecar); the release must be in the line's current month
./src/scripts/upload-gkm-to-r2.sh <yyyy-mm-dd> <version> /tmp/clinvar-gkm-<yyyy-mm-dd>.json.gz --weekly

# The <yyyy-mm> official monthly, as a server-side copy of the weekly full of its ADR 0002 source release
./src/scripts/upload-gkm-to-r2.sh <source-release> <version> - --month-label=<yyyy-mm> --from-weekly

# Preview: lists the bucket and prints the writes, uploading nothing
./src/scripts/upload-gkm-to-r2.sh <yyyy-mm-dd> <version> /tmp/clinvar-gkm-<yyyy-mm-dd>.json.gz --weekly --dry-run
```

!!! warning "Writes to the live line"
    Without `--dry-run`, these commands write to the public line (`R2_LINE`) and regenerate its `index.json`. The
    guards also apply to `--dry-run`: a weekly full dated before the line's current month is refused, and
    `--from-weekly` stops when the source release's weekly full is no longer in R2 (re-export it with
    `release-gkm.sh <source-release> <version> --month-label=<yyyy-mm>` instead). Pass `--weekly` or
    `--month-label`: without either, the script publishes the bundle as the monthly of `<export_date>`'s own month,
    which is not the ADR 0002 mapping.

The R2 layout mirrors NCBI's ClinVar XML folder (ADR 0009). Under the line folder `v1/1.2/`:

- **top level** — official monthly fulls for the current year (`clinvar-gkm_yyyy-mm.json.gz`) plus a stable `clinvar-gkm_00-latest.json.gz`, each with a `.sha256` sidecar
- **`weekly/`** — a weekly full bundle for every release of the current month (`clinvar-gkm_yyyy-mmdd.json.gz`) plus a stable `clinvar-gkm_00-latest_weekly.json.gz`
- **`archive/{yyyy}/`** — monthly fulls from prior years, and their deltas under `archive/{yyyy}/deltas/{yyyy-mm}/`

Rollovers are done by `r2-rollover.sh <release_date>`, which `run-release.sh` runs before the weekly uploads and again after any monthly is published; it is idempotent, so a run with nothing to move does nothing. **New month** (the first release dated in a new month): the finished month's deltas move into `deltas/{yyyy-mm}/` and its weekly fulls are deleted, except the newest, which is kept until the new month's official monthly is published (the monthly's source candidate) and deleted by the run that publishes it. **New year:** the finished year's monthlies and delta folders move into `archive/{yyyy}/`. Each move or delete is followed by a CDN purge of the old paths. After upload, `generate-r2-index.sh` regenerates the line's `index.json`, which lists the monthlies (with their sha256 and `source_release`, the release each was built from), the weekly fulls, the deltas wherever they now sit, the `archive` years and the Parquet dataset.

### Step 4: Publish the Weekly Delta

`release-gkm-delta.sh` publishes the per-release delta for every ClinVar release. It exports the `delta_<dict>` change tables produced by step 8 of the pipeline, assembles a delta bundle (added + updated records, same section structure as the full), builds the delta manifest, and uploads them to R2. Deltas carry no Parquet.

```text
./src/scripts/release-gkm-delta.sh <export_date> <dataset_version> [--start-step=N] [--dry-run] [--no-upload]
```

```text
# Build and strictly validate a release's delta, keeping it in STAGE_DIR; nothing is written to R2
./src/scripts/release-gkm-delta.sh <yyyy-mm-dd> <version> --no-upload

# Publish it to deltas/ in the live line
./src/scripts/release-gkm-delta.sh <yyyy-mm-dd> <version> --start-step=3
```

The upload is refused unless the delta follows the newest delta already in the line (the chain check below), so a
delta is published for each release in order.

The internal steps are: export delta tables to GCS, assemble and strictly validate the delta bundle, then build the manifest (`build-delta-manifest.py`) and upload (`upload-gkm-delta-to-r2.sh`).

!!! warning "Strict validation stops the release"
    Every delta record is validated with [jsonschema-rs](https://pypi.org/project/jsonschema-rs/) by `validate-bundle.sh --engine rs` before upload, as every full is (see [Release Validation](../reference/release-validation.md)). `run-release.sh` does this at the start of stage 5, so a failing delta stops the release with R2 untouched; the bundle stays in `STAGE_DIR` for inspection. The check needs [`uv`](https://docs.astral.sh/uv/) and the `va-spec` submodule (`git submodule update --init --recursive`), and `run-release.sh` confirms both at startup.

    `--start-step=3` publishes the staged bundle without validating it again, so only use it on a bundle that passed.

    Every full bundle is validated too: `release-gkm.sh` validates each full it assembles, the weekly full and any re-exported monthly, before upload, and `run-release.sh` builds the weekly full with the delta, so a failing full also stops the release with R2 untouched. The GKM Toolkit takes hours on a full, so fulls are validated with [jsonschema-rs](https://github.com/Stranger6667/jsonschema) instead (`validate-bundle.sh --engine rs`): the same bundle schema, the same `schema/` registry and the same document for each record, in minutes. jsonschema-rs is not the GKM Toolkit. Its verdicts are tested against the toolkit's: both engines must name the same failing records in a bundle with planted violations (`src/scripts/tests/test_validate_bundle_rs.py`). It reads only the one-record-per-line layout the assembler writes and stops on any other. Run `./src/scripts/validate-bundle.sh <bundle.json.gz> --engine toolkit` on a full by hand when the official validator's verdict is needed, as for a version release; without `--engine`, the script uses jsonschema-rs.

The uploader writes:

- **`deltas/`** — the delta bundle (`clinvar-gkm-delta_<yyyy-mmdd>.json.gz`), its `.sha256` sidecar, and its manifest (`clinvar-gkm-delta_<yyyy-mmdd>.manifest.json`); the current month's deltas sit here, earlier months in `deltas/<yyyy-mm>/`

`build-delta-manifest.py` derives each section's `added` / `updated` counts and `deleted` primary-key list from the dataset's `gkm_change_log`, and records `baseline_release`, `compare_release`, `pipeline_version`, and `counts`. The uploader then completes the manifest: `checkpoint_full` (`{path, release, month, sha256}`, the newest official monthly whose `source_release` is on or before the delta's `baseline_release`, with `release` set to that `source_release`) so a consumer knows which monthly the delta chain replays onto, plus `schema_version`, `bundle` (`{name, path, size, sha256}`) and `sha256`. It also checks the chain: a delta whose `baseline_release` is not the release of the newest delta already in the line is refused (`--allow-gap` overrides). Monthlies are therefore published before the deltas that follow them. See [Weekly Deltas](../data-access/weekly-deltas.md) for the manifest shape and the consumer replay model.

### Step 5: Build and Publish the Latest Parquet

One Parquet set is published per version line, at `v1/1.2/parquet/`, and overwritten every release (ADR 0009). It is
built from the **published weekly full** of the newest release by
[gkm-bundle-parquet](https://github.com/clingen-data-model/gkm-bundle-parquet), a separate, independently versioned
tool for any GKM bundle, installed from [PyPI](https://pypi.org/project/gkm-bundle-parquet/2.0.0/) and pinned to
**2.0.0**. BigQuery exports no Parquet: every table and value is derived from the bundle, so the bundle stays the
record and the Parquet set is a convenience that can be regenerated from it. To build the same tables yourself, or
cut a mini-bundle from a full bundle, see [Build Your Own Tables and Mini-Bundles](../parquet/build-your-own.md).

`run-release.sh` runs this step as its step 4, after its step 3 has uploaded the weekly full; `--skip-parquet` skips it
and leaves the previous set in place. It can also be run on its own for a release that is already published:

```text
./src/scripts/release-gkm-parquet.sh <export_date> <dataset_version> [--start-step=N] [--dry-run] [--no-upload] [--purge]
```

Without `--no-upload` or `--dry-run`, it overwrites `parquet/` in the live line.

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

    ```text
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

A failure in steps 1–4 stops before anything on R2 changes. After `run-release.sh` step 3, a failure is non-fatal to the release:
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

The policy is checked in at [`src/scripts/r2-cors.json`](https://github.com/clingen-data-model/clinvar-gkm/blob/main/src/scripts/r2-cors.json) (`GET`/`HEAD` from `*` — appropriate for public, read-only data). It is **not** applied by the release scripts, because their object-scoped `r2` upload token cannot read or write bucket configuration (`PutBucketCors` → `AccessDenied`). Apply it once with an **Admin Read & Write** R2 token (Cloudflare dashboard: **R2 → Manage R2 API Tokens**), stored as an AWS profile with `aws configure --profile r2admin` (region `auto`). The script writes the live bucket's configuration:

```bash
./src/scripts/apply-r2-cors.sh            # profile r2admin; another profile: ./src/scripts/apply-r2-cors.sh PROFILE
```

Or paste `r2-cors.json`'s rules into the Cloudflare dashboard: **R2 → clinvar-gkm → Settings → CORS Policy**. It only needs to be re-applied if the bucket is recreated or the policy is cleared.

---

## Retired: gkm_json_proc

`gkm_json_proc` previously rendered the statement and dictionary tables into inlined JSON columns. Those render tables were **never published** — the export assembles the bundle directly from the `gkm_dict_*` tables — so the procedure has been retired from the hot path. The null/empty stripping it used to perform is now applied during assembly (`assemble-gkm-dicts.py`), matching the old `remove_empty` cleanup. `gkm_json_proc` is not a live pipeline step and not a downstream consumer of the dictionary tables.

---

## Full Example

The weekly publish of one release by hand, in the order `run-release.sh` runs it (its steps 3 and 4; see
[Single-command run](index.md#single-command-run)). `run-release.sh` also publishes any monthly that is due, so
prefer it for a real release. `<yyyy-mm-dd>` is a release in the line's current month whose dataset,
`clinvar_<yyyy>_<mm>_<dd>_<version>`, is built, and whose delta follows the newest delta in the line.

!!! warning "Billed, and published to the live line"
    The `--no-upload` commands bill BigQuery for their exports. Every later command writes to the public line
    (`R2_LINE`) and regenerates its `index.json`. Add `--dry-run` to any of them to print the writes instead. See
    [Prerequisites](#prerequisites) for the access each needs.

```text
# Build and strictly validate the delta and the weekly full; nothing is written to R2
./src/scripts/release-gkm-delta.sh <yyyy-mm-dd> <version> --no-upload
./src/scripts/release-gkm.sh <yyyy-mm-dd> <version> --weekly --no-upload

# Month or year rollover of the line (does nothing when none is due), then publish the weekly full and the delta
./src/scripts/r2-rollover.sh <yyyy-mm-dd>
./src/scripts/release-gkm.sh <yyyy-mm-dd> <version> --weekly --start-step=3
./src/scripts/release-gkm-delta.sh <yyyy-mm-dd> <version> --start-step=3

# Rebuild the latest Parquet from the weekly full just published
./src/scripts/release-gkm-parquet.sh <yyyy-mm-dd> <version> --purge
```

When ClinVar has published a new monthly XML since the line's newest monthly, `run-release.sh` publishes it after
the weekly full, from its ADR 0002 source release (see [Step 3](#step-3-upload-the-weekly-and-monthly-fulls-to-r2)),
and runs `r2-rollover.sh` again.

`release-gkm.sh` runs export, assembly and validation, and upload as steps 1, 2 and 3; `--start-step` resumes it
from one, and step 3 reads the bundle from `STAGE_DIR`. The same steps by hand (Steps 1–3 above):

```text
# 1. Export the dictionary tables to a GCS prefix of your own, cleared first
gsutil -m rm -r gs://clinvar-gkm/gkm-dicts-<user>/ 2>/dev/null || true
./src/scripts/export-gkm-dicts.sh clinvar_<yyyy>_<mm>_<dd>_<version> clinvar-gkm gkm-dicts-<user>

# 2. Assemble the NDJSON into one bundle (this deletes the shards), then validate it strictly
venv/3.12/bin/python3 ./src/scripts/assemble-gkm-dicts.py gs://clinvar-gkm/gkm-dicts-<user>/ <yyyy-mm-dd>
./src/scripts/validate-bundle.sh /tmp/clinvar-gkm-<yyyy-mm-dd>.json.gz --engine rs

# 3. Upload the validated bundle as the weekly full (writes to the live line)
./src/scripts/upload-gkm-to-r2.sh <yyyy-mm-dd> <version> /tmp/clinvar-gkm-<yyyy-mm-dd>.json.gz --weekly
```
