# Proposition Reorganization by Meaning — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development or superpowers:executing-plans.
> Steps use checkbox (`- [ ]`) syntax. Each PR in §8 is one reviewable unit. Run `/catchup` before starting
> a PR; this plan was written against `main` @ `567272c` and `1.0` @ `6606d3d` with the PR stack as of
> 2026-10-18. Every live BigQuery rebuild and every R2 write is a separately user-confirmed step.

**Goal:** Reorganize ClinVar-GKM propositions by **meaning** instead of object shape, in **both** the JSON
bundle and the typed Parquet, in the current 1.x line, as part of the **one** consolidated rebuild and
backfill (see the master plan `2026-10-16-parquet-followups.md`, "Consolidated data release").

**Decided (user, 2026-10-18):**

1. Four meaning-based groups replace `varcond-proposition`, `varcustom-proposition`, `vartumor-proposition` and
   `vartherapy-proposition` (§2).
2. All proposition Parquet tables share **one column schema**, so `read_parquet('proposition*.parquet')`
   unions them with no renaming. Every column is derivable from the bundle (§4).
3. It ships now under ADR 0004 §5 (in-place change during stabilization, announced), inside the single
   consolidated rebuild + backfill. Docs move with every PR.

**Architecture (recommended):** Keep the three per-level dict tables (`gkm_dict_proposition`,
`gkm_dict_rcv_proposition`, `gkm_dict_vcv_proposition`) exactly as they are. Only two things change in BigQuery:
the section name inside every statement and evidence-line pointer (`#/<section>/<id>`), and one canonical
type→section function that every producer and the export share. The split into sections stays at the delivery
layer (export + assemble), as Phase 2 did. Proposition ids, proposition records, the change log, the delta
build and both oracles are untouched by the reorganization itself.

**Consequence:** every SCV, VCV and RCV statement and every SCV evidence line changes (its pointer), so the
patch-style backfill prepared for 1.0.2 (`scratchpad/backfill102/`) no longer fits. The release becomes a
**full rebuild of all 16 datasets + full re-export + re-assembly of every published bundle and Parquet set**,
modeled on 1.0.1 (§6).

**Source:** Counts were measured read-only on `clinvar_2026_09_28_v2_6_0` (source of the 2026-10 monthly) and
`clinvar_2026_10_11_v2_6_0`, and type coverage across all 16 published-release datasets. Parquet sizes are
from a prototype that rebuilt the four new tables from the published 2026-10 Parquet `data` column (the bundle
record) with DuckDB, calibrated against the published files (§5).

---

## 1. Decisions at a glance

