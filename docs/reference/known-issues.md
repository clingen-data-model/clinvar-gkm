# Known Issues

This page documents the current release status, data-coverage limitations, and transformation caveats of the
ClinVar-GKM pipeline.

## Release status

The current line is **`1.2`** (schema `1.2.0`): the ClinVar profiles narrowed to exactly what the pipeline
writes. It is built on the finalized **GKM (Genomic Knowledge Model)** standards — VRS 2.1.1, Cat-VRS 1.1.1,
VA-Spec 1.1.0, and GKM-Core 1.3.0 — and published under `v1/1.2/`, starting with one checkpoint monthly. The
1.1.x releases are kept, frozen, under `v1/1.1/`, and the 1.0.1 releases under `v1/1.0/`. See the
[Changelog](changelog.md) for what 1.2.0 changes and [1.1.0](changelog.md#110) for the release before it.

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
the genes ClinVar associates with a variant, so such a gene has no `gene` record, and in the Parquet
`'ncbigene:' || geneContextQualifier.primaryCoding.code` finds no row in `gene.parquet`. In the 2026-10-11 release this is 25 variants and 31 SCV
propositions. Genes with no HGNC id (`LOC*`) and NCBI-discontinued gene ids get no gene context, by design of
the upstream method.

## SCV and aggregate codes for Pathogenic/Likely pathogenic differ in case (resolved in 1.3.0) { #scv-and-aggregate-codes-for-pathogeniclikely-pathogenic-differ-in-case }

In 1.2.0, ClinVar-GKM's classification lookup (`clinvar_clinsig_types`, maintained upstream in
`clinvar-ingest-bq-tools`) coded `Pathogenic/Likely pathogenic` as `pathogenic/Likely pathogenic`, with a capital
L, and an SCV classified `Pathogenic/Likely pathogenic` carried that code in its `classification.primaryCoding`.
VCV and RCV codes are always lower case, so the same label was `pathogenic/likely pathogenic` there.
**Resolved in 1.3.0**: the lookup codes it `pathogenic/likely pathogenic`, so SCV and aggregate codes agree. 1.2
bundles keep the old SCV code; compare codes case-insensitively when you read both lines. See
[`classification.primaryCoding`](../pipeline/vcv-statements/vcv-aggregation-rules.md#classification-primarycoding).

## Guideline codings before 1.3.0 (resolved in 1.3.0) { #guideline-codings-before-1-3-0 }

Every line before 1.3, the frozen `v1/1.0/`, `v1/1.1/` and `v1/1.2/`, codes some classifications as no guideline
does. 1.3.0 corrects them, and adds the strengths and tier names the guidelines define. Published files never
change, so those lines keep the old codings. Each correction follows from the old record alone:

| In 1.0, 1.1 and 1.2 | From 1.3.0 | Where |
| --- | --- | --- |
| code `tier 1`, `tier 2`, `tier 3`, `tier 4` | `tier i`, `tier ii`, `tier iii`, `tier iv` | somatic clinical impact SCV, VCV and RCV classifications |
| system `AMP/ASCO/CAP (AAC) Guidelines, 2017` | `AMP/ASCO/CAP Guidelines, 2017` | the same, and SCV strengths |
| system `SVC v4` | `ACMG/AMP/CAP/ClinGen SVCv4.0` | VUS-high, VUS-mid and VUS-low classifications |
| code `pathogenic/Likely pathogenic` | `pathogenic/likely pathogenic` | SCV classifications ([above](#scv-and-aggregate-codes-for-pathogeniclikely-pathogenic-differ-in-case)) |
| no `classification.primaryCoding.name` | `Tier I` … `Tier IV`, from the code | somatic clinical impact SCVs |
| no `strength` | `High`, `Mid`, `Low`, from the code (on SCVs also coded `high`, `mid`, `low` under `ACMG/AMP/CAP/ClinGen SVCv4.0`) | statements classified VUS-high, VUS-mid or VUS-low |

ClinVar's own labels (`classification.name`, such as `Tier I - Strong`) are the same in every line. The changes
touch few records: in the 2026-11-22 release, 2,043 of 6.9 million SCVs and 3,592 VCV and RCV classification
aggregates.

**To compare across 1.3.0, or to read an older line with 1.3.0's codings**, recode the older bundle.
`recode-1-3-0.py` (Python 3.9 or later, no packages) copies a published bundle, changing only the records that
carry an old coding. Its output keeps the input's `schema_version`: it is the older line's bundle with 1.3.0's
codings, not a 1.3.0 bundle.

```bash
curl -fsSO https://clinvar-gkm.org/1.3/assets/scripts/recode-1-3-0.py
python3 recode-1-3-0.py clinvar-gkm_2026-11.json.gz clinvar-gkm_2026-11.recoded.json.gz
```

Its `recode(section, record)` function does the same for one record, for code that reads bundles itself. The
1.3.0 release checks it: applied to the final 1.2 monthly, it must give 1.3's first monthly, built from the same
ClinVar release, record for record ([Release Validation](release-validation.md)).

## Past Parquet is built, not downloaded

Only the latest Parquet set of each live line is published. Tables for an earlier release are built from its
bundle with [`gkm-bundle-parquet`](https://github.com/clingen-data-model/gkm-bundle-parquet) (2.0.0 on PyPI),
which builds a full bundle in about 3.5 hours on a 16 GB machine, or 40 minutes on a 128 GiB one; a mini-bundle of the records you need takes far less. See
[Build Your Own Tables and Mini-Bundles](../parquet/build-your-own.md).

---

Additional edge cases, transformation caveats, and specific limitations will be documented here as they are
identified.
