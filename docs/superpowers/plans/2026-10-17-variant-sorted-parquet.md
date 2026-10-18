# Statement Lookup Files (C1) — Design Plan

> **Status: design only (2026-10-17, extended 2026-10-18).** Nothing here is wired into the release
> pipeline. This plan answers the **C1** "Plan first" item in
> `docs/superpowers/plans/2026-10-16-parquet-followups.md` (branch `docs/parquet-followups-plan`, PR #144).
> On 2026-10-18 it grew from one file into a **family** of lookup files that share one set of statement
> columns, each sorted by a different key. All export SQL below is a prototype, quoted here so nobody mistakes
> it for a live `parquet-schemas/` file. Decisions marked **(maintainer)** are collected in §11.

**Goal.** Publish pre-joined Parquet files, sorted by the key a question starts from:

- a variant
- a condition or therapy (including through the sets that contain it)
- a gene
- a PubMed id

Each such question then reads one or two row groups instead of scanning `scv.parquet` (3.1 GB) and a
proposition table. That makes the questions runnable over HTTPS, including in the browser console, which gets
HTTP 429 after about 55 requests in 10 s.

**Ground rule for the whole family: a column or a file never implies a relationship the source data doesn't
make.** Three consequences:

- A concept reached through a condition set is labelled as such, never presented as the proposition's own
  object.
- ClinVar's variant-to-gene list is never presented as a statement's gene.
- A method citation is never presented as evidence.

**Measurement sources:**

- **Files:** every one was built from the 2026-10 monthly Parquet set (`~/Development/sandbox/clinvar-gkm-parquet`)
  with DuckDB 1.5.4. All share the same settings: ZSTD, default 122,880-row groups, no bloom filters, a
  total-order sort.
- **Request counts:** DuckDB's `httpfs` reading from a local HTTP server that supports range requests and
  logs each one. Every query ran in a fresh process with `SET threads = 1`, to match the single-threaded
  console. Counts include the footer fetch.
- **BigQuery (read-only):** every prototype was dry-run on `clinvar_2026_10_11_v2_6_0`. Each was also run as
  a `SELECT` with row-count breakdowns on that dataset and on `clinvar_2026_09_28_v2_6_0`. The latter is the
  source of the 2026-10 monthly set.
- **Equivalence:** on `2026_09_28`, every breakdown of every file matches the local build exactly. No
  `EXPORT DATA`, `CREATE` or `DELETE` was run.

---

## The family at a glance

| File | One row per | Sort key | Rows (2026-10) | Size | Row groups | Typical lookup |
| --- | --- | --- | --- | --- | --- | --- |
| `statement-by-variant` | statement | `variant_id` | 27,653,888 | 189.2 MB | 226 | 10–17 requests |
| `statement-by-object` | statement × condition/therapy | `concept_id` | 32,555,778 | 236.5 MB | 265 | 8–16 requests |
| `concept-set-membership` | set × member | `member_concept_id` | 401,265 | 6.4 MB | 4 | 5–9 requests |
| `variant-gene` | gene × variant (ClinVar's gene list) | `gene_id` | 7,346,154 | 24.2 MB | 60 | 5–7 requests |
| `statement-by-gene-context` | statement with a gene-context qualifier | `gene_context_id` | 6,694,162 | 73.9 MB | 55 | 4–7 requests |
| `statement-by-citation` | citation id × SCV × role | `citation_id` | 4,886,981 PMID-only as measured; ~7.9 M with the citation fix (§5) | 47.7 MB as measured | 40 | 7–23 requests |
| *(on hold)* `statement-by-variant-gene` | statement × gene from the gene list | `gene_id` | 41,777,105 | 250.6 MB | 340 | 9–15 requests |

**Total for one monthly set:** ~578 MB for the six recommended files. For comparison, the 22 section files
come to ~13.0 GB.

**One-variant answer today:** the `scv` ⨝ `varcond-proposition` join for PubMed ids on `clinvar:10` takes
**399 requests and 331 MB**. With `statement-by-variant` it takes **16 requests and 1.2 MB**.

---

## Decisions shared by every file

| Topic | Decision | Why |
| --- | --- | --- |
| Compression | **ZSTD** | `statement-by-variant` is 189 MB, against 328 MB with Snappy. DuckDB, DuckDB-Wasm, pyarrow and polars all read it |
| Row groups | **122,880 rows** (DuckDB default) | Smaller groups added requests and grew the footer (§1) |
| Bloom filters | **Off** (`WRITE_BLOOM_FILTER false`) | With them on, any filter besides the sort key costs one request per row group (§1) |
| Sort | **Total order**, with the lookup key first | Pruning, and stable rebuilds: two separate builds of `statement-by-variant` came out the same size to the byte (189,156,552) |
| Ids | **Bare** (`clinvar.trait:2645`, `ncbigene:672`) | Same as every typed-Parquet foreign-key column after #143 |
| Provenance | Parquet key/value metadata: `clinvar_gkm_release`, `clinvar_gkm_schema_version`, `sort_order` | Readable from the footer. A constant column would add one to every row |
| Built by | One `parquet-schemas/<file>.sql` `EXPORT DATA` per file, sharing spliced fragments; **sorted in the local merge step** | `EXPORT DATA` controls neither order nor row groups nor bloom filters (§6) |
| Deltas | **Never in deltas.** Every file is rebuilt whole for each monthly set | §7 |
| Location | Inside each monthly set, `v1/datasets/parquet/YYYY-MM/` (+ `00-latest/`) | The console's `{BASE}` already points there (§8) |
| Past releases | **Yes, for the four monthly sets** (2026-07 … 2026-10). Nothing for the 15 weeklies | §9 |

### The core statement columns

Four files carry these 17 columns unchanged: `statement-by-variant`, `statement-by-object`,
`statement-by-gene-context`, and `statement-by-citation` (which drops `pmids`). Users learn them once.

| Column | Type | From | Notes |
| --- | --- | --- | --- |
| `variant_id` | string | proposition `subject` | `clinvar:<variation id>` |
| `source_table` | string | — | `scv`, `vcv` or `rcv`: the table `statement_id` lives in |
| `statement_id` | string | statement `id` | Joins to `id` in that table |
| `proposition_type` | string | proposition `type` | |
| `predicate` | string | proposition `predicate` | |
| `object_id` | string | proposition `object`, **as stated** | A condition, condition set, tumor type, therapy or therapy group id |
| `condition_qualifier_id` | string | `conditionQualifier` | Therapeutic-response propositions only |
| `gene_context_name` | string | `geneContextQualifier.name` | **Variant-derived**, not submitter-asserted (§4). SCV only |
| `mode_of_inheritance` | string | `modeOfInheritanceQualifier.name` | SCV only |
| `penetrance` | string | `penetranceQualifier.name` | SCV only |
| `classification_name` | string | `classification.name` | |
| `strength_name` | string | `strength.name` | |
| `quality_name` | string | `quality.name` | Submission level (SCV) or aggregate level (VCV/RCV) |
| `direction` | string | `direction` | |
| `submitter_id` | string | first `contributions[]` with `activityType = 'submitted'` | SCV only. Joins to `submitter.parquet` |
| `date_last_evaluated` | date | first `contributions[]` with `activityType = 'evaluated'` | SCV only |
| `pmids` | list\<string\> | `reportedIn[].pmid` | SCV only. Empty for VCV/RCV |

The struct columns are flattened with a `_name` suffix, so they can't be mistaken for the structs in
`scv.parquet`.

**Not carried:** `data`, `description`, `specifiedBy` and extensions. A lookup joins back on `statement_id`
for those.

**`proposition_id` dropped (maintainer):** it was 91 MB of 292 MB. Every field a lookup needs from the
proposition is already inlined, and the id stays reachable through the statement table.

---

## 1. `statement-by-variant`

**Purpose:** everything ClinVar says about one variant (submissions, VCV layers, RCVs) in one footer fetch
plus one row group.

| Column | Notes |
| --- | --- |
| The 17 core columns | Sort: `variant_id, source_table, statement_id` |

**Which tiers.** SCV, VCV and RCV, in one file:

- All three join to a proposition 100 % of the time: 0 unjoined of 28,045,103 rows on 2026-10-11.
- SCV alone would be 75 MB.
- A `source_table = 'scv'` filter costs nothing extra, provided bloom filters are off.

**Pruning.** I sampled 2,000 random variants, plus `clinvar:10` and the busiest variant (`clinvar:17004`,
189 statements). Every lookup touched exactly 1 of 226 row groups.

`variant_id` sorts as text (`clinvar:10` < `clinvar:100` < `clinvar:11`). That is fine for `=` and `IN`;
numeric ranges don't prune.

**Row-group size**, with bloom filters on (so the files are slightly bigger than the final layout):

| Rows per group | Row groups | File | Footer | Requests: `SELECT *` for one variant |
| --- | --- | --- | --- | --- |
| **122,880** | **226** | 201 MB | 0.52 MB | **11** |
| 61,440 | 451 | 205 MB | 1.03 MB | 17 |
| 30,720 | 901 | 212 MB | 2.03 MB | 28 |

**Why bloom filters must be off:**

- DuckDB writes them by default. The published `scv.parquet` has them on 3,523 of its 3,960 column chunks.
- When a filter's min/max can't rule a row group out, DuckDB probes that column's bloom filter, which costs
  one request per row group. It does this even when the sort-key filter has already excluded the group.

| Query on `statement-by-variant` | Bloom on | Bloom off |
| --- | --- | --- |
| `variant_id = 'clinvar:10'` | 11 | 10 |
| `… AND source_table = 'scv'` | **238** | **16** |
| `… AND classification_name = 'Pathogenic'` | **238** | **16** |

## 2. `statement-by-object`

**Purpose:** every statement about a condition or therapy, whether the proposition names the concept itself
or names a set that contains it. Every row says which of those is the case.

**One row per (statement, concept):**

| `role` | The concept is… | `via_set_id` | `membership_operator` | `via_nested_set_id` |
| --- | --- | --- | --- | --- |
| `object` | the proposition's own object: a single condition, tumor type or therapy | NULL | NULL | NULL |
| `set_member` | a leaf member of the condition set or therapy group the proposition names | that set | its `AND`/`OR` | the inner `clinvar.traitset` when the member came through one nested inside a minted `clinvar.conditionset`, else NULL |
| `condition_qualifier` | a therapeutic-response proposition's `conditionQualifier` | NULL | NULL | NULL |

Direct rows and set rows are never merged. A query for "statements *about* Marfan syndrome" filters
`role = 'object'`; "statements whose condition set *includes* Marfan" filters `role = 'set_member'`. The
nested set's own operator is in `concept-set-membership` (§3). Only minted sets nest, and only one level, so
no deeper expansion is needed. Sets themselves are not rows: they have no single meaning to look up by, and
a lookup by set id is the job of §3.

**Therapies come only through evidence lines.** No statement's own proposition is therapeutic. In 2026-10,
13 therapeutic-response propositions are the targets of somatic SCVs' evidence lines (1,568 evidence lines,
which also target 1,555 diagnostic and prognostic propositions). The file includes each targeted proposition's
concepts and marks those rows `via_evidence_line = TRUE`:

- Their proposition columns (`proposition_type`, `predicate`, `object_id`, qualifiers) are the **targeted**
  proposition's.
- Their statement columns (`classification_name`, …) are the SCV's own, and the SCV's classification is about
  its own proposition.
- So those rows also carry the evidence line's own `evidence_outcome_name` (`Level A/B` 1,022, `Level C/D`
  570) and `evidence_direction`. Read those, not `classification_name`, for the therapy.

