# Known Issues

This page documents the current release status, data-coverage limitations, and transformation caveats of the
ClinVar-GKM pipeline.

## Release status

The current release is **`1.0.1`** — a schema-conformance patch over the first official release (`1.0.0`) of
ClinVar-GKM, built on the finalized **GKM (Genomic Knowledge Model)** standards — VRS 2.1.1, Cat-VRS 1.1.1,
VA-Spec 1.1.0, and GKM-Core 1.3.0. Earlier builds were release candidates that tracked these specifications
while they were in ballot review; now that the standards are finalized, the output validates against the
released schemas. See the [Changelog](changelog.md) for what 1.0.1 corrected.

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

## Delta reconstruction — VRS allele records

Reconstructing a release's full `allele` set from a prior release plus a weekly delta is exact for every
section **except a small number of VRS `allele` records** — roughly a dozen, concentrated at the 2026-08-29
release (where the VRS line advanced and some allele/SPDI digests shifted) plus a handful elsewhere from a
non-deterministic ordering in allele assembly. The affected alleles' **keys are unchanged**, so every
`#/allele/…` reference still resolves and the **monthly full bundles are complete and correct**; only the
pairwise delta-reconstruction of those few records is imperfect. Pre-existing and tracked for a fix
(deterministic allele ordering).

---

Additional edge cases, transformation caveats, and specific limitations will be documented here as they are
identified.
