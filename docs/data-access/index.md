# Data Access

ClinVar-GKM is distributed as **official monthly full bundles**, **weekly full bundles** and **weekly deltas**, synchronized with ClinVar's XML releases and laid out like NCBI's ClinVar XML folder. Each is a gzip-compressed JSON file. One typed Parquet dataset (one file per section) is published for the latest release: it is derived from the bundle and overwritten each release. The files are freely available for download from Cloudflare R2 object storage with no authentication required and no egress fees.

---

## Latest Release

!!! tip "Monthly full or weekly full?"
    `clinvar-gkm_00-latest.json.gz` is the newest **official monthly**; it reflects the **last release of the _previous_ month** — e.g. the `2026-10` monthly is built from the `2026-09-28` release, the last one before ClinVar's October monthly cut. For the current week, download the newest weekly full, `weekly/clinvar-gkm_00-latest_weekly.json.gz`.

Download the newest official monthly and the newest weekly full:

```bash
curl -O https://data.clinvar-gkm.org/v1/1.1/clinvar-gkm_00-latest.json.gz
curl -O https://data.clinvar-gkm.org/v1/1.1/weekly/clinvar-gkm_00-latest_weekly.json.gz
```

The full bundle is a single JSON object containing all bundle sections — variations, statements, propositions, conditions, and supporting reference data. A delta uses the same section structure but carries only the records added or updated since its baseline release. The Parquet dataset (one file per section) is derived from the bundle, published at `v1/1.1/parquet/` and overwritten every release. See [Output Format](../output-reference/overview.md) for the complete structure, [Weekly Deltas](weekly-deltas.md) for the replay model, and [Parquet Files](parquet.md) for the full Parquet list.

---

## Release Schedule

- **Weekly releases**: for every ClinVar weekly release, a weekly full bundle in `weekly/` and a delta in `deltas/`. `weekly/` keeps the current month only
- **Official monthly full bundles** are published once a month at the top of the line folder, aligned to ClinVar's own monthly VCV releases — each `ClinVarVCVRelease_YYYY-MM` triggers our `clinvar-gkm_YYYY-MM` full, built from the most recent weekly release before ClinVar's monthly cut (its `source_release`)
- **At the start of each month**, the previous month's deltas move to `deltas/YYYY-MM/` and its weekly fulls are deleted
- **At the start of each year**, the previous year's monthlies and deltas move to `archive/YYYY/`
- The Parquet dataset (`parquet/`) is rebuilt and overwritten from every release

The stable filenames `clinvar-gkm_00-latest.json.gz` (official monthly) and `weekly/clinvar-gkm_00-latest_weekly.json.gz` (weekly full) always point to the newest of each.

---

## Directory Structure

All paths are under the current line folder, `v1/1.1/` (see [Downloads](download.md#directory-structure) for the version folders):

```text
clinvar-gkm_00-latest.json.gz                newest official monthly full
clinvar-gkm_yyyy-mm.json.gz                  official monthly fulls (current year)

weekly/
  clinvar-gkm_00-latest_weekly.json.gz       newest weekly full
  clinvar-gkm_yyyy-mmdd.json.gz              weekly fulls (current month only)

deltas/
  clinvar-gkm-delta_yyyy-mmdd.json.gz        weekly delta bundles (current month; added + updated records)
  clinvar-gkm-delta_yyyy-mmdd.manifest.json  per-release change manifest
  yyyy-mm/                                   earlier months of the current year

archive/yyyy/
  clinvar-gkm_yyyy-mm.json.gz                monthly fulls from prior years
  deltas/yyyy-mm/                            deltas from prior years

parquet/
  {section}.parquet                          the one Parquet dataset (derived; overwritten every release)
  manifest.json                              build date, source release, tool version
```

Every bundle has a `<file>.sha256` sidecar.

---

## Release Notes

Pipeline changes that affect the structure or content of the output are documented in the `release_notes/` directory. These notes cover additions, bug fixes, or schema changes specific to the ClinVar-GKM pipeline — they do not replicate ClinVar's own release notes.

---

## File Format

The primary release format is a **gzip-compressed JSON file** (`.json.gz`). Typed Parquet files (one per bundle section) are derived from the bundle for analytical use; only one dataset, for the latest release, is published. The decompressed JSON content is a single JSON object with bundle sections at the root level:

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
