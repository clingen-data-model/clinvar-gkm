# Changelog

A running record of every schema change and data re-release on the 1.x line. See
[Versioning & Releases](versioning.md) for how versions are assigned, and the
[GitHub Releases](https://github.com/clingen-data-model/clinvar-gkm/releases) page for the
tagged source of each.

## 1.1.0 — 2026-10-22 { #110 }

A **breaking** release during the
[initial-stabilization period](versioning.md#110-and-general-availability); see
[ADR 0006](../decisions/0006-ship-1.1.0-in-place-under-v1.md). 1.1.0 ends that period: it is **generally
available (GA)**, its published files are immutable, and a later breaking change opens `v2/`. It reorganizes
the proposition sections and carries a set of corrections, all delivered through one full rebuild that rewrites every published file. It is
published under a new line folder, **`v1/1.1/`**, in a new R2 layout that mirrors NCBI's ClinVar FTP site (ADR
0009; see [New R2 layout](#new-r2-layout-110) below). Every download URL changes.

- **Breaking: propositions are grouped by meaning.** The four proposition sections and Parquet tables, which
  were grouped by the shape of their object (`varcond-proposition`, `varcustom-proposition`,
  `vartumor-proposition`, `vartherapy-proposition`), are replaced by four grouped by meaning:
  `propositionPathogenicity`, `propositionOncogenicity`, `propositionSomaticClinicalImpact` and
  `propositionClinvarCustom`. Proposition ids don't change, but every statement and evidence-line pointer
  names the new section (`#/varcond-proposition/SCV…-PATH` becomes `#/propositionPathogenicity/SCV…-PATH`).
  The four Parquet tables share one column schema, so `read_parquet('proposition*.parquet')` reads them all.
  `object_condition_id`, `object_tumor_type_id` and `object_therapy` become `object_id`, and
  `varcustom-proposition.subject_id` becomes `subject_variant_id`. Every proposition table gains
  `object_type` (the table `object_id` points at: `condition`, `conditionSet`, `therapy` or `therapyGroup`)
  and the columns only some of the old tables had (`condition_qualifier_id`, `mode_of_inheritance`,
  `penetrance`). The section is a function of the proposition `type` alone; see the
  [migration table](../parquet/tables.md#proposition-migration). The bundle schema's
  `propositionClinvarCustom` section no longer lists the abstract `ClinvarGermlineCustomProposition` base, so
  each record must carry one of the concrete `Clinvar*` types (every published record already does). The
  Parquet entries below name the pre-1.1.0 tables.
- **Breaking: version.** The schema `$id` version and the bundle `schema_version` move `1.0.1 → 1.1.0`.
- **Corrective**: everything else below. The schema changes accept every published record; the data corrections fix HGVS syntax, duplicate allele keys, RCV propositions without an object,
  condition pointers, condition names, citations, gene context and array order; and the Parquet changes add bare-id and typed columns and
  make every Parquet value match the bundle.

!!! warning "Do not mix 1.0.1 and 1.1.0 files"
    Do not apply 1.1.0 deltas to a 1.0.1 monthly. Replay `v1/1.1/` deltas only onto a `v1/1.1/` monthly, and
    the frozen `v1/1.0/` deltas only onto a `v1/1.0/` monthly. To be told about future releases, join the email
    list [clinvar-gkm@broadinstitute.org](https://groups.google.com/a/broadinstitute.org/g/clinvar-gkm); see
    [Versioning & Releases](versioning.md#stay-informed-have-a-say).

**Schema changes** — no published record changes:

- The four `ClinvarCategoricalVariant` branches are now mutually exclusive, each keyed on its constraint
  (`DefiningAlleleConstraint`, `CopyCountConstraint`, `CopyChangeConstraint`, or no `constraints`). Before, real
  variants matched more than one branch and failed the `oneOf`. The bundle schema now validates the
  `variation` section through `ClinvarCategoricalVariant`.
- The nine ClinVar `*Properties` mixins (`ClinvarScvStatementProperties`, `ClinvarAggregateStatementProperties`,
  `ClinvarCategoricalVariantProperties` and six more) are now `abstract`. They were emitted closed
  (`additionalProperties: false`) inside `allOf`, so a strict validator rejected the fields their GA4GH base
  classes supply. Each record is still closed by its class's `unevaluatedProperties: false`. This works around
  [ga4gh/gkm-metaschema#88](https://github.com/ga4gh/gkm-metaschema/issues/88) (#153).
- `GeneListItem` now describes the published shape, `{gene, relationship_type, source}`, all three required:
  `gene` is a `#/gene/` reference and `source` is `calculated` or `submitted`. It used to list
  `entrez_gene_id`, `hgnc_id`, `symbol` and `iris`, which no published record carries (#153).
- `ClinvarCanonicalAllele.definingContext` is removed. Cat-VRS 1.1.1's closed `CanonicalAllele` cannot accept
  it, and no record carried it (#153).

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

Expression order and the `name` are now fully deterministic. When equivalent ClinVar HGVS spellings tie for the
name, the tie is broken by value. That changes the `name` of the few alleles with tied expressions; the number
depends on the release (1 or 2 per release, 2 in 2026-10-11).

**RCV propositions without an object** — in the 2026-10-04 and 2026-10-11 releases, the 4 propositions of
`RCV000001117` (`-G-PATH`, `-G-PATH-CP`, `-G-NP`, `-G-NP-NOCL`) had no `object` and failed validation. This
also made the 2026-10-04 delta fail. An RCV's condition comes from one of its member SCVs. ClinVar's RCV-to-SCV
mapping still listed an SCV that ClinVar had removed (`SCV000021267`), and that SCV was picked even though it
no longer had a condition. The SCV is now picked from the members that have a condition. The propositions point
to `#/condition/clinvar.trait:2478` again, as they did through 2026-09-28. No other RCV changes.

**Condition references are all `#/` pointers** — two kinds of condition reference were bare ids, while every
other reference in the bundle was a `#/<section>/<id>` pointer. Both are now pointers to the same record (counts
for the 2026-10-11 release):

- A VCV proposition's `object`, when the VCV has a single condition (7,474,404 of 9,156,181): `clinvar.trait:2478`
  is now `#/condition/clinvar.trait:2478`, and `clinvar.traitset:…` is now `#/conditionSet/clinvar.traitset:…`.
- The `concepts` of the condition sets minted for VCV aggregates (`clinvar.conditionset:vcv-…`, 94,980 sets):
  members are now `#/condition/…` or, for a nested TraitSet, `#/conditionSet/…`.

The ids themselves are unchanged, including every `vcv-` set id. A pointer-following reader (the
[GKM Toolkit](https://ga4gh.github.io/gkm-starter-kit/latest/tools/gkm-toolkit/), `sub-bundle.py`)
now reaches these conditions. The `submittedCondition` and `submittedConditionSet` extension values stay bare
CURIEs: they record what was submitted, not a reference. In Parquet, the typed id columns (`object_condition_id`,
`object_id`, `object_tumor_type_id`, `conditionSet.concepts`) are unchanged bare ids; only the `data` columns
change, to the pointer form. See [ID References](../output-reference/id-references.md#where-references-appear).

**Conditions without a name** — 58 `condition` records in the 2026-10-11 release (57 or 58 in every release
since 2026-06-27) had neither `name` nor `primaryCoding`, so they failed `MappableConcept` validation. ClinVar
gives these traits no Preferred name in the trait record, but it does name them elsewhere. Each now takes its
name from ClinVar, in this order: the trait's Preferred name, then the Preferred name in the RCV's TraitSet, then
the trait's Alternate name (the first alphabetically). No value is made up, and `aliases` is unchanged:

- **Alternate name only** (51), such as `clinvar.trait:9800`, now named
  `Apolipoprotein c-ii variants, molecular defect unknown`. The name is also in `aliases`, as before.
- **Named only in the RCV** (7: `clinvar.trait:10547`, `10548`, `54780`, `76440`, `76481`, `78166`, `78167`). The
  trait record is empty, but the RCV's TraitSet names each `not provided`.

When an SCV's submitted condition has no name, its classification `description` uses the condition's name. In
173 SCVs of the 2026-10-11 release it changes from `for unspecified condition` to the ClinVar name.

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
  citation stays there. The second used to be fused into it as `pmid: "29116469,29907814"`; it is now a
  Document in the Method's own `additionalClinvarMethodCitations` extension (an array of Documents).

See [Citations](../output-reference/scv-statements.md#citations). This is a data change only; the schema already
allows these Document fields and extensions. In Parquet, `scv.reportedIn` and `scv.specifiedBy.reportedIn` gain
`name`, `documentType` and `extensions` at the end of the struct, and `scv.specifiedBy` gains
`extensions` after `reportedIn`. The existing fields keep their names, types and
positions.

**Gene context** — every SCV proposition `geneContextQualifier` gains a `geneContextSource` extension that says
where its gene came from. The gene is still the variant's one representative gene, chosen upstream; only the
name-derived genes below are new. Counts are for the 2026-09-28 release, before that change:

| `geneContextSource` | Meaning | Propositions |
| --- | --- | ---: |
| `submittedSymbolMatches` | The submitter's symbols include the qualifier's symbol | 5,781,920 |
| `submittedSymbolDiffers` | The submitter gave symbols, none equal to the qualifier's symbol (mostly previous symbols of the same gene, e.g. `GBA` for `GBA1`) | 27,671 |
| `inferredFromVariant` | The submitter gave no symbols | 881,325 |
| `submittedNotNormalized` | The variant has no single representative gene (the placeholder) | 4,814 |

- Symbols are compared after trimming spaces and ignoring case, so `C19ORF12` matches `C19orf12`.
- **Schema**: `geneContextSource` accepts only these four values. The new `ClinvarGeneContextQualifier` class
  defines them, and the bundle schema applies it to every proposition section.
- **Placeholder name**: the 4,814 placeholder qualifiers are named with the submitter's symbol, verbatim,
  instead of the literal `submitted genes were not normalized`. The 5 with several symbols join them with `, `
  in submitted order. They still have no `primaryCoding`, and `submittedGeneSymbols` is unchanged.
- **`submittedGeneSymbols` order**: the symbols are now in submitted order. Before, their order was not fixed,
  and the 45 lists with more than one symbol could change order from one build to the next.
- **`submittedGeneSymbols` trimmed**: the leading space our comma split left on symbols such as `" MEG3"` is
  removed (3 propositions, 8 symbols); ClinVar's own values are unchanged.
- **Name-derived genes**: gene context now comes entirely from the upstream
  [single-gene method](https://github.com/clingen-data-model/clinvar-ingest-bq-tools/blob/main/docs/methods/single-gene-variation.md), including the gene's symbol and HGNC id. This adds genes named in a variant's title
  that ClinVar does not associate with it, such as `NR_164162.1(GLRA4):n.1091C>T` → GLRA4. In the 2026-10-11
  release that is 25 variants (GLRA4, CCDC144NL, RNU6-81P) and 31 SCV propositions. 20 of them had the placeholder
  and now get the gene, with `submittedSymbolMatches`; the other 11 had no qualifier and now get one, with
  `inferredFromVariant`.
    - These genes are not in the bundle's `gene` section, which lists the genes ClinVar associates with a variant.
      So their Parquet `gene_context_id` does not join to `gene.parquet`.

The gene context stays on the proposition. This is a data change only: the schema already allows extensions
on the qualifier. See [Qualifier Extensions](../output-reference/scv-statements.md#qualifier-extensions).

**Upstream gene-context fixes** — two defects in the upstream `single_gene_variation` table
([clinvar-ingest-bq-tools](https://github.com/clingen-data-model/clinvar-ingest-bq-tools)) were fixed and
backfilled before the rebuild, so 1.1.0 carries them. Counts are for the 2026-09-28 release:

- **Haplotypes and genotypes in one gene**
  ([bq-tools #38](https://github.com/clingen-data-model/clinvar-ingest-bq-tools/issues/38)): when all of a
  haplotype's or genotype's alleles share one gene, it was rejected, so 63 SCV propositions had the placeholder
  or no gene context. They now get the shared gene; variation 3737 (FH Aarhus), for example, gets LDLR.
- **Gene ids missing from the gene table**
  ([bq-tools #39](https://github.com/clingen-data-model/clinvar-ingest-bq-tools/issues/39), fixed by #41 and
  #42): 37 SCV propositions lost their gene context because the variant's gene was not in the upstream gene
  table. Genes such as SMIM48 and LINC03103 now resolve. Genes with no HGNC id (`LOC*`) and NCBI-discontinued
  ids (such as STRTS) stay excluded by design, so not every one of the 37 regains a gene.

Both are tracked, with the other upstream defects found during 1.1.0, in
[#164](https://github.com/clingen-data-model/clinvar-gkm/issues/164).

**Array order** — several arrays had no fixed order, so two builds of the same release could list the same
items in a different order. Each now has one fixed order, and every build gives the same bytes. Only the order
changes; no value is added, removed or changed. Counts are for the 2026-10-11 release:

- `variation` (4,686,825 of 4,687,256 records): `extensions` follow a fixed order by name (`categoricalVariationType`
  … `clinvarHgvsList`, `clinvarGeneList`). `clinvarHgvsList` entries are ordered by expression, `clinvarGeneList` by
  NCBI gene id, and `mappings` start with the ClinVar `exactMatch`. A copy-number variant lists its
  `DefiningLocationConstraint` before its copy constraint.
- `condition` (12,832 of 23,392): `mappings` are ordered by system and code, and each coding's `iris` in a fixed
  order.
- VCV and RCV `evidenceLine` (688,701 and 358,507): `hasEvidenceItems` lists SCVs in id order and
  non-contributing statements in priority order.

Values picked from several equal candidates are made deterministic the same way: the sequence reference and
cross-reference IRI system of a variant, a condition's `primaryCoding`, `membershipOperator` and merged trait
attributes, and the representative expression source in variation identity. On 2026-10-11 none of these picks
changed a published value.

**Parquet** — typed columns now hold bare ids, as the other id columns already did:

- `vartherapy-proposition.object_therapy` is `clinvar.therapy:…` or `clinvar.therapygroup:…`, not a
  JSON-quoted `"#/therapy/…"` pointer.
- `variation.extensions[].value_gene_array[].gene` is `ncbigene:…`, not `#/gene/ncbigene:…`.
- New columns: `condition.data`; `therapy.name` and `therapy.concept_type`; `therapyGroup.membership_operator`
  and `therapyGroup.members`. `condition` keeps its camelCase column names, and `therapy` / `therapyGroup` keep
  `key` and `value`.
- The four proposition tables gain `gene_context_id` (the gene-context qualifier's own `ncbigene:` coding;
  NULL for the placeholder), `submitted_gene_symbols` (the submitter's gene symbols, verbatim) and
  `gene_context_source` (the qualifier's `geneContextSource`; see Gene context above). `gene_context_name` is
  unchanged, except that a placeholder now holds the submitter's symbol. The qualifier is one representative gene per
  variant, chosen upstream, not a submitter-asserted gene; see
  [Gene context](../parquet/tables.md#gene-context).
- `location` gains `loc_start_min`, `loc_start_max`, `loc_end_min` and `loc_end_max`: the bounds of each
  coordinate, set from the range when ClinVar gives an uncertain start or end (about 72,000 rows, mostly
  copy-number variants), where `loc_start` / `loc_end` are NULL. See [`location`](../parquet/tables.md#location).
- `scv`, `vcv` and `rcv` gain `proposition_section`: the proposition table their `proposition_id` is in
  (`propositionPathogenicity`, `propositionOncogenicity`, `propositionSomaticClinicalImpact` or
  `propositionClinvarCustom`), taken from the statement's pointer (#171).

References inside the JSON bundle and the `data` columns still use `#/<section>/` pointers.

**Parquet matches the bundle** — every Parquet value can now be recomputed from the JSON bundle:

- `scv.extensions` and `evidenceLine.extensions` no longer carry empty placeholder elements. Every row held
  all-null structs the bundle doesn't have: the unused `value_*` fields of each extension, with empty
  `concepts[]` and `xrefs[]` elements inside them (in the 2026-10-11 delta, 69,956 empty `concepts[]` and
  58,375 empty `xrefs[]` elements). An unused `value_*` field is now NULL and the empty elements are gone.
  The column type is unchanged.
- `conditionSet.data` is null-stripped like every other `data` column: a set with no `conceptSetType`
  omits the key instead of carrying `"conceptSetType": null`.

**Validation** — the rebuilt datasets and the real staged bundles were gated before publishing (reference
integrity, expected difference, delta reconstruction, strict GA4GH gkm-toolkit validation, bundle ↔ Parquet).
See [Release Validation](release-validation.md) for the gates and the results.

**Known issues** — see [Known Issues](known-issues.md) for the current list. In short: in the 2026-10-18
release, VRS normalization returned an error for 6 variations; 16 HGVS expressions in ClinVar's XML are
malformed and were reported to ClinVar; and DOIs that VA-Spec's pattern rejects are kept in `clinvarDoi`.
Upstream defects and their workarounds are tracked in
[#164](https://github.com/clingen-data-model/clinvar-gkm/issues/164).

**Republish**: 1.1.0 is not a patch. All 17 BigQuery datasets behind the published releases were rebuilt in
full. Then the 4 monthly full bundles (2026-07 … 2026-10, and `00-latest`), October's 3 weekly full bundles
(2026-10-04, 2026-10-11, 2026-10-18, and `00-latest_weekly`) and the 16 weekly deltas (2026-07-06 …
2026-10-18) were re-assembled and published under `v1/1.1/`. Every published bundle therefore
carries every change above, including the new proposition sections. File contents and checksums change, so
re-download anything fetched before 1.1.0. Copies downloaded earlier keep the old forms; the
[Query the Data](../parquet/index.md) pages note where they differ.

### New R2 layout { #new-r2-layout-110 }

The published files move to a layout modelled on NCBI's ClinVar XML folder (`xml/`, `xml/weekly_release/`,
`xml/archive/YYYY/`); see [How the layout mirrors NCBI](../data-access/download.md#how-the-layout-mirrors-ncbi).
The old `v1/datasets/`, `v1/deltas/` and `archive/1.0.1/` paths are removed, so update any script or bookmark:

| Before 1.1.0 | From 1.1.0 |
| --- | --- |
| `v1/index.json` | `v1/1.1/index.json` (the root `index.json` lists each line) |
| `v1/datasets/clinvar-gkm_YYYY-MM.json.gz`, `…_00-latest.json.gz` | `v1/1.1/clinvar-gkm_YYYY-MM.json.gz`, `v1/1.1/clinvar-gkm_00-latest.json.gz` |
| — (no weekly full) | `v1/1.1/weekly/clinvar-gkm_YYYY-MMDD.json.gz` and `weekly/clinvar-gkm_00-latest_weekly.json.gz`, current month only |
| `v1/deltas/YYYY-MMDD/clinvar-gkm-delta_YYYY-MMDD.json.gz` | `v1/1.1/deltas/clinvar-gkm-delta_YYYY-MMDD.json.gz` (current month); `deltas/YYYY-MM/…` (earlier months) |
| `v1/deltas/YYYY-MMDD/manifest.json` | `…/clinvar-gkm-delta_YYYY-MMDD.manifest.json`, beside its bundle |
| `v1/deltas/00-latest/` | removed; the newest delta is listed in `index.json`, and the newest weekly full is `weekly/clinvar-gkm_00-latest_weekly.json.gz` |
| `v1/archives/YYYY/` | `v1/1.1/archive/YYYY/` (monthlies, plus `deltas/YYYY-MM/`) |
| `v1/datasets/parquet/…` | `v1/1.1/parquet/` (one dataset) |
| `archive/1.0.1/` | `v1/1.0/` (the frozen 1.0.1 line) |

- **Weekly full bundles are new.** A full bundle is published for every weekly release and kept for the
  current month. When a new month's first release is published, the previous month's weekly fulls are deleted
  (the newest once the new month's monthly is published) and its deltas move to `deltas/YYYY-MM/`; at a new year, the year's monthlies and deltas move to
  `archive/YYYY/`. Any past week can be rebuilt from a monthly plus deltas; see
  [Rebuild a past week](../data-access/weekly-deltas.md#rebuild-a-past-week).
- **Replay fixes.** Each delta manifest's `checkpoint_full` now names the official monthly the delta's chain
  replays onto, as `{path, release, month, sha256}` with `release` the monthly's `source_release`; before,
  every manifest named the newest monthly (`2026-10`). Manifests also carry `schema_version`, `sha256` and
  `bundle`. Each monthly's `source_release`, the
  release it was built from, is published in `index.json`. The documented replay recipe compared months and
  skipped deltas from the monthly's own month; it now selects deltas by release date.
- **Checksums.** Every bundle has a `<file>.sha256` sidecar (`sha256sum -c` format), and the index lists each
  bundle's `sha256`. The root manifest's `schema` reads `1.1.0` (it said `1.0.0`).

**One Parquet dataset.** Parquet is derived from the bundle, so it is no longer kept per release: the dated
monthly sets (`v1/datasets/parquet/<YYYY-MM>/`) and every per-delta set (`v1/deltas/<YYYY-MMDD>/parquet/`) are
deleted. One dataset is published at `v1/1.1/parquet/`, built from the newest release (2026-10-18 for 1.1.0,
not the 2026-10 monthly) and overwritten every release. Its `manifest.json` gives the build date, the release
and dataset it was built from, the builder and every file's sha256, and the index's Parquet entry
(`source_release`) names the release too. No Parquet is kept in `archive/` or in frozen lines; past Parquet is rebuilt from the monthly
bundles with [`clinvar-gkm-parquet`](https://github.com/clingen-data-model/clinvar-gkm-parquet), which is
planned and not yet released. The index's delta entries lose their `parquet` list.

**The 1.0.1 generation.** Every 1.0.1 bundle and delta manifest is kept, byte-identical, in the frozen line
`v1/1.0/` (monthlies at the top, deltas under `deltas/YYYY-MM/`), with `.sha256` sidecars, a `MANIFEST.json`
(sha256 and original key per file), a `README.txt`, and a new `index.json` and `feed.xml` in the line layout.
It has no Parquet. Its delta manifests still name the old `v1/` paths and `checkpoint_full` `2026-10`; replay
it from `v1/1.0/index.json`.

## 1.0.1 — 2026-10-13

A schema-conformance release shipped in place during the
[initial-stabilization period](versioning.md#110-and-general-availability). Every published bundle (full **and** delta) now validates
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