**Columns:**

| Column | Type | Notes |
| --- | --- | --- |
| `concept_id` | string | **Sort key 1.** `clinvar.trait:` or `clinvar.therapy:` id. NULL only on `concept_type = 'none'` rows |
| `concept_type` | string | `condition`, `therapy`, or `none` for a proposition with no `object` |
| `role` | string | `object`, `set_member` or `condition_qualifier` |
| `via_set_id` | string | The set/group the proposition names (NULL unless `set_member`) |
| `membership_operator` | string | That set's `AND`/`OR` (NULL unless `set_member`) |
| `via_nested_set_id` | string | Inner `clinvar.traitset`, when flattened through one |
| The 17 core columns | | `object_id` is the proposition's object as stated, so it equals `via_set_id` on set rows |
| `via_evidence_line` | boolean | TRUE when the concept came from a proposition an SCV's evidence line targets |
| `evidence_outcome_name` | string | Evidence line `evidenceOutcome.name` (NULL unless `via_evidence_line`)* |
| `evidence_direction` | string | Evidence line `directionOfEvidenceProvided` (same)* |

\* In the BigQuery prototype, not in the local measurement build. These columns are non-null on 1,592 rows
only, so the size is unaffected.

**NULL objects.** Four propositions have a NULL `object`. An earlier prototype typed them as sets, so their
statements silently fell out of the file. They are kept as `role = 'object'` rows with `concept_id` NULL and
`concept_type = 'none'`, sorted last, so every statement in the file is accounted for.

**Sort:** `concept_id NULLS LAST, variant_id, source_table, statement_id, via_evidence_line, role, via_set_id
NULLS FIRST, via_nested_set_id NULLS FIRST`. The key is unique: 32,555,778 distinct of 32,555,778.

**Rows (2026-10):**

| `role` / `concept_type` | Rows |
| --- | --- |
| object / condition | 24,750,175 (+ 1,555 via evidence line) |
| set_member / condition | 7,019,358 direct + 784,653 through a nested traitset |
| object / therapy | 6 (all via evidence line) |
| set_member / therapy | 18 (all via evidence line) |
| condition_qualifier / condition | 13 (all via evidence line) |

**Marfan syndrome (`clinvar.trait:2645`), one lookup, 9 requests:**

| `role` | SCV | VCV | RCV |
| --- | --- | --- | --- |
| object | 4,365 | 3,119 | 7,273 |
| set_member | 5,892 (15 traitsets) | 9,287 direct (227 minted sets) + 6,304 nested (234) | 11,760 (15 traitsets) |

**Heavy concepts.** `clinvar.trait:17556` (not provided) and `clinvar.trait:16789` (not specified) each have
about 7–8 M rows. A `count(*)` of one takes 70 requests, over the rate limit. These are catch-alls; leave
them download-only (decision 8).

## 3. `concept-set-membership`

**Purpose:** "which sets contain X" and "what is in set Y", without parsing `conditionSet.concepts` or
`therapyGroup.value`. It is the small companion that explains the `set_member` rows of §2.

**One row per (set, member).** Rows come from every published condition set (the >1-member filter applies)
and every therapy group:

- **Direct members.** A nested `clinvar.traitset` inside a minted set appears as a row with
  `member_type = 'set'`.
- **Flattened leaves** of each nested set, with `via_nested_set_id`.

| Column | Type | Notes |
| --- | --- | --- |
| `member_concept_id` | string | **Sort key 1.** Bare id |
| `member_type` | string | `condition`, `therapy` or `set` (a nested traitset) |
| `member_name` | string | From `condition.parquet` / `therapy.parquet`. NULL for nested sets, which have no name, and for 30 conditions with no name in the source |
| `set_id` | string | The containing set |
| `set_type` | string | `conditionSet` or `therapyGroup` |
| `concept_set_type` | string | `Disease`, `Finding`, `TraitChoice`, `DrugResponse` for ClinVar traitsets. NULL for minted sets and therapy groups |
| `membership_operator` | string | The containing set's `AND`/`OR` |
| `via_nested_set_id` | string | Set when the row is a leaf flattened through a nested traitset |

