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

**Duplicate allele keys** — when two ClinVar variations normalize to the same VRS allele, the `allele` section
held one record per variation under the same key. A JSON reader kept whichever record came last, and Parquet had
one row per record. This affected 1 allele in the 2026-09-23 to 2026-10-11 releases:
`ga4gh:VA.lP8drLGSbZDn4x3Dr2TPwZOvvvU6kAJl`, the SERPINE1 4G/5G dup shared by variations 13572 and 4897201. It
also affected 8 alleles in the June to August releases, which were ClinVar duplicate variations that ClinVar has
since merged. Each allele now has exactly one record:

- `expressions` is the union of the expressions from every variation that shares the allele, with no duplicates.
- `name` is picked from that union by the existing rule (HGVS type, then precedence). Nothing is lost: the
  expressions the other variations would have used as the name are still in `expressions`.
- Each variation keeps its own `variation` record, which points to the shared allele.

Expression order and the `name` are now fully deterministic. Ties are broken by value, which changes the name of
2 alleles that had tied expressions.

**Citations** — SCV `reportedIn` and `specifiedBy.reportedIn` now hold **one Document per ClinVar citation**,
with no citation dropped and no ClinVar value changed silently. Counts are for the 2026-09-28 release:

- **Multi-id citations merged** (5,698 citations on 5,698 SCVs): a citation with several ids, such as ACMG 2015
  with a DOI, a PubMed id and a PMC id, was split into 2–3 Documents. It is now one Document with `pmid`, `doi`
  and every URL. Together these citations account for 10,260 fewer Documents.
- **Restored** (78,142 citations on 72,603 SCVs): URL-only citations (76,379) were dropped and are now
  `{urls: [url]}`. Text-only citations (1,763) were dropped and now keep their text in a `clinvarCitationText`
  extension. The 109 text-only assertion-method citations had no `reportedIn`; they now get one the same way.
  Assertion-method citations that have both a URL and text (12,451) also gain `clinvarCitationText`.
- **New labels**: ClinVar's citation `abbrev` (e.g. `ACMG, 2015`) is the Document `name`, and its citation
  `type` (e.g. `general`, `practice guideline`) is `documentType`, verbatim.
- **No more non-URL `urls` or invalid `doi` values.** 3,874 Documents had a `doi` that fails the VA-Spec pattern,
  and 12 had a non-URL `urls` entry. Malformed DOIs such as `doi:10.…`, `https://doi.org/10.…` or ones with stray spaces (117)
  are repaired; the original is kept in `originalClinvarCitation`, flagged `citationRepaired`. A DOI-sourced PubMed
  or PMC id (3) moves to `pmid` or a PMC URL and also keeps `originalClinvarCitationSource`. Unusable ids, mostly
  3,746 assertion-method DOIs recorded as `https`, are kept only in `invalidClinvarCitation`. A valid
  SICI-style DOI that the VA-Spec pattern rejects is kept in `clinvarDoi`, with its `doi.org` URL.
- **Ordering**: Documents are ordered by PubMed id and then by content, so a full and an incremental build
  produce the same bytes.
- **Assertion methods with two citations** (6 SCVs): `Method.reportedIn` holds one Document. ClinVar's first
  citation stays on the method. The second used to be fused into it as `pmid: "29116469,29907814"`; it now goes on
  the statement's `reportedIn`, flagged `clinvarAssertionMethodCitation`.

See [Citations](../output-reference/scv-statements.md#citations). This is a data change only; the schema already
allows these Document fields and extensions. In Parquet, `scv.reportedIn` and `scv.specifiedBy.reportedIn` gain
`name`, `documentType` and `extensions` at the end of the struct. The existing fields keep their names, types and
positions.

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

**Parquet matches the bundle** — every Parquet value can now be recomputed from the JSON bundle:

- `scv.extensions` and `evidenceLine.extensions` no longer carry empty placeholder elements. Every row held
  all-null structs the bundle doesn't have: the unused `value_*` fields of each extension, with empty
  `concepts[]` and `xrefs[]` elements inside them (in the 2026-10-11 delta, 69,956 empty `concepts[]` and
  58,375 empty `xrefs[]` elements). An unused `value_*` field is now NULL and the empty elements are gone.
  The column type is unchanged.
- `conditionSet.data` is null-stripped like every other `data` column: a set with no `conceptSetType`
  omits the key instead of carrying `"conceptSetType": null`.

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
