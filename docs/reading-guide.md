# How to Read These Docs

These docs serve three kinds of reader. Some want to understand the data, often starting from what they already know of ClinVar's website. Some want to know how ClinVar's XML becomes this format. Some are building a pipeline or an application on top of it. Find yours below, follow its path as far as you need, and use the section map to jump around.

---

## The sections at a glance

| Section | What it gives you | Read it when |
| --- | --- | --- |
| [Home](index.md) | What ClinVar-GKM is, the key concepts, and a first download | You are new to the project |
| [Downloads](data-access/download.md) | The files: monthly and weekly full bundles, weekly deltas, Parquet, and [how releases work](data-access/release-model.md) | You need the data, or need to keep a copy current |
| [Query the Data](parquet/index.md) | The 22 Parquet tables, a browser query console, joins, recipes, and working at scale | You prefer SQL and tables to JSON |
| [User Stories](user-story.md) | Two end-to-end worked problems | You want to see the data used for a real task |
| [Data Guide](output-reference/overview.md) | What each part of the bundle means: variations, SCV, VCV and RCV statements, ID references, and annotated examples | You want to understand the data itself |
| [Data Model](output-reference/classes/index.md) | Every class and field, generated from the schemas, plus the [profiles](profiles/index.md) that map ClinVar's statement types, classifications and review status | You need exact field definitions or validation rules |
| [Pipeline](pipeline/index.md) | Each step from ClinVar's XML to the published bundle | You want to know how a value was produced |
| Reference | [Versioning](reference/versioning.md), [Changelog](reference/changelog.md), [Release Validation](reference/release-validation.md), [Known Issues](reference/known-issues.md), [FAQ](reference/faq.md), [Glossary](reference/glossary.md) and more | You need what changed, what is guaranteed, or a definition |

The sections build on each other:

- **Downloads** delivers the files.
- The **Data Guide** explains what is in them.
- The **Data Model** defines every field exactly.
- **Query the Data** offers the same content as tables.
- The **Pipeline** explains how each value was derived from ClinVar.
- **Reference** records what changes between releases and what each release guarantees.

---

## Path 1: I know ClinVar's website and want to understand the data

Everything on a ClinVar variation page has a place in the bundle. This table maps the pieces of the page you know to where they live, and to the page that explains each one.

| On ClinVar's website | In ClinVar-GKM | Explained in |
| --- | --- | --- |
| A variation (`VCV000012582`) and its details: HGVS names, location, genes | A `variation` record (`clinvar:12582`), a Cat-VRS categorical variant, defined by GA4GH VRS `allele` and `location` records | [Variations](output-reference/cat-vrs.md) |
| The **Germline classification** and its review status | A `vcv` statement in the germline group, with its aggregate classification | [VCV Statements](output-reference/vcv-statements.md) |
| The **Somatic** clinical impact and oncogenicity classifications | `vcv` statements in the somatic clinical impact and oncogenicity groups | [VCV Statements](output-reference/vcv-statements.md), [Statement Types](profiles/statement-types.md) |
| Each row of **Submitted classifications** (an `SCV`) | An `scv` statement, which points to its submitter, its proposition and its evidence | [SCV Statements](output-reference/scv-statements.md) |
| A classification for one condition (an `RCV`) | An `rcv` statement | [RCV Statements](output-reference/rcv-statements.md) |
| The condition (a MedGen-linked trait) | A `condition`, or a `conditionSet` when there are several | [Output Format](output-reference/overview.md) |
| Review status stars | The statement's review status, which also sets its rank when submissions are aggregated | [Review Status](profiles/review-status.md) |
| "Pathogenic", "Drug response", and the other classification terms | A classification on a typed **proposition** (for example `VariantPathogenicityProposition`) | [Classifications](profiles/classifications.md), [Propositions](profiles/propositions.md) |

