# GA4GH GKS Standards

ClinVar-GKM represents ClinVar data using the **GKM (Genomic Knowledge Model)** schema set — **VRS**,
**Cat-VRS**, and **VA-Spec** — curated by the GA4GH [Genomic Knowledge Standards (GKS)](https://www.ga4gh.org/genomic-knowledge-standards/)
workstream and built on shared **GKS-Core** classes. This page links each specification, its schema
repository, and its official Python implementation, and notes how each is applied in this pipeline.

## Specifications

| Standard | What it is | How ClinVar-GKM uses it | Specification | Schema repo | Python library |
| --- | --- | --- | --- | --- | --- |
| **VRS** — Variation Representation Specification | Extensible spec for representing and uniquely identifying biological sequence variation | Every variant receives a computable, digest-identified VRS identifier | [vrs.ga4gh.org](https://vrs.ga4gh.org) | [ga4gh/vrs](https://github.com/ga4gh/vrs) | [ga4gh/vrs-python](https://github.com/ga4gh/vrs-python) |
| **Cat-VRS** — Categorical Variation | A terminology and data model for describing categorical variation concepts | Variations are represented as Cat-VRS categorical variants with defining-allele constraints and expressions | [cat-vrs.ga4gh.org](https://cat-vrs.ga4gh.org/) | [ga4gh/cat-vrs](https://github.com/ga4gh/cat-vrs) | [ga4gh/cat-vrs-python](https://github.com/ga4gh/cat-vrs-python) |
| **VA-Spec** — Variant Annotation Specification | An information model for representing variant annotations (statements, propositions, evidence) | Every SCV, VCV, and RCV classification is a VA-Spec statement with explicit propositions, evidence, and provenance | [va-spec.ga4gh.org](https://va-spec.ga4gh.org/) | [ga4gh/va-spec](https://github.com/ga4gh/va-spec) | [ga4gh/va-spec-python](https://github.com/ga4gh/va-spec-python) |
| **GKS-Core** | Common classes and schemas shared by all GKS specifications (entities, `MappableConcept`, extensions, etc.) | Underlies the shared building blocks used across VRS, Cat-VRS, and VA-Spec output | — | [ga4gh/gks-core](https://github.com/ga4gh/gks-core) | *(bundled with the libraries above)* |

## Getting started with the standards

- **[GKM Starter Kit](https://github.com/ga4gh/gkm-starter-kit)** ([site](https://ga4gh.github.io/gkm-starter-kit/)) — a single community-facing entry point that helps you understand and adopt the GKS/GKM standards in practice.

The three Python libraries above (`vrs-python`, `cat-vrs-python`, `va-spec-python`) let you parse ClinVar-GKM
bundle and Parquet records directly into the standards' validated models — see the planned
[Starter-kit documentation page](https://github.com/clingen-data-model/clinvar-gkm/discussions/100) on the
[Roadmap](roadmap.md) for worked examples.
