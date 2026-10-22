# Known Issues

This page documents the current release status, data-coverage limitations, and transformation caveats of the
ClinVar-GKM pipeline.

## Release status

The current release is **`1.1.0`**. It regroups the proposition sections by meaning and carries a set of data
corrections, all delivered by one full rebuild of every published release. It is built on the finalized
**GKM (Genomic Knowledge Model)** standards — VRS 2.1.1, Cat-VRS 1.1.1, VA-Spec 1.1.0, and GKM-Core 1.3.0 — and
published under `v1/1.1/`; the 1.0.1 releases are kept, frozen, under `v1/1.0/`. See the
[Changelog](changelog.md#110) for what 1.1.0 changed.

## Data coverage

Each release includes **100% of the Germline and Somatic submission (SCV) records** from the corresponding
ClinVar XML release, and their classification content is carried through **without modification** to what
ClinVar provides. However, the pipeline does **not** yet extract 100% of every attribute and tertiary content:

- **Case-level and functional data** — aggregate case values, grouped/individual case-level evidence, and
  functional-data (incl. MaveDB) submissions are **not currently extracted**.
- **Rarely-provided attributes** — some attributes that ClinVar provides only occasionally and sparsely may
  also **not yet be represented**.

If data that exists in ClinVar is missing here and would be useful to you, it can be added to the
[Roadmap](roadmap.md) and prioritized by community demand — open or upvote a discussion in the
[Ideas](https://github.com/clingen-data-model/clinvar-gkm/discussions/categories/ideas) category. Case-level /
functional data are already tracked as roadmap items
([case data](https://github.com/clingen-data-model/clinvar-gkm/discussions/104),
[functional data](https://github.com/clingen-data-model/clinvar-gkm/discussions/105)).

## Delta reconstruction — VRS allele records (resolved in 1.1.0)

In 1.0.1, reconstructing a release's `allele` section from the prior release plus its weekly delta was inexact
for about a dozen VRS `allele` records, most at the 2026-08-29 release, where the VRS line advanced, and the
rest from non-deterministic ordering in allele assembly. **Resolved in 1.1.0**: alleles are built once per
allele id with a total order, and the delta-reconstruction oracle finds no difference (`0,0,0`) on every
section for all 16 delta pairs, including the cross-version pair 2026-08-22 → 2026-08-29. The frozen 1.0.1
deltas under `v1/1.0/` keep the old behavior.

## VRS normalization errors

VRS normalization does not resolve every variation. In the 2026-10-18 release, 6 of the 43,868 variations
sent for normalization returned an error. The error text is in the `vrsProcessingException` extension on the
variation's `variation` record. See
[Categorical Variant Extensions](../pipeline/cat-vrs/catvar-extensions.md).

## Malformed HGVS expressions in ClinVar

16 HGVS expressions on 14 variations in ClinVar's VCV XML are malformed at the source, most without an HGVS
type letter (`g.`, `c.`). From 1.1.0 each is kept verbatim as an extension of a listed expression, either merged
onto ClinVar's valid expression for the same accession or on a repaired one; see
[HgvsListItem](../output-reference/cat-vrs.md#hgvslistitem). They were reported to ClinVar on 2026-10-18 (NCBI
case CAS-1713568-P1W1Q1), tracked in [#163](https://github.com/clingen-data-model/clinvar-gkm/issues/163).

## DOIs that VA-Spec's pattern rejects

VA-Spec's `Document.doi` pattern rejects some valid DOIs, such as SICI-style DOIs with parentheses
([ga4gh/va-spec#461](https://github.com/ga4gh/va-spec/issues/461)). Such a DOI is kept in the `clinvarDoi`
extension of its Document, with its `doi.org` URL in `urls`, instead of in `doi`. See
[Citations](../output-reference/scv-statements.md#citations).

## RCV membership lists SCVs missing from the VCV data

ClinVar's RCV-format XML runs out of sync with its VCV XML: an RCV's SCV list sometimes names SCVs that are
absent from the VCV data, 2–3 a week. This is ClinVar's data, faithfully parsed. RCV statements
are built only from SCVs present in the VCV data, so an RCV's evidence can list fewer SCVs than ClinVar's RCV
record.

## Name-derived gene context genes are not in the `gene` section

An SCV proposition's gene context can be a gene named in the variant's title that ClinVar does not associate
with the variant (for example `NR_164162.1(GLRA4):n.1091C>T` → GLRA4). The bundle's `gene` section lists only
the genes ClinVar associates with a variant, so such a gene has no `gene` record, and its Parquet
`gene_context_id` does not join to `gene.parquet`. In the 2026-10-11 release this is 25 variants and 31 SCV
propositions. Genes with no HGNC id (`LOC*`) and NCBI-discontinued gene ids get no gene context, by design of
the upstream method.

## Bundle schema `$id` does not resolve

The bundle schema's `$id`, `https://w3id.org/clingen/schema/clinvar-gkm/<version>/json/ClinvarGkmBundle`,
returns 404: the file is published as `schema/clinvar-gkm/clinvar-gkm-bundle.schema.json`, not under `json/`.
This is true for 1.0.0 and 1.0.1 as well, whose class schema `$id`s do resolve. Validators that load the
schemas from a local copy or registry are unaffected.

## Past Parquet cannot yet be rebuilt

Only the latest Parquet set is published. Past Parquet is meant to be rebuilt from the monthly bundles with
[`clinvar-gkm-parquet`](https://github.com/clingen-data-model/clinvar-gkm-parquet), which has no release yet.

---

Additional edge cases, transformation caveats, and specific limitations will be documented here as they are
identified.