**Suggested order:**
1. The [Key Concepts](index.md#key-concepts) on Home.
2. [Output Format](output-reference/overview.md), for how the bundle's sections fit together.
3. The statement pages, starting with [SCV Statements](output-reference/scv-statements.md).
4. The annotated [Examples](data-access/examples.md), to see one real variation end to end.

Keep the [Glossary](reference/glossary.md) and the [FAQ](reference/faq.md) at hand. To explore without writing code, the [query console](parquet/index.md) runs SQL in your browser.

---

## Path 2: I want to know how ClinVar's XML becomes this format

The [Pipeline Overview](pipeline/index.md) walks the whole release. ClinVar's XML is first loaded into relational BigQuery tables by the upstream [clinvar-ingest](https://github.com/clingen-data-model/clinvar-ingest) pipeline and prepared by [clinvar-ingest-bq-tools](https://github.com/clingen-data-model/clinvar-ingest-bq-tools). ClinVar-GKM's stored procedures take over from there.

**Suggested order:**
1. [Variation Identity](pipeline/variation-identity/index.md) and [VRS Processing](pipeline/vrs-processing.md): how each variant gets its GA4GH VRS identity.
2. [Cat-VRS](pipeline/cat-vrs/index.md): how a ClinVar variation becomes a categorical variant.
3. [Conditions & Traits](pipeline/conditions-and-traits/index.md): how submitted conditions are matched to ClinVar's traits.
4. [SCV Statements](pipeline/scv-statements/index.md), then [VCV Statements](pipeline/vcv-statements/index.md) with their [aggregation rules](pipeline/vcv-statements/vcv-aggregation-rules.md), then [RCV Statements](pipeline/rcv-statements/index.md).
5. [Export & Distribute](pipeline/export.md): bundle assembly, weekly deltas, Parquet and publication.

When a value in the data surprises you, the matching pipeline step says where it came from. The [Profiles](profiles/index.md) record the mapping rules. [Release Validation](reference/release-validation.md) lists the checks every release passes before publication. Design decisions are recorded as ADRs, for example [ADR 0007](decisions/0007-pipeline-principles-and-simplification.md) on pipeline principles.

---

## Path 3: I am building a pipeline or an application on this data

**Suggested order:**
1. [How Releases Work](data-access/release-model.md): monthly and weekly full bundles, weekly deltas, and how to keep a copy current. Then [Weekly Deltas](data-access/weekly-deltas.md) for applying a delta to a full bundle.
2. [Versioning & Releases](reference/versioning.md): what is guaranteed. 1.1.0 is the general-availability release; published files are immutable, and a breaking change opens a new major line.
3. Pick an interface:
   - **JSON bundles:** the [Output Format](output-reference/overview.md), [ID References](output-reference/id-references.md) for resolving `#/section/id` pointers, and the [Data Model](output-reference/classes/index.md) for exact fields and schemas.
   - **Parquet:** [Query the Data](parquet/index.md), from the [22 tables](parquet/tables.md) and [joins](parquet/joining.md) to [working at scale](parquet/performance.md) and [other tools](parquet/other-tools.md).
4. The GA4GH libraries: the [GKM Starter Kit](https://ga4gh.github.io/gkm-starter-kit/) (vrs-python, cat-vrs-python, va-spec-python and the GKM Toolkit) works directly on these bundles. See [GA4GH Standards](reference/gks-standards.md).
5. Worked problems: the [User Stories](user-story.md), and [Sub-Bundle Extraction](pipeline/sub-bundle.md) for cutting a self-contained subset.

Before you depend on a release, check the [Changelog](reference/changelog.md) for migration notes and [Known Issues](reference/known-issues.md). The [Release Validation](reference/release-validation.md) page lists the checks behind each release.

---

## Getting help and news

- **Questions and ideas:** [GitHub Discussions](https://github.com/clingen-data-model/clinvar-gkm/discussions). The [Roadmap](reference/roadmap.md) is built from them.
- **Problems with the data:** [GitHub Issues](https://github.com/clingen-data-model/clinvar-gkm/issues).
- **Release announcements, version changes and events:** the [clinvar-gkm@broadinstitute.org](https://groups.google.com/a/broadinstitute.org/g/clinvar-gkm) email list. [Stay Informed](stay-informed.md) explains how to join.
