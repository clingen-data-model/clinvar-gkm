# VRS Processing

## Overview

VRS processing is the step between [Variation Identity](variation-identity/index.md) extraction and [Cat-VRS](cat-vrs/index.md) generation. It translates the selected SPDI or HGVS expression for each variation's defining allele into a GA4GH VRS (Variation Representation Specification) object — producing a computable, digest-identified representation of the variant.

The work is split between two repositories:

- **[clinvar-ingest](https://github.com/clingen-data-model/clinvar-ingest) (pipeline v2.7.0 and later)** exports each release's changed `variation_identity` rows to `gs://clinvar-gkm/YYYY-MM-DD/dev/vi.jsonl.gz`, and its Cloud Run job `clinvar-ingest-vrsify` translates them with [vrs-python](https://github.com/ga4gh/vrs-python) against a [RefgetStore](https://refgenie.org/refget/refgetstore-explained/) of genomic sequences, with no local services.
- **This project's release** (`run-release.sh`) starts after that: step 1 runs `src/scripts/check-cloud-vrsify.sh`, which checks that the translation belongs to the current export, and step 2 runs `src/scripts/vrs-to-bq-table.sh`, which transforms the translation, loads `gkm_vrs`, and runs the downstream procedures. Export and publish follow: `release-gkm.sh` (full bundles), `release-gkm-delta.sh` (deltas) and `release-gkm-parquet.sh` (the latest Parquet). See [Single-command run](index.md#single-command-run).

**This step is incremental.** VRS translation is per-variation (no cross-variation dependency), so diffing `variation_identity` between releases is a clean driver: the export holds only the variations whose `variation_identity` changed since the prior release (~0.3% of a weekly release, versus the whole ~4.5M snapshot), and the `gkm_vrs` load carries the prior release's results forward for the unchanged variations. This is where the largest cost reduction in the whole pipeline lands, because VRS translation is the most expensive stage.

The location transformation step uses a lightweight Cloud Run job defined in this project under `src/vrs-location-transformer/`.

---

## Workflow

### Step 1: Export `variation_identity` (clinvar-ingest)

clinvar-ingest's stored procedures job runs, for every release, `dataset_diff_on`, `variation_identity_incremental` and `variation_vrs_changed`, then exports only the changed variations' `variation_identity` rows to `gs://clinvar-gkm/YYYY-MM-DD/dev/vi.jsonl.gz`. When no usable baseline exists, every variation counts as changed and the export holds the whole table. The procedures it calls live in this repository's `src/procedures/`, but this project's release never runs them.

Each record contains the single best expression source for a ClinVar variation — including the `source` expression string, `fmt` (spdi, hgvs, or gnomad), `vrs_class`, and copy number fields when applicable.

`src/scripts/export-vi-table-to-gcs.sh` is not part of the release. It is kept because clinvar-ingest's error message, when its own export fails, tells the operator to rerun the export with it. Don't run it after the release has been translated: a rewrite with different content no longer matches the translation.

### Step 2: Translate with vrs-python (cloud vrsify)

The `clinvar-ingest-vrsify` Cloud Run job (project `clingen-dev`, region `us-east1`) runs every 15 minutes. It takes the next release whose upstream stored procedures have finished, waits for that release's `vi.jsonl.gz` to be written, and runs the translation on Cloud Batch. It takes each release once, and never replaces an existing output. It writes, beside the input:

- `vi-vrs-python.jsonl.gz` — one line per input record
- `vi-vrs-python.provenance.json` — the input it read (`inputs`: URI, generation, MD5 and size), the output, the RefgetStore, the library versions and record counts

For each input record, the translation attempts to resolve the `source` expression into a VRS object according to its `vrs_class`. Not every variation can be resolved: records that fail resolution carry an `errors` field in the output. Transcript and protein expressions are not translated (the translation uses only the RefgetStore, with no UTA), and records of classes it does not translate (`Unknown`, `Not Available`, `Haplotype`) get a null `out`. The supported VRS classes are:

- **Allele** — translates SPDI or HGVS into a VRS `Allele` with a `SequenceLocation` and `state`
- **CopyNumberChange** — resolves the location and applies the `copyChange` designation (gain/loss)
- **CopyNumberCount** — resolves the location and attaches the `copies` value

Each output record pairs the original `variation_identity` input (`in`) with the VRS resolution result (`out`).

**Output:** `vi-vrs-python.jsonl.gz` on GCS.

#### Checking the cloud output { #checking-the-cloud-output }

The release starts here. `run-release.sh` step 1 runs `src/scripts/check-cloud-vrsify.sh YYYY-MM-DD`; a release started with `--start-step 2` runs it too, so every `gkm_vrs` load is checked. The check reads the objects, runs nothing, and stops the release at once (it does not wait) unless:

- both `vi-vrs-python.jsonl.gz` and its provenance exist;
- the provenance names this release's `vi.jsonl.gz` as its only input, with the MD5 and size that object has now;
- the provenance names `vi-vrs-python.jsonl.gz` as its output, with its current size when the provenance records one.

A new generation of `vi.jsonl.gz` with the same MD5 passes: a re-export of unchanged `variation_identity` writes the same bytes. A `vi.jsonl.gz` with different content fails, and the cloud job does not redo the release by itself; translate the current export again upstream (`clinvar-ingest vrsify-submit` with `--overwrite`), then run the release again. If the output is not there yet, run the release again after the cloud job's next run.

### Step 3: Transform VRS locations

VRS `SequenceLocation` objects use array-valued `start` and `end` fields to represent imprecise ranges (inner/outer bounds). BigQuery does not natively support loading these mixed scalar/array values, so a minor transformation is needed before the data can be imported.

The `vrs-to-vi-location-transformer` Cloud Run job — defined in this project at `src/vrs-location-transformer/` — streams the VRS output through a `jq` filter that flattens each location's `start` and `end` arrays into separate scalar fields: `start`, `start_inner`, `start_outer`, `end`, `end_inner`, `end_outer`. When `start` or `end` is already a scalar (precise variants), the value is left unchanged.

This job is normally invoked by the `src/scripts/vrs-to-bq-table.sh` orchestrator (Step 4 below), not run by hand; the direct invocation is shown for reference. It executes a billed Cloud Run job in `clingen-dev` and overwrites `vi-final.jsonl.gz`, so it needs the right to execute Cloud Run jobs there and to write `gs://clinvar-gkm` (see [Export & Distribute: Prerequisites](export.md#prerequisites)):

```text
gcloud run jobs execute vrs-to-vi-location-transformer --project clingen-dev \
  --args "gs://clinvar-gkm/<yyyy-mm-dd>/dev/vi-vrs-python.jsonl.gz" \
  --args "gs://clinvar-gkm/<yyyy-mm-dd>/dev/vi-final.jsonl.gz" \
  --wait --region us-east1
```

**Output:** `vi-final.jsonl.gz` on GCS.

### Step 4: Transform, load, run procedures

The transform + load + downstream procedures are run by `src/scripts/vrs-to-bq-table.sh` (a 3-step script): the Cloud Run transform (Step 3 above), the `gkm_vrs` load, and the gkm_* stored procedures. Export and publish are **not** done here — they are handled separately by `release-gkm.sh` (see [Export & Distribute](export.md)); `run-release.sh` runs this script as its step 2 and then `release-gkm.sh`.

```text
GKS_FULL=true ./src/scripts/vrs-to-bq-table.sh <yyyy-mm-dd>     # from the start (Cloud Run transform), gkm procs full
GKS_FULL=true ./src/scripts/vrs-to-bq-table.sh <yyyy-mm-dd> 2   # resume from a later step (2=load, 3=procs)
```

!!! warning "Billed, and written to the live dataset"
    The script runs in `clingen-dev` (set in the script, not read from `PROJECT_ID`) and needs the setup in
    [Export & Distribute: Prerequisites](export.md#prerequisites). It executes the Cloud Run transform, replaces
    the release dataset's `gkm_vrs`, and runs the gkm procedures, which bill about 0.2 TiB per full build and replace
    that dataset's `gkm_*` tables. Run on its own, the script calls the **incremental** procedure wrappers unless
    `GKS_FULL=true` is set; `run-release.sh --full-procs` sets it. `INCREMENTAL=false` forces a full `--replace`
    load of `gkm_vrs`.

The `gkm_vrs` load is **incremental**: it clones the prior release's `gkm_vrs` forward and merges in only the changed variations' new results (keyed on `in.variation_id`), rather than a `--replace` full load. It **self-corrects to a full `--replace`** when no baseline `gkm_vrs` exists or when the staged rows are not the changed subset — so a translation of the whole table is loaded correctly without any flag change.

Because each release clones the immediately prior one, the clone lineage grows one level per release and reaches BigQuery's cap of **3 chained clones/snapshots** roughly every 3 releases. When the seed clone fails with that error, the load automatically falls back to a **deep copy** (`CREATE OR REPLACE TABLE … AS SELECT *`) of the baseline, which materializes a fresh depth-0 table and resets the chain — self-healing, with no manual intervention. You'll see `clone chain full; reseeding via deep copy` in the log on those releases; it is expected and does not change the result.

!!! warning "Version-invalidation"
    The incremental carry-forward assumes the prior release's `gkm_vrs` was produced by the **same** VRS translation and the **same** `variation_identity` transform. A `variation_identity` transform change is caught by the diff, once clinvar-ingest runs the changed procedure: every variation whose row changes is exported and translated again.

    A change to the translation (vrs-python, the RefgetStore, or the cloud job's code) is not. Each release's provenance file records its `libraries` and `refget_store`, but the release does not compare them between releases. Re-translating every variation is an upstream run; this project's release has no full mode for it. When such a translation is in place, step 2's load self-corrects to a full `--replace`, and step 1's check still requires the translation's provenance to name `vi.jsonl.gz` as its only input.

---

## Output Table (`gkm_vrs`)

The `gkm_vrs` table contains one row per variation that was submitted for VRS processing. Each row is a two-part record:

<div class="field-table" markdown>

| Field | Type | Description |
|---|---|---|
| `in` | record | The original `variation_identity` record — all fields from the input including `variation_id`, `source`, `fmt`, `vrs_class`, copy number fields, and metadata |
| `out` | record | The VRS resolution result — contains `id` (VRS digest identifier), `type` (Allele, CopyNumberChange, CopyNumberCount), `location`, `state`, `copyChange`, `copies`, and `errors` when resolution failed |

</div>

The `out.location` record includes the flattened position fields: `start`, `end`, `start_inner`, `start_outer`, `end_inner`, `end_outer`. For precise variants only `start` and `end` are populated; imprecise ranges use the inner/outer fields.

---

## Current Scope and Future Direction

!!! warning "Limited Scope"
    VRS processing currently resolves only the **single best expression** per variation — the defining allele for each Canonical Allele as selected by the [precedence hierarchy](variation-identity/index.md#precedence-hierarchy). Only variations that vrs-python can handle are successfully resolved; the remainder carry errors in the output.

The release runs from a single command — `src/scripts/run-release.sh` starts at the check of the cloud translation (see [Checking the cloud output](#checking-the-cloud-output)) and chains the transform/load/procedures and publish steps; variation identity, the export and the translation run in clinvar-ingest. See [Single-command run](index.md#single-command-run). No step needs local SeqRepo, UTA or gene-normalizer services.

One area of improvement remains planned:

- **Broader expression coverage** — expand VRS processing to resolve **all variant expressions** in ClinVar — the full `hgvs_list` preserved in the `variation_hgvs` table — rather than only the single selected source. This will provide richer downstream representation with multiple VRS identities per variation.

---

## Dependencies

- **Upstream**: [clinvar-ingest](https://github.com/clingen-data-model/clinvar-ingest) pipeline v2.7.0+ — `dataset_diff_on`, `variation_identity_incremental`, the `variation_identity` export and the `clinvar-ingest-vrsify` Cloud Run job ([vrs-python](https://github.com/ga4gh/vrs-python) against a RefgetStore)
- **Cloud Run job**: `vrs-to-vi-location-transformer` (`src/vrs-location-transformer/`) — location field flattening
- **BigQuery schema**: `schemas/vrs_output_2_0_1.schema.json`
- **Source table**: [`variation_identity`](variation-identity/variation-identity.md)
- **Downstream consumer**: [`gkm_catvar_proc`](cat-vrs/index.md)
