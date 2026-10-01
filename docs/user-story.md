# User Story: Harmonizing ClinVar by VRS Identity

**Why this matters**

ClinVar is the largest public collection of expert interpretations linking genetic variants to health
conditions. But using it alongside other resources has meant reconciling how each one *describes* a
variant — HGVS strings, genomic coordinates, assembly versions — even when they mean the exact same
change. ClinVar-GKM republishes ClinVar in the GA4GH **Genomic Knowledge Model (GKM)**: every variant
carries a computed **VRS identifier** — a content-based fingerprint that is identical wherever that
same change appears — and every classification is a structured **VA-Spec statement** with its evidence
and provenance attached. So you can look up a variant's ClinVar classifications *by identity*, and line
ClinVar up against any other VRS-aware dataset, without translating coordinates.

**At a glance**

- **Implementer** — ClinGen / ClinVar-GKM (a transformation of NCBI ClinVar)
- **Products** — VRS, Cat-VRS, VA-Spec, GKM-Core
- **Pattern** — Cross-source variant harmonization
- **Tools** — [vrs-python](https://github.com/ga4gh/vrs-python), [va-spec-python](https://github.com/ga4gh/va-spec-python), and the [GKM Toolkit](https://ga4gh.github.io/gkm-starter-kit/tools/gkm-toolkit/); the published clinvar-gkm [bundle](data-access/download.md)
- **Status** — Release candidate

!!! tip "New to GKM datasets?"
    The GA4GH [**GKM Starter Kit**](https://ga4gh.github.io/gkm-starter-kit/) is the best place to get
    oriented — it collects the reference libraries, the [GKM Toolkit](https://ga4gh.github.io/gkm-starter-kit/tools/gkm-toolkit/getting-started/)
    for loading and exploring bundles, and [other user stories](https://ga4gh.github.io/gkm-starter-kit/user-stories/)
    showing how projects put GKM to work. clinvar-gkm is one such producer.

---

## The challenge

A lab or knowledgebase that wants to annotate its variants with ClinVar's classifications has to answer
"is *my* variant the *same* variant ClinVar classified?" — a surprisingly hard question when the two
sides use different HGVS transcripts, 0- vs 1-based coordinates, or different genome builds. Teams end
up maintaining brittle normalization code just to join two tables, and the join silently misses variants
whose descriptions don't line up. And once a match is found, ClinVar's flat XML says *what* the
classification is but not, in a machine-actionable way, *who* made it, *how*, or *against which method*.

## What GKM enables

clinvar-gkm removes both frictions:

- **Identity, not description.** Each ClinVar variant is represented as a Cat-VRS `CategoricalVariant`
  over one or more **VRS** alleles. The VRS allele id (`ga4gh:VA.…`) is a digest of the normalized
  sequence change, so the *same* change computed from any other source produces the *same* id — the
  join is an equality check, no coordinate math.
- **Structured knowledge with provenance.** Each classification is a **VA-Spec** `Statement` asserting a
  `Proposition` (variant → condition) with its strength, review status, submitter `Contribution`s, and
  citations — the same shape whether it came from a single submitter (SCV), a variant-level aggregate
  (VCV), or a condition-level aggregate (RCV).
- **One self-describing file.** Everything is delivered as a [bundle](output-reference/overview.md) of
  named sections that reference each other by `#/section/id` [pointers](output-reference/id-references.md),
  so a variant, its classifications, conditions, and submitters are all reachable from one download.

## The data

Take the ClinVar expert-panel call on *BRCA1* `c.68_69del` (a pathogenic frameshift). In the bundle it
is a small connected graph — the classification statement points at a proposition, which points at the
variant, which resolves down to a VRS allele:

```json
// scv/  — the expert-panel classification statement
{
  "id": "clinvar.submission:SCV004101425.2",
  "type": "Statement",
  "classification": { "name": "Pathogenic", "primaryCoding": { "code": "pathogenic", "system": "ACMG Guidelines, 2015" } },
  "quality": { "conceptType": "Quality", "name": "expert panel" },
  "proposition": "#/varcond-proposition/SCV004101425-PATH",
  "contributions": [ { "contributor": "#/submitter/clinvar.submitter:509268", "activityType": "evaluated", "date": "2024-06-11" } ]
}

// varcond-proposition/  — what it asserts
{ "type": "VariantPathogenicityProposition", "predicate": "isCausalFor",
  "subject": "#/variation/clinvar:17662", "object": "#/condition/clinvar.trait:76328" }

// variation/  → allele/  → the VRS identity you can join on
{ "id": "clinvar:17662", "type": "CategoricalVariant", "members": [ "#/allele/ga4gh:VA.EE08XW4IpzeWhJAwComKOSmsPHTcP-1R" ] }
```

Any dataset that computes the same `ga4gh:VA.EE08XW4IpzeWhJAwComKOSmsPHTcP-1R` allele — a VCF annotation
pipeline, gnomAD, another knowledgebase — matches this ClinVar classification exactly, and can then read
its strength, review status, submitter, and condition straight from the bundle.

## The tools used

- **[vrs-python](https://github.com/ga4gh/vrs-python)** — compute the VRS allele id for your own variants
  to join against clinvar-gkm's `allele` section (GKM-Core + VRS).
- **[va-spec-python](https://github.com/ga4gh/va-spec-python)** — construct and validate the classification
  `Statement`s / `Proposition`s as typed Python models.
- **[GKM Toolkit](https://ga4gh.github.io/gkm-starter-kit/tools/gkm-toolkit/)** (`ga4gh.gkm`) — load a
  published bundle, follow `#/…` pointers, and export a connected slice, without writing the resolution
  yourself.
- **The clinvar-gkm [bundle](data-access/download.md)** — the monthly full plus weekly deltas on Cloudflare R2.

## How to explore this

- **Get the data** — [Downloads](data-access/download.md).
- **Understand the shape** — [Output Format](output-reference/overview.md) and
  [ID References](output-reference/id-references.md) (including a small `resolve()` helper for pointers).
- **Pull one variant's full graph** — maintainers can use the
  [Sub-Bundle Extraction](pipeline/sub-bundle.md) tool to slice a self-contained example like the one above.
- **See more GKM use cases** — the GKM Starter Kit's
  [user stories](https://ga4gh.github.io/gkm-starter-kit/user-stories/).
