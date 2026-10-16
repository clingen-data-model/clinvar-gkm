# The 22 Tables

!!! info "Release"
    Counts and sizes on this page are from the **2026-10 monthly release** (published 14 Oct 2026). They change with every release; the queries give you today's numbers.

The Parquet release is **22 tables**, one per bundle section. They fall into six areas that you can learn one at a time. Variants and conditions are the nouns. Propositions say what is claimed about them. Statements say who claimed it, and how confidently.

<iframe src="../assets/diagrams/parquet-table-map.html" style="width:100%; height:760px; border:1px solid rgba(128,128,128,.25); border-radius:6px;" title="ClinVar-GKM Parquet table map" loading="lazy"></iframe>

The map renders at full size in a scrollable frame. Each area has a runnable query you can expand, and each table box links to that table's [column reference](#column-reference) below.

## The six areas

| Area | Tables | The question it answers |
| --- | --- | --- |
| **1 · Variant** | [`variation`](#variation), [`allele`](#allele), [`copyNumberCount`](#copyNumberCount), [`copyNumberChange`](#copyNumberChange), [`location`](#location), [`sequenceReference`](#sequenceReference), [`gene`](#gene) | Which variant is this, and where is it on the genome? |
| **2 · Condition & therapy** | [`condition`](#condition), [`conditionSet`](#conditionSet), [`therapy`](#therapy), [`therapyGroup`](#therapyGroup) | Which disease, tumor type or drug is the claim about? |
| **3 · Proposition** | [`varcond-proposition`](#varcond-proposition), [`varcustom-proposition`](#varcustom-proposition), [`vartumor-proposition`](#vartumor-proposition), [`vartherapy-proposition`](#vartherapy-proposition) | What exactly is being claimed about the variant? |
| **4 · SCV** | [`scv`](#scv), [`evidenceLine`](#evidenceLine), [`submitter`](#submitter) | What did each submitter say, how, and on what evidence? |
| **5 · RCV** | [`rcv`](#rcv), [`rcv_evidenceLine`](#rcv_evidenceLine) | What is ClinVar's combined call for this variant **and this condition**? |
| **6 · VCV** | [`vcv`](#vcv), [`vcv_evidenceLine`](#vcv_evidenceLine) | What is ClinVar's combined call for this variant **across all its conditions**? |

Most questions start in area 1 or 2, go through area 3, and end in one statement area. The [Joining Tables](joining.md) page covers each of those hops. For download links and the release layout, see [Downloads → Parquet Files](../data-access/parquet.md).

## Ids tell you where to look

Every row has an id, and the id's shape names its table. Learn these shapes before writing a join. Several columns can hold more than one kind of id, so the prefix tells you which table to join.

| Id shape | Example | Table |
| --- | --- | --- |
| `clinvar:<n>` | `clinvar:51592` | [`variation`](#variation) |
| `ga4gh:VA.<digest>` | `ga4gh:VA.Apas_jvqBJU7l4DGHGlvTGRY3BBh-UR9` | [`allele`](#allele) |
| `ga4gh:CN.<digest>` | `ga4gh:CN.DRAu4AtQd-hge-7X3WhuN8ZP8Ly3tnZy` | [`copyNumberCount`](#copyNumberCount) |
| `ga4gh:CX.<digest>` | `ga4gh:CX.X1aEdg3zvDBvYfZfupzYACFNXKTi1Yh2` | [`copyNumberChange`](#copyNumberChange) |
| `ga4gh:SL.<digest>` | `ga4gh:SL.PMlrYeTHc_PlcGkq_mRgtJ74aIZvjKCM` | [`location`](#location) |
| `SQ.<digest>` | `SQ.bN6Bx164NNk85Q4z_tOLZunW1BA-4vL_` | [`sequenceReference`](#sequenceReference) |
| `ncbigene:<n>` | `ncbigene:675` | [`gene`](#gene) |
| `clinvar.trait:<n>` | `clinvar.trait:9580` | [`condition`](#condition) |
| `clinvar.traitset:<n>` | `clinvar.traitset:10013` | [`conditionSet`](#conditionSet) (accessioned) |
| `clinvar.conditionset:vcv-<md5>` | `clinvar.conditionset:vcv-50aae75c5e3a7740ab0c2f3ff9ebd970` | [`conditionSet`](#conditionSet) (minted) |
| `clinvar.therapy:<sha256>` | `clinvar.therapy:b150cd67…` | [`therapy`](#therapy) |
| `clinvar.therapygroup:<sha256>` | `clinvar.therapygroup:3595163a…` | [`therapyGroup`](#therapyGroup) |
| `clinvar.submitter:<n>` | `clinvar.submitter:500034` | [`submitter`](#submitter) |
| `clinvar.submission:SCV<n>.<ver>` | `clinvar.submission:SCV000056982.2` | [`scv`](#scv) — and [`evidenceLine`](#evidenceLine), which shares the key |
| `SCV<n>-<CODE>` | `SCV000056982-ASSOC` | a proposition table (a submission's proposition) |
| `VCV<n>-<G\|S>-<CODE>[-<LEVEL>]` | `VCV000051592-G-PATH-CP` | a proposition table (an aggregate's proposition) |
| `VCV<n>.<ver>-<G\|S>-<CODE>[-<LEVEL>]` | `VCV000051592.122-G-PATH-CP` | [`vcv`](#vcv) |
| `RCV<n>.<ver>-<G\|S>-<CODE>[-<LEVEL>]` | `RCV003486676.1-G-PATH-CP` | [`rcv`](#rcv) |
| `<statement id>.contributing` / `.non-contributing` | `VCV000051592.122-G-PATH-NOCP.contributing` | [`vcv_evidenceLine`](#vcv_evidenceLine) / [`rcv_evidenceLine`](#rcv_evidenceLine) |

Two details are easy to miss:

- **A proposition id is its statement's id without the version.** `VCV000051592-G-PATH-CP` is the proposition, and `VCV000051592.122-G-PATH-CP` is the statement about it.
- **A proposition id's classification code names its table.** `PATH`, `SCI`, `DIAG` and `PROG` are in `varcond-proposition`, `ONCO` in `vartumor-proposition`, `TR` in `vartherapy-proposition`, and every other code in `varcustom-proposition` (see the code table under [Reading a variant's statements](#reading-a-variants-statements)). A query that spans several codes is still simplest with one `UNION ALL` of the four tables.

## Where a traversal ends

Five tables are **leaves**: they reference no other table, so a chain of joins stops there.

- [`sequenceReference`](#sequenceReference): the bottom of the variant chain (`variation` → `allele` → `location` → `sequenceReference`).
- [`gene`](#gene): reached from a variant's gene list.
- [`condition`](#condition): reached from a proposition, directly or through a `conditionSet`.
- [`therapy`](#therapy): reached from a therapeutic-response proposition, directly or through a `therapyGroup`.
- [`submitter`](#submitter): reached from an SCV's contributions.

[`scv`](#scv) is a leaf of the *statement* graph: RCV and VCV statements cite SCVs, but an SCV cites no other statement.

## Reading a variant's statements { #reading-a-variants-statements }

A single variant usually has several VCV statements: one per classification type and aggregate level, in a germline lane and sometimes a somatic lane. The statement id encodes all three, as the diagram below shows. It also shows how somatic clinical-impact statements add an evidence-line layer, and which levels contribute to the aggregate call.

<iframe src="../assets/diagrams/parquet-vcv-levels.html" style="width:100%; height:760px; border:1px solid rgba(128,128,128,.25); border-radius:6px;" title="Reading a variant's statements" loading="lazy"></iframe>

The same facts as text. A statement id reads `<accession>.<version>-<lane>-<code>[-<level>]`, for example `VCV000012871.93-G-PATH-CP`.

**Lane and classification code.** The lane is `G` (germline) or `S` (somatic). The code is shorthand for the proposition type, and says which proposition table holds the proposition:

| Lane | Code | Proposition type | Proposition table | Root statements |
| --- | --- | --- | --- | ---: |
| G | `PATH` | `VariantPathogenicityProposition` | `varcond-proposition` | 4,390,392 |
| G | `NP` | `ClinvarNotProvidedProposition` | `varcustom-proposition` | 27,920 |
| G | `DR` | `ClinvarDrugResponseProposition` | `varcustom-proposition` | 2,760 |
| G | `OTH` | `ClinvarOtherProposition` | `varcustom-proposition` | 2,171 |
| G | `RF` | `ClinvarRiskFactorProposition` | `varcustom-proposition` | 1,072 |
| G | `ASSOC` | `ClinvarAssociationProposition` | `varcustom-proposition` | 525 |
| G | `AFF` | `ClinvarAffectsProposition` | `varcustom-proposition` | 331 |
| G | `CDFS` | `ClinvarConflictingDataFromSubmitterProposition` | `varcustom-proposition` | 192 |
| G | `PROTECT` | `ClinvarProtectiveProposition` | `varcustom-proposition` | 99 |
| G | `CS` | `ClinvarConfersSensitivityProposition` | `varcustom-proposition` | 20 |
| S | `ONCO` | `VariantOncogenicityProposition` | `vartumor-proposition` | 1,905 |
| S | `SCI` | `VariantClinicalSignificanceProposition` | `varcond-proposition` | 1,317 |

Root statement counts are VCV roots. An SCV's proposition id uses the same codes without a lane (`SCV000056982-ASSOC`). Somatic clinical impact (`SCI`) also has evidence lines whose `target_proposition_id` names the specific impact: `-TR` (therapeutic response, in `vartherapy-proposition`), `-DIAG` or `-PROG` (in `varcond-proposition`). Their tier is in `evidenceOutcome`: `Level A/B` is Tier I, `Level C/D` is Tier II.

**Aggregate level.** The level suffix matches the `quality.name` of the submissions it groups:

| Level | `quality.name` | Precedence |
| --- | --- | ---: |
| `PG` | practice guidelines | 5 |
| `EP` | expert panel | 4 |
| `CP` | criteria provided | 3 |
| `NOCP` | no assertion criteria provided | 2 |
| `NOCL` | no classification | 1 |
| `FLAG` | flagged | set apart |

A root statement takes its call from the **highest level present**, and the levels below it are marked non-contributing. Which level contributes therefore depends on the variant: a variant whose best submissions are `NOCP` contributes `NOCP`. Two exceptions: `PG` and `EP` **both** contribute when both are present (the practice guideline doesn't mask the expert panel), and flagged submissions never contribute.

## The `data` column { #the-data-column }

Almost every table has a `data` column holding the row's **complete JSON object as a string**, exactly as it appears in the JSON bundle. The typed columns are a convenient, fast subset of it. When a field has no typed column, reach into `data`:

```sql
SELECT id,
       data->>'$.contributions[0].contributor' AS first_contributor
FROM 'scv.parquet'
LIMIT 5;
```

Two things differ inside `data`. References are bundle pointers (`#/submitter/clinvar.submitter:500034`), whereas typed columns carry the bare id (`clinvar.submitter:500034`). And `data` is by far the largest column. Leave it out of your `SELECT` unless you need it; [Working at Scale](performance.md) explains why.

Three tables break the pattern:

- **[`condition`](#condition)** has no `data` column, and its columns are camelCase (`conceptType`, `primaryCoding`), not snake_case.
- **[`therapy`](#therapy)** and **[`therapyGroup`](#therapyGroup)** have just two columns, `key` (the id) and `value` (the JSON object), so there is no `id` or `name`. Read a therapy's name with `value->>'name'`.

## Reading a table remotely

Every table can be queried straight from `https://data.clinvar-gkm.org/v1/datasets/parquet/00-latest/<table>.parquet`, without downloading it. How well that works depends on what you ask:

- **Cheap on any table:** `DESCRIBE`, `count(*)`, and `LIMIT` reads. These touch only the file's footer or its first chunk, so they return in under a second even on the 3 GB `scv.parquet`.
- **Fine on small tables:** full scans of anything up to tens of megabytes (`condition`, `gene`, `submitter`, `therapy`, the somatic propositions).
- **Download first for big tables:** a full scan or `GROUP BY` over `scv`, `variation`, `varcond-proposition`, or the aggregates reads every row group, one request each, in a burst. The CDN rate-limits that with **HTTP 429**, even single-threaded. Download the table once and query it locally. See [Working at Scale](performance.md#local-or-remote).

The sizes in the reference below tell you which category a table is in.

## Column reference { #column-reference }

Every column of every table, from `DESCRIBE` on the release. Types are shown compactly: `STRUCT(a, b)` lists only the top-level fields, and `[]` marks a list. Expand **Full nested types** under a table for the complete DuckDB type, or run `DESCRIBE SELECT * FROM '<table>.parquet'` yourself.

Read a `STRUCT` field with a dot (`classification.name`) and a list with `unnest(…)` or an index (`members[1]`). [Anatomy of a Table](table-anatomy.md) walks through both.

### 1 · Variant

#### `variation` { #variation }

ClinVar's variants, one row per ClinVar Variation id, as Cat-VRS **CategoricalVariant** records. The subject of every proposition. Each row points at the concrete VRS variant(s) that define it.

`variation.parquet` · **4,647,675** rows · 4.1 GB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `clinvar:<variation id>`, e.g. `clinvar:51592`. |
| `type` | `VARCHAR` | Always `CategoricalVariant`. |
| `name` | `VARCHAR` | ClinVar's preferred name, e.g. `NM_000059.4(BRCA2):c.4090A>C (p.Ile1364Leu)`. |
| `extensions` | `STRUCT(name, value_string, value_boolean, value_coding, value_hgvs_array, value_gene_array)[]` | Named ClinVar attributes, each `{name, value_*}` with the one `value_*` field matching its kind populated: `clinvarVariationType`, `clinvarSubclassType`, `definingVrsVariationType`, `categoricalVariationType`, `clinvarCytogeneticLocation`, `clinvarHgvsList` (→ `value_hgvs_array`), `clinvarGeneList` (→ `value_gene_array`, whose `.gene` is a `#/gene/ncbigene:…` pointer), and VRS processing notes (`vrsProcessingException`, `vrsPreProcessingIssue`). |
| `mappings` | `STRUCT(coding, relation)[]` | Identifiers for this variant in other systems: `{coding{system, code, iris}, relation}`. Always the ClinVar id (`exactMatch`); often dbSNP and ClinGen Allele Registry; sometimes dbVar, OMIM, UniProt, and locus-specific databases. |
| `members` | `VARCHAR[]` | VRS ids of the concrete variants that are members of this category — `ga4gh:VA.` → `allele`, `ga4gh:CN.` → `copyNumberCount`, `ga4gh:CX.` → `copyNumberChange`. |
| `constraints` | `STRUCT(type, allele, location, copies, copyChange, matchCharacteristic, relations)[]` | Cat-VRS constraints that define the category: `DefiningAlleleConstraint` (`.allele`), `DefiningLocationConstraint` (`.location`), `CopyCountConstraint` (`.copies`), `CopyChangeConstraint` (`.copyChange`); `.relations` lists allowed relations such as `liftover_to`, `transcribed_to`. |
| `data` | `VARCHAR` | Full JSON object as a string — see [The `data` column](#the-data-column). |

??? note "Full nested types — `variation`"
    ```text
    extensions  STRUCT("name" VARCHAR, value_string VARCHAR, value_boolean BOOLEAN, value_coding BIGINT, value_hgvs_array STRUCT(nucleotideExpression STRUCT(syntax VARCHAR, "value" VARCHAR), nucleotideType VARCHAR, maneSelect BOOLEAN, manePlus BOOLEAN, proteinExpression STRUCT(syntax VARCHAR, "value" VARCHAR), molecularConsequence STRUCT(code VARCHAR, "system" VARCHAR, "name" VARCHAR, iris VARCHAR[])[])[], value_gene_array STRUCT(gene VARCHAR, relationship_type VARCHAR, "source" VARCHAR)[])[]
    mappings  STRUCT(coding STRUCT("system" VARCHAR, code VARCHAR, iris VARCHAR[]), relation VARCHAR)[]
    constraints  STRUCT("type" VARCHAR, allele VARCHAR, "location" VARCHAR, copies BIGINT, copyChange VARCHAR, matchCharacteristic STRUCT("type" VARCHAR, primaryCoding STRUCT(code VARCHAR, "system" VARCHAR, iris VARCHAR[])), relations STRUCT("type" VARCHAR, primaryCoding STRUCT(code VARCHAR, "system" VARCHAR, iris VARCHAR[]))[])[]
    ```

#### `allele` { #allele }

VRS **Allele** records — a specific sequence change at a location. Reached from `variation.members[]` / `constraints[].allele` (`ga4gh:VA.` prefix).

`allele.parquet` · **4,554,562** rows · 1.1 GB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `ga4gh:VA.<digest>` — the GA4GH computed identifier. |
| `type` | `VARCHAR` | Always `Allele`. |
| `digest` | `VARCHAR` | The digest part of the id (the id without `ga4gh:VA.`). |
| `name` | `VARCHAR` | An HGVS expression for the allele, e.g. `NC_000016.10:g.376236G>A`. |
| `location_id` | `VARCHAR` | `ga4gh:SL.…` → `location.id`. |
| `data` | `VARCHAR` | Full JSON object as a string — see [The `data` column](#the-data-column). |

#### `copyNumberCount` { #copyNumberCount }

VRS **CopyNumberCount** records — an absolute copy count over a region (`ga4gh:CN.` prefix).

`copyNumberCount.parquet` · **47,453** rows · 8.7 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `ga4gh:CN.<digest>`. |
| `type` | `VARCHAR` | Always `CopyNumberCount`. |
| `digest` | `VARCHAR` | The digest part of the id. |
| `copies` | `BIGINT` | The absolute copy number (`0`–`7` in this release). |
| `location_id` | `VARCHAR` | `ga4gh:SL.…` → `location.id`. |
| `data` | `VARCHAR` | Full JSON object as a string — see [The `data` column](#the-data-column). |

#### `copyNumberChange` { #copyNumberChange }

VRS **CopyNumberChange** records — a relative copy gain or loss over a region (`ga4gh:CX.` prefix).

`copyNumberChange.parquet` · **31,717** rows · 5.8 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `ga4gh:CX.<digest>`. |
| `type` | `VARCHAR` | Always `CopyNumberChange`. |
| `digest` | `VARCHAR` | The digest part of the id. |
| `copy_change` | `VARCHAR` | `gain` or `loss`. |
| `location_id` | `VARCHAR` | `ga4gh:SL.…` → `location.id`. |
| `data` | `VARCHAR` | Full JSON object as a string — see [The `data` column](#the-data-column). |

#### `location` { #location }

VRS **SequenceLocation** records — a span on a reference sequence, shared by alleles and copy-number variants.

`location.parquet` · **4,177,664** rows · 611.7 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `ga4gh:SL.<digest>`. |
| `type` | `VARCHAR` | Always `SequenceLocation`. |
| `digest` | `VARCHAR` | The digest part of the id. |
| `loc_start` | `BIGINT` | Start coordinate (0-based, interbase). NULL when the start is an uncertain range — the range is in `data` as `"start": [min, max]`. |
| `loc_end` | `BIGINT` | End coordinate (interbase). NULL when the end is an uncertain range. |
| `sequence_reference_id` | `VARCHAR` | `SQ.…` → `sequenceReference.id`. |
| `data` | `VARCHAR` | Full JSON object as a string — see [The `data` column](#the-data-column). |

#### `sequenceReference` { #sequenceReference }

The reference sequences locations are placed on — RefSeq chromosomes, transcripts, and other sequences, keyed by their GA4GH refget id. A **leaf**: it references nothing.

`sequenceReference.parquet` · **215** rows · 29.1 KB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `SQ.<digest>` — the refget accession (note: no `ga4gh:` prefix). |
| `type` | `VARCHAR` | Always `SequenceReference`. |
| `refget_accession` | `VARCHAR` | Same value as `id`. |
| `name` | `VARCHAR` | The RefSeq accession, e.g. `NC_000017.11`, `NM_000059.4`. |
| `molecule_type` | `VARCHAR` | `genomic`, `mRNA`, or `RNA`. |
| `residue_alphabet` | `VARCHAR` | `na` (nucleic acid). |
| `data` | `VARCHAR` | Full JSON object as a string — see [The `data` column](#the-data-column). |

#### `gene` { #gene }

Genes referenced by variants' gene lists, keyed by NCBI Gene id. A **leaf**.

`gene.parquet` · **92,972** rows · 5.4 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `ncbigene:<n>`, e.g. `ncbigene:675` (BRCA2). |
| `concept_type` | `VARCHAR` | Always `gene`. |
| `name` | `VARCHAR` | The gene symbol, e.g. `BRCA2`. |
| `data` | `VARCHAR` | Full JSON object as a string; adds `primaryCoding` (the NCBI Gene coding). |

### 2 · Condition & therapy

#### `condition` { #condition }

ClinVar's conditions (traits) — diseases, phenotypes, findings — one row per ClinVar trait. The object of most propositions. A **leaf**. **No `data` column, and camelCase column names** (`conceptType`, `primaryCoding`), unlike the other tables.

`condition.parquet` · **23,162** rows · 2.0 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `clinvar.trait:<n>`, e.g. `clinvar.trait:9580`. |
| `type` | `VARCHAR` | Always `MappableConcept`. |
| `conceptType` | `VARCHAR` | `Disease`, `Phenotype`, `Trait`, or `Condition`. |
| `name` | `VARCHAR` | Preferred name, e.g. `Hereditary spastic paraplegia 48`. |
| `aliases` | `VARCHAR[]` | Alternate names. |
| `primaryCoding` | `STRUCT(name, code, system, iris)` | The MedGen coding: `{name, code, system, iris}`; `primaryCoding.code` is the MedGen CUI (e.g. `C3150901`). |
| `mappings` | `STRUCT(coding, relation)[]` | Cross-references `{coding{name, code, system, iris}, relation}` — MONDO, Orphanet, OMIM, HPO, and others. |

??? note "Full nested types — `condition`"
    ```text
    primaryCoding  STRUCT("name" VARCHAR, code VARCHAR, "system" VARCHAR, iris VARCHAR[])
    mappings  STRUCT(coding STRUCT("name" VARCHAR, code VARCHAR, "system" VARCHAR, iris VARCHAR[]), relation VARCHAR)[]
    ```

#### `conditionSet` { #conditionSet }

Sets of conditions a single proposition is about. Two kinds of row share the table: **accessioned** ClinVar TraitSets (`clinvar.traitset:`) and sets **minted** for VCV-level aggregates (`clinvar.conditionset:vcv-…`).

`conditionSet.parquet` · **88,883** rows · 9.7 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `clinvar.traitset:<n>` (accessioned) or `clinvar.conditionset:vcv-<md5>` (minted). |
| `type` | `VARCHAR` | Always `ConceptSet`. |
| `conceptSetType` | `VARCHAR` | For TraitSets, ClinVar's set type — `Disease`, `Finding`, `TraitChoice`, `DrugResponse`. NULL on minted sets. |
| `membershipOperator` | `VARCHAR` | `AND` (all members together) or `OR` (any member). Minted sets are `OR`. |
| `concepts` | `VARCHAR[]` | Member **ids**, not names — `clinvar.trait:` ids, and on minted sets possibly a nested `clinvar.traitset:`. Re-join to `condition` (see [Joining → Seam B](joining.md)). |
| `data` | `VARCHAR` | Full JSON object as a string — see [The `data` column](#the-data-column). |

#### `therapy` { #therapy }

Drug therapies named by therapeutic-response propositions. A **leaf**. **A two-column key/value table**: there are no `id` or `name` columns.

`therapy.parquet` · **38** rows · 4.0 KB

| Column | Type | Description |
| --- | --- | --- |
| `key` | `VARCHAR` | The therapy id, `clinvar.therapy:<sha256>` (content-addressed). |
| `value` | `VARCHAR` | The JSON object as a string: `{conceptType: "Drug", name, type}`. Read the name with `value->>'name'`. |

#### `therapyGroup` { #therapyGroup }

Combination therapies — a set of `therapy` members. Same key/value shape as `therapy`; its members exist only inside the JSON `value`.

`therapyGroup.parquet` · **10** rows · 4.9 KB

| Column | Type | Description |
| --- | --- | --- |
| `key` | `VARCHAR` | The group id, `clinvar.therapygroup:<sha256>`. |
| `value` | `VARCHAR` | The JSON object as a string: `{type, membershipOperator, concepts}`, where `concepts` is a list of `#/therapy/clinvar.therapy:…` pointers. |

### 3 · Proposition

#### `varcond-proposition` { #varcond-proposition }

Variant × condition propositions — the claim a germline or somatic classification is about: **pathogenicity** (`VariantPathogenicityProposition`, 99.9 % of rows), somatic **clinical significance**, **diagnostic**, and **prognostic**. The 1,555 diagnostic and prognostic rows are SCI evidence-line targets, so no statement classifies them directly.

`varcond-proposition.parquet` · **27,459,666** rows · 1.4 GB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `SCV<n>-<CODE>` for a submission's proposition; `VCV<n>-<G|S>-<CODE>[-<LEVEL>]` or `RCV…` for an aggregate's — e.g. `VCV000051592-G-PATH-CP`. Matches the `proposition_id` of at most one statement. |
| `type` | `VARCHAR` | The proposition class, e.g. `VariantPathogenicityProposition`. |
| `predicate` | `VARCHAR` | The relation, e.g. `isCausalFor`, `hasClinicalSignificanceFor`, `isDiagnosticInclusionCriterionFor`, `associatedWithBetterOutcomeFor`. |
| `subject_variant_id` | `VARCHAR` | `clinvar:<n>` → `variation.id`. |
| `object_condition_id` | `VARCHAR` | **Prefix-dispatched**: `clinvar.trait:` → `condition.id`; `clinvar.traitset:` or `clinvar.conditionset:` → `conditionSet.id`. |
| `gene_context_name` | `VARCHAR` | Gene symbol the submitter named as context for the claim (e.g. `EGFR`), or NULL. A natural key, not an id — symbols are not unique; join genes by `ncbigene:` id instead. |
| `mode_of_inheritance` | `VARCHAR` | Mode-of-inheritance qualifier (e.g. `Autosomal dominant inheritance`), or NULL. |
| `penetrance` | `VARCHAR` | Penetrance qualifier, or NULL. |
| `data` | `VARCHAR` | Full JSON object as a string — see [The `data` column](#the-data-column). |

#### `varcustom-proposition` { #varcustom-proposition }

Variant × condition propositions for ClinVar's **non-pathogenicity germline** classifications, which have no standard VA-Spec proposition: not provided, drug response, risk factor, association, affects, protective, confers sensitivity, other, conflicting data from submitters.

`varcustom-proposition.parquet` · **186,182** rows · 9.9 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `SCV<n>-<CODE>` for a submission's proposition; `VCV<n>-<G|S>-<CODE>[-<LEVEL>]` or `RCV…` for an aggregate's — e.g. `VCV000009525-G-AFF`. Matches the `proposition_id` of at most one statement. |
| `type` | `VARCHAR` | The ClinVar custom proposition class, e.g. `ClinvarRiskFactorProposition`. |
| `predicate` | `VARCHAR` | The relation, e.g. `isRiskFactorFor`, `hasDrugResponseFor`. |
| `subject_id` | `VARCHAR` | `clinvar:<n>` → `variation.id`. (Spelled `subject_id` here, `subject_variant_id` in the other three.) |
| `object_id` | `VARCHAR` | **Prefix-dispatched**, same as `varcond-proposition.object_condition_id`. |
| `gene_context_name` | `VARCHAR` | Gene symbol the submitter named as context for the claim (e.g. `EGFR`), or NULL. A natural key, not an id — symbols are not unique; join genes by `ncbigene:` id instead. |
| `mode_of_inheritance` | `VARCHAR` | Mode-of-inheritance qualifier (e.g. `Autosomal dominant inheritance`), or NULL. |
| `penetrance` | `VARCHAR` | Penetrance qualifier, or NULL. |
| `data` | `VARCHAR` | Full JSON object as a string — see [The `data` column](#the-data-column). |

#### `vartumor-proposition` { #vartumor-proposition }

Variant × tumor-type propositions — somatic **oncogenicity** claims.

`vartumor-proposition.parquet` · **9,595** rows · 436.4 KB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `SCV<n>-<CODE>` for a submission's proposition; `VCV<n>-<G|S>-<CODE>[-<LEVEL>]` or `RCV…` for an aggregate's — e.g. `VCV003897731-S-ONCO-CP`. Matches the `proposition_id` of at most one statement. |
| `type` | `VARCHAR` | Always `VariantOncogenicityProposition`. |
| `predicate` | `VARCHAR` | `isOncogenicFor`. |
| `subject_variant_id` | `VARCHAR` | `clinvar:<n>` → `variation.id`. |
| `object_tumor_type_id` | `VARCHAR` | The tumor type. **Prefix-dispatched**: almost always a `clinvar.trait:` → `condition.id`, but 12 rows name a `clinvar.conditionset:` → `conditionSet.id`. |
| `gene_context_name` | `VARCHAR` | Gene symbol the submitter named as context for the claim (e.g. `EGFR`), or NULL. A natural key, not an id — symbols are not unique; join genes by `ncbigene:` id instead. |
| `data` | `VARCHAR` | Full JSON object as a string — see [The `data` column](#the-data-column). |

#### `vartherapy-proposition` { #vartherapy-proposition }

Variant × therapy propositions — somatic **therapeutic response**. These are the specific-impact targets of SCI evidence lines; no statement classifies one directly.

`vartherapy-proposition.parquet` · **13** rows · 6.1 KB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `SCV<n>-<CODE>` for a submission's proposition; `VCV<n>-<G|S>-<CODE>[-<LEVEL>]` or `RCV…` for an aggregate's — e.g. `SCV004565359-TR`. Matches the `proposition_id` of at most one statement. |
| `type` | `VARCHAR` | Always `VariantTherapeuticResponseProposition`. |
| `predicate` | `VARCHAR` | `predictsSensitivityTo` or `predictsResistanceTo`. |
| `subject_variant_id` | `VARCHAR` | `clinvar:<n>` → `variation.id`. |
| `condition_qualifier_id` | `VARCHAR` | The tumor/condition context, `clinvar.trait:` → `condition.id`. |
| `object_therapy` | `VARCHAR` | A **JSON-quoted pointer**, not a bare id: `"#/therapy/clinvar.therapy:…"` or `"#/therapyGroup/clinvar.therapygroup:…"`. Strip the quotes and the `#/<section>/` prefix to join `therapy.key` / `therapyGroup.key`. |
| `gene_context_name` | `VARCHAR` | Gene symbol the submitter named as context for the claim (e.g. `EGFR`), or NULL. A natural key, not an id — symbols are not unique; join genes by `ncbigene:` id instead. |
| `data` | `VARCHAR` | Full JSON object as a string — see [The `data` column](#the-data-column). |

### 4 · SCV

#### `scv` { #scv }

**SCV** statements — each submitter's classification of a variant, one row per ClinVar submission (SCV accession). The leaves every aggregate cites.

`scv.parquet` · **6,735,011** rows · 3.1 GB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `clinvar.submission:SCV<n>.<ver>`, e.g. `clinvar.submission:SCV000056982.2`. |
| `type` | `VARCHAR` | Always `Statement`. |
| `classification` | `STRUCT(type, conceptType, name, primaryCoding, extensions)` | MappableConcept; `classification.name` is the submitted call (e.g. `Pathogenic`, `Likely benign`) — **not case-normalized**. `classification.extensions` may carry the submitter's `description`. |
| `strength` | `STRUCT(type, conceptType, name, primaryCoding)` | MappableConcept; `strength.name` is `Definitive`, `Likely`, `Strong`, `Potential`, or NULL. |
| `direction` | `VARCHAR` | `supports`, `disputes`, or `neutral` — the direction of the classification relative to the proposition (e.g. a *Benign* call `disputes` a pathogenicity proposition). |
| `quality` | `STRUCT(type, conceptType, name)` | MappableConcept; `quality.name` is the submission level — `practice guidelines`, `expert panel`, `criteria provided`, `no assertion criteria provided`, `no classification`, or `flagged`. |
| `description` | `VARCHAR` | The submitter's free-text comment on the classification, or NULL. |
| `specifiedBy` | `STRUCT(type, methodType, name, reportedIn)` | The method: `methodType` (ClinVar collection method — `clinical testing`, `curation`, `research`, …), `name` (the assertion criteria, e.g. ACMG guidelines), and `reportedIn` (the criteria document). |
| `reportedIn` | `STRUCT(type, pmid, doi, urls)[]` | Citations supporting the submission — each `{pmid, doi, urls}`. |
| `extensions` | `STRUCT(name, value_string, value_submitted_condition_set, value_submitted_condition)[]` | Named ClinVar attributes: `clinvarScvId`, `clinvarScvVersion`, `clinvarScvReviewStatus`, `submissionLevel`, `submittedScvLocalKey`, `submittedScvClassification`, and the submitter's original condition (`submittedCondition` → `value_submitted_condition`, or `submittedConditionSet` → `value_submitted_condition_set`) with its MedGen mapping. |
| `proposition_id` | `VARCHAR` | The proposition this statement classifies. Its classification code names the proposition table (see [Reading a variant's statements](#reading-a-variants-statements)); to cover every code, join the four-table union ([Joining → Seam C](joining.md#seam-c-proposition-statements-1-1)). One statement per proposition. |
| `contributions` | `STRUCT(type, contributor, date, activityType)[]` | `{contributor, date, activityType}` — `contributor` is a `clinvar.submitter:` id → `submitter.id`; `activityType` is `submitted`, `created`, or `evaluated`. |
| `has_evidence_lines` | `VARCHAR[]` | Ids of this statement's evidence lines in `evidenceLine`. |
| `data` | `VARCHAR` | Full JSON object as a string — see [The `data` column](#the-data-column). |

??? note "Full nested types — `scv`"
    ```text
    classification  STRUCT("type" VARCHAR, conceptType VARCHAR, "name" VARCHAR, primaryCoding STRUCT(code VARCHAR, "system" VARCHAR), "extensions" STRUCT("name" VARCHAR, value_string VARCHAR)[])
    strength  STRUCT("type" VARCHAR, conceptType VARCHAR, "name" VARCHAR, primaryCoding STRUCT(code VARCHAR, "system" VARCHAR))
    quality  STRUCT("type" VARCHAR, conceptType VARCHAR, "name" VARCHAR)
    specifiedBy  STRUCT("type" VARCHAR, methodType VARCHAR, "name" VARCHAR, reportedIn STRUCT("type" VARCHAR, pmid VARCHAR, doi VARCHAR, urls VARCHAR[]))
    reportedIn  STRUCT("type" VARCHAR, pmid VARCHAR, doi VARCHAR, urls VARCHAR[])[]
    extensions  STRUCT("name" VARCHAR, value_string VARCHAR, value_submitted_condition_set STRUCT(conditionSet VARCHAR, condition VARCHAR, multiple_condition_explanation VARCHAR, concepts STRUCT(id VARCHAR, "name" VARCHAR, "type" VARCHAR, medgen_id VARCHAR, xrefs STRUCT(code VARCHAR, "system" VARCHAR)[], original_medgen_match STRUCT(id VARCHAR, "name" VARCHAR), direct_match VARCHAR, normalized_match VARCHAR, normalized_resolution VARCHAR, "mapping" STRUCT("type" VARCHAR, "ref" VARCHAR, "value" VARCHAR))[]), value_submitted_condition STRUCT(conditionSet VARCHAR, condition VARCHAR, id VARCHAR, "name" VARCHAR, "type" VARCHAR, medgen_id VARCHAR, xrefs STRUCT(code VARCHAR, "system" VARCHAR)[], original_medgen_match STRUCT(id VARCHAR, "name" VARCHAR), direct_match VARCHAR, normalized_match VARCHAR, normalized_resolution VARCHAR, "mapping" STRUCT("type" VARCHAR, "ref" VARCHAR, "value" VARCHAR)))[]
    contributions  STRUCT("type" VARCHAR, contributor VARCHAR, date DATE, activityType VARCHAR)[]
    ```

#### `evidenceLine` { #evidenceLine }

SCV-level evidence lines — used only by somatic **clinical impact (SCI)** submissions. Each points at the specific impact (therapeutic response, diagnostic, prognostic) and carries its AMP/ASCO/CAP tier.

`evidenceLine.parquet` · **1,568** rows · 150.1 KB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | **Shares its primary key with `scv`**: the id is the SCV's own id, `clinvar.submission:SCV<n>.<ver>`. |
| `type` | `VARCHAR` | Always `EvidenceLine`. |
| `directionOfEvidenceProvided` | `VARCHAR` | `supports` / `disputes` / `neutral`. |
| `evidenceOutcome` | `STRUCT(type, conceptType, name)` | MappableConcept; `.name` is `Level A/B` (Tier I) or `Level C/D` (Tier II). |
| `extensions` | `STRUCT(name, value_submitted_condition_set, value_submitted_condition)[]` | The submitter's original condition (`submittedCondition`), same shape as on `scv`. |
| `target_proposition_id` | `VARCHAR` | The specific-impact proposition: `…-DIAG` / `…-PROG` → `varcond-proposition`, `…-TR` → `vartherapy-proposition`. |
| `data` | `VARCHAR` | Full JSON object as a string — see [The `data` column](#the-data-column). |

??? note "Full nested types — `evidenceLine`"
    ```text
    evidenceOutcome  STRUCT("type" VARCHAR, conceptType VARCHAR, "name" VARCHAR)
    extensions  STRUCT("name" VARCHAR, value_submitted_condition_set STRUCT(conditionSet VARCHAR, condition VARCHAR, multiple_condition_explanation VARCHAR, concepts STRUCT(id VARCHAR, "name" VARCHAR, "type" VARCHAR, medgen_id VARCHAR, xrefs STRUCT(code VARCHAR, "system" VARCHAR)[], original_medgen_match STRUCT(id VARCHAR, "name" VARCHAR), direct_match VARCHAR, normalized_match VARCHAR, normalized_resolution VARCHAR, "mapping" STRUCT("type" VARCHAR, "ref" VARCHAR, "value" VARCHAR))[]), value_submitted_condition STRUCT(conditionSet VARCHAR, condition VARCHAR, id VARCHAR, "name" VARCHAR, "type" VARCHAR, medgen_id VARCHAR, xrefs STRUCT(code VARCHAR, "system" VARCHAR)[], original_medgen_match STRUCT(id VARCHAR, "name" VARCHAR), direct_match VARCHAR, normalized_match VARCHAR, normalized_resolution VARCHAR, "mapping" STRUCT("type" VARCHAR, "ref" VARCHAR, "value" VARCHAR)))[]
    ```

#### `submitter` { #submitter }

The organizations that submit to ClinVar. A **leaf**, referenced from `scv.contributions[].contributor`.

`submitter.parquet` · **3,532** rows · 273.0 KB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `clinvar.submitter:<n>` — ClinVar's organization id. |
| `type` | `VARCHAR` | Always `Agent`. |
| `name` | `VARCHAR` | The organization name. |
| `data` | `VARCHAR` | Full JSON object as a string — see [The `data` column](#the-data-column). |

### 5 · RCV

#### `rcv` { #rcv }

**RCV** aggregate statements — ClinVar's rollup of SCVs for one variant **and one condition**. Each RCV accession yields a root statement plus one statement per contributing level.

`rcv.parquet` · **11,839,428** rows · 847.1 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `RCV<n>.<ver>-<G|S>-<CODE>[-<LEVEL>]`, e.g. `RCV003486676.1-G-PATH-CP`. A **root** id stops at the classification code; a **level** id adds `-PG`, `-EP`, `-CP`, `-NOCP`, `-NOCL`, or `-FLAG` (somatic clinical impact adds a tier, `-T1`/`-T2`). See [Reading a variant's statements](#reading-a-variants-statements). |
| `type` | `VARCHAR` | Always `Statement`. |
| `direction` | `VARCHAR` | `supports`, `disputes`, or `neutral` — the direction of the classification relative to the proposition (e.g. a *Benign* call `disputes` a pathogenicity proposition). |
| `strength` | `STRUCT(type, conceptType, name)` | MappableConcept; `strength.name` is e.g. `Definitive`, or NULL. |
| `quality` | `STRUCT(type, conceptType, name)` | MappableConcept; `quality.name` is the aggregate level — `practice guidelines`, `expert panel`, `criteria provided`, `no assertion criteria provided`, `no classification`, or `flagged`. |
| `classification` | `STRUCT(type, conceptType, name, extensions)` | MappableConcept; `classification.name` is the aggregate call (e.g. `Pathogenic`, `Benign/Likely benign`, `Conflicting classifications of pathogenicity`). `classification.extensions` carries `conflictingExplanation` when the call is a conflict. |
| `extensions` | `STRUCT(name, value)[]` | `{name, value}` pairs; today one: `clinvarReviewStatus` — ClinVar's review-status text (e.g. `criteria provided, multiple submitters, no conflicts`). |
| `proposition_id` | `VARCHAR` | The proposition this statement classifies. Its classification code names the proposition table (see [Reading a variant's statements](#reading-a-variants-statements)); to cover every code, join the four-table union ([Joining → Seam C](joining.md#seam-c-proposition-statements-1-1)). One statement per proposition. |
| `has_evidence_lines` | `VARCHAR[]` | Ids of this statement's evidence lines in `rcv_evidenceLine`. |
| `data` | `VARCHAR` | Full JSON object as a string — see [The `data` column](#the-data-column). |

??? note "Full nested types — `rcv`"
    ```text
    strength  STRUCT("type" VARCHAR, conceptType VARCHAR, "name" VARCHAR)
    quality  STRUCT("type" VARCHAR, conceptType VARCHAR, "name" VARCHAR)
    classification  STRUCT("type" VARCHAR, conceptType VARCHAR, "name" VARCHAR, "extensions" STRUCT("name" VARCHAR, "value" VARCHAR)[])
    extensions  STRUCT("name" VARCHAR, "value" VARCHAR)[]
    ```

#### `rcv_evidenceLine` { #rcv_evidenceLine }

Evidence lines of RCV statements: which statements each RCV statement cites, and whether they contribute.

`rcv_evidenceLine.parquet` · **11,939,549** rows · 627.9 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `<statement id>.contributing` or `<statement id>.non-contributing`, e.g. `RCV003486676.1-G-PATH-CP.contributing`. |
| `type` | `VARCHAR` | Always `EvidenceLine`. |
| `directionOfEvidenceProvided` | `VARCHAR` | Direction of the evidence relative to the citing statement's proposition. |
| `strengthOfEvidenceProvided` | `STRUCT(type, conceptType, name)` | MappableConcept; `.name` is `Contributing` or `Non-contributing` — whether the cited items count toward the aggregate classification. |
| `evidence_items` | `VARCHAR[]` | The cited statement ids. On a root statement's line these are its level statements (`…-CP`, `…-NOCL`); on a level statement's line they are SCV ids (`clinvar.submission:SCV…`). |
| `data` | `VARCHAR` | Full JSON object as a string — see [The `data` column](#the-data-column). |

??? note "Full nested types — `rcv_evidenceLine`"
    ```text
    strengthOfEvidenceProvided  STRUCT("type" VARCHAR, conceptType VARCHAR, "name" VARCHAR)
    ```

### 6 · VCV

#### `vcv` { #vcv }

**VCV** aggregate statements — ClinVar's rollup of SCVs for one variant across all its conditions. Same shape as `rcv`.

`vcv.parquet` · **9,079,449** rows · 657.5 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `VCV<n>.<ver>-<G|S>-<CODE>[-<LEVEL>]`, e.g. `VCV000051592.122-G-PATH-CP`. A **root** id stops at the classification code; a **level** id adds `-PG`, `-EP`, `-CP`, `-NOCP`, `-NOCL`, or `-FLAG` (somatic clinical impact adds a tier, `-T1`/`-T2`). See [Reading a variant's statements](#reading-a-variants-statements). |
| `type` | `VARCHAR` | Always `Statement`. |
| `direction` | `VARCHAR` | `supports`, `disputes`, or `neutral` — the direction of the classification relative to the proposition (e.g. a *Benign* call `disputes` a pathogenicity proposition). |
| `strength` | `STRUCT(type, conceptType, name)` | MappableConcept; `strength.name` is e.g. `Definitive`, or NULL. |
| `quality` | `STRUCT(type, conceptType, name)` | MappableConcept; `quality.name` is the aggregate level — `practice guidelines`, `expert panel`, `criteria provided`, `no assertion criteria provided`, `no classification`, or `flagged`. |
| `classification` | `STRUCT(type, conceptType, name, extensions)` | MappableConcept; `classification.name` is the aggregate call (e.g. `Pathogenic`, `Benign/Likely benign`, `Conflicting classifications of pathogenicity`). `classification.extensions` carries `conflictingExplanation` when the call is a conflict. |
| `extensions` | `STRUCT(name, value)[]` | `{name, value}` pairs; today one: `clinvarReviewStatus` — ClinVar's review-status text (e.g. `criteria provided, multiple submitters, no conflicts`). |
| `proposition_id` | `VARCHAR` | The proposition this statement classifies. Its classification code names the proposition table (see [Reading a variant's statements](#reading-a-variants-statements)); to cover every code, join the four-table union ([Joining → Seam C](joining.md#seam-c-proposition-statements-1-1)). One statement per proposition. |
| `has_evidence_lines` | `VARCHAR[]` | Ids of this statement's evidence lines in `vcv_evidenceLine`. |
| `data` | `VARCHAR` | Full JSON object as a string — see [The `data` column](#the-data-column). |

??? note "Full nested types — `vcv`"
    ```text
    strength  STRUCT("type" VARCHAR, conceptType VARCHAR, "name" VARCHAR)
    quality  STRUCT("type" VARCHAR, conceptType VARCHAR, "name" VARCHAR)
    classification  STRUCT("type" VARCHAR, conceptType VARCHAR, "name" VARCHAR, "extensions" STRUCT("name" VARCHAR, "value" VARCHAR)[])
    extensions  STRUCT("name" VARCHAR, "value" VARCHAR)[]
    ```

#### `vcv_evidenceLine` { #vcv_evidenceLine }

Evidence lines of VCV statements. Same shape as `rcv_evidenceLine`.

`vcv_evidenceLine.parquet` · **9,291,483** rows · 508.4 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `<statement id>.contributing` or `<statement id>.non-contributing`, e.g. `VCV000051592.122-G-PATH-NOCP.contributing`. |
| `type` | `VARCHAR` | Always `EvidenceLine`. |
| `directionOfEvidenceProvided` | `VARCHAR` | Direction of the evidence relative to the citing statement's proposition. |
| `strengthOfEvidenceProvided` | `STRUCT(type, conceptType, name)` | MappableConcept; `.name` is `Contributing` or `Non-contributing` — whether the cited items count toward the aggregate classification. |
| `evidence_items` | `VARCHAR[]` | The cited statement ids. On a root statement's line these are its level statements (`…-CP`, `…-NOCL`); on a level statement's line they are SCV ids (`clinvar.submission:SCV…`). |
| `data` | `VARCHAR` | Full JSON object as a string — see [The `data` column](#the-data-column). |

??? note "Full nested types — `vcv_evidenceLine`"
    ```text
    strengthOfEvidenceProvided  STRUCT("type" VARCHAR, conceptType VARCHAR, "name" VARCHAR)
    ```