**Sort:** `member_concept_id, set_id, via_nested_set_id NULLS FIRST`. One duplicate pair is dropped with
`DISTINCT`: a therapy group lists the same therapy twice.

**Rows (2026-10):**

| Kind | Rows |
| --- | --- |
| conditionSet → condition, direct | 281,065 |
| conditionSet → condition, through a nested set | 90,113 |
| conditionSet → nested set | 30,032 |
| therapyGroup → therapy | 55 |
| **Total** | **401,265** (6.4 MB, 4 row groups) |

**Lookups:**

- **Which sets contain `clinvar.trait:2645`:** 5 requests. It is in 8 Disease and 7 TraitChoice traitsets
  (AND), 214 minted sets directly and 290 through a nested traitset (OR).
- **Members of a given set:** 9 requests. That is the whole 6.4 MB file, which is fine at this size.

## 4. Genes: two different relationships, two files, never merged

The data holds two gene relationships. They mean different things, and no file may present one as the other.

**(a) ClinVar's variant-to-gene list**, the variation's `clinvarGeneList` extension:
- **Shape:** many genes per variant.
- **Columns:** each entry carries a `relationship_type` (`within single gene`, `within multiple genes by
  overlap`, `genes overlapped by variant`, `near gene, upstream/downstream`, `asserted, but not computed`) and
  a `source` (`submitted` or `calculated`).
- **Meaning:** it describes the **variant**, not any statement.
- **Scale:** 7,346,154 pairs over 4,637,755 variants and 92,972 genes. 866 variants list more than 500
  genes each, contributing 911,238 pairs (mostly `genes overlapped by variant`, the large CNVs).

**(b) The proposition's gene-context qualifier**, `geneContextQualifier` (`gene_context_name` in the typed
Parquet). It is **variant-derived and single-valued**, not submitter-asserted. Provenance:

1. **Built in** `gkm-scv-statement-proc.sql`, Step 2 (`temp_gene_context_qualifiers`). It joins each SCV's
   `variation_id` to the upstream `single_gene_variation` table, then to `gene`. That sets `name` = gene
   symbol, `primaryCoding.code` = the NCBI Gene id, and an HGNC `exactMatch` mapping.
2. **`single_gene_variation`** comes from clinvar-ingest-bq-tools,
   `scripts/dataset-preparation/04-single-gene-variation-proc.sql`. It picks **one representative gene per
   variation**, taking the first step of this cascade that applies:
   1. a MANE Select transcript at the start of the variation name
   2. a resolvable gene symbol in an HGVS-style name (`NM_…(GENE):c.…`)
   3. a star-allele name (`CYP2C19*10`)
   4. a single gene association of any kind
   5. a single *submitted* association that is neither `genes overlapped by variant` nor `asserted, but not
      computed`
   6. a single `within single gene` association
   7. a haplotype/genotype whose child variations all share one gene

   Steps 1–3 and 7 record `source = 'cvc calculated'` when no gene-association row backs the chosen
   gene. That marks a gene *inferred by this heuristic*, not one ClinVar reported. The `source` and
   `relationship_type` are **not** carried into the qualifier, so the Parquet can't tell which step chose
   the gene.
3. **The same gene on every SCV of a variant.** Because the qualifier hangs off `variation_id`, every SCV
   of a variant gets the same gene.
4. **The submitter's own genes** appear only as the qualifier's `submittedGeneSymbols` extension, a per-SCV
   list parsed from `clinical_assertion_variation`.
5. **The placeholder.** When the variation has no single gene but the submitter named genes, `name` is the
   literal `submitted genes were not normalized`, with no coding.

**In 2026-10:**
- 6,694,162 SCVs carry a qualifier: 19,190 gene ids, plus the placeholder on **4,814** SCVs.
- 5,812,837 of them also carry `submittedGeneSymbols`.
- In 27,817 the submitted symbols don't include the chosen gene's symbol.
- VCV/RCV propositions carry no qualifier today (C4).

**The two must stay separate.** Sending (a) through statements would label 41.8 M statement rows with genes
no statement asserted, and would bury the single-gene choice among overlap genes. Sending (b) through the
gene list would lose its "one representative gene" meaning.

### 4.1 `variant-gene`

**Purpose:** a thin crosswalk of (a). It saves every consumer from unnesting
`variation.extensions[].value_gene_array[]` from a 4 GB file.

| Column | Type | Notes |
| --- | --- | --- |
| `gene_id` | string | **Sort key 1.** `ncbigene:` id |
| `gene_symbol` | string | From `gene.parquet` `name` (a join on the id, not a symbol mapping) |
| `variant_id` | string | Sort key 2 |
| `relationship_type` | string | As in the gene list |
| `relationship_source` | string | `submitted` or `calculated` |

**Sort:** `gene_id, variant_id, relationship_type, relationship_source` (unique). The file is 24.2 MB, 60
row groups. All CNV fan-out is kept; filter on `relationship_type` to drop it.

**Lookups:**
- BRCA1 (`ncbigene:672`, 16,089 variants): 5 requests.
- TTN (`ncbigene:7273`, 40,949 variants): 7 requests.
- By symbol (`gene_symbol = 'BRCA1'`, not the sort key): 60 requests. Resolve the symbol to an id in the
  small `gene.parquet` first.

### 4.2 `statement-by-gene-context`

**Purpose:** statements by (b), keyed on the qualifier's own NCBI Gene id. That id is
`geneContextQualifier.primaryCoding.code`, already in the data, so no symbol is mapped to an id. Names are
carried verbatim, including the placeholder.

| Column | Type | Notes |
| --- | --- | --- |
| `gene_context_id` | string | **Sort key 1.** `ncbigene:` + `primaryCoding.code`. NULL for the placeholder |
| `gene_context_name` | string | Verbatim, including `submitted genes were not normalized` |
| `submitted_gene_symbols` | list\<string\> | The `submittedGeneSymbols` extension, verbatim and in the bundle's order |
| The core columns, except `gene_context_name` | | |

**Sort:** `gene_context_id NULLS LAST, variant_id, source_table, statement_id`. The placeholder rows sort
last, and a `gene_context_name = 'submitted genes were not normalized'` filter finds them.

**Size:** 6,694,162 rows (SCV only today), 73.9 MB, 55 row groups.

| Query | Requests |
| --- | --- |
| SCVs for `ncbigene:672` (BRCA1), by classification | 4 |
| SCVs for `ncbigene:4625` (MYH7) | 4 |
| SCVs for `ncbigene:7273` (TTN) | 6 |
| BRCA1 PubMed ids (from `pmids`) | 5 |
| By name `gene_context_name = 'BRCA1'` (not the sort key) | 56 |
| Symbol → id in `gene.parquet` as a scalar subquery, then by id | **7** |

**Typed-Parquet gap:** `parquet-schemas/var*-proposition.sql` exports only `gene_context_name`. This file is
built from the proposition JSON in BigQuery, so it doesn't need them. Adding `gene_context_id` and
`submitted_gene_symbols` to the four proposition exports is a separate, additive choice (decision 7).

### 4.3 On hold: a fat `statement-by-variant-gene` file

A file of (a) × statements, sorted by gene, answers "every statement on a variant in gene X" in one lookup.
It is **not recommended for now**: it attaches gene-list genes to statements, which is exactly the
relationship the source doesn't make, unless every row carries `relationship_type`/`relationship_source`
and the docs keep saying "variants in/overlapping gene X". The numbers for that decision:

| | Rows | Size (ZSTD) | Row groups |
| --- | --- | --- | --- |
| All gene-list relationships | 41,777,105 | **250.6 MB** | 340 |
| Without `genes overlapped by variant` | 30,791,138 | 210.7 MB | 251 |
| Rows from the 866 variants with >500 genes | 4,575,394 | — | — |

