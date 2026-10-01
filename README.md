<p align="center">
  <a href="https://clinicalgenome.org"><img src="docs/assets/images/clingen-logo.svg" alt="ClinGen" height="60"></a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="https://www.ga4gh.org"><img src="docs/assets/images/ga4gh-logo.svg" alt="GA4GH" height="50"></a>
</p>

# ClinVar-GKM

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18343663.svg)](https://doi.org/10.5281/zenodo.18343663)

ClinVar-GKM is a data transformation pipeline that converts [ClinVar](https://www.ncbi.nlm.nih.gov/clinvar/) release data into the **GKM (Genomic Knowledge Model)** schema set — VRS, Cat-VRS, and VA-Spec — curated by the GA4GH [GKS (Genomic Knowledge Standards)](https://www.ga4gh.org/genomic-knowledge-standards/) workstream. Developed and maintained by the [ClinGen](https://clinicalgenome.org/) driver project, it transforms the **entirety** of each ClinVar release — every variation, submitted classification, and aggregate record — into standardized, computable formats.

The pipeline runs with each weekly ClinVar release, publishing a monthly full bundle plus weekly deltas in GA4GH standard formats via Cloudflare R2.

## GA4GH Standards Implemented

- **[VRS](https://vrs.ga4gh.org/)** (Variation Representation Specification) — normalized, computable variant identifiers
- **[Cat-VRS](https://cat-vrs.readthedocs.io/)** (Categorical VRS) — categorical variant representations (canonical alleles)
- **[VA-Spec](https://va-spec.readthedocs.io/)** (Variant Annotation Specification) — variant classification statements

## Output

Each release is published as a self-contained **bundle**: a single gzip-compressed JSON object whose top-level keys are named sections, cross-referenced by `#/section/key` JSON pointers. The same content is also published as **typed Parquet**, one file per section. Sections span VRS/Cat-VRS variant representations (`variation`, `allele`, `location`, `gene`, …), VA-Spec classification statements (`scv`, `vcv`, `rcv`), propositions, and supporting condition, therapy, and submitter records.

Distribution follows a **full + delta** model:

| Product | Cadence | Contents |
| --- | --- | --- |
| **Monthly full** | Monthly | Every record for the release — JSON bundle + typed Parquet |
| **Weekly delta** | Every ClinVar release | Only records added or updated since the prior release, plus a `manifest.json` of per-section adds, updates, and deletes |

A consumer reconstructs current state by taking the latest monthly full and replaying the weekly deltas published since.

## Data Access

Releases are hosted on **Cloudflare R2** — free, no authentication, no egress fees. The stable "latest" URLs always point at the newest release:

- **Latest monthly full (JSON):** <https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev/datasets/clinvar-gkm_00-latest.json.gz>
- **Latest weekly delta (JSON):** <https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev/deltas/00-latest/clinvar-gkm-delta_00-latest.json.gz>
- **Release index:** <https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev/index.json>

See the [Downloads guide](https://clingen-data-model.github.io/clinvar-gkm/data-access/download/) for Parquet, dated releases, the delta replay model, and curl / Python / DuckDB examples. Sample records for each section are in the [`examples/`](examples/) directory.

## Pipeline Overview

The pipeline runs on **Google BigQuery** using SQL stored procedures, with an external VRS processing step:

1. **Variation Identity** — extract core variant data from ClinVar XML
2. **VRS Processing** — convert variants to VRS format (external Python tooling)
3. **Cat-VRS Generation** — create categorical variant representations
4. **Condition & Trait Mapping** — map ClinVar conditions to standardized terms
5. **SCV Statement Generation** — produce clinical classification statements
6. **VCV Statement Generation** — produce aggregate classification statements
7. **Export & Publish** — assemble the JSON bundle and typed Parquet, then publish the full/delta products to Cloudflare R2

## Documentation

Full documentation is available at **[clingen-data-model.github.io/clinvar-gkm](https://clingen-data-model.github.io/clinvar-gkm/)**, including pipeline details, GA4GH profile definitions, data access guides, and a schema registry.

## Repository Structure

```text
src/
  procedures/                BigQuery SQL stored procedures (the pipeline core)
  scripts/                   Release orchestration and R2 publishing scripts
  vrsify/                    VRS processing driver (GA4GH vrs-python)
  vrs-location-transformer/  Cloud Run service for VRS sequence-location transforms
  gks-registry/              Python tool for GA4GH schema metadata
schema/                      GKM schema set (clinvar-gkm + VRS/Cat-VRS/VA-Spec/gkm-core submodules)
schemas/                     VRS transform output JSON schemas
examples/                    Sample output organized by type (cat-vrs, scv, vcv, rcv)
docs/                        Zensical documentation source
```

## Citation

If you use this project, please cite it:

> Babb, L., Ferriter, K., & O'Neill, T. (2026). *ClinVar-GKM* (Version 1.0.0) [Software]. <https://doi.org/10.5281/zenodo.18343663>

See [CITATION.cff](CITATION.cff) for machine-readable citation metadata.

## License

This project is licensed under [CC0 1.0 Universal](LICENSE) (public domain dedication), covering both the code and data outputs. This aligns with FAIR data principles and common practices in the genomics and bioinformatics community.