| # | Item | Status | Recommendation |
| --- | --- | --- | --- |
| 1 | Groups and names | decided | keep the proposed names (§2.2) |
| 2 | Shared Parquet schema | decided | the 14 columns in §4, `data` last |
| 3 | Ship in 1.x now, one rebuild | decided | full rebuild of 16 datasets (§6) |
| A | Gene-context qualifier design | **resolved** (2026-10-18) | (a) + (b) in this release (#159), (c) deferred; unaffected by the reorg (§3.A) |
| B | Content-shared propositions | open | **defer** (§3.B) |
| C | Version label | open | **1.1.0**, in place under `/v1/` (§3.C) |
| D | Normalize VCV `object` and `vcv-` set members to `#/` pointers | **decided** (2026-10-18) | (i), in this rebuild, as its own PR: #160, branch `fix/uniform-condition-pointers` (§3.D) |
| E | `proposition_section` column on statement Parquet | new, open | optional; recommended (§4.4) |

---

## 2. The groups

### 2.1 Coverage check

Every proposition type in all 16 datasets behind published releases (`clinvar_2026_06_27_v2_5_0` …
`clinvar_2026_10_11_v2_6_0`, SCV + RCV + VCV dicts, 91 GB scanned) falls into exactly one group. 15 types occur:

| Type | Levels seen | New section |
| --- | --- | --- |
| `VariantPathogenicityProposition` | SCV, RCV, VCV | `propositionPathogenicity` |
| `ClinvarNotProvidedProposition`, `ClinvarDrugResponseProposition`, `ClinvarOtherProposition`, `ClinvarRiskFactorProposition`, `ClinvarAssociationProposition`, `ClinvarAffectsProposition`, `ClinvarConflictingDataFromSubmitterProposition`, `ClinvarProtectiveProposition`, `ClinvarConfersSensitivityProposition` | SCV, RCV, VCV | `propositionClinvarCustom` |
| `VariantClinicalSignificanceProposition` | SCV, RCV, VCV | `propositionSomaticClinicalImpact` |
| `VariantDiagnosticProposition`, `VariantPrognosticProposition`, `VariantTherapeuticResponseProposition` | SCV only (evidence-line targets) | `propositionSomaticClinicalImpact` |
| `VariantOncogenicityProposition` | SCV, RCV, VCV | `propositionOncogenicity` |

**Stragglers:**

- **`ClinvarUndefinedProposition`:** 0 rows in all 16 datasets, but reachable. The SCV proc falls back to it
  when a classification has no type (`gkm-scv-statement-proc.sql` Step 1, the `STRUCT('ClinvarUndefinedProposition' …)`
  arm), and the RCV/VCV dict builds use `IFNULL(cpt.gks_type, 'ClinvarUndefinedProposition')`. The lookup table
  `clinvar_ingest.clinvar_proposition_types` also has an `undef` row. → `propositionClinvarCustom` (it is a
  `Clinvar*` custom type and is already in the custom section's schema `anyOf`).
- **`ClinvarGermlineCustomProposition`:** 0 rows. It is the abstract base the custom types compose, never a
  `type` value. It gets no section. It should also leave the custom section's `anyOf` in the bundle schema
  (today it is listed there, which lets a custom-shaped record with a wrong `type` pass); coordinate with #153,
  which reworks those mixins.
- **VCV/RCV:** there are no VCV/RCV-only types. Diagnostic, Prognostic and TherapeuticResponse never occur
  above SCV; VCV/RCV somatic aggregates use `VariantClinicalSignificanceProposition`, which lands in the same
  group as the SCI SCVs they aggregate.

**Latent gap (fix in this release):** the RCV/VCV statement pointer sites compute the group from
`cpt.gks_type` without the `IFNULL`. A NULL type would hit the `ELSE ERROR`, so it fails loudly today. The new
canonical function (§2.3) takes the same resolved type the dict row carries, so a future Undefined row gets a
consistent pointer.

### 2.2 Names

Existing bundle sections are lowerCamelCase nouns (`sequenceReference`, `copyNumberChange`, `conditionSet`,
`therapyGroup`, `evidenceLine`). The four `*-proposition` keys are the only kebab-case sections, so the reorg
also removes an inconsistency.

| Option | Example | For | Against |
| --- | --- | --- | --- |
| **`proposition<Meaning>`** (proposed) | `propositionPathogenicity` | lowerCamelCase like every other section; sorts together in listings and the R2 browser; `proposition*.parquet` is one glob; a pointer test is `startsWith('#/proposition')` | reads noun-first |
| `<meaning>Proposition` | `pathogenicityProposition` | mirrors the va-spec class names | scatters alphabetically; the glob becomes `*Proposition.parquet` |

**Recommendation:** keep the proposed names: `propositionPathogenicity`, `propositionClinvarCustom`,
`propositionSomaticClinicalImpact`, `propositionOncogenicity`. The Parquet file names equal the section names
(as every other section's do), so `read_parquet('proposition*.parquet')` matches exactly these four and nothing
else.

**Section order in the bundle** (assembler `SECTIONS`, in place of the four current entries):
`propositionPathogenicity`, `propositionOncogenicity`, `propositionSomaticClinicalImpact`,
`propositionClinvarCustom`.

### 2.3 One canonical mapping

Today the type→group CASE is copied verbatim into 11 places (8 proc sites, the NDJSON export, the delta
manifest, the conformance validator) and the Parquet SQL uses four separate `WHERE` filters. Copies can drift,
and the `WHERE` filters silently drop an unmapped type from Parquet while the NDJSON export raises (Parquet-vs-
bundle audit, finding 1).

**Recommendation:** one persistent SQL UDF, versioned in this repo and deployed with the procs:

```sql
-- src/procedures/gkm-proposition-section-func.sql
CREATE OR REPLACE FUNCTION `clinvar_ingest.gkm_proposition_section`(prop_type STRING) AS (
  CASE
    WHEN prop_type = 'VariantPathogenicityProposition' THEN 'propositionPathogenicity'
    WHEN prop_type = 'VariantOncogenicityProposition' THEN 'propositionOncogenicity'
    WHEN prop_type IN ('VariantClinicalSignificanceProposition', 'VariantDiagnosticProposition',
                       'VariantPrognosticProposition', 'VariantTherapeuticResponseProposition')
      THEN 'propositionSomaticClinicalImpact'
    WHEN prop_type IN ('ClinvarNotProvidedProposition', 'ClinvarDrugResponseProposition',
                       'ClinvarOtherProposition', 'ClinvarRiskFactorProposition',
                       'ClinvarAssociationProposition', 'ClinvarAffectsProposition',
                       'ClinvarConflictingDataFromSubmitterProposition', 'ClinvarProtectiveProposition',
                       'ClinvarConfersSensitivityProposition', 'ClinvarUndefinedProposition')
      THEN 'propositionClinvarCustom'
    ELSE ERROR(FORMAT('unmapped proposition type for section mapping: %t', prop_type))
  END
);
```

- The custom list is **explicit** (not `LIKE 'Clinvar%'`), so a new upstream type fails the build instead of
  landing in a section whose schema rejects it.
- Every consumer calls it: the 8 pointer sites, the NDJSON export, the Parquet template's `WHERE`, the delta
  manifest and the validator. In the Parquet export the `WHERE` evaluates the function on every row, so an
  unmapped type raises and fails the export: the same fail-loud behavior as NDJSON.
- It lives under `src/procedures/`, so it is part of `run-release.sh`'s `gate_key`
  (`git log -1 -- src/procedures src/scripts src/vrsify`).
- Belt and braces: the export also asserts that the four sections' row counts sum to the three dicts' total.

---

## 3. Pending decisions

### 3.A Gene-context qualifier: keep it on the proposition (revised)

**Not planned:** moving `submittedGeneSymbols` to the SCV statement, or dropping the placeholder qualifiers.
The user's direction (2026-10-18): propositions must capture the `geneContextQualifier`, because the
submitter's stated gene is the strongest evidence of the gene context of the claim.

- `submittedGeneSymbols` stays an extension on the qualifier.
- The Parquet `submitted_gene_symbols`, `gene_context_id` and `gene_context_name` stay on the proposition
  tables (PR #143 adds them; the shared schema in §4 carries them on all four tables).
- The placeholder qualifiers stay.

**Measured facts** (2026-09-28, 6,736,579 SCV propositions; the six cases sum to the total):

| Case | SCV propositions |
| --- | ---: |
| Submitter's gene equals the qualifier gene | 5,781,673 |
| Submitter gave this gene plus others | 101 |
| Submitter's gene differs from the qualifier gene (top cases are old or renamed symbols for the same gene: GBA→GBA1, MUT→MMUT, C10orf2→TWNK, CENPJ→CPAP) | 27,817 |
| Gene inferred from the variant (`single_gene_variation`); submitter gave none | 881,325 |
| Placeholder: submitter gave a gene, the variant has no single gene (`name` = "submitted genes were not normalized") | 4,814 |
| No qualifier | 40,849 |

**Candidate improvements (the user's to decide):**

- **(a)** a provenance extension on the qualifier: the gene came from the submitter, was inferred, or differs;
- **(b)** the placeholder's `name` set to the submitted symbol verbatim, plus a not-normalized flag, instead of
  the literal "submitted genes were not normalized";
- **(c)** submitter-first selection of the qualifier gene.

VCV/RCV propositions carry no `geneContextQualifier` today (C4 keeps it SCV-only); the shared Parquet columns
are NULL on those rows.

**Does the reorganization affect this?** No. The qualifier lives inside the proposition record; the reorg
changes only which section the record sits in and the pointer prefix. The record and its id are unchanged.

**Timing constraint:** (a), (b) and (c) all change SCV proposition records. Under the single-rebuild rule
they must be decided **before** the rebuild in §6, or deferred to a later release that ships forward-only
(new releases only, no backfill). Deciding one of them after the backfill would force a second backfill.
(a) and (b) are additive or value-only; (c) changes which gene 27,817 propositions name, a semantic change
that would need its own announcement.

**Resolved (2026-10-18): (a) + (b) in this release, (c) deferred.** Implemented in #159 (`1.0`, SCV proc
Step 2), so they ride the single rebuild:

- (a) every `geneContextQualifier` carries a `geneContextSource` extension: `submittedSymbolMatches`,
  `submittedSymbolDiffers`, `inferredFromVariant` or `submittedNotNormalized`. Symbols are compared trimmed and
  case-insensitively, which moves 146 case-only differences (`C19ORF12` vs `C19orf12`) from "differs" to
  "matches". On 2026-09-28 the counts are 5,781,920 / 27,671 / 881,325 / 4,814, plus 40,849 propositions with
  no qualifier.
- (b) the placeholder's `name` is the submitter's symbol. The 5 multi-symbol placeholders join the symbols with
  `", "` in submitted order. There is still no `primaryCoding`, and `submittedGeneSymbols` stays. The
  `submittedNotNormalized` value is the not-normalized flag.
- #159 also gives `submittedGeneSymbols` a total (submitted) order. `ARRAY_AGG(DISTINCT)` had left 45
  multi-symbol lists to flip order between runs. It also trims the leading space our comma split left (`" MEG3"`; 3
  propositions).
- The shared Parquet schema gains `gene_context_source` (§4.1); #143 adds it to the four current tables.

### 3.B Content-shared propositions: defer

**Measured** (memory `project_proposition_content_dedup`, 2026-08-16; and 2026-10-18 notes): VCV and RCV
propositions are about 50% exact-content duplicates; SCV dedup tops out at 10–13%. Today no proposition is
shared at any level (SCV/VCV/RCV are all 1:1 with statements).

**Confirmed in the procs:** the incremental VCV/RCV carry-forward recovers the parent accession from the
proposition key:

- `gkm-vcv-statement-proc.sql:35` (contract) and `:708`, `:710` — `SPLIT(b.key, '-')[OFFSET(0)]` decides which
  baseline rows to carry forward (accession not impacted) and drops rows of removed VCVs;
- `gkm-rcv-statement-proc.sql:38` and `:702`, `:704` — the same for RCVs.

SCV propositions are recomputed globally every release (`gkm-scv-statement-proc.sql` header, Step 7e), so they
do not depend on this parse; the per-SCV outputs parse `clinvar.submission:` ids instead.

**Consequence of content-addressed ids:**

- the VCV/RCV carry-forward breaks: a shared key names no accession, so the merge needs a statement→proposition
  join and reference counting;
- delta tombstones need garbage collection: a shared proposition can be deleted only when no statement uses it;
- the change log sees every proposition key change once (a full churn delta);
- `build-delta-manifest.py` assumes "each key encodes its type code"; `sub-bundle.py` routes propositions by
  key prefix (`SCV`/`VCV`/`RCV`); the bundle schema's `patternProperties` is `^(SCV|VCV|RCV).+`;
- consumers that read the level from the id prefix break.

The size win is small: about 2.9 GB uncompressed, 4.7% of the statement+proposition core, less gzipped.
**Recommendation:** defer, as decided on 2026-09-29. The reorganization keeps ids unchanged, so it neither
helps nor blocks a later dedup.

### 3.C Version label

ADR 0004 §1: renaming sections is breaking (a MAJOR change). §5 allows breaking fixes **in place** in the 1.x
line until GA, announced rather than RFC'd. #142, #145 and #153 already bump the schema strings to `1.0.2`.

| Option | What it means | For | Against |
| --- | --- | --- | --- |
| 1.0.2 in place | keep the strings #142 already set | no extra bump; matches the "1.0.x line" wording | a PATCH must not change valid instances (ADR §1); this renames sections and Parquet tables. §5 speaks of *corrective* fixes; the reorg is a deliberate redesign |
| **1.1.0 in place under `/v1/`** | bump `$id`s, `schema_version` and the bundle schema to 1.1.0 | the most honest label available without leaving `/v1/` (§4 keys directories by MAJOR); consumers pinning a 1.0.x `$id` get a clear signal | still not strict semver (MINOR should be additive); every 1.0.2 string in #142/#145/#153 must be re-bumped |
| 2.0.0 under `/v2/` | the post-GA machinery: parallel 1.x line for 6 months, RFC | strictly correct | contradicts the decision to ship in place now; doubles pipeline and storage for 6 months |

**Recommendation: 1.1.0, in place under `/v1/`.**

- No `1.0.2` tag is cut; the consolidated release is one tag, `1.1.0`, on the `1.0` release branch (the branch
  name stays; it carries the 1.x line).
- Amend #142's version commit to 1.1.0 before it merges, so #145/#153 inherit it.
- Record that §5 also covered a deliberate structural change before GA: a short **ADR 0006** "Propositions
  sectioned by meaning" (supersedes the Phase 2 grouping spec) with a one-line note in ADR 0004's consequences.

**What must be announced (ADR 0004 §6, §7):**

- **Where:** a GitHub Discussions *Announcements* post, the `/v1/feed.xml` Atom entry (`generate-r2-index.sh`
  writes it), release notes, and the CHANGELOG entry (`docs/reference/changelog.md`). The Google Group is on
  hold.
- **When:** an advance notice with the cutover date **before** the R2 overwrite, then a completion notice.
- **What:**
  - the old → new section and table mapping (§7);
  - the pointer change in every statement and evidence line;
  - the Parquet column renames;
  - `schema_version` / `$id` 1.1.0;
  - every published release (4 monthly fulls, `00-latest`, 15 deltas, every Parquet set) rewritten in place,
    so checksums change and earlier downloads should be refreshed;
  - the other data changes riding the same rebuild (A1 HGVS, citations, allele duplicate key, #143, C3, and D).

### 3.D New: normalize VCV `object` and `vcv-` set members (found while measuring)

**Decided (user, 2026-10-18): (i).** It is its own PR, **#160** (branch `fix/uniform-condition-pointers`, base
`1.0`), not part of PR 1–4. The re-wrap is done at emission in `gkm-vcv-statement-proc.sql` (the three `obj_ref`
builds and the synthetic `vcv-` set `concepts`), not in `gkm-vcv-proc.sql`'s `condition_ref`: the `vcv-` id
digest stays over the bare CURIEs, so no `vcv-` id changes, and the `gkm_vcv_*_agg` tables are untouched. On
2026-10-11 it rewrites 7,474,404 VCV propositions and all 94,980 `vcv-` sets; 0 bare references and 0 dangling
pointers remain; the Parquet typed id columns are unchanged. The text below is the original analysis.

The bundle mixes reference forms for the same kind of target:

| Where | Form | Count (2026-10-11) |
| --- | --- | ---: |
| SCV and RCV proposition `object` | `#/condition/…` or `#/conditionSet/…` pointer | all rows |
| VCV proposition `object`, single condition | **bare CURIE** `clinvar.trait:…` / `clinvar.traitset:…` | 7,474,404 of 9,156,181 |
| VCV proposition `object`, several conditions | `#/conditionSet/clinvar.conditionset:vcv-…` pointer | 1,681,777 |
| traitset `ConceptSet` members | `#/condition/` pointers | 5,345 sets (audit) |
| pipeline `vcv-` `ConceptSet` members | bare ids | 83,538 sets (audit) |
| `therapyGroup` members | `#/therapy/` pointers | all |

**Cause:** the 1.0.0 `submittedCondition` de-pointer turned the extension's `condition`/`conditionSet` into bare
CURIEs. The SCV and RCV consumers re-wrap them into pointers; `gkm-vcv-proc.sql` (`vcv_conditions`,
`condition_ref`) does not, so VCV propositions and the synthetic `vcv-` sets carry them bare. Both validate (a
string is a valid `iriReference`), but the bundle schema's description promises `#/<section>/<id>` cross-
references, and a consumer resolving pointers misses 7.5 M VCV objects.

**Options:**

- **(i) Normalize now** (recommended): in `gkm-vcv-proc.sql` wrap `condition_ref` as `#/condition/` +
  `clinvar.trait:` / `#/conditionSet/` + `clinvar.traitset:` (the same re-wrap the SCV/RCV procs use), and build
  the `vcv-` set `concepts` as `#/condition/` pointers. Every VCV row is rewritten in this rebuild anyway, so the
  marginal cost is the review and the oracle. The Parquet `object_id` is bare either way; `object_type` becomes
  pointer-derived.
- **(ii) Leave as is:** the shared Parquet derives `object_type` from the CURIE prefix as a fallback (§4.2).
  Document the mixed forms on Joining Tables.

**Also found:** 4 RCV propositions have **no `object`** (all on `RCV000001117`, since 2026-10-04; 2 Pathogenicity,
2 NotProvided). va-spec requires `object`, so these fail validation in the published 2026-10-04 delta; the
1.0.1 toolkit gate covered only the 2026-10-11 delta and a full. Trace the cause in the RCV proc (likely an RCV
whose condition no longer resolves) before the rebuild, and run the toolkit gate on **every** published bundle
(§6.4).

---

## 4. The shared Parquet schema

### 4.1 Columns

All four tables have exactly these columns, in this order; non-applicable columns are NULL. Each column cites
the bundle path it derives from (user rule: Parquet holds only bundle-derivable values).

| Column | Type | Bundle source | Notes |
| --- | --- | --- | --- |
| `id` | `VARCHAR` | section key (= `$.id`) | unchanged ids |
| `type` | `VARCHAR` | `$.type` | |
| `predicate` | `VARCHAR` | `$.predicate` | |
| `subject_variant_id` | `VARCHAR` | `$.subject`, pointer stripped | was `subject_id` on `varcustom` |
| `object_id` | `VARCHAR` | `$.object`, pointer stripped | was `object_condition_id` / `object_tumor_type_id` / `object_therapy` |
| `object_type` | `VARCHAR` | `$.object` pointer section (CURIE prefix as fallback) | `condition`, `conditionSet`, `therapy`, `therapyGroup` |
| `condition_qualifier_id` | `VARCHAR` | `$.conditionQualifier`, stripped | TherapeuticResponse only |
| `gene_context_id` | `VARCHAR` | `'ncbigene:' ‖ $.geneContextQualifier.primaryCoding.code` | from #143; NULL on placeholders |
| `gene_context_name` | `VARCHAR` | `$.geneContextQualifier.name` | |
| `submitted_gene_symbols` | `VARCHAR[]` | the `submittedGeneSymbols` extension on the qualifier | from #143 |
| `gene_context_source` | `VARCHAR` | the `geneContextSource` extension on the qualifier, picked by name | from #143 / #159 (decision A) |
| `mode_of_inheritance` | `VARCHAR` | `$.modeOfInheritanceQualifier.name` | germline SCV only |
| `penetrance` | `VARCHAR` | `$.penetranceQualifier.name` | germline SCV only |
| `data` | `VARCHAR` | the whole record, `collapse_ext_values` applied | last, as in every table |

**There is no tumor-type section.** Oncogenicity objects are `condition` / `conditionSet` records, so
`object_type` has four values. (`vartumor-proposition.object_tumor_type_id` was already a condition id.)

### 4.2 The template

One schema file replaces the four (`parquet-schemas/proposition.sql`, with a `{SECTION}` placeholder that
`extract_parquet_typed` substitutes). The `data` expression is unchanged from today, so neither strip path moves
(audit note 3: BigQuery `JSON_STRIP_NULLS` drops empty array elements at dict-build time; the assembler's Python
`strip_empty` keeps them; the reorg touches neither).

```sql
-- One shared column schema for every proposition section ({SECTION}). Unions the SCV/RCV/VCV dicts.
-- The WHERE calls the canonical section function, which raises on an unmapped type (fail loud).
SELECT
  key AS id,
  JSON_VALUE(value, '$.type') AS type,
  JSON_VALUE(value, '$.predicate') AS predicate,
  REGEXP_REPLACE(JSON_VALUE(value, '$.subject'), r'^#/[^/]+/', '') AS subject_variant_id,
  REGEXP_REPLACE(JSON_VALUE(value, '$.object'), r'^#/[^/]+/', '') AS object_id,
  CASE
    WHEN JSON_VALUE(value, '$.object') IS NULL THEN NULL
    WHEN STARTS_WITH(JSON_VALUE(value, '$.object'), '#/')
      THEN REGEXP_EXTRACT(JSON_VALUE(value, '$.object'), r'^#/([^/]+)/')
    WHEN STARTS_WITH(JSON_VALUE(value, '$.object'), 'clinvar.trait:') THEN 'condition'
    WHEN STARTS_WITH(JSON_VALUE(value, '$.object'), 'clinvar.traitset:') THEN 'conditionSet'
    ELSE ERROR(FORMAT('unrecognized proposition object: %t', JSON_VALUE(value, '$.object')))
  END AS object_type,
  REGEXP_REPLACE(JSON_VALUE(value, '$.conditionQualifier'), r'^#/[^/]+/', '') AS condition_qualifier_id,
  IF(JSON_VALUE(value, '$.geneContextQualifier.primaryCoding.code') IS NULL, NULL,
     CONCAT('ncbigene:', JSON_VALUE(value, '$.geneContextQualifier.primaryCoding.code'))) AS gene_context_id,
  JSON_VALUE(value, '$.geneContextQualifier.name') AS gene_context_name,
  ARRAY(
    SELECT JSON_VALUE(sym)
    FROM UNNEST(JSON_QUERY_ARRAY(value, '$.geneContextQualifier.extensions')) AS ext,
         UNNEST(JSON_QUERY_ARRAY(ext, '$.value_string')) AS sym WITH OFFSET so
    WHERE JSON_VALUE(ext, '$.name') = 'submittedGeneSymbols'
    ORDER BY so
  ) AS submitted_gene_symbols,
  (
    SELECT JSON_VALUE(ext, '$.value_enum')
    FROM UNNEST(JSON_QUERY_ARRAY(value, '$.geneContextQualifier.extensions')) AS ext
    WHERE JSON_VALUE(ext, '$.name') = 'geneContextSource'
  ) AS gene_context_source,
  JSON_VALUE(value, '$.modeOfInheritanceQualifier.name') AS mode_of_inheritance,
  JSON_VALUE(value, '$.penetranceQualifier.name') AS penetrance,
  collapse_ext_values(TO_JSON_STRING(value)) AS data
FROM (
  SELECT key, value FROM `{DATASET}.gkm_dict_proposition`
  UNION ALL SELECT key, value FROM `{DATASET}.gkm_dict_rcv_proposition`
  UNION ALL SELECT key, value FROM `{DATASET}.gkm_dict_vcv_proposition`
)
WHERE `clinvar_ingest.gkm_proposition_section`(JSON_VALUE(value, '$.type')) = '{SECTION}'
```

- 3.D (i) is decided (#160): drop the two CURIE fallback arms so a non-pointer object fails the export.
- The delta export's `.gkm_dict_` → `.delta_gkm_dict_` rewrite (`export-gkm-dicts.sh:112-118`) works unchanged:
  the template references the three dicts, each with a `delta_` counterpart (the invariant comment as corrected
  by #143 `c4cabeb`).
- `submitted_gene_symbols` is an empty array, not NULL, where there is none (same as #143). Pick one and
  document it; NULL is easier to test and matches "non-applicable columns are NULL".
- Row order is unchanged: the Parquet is not sorted, so row-group pruning is as today. Sorted lookups are C1's
  job (PR #151).

### 4.3 Old → new columns

| Old table.column | New column |
| --- | --- |
| `varcond-proposition.object_condition_id` | `object_id` |
| `vartumor-proposition.object_tumor_type_id` | `object_id` |
| `vartherapy-proposition.object_therapy` | `object_id` |
| `varcustom-proposition.subject_id` | `subject_variant_id` |
| `varcustom-proposition.object_id` | `object_id` |
| `vartherapy-proposition.condition_qualifier_id` | `condition_qualifier_id` (now on every table) |
| — | `object_type` (new) |
| `gene_context_id`, `submitted_gene_symbols` (#143, three of four tables) | same names, all four tables |
| `gene_context_source` (#143, all four tables) | same name, all four tables |
| `mode_of_inheritance`, `penetrance` (varcond, varcustom only) | all four tables |

### 4.4 Optional: `proposition_section` on statement tables (decision E)

`scv`, `vcv`, `rcv` and `evidenceLine` Parquet keep `proposition_id` / `target_proposition_id` as bare ids
(values unchanged). Their `data` column changes, because it holds the record's pointer. A
`proposition_section` column (the pointer's section name; 4 dictionary-encoded values) would tell a query which
one file to read instead of globbing all four. It is bundle-derivable and costs almost nothing.
**Recommendation:** add it in PR 3, or skip it, since the glob already works.

---

## 5. Measurements

### 5.1 Row counts per group

| Section | Level | 2026-09-28 | 2026-10-11 |
| --- | --- | ---: | ---: |
| `propositionPathogenicity` | SCV | 6,692,530 | 6,803,300 |
| | RCV | 11,753,254 | 11,957,075 |
| | VCV | 9,001,288 | 9,078,090 |
| | **total** | **27,447,072** | **27,838,465** |
| `propositionClinvarCustom` | SCV / RCV / VCV | 38,805 / 77,087 / 70,290 | 38,769 / 77,015 / 70,220 |
| | **total** | **186,182** | **186,004** |
| `propositionSomaticClinicalImpact` | SCV (1,752 SCI + 1,521 DIAG + 34 PROG + 13 TR) | 3,320 | 3,320 |
| | RCV / VCV (SCI) | 5,239 / 4,048 | 5,239 / 4,048 |
| | **total** | **12,607** | **12,607** |
| `propositionOncogenicity` | SCV / RCV / VCV | 1,924 / 3,848 / 3,823 | same |
| | **total** | **9,595** | **9,595** |
| **all** | | **27,655,456** | **28,046,671** |

Object types per section (2026-09-28; in brackets, objects that are bare VCV CURIEs, §3.D):

| Section | `condition` | `conditionSet` | `therapy` | `therapyGroup` |
| --- | ---: | ---: | ---: | ---: |
| `propositionPathogenicity` | 24,556,081 (7,051,212) | 2,890,991 (322,134) | — | — |
| `propositionClinvarCustom` | 173,922 (63,628) | 12,260 (3,314) | — | — |
| `propositionSomaticClinicalImpact` | 12,144 (3,598) | 450 | 6 | 7 |
| `propositionOncogenicity` | 9,583 (3,811) | 12 | — | — |

13 rows (the TherapeuticResponse ones) carry a `conditionQualifier`.

### 5.2 Parquet sizes (2026-10 monthly, from 2026-09-28)

The prototype rebuilt the four tables from the published 2026-10 Parquet `data` column alone, with the §4
columns, written by DuckDB (Snappy). Calibration: DuckDB rewriting the *current* files gives
`varcond-proposition` 1,423,086,641 B vs 1,423,042,325 B published (+0.003%) and `varcustom-proposition`
9,935,637 B vs 9,929,590 B (+0.06%), so the estimates are within a fraction of a percent of a BigQuery export.

| New table | Rows | Size | Replaces (published 2026-10) |
| --- | ---: | ---: | --- |
| `propositionPathogenicity` | 27,447,072 | **1.45 GB** (1,447,890,716 B) | `varcond-proposition` 1.42 GB (incl. SCI/DIAG/PROG) |
| `propositionClinvarCustom` | 186,182 | **10.1 MB** | `varcustom-proposition` 9.9 MB |
| `propositionSomaticClinicalImpact` | 12,607 | **0.72 MB** | `vartherapy-proposition` 6.1 KB + 11,029 rows of `varcond` |
| `propositionOncogenicity` | 9,595 | **0.45 MB** | `vartumor-proposition` 0.44 MB |
| **total** | 27,655,456 | **1.459 GB** | 1.433 GB (+1.8%, the new shared columns) |

The 2026-10-11 data would give about 1.47 GB for Pathogenicity (+1.4% rows). The prototype also showed that
`read_parquet('proposition*.parquet')` unions the four with no renaming, and that every column is recomputable
from `data`, i.e. from the bundle record.

---

## 6. Release mechanics

### 6.1 Why a full rebuild

The pointer strings live in the stored statement and evidence-line dicts (`gkm_dict_scv`, `gkm_dict_vcv`,
`gkm_dict_rcv`, `gkm_dict_evidence_line`) of every dataset. Every statement changes, so every published bundle
and every statement and proposition Parquet file changes. The 1.0.2 patch scripts swapped 14 `variation` lines
per full; they cannot rewrite every statement.

A pointer-only SQL rewrite of the four dict tables in 16 datasets would be cheaper, but A1 (catvar), the
citation fix (SCV statement proc), the allele duplicate-key fix and 3.D (VCV proc) need the procs to run anyway.
One proc-level rebuild is simpler to reason about and to oracle-gate. **Recommendation: full rebuild**, the
proven #132 / 1.0.1 path.

### 6.2 Order relative to merging the `1.0` PRs

1. **Settle every data decision:** C (label), 3.A (a)/(b)/(c) or defer, 3.D, E, and any other decision in the
   master plan that changes data (§9).
2. **Merge into `1.0`, in this order** (each rebased on the previous; see §9 for conflicts):
   1. #142: oneOf fix + B2 + A3; amend its version commit to **1.1.0** if C = 1.1.0
   2. #145 (A1 `hgvs.?`)
   3. #153 (B1 strict; retarget from `fix/hgvs-invalid-expressions` to `1.0`)
   4. `fix/allele-duplicate-key` (one duplicate allele key in 10-04 / 10-11) — ideally with total-order
      tie-breakers on the allele `ARRAY_AGG`s (the 1.0.1 non-determinism follow-up), or the rebuild repeats the
      1.0.1 allele oracle exceptions
   5. `fix/scv-citations` (uncommitted today in worktree `scv-citations`, based on the `1.0.1` tag)
   6. #143 (bare ids, typed condition, C2, gene-context columns, plus the Parquet `extensions` placeholder cleanup)
   7. #150 (C3 location ranges)
   8. **PR 1 → PR 2 → PR 3 → PR 4** of this plan (§8), and PR 5 (#160, 3.D)
3. **Do not run a weekly release from `1.0` between these merges and the backfill** (master plan rule): pause
   `run-release.sh` for the window. If ClinVar publishes a new weekly before the rebuild, build it as the 17th
   dataset at the end of §6.3.
4. Merge the paired `main` docs PRs **with** the publish (§8), not before.

### 6.3 Rebuild (BigQuery; each step user-confirmed)

- [ ] Deploy the UDF and every changed proc to `clinvar_ingest` (`bq query < file` for each changed
  `src/procedures/*.sql`).
- [ ] **Snapshot** the published dict tables in each of the 16 datasets
  (`CREATE SNAPSHOT TABLE <ds>.<t>__pre110 CLONE <ds>.<t>`; snapshots bill only changed bytes). They let the
  expected-diff gate (§6.4) prove that only the intended fields changed, and they make a rollback cheap.
- [ ] Rebuild the 16 datasets **in date order**, because each `gkm_change_log` diffs against the previous
  dataset: `clinvar_2026_06_27_v2_5_0`, `07_06`, `07_15`, `07_20`, `07_27`, `08_04`, `08_08`, `08_16`, `08_22`
  (`v2_5_0`), `08_29`, `09_05`, `09_13`, `09_23`, `09_28`, `10_04`, `10_11` (`v2_6_0`). Each:
  `GKS_FULL=true vrs-to-bq-table.sh <date> 3` (catvar, scv-condition, scv-statement, rcv, rcv-statement, vcv,
  vcv-statement, change log, delta build).
- [ ] Re-stamp `gkm_pipeline_version` on 10-11 with the new `gate_key` so the next weekly resumes incremental
  (otherwise it runs one more full build, which is safe but costlier).
- [ ] Re-extract the examples from the rebuilt 10-11 (A1, citations and 3.D change some; the reorg alone does not,
  since examples inline propositions) and re-validate them.

**Estimate**, from the #132 rebuild of the same 16 datasets on 2026-10-11 (`INFORMATION_SCHEMA.JOBS`):

| Item | Per dataset | 16 datasets |
| --- | --- | --- |
| Wall clock (sequential CALLs) | about 11–12 min | **3–4 h** (plus retries) |
| Bytes billed | about 0.21 TiB | **about 3.4 TiB**, ≈ **$21** at on-demand $6.25/TiB |
| Slot time | about 14 slot-h | about 230 slot-h |

### 6.4 Gates (all must pass before any R2 write)

- [ ] **Reference integrity** (`validate-proposition-conformance.sh`, updated in PR 1) on every dataset: each
  pointer's section equals `gkm_proposition_section(<target type>)`; 0 old `-proposition/` pointers; 0 dangling;
  0 unmapped. Make the script **exit non-zero** on any `*_BAD` (it only prints today).
- [ ] **Uniform `#/` references** (`validate-proposition-conformance.sh`, hard gate added in #160) on every
  dataset: 0 bare ids in every reference field (proposition `subject`/`object`/`conditionQualifier`,
  ConceptSet and therapyGroup `concepts`, variation and VRS refs, statement and evidence-line refs). The script
  exits non-zero on any bare value. The `submittedCondition` / `submittedConditionSet` extension strings are
  bare by design and not checked. On 2026-10-11 before #160: 7,811,379 bare (fails); with #160: 0 (passes).
- [ ] **Expected-diff** against the `__pre110` snapshots, per table:
  - proposition dicts: unchanged except the decided 3.A/3.D fields;
  - statement and evidence-line dicts: differ only in the pointer section, plus citations (`scv`) and the 3.D
    VCV objects;
  - `gkm_dict_variation`: only the 14 A1 ids;
  - `gkm_dict_allele`: only the duplicate-key fix.

  The `verify_patch.sh` pattern from `scratchpad/backfill102/` carries over.
- [ ] **Full-vs-incremental oracle** (`oracle-catvar.sh`, `oracle-scv-condition.sh`, `oracle-scv-statement.sh`,
  `oracle-rcv*.sh`, `oracle-vcv*.sh`) on 10-04 → 10-11: 0,0,0.
- [ ] **Delta-reconstruction oracle** (`oracle-delta-reconstruction.sh`) on all 15 consecutive pairs: 0,0,0 on
  all 21 tables. The 1.0.1 exceptions (allele, 08-22→08-29 cross-version SPDI gap; 09-13→09-23 non-
  determinism) must be either fixed by the allele PR or explicitly re-accepted by the user.
- [ ] **Export + assemble to staging only** (no upload; PR 4 adds a `--no-upload` stop to `release-gkm.sh` and
  `release-gkm-delta.sh`): 4 fulls (`2026-07` ← 06-27, `2026-08` ← 08-04, `2026-09` ← 08-29, `2026-10` ← 09-28,
  with `--month-label`) and 15 deltas.
- [ ] **gkm-toolkit `validate_bundle_schema`** on **all** 4 fulls and 15 deltas (not a sample: the 10-04 delta
  carries the 4 object-less RCV propositions, §3.D), with the registry over the whole `schema/` tree.
- [ ] **Bundle ↔ Parquet**: per section, Parquet row count and id set equal the bundle's; the four proposition
  tables' union equals the three dicts; spot-check `data` equals the bundle record.
- [ ] **Published-bundle reconstruction:** full + its deltas == next full (the existing check), on the staged
  bundles.
- [ ] **Re-extract `examples/`** from the rebuilt data, as for 1.0.0 in PR #131. The committed example JSON
  must show the rebuilt shapes, including the gene-context changes (`geneContextSource`, the placeholder name,
  trimmed and ordered `submittedGeneSymbols`), citations, A1 and 3.D. Commit the refresh to `1.0` before the
  tag.

Oracle and gate cost, from 2026-10-12/13: about **2 TiB ≈ $12**, several hours.

### 6.5 Publish (live R2; each step user-confirmed)

- [ ] **Advance announcement** posted (§3.C) with the cutover date.
- [ ] **Back up** every object under `v1/` to `v1/_backup/pre-1.1.0/` with the size-aware server-side copy
  (`.claude/rules/scripts.md`). About 60–80 GB, ≈ $1/month of R2 storage until deleted.
- [ ] **Remove stale section files.** The uploaders wipe only `00-latest/`; dated directories are not wiped, and
  `generate-r2-index.sh` lists a delta's Parquet sections from the R2 listing. Without a delete, every dated
  Parquet directory would keep the four old `var*-proposition.parquet` files beside the new ones and the index
  would list both. Delete them in the 4 monthly sets and the 15 delta `parquet/` directories (PR 4 adds a
  `--replace-sections` wipe to the dated-dir upload).
- [ ] **Upload** the 4 fulls, `00-latest` (server-side copy of 2026-10), the 5 Parquet sets and the 15 delta
  trees; then regenerate `v1/index.json` and `v1/feed.xml`.
- [ ] **CDN purge** (ADR 0005): every overwritten or deleted dated path is cached hard. Purge everything on the
  `clinvar-gkm.org` zone (it serves only this bucket), or purge by URL. **Needs `CF_PURGE_TOKEN` and
  `CF_ZONE_ID` from the user.**
- [ ] **Verify through the CDN:** index lists only the new section names; HEAD every listed file; validate one
  full and the largest delta as downloaded; run the console's example queries.
- [ ] **Tag and merge:** tag `1.1.0` on `1.0`, cut the GitHub Release, confirm the 1.1.0 `$id`s resolve on w3id
  (dynamic rule, no `.htaccess` change); forward-merge `1.0` → `main` with `--no-ff` and move the `dev` tag
  (release-branch policy).
- [ ] Merge the paired `main` docs PRs; post the completion announcement.

### 6.6 Time and cost summary

| Phase | Wall clock | BigQuery |
| --- | --- | --- |
| Rebuild 16 datasets | 3–4 h | ≈ 3.4 TiB |
| Gates and oracles | 4–6 h | ≈ 2 TiB |
| Export + assemble 4 fulls + 15 deltas | 10–12 h (≈ 1.5–2.5 h per full, 15–30 min per delta) | ≈ 0.8 TiB |
| R2 backup, upload, purge, verify | 3–4 h | — |
| **Total** | **≈ 2–3 working days elapsed** | **≈ 6–7 TiB ≈ $40–45** (on-demand) |

Local disk is the tight resource: a monthly full is 4.8 GB and its Parquet set about 12 GB, against about
15 GB free on the build machine. Assemble one full at a time and clear staging between them, or run on a VM.

### 6.7 What the rebuild delivers, and what becomes obsolete

Arrives through the rebuild instead of patching: **A1** (`hgvs.?`; no separate full-mode variant run needed),
the **citation fix**, the **allele duplicate-key fix**, **#143** (bare ids, typed condition, C2, gene-context
columns, extensions cleanup), **C3**, **#142/#153** schema changes, and **3.D** (#160).

Obsolete in `scratchpad/backfill102/`:

- `stage1_patch_datasets.sh`, `gen_variation_patch.py`;
- `stage2_splice_fulls.sh`, `splice_bundle.py`, `variation_lines.py`, `lines_*.json`, `ids.json`;
- `stage3_parquet.sh`;
- `test_patch.sql`, `test_delta.sql`, `dbg.sql`;
- the planned SCV-citation splice.

Worth keeping: the month ↔ dataset `TARGETS` table, the `_backup/pre-…/` backup idiom, and `verify_patch.sh`'s
"differs only on the expected ids" check (reuse in the expected-diff gate).

---

## 7. Migration notes for consumers

### 7.1 Section and table mapping

Proposition **ids do not change**; only the section (bundle key, pointer prefix, Parquet file) does.

| Type (id code) | Old section / table | New section / table |
| --- | --- | --- |
| `VariantPathogenicityProposition` (`PATH`) | `varcond-proposition` | `propositionPathogenicity` |
| `VariantClinicalSignificanceProposition` (`SCI`) | `varcond-proposition` | `propositionSomaticClinicalImpact` |
| `VariantDiagnosticProposition` (`DIAG`) | `varcond-proposition` | `propositionSomaticClinicalImpact` |
| `VariantPrognosticProposition` (`PROG`) | `varcond-proposition` | `propositionSomaticClinicalImpact` |
| `VariantTherapeuticResponseProposition` (`TR`) | `vartherapy-proposition` | `propositionSomaticClinicalImpact` |
| `VariantOncogenicityProposition` (`ONCO`) | `vartumor-proposition` | `propositionOncogenicity` |
| the 9 `Clinvar*` types + `ClinvarUndefinedProposition` (`NP`, `DR`, `OTH`, `RF`, `ASSOC`, `AFF`, `CDFS`, `PROTECT`, `CS`, `UNDEF`) | `varcustom-proposition` | `propositionClinvarCustom` |

Pointers: `#/varcond-proposition/SCV001234567-PATH` → `#/propositionPathogenicity/SCV001234567-PATH`, and so on.
A consumer that resolves pointers generically (`#/<section>/<id>`) needs no code change.

### 7.2 Querying old and new releases together (DuckDB)

Every published release is re-written, so R2 serves only the new layout. Local copies downloaded earlier keep
the old one. Because both layouts keep the full record in `data`, the new shape can be rebuilt from either:

```sql
-- New layout (1.1.0 and later): one glob, one schema.
SELECT * FROM read_parquet('proposition*.parquet');

-- Old layout (local copies from before 1.1.0): rebuild the new shape and section from `data`.
CREATE OR REPLACE MACRO bare(p) AS regexp_replace(p, '^#/[^/]+/', '');
CREATE OR REPLACE VIEW proposition_old AS
SELECT
  j->>'$.id' AS id, j->>'$.type' AS type, j->>'$.predicate' AS predicate,
  bare(j->>'$.subject') AS subject_variant_id,
  bare(j->>'$.object') AS object_id,
  CASE WHEN j->>'$.object' LIKE '#/%' THEN regexp_extract(j->>'$.object', '^#/([^/]+)/', 1)
       WHEN j->>'$.object' LIKE 'clinvar.trait:%' THEN 'condition'
       WHEN j->>'$.object' LIKE 'clinvar.traitset:%' THEN 'conditionSet' END AS object_type,
  bare(j->>'$.conditionQualifier') AS condition_qualifier_id,
  CASE WHEN j->>'$.geneContextQualifier.primaryCoding.code' IS NOT NULL
       THEN 'ncbigene:' || (j->>'$.geneContextQualifier.primaryCoding.code') END AS gene_context_id,
  j->>'$.geneContextQualifier.name' AS gene_context_name,
  CAST(list_filter(CAST(j->'$.geneContextQualifier.extensions' AS JSON[]),
                   lambda e: e->>'$.name' = 'submittedGeneSymbols')[1]->'$.value' AS VARCHAR[]) AS submitted_gene_symbols,
  list_filter(CAST(j->'$.geneContextQualifier.extensions' AS JSON[]),
              lambda e: e->>'$.name' = 'geneContextSource')[1]->>'$.value' AS gene_context_source,
  j->>'$.modeOfInheritanceQualifier.name' AS mode_of_inheritance,
  j->>'$.penetranceQualifier.name' AS penetrance,
  data,
  CASE WHEN j->>'$.type' = 'VariantPathogenicityProposition' THEN 'propositionPathogenicity'
       WHEN j->>'$.type' = 'VariantOncogenicityProposition' THEN 'propositionOncogenicity'
       WHEN j->>'$.type' LIKE 'Clinvar%' THEN 'propositionClinvarCustom'
       ELSE 'propositionSomaticClinicalImpact' END AS section
FROM (
  SELECT data, data::JSON AS j
  FROM read_parquet(['varcond-proposition.parquet', 'varcustom-proposition.parquet',
                     'vartumor-proposition.parquet', 'vartherapy-proposition.parquet'], union_by_name = true)
);
```

(Extensions are picked by `name`: from decision A the qualifier can carry two, so `extensions[0]` is no
longer safe. `lambda e:` needs DuckDB 1.3 or later. `gene_context_source` is NULL in releases before #159.)
The same expressions reproduce the new tables exactly: they are the §5.2 prototype.

### 7.3 Bundle code

- Read proposition sections by prefix: every key starting with `proposition`.
- To migrate stored pointers, replace the section name using the table in §7.1, keyed by the target record's
  `type`.

---

## 8. PR breakdown (merge order)

Code goes to `1.0`; `docs/parquet/` exists only on `main`, so each code PR has a paired `main` docs PR merged in
the publish window. All `1.0` PRs merge just before the rebuild (§6.2).

| # | Base | Title | Contents | Paired docs |
| --- | --- | --- | --- | --- |
| 0 | `main` | this plan | `docs/superpowers/plans/2026-10-18-proposition-reorganization.md` | — |
| 1 | `1.0` | `feat(propositions): canonical section function + meaning-based pointers` | new `src/procedures/gkm-proposition-section-func.sql`; the 8 pointer sites call it; `validate-proposition-conformance.sh` updated and exits non-zero; header comments | D1 |
| 2 | `1.0` | `feat(bundle): proposition sections by meaning + schema 1.1.0` | `export-gkm-dicts.sh` NDJSON groups; `assemble-gkm-dicts.py` `SECTIONS` + `SCHEMA_VERSION`; `build-delta-manifest.py`; `sub-bundle.py`; bundle schema sections + `$id`/const; 4 source YAML `$id`s; `json/` regen (version-only diff; revert `$defs` reorder churn) | D1 |
| 3 | `1.0` | `feat(parquet): one shared proposition schema` | `parquet-schemas/proposition.sql` template replaces the four `var*-proposition.sql`; `extract_parquet_typed` `{SECTION}` substitution + row-count assertion; `extract-example.py` maps `proposition*` sections to the template; optional `proposition_section` (E) on `scv`/`vcv`/`rcv`/`evidenceLine` | D2 |
| 4 | `1.0` | `chore(release): staged republish for the 1.1.0 backfill` | `--no-upload` stop in `release-gkm.sh` / `release-gkm-delta.sh`; dated-dir `--replace-sections` wipe in both uploaders; a `republish-v1.sh` runbook driver (backup → stale delete → upload → index) | D3 |
| 5 | `1.0` | **#160** `fix(vcv-statement): #/ pointers for VCV condition objects and vcv- set members (D)`, branch `fix/uniform-condition-pointers` | `gkm-vcv-statement-proc.sql`: `obj_ref` re-wrap (×3) and synthetic set `concepts` as pointers; `vcv-` digest unchanged | #146 (changelog, ID References, Joining Tables) |
| D1 | `main` | `docs: bundle reference for the proposition sections` | bundle/reference pages, ADR 0006, ADR 0004 note | with 1+2 (+5) |
| D2 | `main` | `docs(parquet): Query the Data for the shared proposition schema` | Query the Data pages, diagrams, console, `r2-browser.js`; folds into or rebases on #146 | with 3 |
| D3 | `main` | `docs: 1.1.0 changelog, versioning, announcement` | changelog, versioning, known-issues, release notes, master-plan update | with the publish |

PR 1 and PR 2 must ship together (pointers must name sections that exist); they are split only for review.
Each `1.0` PR's description names its paired `main` PR.

### 8.1 Touchpoint inventory

| Area | Files | Where |
| --- | --- | --- |
| **Procs** (PR 1, PR 5) | 3 changed + 1 new (+1 for 3.D) | `gkm-scv-statement-proc.sql` evidence-line `targetProposition` `:981-988` and statement `proposition` `:1066-1078`; `gkm-rcv-statement-proc.sql` `:268-276`, `:341-349`, `:419-427`; `gkm-vcv-statement-proc.sql` `:221-229`, `:294-302`, `:372-380` (8 pointer sites); new `gkm-proposition-section-func.sql`; 3.D (#160): `gkm-vcv-statement-proc.sql` `obj_ref` `:533-535`, `:567-569`, `:601-603` and the synthetic-set build. Dict builds unchanged (SCV Step 7e `:880-898`; RCV/VCV `dict_*_proposition_query`). |
| **Export + Parquet SQL** (PR 3) | 6 | `export-gkm-dicts.sh` `PROP_GROUP_CASE` `:133-146`, `export_proposition_group_ndjson` `:172-188`, NDJSON calls `:242-249`, Parquet calls `:286-290`, delta rewrite `:112-118` (no change, verify); `parquet-schemas/var{cond,custom,tumor,therapy}-proposition.sql` → `proposition.sql`; `extract-example.py` (section → schema-file mapping) |
| **Assembler + cleanup** (PR 2) | 1 (+1 verified unchanged) | `assemble-gkm-dicts.py` `SCHEMA_VERSION` `:69`, `SECTIONS` `:87-90`; `gkm_json_cleanup.py` unchanged (strip/collapse untouched) |
| **Delta model / change log** (PR 2, PR 4) | 3 | `build-delta-manifest.py` `TABLE_SECTION` comment + `GROUP_SECTION_CASE` `:36-49` (also drop the vestigial `customPropositionType` COALESCE); `upload-gkm-to-r2.sh`, `upload-gkm-delta-to-r2.sh` (dated-dir wipe). Unchanged: `gkm-change-log-proc.sql`, `gkm-delta-proc.sql` (track dict tables), `generate-r2-index.sh` (lists from R2), `r2-readme.txt` (generic) |
| **Validators** (PR 1, PR 2) | 2 | `validate-proposition-conformance.sh` `:41-95` (pointer regex `^#/([a-z]+)-proposition/` → `^#/(proposition[A-Za-z]+)/`; group CASE → function); `sub-bundle.py` `:67-68` section list and `:117` `section.endswith("-proposition")` → `startswith("proposition")`. Unchanged: `validate-schema-conformance.py` (routes by `type`) |
| **Bundle schema** (PR 2) | 5 sources + regen | `clinvar-gkm-bundle.schema.json` `:175-269` (4 sections; drop `ClinvarGermlineCustomProposition` from the custom `anyOf`) + `$id` `:3` + `schema_version` const `:12`; `$id` in the 4 `*-source.yaml`; `make -C schema/clinvar-gkm`. The bundle schema is hand-maintained (no generator); `y2md.py` and the class-page sync are unaffected |
| **R2 index / manifest** | 0 code | section-agnostic; the dated-dir stale-file issue is handled in PR 4 |
| **Oracles** | 0 | all compare dict tables, which keep their shape; the new expected-diff gate reuses `verify_patch.sh` |
| **Examples** | 0 from the reorg | they inline propositions (no section pointers); refresh after the rebuild for A1/citations/3.D |
| **Docs** (D1–D3) | ≈ 31 | see §8.2 |

### 8.2 Docs touchpoints

- **Bundle and reference (D1):** `docs/index.md` (`:83-86`, `:117`), `getting-started.md` (`:44-47`, `:80`),
  `output-reference/overview.md` (`:25-28`, `:72-77`, `:111-114`), `id-references.md` (`:51-54`, `:76-81`),
  `output-reference/index.md` `:53`, `scv-statements.md` (`:23`, `:132`, `:182`), `vcv-statements.md` (`:21`,
  `:77`), `rcv-statements.md` (`:23`, `:57`), `output-reference/classes/index.md` `:57-60` (hand-written),
  `classes/propositions.md`, `pipeline/export.md` `:79`, `pipeline/sub-bundle.md` (`:125`, `:141`),
  `data-access/index.md` `:93-96`, `data-access/output-files.md` `:124-127`, `data-access/parquet.md` (17 refs),
  `assets/diagrams/bundle-section-map.html`, `assets/presentations/clinvar-gkm-primer.html`, new ADR 0006.
- **Query the Data (D2; line numbers on #146):**
  - `parquet/tables.md`: layer table `:18`, code→table map `:54`, `:80-91`, the four table sections `:341-425`,
    `target_proposition_id` `:480`
  - `parquet/joining.md`: the subject seam `:14-43` and **the varcond-only trap** `:43`, `:178` (the trap mostly
    disappears: Pathogenicity is still the "obvious" table, but SCI/DIAG/PROG move out, so restate the counts),
    the object seam `:47-86` (now `object_type`), statement→proposition seam `:142-178`, prefix box `:256-264`
  - `parquet/recipes.md` (`:56-58`, `:99-101`, `:145-148`, `:199-200`, `:400-403`, `:429-430`): each 3–4-way
    `UNION ALL` collapses to one `read_parquet('proposition*.parquet')`
  - `parquet/performance.md` (`:6`, `:42`, `:99-115`)
  - `assets/diagrams/parquet-join-seams.html` (22), `parquet-table-map.html` (5), `parquet-vcv-levels.html` (5)
  - `assets/duckdb-console.html` `:258` hint
  - `assets/js/r2-browser.js` `:18` `PARQUET_SECTIONS`
  - the tabled `docs/ai-query-guide` branch's `llms*.txt` (if revived)
- **Release (D3):** `reference/changelog.md` (#146's 1.0.2 text describes the patch backfill and `vartherapy`
  re-export; rewrite for 1.1.0), `reference/versioning.md` (stabilization note), `reference/known-issues.md`,
  release notes.
- **README:** generic wording ("propositions"); no change needed. Optionally name the four sections.
- **Unchanged on purpose:** historical plans and specs under `docs/superpowers/` (Phase 2, va-spec migration,
  therapy irirefs, …) and `user-story*.md` stay as records.
- **Master plan (#144):** add the reorg to "What changes published data", replace step 6 (option-2 backfill)
  with §6 here, and mark A1's "full-mode variant run" and option-2 backfill as superseded.
- **C1 plan (#151, worktree `plan-c1`):** text refs `:60`, `:375`, `:612` (decision 7 is moot: the shared schema
  puts `gene_context_id` / `submitted_gene_symbols` on every proposition table), `:644`; its prototype SQL
  (`_statement-core.sql`) reads the dict tables and strips pointers, so it is unaffected, and its `prop` CTE
  should adopt the shared column names (`object_id`, `object_type`, `subject_variant_id`).

---

## 9. Conflicts with open PRs

| PR / branch | Base | Overlap | Action |
| --- | --- | --- | --- |
| #142 oneOf + 1.0.2 | `1.0` | bundle schema, 4 source YAMLs, `json/`, `SCHEMA_VERSION` | merge first; amend version to 1.1.0 (if C); PR 2 rebases |
| #145 A1 | `1.0` | same version strings (contains #142); catvar proc (no overlap) | merge before PR 1–3; rebase conflicts are version-only |
| #153 B1 strict | `fix/hgvs-invalid-expressions` | source YAMLs, `json/`, custom-proposition mixins | retarget to `1.0` after #145; coordinate dropping `ClinvarGermlineCustomProposition` from the bundle `anyOf` |
| #143 Parquet ids | `1.0` | **the four `var*-proposition.sql` files PR 3 deletes**; `export-gkm-dicts.sh` | merge first; PR 3 carries its `gene_context_id` / `submitted_gene_symbols` / bare `object_therapy` logic into the template (direct conflict, resolved by PR 3) |
| #150 C3 | `1.0` | `location.sql` only | none |
| #159 gene context (decision A) | `1.0` | `gkm-scv-statement-proc.sql` Step 2 only; no pointer sites | merge before the rebuild; PR 3's template carries `gene_context_source` (already in §4.2) |
| `fix/scv-citations` | `1.0.1` tag (uncommitted) | `gkm-scv-statement-proc.sql` Step 7b/7c, ~200 lines above the pointer sites | merge before PR 1; PR 1 rebases (shifted lines, low textual risk) |
| `fix/allele-duplicate-key` | `1.0` | catvar proc | none |
| #146 docs 1.0.2 | `main` | **every Query the Data page, the table-map diagram, the console, the changelog** | keep it as the base for D2: rebase D2 on it (or fold D2 into it); its changelog's patch-backfill text must be rewritten |
| #148 console release list | `main` | `duckdb-console.html` | small conflict at the hint line; merge either first |
| #144 master plan | `main` | consolidated-release section | update as in §8.2 |
| #151 C1 plan | `main` | text only | update as in §8.2 |
| #147, #149, #152 | `main` | none | none |

---

## 10. Risks and open questions

**Risks**

1. **Stale sections on R2.** Dated Parquet directories are never wiped, and the index lists sections from the
   R2 listing. Without PR 4's wipe plus the explicit delete, every release would list eight proposition tables
   (four dead). Gate: index section lists equal the expected 22.
2. **Allele non-determinism.** Independent full rebuilds pick different duplicate-key alleles (1.0.1 follow-up),
   which reappears as allele oracle failures and spurious allele changes in republished releases unless the
   tie-breakers land first.
3. **A second rebuild.** Any data decision left open (3.A (c), 3.D, E, C1-driven bundle additions)
   that is taken after the backfill forces another full backfill. Settle them first, or explicitly defer them as
   forward-only.
4. **Weekly releases in the window.** A weekly run from `1.0` after the merges and before the backfill would
   publish the new layout on top of unpatched history. Pause the weekly runs.
5. **Disk and stalls.** About 15 GB free against a 4.8 GB full plus about 12 GB Parquet per monthly set; `bq`
   poll hangs seen in 1.0.1. Run one full at a time with a watchdog.
6. **Consumer breakage.** Every section, table and three column names change, and every published file is
   rewritten. The advance announcement and §7 are the mitigation; the stabilization window is the justification.
7. **Schema-invalid records already published.** The 4 object-less RCV propositions in the 2026-10-04 delta
   (§3.D). The all-bundles toolkit gate catches this class; fix the cause before the rebuild.
8. **Version label churn.** If C = 1.1.0, three open PRs carry `1.0.2`; a missed string makes `$id`s or
   `schema_version` disagree. Gate: `grep -r 1.0.2 schema src` = 0 before tagging.

**Open questions**

1. C: 1.1.0 (recommended) or 1.0.2?
2. ~~3.A: decide (a)/(b)/(c) before the rebuild, or defer them as forward-only?~~ Resolved: (a) + (b) in this
   release (#159), (c) deferred.
3. ~~3.D: normalize VCV objects and `vcv-` set members now (recommended)?~~ Resolved: (i), PR #160
   (`fix/uniform-condition-pointers`).
4. E: add `proposition_section` to the statement Parquet?
5. `submitted_gene_symbols`: empty array (as #143) or NULL when absent?
6. Should the shared schema also carry a derived `statement_level` (`scv`/`vcv`/`rcv`, from the id prefix)?
   `propositionPathogenicity` mixes 27 M rows from three levels; today the level is read from `id`.
7. CDN purge: purge everything on the zone, or purge by URL? Either needs `CF_PURGE_TOKEN` / `CF_ZONE_ID`.
8. R2 backup retention for `v1/_backup/pre-1.1.0/`: how long?