| Query: VCV classifications for variants in the gene | Two-step: `variant-gene` → `statement-by-variant` | Fat file |
| --- | --- | --- |
| BRCA1 (16,089 variants) | **686 requests**, 20.5 MB; touches 196 of 226 row groups | **9 requests**, 1.2 MB |
| TTN (40,949 variants) | **688 requests**, 20.9 MB; 188 of 226 row groups | **15 requests**, 1.3 MB |
| BRCA1, ids already in hand (local list) | 681 requests | — |
| BRCA1 PubMed ids | — | 11 requests |

The two-step path is correct but not remote-viable: a gene's variant ids are scattered across almost every
row group of a variant-sorted file. It works fine on a downloaded `statement-by-variant` (189 MB).

## 5. `statement-by-citation`

**Purpose:** every statement that cites a given publication or URL: a PubMed id, a DOI or a URL.

**Keyed on a typed `citation_id` (decided).** The key is `pmid:<n>`, `doi:<doi>` or `url:<url>`, verbatim
after the prefix, so every kind of citation prunes the same way. It is derived from the bundle's citation
Documents, which after the citation fix (`fix/scv-citations`) are **one Document per ClinVar citation**,
with `pmid`, `doi`, `urls`, `name`, `documentType` and verbatim-keeping extensions.

**One row per (citation id, SCV, role).** VCV and RCV carry no citations.

- **A multi-id Document yields one row per id.** ACMG 2015 is one Document with a PMID, a DOI and a PMC URL. It
  gives three rows: `pmid:25741868`, `doi:10.1038/gim.2015.30` and
  `url:https://europepmc.org/article/PMC/4544753`.
- **Ids, not every URL.** `pmid` gives a `pmid:` row and `doi` a `doi:` row. Each entry of `urls` gives a
  `url:` row, except the resolver URL the pipeline derives from the Document's own `pmid` or `doi`
  (`https://pubmed.ncbi.nlm.nih.gov/<pmid>`, `https://doi.org/<doi>`), which would only repeat that id. PMC and
  Bookshelf ids exist in the bundle only as URLs, so they are `url:` rows. A SICI-style DOI that VA-Spec's
  pattern rejects has no `doi`; it is reachable through its `url:https://doi.org/…` row.
- **Text-only Documents are excluded.** They have no `pmid`, `doi` or `urls`, only the verbatim
  `clinvarCitationText` extension, so they have no `citation_id`. The same goes for a Document that carries
  only `invalidClinvarCitation`.
- **Role comes from the bundle.** `evidence` is `reportedIn[]` and `method` is `specifiedBy.reportedIn`. A
  `reportedIn[]` Document flagged `clinvarAssertionMethodCitation` is a second assertion-method citation that
  `Method.reportedIn` could not hold, so it is a `method` row. A method citation is never presented as
  evidence.

| Column | Type | Notes |
| --- | --- | --- |
| `citation_id` | string | **Sort key 1.** `pmid:…`, `doi:…` or `url:…` |
| `citation_type` | string | `pmid`, `doi` or `url` (the prefix) |
| `citation_role` | string | `evidence` or `method` |
| `pmid` | string | The Document's `pmid`, on every row of that Document, so a DOI or URL row still shows its PubMed id |
| The core columns, except `pmids` | | Includes `variant_id` and `object_id` |

**Sort:** `citation_id, citation_role, source_table, statement_id`. `DISTINCT` drops a key that one SCV lists
twice in the same role.

**Rows, estimated on `clinvar_2026_09_28_v2_6_0` with the citation fix applied (BigQuery, read-only):**

| Role | `pmid:` | `doi:` | `url:` | Total | Distinct keys |
| --- | --- | --- | --- | --- | --- |
| evidence | 1,546,184 | 8,189 | 86,522 | 1,640,895 | 159,641 |
| method | 3,340,801 | 1,790 | 2,947,149 | 6,289,740 | 1,222 |
| **All** | | | | **7,930,635** | 160,318 |

That is about 62 % more rows than the PMID-only file measured below (4,886,981). Nearly all of the growth is
2.95 M `method` `url:` rows, most of them a few submitter-uploaded FileTrack PDFs. They are cheap because they
compress to a few keys. Size and request counts were not re-measured; re-measure before publishing (task 6).

**PMID-only file as measured (2026-10, before the citation fix):** 1,546,181 evidence and 3,340,800 method
rows, 4,886,981 in all (47.7 MB, 40 row groups). `method` rows are mostly a few guideline papers: PMID
25741868 (ACMG/AMP 2015) alone has 1,194,391.

| Query (PMID-only build) | Requests |
| --- | --- |
| Statements citing PMID 20301691 | 7 |
| PMID 25741868, by role (1.2 M rows) | 23 |
| BRCA1 PubMed ids by joining `statement-by-gene-context` → this file on `statement_id` | 55, at the limit |
| BRCA1 PubMed ids from `statement-by-gene-context.pmids` directly | **5** |

With the typed key, a PMID lookup filters `citation_id = 'pmid:20301691'`. The prefix keeps all `pmid:` keys
in one contiguous range, so pruning matches the PMID-only file.

**PubMed ids for a gene:** `statement-by-gene-context` already has `pmids`, so it is the gene → PMID path
(5 requests). The join is the wrong path remotely, because this file is not sorted by `statement_id`.

---

## 6. How the files are built

1. **SQL.** Each file is one `parquet-schemas/<file>.sql`.
   - The four statement files share the CTE fragment `_statement-core.sql`, spliced in at
     `{STATEMENT_CORE}`.
   - `statement-by-object` and `concept-set-membership` share `_concept-sets.sql`, spliced in at
     `{CONCEPT_SETS}`.
   - This needs a small change to `extract_parquet_typed`: substitute the fragments, and skip files whose
     name starts with `_`.
   - The `--delta` table rewrite must never touch these files (§7).
2. **Sort in the merge.** `release-gkm.sh` step 3 replaces the plain merge `COPY` for each file with:

   ```sql
   SET preserve_insertion_order = false;
   COPY (SELECT * FROM read_parquet('<shards>/<file>-*.parquet') ORDER BY <sort key from the table above>)
   TO '<dir>/<file>.parquet'
   (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 122880, WRITE_BLOOM_FILTER false,
    KV_METADATA {clinvar_gkm_release: '<YYYY-MM>', clinvar_gkm_schema_version: '<x.y.z>',
                 sort_order: '<sort key>'});
   ```

   The biggest sort (`statement-by-object`, 32.6 M rows) fits in the 4–8 GB the merge already uses. The full
   local family build peaked at 8 GB.
3. **Gate in the merge.** Fail the release if any of these fails:
   - Row counts against the source tables:
     - `statement-by-variant` = scv + vcv + rcv
     - `statement-by-gene-context` = SCVs with a qualifier
     - `concept-set-membership` > 0
   - 0 NULL sort keys, except `gene_context_id` on placeholder rows and `concept_id` on
     `concept_type = 'none'` rows (the NULL-object propositions).
   - 0 bloom filters.
   - A probe key falls in exactly 1 row group.
4. **Cost per monthly set.** The dry runs on 2026-10-11 processed (upper bound):

   | File | GB processed |
   | --- | --- |
   | `statement-by-variant` | 11.19 |
   | `statement-by-object` | 11.21 |
   | `statement-by-gene-context` | 11.19 |
   | `statement-by-citation` | 8.63 |
   | `variant-gene` | 1.28 |
   | `concept-set-membership` | 0.02 |

   That is **~43.5 GB, about $0.27 per set**. Exporting the core once and deriving the other files locally
   would save ~$0.20 a month, but it would break the one-SQL-per-file convention and couple the files to
   the merge step. Not worth it.

