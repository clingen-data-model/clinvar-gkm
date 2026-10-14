# Changelog

A running record of every schema change and data re-release on the 1.x line. See
[Versioning & Releases](versioning.md) for how versions are assigned, and the
[GitHub Releases](https://github.com/clingen-data-model/clinvar-gkm/releases) page for the
tagged source of each.

## 1.0.1 — 2026-10-13

A schema-conformance release shipped in place during the
[initial-stabilization period](versioning.md). Every published bundle (full **and** delta) now validates
against the [`schema/clinvar-gkm/`](https://github.com/clingen-data-model/clinvar-gkm/tree/main/schema/clinvar-gkm)
schemas with the official GA4GH gkm-toolkit — the largest published delta went from thousands of
non-conforming records to **zero**. All data was rebuilt, oracle-gated (full-vs-incremental and
delta-reconstruction, `0,0,0` across every section), and re-published to `/v1/`.

**Data-shape corrections** — bring the emitted data into conformance with the existing schema (no change to
the schema shape):

- Unmappable variants (haplotypes, genotypes, unmapped) no longer emit an empty `constraints` array; they
  validate as `ClinvarNonConstrainedVariant`.
- Typed extension values (`value_<type>`) are collapsed to the single polymorphic `value` field everywhere,
  including nested `classification.extensions`.
- Single-member condition sets are no longer emitted — a `ConceptSet` requires ≥2 concepts, and the lone
  condition is already referenced directly as `#/condition/…`.
- Delta bundles no longer contain empty (`{}`) sections.

**Schema change** — additive, backward-compatible:

- `flagged submission` added to the `clinvarReviewStatus` and `clinvarScvReviewStatus` enumerations (FLAG tier).

**Data**: re-released 4 monthly fulls (2026-07 … 2026-10) and 15 weekly deltas (2026-07-06 … **2026-10-11**, a
newly added weekly). `00-latest` advances to 2026-10-11. The schema `$id` version and bundle `schema_version`
move `1.0.0 → 1.0.1`; the `/v1/` layout is unchanged (keyed by major version, [ADR 0004](../decisions/0004-schema-versioning-and-release-management.md)).

## 1.0.0 — 2026-10-12

First official release on the finalized GKM standards — VRS 2.1.1, Cat-VRS 1.1.1, VA-Spec 1.1.0, and
GKM-Core 1.3.0. The 1.0.0 tag is frozen and immutable; its schema `$id`s remain resolvable.
