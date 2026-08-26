# Known Issues

This page documents the current release status, data-coverage limitations, and transformation caveats of the
ClinVar-GKM pipeline.

## Release status — Release Candidate

The current release is a **Release Candidate** (`1.0-rc3`). It will **not** become the first official version
until the impending release of the **GKM (Genomic Knowledge Model)** suite — VRS, Cat-VRS, and VA-Spec — which
is currently in **Ballot review** and expected to be released **before mid-September 2026**. Until those
specifications are finalized, schema and output details may still change to track the approved standards.

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

## Outdated example files

The annotated JSONC/JSON example files in the repository's [`examples/`](https://github.com/clingen-data-model/clinvar-gkm/tree/main/examples)
directory (VCV, RCV, SCV, and Cat-VRS) currently reflect an **earlier output shape** and do **not** match what
the pipeline now produces in the bundles. They predate the four-section proposition refactor and the va-spec
1.1.0 conformance updates — for example, `classification`/`confidence`/`strength` are shown in an older form
rather than as `MappableConcept` structs, and propositions are shown inline rather than in the datatype-specific
sections. Refreshing them from current output is tracked in
[issue #115](https://github.com/clingen-data-model/clinvar-gkm/issues/115). Until then, treat the published
bundle (and `DESCRIBE` on the Parquet files) as the source of truth for output structure, not the example files.

---

Additional edge cases, transformation caveats, and specific limitations will be documented here as they are
identified.