**Drift risk, and the bundle-derivability rule.** Every Parquet value must be recomputable from the JSON bundle
(user rule, 2026-10-18). Each file here derives only from bundle content: ids are stripped from `#/` pointers,
citation keys come from the citation Documents (§5), and the statement and proposition fields are inlined.
Building from the dict tables in BigQuery can still drift from what the bundle publishes, because the
assembler filters and cleanup (single-member conditionSet drop, `strip_empty`, extension collapse) must be
mirrored by hand. Building the files from the **published** Parquet, or checking them against it, would
prevent that drift. At minimum, task 6 compares each file with the same set's section files.

**Why not build them locally from the section Parquet:**
- It ties the files to typed-table quirks: the pre-#143 quoted `object_therapy`, and `gene_context_id`,
  which the section Parquet doesn't have.
- It only works where a full Parquet set exists on disk.

## 7. Deltas

**None of these files ships in a weekly delta. Each is rebuilt whole for each monthly set.**

- **The delta rewrite can't produce them.** `extract_parquet_typed --delta` rewrites
  `.gkm_dict_` → `.delta_gkm_dict_`. Every file here joins two or more dict tables: statements to
  propositions; sets to conditions; variations to genes. Joining delta to delta drops every row whose other
  side didn't change.
  - Also, the comment in `extract_parquet_typed` saying each schema file reads exactly ONE table is already
    wrong (the proposition and therapy files read 3–4). Reword it.
- **Applying a delta would undo the sort**, and the sort is the whole point. A consumer replaying deltas
  rebuilds locally instead, with the Working at Scale recipe (about 1 minute per file).
- **They aren't bundle sections.** The manifest, the reconstruction oracle and the replay examples iterate
  over sections. A full derived file in `deltas/<date>/parquet/` would be listed as changed rows.

Weekly full copies are decision 4.

## 8. R2 layout, `index.json` and scripts

All six files sit in the monthly set directory: `v1/datasets/parquet/YYYY-MM/<file>.parquet`, copied to
`00-latest/`. Year-end archiving (`archive_parquet_yearly`) moves every file in that directory. An upload
with `R2_PREFIX=''` publishes the flat-root copy the same way.

| Script / file | Change |
| --- | --- |
| `parquet-schemas/` | Six new SQL files + two `_` fragments |
| `export-gkm-dicts.sh` | Export lines guarded by `if ! $DELTA`; fragment splicing; fix the ONE-table comment |
| `release-gkm.sh` | Sorted merge + gate per file (§6) |
| `upload-gkm-to-r2.sh` | **None.** `upload_parquet` uploads every `*.parquet` and copies each to `00-latest/`. The dated paths are new, so nothing needs purging |
| `generate-r2-index.sh` | **Additive:** each `datasets.parquet[]` entry gets a `"parquet": [...]` file list (reuse `r2_parquet_sections_under`, as delta entries do), so readers can tell which sets have the lookup files |
| `docs/assets/js/r2-browser.js` | Render that list, falling back to the fixed 22. Group the lookup files under a "Lookup files (derived)" sub-heading |
| Delta scripts, `build-delta-manifest.py`, oracles | None |

## 9. Past releases and the backfill

**Recommendation: give all six files to the four monthly sets (2026-07, -08, -09, -10). The 15 weeklies need
nothing.** The console's release picker and the docs file browser both list all four months, so a missing
file would 404 there.

This doesn't need to wait for the consolidated backfill or block it:
- The files are new, at paths never cached.
- They are in no manifest and feed no oracle.
- No published file changes.

So they can go out with that backfill if they're ready, or as a separate additive step later.

**Cost per monthly set:**

| Step | Cost |
| --- | --- |
| `EXPORT DATA` ×6 from the month's source dataset (2026-10 ← `clinvar_2026_09_28_v2_6_0`, per ADR 0002) | ~43.5 GB processed, ~$0.27 |
| Download shards + sort/merge | ~5 min, ≤ 8 GB RAM |
| Upload | ~578 MB, plus server-side copies for `00-latest` (latest set only) |
| CDN purge | None (new paths) |

**For four sets:** about $1.10 of BigQuery, about 20 minutes, about 2.3 GB of uploads, then one
`index.json` regeneration. Nothing is overwritten and there is no oracle or reconstruction re-run.

**Ordering:** build after C4 is decided, because populating aggregate gene context would change the VCV/RCV
rows of `statement-by-gene-context` and `statement-by-variant`. And if past months should carry the citation
fix, build after it too.

## 10. Docs changes (in the implementation PR, on `main`)

Docs ship with the first set that has the files; examples are run against the published files first.

- [ ] **The 22 Tables → new section "Lookup files (derived)":**
  - each file's column table from this plan, and its sort key
  - that the files are rebuilt monthly, are not in deltas, and have no `id` column
  - the two gene relationships (§4), with the provenance of the gene-context qualifier
- [ ] **Recipes:** one-lookup recipes for each key:
  - a variant's PubMed ids and VCV layers
  - a condition's statements, direct versus through sets, and its P/LP calls by submitter
  - a therapy's statements, explaining `via_evidence_line`
  - a gene, with both relationships side by side
  - the statements citing a PMID
  - which sets contain a condition
- [ ] **Console:** examples for a variant, a condition, a gene context and a PMID; point the 429 hint at
  the lookup files.
- [ ] **Working at Scale:**
  - "Materialize the joins you repeat" opens by pointing to the published files
  - the local recipe stays for custom columns
  - "Local or remote" gains rows for the lookup files
  - the bloom-filter finding goes into "Share it as a sorted Parquet file"
- [ ] **Joining Tables:** a note that `gene_context_name` is variant-derived, not submitter-asserted. The
  provenance text from §4 belongs in the Data Guide as well.
- [ ] **Downloads → Parquet Files:** list the lookup files as derived and monthly-only.
- [ ] **ADR "Derived Parquet lookup files":**
  - not sections
  - rebuilt per monthly set, never in deltas
  - sorted, no bloom filters, key/value metadata
  - the no-implied-relationship rule

## 11. Decisions needed from the maintainer

1. **Which files to publish.** Recommended: the six in the table (≈ 578 MB a month). The fat
   `statement-by-variant-gene` is on hold (decision 5).
2. **Statement tiers:** SCV + VCV + RCV in every statement file (recommended), or SCV only? VCV/RCV rows reach
   conditions mostly through minted sets, which `role`/`via_set_id` keeps visible.
3. **Drop `proposition_id`** from the core? Recommended: −91 MB on `statement-by-variant` alone.
4. **Weekly freshness:** monthly only (recommended for now), or also full weekly copies at
   `v1/deltas/<YYYY-MMDD>/lookup/`? That would cost about $0.27, ~578 MB a week (~30 GB/year of R2), plus
   delta-script, index and console work.
5. **Fat `statement-by-variant-gene` (for the user).** 250.6 MB with all relationships, or 210.7 MB without
   `genes overlapped by variant`. 9–15 requests per gene, against ~690 for the two-step path. If published,
   every row must carry `relationship_type`/`relationship_source`, and the name and docs must say "variants
   in gene X", never "statements about gene X".
6. **Non-PMID citations — RESOLVED (2026-10-18).** The key is a typed `citation_id` (`pmid:` / `doi:` /
   `url:`). A multi-id Document yields one row per id, and text-only Documents have no `citation_id` and are
   excluded (§5). `method` rows are kept, with `citation_role`.
7. **Typed export:** add `gene_context_id` and `submitted_gene_symbols` to `var*-proposition.sql`? This is
   additive and makes the qualifier usable without the lookup file. Recommended, with C2/C3.
8. **Catch-all concepts** (`not provided`, `not specified`: ~7–8 M rows each in `statement-by-object`): keep
   them and document them as download-only (recommended), or leave them out of the file? Leaving them out
   would make the file a subset of the data.
9. **Sort every published section by `id`** in the merge step? Separate from C1, but it would make
   `statement_id` → `scv.parquet` (`data`, `description`) cheap remotely.
