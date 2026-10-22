# ClinVar-GKM

ClinVar-GKM provides a standardized, machine-readable representation of [ClinVar](https://www.ncbi.nlm.nih.gov/clinvar/) release data using the **GKM (Genomic Knowledge Model)** schema set — VRS, Cat-VRS, and VA-Spec — from the GA4GH [Genomic Knowledge Standards](https://www.ga4gh.org/genomic-knowledge-standards/) workstream. It is developed and maintained by the [ClinGen](https://clinicalgenome.org/) driver project.

!!! tip "New to GKM datasets? Start with the GKM Starter Kit"
    The GA4GH [**GKM Starter Kit**](https://ga4gh.github.io/gkm-starter-kit/) is a practical entry point for working with GKM data. It brings together the [reference libraries](https://ga4gh.github.io/gkm-starter-kit/latest/tools/reference-implementations/) (vrs-python, cat-vrs-python, va-spec-python), the [GKM Toolkit](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/) for loading and exploring published bundles, and [user stories](https://ga4gh.github.io/gkm-starter-kit/latest/user-stories/) from projects putting GKM to work. clinvar-gkm is a GKM data producer — those tools work directly on its bundles.

## Why ClinVar-GKM

ClinVar is one of the most widely used public archives of human genetic variation and its relationship to disease. However, the native ClinVar XML format presents challenges for programmatic consumption — inconsistent structures, deeply nested records, and representations that do not align with emerging genomic data standards.

ClinVar-GKM addresses these challenges by transforming every ClinVar release into a consistent, semantically rich format built on GA4GH specifications:

- **Normalized variant identifiers** — Every variant receives a computable [VRS](https://vrs.ga4gh.org/) identifier, enabling unambiguous cross-system matching
- **Categorical variant representations** — Variants are represented as [Cat-VRS](https://cat-vrs.readthedocs.io/) categorical variants with defining allele constraints and expressions
- **Structured classification statements** — Every submitted (SCV), aggregate (VCV), and condition-level (RCV) classification is represented as a [VA-Spec](https://va-spec.ga4gh.org/) statement with explicit propositions, evidence, and provenance
- **Semantic consistency** — Classifications, propositions, conditions, genes, and cross-references use standardized structures with typed references

## What It Covers

The pipeline processes the **entirety** of each ClinVar XML release — every variation, submitted classification, and aggregate record is represented. While 100% of variant, SCV, VCV, and RCV records from the corresponding ClinVar XML release are included, some data types within ClinVar are not yet part of the v1 release.

| ClinVar Data Type | v1 Status |
| --- | --- |
| Variation Aggregate Classifications (VCVs) | Included |
| Variation-Condition Aggregate Classifications (RCVs) | Included |
| Germline and Somatic Submissions (SCVs) | Included |
| Variations (incl. Genes, HGVS, SPDI and VCF extensions) | Included |
| [Submitters](https://www.ncbi.nlm.nih.gov/clinvar/docs/submitter_list/) | Included |
| Aggregate & Case-level observations ([example](https://www.ncbi.nlm.nih.gov/clinvar/variation/1185392/#new-submission-germline)) | Planned |
| Functional data submissions ([example](https://www.ncbi.nlm.nih.gov/clinvar/variation/548447/#new-submission-functional-data)) | Planned |

Items marked **Planned** are not currently included in the v1 release. If this data is requested by the community, it will be added as demand indicates.

!!! note "Functional Data Submissions"
    Functional data is submitted to ClinVar as an SCV and may or may not be associated with a germline or somatic classification record. Functional data SCVs are excluded from the v1 release regardless of whether they are linked to a classification SCV. They will be included in a future release when functional data support is added.

Feedback and feature requests are welcome via the [GitHub issue tracker](https://github.com/clingen-data-model/clinvar-gkm/issues). For release announcements and change notices, join the email list [clinvar-gkm@broadinstitute.org](https://groups.google.com/a/broadinstitute.org/g/clinvar-gkm); see [Versioning & Releases](reference/versioning.md#stay-informed-have-a-say) for other ways to follow along.

New releases are produced within a day or two after ClinVar's XML releases and are intended to be synchronized with ClinVar's release dates.

## Who It's For

- **Variant scientists** seeking a clear, consistent representation of ClinVar classifications with explicit propositions, conditions, and evidence
- **Platform engineers** building systems that consume ClinVar data and need a structured, well-documented format for integration
- **GA4GH implementers** using ClinVar-GKM as a real-world validation of VRS, Cat-VRS, and VA-Spec schemas

---

## Getting Started

!!! tip "Prefer tables to JSON?"
    The latest release is also published as one set of **22 typed [Parquet](data-access/parquet.md) tables**, rebuilt every week, that you can query with SQL, with no database and no data loading. [**Query the Data**](parquet/index.md) starts with a live query console in your browser and works up to joins, recipes and large-scale analysis.

### Download the Latest Release

The latest ClinVar-GKM release is available as a single compressed JSON file:

```bash
# Download the newest official monthly release
curl -O https://data.clinvar-gkm.org/v1/1.1/clinvar-gkm_00-latest.json.gz

# Decompress
gunzip clinvar-gkm_00-latest.json.gz
```

### What's in the File

The release file is a single JSON object with **bundle sections** at the root level. Each section is a keyed collection of objects — the key is the object's unique identifier, and the value is the object itself.

```json
{
  "sequenceReference": { "SQ.abc123": { ... } },
  "location":          { "ga4gh:SL.xyz789": { ... } },
  "allele":            { "ga4gh:VA.def456": { ... } },
  "gene":              { "ncbigene:3077": { ... } },
  "variation":         { "clinvar:10": { ... } },
  "condition":         { "clinvar.trait:9580": { ... } },
  "conditionSet":      { "clinvar.traitset:1234": { ... } },
  "therapy":           { "clinvar.therapy:{sha256}": { ... } },
  "therapyGroup":      { "clinvar.therapygroup:{sha256}": { ... } },
  "submitter":            { "clinvar.submitter:500139": { ... } },
  "propositionPathogenicity":         { "SCV001234567-PATH": { ... } },
  "propositionOncogenicity":          { "SCV002345678-ONCO": { ... } },
  "propositionSomaticClinicalImpact": { "SCV003456789-TR": { ... } },
  "propositionClinvarCustom":         { "SCV004567890-RF": { ... } },
  "scv":                  { "clinvar.submission:SCV001234567.1": { ... } },
  "vcv":               { "VCV000012582.63-G-PATH-CP": { ... } },
  "rcv":               { "RCV000012345.8-G-PATH-CP": { ... } }
}
```

Objects reference each other using `#/` JSON pointer strings. For example, an allele references its location as `"#/location/ga4gh:SL.xyz789"`, and an SCV statement references its proposition as `"#/propositionPathogenicity/SCV001234567-PATH"`. Propositions are delivered in four sections grouped by meaning (`propositionPathogenicity`, `propositionOncogenicity`, `propositionSomaticClinicalImpact`, `propositionClinvarCustom`) — the pointer names the section the proposition lives in.

See [Output Format](output-reference/overview.md) for the full structure and reference patterns.

### Quick Example

To find the classification statements for a specific variant, start with the variation ID. ClinVar variation 10 (the HFE p.His63Asp variant) has the key `clinvar:10` in the `variation` section:

```json
{
  "variation": {
    "clinvar:10": {
      "id": "clinvar:10",
      "type": "CategoricalVariant",
      "name": "NM_000410.4(HFE):c.187C>G (p.His63Asp)",
      "members": ["#/allele/ga4gh:VA.ELQCnIBGqaTl0AEE0Az18XZ2cgIHAQIY"],
      "constraints": [ ... ],
      "extensions": [ ... ],
      "mappings": [ ... ]
    }
  }
}
```

The SCV statements for this variant reference it via `#/variation/clinvar:10` in their propositions. To find them, look for entries in the proposition sections (`propositionPathogenicity`, `propositionOncogenicity`, `propositionSomaticClinicalImpact`, `propositionClinvarCustom`) where `subject` matches, then find the corresponding `scv` entries that reference those propositions.

### Key Concepts

**Statements** are the core unit of ClinVar-GKM. Each statement represents a classification — either submitted (SCV), aggregated per variation (VCV), or aggregated per condition (RCV). Statements carry:

- A **classification** — the clinical significance label (e.g., Pathogenic, Likely benign)
- A **proposition** — what the classification asserts (variant X causes condition Y)
- **Direction** and **strength** — whether the evidence supports, disputes, or is neutral toward the proposition
- **Evidence lines** — links to the contributing submissions or lower-level aggregations
- **Extensions** — provenance metadata including submitted conditions, review status, and submission details

**Propositions** define the relationship being classified — a variant's causal role for a condition, its oncogenic potential, or its clinical impact. Each proposition has a type (e.g., `VariantPathogenicityProposition`), a predicate (e.g., `isCausalFor`), a subject variant, and an object condition.

**Conditions** represent the diseases or phenotypes that classifications are made against. Single conditions reference `#/condition/clinvar.trait:{id}`, while multi-condition sets reference `#/conditionSet/clinvar.traitset:{id}`.

---

## Data Access

ClinVar-GKM is distributed as **official monthly full bundles**, **weekly full bundles** and **weekly deltas**, laid out like NCBI's ClinVar XML folder, plus one typed Parquet dataset (one file per section) for the latest release. Each bundle is a gzip-compressed JSON file. The files are freely available for download from Cloudflare R2 object storage with no authentication required and no egress fees.

### Release Schedule

- **Weekly releases**: for every ClinVar weekly release, a weekly full bundle in `weekly/` and a delta in `deltas/` (the records added or updated since the prior release, plus a manifest listing per-section adds, updates, and deletes). `weekly/` keeps the current month only
- **Official monthly full bundles** are published once a month, aligned to ClinVar's own monthly VCV releases — each `ClinVarVCVRelease_YYYY-MM` triggers our `clinvar-gkm_YYYY-MM` full, built from the most recent weekly release before ClinVar's monthly cut
- At the start of each month, the previous month's deltas move to `deltas/YYYY-MM/` and its weekly fulls are deleted (the last one once the new month's monthly is published); at the start of each year, the previous year's monthlies and deltas move to `archive/YYYY/`

The stable filenames `clinvar-gkm_00-latest.json.gz` (official monthly) and `weekly/clinvar-gkm_00-latest_weekly.json.gz` (weekly full) always point to the newest of each. Any past week can be rebuilt from a monthly plus the deltas after it.

### Downloads

Download the newest official monthly and the newest weekly full:

```bash
curl -O https://data.clinvar-gkm.org/v1/1.1/clinvar-gkm_00-latest.json.gz
curl -O https://data.clinvar-gkm.org/v1/1.1/weekly/clinvar-gkm_00-latest_weekly.json.gz
```

See [How Releases Work](data-access/release-model.md) for the release model, and [Weekly Deltas](data-access/weekly-deltas.md) for the deltas and the replay recipe.

### Directory Structure

All paths are under the current line folder, `v1/1.1/`:

```text
clinvar-gkm_00-latest.json.gz                newest official monthly full
clinvar-gkm_yyyy-mm.json.gz                  official monthly fulls (current year)

weekly/
  clinvar-gkm_00-latest_weekly.json.gz       newest weekly full
  clinvar-gkm_yyyy-mmdd.json.gz              weekly fulls (current month only)

deltas/
  clinvar-gkm-delta_yyyy-mmdd.json.gz        weekly deltas (current month)
  clinvar-gkm-delta_yyyy-mmdd.manifest.json  per-release change manifest
  yyyy-mm/                                   earlier months of the current year

archive/yyyy/                                prior years: monthlies and deltas/yyyy-mm/

parquet/                                     one Parquet dataset, overwritten every release
```

### Release Notes

Pipeline changes that affect the structure or content of the output are recorded in the [Changelog](reference/changelog.md), and each tagged release is listed on [GitHub Releases](https://github.com/clingen-data-model/clinvar-gkm/releases). They cover changes specific to the ClinVar-GKM pipeline and do not replicate ClinVar's own release notes.

---

## How It Works

The pipeline runs on **Google BigQuery** using SQL stored procedures, with an external VRS Python processing step. The two most expensive stages — variation identity and VRS processing — run **incrementally**, recomputing only the variations that changed since the prior release and carrying the rest forward. From 1.1.0 the downstream GKM procedures rebuild in full every week. A per-release change log drives the weekly delta published to R2.

See the [Pipeline Overview](pipeline/index.md) for the full workflow.

---

## Next Steps

- [Output Format](output-reference/overview.md) — detailed guide to the bundle format
- [Variations](output-reference/cat-vrs.md) — how ClinVar variations are represented
- [SCV Statements](output-reference/scv-statements.md) — submitted classification statements
- [Data Model](output-reference/classes/index.md) — class hierarchy and schema reference
- [Pipeline Overview](pipeline/index.md) — how the data is produced from ClinVar XML
- [Examples](data-access/examples.md) — annotated JSON examples

## License

The code and the published data — the transformed bundles and Parquet files — are released under [CC0 1.0 Universal](https://github.com/clingen-data-model/clinvar-gkm/blob/main/LICENSE) (public domain dedication). The underlying ClinVar data comes from NCBI; see ClinVar's [disclaimer and data use policy](https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/#disclaimer).
