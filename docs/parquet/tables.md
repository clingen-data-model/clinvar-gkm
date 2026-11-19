# The 20 Tables

!!! info "Release"
    Row counts and sizes on this page are from a `gkm-bundle-parquet` 2.0.0 build of the **2026-10-31 release**
    with the 1.2.0 schema (decimal units: 1 MB is 1,000,000 bytes). They change with every release; the queries give
    you today's numbers. The 1.1 tables (`v1/1.1/parquet/`, 22 tables) are described only in
    [Moving from the 1.1 Tables](migrating-from-1.1.md).

The Parquet release is **20 tables**, one per bundle section. They fall into six areas that you can learn one at a time. Variants and conditions are the nouns. Propositions say what is claimed about them. Statements say who claimed it, and how confidently.

<iframe src="../assets/diagrams/parquet-table-map.html" style="width:100%; height:760px; border:1px solid rgba(128,128,128,.25); border-radius:6px;" title="ClinVar-GKM Parquet table map" loading="lazy"></iframe>

The map renders at full size in a scrollable frame. Each area has a runnable query you can expand, and each table box links to that table's [column reference](#column-reference) below.

## The six areas

| Area | Tables | The question it answers |
| --- | --- | --- |
| **1 · Variant** | [`variation`](#variation), [`allele`](#allele), [`copyNumberCount`](#copyNumberCount), [`copyNumberChange`](#copyNumberChange), [`location`](#location), [`sequenceReference`](#sequenceReference), [`gene`](#gene) | Which variant is this, and where is it on the genome? |
| **2 · Condition & therapy** | [`condition`](#condition), [`conditionSet`](#conditionSet), [`therapy`](#therapy), [`therapyGroup`](#therapyGroup) | Which disease, tumor type or drug is the claim about? |
| **3 · Proposition** | [`propositionPathogenicity`](#propositionPathogenicity), [`propositionClinvarCustom`](#propositionClinvarCustom), [`propositionSomaticClinicalImpact`](#propositionSomaticClinicalImpact), [`propositionOncogenicity`](#propositionOncogenicity) | What exactly is being claimed about the variant? |
| **4 · SCV** | [`scv`](#scv), [`submitter`](#submitter), and the SCV rows of [`evidenceLine`](#evidenceLine) | What did each submitter say, how, and on what evidence? |
| **5 · RCV** | [`rcv`](#rcv), and the RCV rows of [`evidenceLine`](#evidenceLine) | What is ClinVar's combined call for this variant **and this condition**? |
| **6 · VCV** | [`vcv`](#vcv), and the VCV rows of [`evidenceLine`](#evidenceLine) | What is ClinVar's combined call for this variant **across all its conditions**? |

Most questions start in area 1 or 2, go through area 3, and end in one statement area. The [Joining Tables](joining.md) page covers each of those hops. For download links and the release layout, see [Downloads → Parquet Files](../data-access/parquet.md).

## How the tables follow from the bundle

The tables are generated from the bundle's JSON Schema by [`gkm-bundle-parquet`](build-your-own.md), with no hand-chosen column list (the schema's **default** column set). The same rules hold in every table:

- **One row per bundle record, and every field has a column.** A column is named after its JSON field, in the bundle's camelCase (`conceptType`, `primaryCoding`, `hasEvidenceLines`). An object becomes a `STRUCT`, a list becomes a list. There is no `data` column: [`to_json()`](table-anatomy.md#whole-records) turns a row back into its JSON, and [`gkm-bundle-parquet rebuild`](build-your-own.md#rebuild-the-bundle) turns the tables back into the bundle, record for record.
- **References hold bare ids.** Where the bundle has a pointer such as `#/condition/clinvar.trait:9580`, the column holds `clinvar.trait:9580`. When a reference can point to more than one table, a `<column>_section` column beside it names the table (`object_section`, `proposition_section`), and a list of such references is a list of `STRUCT(id, section)` (`members`, `concepts`, `hasEvidenceItems`).
- **A field that can hold different kinds of value has one column per kind**, named `value_<kind>`: `value_string`, `value_object`, `value_object_array`, `value_string_array`. In each element exactly one of them is set. See [Extensions](table-anatomy.md#extensions).
- **Rows are sorted by `id`.** A lookup by id reads only the row groups whose id range covers it.
- **Every file says what it is.** Its key-value metadata names the tool version, the table spec, the bundle schema version and the source bundle's sha256; see [Which set do you have?](migrating-from-1.1.md#which-set-do-you-have).

A few deeply nested positions, mostly extensions inside extensions, are kept as compact JSON text in a `VARCHAR`; `gkm-bundle-parquet generate` lists them. The one you are likely to meet is the member list of a submitted condition set on `scv` (see [Extensions](table-anatomy.md#extensions)); read it with `json_extract_string`.

## Ids tell you where to look { #ids-tell-you-where-to-look }

Every row has an id, and the id's shape names its table. A `_section` column names the table for you wherever a reference can go to more than one; the shapes are still the quickest way to read a result.

| Id shape | Example | Table |
| --- | --- | --- |
| `clinvar:<n>` | `clinvar:51592` | [`variation`](#variation) |
| `ga4gh:VA.<digest>` | `ga4gh:VA.Apas_jvqBJU7l4DGHGlvTGRY3BBh-UR9` | [`allele`](#allele) |
| `ga4gh:CN.<digest>` | `ga4gh:CN.wGhFBul2d7nEcVf-2n9HOBuhskBqdK-C` | [`copyNumberCount`](#copyNumberCount) |
| `ga4gh:CX.<digest>` | `ga4gh:CX.X1aEdg3zvDBvYfZfupzYACFNXKTi1Yh2` | [`copyNumberChange`](#copyNumberChange) |
| `ga4gh:SL.<digest>` | `ga4gh:SL.Gga5J2ccypatzYD5tBIeQEU9K4sPXc6J` | [`location`](#location) |
| `SQ.<digest>` | `SQ._0wi-qoDrvram155UmcSC-zA5ZK4fpLT` | [`sequenceReference`](#sequenceReference) |
| `ncbigene:<n>` | `ncbigene:675` | [`gene`](#gene) |
| `clinvar.trait:<n>` | `clinvar.trait:9580` | [`condition`](#condition) |
| `clinvar.traitset:<n>` | `clinvar.traitset:10013` | [`conditionSet`](#conditionSet) (accessioned) |
| `clinvar.conditionset:vcv-<md5>` | `clinvar.conditionset:vcv-50aae75c5e3a7740ab0c2f3ff9ebd970` | [`conditionSet`](#conditionSet) (minted) |
| `clinvar.therapy:<sha256>` | `clinvar.therapy:b150cd67…` | [`therapy`](#therapy) |
| `clinvar.therapygroup:<sha256>` | `clinvar.therapygroup:3595163a…` | [`therapyGroup`](#therapyGroup) |
| `clinvar.submitter:<n>` | `clinvar.submitter:500034` | [`submitter`](#submitter) |
| `clinvar.submission:SCV<n>.<ver>` | `clinvar.submission:SCV000056982.2` | [`scv`](#scv), and [`evidenceLine`](#evidenceLine) for a somatic clinical-impact SCV's own evidence line |
| `SCV<n>-<CODE>` | `SCV000056982-ASSOC` | a proposition table (a submission's proposition) |
| `VCV<n>-<G\|S>-<CODE>[-<LEVEL>]` | `VCV000051592-G-PATH-CP` | a proposition table (an aggregate's proposition) |
| `VCV<n>.<ver>-<G\|S>-<CODE>[-<LEVEL>]` | `VCV000051592.122-G-PATH-CP` | [`vcv`](#vcv) |
| `RCV<n>.<ver>-<G\|S>-<CODE>[-<LEVEL>]` | `RCV003486676.1-G-PATH-CP` | [`rcv`](#rcv) |
| `<statement id>.contributing` / `.non-contributing` | `VCV000051592.122-G-PATH-NOCP.contributing` | [`evidenceLine`](#evidenceLine) (a VCV or RCV statement's line) |

Two details are easy to miss:

- **A proposition id is its statement's id without the version.** `VCV000051592-G-PATH-CP` is the proposition, and `VCV000051592.122-G-PATH-CP` is the statement about it.
- **A proposition id's classification code names its table.** `PATH` is in `propositionPathogenicity`, `ONCO` in `propositionOncogenicity`, `SCI`, `DIAG`, `PROG` and `TR` in `propositionSomaticClinicalImpact`, and every other code in `propositionClinvarCustom` (see the code table under [Reading a variant's statements](#reading-a-variants-statements)). A statement's `proposition_section` names the table directly. To read all four at once, use `read_parquet('proposition*.parquet', union_by_name = true)`: the four tables have [different columns](#proposition-columns).

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

The same facts as text. A statement id reads `<accession>.<version>-<lane>-<code>[-<level>]`, for example `VCV000012871.94-G-PATH-CP`.

**Lane and classification code.** The lane is `G` (germline) or `S` (somatic). The code is shorthand for the proposition type, and says which proposition table holds the proposition:

| Lane | Code | Proposition type | Proposition table | Root statements |
| --- | --- | --- | --- | ---: |
| G | `PATH` | `VariantPathogenicityProposition` | `propositionPathogenicity` | 4,451,497 |
| G | `NP` | `ClinvarNotProvidedProposition` | `propositionClinvarCustom` | 27,921 |
| G | `DR` | `ClinvarDrugResponseProposition` | `propositionClinvarCustom` | 2,760 |
| G | `OTH` | `ClinvarOtherProposition` | `propositionClinvarCustom` | 2,171 |
| G | `RF` | `ClinvarRiskFactorProposition` | `propositionClinvarCustom` | 1,072 |
| G | `ASSOC` | `ClinvarAssociationProposition` | `propositionClinvarCustom` | 525 |
| G | `AFF` | `ClinvarAffectsProposition` | `propositionClinvarCustom` | 332 |
| G | `CDFS` | `ClinvarConflictingDataFromSubmitterProposition` | `propositionClinvarCustom` | 192 |
| G | `PROTECT` | `ClinvarProtectiveProposition` | `propositionClinvarCustom` | 99 |
| G | `CS` | `ClinvarConfersSensitivityProposition` | `propositionClinvarCustom` | 20 |
| S | `ONCO` | `VariantOncogenicityProposition` | `propositionOncogenicity` | 2,425 |
| S | `SCI` | `VariantClinicalSignificanceProposition` | `propositionSomaticClinicalImpact` | 1,317 |

Root statement counts are VCV roots. An SCV's proposition id uses the same codes without a lane (`SCV000056982-ASSOC`). A somatic clinical-impact (`SCI`) SCV also has an evidence line, in `evidenceLine` under the SCV's own id, whose `targetProposition` names the specific impact: `-TR` (therapeutic response), `-DIAG` or `-PROG`, all in `propositionSomaticClinicalImpact` with the `SCI` propositions. Its tier is in `evidenceOutcome`: `Level A/B` is Tier I, `Level C/D` is Tier II.

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

## Reading a table remotely

Every table can be queried straight from `https://data.clinvar-gkm.org/v1/1.2/parquet/<table>.parquet`, without downloading it. How well that works depends on what you ask:

- **Cheap on any table:** `DESCRIBE`, `count(*)`, and `LIMIT` reads. These touch only the file's footer or its first chunk, so they return in about a second even on the 1.66 GB `variation.parquet`.
- **Fine on small tables:** full scans of anything up to tens of megabytes (`condition`, `conditionSet`, `gene`, `submitter`, `therapy`, the three smaller proposition tables).
- **Download first for big tables:** a full scan or `GROUP BY` over `variation`, `scv`, `allele`, `location`, `propositionPathogenicity`, `evidenceLine`, `vcv` or `rcv` reads every row group, one request each, in a burst. Remotely that takes tens of seconds, and a heavier query can hit the CDN's rate limit (**HTTP 429**). Download the table once and query it locally. See [Working at Scale](performance.md#local-or-remote).

The sizes in the reference below tell you which category a table is in.

## Column reference { #column-reference }

Every column of every table, from `DESCRIBE`, with the 2026-10-31 row counts and file sizes. Types are shown compactly: `STRUCT(a, b)` lists only the top-level fields, and `[]` marks a list. Expand **Full nested types** under a table for the complete DuckDB type, or run `DESCRIBE SELECT * FROM '<table>.parquet'` yourself.

Read a `STRUCT` field with a dot (`classification.name`) and a list with `unnest(…)` or an index (`members[1]`). [Anatomy of a Table](table-anatomy.md) walks through both.

### 1 · Variant

#### `variation` { #variation }

ClinVar's variants, one row per ClinVar Variation id, as Cat-VRS **CategoricalVariant** records. The subject of every proposition. Each row points at the concrete VRS variant(s) that define it.

`variation.parquet` · **4,708,791** rows · 1.66 GB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `clinvar:<variation id>`, e.g. `clinvar:51592`. |
| `type` | `VARCHAR` | Always `CategoricalVariant`. |
| `name` | `VARCHAR` | ClinVar's preferred name, e.g. `NM_000059.4(BRCA2):c.4090A>C (p.Ile1364Leu)`. |
| `extensions` | `STRUCT(name, id, extensions, description, value_string, value_object_array)[]` | Named ClinVar attributes. Text attributes are in `value_string`: `clinvarVariationType`, `clinvarSubclassType`, `definingVrsVariationType`, `categoricalVariationType`, `clinvarCytogeneticLocation`, and the VRS processing notes `vrsProcessingException` and `vrsPreProcessingIssue`. Two lists are in `value_object_array`, which has the fields of both: `clinvarHgvsList` (`nucleotideExpression`, `nucleotideType`, `maneSelect`, `manePlus`, `proteinExpression`, `molecularConsequence`) and `clinvarGeneList` (`gene`, a bare `ncbigene:…` id → `gene.id`, `relationship_type`, `source`). A `nucleotideExpression.extensions` entry, JSON text, keeps ClinVar's submitted text when it wasn't valid HGVS. |
| `members` | `STRUCT(id, section)[]` | The concrete VRS variants that are members of this category: `section` is `allele`, `copyNumberCount` or `copyNumberChange`, and `id` is that table's id. |
| `constraints` | `STRUCT(type, …, copyChange, copies, copies_min, copies_max, allele, allele_section, allele_json, relations, location, location_section, location_json, matchCharacteristic, …)[]` | Cat-VRS constraints that define the category: `DefiningAlleleConstraint` (`allele` → `allele.id`, with `allele_section` = `allele`), `DefiningLocationConstraint` (`location` → `location.id`, and `matchCharacteristic`), `CopyCountConstraint` (`copies`, with `copies_min` / `copies_max`), `CopyChangeConstraint` (`copyChange`). `relations` lists allowed relations such as `liftover_to`, `transcribed_to`. The struct has every Cat-VRS constraint field; ClinVar-GKM leaves the others (`adjoinedElements`, `functionalDomains`, `linker`, …) NULL, and `allele_json` / `location_json` would hold an inline object instead of a reference. |
| `mappings` | `STRUCT(coding, relation)[]` | Identifiers for this variant in other systems: `{coding{system, code, iris}, relation}`. Always the ClinVar id (`exactMatch`); often dbSNP and ClinGen Allele Registry; sometimes dbVar, OMIM, UniProt, GTR and locus-specific databases. |

??? note "Full nested types — `variation`"
    ```text
    extensions  STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_string VARCHAR, value_object_array STRUCT(nucleotideExpression STRUCT("extensions" VARCHAR[], syntax VARCHAR, "value" VARCHAR), nucleotideType VARCHAR, maneSelect BOOLEAN, manePlus BOOLEAN, proteinExpression STRUCT(syntax VARCHAR, "value" VARCHAR), molecularConsequence STRUCT("name" VARCHAR, "system" VARCHAR, code VARCHAR, iris STRUCT(id VARCHAR, section VARCHAR)[])[], gene VARCHAR, relationship_type VARCHAR, "source" VARCHAR)[])[]
    members  STRUCT(id VARCHAR, section VARCHAR)[]
    constraints  STRUCT("type" VARCHAR, adjoinedElements STRUCT(id VARCHAR, section VARCHAR, "json" VARCHAR)[], functionalDomains STRUCT(id VARCHAR, "type" VARCHAR, "name" VARCHAR, description VARCHAR, aliases VARCHAR[], "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_json VARCHAR)[], "location" STRUCT(id VARCHAR, "type" VARCHAR, "name" VARCHAR, description VARCHAR, aliases VARCHAR[], "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_json VARCHAR)[], digest VARCHAR, baseSequenceLocation VARCHAR, baseSequenceLocation_section VARCHAR, baseSequenceLocation_json VARCHAR, mappedSequenceLocation VARCHAR, mappedSequenceLocation_section VARCHAR, mappedSequenceLocation_json VARCHAR, sequenceReference VARCHAR, sequenceReference_section VARCHAR, sequenceReference_json VARCHAR, "start" BIGINT, start_min BIGINT, start_max BIGINT, "end" BIGINT, end_min BIGINT, end_max BIGINT, "sequence" VARCHAR), status VARCHAR)[], linker STRUCT(id VARCHAR, "type" VARCHAR, "name" VARCHAR, description VARCHAR, aliases VARCHAR[], "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_json VARCHAR)[], length BIGINT, length_min BIGINT, length_max BIGINT, "sequence" VARCHAR, repeatSubunitLength BIGINT), orderKnown BOOLEAN, copyChange VARCHAR, copies BIGINT, copies_min BIGINT, copies_max BIGINT, allele VARCHAR, allele_section VARCHAR, allele_json VARCHAR, relations STRUCT("type" VARCHAR, primaryCoding STRUCT(id VARCHAR, "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_json VARCHAR)[], "name" VARCHAR, "system" VARCHAR, systemVersion VARCHAR, code VARCHAR, iris STRUCT(id VARCHAR, section VARCHAR)[]))[], "location" VARCHAR, location_section VARCHAR, location_json VARCHAR, matchCharacteristic STRUCT(id VARCHAR, "type" VARCHAR, "name" VARCHAR, description VARCHAR, aliases VARCHAR[], "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_json VARCHAR)[], conceptType VARCHAR, primaryCoding STRUCT(id VARCHAR, "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_json VARCHAR)[], "name" VARCHAR, "system" VARCHAR, systemVersion VARCHAR, code VARCHAR, iris STRUCT(id VARCHAR, section VARCHAR)[]), mappings STRUCT(id VARCHAR, "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_json VARCHAR)[], coding STRUCT(id VARCHAR, "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_json VARCHAR)[], "name" VARCHAR, "system" VARCHAR, systemVersion VARCHAR, code VARCHAR, iris STRUCT(id VARCHAR, section VARCHAR)[]), relation VARCHAR)[]), featureContext STRUCT(id VARCHAR, "type" VARCHAR, "name" VARCHAR, description VARCHAR, aliases VARCHAR[], "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_json VARCHAR)[], conceptType VARCHAR, primaryCoding STRUCT(id VARCHAR, "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_json VARCHAR)[], "name" VARCHAR, "system" VARCHAR, systemVersion VARCHAR, code VARCHAR, iris STRUCT(id VARCHAR, section VARCHAR)[]), mappings STRUCT(id VARCHAR, "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_json VARCHAR)[], coding STRUCT(id VARCHAR, "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_json VARCHAR)[], "name" VARCHAR, "system" VARCHAR, systemVersion VARCHAR, code VARCHAR, iris STRUCT(id VARCHAR, section VARCHAR)[]), relation VARCHAR)[]), functionConsequence STRUCT(id VARCHAR, "type" VARCHAR, "name" VARCHAR, description VARCHAR, aliases VARCHAR[], "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_json VARCHAR)[], conceptType VARCHAR, primaryCoding STRUCT(id VARCHAR, "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_json VARCHAR)[], "name" VARCHAR, "system" VARCHAR, systemVersion VARCHAR, code VARCHAR, iris STRUCT(id VARCHAR, section VARCHAR)[]), mappings STRUCT(id VARCHAR, "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_json VARCHAR)[], coding STRUCT(id VARCHAR, "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_json VARCHAR)[], "name" VARCHAR, "system" VARCHAR, systemVersion VARCHAR, code VARCHAR, iris STRUCT(id VARCHAR, section VARCHAR)[]), relation VARCHAR)[]), description VARCHAR)[]
    mappings  STRUCT(coding STRUCT("system" VARCHAR, code VARCHAR, iris STRUCT(id VARCHAR, section VARCHAR)[]), relation VARCHAR)[]
    ```

#### `allele` { #allele }

VRS **Allele** records: a specific sequence change at a location. Reached from `variation.members[]` and `constraints[].allele` (`ga4gh:VA.` prefix).

`allele.parquet` · **4,615,593** rows · 700.8 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `ga4gh:VA.<digest>`, the GA4GH computed identifier. |
| `type` | `VARCHAR` | Always `Allele`. |
| `name` | `VARCHAR` | An HGVS expression for the allele, e.g. `NC_000013.11:g.32338445A>C`. |
| `digest` | `VARCHAR` | The digest part of the id (the id without `ga4gh:VA.`). |
| `expressions` | `STRUCT(syntax, value)[]` | The allele written other ways: `spdi` (`NC_000013.11:32338444:A:C`), `hgvs.g`, and `gnomad` (`13-32338445-A-C`) where it applies. |
| `location` | `VARCHAR` | `ga4gh:SL.…` → `location.id`. |
| `state` | `STRUCT(type, length, sequence, repeatSubunitLength)` | The allele's sequence: for a `LiteralSequenceExpression`, `state.sequence` is the alternate bases; a `ReferenceLengthExpression` has `length` and `repeatSubunitLength`. |

#### `copyNumberCount` { #copyNumberCount }

VRS **CopyNumberCount** records: an absolute copy count over a region (`ga4gh:CN.` prefix).

`copyNumberCount.parquet` · **47,469** rows · 4.9 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `ga4gh:CN.<digest>`. |
| `type` | `VARCHAR` | Always `CopyNumberCount`. |
| `digest` | `VARCHAR` | The digest part of the id. |
| `location` | `VARCHAR` | `ga4gh:SL.…` → `location.id`. |
| `copies` | `BIGINT` | The absolute copy number. |

#### `copyNumberChange` { #copyNumberChange }

VRS **CopyNumberChange** records: a relative copy gain or loss over a region (`ga4gh:CX.` prefix).

`copyNumberChange.parquet` · **31,745** rows · 3.3 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `ga4gh:CX.<digest>`. |
| `type` | `VARCHAR` | Always `CopyNumberChange`. |
| `digest` | `VARCHAR` | The digest part of the id. |
| `location` | `VARCHAR` | `ga4gh:SL.…` → `location.id`. |
| `copyChange` | `VARCHAR` | `gain` or `loss`. |

#### `location` { #location }

VRS **SequenceLocation** records: a span on a reference sequence, shared by alleles and copy-number variants.

`location.parquet` · **4,226,867** rows · 427.3 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `ga4gh:SL.<digest>`. |
| `type` | `VARCHAR` | Always `SequenceLocation`. |
| `digest` | `VARCHAR` | The digest part of the id. |
| `sequenceReference` | `VARCHAR` | `SQ.…` → `sequenceReference.id`. |
| `start` | `BIGINT` | Start coordinate (0-based, interbase). NULL when the start is an uncertain range; use `start_min` / `start_max`. |
| `start_min` | `BIGINT` | Lower bound of the start. Equals `start` for a definite start; for a range, the range's first value, or NULL when the range is open below. |
| `start_max` | `BIGINT` | Upper bound of the start. Equals `start` for a definite start; for a range, its second value. |
| `end` | `BIGINT` | End coordinate (interbase). NULL when the end is an uncertain range; use `end_min` / `end_max`. **Quote it**: `"end"` is a reserved word. |
| `end_min` | `BIGINT` | Lower bound of the end. Equals `end` for a definite end; for a range, its first value. |
| `end_max` | `BIGINT` | Upper bound of the end. Equals `end` for a definite end; for a range, its second value, or NULL when the range is open above. |

In the bundle, an uncertain coordinate is a two-element list (`"start": [null, 18445861]`), so the bundle field becomes three columns. `start_max` and `end_min` bound the span the variant certainly covers, and are set on every row, so window queries can use them without skipping uncertain-range locations (71,989 locations in 2026-10-31, all of them copy-number variant locations). `start_min` and `end_max` bound the widest span it may cover.

!!! note "`end` is a reserved word"
    DuckDB and BigQuery both reject an unquoted `end` (`SELECT end FROM …` is a syntax error). Write `"end"`
    (`` `end` `` in BigQuery), or alias it: `SELECT start, "end" AS stop FROM 'location.parquet'`.

#### `sequenceReference` { #sequenceReference }

The reference sequences locations are placed on: RefSeq chromosomes, transcripts and other sequences, keyed by their GA4GH refget id. A **leaf**: it references nothing.

`sequenceReference.parquet` · **216** rows · 19.7 KB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `SQ.<digest>`, the refget accession (no `ga4gh:` prefix). |
| `type` | `VARCHAR` | Always `SequenceReference`. |
| `name` | `VARCHAR` | The RefSeq accession, e.g. `NC_000013.11`, `NM_000059.4`. |
| `extensions` | `STRUCT(name, value_string)[]` | On chromosomes, `assembly` (e.g. `GRCh38`). |
| `refgetAccession` | `VARCHAR` | Same value as `id`. |
| `residueAlphabet` | `VARCHAR` | `na` (nucleic acid). |
| `moleculeType` | `VARCHAR` | `genomic`, `mRNA`, or `RNA`. |

#### `gene` { #gene }

Genes referenced by variants' gene lists, keyed by NCBI Gene id. A **leaf**.

`gene.parquet` · **92,989** rows · 3.4 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `ncbigene:<n>`, e.g. `ncbigene:675` (BRCA2). |
| `type` | `VARCHAR` | Always `MappableConcept`. |
| `name` | `VARCHAR` | The gene symbol, e.g. `BRCA2`. |
| `conceptType` | `VARCHAR` | Always `gene`. |
| `primaryCoding` | `STRUCT(name, system, code, iris)` | The NCBI Gene coding; `primaryCoding.code` is the bare number (`675`). |
| `mappings` | `STRUCT(coding, relation)[]` | Cross-references, e.g. the HGNC id. |

### 2 · Condition & therapy

#### `condition` { #condition }

ClinVar's conditions (traits): diseases, phenotypes, findings, one row per ClinVar trait. The object of most propositions. A **leaf**.

`condition.parquet` · **23,426** rows · 2.0 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `clinvar.trait:<n>`, e.g. `clinvar.trait:9580`. |
| `type` | `VARCHAR` | Always `MappableConcept`. |
| `name` | `VARCHAR` | Preferred name, e.g. `Hereditary spastic paraplegia 48`. |
| `aliases` | `VARCHAR[]` | Alternate names. |
| `conceptType` | `VARCHAR` | `Disease`, `Phenotype`, `Trait`, or `Condition`. |
| `primaryCoding` | `STRUCT(name, system, code, iris)` | The MedGen coding; `primaryCoding.code` is the MedGen CUI (e.g. `C3150901`). |
| `mappings` | `STRUCT(coding, relation)[]` | Cross-references `{coding{system, code, iris}, relation}`: MONDO, Orphanet, OMIM, HPO, and others. |

??? note "Full nested types — `condition`"
    ```text
    primaryCoding  STRUCT("name" VARCHAR, "system" VARCHAR, code VARCHAR, iris STRUCT(id VARCHAR, section VARCHAR)[])
    mappings  STRUCT(coding STRUCT("system" VARCHAR, code VARCHAR, iris STRUCT(id VARCHAR, section VARCHAR)[]), relation VARCHAR)[]
    ```

#### `conditionSet` { #conditionSet }

Sets of conditions a single proposition is about. Two kinds of row share the table: **accessioned** ClinVar TraitSets (`clinvar.traitset:`, 5,409 rows) and sets **minted** for VCV-level aggregates (`clinvar.conditionset:vcv-…`, 95,455 rows).

`conditionSet.parquet` · **100,864** rows · 5.0 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `clinvar.traitset:<n>` (accessioned) or `clinvar.conditionset:vcv-<md5>` (minted). |
| `type` | `VARCHAR` | Always `ConceptSet`. |
| `conceptSetType` | `VARCHAR` | For TraitSets, ClinVar's set type: `Disease`, `Finding`, `TraitChoice`, `DrugResponse`. NULL on minted sets. |
| `concepts` | `STRUCT(id, section)[]` | The members: `section` is `condition` for a `clinvar.trait:` id, or `conditionSet` for a nested `clinvar.traitset:` (on minted sets). Join `concepts[].id` to `condition.id` (see [Joining → Seam B](joining.md)). |
| `membershipOperator` | `VARCHAR` | `AND` (all members together) or `OR` (any member). Minted sets are `OR`. |

#### `therapy` { #therapy }

Drug therapies named by therapeutic-response propositions. A **leaf**.

`therapy.parquet` · **38** rows · 5.1 KB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `clinvar.therapy:<sha256>` (content-addressed). |
| `type` | `VARCHAR` | Always `MappableConcept`. |
| `name` | `VARCHAR` | The therapy name. |
| `conceptType` | `VARCHAR` | Always `Drug`. |

#### `therapyGroup` { #therapyGroup }

Combination therapies: a set of `therapy` members.

`therapyGroup.parquet` · **10** rows · 5.6 KB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `clinvar.therapygroup:<sha256>`. |
| `type` | `VARCHAR` | Always `ConceptSet`. |
| `concepts` | `VARCHAR[]` | Member ids, `clinvar.therapy:…` → `therapy.id`. |
| `membershipOperator` | `VARCHAR` | Always `AND`: the members are given together. |

### 3 · Proposition { #proposition-tables }

Propositions are grouped by **meaning**, in four tables. A proposition's table depends only on its `type`.

| Table | Proposition types (id codes) | Rows | Size |
| --- | --- | ---: | ---: |
| [`propositionPathogenicity`](#propositionPathogenicity) | `VariantPathogenicityProposition` (`PATH`) | **27,981,342** | 400.6 MB |
| [`propositionClinvarCustom`](#propositionClinvarCustom) | the 9 `Clinvar*` types and `ClinvarUndefinedProposition` (`NP`, `DR`, `OTH`, `RF`, `ASSOC`, `AFF`, `CDFS`, `PROTECT`, `CS`, `UNDEF`) | **186,189** | 2.4 MB |
| [`propositionSomaticClinicalImpact`](#propositionSomaticClinicalImpact) | `VariantClinicalSignificanceProposition` (`SCI`), `VariantDiagnosticProposition` (`DIAG`), `VariantPrognosticProposition` (`PROG`), `VariantTherapeuticResponseProposition` (`TR`) | **12,607** | 146.8 KB |
| [`propositionOncogenicity`](#propositionOncogenicity) | `VariantOncogenicityProposition` (`ONCO`) | **12,233** | 153.6 KB |

#### The columns { #proposition-columns }

Every proposition table has the first seven columns below (`id` to `geneContextQualifier`), then the qualifiers its proposition types allow:

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `SCV<n>-<CODE>` for a submission's proposition; `VCV<n>-<G|S>-<CODE>[-<LEVEL>]` or `RCV…` for an aggregate's, e.g. `VCV000051592-G-PATH-CP`. Matches the `proposition` of at most one statement. |
| `type` | `VARCHAR` | The proposition class, e.g. `VariantPathogenicityProposition`, `ClinvarRiskFactorProposition`. |
| `subject` | `VARCHAR` | `clinvar:<n>` → `variation.id`. |
| `predicate` | `VARCHAR` | The relation, e.g. `isCausalFor`, `isRiskFactorFor`, `hasClinicalSignificanceFor`, `predictsSensitivityTo`. |
| `object` | `VARCHAR` | The object's id. **Dispatch on `object_section`**. |
| `object_section` | `VARCHAR` | The table `object` is in: `condition`, `conditionSet`, `therapy` or `therapyGroup`. Only therapeutic-response propositions have a therapy object. |
| `geneContextQualifier` | `STRUCT(type, name, extensions, conceptType, primaryCoding, mappings)` | The gene a submission's proposition is framed around; all four tables. See [Gene context](#gene-context). |
| `modeOfInheritanceQualifier` | `STRUCT(type, name, extensions, conceptType, primaryCoding)` | `propositionPathogenicity` and `propositionClinvarCustom`. `.name` is e.g. `Autosomal dominant inheritance`; `.primaryCoding.code` is the HPO id (`HP:0000006`) when there is one. Germline SCV propositions only. |
| `penetranceQualifier` | `STRUCT(type, name, extensions, conceptType)` | `propositionPathogenicity` and `propositionClinvarCustom`. `.name` is e.g. `low`. Germline SCV propositions only. |
| `conditionQualifier` | `VARCHAR` | `propositionSomaticClinicalImpact` only: the tumor or condition context of a therapeutic-response proposition, → `condition.id` (13 rows). |
| `conditionQualifier_section` | `VARCHAR` | The table `conditionQualifier` is in (`condition`). |

So the four tables **don't share one schema**. To read them as one table, use `union_by_name`: a column a table lacks is NULL in its rows.

```sql
SELECT id, type, object, object_section,
       geneContextQualifier.name AS gene,
       modeOfInheritanceQualifier.name AS moi
FROM read_parquet('proposition*.parquet', union_by_name = true)
WHERE subject = 'clinvar:51592';
```

Without `union_by_name = true`, DuckDB takes the column list from the first file, `propositionClinvarCustom`: naming `conditionQualifier` is a binder error, and reading `modeOfInheritanceQualifier` fails with a schema mismatch when the scan reaches `propositionSomaticClinicalImpact`. A query that reads only the seven columns every table has (`id` to `object_section`, and `geneContextQualifier`) works either way.

??? note "Full nested types — the qualifiers"
    ```text
    geneContextQualifier  STRUCT("type" VARCHAR, "name" VARCHAR, "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_string VARCHAR, value_string_array VARCHAR[])[], conceptType VARCHAR, primaryCoding STRUCT("name" VARCHAR, "system" VARCHAR, code VARCHAR, iris STRUCT(id VARCHAR, section VARCHAR)[]), mappings STRUCT(coding STRUCT("system" VARCHAR, code VARCHAR, iris STRUCT(id VARCHAR, section VARCHAR)[]), relation VARCHAR)[])
    penetranceQualifier  STRUCT("type" VARCHAR, "name" VARCHAR, "extensions" STRUCT("name" VARCHAR, value_string VARCHAR)[], conceptType VARCHAR)
    modeOfInheritanceQualifier  STRUCT("type" VARCHAR, "name" VARCHAR, "extensions" STRUCT("name" VARCHAR, value_string VARCHAR)[], conceptType VARCHAR, primaryCoding STRUCT("name" VARCHAR, "system" VARCHAR, code VARCHAR, iris STRUCT(id VARCHAR, section VARCHAR)[]))
    ```

#### `propositionPathogenicity` { #propositionPathogenicity }

Germline **pathogenicity** claims (`VariantPathogenicityProposition`, predicate `isCausalFor`) at every level. By far the largest proposition table. `object_section` is `condition` or `conditionSet` (2,964,682 rows, mostly VCV propositions over several conditions). 6,799,416 SCV rows carry a gene-context qualifier.

`propositionPathogenicity.parquet` · **27,981,342** rows · 400.6 MB · columns: the seven common ones, `penetranceQualifier`, `modeOfInheritanceQualifier`

#### `propositionClinvarCustom` { #propositionClinvarCustom }

ClinVar's **non-pathogenicity germline** classifications, which have no standard VA-Spec proposition: not provided, drug response, risk factor, association, affects, protective, confers sensitivity, other, conflicting data from submitters, plus `ClinvarUndefinedProposition`, the fallback for a classification that maps to no defined type (no rows so far). `object_section` is `condition` or `conditionSet`.

`propositionClinvarCustom.parquet` · **186,189** rows · 2.4 MB · columns: the seven common ones, `modeOfInheritanceQualifier`, `penetranceQualifier`

#### `propositionSomaticClinicalImpact` { #propositionSomaticClinicalImpact }

Somatic **clinical impact**: the clinical significance (`SCI`) that SCV, VCV and RCV statements classify, and the diagnostic (`DIAG`), prognostic (`PROG`) and therapeutic-response (`TR`) propositions that SCI evidence lines target. No statement classifies a `DIAG`, `PROG` or `TR` proposition directly; they are reached through [`evidenceLine.targetProposition`](#evidenceLine). The 13 `TR` rows have a `therapy` or `therapyGroup` object and a `conditionQualifier`; every other row's object is a `condition` or `conditionSet`.

`propositionSomaticClinicalImpact.parquet` · **12,607** rows · 146.8 KB · columns: the seven common ones, `conditionQualifier`, `conditionQualifier_section`

#### `propositionOncogenicity` { #propositionOncogenicity }

Somatic **oncogenicity** claims (`VariantOncogenicityProposition`, predicate `isOncogenicFor`). The object is the tumor type: almost always a `condition`, but 32 rows name a minted `conditionSet`.

`propositionOncogenicity.parquet` · **12,233** rows · 153.6 KB · columns: the seven common ones

#### Gene context { #gene-context }

`geneContextQualifier` is filled in only on **SCV** propositions; every VCV and RCV proposition has NULL. In 2026-10-31, 6,843,043 SCV propositions carry it, 6,799,416 of them in `propositionPathogenicity`.

| Field | What it holds |
| --- | --- |
| `geneContextQualifier.name` | The gene's symbol, e.g. `KRAS`. For the placeholder, the submitter's symbol (see below). |
| `geneContextQualifier.primaryCoding.code` | The gene's NCBI Gene number, e.g. `3845`. `'ncbigene:' || …code` joins `gene.id`. NULL for the placeholder. |
| extension `submittedGeneSymbols` (`value_string_array`) | The gene symbols the submitter gave, verbatim and in submitted order (e.g. `[MYCN, MYCNOS]`). Absent when there are none. |
| extension `geneContextSource` (`value_string`) | Where the gene came from; see the table below. |

```sql
SELECT p.id,
       p.geneContextQualifier.name                                          AS gene,
       'ncbigene:' || p.geneContextQualifier.primaryCoding.code             AS gene_id,
       [e.value_string FOR e IN p.geneContextQualifier.extensions
        IF e.name = 'geneContextSource'][1]                                 AS source,
       [e.value_string_array FOR e IN p.geneContextQualifier.extensions
        IF e.name = 'submittedGeneSymbols'][1]                              AS submitted
FROM 'propositionPathogenicity.parquet' p
WHERE p.subject = 'clinvar:12582' AND p.geneContextQualifier IS NOT NULL;
```

- **One representative gene per variant.** The qualifier comes from the variant, not from the submission. Upstream, clinvar-ingest-bq-tools picks one gene for each variant with its [single-gene method](https://github.com/clingen-data-model/clinvar-ingest-bq-tools/blob/main/docs/methods/single-gene-variation.md): a point-in-time priority procedure that starts from MANE transcripts and gene symbols in the variant's name, then ClinVar's gene associations. A few genes it picks come only from a variant's name and are not ones ClinVar associates; those are not in `gene.parquet`, so the id won't join for them. Every SCV of the variant gets that same gene. The submitter did **not** assert it, and the Parquet doesn't say which step chose it.
- **The code is the gene's own NCBI Gene coding**, never looked up from a symbol.
- **`submittedGeneSymbols`** is what the submitter named. It can list several genes, and may leave out the representative gene.
- **`geneContextSource`** is filled in on every SCV proposition that has the qualifier:

    | Value | Meaning | 2026-10-31 |
    | --- | --- | ---: |
    | `submittedSymbolMatches` | The submitter's symbols include the qualifier's symbol, possibly with other genes. | 5,917,880 |
    | `submittedSymbolDiffers` | The submitter gave symbols, but none equals the qualifier's symbol. Most are a previous symbol of the same gene (`GBA` for `GBA1`); the genes are not necessarily different. | 28,648 |
    | `inferredFromVariant` | The submitter gave no symbols. | 891,903 |
    | `submittedNotNormalized` | The placeholder: the variant has no single representative gene. | 4,612 |

    Symbols are compared after trimming spaces and ignoring case (`C19ORF12` matches `C19orf12`).
- **The placeholder.** When the variant has no single representative gene but the submitter named genes, `geneContextQualifier.name` is the submitter's symbol and `primaryCoding` is NULL. The name is not a normalized gene. Several symbols are joined with `, ` in submitted order (5 SCVs, e.g. `DLK1, MEG3`). There are 4,612 of these SCVs in 2026-10-31: 4,575 in `propositionPathogenicity` and 37 in `propositionClinvarCustom`.

    Because a placeholder's name is a submitted symbol, a filter such as `geneContextQualifier.name = 'TP53'` also matches placeholders: 29 `TP53` rows in 2026-10-31 (77 for `BRCA1`, `BRCA2`, `TP53` and `MLH1` together). To get only normalized genes, require `geneContextQualifier.primaryCoding.code IS NOT NULL`.

This is **not** the variant's gene list. The gene list (`clinvarGeneList` in `variation.extensions`) relates a variant to every gene ClinVar associates with it: many genes per variant, including genes a large copy-number variant merely overlaps. Use the gene list to find a gene's variants, as in the [gene rollup recipe](recipes.md#gene-rollup); use the gene context for the one gene a submission's proposition is framed around.

### 4 · SCV

#### `scv` { #scv }

**SCV** statements: each submitter's classification of a variant, one row per ClinVar submission (SCV accession). The leaves every aggregate cites.

`scv.parquet` · **6,881,795** rows · 784.1 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `clinvar.submission:SCV<n>.<ver>`, e.g. `clinvar.submission:SCV000056982.2`. |
| `type` | `VARCHAR` | Always `Statement`. |
| `description` | `VARCHAR` | The submitter's free-text comment on the classification, or NULL. |
| `extensions` | `STRUCT(name, id, extensions, description, value_string, value_object)[]` | Named ClinVar attributes. In `value_string`: `clinvarScvId`, `clinvarScvVersion`, `clinvarScvReviewStatus`, `submissionLevel`, `submittedScvLocalKey`, `submittedScvClassification`. In `value_object`: the submitter's original condition, `submittedCondition` (one condition: `name`, `type`, `medgen_id`, `xrefs`, `mapping`, `normalized_match`, `condition` → `condition.id`, …) or `submittedConditionSet` (`conditionSet` → `conditionSet.id`, `multiple_condition_explanation`, and `concepts`, a list of each member's object as JSON text). See [Extensions](table-anatomy.md#extensions). |
| `specifiedBy` | `STRUCT(type, name, extensions, methodType, reportedIn)` | The method: `methodType` (ClinVar collection method: `clinical testing`, `curation`, `research`, …), `name` (the assertion criteria, e.g. ACMG guidelines), `reportedIn` (the criteria document) and `extensions`. When ClinVar lists more than one citation for the method, the others are in the extension `additionalClinvarMethodCitations` (`value_object_array`). |
| `contributions` | `STRUCT(type, contributor, activityType, date)[]` | `contributor` is a `clinvar.submitter:` id → `submitter.id`; `activityType` is `submitted`, `created`, or `evaluated`; `date` is ISO text (`2014-04-01`), so cast it with `CAST(date AS DATE)`. |
| `reportedIn` | `STRUCT(type, name, extensions, documentType, urls, doi, pmid)[]` | Citations supporting the submission, one Document per ClinVar citation: `pmid`, `doi`, `urls`, `name` (ClinVar's label, e.g. `ACMG, 2015`) and `documentType` (e.g. `general`, `practice guideline`). `extensions` keep ClinVar's citation text (`clinvarCitationText`) and any repaired or unusable id; see [citation Documents](../pipeline/scv-statements/final-statements.md#temp_scv_citation_docs). A text-only citation carries only `clinvarCitationText`. |
| `proposition` | `VARCHAR` | The id of the proposition this statement classifies. One statement per proposition. |
| `proposition_section` | `VARCHAR` | The proposition table that holds it: `propositionPathogenicity`, `propositionOncogenicity`, `propositionSomaticClinicalImpact` or `propositionClinvarCustom`. Read that one file ([Joining → Seam C](joining.md#seam-c-proposition-statements-1-1)). |
| `direction` | `VARCHAR` | `supports`, `disputes`, or `neutral`: the direction of the classification relative to the proposition (e.g. a *Benign* call `disputes` a pathogenicity proposition). |
| `strength` | `STRUCT(type, name, conceptType, primaryCoding)` | `strength.name` is `Definitive`, `Likely`, `Strong`, `Potential`, or NULL; `primaryCoding` names the guideline (`system`) and code. |
| `quality` | `STRUCT(type, name, conceptType)` | `quality.name` is the submission level: `practice guidelines`, `expert panel`, `criteria provided`, `no assertion criteria provided`, `no classification`, or `flagged`. |
| `classification` | `STRUCT(type, name, extensions, conceptType, primaryCoding)` | `classification.name` is the submitted call (e.g. `Pathogenic`, `Likely benign`), **not case-normalized**; `primaryCoding` is `{system, code}` (e.g. `ACMG Guidelines, 2015`, `pathogenic`). `classification.extensions` may carry the submitter's `description`. |
| `hasEvidenceLines` | `VARCHAR[]` | Ids of this statement's evidence lines in `evidenceLine`; set only on somatic clinical-impact SCVs, where it is the SCV's own id. NULL otherwise. |

??? note "Full nested types — `scv`"
    ```text
    extensions  STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_string VARCHAR, value_object STRUCT(id VARCHAR, "name" VARCHAR, "type" VARCHAR, medgen_id VARCHAR, xrefs STRUCT("system" VARCHAR, code VARCHAR)[], original_medgen_match STRUCT(id VARCHAR, "name" VARCHAR), direct_match VARCHAR, normalized_match VARCHAR, normalized_resolution VARCHAR, "mapping" STRUCT("type" VARCHAR, "ref" VARCHAR, "value" VARCHAR), condition VARCHAR, conditionSet VARCHAR, multiple_condition_explanation VARCHAR, concepts VARCHAR[]))[]
    specifiedBy  STRUCT("type" VARCHAR, "name" VARCHAR, "extensions" STRUCT("name" VARCHAR, value_object_array STRUCT("type" VARCHAR, "name" VARCHAR, "extensions" VARCHAR[], documentType VARCHAR, urls VARCHAR[], doi VARCHAR, pmid VARCHAR)[])[], methodType VARCHAR, reportedIn STRUCT("type" VARCHAR, "name" VARCHAR, "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_string VARCHAR, value_boolean BOOLEAN)[], documentType VARCHAR, urls VARCHAR[], doi VARCHAR, pmid VARCHAR))
    contributions  STRUCT("type" VARCHAR, contributor VARCHAR, activityType VARCHAR, date VARCHAR)[]
    reportedIn  STRUCT("type" VARCHAR, "name" VARCHAR, "extensions" STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_string VARCHAR, value_boolean BOOLEAN)[], documentType VARCHAR, urls VARCHAR[], doi VARCHAR, pmid VARCHAR)[]
    strength  STRUCT("type" VARCHAR, "name" VARCHAR, conceptType VARCHAR, primaryCoding STRUCT("system" VARCHAR, code VARCHAR))
    quality  STRUCT("type" VARCHAR, "name" VARCHAR, conceptType VARCHAR)
    classification  STRUCT("type" VARCHAR, "name" VARCHAR, "extensions" STRUCT("name" VARCHAR, value_string VARCHAR)[], conceptType VARCHAR, primaryCoding STRUCT("system" VARCHAR, code VARCHAR))
    ```

#### `evidenceLine` { #evidenceLine }

Every evidence line in the release, in one table: the lines of SCV, VCV and RCV statements. Two kinds of row:

- **SCV lines** (1,568 rows): only somatic **clinical impact (SCI)** submissions have them. The id is the SCV's own id (`clinvar.submission:SCV…`), and the line points at the specific impact (therapeutic response, diagnostic, prognostic) with its AMP/ASCO/CAP tier.
- **VCV and RCV lines** (9,410,235 and 12,208,356 rows): which statements each aggregate statement cites, and whether they contribute. The id is `<statement id>.contributing` or `<statement id>.non-contributing`.

`evidenceLine.parquet` · **21,620,159** rows · 264.6 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `clinvar.submission:SCV<n>.<ver>` (an SCV line, same id as the `scv` row), or `VCV…`/`RCV…` + `.contributing` / `.non-contributing`, e.g. `VCV000051592.122-G-PATH-NOCP.contributing`. Filter with `id LIKE 'VCV%'` to read one kind. |
| `type` | `VARCHAR` | Always `EvidenceLine`. |
| `extensions` | `STRUCT(name, id, extensions, description, value_object)[]` | SCV lines: the submitter's original condition (`submittedCondition`), same shape as on `scv`. |
| `targetProposition` | `VARCHAR` | SCV lines: the specific-impact proposition (`…-DIAG`, `…-PROG` or `…-TR`) → `propositionSomaticClinicalImpact.id`. |
| `directionOfEvidenceProvided` | `VARCHAR` | `supports` / `disputes` / `neutral`, relative to the citing statement's proposition. |
| `evidenceOutcome` | `STRUCT(type, name, conceptType)` | SCV lines: `.name` is `Level A/B` (Tier I) or `Level C/D` (Tier II). |
| `hasEvidenceItems` | `STRUCT(id, section)[]` | VCV and RCV lines: the cited statements. On a root statement's line these are its level statements (`section` = `vcv` or `rcv`, ids `…-CP`, `…-NOCL`); on a level statement's line they are SCVs (`section` = `scv`). |
| `strengthOfEvidenceProvided` | `STRUCT(type, name, conceptType)` | VCV and RCV lines: `.name` is `Contributing` or `Non-contributing`, whether the cited items count toward the aggregate classification. |

??? note "Full nested types — `evidenceLine`"
    ```text
    extensions  STRUCT("name" VARCHAR, id VARCHAR, "extensions" VARCHAR[], description VARCHAR, value_object STRUCT(id VARCHAR, "name" VARCHAR, "type" VARCHAR, medgen_id VARCHAR, xrefs STRUCT("system" VARCHAR, code VARCHAR)[], original_medgen_match STRUCT(id VARCHAR, "name" VARCHAR), direct_match VARCHAR, normalized_match VARCHAR, normalized_resolution VARCHAR, "mapping" STRUCT("type" VARCHAR, "ref" VARCHAR, "value" VARCHAR), condition VARCHAR, conditionSet VARCHAR, multiple_condition_explanation VARCHAR, concepts VARCHAR[]))[]
    evidenceOutcome  STRUCT("type" VARCHAR, "name" VARCHAR, conceptType VARCHAR)
    hasEvidenceItems  STRUCT(id VARCHAR, section VARCHAR)[]
    strengthOfEvidenceProvided  STRUCT("type" VARCHAR, "name" VARCHAR, conceptType VARCHAR)
    ```

#### `submitter` { #submitter }

The organizations that submit to ClinVar. A **leaf**, referenced from `scv.contributions[].contributor`.

`submitter.parquet` · **3,586** rows · 137.7 KB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `clinvar.submitter:<n>`, ClinVar's organization id. |
| `type` | `VARCHAR` | Always `Agent`. |
| `name` | `VARCHAR` | The organization name. |

### 5 · RCV

#### `rcv` { #rcv }

**RCV** aggregate statements: ClinVar's rollup of SCVs for one variant **and one condition**. Each RCV accession yields a root statement plus one statement per contributing level. Their evidence lines are the `RCV…` rows of [`evidenceLine`](#evidenceLine).

`rcv.parquet` · **12,108,500** rows · 181.9 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `RCV<n>.<ver>-<G|S>-<CODE>[-<LEVEL>]`, e.g. `RCV003486676.1-G-PATH-CP`. A **root** id stops at the classification code; a **level** id adds `-PG`, `-EP`, `-CP`, `-NOCP`, `-NOCL`, or `-FLAG` (somatic clinical impact adds a tier, `-T1`/`-T2`). See [Reading a variant's statements](#reading-a-variants-statements). |
| `type` | `VARCHAR` | Always `Statement`. |
| `extensions` | `STRUCT(name, value_string)[]` | Today one: `clinvarReviewStatus`, ClinVar's review-status text (e.g. `criteria provided, multiple submitters, no conflicts`). |
| `proposition` | `VARCHAR` | The id of the proposition this statement classifies. One statement per proposition. |
| `proposition_section` | `VARCHAR` | The proposition table that holds it. |
| `direction` | `VARCHAR` | `supports`, `disputes`, or `neutral`. |
| `strength` | `STRUCT(type, name, conceptType)` | `strength.name` is e.g. `Definitive`, or NULL. |
| `quality` | `STRUCT(type, name, conceptType)` | `quality.name` is the aggregate level: `practice guidelines`, `expert panel`, `criteria provided`, `no assertion criteria provided`, `no classification`, or `flagged`. |
| `classification` | `STRUCT(type, name, extensions, conceptType, primaryCoding)` | `classification.name` is the aggregate call (e.g. `Pathogenic`, `Benign/Likely benign`, `Conflicting classifications of pathogenicity`). `classification.extensions` carries `conflictingExplanation` when the call is a conflict. `primaryCoding` is `{system, code}` for the call (from 1.2.0). |
| `hasEvidenceLines` | `VARCHAR[]` | Ids of this statement's evidence lines in `evidenceLine`. |

??? note "Full nested types — `rcv`"
    ```text
    extensions  STRUCT("name" VARCHAR, value_string VARCHAR)[]
    strength  STRUCT("type" VARCHAR, "name" VARCHAR, conceptType VARCHAR)
    quality  STRUCT("type" VARCHAR, "name" VARCHAR, conceptType VARCHAR)
    classification  STRUCT("type" VARCHAR, "name" VARCHAR, "extensions" STRUCT("name" VARCHAR, value_string VARCHAR)[], conceptType VARCHAR, primaryCoding STRUCT("system" VARCHAR, code VARCHAR))
    ```

### 6 · VCV

#### `vcv` { #vcv }

**VCV** aggregate statements: ClinVar's rollup of SCVs for one variant across all its conditions. Same columns as `rcv`. Their evidence lines are the `VCV…` rows of [`evidenceLine`](#evidenceLine).

`vcv.parquet` · **9,200,508** rows · 145.4 MB

| Column | Type | Description |
| --- | --- | --- |
| `id` | `VARCHAR` | `VCV<n>.<ver>-<G|S>-<CODE>[-<LEVEL>]`, e.g. `VCV000051592.122-G-PATH-CP`. A **root** id stops at the classification code; a **level** id adds `-PG`, `-EP`, `-CP`, `-NOCP`, `-NOCL`, or `-FLAG` (somatic clinical impact adds a tier, `-T1`/`-T2`). See [Reading a variant's statements](#reading-a-variants-statements). |
| `type` | `VARCHAR` | Always `Statement`. |
| `extensions` | `STRUCT(name, value_string)[]` | Today one: `clinvarReviewStatus`. |
| `proposition` | `VARCHAR` | The id of the proposition this statement classifies. |
| `proposition_section` | `VARCHAR` | The proposition table that holds it. |
| `direction` | `VARCHAR` | `supports`, `disputes`, or `neutral`. |
| `strength` | `STRUCT(type, name, conceptType)` | `strength.name` is e.g. `Definitive`, or NULL. |
| `quality` | `STRUCT(type, name, conceptType)` | `quality.name` is the aggregate level. |
| `classification` | `STRUCT(type, name, extensions, conceptType, primaryCoding)` | `classification.name` is the aggregate call; `classification.extensions` carries `conflictingExplanation`; `primaryCoding` is `{system, code}` (from 1.2.0). |
| `hasEvidenceLines` | `VARCHAR[]` | Ids of this statement's evidence lines in `evidenceLine`. |

??? note "Full nested types — `vcv`"
    ```text
    extensions  STRUCT("name" VARCHAR, value_string VARCHAR)[]
    strength  STRUCT("type" VARCHAR, "name" VARCHAR, conceptType VARCHAR)
    quality  STRUCT("type" VARCHAR, "name" VARCHAR, conceptType VARCHAR)
    classification  STRUCT("type" VARCHAR, "name" VARCHAR, "extensions" STRUCT("name" VARCHAR, value_string VARCHAR)[], conceptType VARCHAR, primaryCoding STRUCT("system" VARCHAR, code VARCHAR))
    ```