10. **Key/value metadata** on these files only (recommended), or on all published files?
11. **Backfill timing:** with the consolidated backfill if ready, otherwise a separate additive publish
    (§9).

---

## Measurements

**Local builds** (2026-10). The whole family took 141 s to join and 288 s to sort and write, peaking at
8 GB RSS. `statement-by-variant` alone: 49 s to join, 50 s to sort.

| File | Rows | Size | Row groups | Footer |
| --- | --- | --- | --- | --- |
| `statement-by-variant` | 27,653,888 | 189.2 MB | 226 | 492 KB |
| `statement-by-object` | 32,555,778 | 236.5 MB | 265 | 800 KB |
| `concept-set-membership` | 401,265 | 6.4 MB | 4 | 5 KB |
| `variant-gene` | 7,346,154 | 24.2 MB | 60 | 37 KB |
| `statement-by-gene-context` | 6,694,162 | 73.9 MB | 55 | 126 KB |
| `statement-by-citation` | 4,886,981 | 47.7 MB | 40 | 84 KB |
| *(on hold)* `statement-by-variant-gene` | 41,777,105 | 250.6 MB | 340 | 905 KB |

**Requests per query** (local range server, `threads = 1`, footer included):

| Query | File(s) | Requests | MB |
| --- | --- | --- | --- |
| PubMed ids for `clinvar:10` (today: `scv` ⨝ `varcond-proposition`) | section files | 399 | 331 |
| PubMed ids for `clinvar:10` | `statement-by-variant` | 16 | 1.2 |
| VCV layers for `clinvar:10` | `statement-by-variant` | 17 | 1.7 |
| SCVs for `clinvar:10` + submitter + condition names | + `submitter`, `condition` | 23 | 5.9 |
| Marfan (`clinvar.trait:2645`), all statements by role | `statement-by-object` | 9 | 1.3 |
| Erlotinib, all statements | `statement-by-object` | 8 | 1.8 |
| Marfan P/LP SCVs by submitter, with names | + `submitter` | 16 | 2.6 |
| `clinvar.trait:17556` (not provided) `count(*)` | `statement-by-object` | **70** | 1.1 |
| Sets containing `clinvar.trait:2645` | `concept-set-membership` | 5 | 0.1 |
| Members of `clinvar.traitset:84974` | `concept-set-membership` | 9 | 6.4 |
| BRCA1 / TTN variants | `variant-gene` | 5 / 7 | 0.1 |
| BRCA1 variants by `gene_symbol` | `variant-gene` | 60 | 0.5 |
| BRCA1 / MYH7 / TTN SCVs by classification | `statement-by-gene-context` | 4 / 4 / 6 | 0.2 |
| BRCA1 PubMed ids | `statement-by-gene-context` | 5 | 0.9 |
| BRCA1 by `gene_context_name` | `statement-by-gene-context` | 56 | 0.3 |
| BRCA1 via `gene.parquet` symbol → id subquery | + `gene` | 7 | 1.1 |
| BRCA1 / TTN VCV calls, two-step | `variant-gene` → `statement-by-variant` | 686 / 688 | 20.5 / 20.9 |
| BRCA1 / TTN VCV calls | fat `statement-by-variant-gene` | 9 / 15 | 1.2 / 1.3 |
| Statements citing PMID 20301691 | `statement-by-citation` | 7 | 0.3 |
| PMID 25741868 by role | `statement-by-citation` | 23 | 0.2 |
| BRCA1 PMIDs via gene-context ⨝ citation | both | 55 | 9.1 |

The browser console runs DuckDB-Wasm 1.29.0. Its request pattern must be checked before the docs ship
(task 7), but its min/max pruning is the same.

**BigQuery `SELECT` breakdowns** (read-only):

| File | `clinvar_2026_09_28_v2_6_0` (= local, exact) | `clinvar_2026_10_11_v2_6_0` |
| --- | --- | --- |
| `statement-by-variant` | scv 6,735,011 · vcv 9,079,449 · rcv 11,839,428 | scv 6,845,745 · vcv 9,156,181 · rcv 12,043,177 |
| `statement-by-object` | object 24,750,175 · set_member 7,019,358 + 784,653 nested · evidence-line rows 1,592 | object 25,087,165 · set_member 7,210,009 + 802,058 nested · evidence-line 1,592 |
| `concept-set-membership` | 281,065 + 90,113 nested + 30,032 sets + 55 therapy | 322,895 + 97,932 nested + 32,771 sets + 55 therapy |
| `variant-gene` | 7,346,154 (92,972 genes) | 7,391,276 (92,977 genes) |
| `statement-by-gene-context` | 6,689,348 with id + 4,814 placeholder | 6,800,068 + 4,827 |
| `statement-by-citation` (PMID-only, before the citation fix) | evidence 1,546,181 · method 3,340,800 | evidence 1,552,301 · method 3,439,337 |

All three tiers join 100 % in both datasets, with 0 NULL `variant_id`.

---

## Prototype SQL

Proposed paths are under `src/scripts/parquet-schemas/`. `{DATASET}` is substituted by
`extract_parquet_typed`, and `{STATEMENT_CORE}` / `{CONCEPT_SETS}` by the splice step in §6. Each file below
was dry-run in its spliced form on `clinvar_2026_10_11_v2_6_0`. None needs `collapse_ext_values`, since none
has a `data` column.

**Fix found while validating:** `gkm_dict_condition_set` stores **traitset** members as `#/condition/…`
pointers and minted-set members bare. The published bundle carries the same mix: traitset ConceptSets list
`#/condition/…` pointers, `vcv-` sets list bare ids. Stripping to bare ids is therefore a supported derivation
from the bundle, not a Parquet-only fact. `conditionSet.sql` strips them; `_concept-sets.sql` must too.

### `_statement-core.sql` (fragment)

