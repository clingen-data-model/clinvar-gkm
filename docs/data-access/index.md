# Data Access

ClinVar-GKM is distributed as a **monthly full bundle** plus **weekly deltas**, synchronized with ClinVar's XML releases. Each is a gzip-compressed JSON file. Typed Parquet (one file per section) is published for the latest release only: it is derived from the bundle and regenerated each release. The files are freely available for download from Cloudflare R2 object storage with no authentication required and no egress fees.

---

## Latest Release

!!! warning "The monthly full is a month-start baseline, not the current week"
    `clinvar-gkm_00-latest.json.gz` reflects the **last release of the _previous_ month** — e.g. the `2026-10` full is built from the `2026-09-28` release, the last one before ClinVar's October monthly cut. It does **not** include the current month's weekly changes. To get the current weekly state, apply the latest delta on top of it — see the [Consumer Replay Model](weekly-deltas.md#consumer-replay-model).

Download the most recent monthly full bundle:

```bash
curl -O https://data.clinvar-gkm.org/v1/datasets/clinvar-gkm_00-latest.json.gz
```

Download the most recent weekly delta and its manifest:

```bash
curl -O https://data.clinvar-gkm.org/v1/deltas/00-latest/clinvar-gkm-delta_00-latest.json.gz
curl -O https://data.clinvar-gkm.org/v1/deltas/00-latest/manifest.json
```

The full bundle is a single JSON object containing all bundle sections — variations, statements, propositions, conditions, and supporting reference data. A delta uses the same section structure but carries only the records added or updated since its baseline release. Typed Parquet files (one per section) are derived from the bundle and published for the latest release only, at `v1/datasets/parquet/00-latest/`, rebuilt every release. See [Output Format](../output-reference/overview.md) for the complete structure, [Weekly Deltas](weekly-deltas.md) for the consumer replay model, and [Parquet Files](parquet.md) for the full Parquet list.

---

## Release Schedule

- **Weekly deltas** are published for every ClinVar release under `deltas/<yyyy-mmdd>/`, mirrored at `deltas/00-latest/`
- **Monthly full bundles** are published once a month under `datasets/`, aligned to ClinVar's own monthly VCV releases — each `ClinVarVCVRelease_YYYY-MM` triggers our `clinvar-gkm_YYYY-MM` full, built from the most recent weekly release before ClinVar's monthly cut
- At the start of each year, the previous year's monthly full bundles move to `archives/`
- The latest Parquet set (`datasets/parquet/00-latest/`) is rebuilt from every release

The stable filenames `clinvar-gkm_00-latest.json.gz` (monthly full) and `clinvar-gkm-delta_00-latest.json.gz` (weekly delta) always point to the most recent full and delta respectively.

---

## Directory Structure

```text
datasets/
  clinvar-gkm_00-latest.json.gz              latest monthly full bundle
  clinvar-gkm_yyyy-mm.json.gz                monthly full bundles (current year)

datasets/parquet/00-latest/
  {section}.parquet                          typed Parquet for the latest release only (derived; rebuilt every release)
  source.json                                the release the Parquet was built from

deltas/00-latest/
  clinvar-gkm-delta_00-latest.json.gz        latest weekly delta bundle
  manifest.json                              latest delta manifest

deltas/yyyy-mmdd/
  clinvar-gkm-delta_yyyy-mmdd.json.gz        weekly delta bundle (added + updated records)
  manifest.json                              per-release change manifest

archives/{yyyy}/
  clinvar-gkm_yyyy-mm.json.gz                monthly full bundles from prior years
```

---

## Release Notes

Pipeline changes that affect the structure or content of the output are documented in the `release_notes/` directory. These notes cover additions, bug fixes, or schema changes specific to the ClinVar-GKM pipeline — they do not replicate ClinVar's own release notes.

---

## File Format

The primary release format is a **gzip-compressed JSON file** (`.json.gz`). Typed Parquet files (one per bundle section) are derived from the bundle for analytical use; only the latest release's set is published. The decompressed JSON content is a single JSON object with bundle sections at the root level:

```json
{
  "sequenceReference": { ... },
  "location": { ... },
  "allele": { ... },
  "copyNumberCount": { ... },
  "copyNumberChange": { ... },
  "gene": { ... },
  "variation": { ... },
  "condition": { ... },
  "conditionSet": { ... },
  "therapy": { ... },
  "therapyGroup": { ... },
  "submitter": { ... },
  "propositionPathogenicity": { ... },
  "propositionOncogenicity": { ... },
  "propositionSomaticClinicalImpact": { ... },
  "propositionClinvarCustom": { ... },
  "evidenceLine": { ... },
  "vcv_evidenceLine": { ... },
  "rcv_evidenceLine": { ... },
  "scv": { ... },
  "vcv": { ... },
  "rcv": { ... }
}
```

Each section is a keyed collection — the key is the object's unique identifier, and the value is the complete object. Objects reference each other using `#/` JSON pointer strings.

See [Output Format](../output-reference/overview.md) for detailed documentation of each section.

---

## What's Next

- [Output Format](../output-reference/overview.md) — the bundle structure and reference patterns
- [Examples](examples.md) — annotated sample records from each section
- [Pipeline Overview](../pipeline/index.md) — how the data is produced from ClinVar XML
