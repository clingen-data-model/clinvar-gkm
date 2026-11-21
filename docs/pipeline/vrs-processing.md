# VRS Processing

## Overview

VRS processing is the step between [Variation Identity](variation-identity/index.md) extraction and [Cat-VRS](cat-vrs/index.md) generation. It translates the selected SPDI or HGVS expression for each variation's defining allele into a GA4GH VRS (Variation Representation Specification) object — producing a computable, digest-identified representation of the variant.

The translation itself runs upstream, in [clinvar-ingest](https://github.com/clingen-data-model/clinvar-ingest): its Cloud Run job `clinvar-ingest-vrsify` translates each release's `variation_identity` export with [vrs-python](https://github.com/ga4gh/vrs-python) against a [RefgetStore](https://refgenie.org/refget/refgetstore-explained/) of genomic sequences, with no local services. In this project, `src/scripts/export-vi-table-to-gcs.sh` writes the same export, `src/scripts/check-cloud-vrsify.sh` checks that the cloud output belongs to the current export, and `src/scripts/vrs-to-bq-table.sh` transforms the output, loads `gkm_vrs`, and runs the downstream procedures. Export and publish are a separate final stage: `release-gkm.sh` (full bundles), `release-gkm-delta.sh` (deltas) and `release-gkm-parquet.sh` (the latest Parquet). The whole release, including this step, can be run end-to-end via `run-release.sh` (see [Single-command run](index.md#single-command-run)).

**This step is incremental.** VRS translation is per-variation (no cross-variation dependency), so diffing `variation_identity` between releases is a clean driver: the export sends only the variations whose `variation_identity` changed since the prior release (~0.3% of a weekly release, versus the whole ~4.5M snapshot), and the `gkm_vrs` load carries the prior release's results forward for the unchanged variations. This is where the largest cost reduction in the whole pipeline lands, because VRS translation is the most expensive stage.

The location transformation step uses a lightweight Cloud Run job defined in this project under `src/vrs-location-transformer/`.

---

## Workflow

### Step 1: Export `variation_identity` from BigQuery

The `variation_identity` table is exported to Google Cloud Storage as gzipped NDJSON at `gs://clinvar-gkm/YYYY-MM-DD/dev/vi.jsonl.gz`.

Upstream, clinvar-ingest's stored procedures job writes this export for every release, right after it runs `dataset_diff_on` and `variation_identity_incremental` (the same work as stages 0 and 1 of `run-release.sh`). So `run-release.sh` skips its stages 0–2 by default and starts at the check in stage 3. With `--with-upstream-stages` it runs them here too, and its stage 2 writes the same object again with:

```bash
./src/scripts/export-vi-table-to-gcs.sh YYYY-MM-DD          # incremental (default)
./src/scripts/export-vi-table-to-gcs.sh YYYY-MM-DD --full   # whole table, as vi-*.jsonl.gz shards
```

By default the export is **incremental** — it diffs `variation_identity` against the prior release and writes only the changed variations, so vrs-python processes the delta. `--full` writes the whole table as sharded `vi-*.jsonl.gz` objects, which the cloud vrsify does not read (see the version-invalidation note below).

Each record contains the single best expression source for a ClinVar variation — including the `source` expression string, `fmt` (spdi, hgvs, or gnomad), `vrs_class`, and copy number fields when applicable.

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

`run-release.sh` stage 3 runs no translation. It runs `src/scripts/check-cloud-vrsify.sh YYYY-MM-DD`, which reads the two objects and stops the release unless the conditions below hold. A release started at stage 4 (`--start-step 4`) runs the same check before it loads `gkm_vrs`; only `--allow-unchecked-vrs` skips it. The check stops the release unless:

- both `vi-vrs-python.jsonl.gz` and its provenance exist;
- the provenance names this release's `vi.jsonl.gz` as its only input, with the MD5 and size that object has now;
- the provenance names `vi-vrs-python.jsonl.gz` as its output, with its current size when the provenance records one.

A new generation of `vi.jsonl.gz` with the same MD5 passes: re-running stage 2 (`--with-upstream-stages`) rewrites the object, and when `variation_identity` has not changed it writes the same bytes. A `vi.jsonl.gz` with different content fails, and the cloud job does not redo the release by itself. That is why stages 0–2 are skipped by default: running them here could race the upstream export, and a rewrite with new content after the translation leaves the release untranslated. The check does not wait. Translate the current export again (upstream, `clinvar-ingest vrsify-submit` with `--overwrite`; or the local fallback below), then resume with `--start-step 3`. If the output is not there yet, wait for the next run of the cloud job and resume with `--start-step 3`.

#### Local fallback (`src/vrsify/`) { #local-vrsify-fallback }

`src/vrsify/vrsify.sh YYYY-MM-DD` is the translation this project ran locally before the cloud job existed; `run-release.sh` no longer calls it. It calls the clinvar-gk-python resolver installed as a pinned dependency (`src/vrsify/requirements.txt`), which wraps vrs-python and the [variation-normalizer](https://github.com/GenomicMedLab/variation-normalizer), against local SeqRepo, UTA and gene-normalizer services. Its output differs slightly from the cloud translation: for 2026-11-08, both produced the same 4,454 records, and the 7 that differed are untranslatable variants whose `out.errors` text differs.

`vrsify.sh` writes `vi-normalized-no-liftover.jsonl.gz` and writes no provenance, so the check cannot pass on it. To use it, copy it to `vi-vrs-python.jsonl.gz` and run `run-release.sh` with `--allow-unchecked-vrs` (from stage 3 or 4), which skips the check (see [`src/vrsify/README.md`](https://github.com/clingen-data-model/clinvar-gkm/tree/main/src/vrsify)).

`vrsify.sh` exits before starting unless four variables are set: `SEQREPO_ROOT_DIR`, `SEQREPO_DATAPROXY_URL`, `HGVS_SEQREPO_DIR` and `GENE_NORM_DB_URL`. It does not check `UTA_DB_URL`, and its comments describe UTA as needed only for liftover. The resolver still reaches UTA for some records; when `UTA_DB_URL` is unset, the UTA client falls back to the public UTA endpoint, which timed out on 33 records in the 2026-10-18 run. Export `UTA_DB_URL` pointing at a reachable UTA, in practice a local container from the variation-normalizer compose setup in the README.

### Step 3: Transform VRS locations

VRS `SequenceLocation` objects use array-valued `start` and `end` fields to represent imprecise ranges (inner/outer bounds). BigQuery does not natively support loading these mixed scalar/array values, so a minor transformation is needed before the data can be imported.

The `vrs-to-vi-location-transformer` Cloud Run job — defined in this project at `src/vrs-location-transformer/` — streams the VRS output through a `jq` filter that flattens each location's `start` and `end` arrays into separate scalar fields: `start`, `start_inner`, `start_outer`, `end`, `end_inner`, `end_outer`. When `start` or `end` is already a scalar (precise variants), the value is left unchanged.

This job is normally invoked by the `src/scripts/vrs-to-bq-table.sh` orchestrator (Step 4), not run by hand; the direct invocation is shown for reference:

```bash
gcloud run jobs execute vrs-to-vi-location-transformer \
  --args "gs://clinvar-gkm/YYYY-MM-DD/dev/vi-vrs-python.jsonl.gz" \
  --args "gs://clinvar-gkm/YYYY-MM-DD/dev/vi-final.jsonl.gz" \
  --wait --region us-east1
```

**Output:** `vi-final.jsonl.gz` on GCS.

### Step 4: Transform, load, run procedures

The transform + load + downstream procedures are run by `src/scripts/vrs-to-bq-table.sh` (a 3-step script): the Cloud Run transform (Step 3 above), the `gkm_vrs` load, and the gkm_* stored procedures. Export and publish are **not** done here — they are handled separately by `release-gkm.sh` (see [Export & Distribute](export.md)); `run-release.sh` chains this script and then `release-gkm.sh`.

```bash
./src/scripts/vrs-to-bq-table.sh YYYY-MM-DD          # from the start (Cloud Run transform)
./src/scripts/vrs-to-bq-table.sh YYYY-MM-DD 2        # resume from a later step (2=load, 3=procs)
```

The `gkm_vrs` load is **incremental**: it clones the prior release's `gkm_vrs` forward and merges in only the changed variations' new results (keyed on `in.variation_id`), rather than a `--replace` full load. It **self-corrects to a full `--replace`** when no baseline `gkm_vrs` exists or when the staged rows are not the changed subset — so a translation of the whole table is loaded correctly without any flag change.

Because each release clones the immediately prior one, the clone lineage grows one level per release and reaches BigQuery's cap of **3 chained clones/snapshots** roughly every 3 releases. When the seed clone fails with that error, the load automatically falls back to a **deep copy** (`CREATE OR REPLACE TABLE … AS SELECT *`) of the baseline, which materializes a fresh depth-0 table and resets the chain — self-healing, with no manual intervention. You'll see `clone chain full; reseeding via deep copy` in the log on those releases; it is expected and does not change the result.

!!! warning "Version-invalidation"
    The incremental carry-forward assumes the prior release's `gkm_vrs` was produced by the **same** VRS translation and the **same** `variation_identity` transform. A `variation_identity` transform change is caught by the diff: every variation whose row changes is exported and translated again.

    A change to the translation (vrs-python, the RefgetStore, or the cloud job's code) is not. Each release's provenance file records its `libraries` and `refget_store`, but the release does not compare them between releases. Re-translating every variation needs an upstream run: the cloud job translates only the incremental `vi.jsonl.gz`, not the `--full` shards. So `run-release.sh --full` stops at stage 3. With `--with-upstream-stages` it first rebuilds `variation_identity` in full and writes the full export (stages 1–2); without it, it stops before doing anything. Once every variation has been translated upstream into `vi-vrs-python.jsonl.gz`, continue with `--full-procs --start-step 4`; the load's self-correction then does a full `--replace`. The stage-4 check needs that translation's provenance to name `vi.jsonl.gz`; `--allow-unchecked-vrs` skips it.

    The local fallback's resolver is pinned in `src/vrsify/requirements.txt`; `vrsify.sh` stops if the installed resolver is not the pinned commit. To move an existing environment to a new pin, run `pip install --force-reinstall --no-deps -r src/vrsify/requirements.txt`; a plain `pip install -r` keeps the installed commit, because the resolver's version never changes.

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

The full release runs from a single command — `src/scripts/run-release.sh` starts at the check of the cloud translation (see [Checking the cloud output](#checking-the-cloud-output)) and chains the transform/load/procedures/publish stages; variation identity and the export run upstream, or here with `--with-upstream-stages`. See [Single-command run](index.md#single-command-run). No stage needs local SeqRepo, UTA or gene-normalizer services; only the [local fallback](#local-vrsify-fallback) does.

One area of improvement remains planned:

- **Broader expression coverage** — expand VRS processing to resolve **all variant expressions** in ClinVar — the full `hgvs_list` preserved in the `variation_hgvs` table — rather than only the single selected source. This will provide richer downstream representation with multiple VRS identities per variation.

---

## Dependencies

- **Upstream**: [clinvar-ingest](https://github.com/clingen-data-model/clinvar-ingest) — the `variation_identity` export and the `clinvar-ingest-vrsify` Cloud Run job ([vrs-python](https://github.com/ga4gh/vrs-python) against a RefgetStore)
- **Local fallback only**: [clinvar-gk-python](https://github.com/clingen-data-model/clinvar-gk-python), [variation-normalizer](https://github.com/GenomicMedLab/variation-normalizer), SeqRepo, UTA
- **Cloud Run job**: `vrs-to-vi-location-transformer` (`src/vrs-location-transformer/`) — location field flattening
- **BigQuery schema**: `schemas/vrs_output_2_0_1.schema.json`
- **Source table**: [`variation_identity`](variation-identity/variation-identity.md)
- **Downstream consumer**: [`gkm_catvar_proc`](cat-vrs/index.md)