```sql
-- Shared CTEs for the statement lookup files (spliced in where a file says {STATEMENT_CORE}).
-- prop: every proposition, aligned to one shape; bare ids (no '#/section/' pointers).
prop AS (
  SELECT
    key AS proposition_id,
    JSON_VALUE(value, '$.type') AS proposition_type,
    JSON_VALUE(value, '$.predicate') AS predicate,
    REGEXP_REPLACE(JSON_VALUE(value, '$.subject'), r'^#/[^/]+/', '') AS variant_id,
    REGEXP_REPLACE(JSON_VALUE(value, '$.object'), r'^#/[^/]+/', '') AS object_id,
    REGEXP_REPLACE(JSON_VALUE(value, '$.conditionQualifier'), r'^#/[^/]+/', '') AS condition_qualifier_id,
    JSON_VALUE(value, '$.geneContextQualifier.name') AS gene_context_name,
    IF(JSON_VALUE(value, '$.geneContextQualifier.primaryCoding.code') IS NULL, NULL,
       CONCAT('ncbigene:', JSON_VALUE(value, '$.geneContextQualifier.primaryCoding.code'))) AS gene_context_id,
    -- the bundle's array order, as in #143's var*-proposition.sql
    ARRAY(
      SELECT JSON_VALUE(sym)
      FROM UNNEST(JSON_QUERY_ARRAY(value, '$.geneContextQualifier.extensions')) AS ext,
           UNNEST(JSON_QUERY_ARRAY(ext, '$.value_string')) AS sym WITH OFFSET so
      WHERE JSON_VALUE(ext, '$.name') = 'submittedGeneSymbols'
      ORDER BY so
    ) AS submitted_gene_symbols,
    JSON_VALUE(value, '$.modeOfInheritanceQualifier.name') AS mode_of_inheritance,
    JSON_VALUE(value, '$.penetranceQualifier.name') AS penetrance
  FROM (
    SELECT key, value FROM `{DATASET}.gkm_dict_proposition`
    UNION ALL SELECT key, value FROM `{DATASET}.gkm_dict_vcv_proposition`
    UNION ALL SELECT key, value FROM `{DATASET}.gkm_dict_rcv_proposition`
  )
),
-- stmt: statement-level columns, plus two SCV-only helpers (citation_keys, evidence_line_ids).
-- citation_keys: one entry per typed id of each citation Document (§5). A reportedIn Document flagged
-- clinvarAssertionMethodCitation is a method citation. Text-only Documents yield no key.
stmt AS (
  SELECT
    'scv' AS source_table, s.id AS statement_id,
    REGEXP_REPLACE(s.proposition, r'^#/[^/]+/', '') AS proposition_id,
    s.classification.name AS classification_name, s.strength.name AS strength_name,
    s.quality.name AS quality_name, s.direction,
    (SELECT REGEXP_REPLACE(c.contributor, r'^#/[^/]+/', '') FROM UNNEST(s.contributions) AS c
       WHERE c.activityType = 'submitted' LIMIT 1) AS submitter_id,
    (SELECT c.date FROM UNNEST(s.contributions) AS c
       WHERE c.activityType = 'evaluated' LIMIT 1) AS date_last_evaluated,
    ARRAY(SELECT r.pmid FROM UNNEST(s.reportedIn) AS r WITH OFFSET AS o
          WHERE r.pmid IS NOT NULL ORDER BY o) AS pmids,
    ARRAY(
      SELECT AS STRUCT k.citation_id, k.citation_type, x.citation_role, x.d.pmid
      FROM (
        SELECT IF(EXISTS(SELECT 1 FROM UNNEST(d.extensions) AS e
                         WHERE e.name = 'clinvarAssertionMethodCitation'), 'method', 'evidence') AS citation_role, d
        FROM UNNEST(s.reportedIn) AS d
        UNION ALL
        SELECT 'method', s.specifiedBy.reportedIn
        FROM UNNEST([1]) WHERE s.specifiedBy.reportedIn IS NOT NULL
      ) AS x,
      UNNEST(ARRAY_CONCAT(
        IF(x.d.pmid IS NULL, [], [STRUCT(CONCAT('pmid:', x.d.pmid) AS citation_id, 'pmid' AS citation_type)]),
        IF(x.d.doi IS NULL, [], [STRUCT(CONCAT('doi:', x.d.doi), 'doi')]),
        ARRAY(SELECT AS STRUCT CONCAT('url:', u), 'url' FROM UNNEST(x.d.urls) AS u
              WHERE u != CONCAT('https://pubmed.ncbi.nlm.nih.gov/', IFNULL(x.d.pmid, ''))
                AND u != CONCAT('https://doi.org/', IFNULL(x.d.doi, '')))
      )) AS k
    ) AS citation_keys,
    ARRAY(SELECT REGEXP_REPLACE(el, r'^#/[^/]+/', '') FROM UNNEST(s.hasEvidenceLines) AS el) AS evidence_line_ids
  FROM `{DATASET}.gkm_dict_scv` AS s
  UNION ALL
  SELECT
    'vcv', v.id, REGEXP_REPLACE(v.proposition, r'^#/[^/]+/', ''),
    v.classification.name, v.strength.name, v.quality.name, v.direction,
    CAST(NULL AS STRING), CAST(NULL AS DATE), CAST([] AS ARRAY<STRING>),
    CAST([] AS ARRAY<STRUCT<citation_id STRING, citation_type STRING, citation_role STRING, pmid STRING>>),
    CAST([] AS ARRAY<STRING>)
  FROM `{DATASET}.gkm_dict_vcv` AS v
  UNION ALL
  SELECT
    'rcv', r.id, REGEXP_REPLACE(r.proposition, r'^#/[^/]+/', ''),
    r.classification.name, r.strength.name, r.quality.name, r.direction,
    CAST(NULL AS STRING), CAST(NULL AS DATE), CAST([] AS ARRAY<STRING>),
    CAST([] AS ARRAY<STRUCT<citation_id STRING, citation_type STRING, citation_role STRING, pmid STRING>>),
    CAST([] AS ARRAY<STRING>)
  FROM `{DATASET}.gkm_dict_rcv` AS r
),
-- core: the 17 published core columns, then helper columns no file publishes as-is.
core AS (
  SELECT
    p.variant_id, st.source_table, st.statement_id, p.proposition_type, p.predicate, p.object_id,
    p.condition_qualifier_id, p.gene_context_name, p.mode_of_inheritance, p.penetrance,
    st.classification_name, st.strength_name, st.quality_name, st.direction,
    st.submitter_id, st.date_last_evaluated, st.pmids,
    p.gene_context_id, p.submitted_gene_symbols, st.citation_keys, st.evidence_line_ids
  FROM stmt AS st
  JOIN prop AS p ON p.proposition_id = st.proposition_id
)
```

### `_concept-sets.sql` (fragment)

```sql
-- Shared CTEs for concept sets (spliced in where a file says {CONCEPT_SETS}).
-- sets: condition sets (the published >1-member filter) and therapy groups, members as bare ids
-- (traitset members are stored as '#/condition/…' pointers; minted-set members are already bare).
sets AS (
  SELECT id AS set_id, 'conditionSet' AS set_type, conceptSetType AS concept_set_type,
         membershipOperator AS membership_operator,
         ARRAY(SELECT REGEXP_REPLACE(c, r'^#/[^/]+/', '') FROM UNNEST(concepts) AS c) AS concepts
  FROM `{DATASET}.gkm_dict_condition_set`
  WHERE ARRAY_LENGTH(concepts) > 1
  UNION ALL
  SELECT key, 'therapyGroup', CAST(NULL AS STRING), JSON_VALUE(value, '$.membershipOperator'),
         ARRAY(SELECT REGEXP_REPLACE(JSON_VALUE(c), r'^#/[^/]+/', '')
               FROM UNNEST(JSON_QUERY_ARRAY(value, '$.concepts')) AS c)
  FROM `{DATASET}.gkm_dict_therapygroup`
),
-- membership: direct members, plus the leaves of a nested set flattened one level
-- (only minted clinvar.conditionset sets nest clinvar.traitset sets).
membership AS (
  SELECT s.set_id, s.set_type, s.concept_set_type, s.membership_operator,
         m AS member_concept_id, CAST(NULL AS STRING) AS via_nested_set_id
  FROM sets AS s, UNNEST(s.concepts) AS m
  UNION ALL
  SELECT o.set_id, o.set_type, o.concept_set_type, o.membership_operator,
         im AS member_concept_id, n.set_id AS via_nested_set_id
  FROM sets AS o
  CROSS JOIN UNNEST(o.concepts) AS m
  JOIN sets AS n ON n.set_id = m
  CROSS JOIN UNNEST(n.concepts) AS im
)
```

### `statement-by-variant.sql`

```sql
-- statement-by-variant: one row per SCV/VCV/RCV statement. Merge-step sort:
-- variant_id, source_table, statement_id.
WITH {STATEMENT_CORE}
SELECT * EXCEPT (gene_context_id, submitted_gene_symbols, citation_keys, evidence_line_ids)
FROM core
```

### `statement-by-object.sql`

