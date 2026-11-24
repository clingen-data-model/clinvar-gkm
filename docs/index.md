# ClinVar-GKM

**All of [ClinVar](https://www.ncbi.nlm.nih.gov/clinvar/), every week, as standardized records you can query with SQL or load in Python.**

ClinVar-GKM turns each ClinVar release into records in the GA4GH **GKM (Genomic Knowledge Model)** schemas — [VRS](https://vrs.ga4gh.org/), [Cat-VRS](https://cat-vrs.readthedocs.io/) and [VA-Spec](https://va-spec.ga4gh.org/) — and publishes them as JSON bundles and Parquet tables, free, with no sign-in. It is built and maintained by [ClinGen](https://clinicalgenome.org/).

**Current version line:** 1.2 (`v1/1.2/`, schema 1.2.0), with a new release within a day or two of each ClinVar weekly release. The newest files are on [Downloads](data-access/download.md).

!!! warning ""
    **1.2.0 started a new version line.** Change `v1/1.1/` to `v1/1.2/` in your scripts; see [Version Lines](data-access/release-model.md#version-lines).

## Get started { #getting-started }

<div class="grid cards" markdown>

-   **Try it in your browser** · 2 minutes

    ---

    Run SQL against all of ClinVar in a live console, with nothing to install. Then follow one variant end to end in the [Quick Start](start/quick-start.md).

    [Open the query console](parquet/index.md)

-   **Get the data**

    ---

    20 Parquet tables (5 KB to 1.7 GB each, 4.6 GB in all), full JSON bundles (4.9 GB compressed), or weekly deltas (usually under 30 MB).

    [Choose your data](start/choose-your-data.md)

-   **What can I do with it?**

    ---

    Tasks the data makes possible, from finding conflicting classifications to harmonizing variants by VRS identifier.

    [See what you can do](start/what-you-can-do.md)

-   **I know ClinVar's website**

    ---

    Where each part of a ClinVar variation page lives in the data: the variant, its classifications, its submissions and their review status.

    [Map the website to the data](reading-guide.md#path-1-i-know-clinvars-website-and-want-to-understand-the-data)

</div>

New to SCV, VCV and RCV, propositions or bundles? [Key Concepts](start/concepts.md) explains them in five minutes, and the [Glossary](reference/glossary.md) defines every term. [How to Read These Docs](reading-guide.md) maps the site to what you need.
{ #key-concepts }

## What it covers

Every release covers the **whole** of ClinVar's XML release: 100% of its variations and of its SCV (submitted), VCV (per-variant) and RCV (per-variant-and-condition) classifications.

| ClinVar data type | v1 status |
| --- | --- |
| Variation aggregate classifications (VCVs) and variation-condition aggregate classifications (RCVs) | Included |
| Germline and somatic submissions (SCVs) | Included |
| Variations, with genes, HGVS, SPDI and VCF extensions | Included |
| [Submitters](https://www.ncbi.nlm.nih.gov/clinvar/docs/submitter_list/) | Included |
| Aggregate and case-level observations ([example](https://www.ncbi.nlm.nih.gov/clinvar/variation/1185392/#new-submission-germline)) | Planned |
| Functional data submissions ([example](https://www.ncbi.nlm.nih.gov/clinvar/variation/548447/#new-submission-functional-data)) | Planned |

**Planned** items are not in v1 and will be added as the community asks for them. Functional data SCVs are left out of v1 even when they are linked to a classification SCV.

## Data use and citation

ClinVar-GKM re-represents ClinVar data from NCBI, and ClinVar's [disclaimer and data use policy](https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/#disclaimer) applies to it:

- **Not for direct clinical use** without review by a genetics professional.
- **Cite ClinVar** as the data source, and ClinVar-GKM ([DOI 10.5281/zenodo.18343663](https://doi.org/10.5281/zenodo.18343663)) if you used these files.
- **License:** the code and the published files are [CC0 1.0](https://github.com/clingen-data-model/clinvar-gkm/blob/main/LICENSE). CC0 covers ClinGen's contribution only; NCBI's and ClinVar's policies still apply. ClinVar-GKM is not an NCBI, NLM or NIH product.

[Data Use and Citation](data-use.md) has the citations and what to carry with the data when you redistribute it.

## Help and news

Report data problems on [GitHub Issues](https://github.com/clingen-data-model/clinvar-gkm/issues) and ask questions in [Discussions](https://github.com/clingen-data-model/clinvar-gkm/discussions). Release announcements go to the [clinvar-gkm@broadinstitute.org](https://groups.google.com/a/broadinstitute.org/g/clinvar-gkm) list ([Stay Informed](stay-informed.md)); changes are in the [Changelog](reference/changelog.md). How the data is made: [Pipeline Overview](pipeline/index.md). Other GKM data and tools: the GA4GH [GKM Starter Kit](https://ga4gh.github.io/gkm-starter-kit/).
