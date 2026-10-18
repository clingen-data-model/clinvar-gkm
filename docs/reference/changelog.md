# Changelog

A running record of every schema change and data re-release on the 1.x line. See
[Versioning & Releases](versioning.md) for how versions are assigned, and the
[GitHub Releases](https://github.com/clingen-data-model/clinvar-gkm/releases) page for the
tagged source of each.

## 1.0.2

<!-- set the release date when 1.0.2 is tagged -->

A conformance and Parquet-consistency release, shipped with one rebuild and one backfill of the published
releases.

**Schema change** — no change to valid instances:

- The four `ClinvarCategoricalVariant` branches are now mutually exclusive, each keyed on its constraint
  (`DefiningAlleleConstraint`, `CopyCountConstraint`, `CopyChangeConstraint`, or no `constraints`). Before, real
  variants matched more than one branch and failed the `oneOf`. The bundle schema now validates the
  `variation` section through `ClinvarCategoricalVariant`.
- The schema `$id` version and the bundle `schema_version` move `1.0.1 → 1.0.2`.

**Data-shape correction** — 14 variants (16 HGVS expressions) had `clinvarHgvsList` entries with syntax
`hgvs.?`, which VRS doesn't allow. ClinVar's submitted text had no HGVS type letter. It is now kept as an
extension on the listed expression's `nucleotideExpression`, never altered or dropped:

- **Merged** (11): ClinVar also supplies a valid expression for the same accession. That one is listed, with
  `invalidClinvarExpression` (the submitted text) and `expressionMerged: true`.
- **Repaired** (5): no valid one exists. The expression is listed with its type letter restored, with
  `originalClinvarExpression` (the submitted text) and `expressionRepaired: true`.

**Parquet** — typed columns now hold bare ids, as the other id columns already did:

- `vartherapy-proposition.object_therapy` is `clinvar.therapy:…` or `clinvar.therapygroup:…`, not a
  JSON-quoted `"#/therapy/…"` pointer.
- `variation.extensions[].value_gene_array[].gene` is `ncbigene:…`, not `#/gene/ncbigene:…`.
- New columns: `condition.data`; `therapy.name` and `therapy.concept_type`; `therapyGroup.membership_operator`
  and `therapyGroup.members`. `condition` keeps its camelCase column names, and `therapy` / `therapyGroup` keep
  `key` and `value`.
- The four proposition tables gain `gene_context_id` (the gene-context qualifier's own `ncbigene:` coding;
  NULL for the `submitted genes were not normalized` placeholder) and `submitted_gene_symbols` (the submitter's
  gene symbols, verbatim). `gene_context_name` is unchanged. The qualifier is one representative gene per
  variant, chosen upstream, not a submitter-asserted gene; see
  [Gene context](../parquet/tables.md#gene-context).
- `location` gains `loc_start_min`, `loc_start_max`, `loc_end_min` and `loc_end_max`: the bounds of each
  coordinate, set from the range when ClinVar gives an uncertain start or end (about 72,000 rows, mostly
  copy-number variants), where `loc_start` / `loc_end` are NULL. See [`location`](../parquet/tables.md#location).

References inside the JSON bundle and the `data` columns still use `#/<section>/` pointers.

**Backfill**: the 14 corrected `variation` records were patched into the published monthly full bundles, and
the `variation` and `vartherapy-proposition` Parquet files were re-exported for every published release, so
fulls and deltas carry the same forms. The new columns start with the 1.0.2 export and are not backfilled. The
[Query the Data](../parquet/index.md) queries run on both the old and new forms.

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