```sql
-- statement-by-object: one row per (statement, concept). A concept is the proposition's object when that
-- is a single condition or therapy (role = object); each leaf member of the set/group it names
-- (role = set_member, via_set_id + membership_operator, via_nested_set_id when reached through a nested
-- traitset); and a therapeutic proposition's conditionQualifier (role = condition_qualifier). Propositions
-- an SCV's evidence lines target are included with via_evidence_line = TRUE (the only route to therapies);
-- those rows also carry the evidence line's own outcome and direction, since the statement's
-- classification is about the statement's proposition, not the targeted one.
-- A proposition with a NULL object gives one role = object row with concept_id NULL, concept_type 'none'.
-- Merge-step sort: concept_id NULLS LAST, variant_id, source_table, statement_id, via_evidence_line, role,
-- via_set_id NULLS FIRST, via_nested_set_id NULLS FIRST.
WITH {STATEMENT_CORE}, {CONCEPT_SETS},
stmt_prop AS (
  SELECT c.* EXCEPT (gene_context_id, submitted_gene_symbols, citation_keys, evidence_line_ids),
         FALSE AS via_evidence_line,
         CAST(NULL AS STRING) AS evidence_outcome_name, CAST(NULL AS STRING) AS evidence_direction
  FROM core AS c
  UNION ALL
  SELECT p.variant_id, c.source_table, c.statement_id, p.proposition_type, p.predicate, p.object_id,
         p.condition_qualifier_id, p.gene_context_name, p.mode_of_inheritance, p.penetrance,
         c.classification_name, c.strength_name, c.quality_name, c.direction,
         c.submitter_id, c.date_last_evaluated, c.pmids, TRUE AS via_evidence_line,
         el.evidenceOutcome.name AS evidence_outcome_name, el.directionOfEvidenceProvided AS evidence_direction
  FROM core AS c
  CROSS JOIN UNNEST(c.evidence_line_ids) AS el_id
  JOIN `{DATASET}.gkm_dict_evidence_line` AS el ON el.id = el_id
  JOIN prop AS p ON p.proposition_id = REGEXP_REPLACE(el.targetProposition, r'^#/[^/]+/', '')
),
typed AS (
  SELECT sp.*,
         CASE WHEN sp.object_id IS NULL THEN 'none'   -- 4 propositions have no object; keep their rows
              WHEN STARTS_WITH(sp.object_id, 'clinvar.trait:') THEN 'condition'
              WHEN STARTS_WITH(sp.object_id, 'clinvar.therapy:') THEN 'therapy'
              ELSE 'set' END AS object_kind
  FROM stmt_prop AS sp
)
SELECT t.object_id AS concept_id, t.object_kind AS concept_type, 'object' AS role,
       CAST(NULL AS STRING) AS via_set_id, CAST(NULL AS STRING) AS membership_operator,
       CAST(NULL AS STRING) AS via_nested_set_id, t.* EXCEPT (object_kind)
FROM typed AS t
WHERE t.object_kind <> 'set'
UNION ALL
SELECT m.member_concept_id,
       IF(STARTS_WITH(m.member_concept_id, 'clinvar.therapy:'), 'therapy', 'condition'),
       'set_member', t.object_id, m.membership_operator, m.via_nested_set_id, t.* EXCEPT (object_kind)
FROM typed AS t
JOIN membership AS m ON m.set_id = t.object_id
WHERE t.object_kind = 'set'
  AND (STARTS_WITH(m.member_concept_id, 'clinvar.trait:') OR STARTS_WITH(m.member_concept_id, 'clinvar.therapy:'))
UNION ALL
SELECT t.condition_qualifier_id, 'condition', 'condition_qualifier',
       CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING), t.* EXCEPT (object_kind)
FROM typed AS t
WHERE t.condition_qualifier_id IS NOT NULL
```

### `concept-set-membership.sql`

```sql
-- concept-set-membership: one row per (set, member) for every condition set and therapy group, with
-- nested-set leaves flattened (via_nested_set_id). Merge-step sort:
-- member_concept_id, set_id, via_nested_set_id NULLS FIRST.
WITH {CONCEPT_SETS},
names AS (
  SELECT id, name FROM `{DATASET}.gkm_dict_condition`
  UNION ALL
  SELECT key, JSON_VALUE(value, '$.name') FROM `{DATASET}.gkm_dict_therapy`
)
SELECT DISTINCT
  m.member_concept_id,
  CASE WHEN STARTS_WITH(m.member_concept_id, 'clinvar.trait:') THEN 'condition'
       WHEN STARTS_WITH(m.member_concept_id, 'clinvar.therapy:') THEN 'therapy'
       ELSE 'set' END AS member_type,
  nm.name AS member_name,
  m.set_id, m.set_type, m.concept_set_type, m.membership_operator, m.via_nested_set_id
FROM membership AS m
LEFT JOIN names AS nm ON nm.id = m.member_concept_id
```

### `variant-gene.sql`

```sql
-- variant-gene: ClinVar's variant-to-gene list (the variation's clinvarGeneList extension), one row per
-- (gene, variant, relationship). Describes the variant, not any statement. Merge-step sort:
-- gene_id, variant_id, relationship_type, relationship_source.
SELECT
  REGEXP_REPLACE(g.gene, r'^#/[^/]+/', '') AS gene_id,
  JSON_VALUE(gn.value, '$.name') AS gene_symbol,
  v.id AS variant_id,
  g.relationship_type,
  g.source AS relationship_source
FROM `{DATASET}.gkm_dict_variation` AS v
CROSS JOIN UNNEST(v.extensions) AS e
CROSS JOIN UNNEST(e.value_gene_array) AS g
LEFT JOIN `{DATASET}.gkm_dict_gene` AS gn ON gn.key = REGEXP_REPLACE(g.gene, r'^#/[^/]+/', '')
WHERE e.name = 'clinvarGeneList'
```

### `statement-by-gene-context.sql`

```sql
-- statement-by-gene-context: statements whose proposition carries a geneContextQualifier (SCV only today).
-- gene_context_id is the qualifier's own primaryCoding.code (NULL for the 'submitted genes were not
-- normalized' placeholder). Merge-step sort: gene_context_id NULLS LAST, variant_id, source_table, statement_id.
WITH {STATEMENT_CORE}
SELECT gene_context_id, gene_context_name, submitted_gene_symbols,
       * EXCEPT (gene_context_id, gene_context_name, submitted_gene_symbols, citation_keys, evidence_line_ids)
FROM core
WHERE gene_context_name IS NOT NULL
```

### `statement-by-citation.sql`

```sql
-- statement-by-citation: one row per (typed citation id, SCV statement, role). citation_id is pmid:/doi:/url:
-- (§5); a multi-id Document gives one row per id; text-only Documents have no key and are absent.
-- DISTINCT drops a key one SCV lists twice in the same role.
-- Merge-step sort: citation_id, citation_role, source_table, statement_id.
WITH {STATEMENT_CORE}
SELECT DISTINCT
  k.citation_id, k.citation_type, k.citation_role, k.pmid,
  c.* EXCEPT (pmids, gene_context_id, submitted_gene_symbols, citation_keys, evidence_line_ids)
FROM core AS c, UNNEST(c.citation_keys) AS k
WHERE c.source_table = 'scv'
```

---

## Implementation tasks (after the decisions)

Base: `1.0` for the scripts and SQL, with a paired `main` docs PR. Size: L as a family. The files can ship
one at a time; `statement-by-variant` goes first.

- [ ] **1.** Add the SQL files and fragments above, adjusted for the decisions.
- [ ] **2.** `export-gkm-dicts.sh`:
  - fragment splicing
  - full-mode-only exports
  - fix the ONE-table comment
- [ ] **3.** `release-gkm.sh` step 3: sorted merge + gate per file (§6), with `--month-label` passed into
  `KV_METADATA`. Validate with `bash -n` and `shellcheck`.
- [ ] **4.** `generate-r2-index.sh`: the `parquet` file list on month-set entries. `r2-browser.js`: render it.
- [ ] **5.** Dry-run the release. Then do a real export to a scratch GCS prefix and gate it.
- [ ] **6.** Compare aggregates against the section files of the same set: the same breakdowns as the
  Measurements tables.
- [ ] **7.** Console check, with no R2 writes:
  - serve the files locally with CORS and range support
  - point a local docs build's console at them
  - confirm each example stays under ~20 requests in DuckDB-Wasm 1.29.0
- [ ] **8.** Publish with the next monthly set. Backfill 2026-07 … 2026-10 per §9, with each live write
  confirmed.
- [ ] **9.** Docs per §10, merged in the same window as step 8.
