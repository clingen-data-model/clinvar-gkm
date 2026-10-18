# Joining Tables

!!! info "Release"
    Outputs, counts and timings on this page are from the **2026-10 monthly release** (published 14 Oct 2026), run with DuckDB 1.5 on a laptop against downloaded files. Re-run a query to get today's numbers.

The 22 tables connect in five places, the **seams**. Two are plain foreign keys. The other three hide the trap that causes most wrong answers: a column whose values point at **more than one table**, distinguished only by the id's prefix or a type column. Join just one branch and the rows for the others disappear without an error.

<iframe src="../assets/diagrams/parquet-join-seams.html" style="width:100%; height:760px; border:1px solid rgba(128,128,128,.25); border-radius:6px;" title="ClinVar-GKM Parquet join seams" loading="lazy"></iframe>

Every query on this page runs against **downloaded** files; the joins read multi-GB tables, which is too much for the [live console](index.md#run-a-query-now). Each runs in about a second or less unless noted. Each table name links to its entry in the [column reference](tables.md#column-reference).

## Seam A · Variant → Proposition

Every proposition has a subject, and every subject is a [`variation`](tables.md#variation) id: 27,655,456 references, all resolving. The four proposition tables share one column schema (from 1.1.0), so one glob reads them all as a single table, `subject_variant_id` included. `filename = true` adds the file each row came from:

```sql
-- One variant, every proposition, from all four tables
SELECT v.id, v.name,
       regexp_extract(p.filename, 'proposition[A-Za-z]+') AS prop_table,
       p.type, count(*) AS propositions
FROM 'variation.parquet' v
JOIN read_parquet('proposition*.parquet', filename = true) p ON p.subject_variant_id = v.id
WHERE v.id = 'clinvar:10'
GROUP BY ALL
ORDER BY propositions DESC;
```

```text
id          name                                    prop_table                type                             propositions
clinvar:10  NM_000410.4(HFE):c.187C>G (p.His63Asp)  propositionPathogenicity  VariantPathogenicityProposition  79
clinvar:10  NM_000410.4(HFE):c.187C>G (p.His63Asp)  propositionClinvarCustom  ClinvarNotProvidedProposition    12
clinvar:10  NM_000410.4(HFE):c.187C>G (p.His63Asp)  propositionClinvarCustom  ClinvarRiskFactorProposition      5
clinvar:10  NM_000410.4(HFE):c.187C>G (p.His63Asp)  propositionClinvarCustom  ClinvarOtherProposition           5
```

!!! warning "The trap"
    Reading `propositionPathogenicity` alone, the obvious table for "what is claimed about this variant", returns **79** of this variant's **101** propositions. It misses the risk-factor, not-provided and other claims, with no error. Read `proposition*.parquet` unless you mean only pathogenicity.

## Seam B · Proposition → Condition or ConditionSet

A proposition's object is in `object_id`, and `object_type` names the table it points at. Across all four tables:

| `object_type` | Joins to | References |
| --- | --- | ---: |
| `condition` | [`condition`](tables.md#condition).`id` (`clinvar.trait:<n>`) | 24,751,730 |
| `conditionSet` | [`conditionSet`](tables.md#conditionSet).`id`: an accessioned ClinVar TraitSet (`clinvar.traitset:<n>`) or a set minted for a VCV aggregate (`clinvar.conditionset:vcv-<md5>`) | 2,903,713 |
| `therapy` | [`therapy`](tables.md#therapy).`key` | 6 |
| `therapyGroup` | [`therapyGroup`](tables.md#therapyGroup).`key` | 7 |

Every reference resolves. Even a tumor type is not always a single condition: 12 `propositionOncogenicity` rows name a minted condition set. The 13 therapeutic-response propositions put their tumor type in `condition_qualifier_id` instead, which always names a `condition`. Join each branch on `object_type`, and `LEFT JOIN` so a lost row shows up as `UNRESOLVED` instead of vanishing:

```sql
-- Resolve an object id to a name: condition.name, or the set's members joined by ';'
WITH set_names AS (
    SELECT cs.id, string_agg(c.name, '; ') AS member_names
    FROM 'conditionSet.parquet' cs, unnest(cs.concepts) AS t(cid)
    LEFT JOIN 'condition.parquet' c ON c.id = cid
    GROUP BY cs.id
)
SELECT DISTINCT p.object_id, p.object_type,
    coalesce(c.name, sn.member_names, 'UNRESOLVED') AS condition_name
FROM 'propositionPathogenicity.parquet' p
LEFT JOIN 'condition.parquet' c  ON p.object_type = 'condition'    AND c.id  = p.object_id
LEFT JOIN set_names           sn ON p.object_type = 'conditionSet' AND sn.id = p.object_id
WHERE p.object_id IN (
    'clinvar.trait:16789', 'clinvar.traitset:10013',
    'clinvar.conditionset:vcv-c620785e2025efde81bdd15c814fa83d')
ORDER BY p.object_type;
```

```text
object_id                                                  object_type   condition_name
clinvar.trait:16789                                        condition     not specified
clinvar.traitset:10013                                     conditionSet  GM1 gangliosidosis; Mucopolysaccharidosis, MPS-IV-B
clinvar.conditionset:vcv-c620785e2025efde81bdd15c814fa83d  conditionSet  Epidermodysplasia verruciformis; Inborn genetic diseases
```

!!! warning "The trap"
    `JOIN 'condition.parquet' c ON c.id = p.object_id` (an inner join to `condition` only) keeps **24,556,081** of the 27,447,072 `propositionPathogenicity` rows. The **2.9 million** whose object is a set (10.5 %) silently disappear.

### Expanding a set to its member names

`conditionSet.concepts` holds member **ids**, not names. Parquet keeps them as bare ids. In the bundle and the
`data` column they are `#/condition/…` or `#/conditionSet/…` pointers from 1.1.0 (before, minted sets listed
bare ids there). Printing the list gives you ids:

```sql
SELECT id, membershipOperator, array_to_string(concepts, '; ') AS members
FROM 'conditionSet.parquet'
WHERE id = 'clinvar.traitset:10013';
```

```text
id                      membershipOperator  members
clinvar.traitset:10013  AND                 clinvar.trait:2965; clinvar.trait:7352
```

To get names, `unnest` the list and join each member to `condition`, as `set_names` does above. Two more things matter:

- **`membershipOperator` changes what the set asserts.** `AND` means the members together (a TraitSet describing one patient presentation); `OR` means any of them (every set minted for a VCV aggregate is `OR`). Carry it as its own column next to the names.
- **A minted set can contain a TraitSet.** 26,033 of the 83,538 minted sets list a `clinvar.traitset:` id among their members, so expansion goes one level deeper than it looks. It never goes further; TraitSets contain only traits.

This version handles the nesting:

```sql
WITH m1 AS (                                   -- direct members
  SELECT cs.id AS set_id, cs.membershipOperator AS op, cid AS member
  FROM 'conditionSet.parquet' cs, unnest(cs.concepts) AS t(cid)
),
m2 AS (                                        -- a member that is itself a TraitSet -> its members
  SELECT m1.set_id, m1.op, coalesce(inner_cid, m1.member) AS trait_id
  FROM m1
  LEFT JOIN (SELECT cs.id AS sid, cid AS inner_cid
             FROM 'conditionSet.parquet' cs, unnest(cs.concepts) AS t(cid)) n
         ON n.sid = m1.member
)
SELECT m2.set_id, m2.op,
       string_agg(DISTINCT c.name, '; ' ORDER BY c.name) AS member_names,
       count(*) FILTER (WHERE c.id IS NULL) AS unresolved
FROM m2
LEFT JOIN 'condition.parquet' c ON c.id = m2.trait_id
WHERE m2.set_id = 'clinvar.conditionset:vcv-0004f99fad9020b992e544614b5fb995'
GROUP BY ALL;
```

```text
set_id                                                     op  member_names                                                                                                          unresolved
clinvar.conditionset:vcv-0004f99fad9020b992e544614b5fb995  OR  Developmental delay with or without dysmorphic facies and autism; TRAPP-associated developmental delay; not provided  0
```

That set's members are two traits and `clinvar.traitset:55931`, whose own members contribute the third name. Flattening like this is right for a label. If the meaning matters, keep the nested set as a unit, since its members are `AND`-ed within an `OR` set.

## Seam C · Proposition → Statements (1 : 1)

Each statement table (`scv`, `rcv`, `vcv`) has a `proposition_id`, and a proposition has **at most one** statement: 27,653,888 references, 27,653,888 distinct ids. Treat the proposition as a side table of its statement.

A proposition id's classification code names its table (`PATH` → `propositionPathogenicity`, `ONCO` → `propositionOncogenicity`, and so on; see the [code table](tables.md#reading-a-variants-statements)). A query over every statement spans all four, so join the glob:

```sql
-- Where every statement's proposition lives
WITH stmt AS (
  SELECT 'scv' AS tier, proposition_id FROM 'scv.parquet'
  UNION ALL SELECT 'rcv', proposition_id FROM 'rcv.parquet'
  UNION ALL SELECT 'vcv', proposition_id FROM 'vcv.parquet'
)
SELECT s.tier,
       coalesce(regexp_extract(p.filename, 'proposition[A-Za-z]+'), 'UNRESOLVED') AS prop_table,
       count(*) AS statements
FROM stmt s
LEFT JOIN read_parquet('proposition*.parquet', filename = true) p ON p.id = s.proposition_id
GROUP BY ALL ORDER BY s.tier, statements DESC;
```

```text
tier  prop_table                        statements
rcv   propositionPathogenicity          11,753,254
rcv   propositionClinvarCustom              77,087
rcv   propositionSomaticClinicalImpact       5,239
rcv   propositionOncogenicity                3,848
scv   propositionPathogenicity           6,692,530
scv   propositionClinvarCustom              38,805
scv   propositionOncogenicity                1,924
scv   propositionSomaticClinicalImpact       1,752
vcv   propositionPathogenicity           9,001,288
vcv   propositionClinvarCustom              70,290
vcv   propositionSomaticClinicalImpact       4,048
vcv   propositionOncogenicity                3,823
```

Each tier's four rows sum to its exact row count, and nothing is `UNRESOLVED`. The 1,568 other `propositionSomaticClinicalImpact` rows (the diagnostic, prognostic and therapeutic-response propositions) have no statement: they are reached through SCI evidence lines (`evidenceLine.target_proposition_id`).

!!! warning "The trap"
    Joining statements to `propositionPathogenicity` alone drops **42,481** SCVs, **86,174** RCV statements and **78,161** VCV statements: every non-pathogenicity germline call, every somatic clinical-impact call and every oncogenicity call.

The [column-reference entry for `scv`](tables.md#scv) lists what each statement carries. To query statements directly by their proposition's subject, object or qualifiers without repeating this join, [materialize it once](performance.md#materialize-join-tables).

## Seam D · Inside an aggregate

A VCV (or RCV) accession is not one statement but a small tree. Each **root** statement (`…-G-PATH`) cites its **level** statements (`…-G-PATH-CP`, `…-G-PATH-NOCP`, …) through an evidence line, and each level statement cites the **SCVs** at that level. SCVs cite nothing.

The edge is `has_evidence_lines` (statement → evidence-line ids) followed by `evidence_items` (evidence line → cited ids):

```sql
-- One aggregate group: what each VCV statement cites, and whether it counts
SELECT s.id AS statement,
       el.strengthOfEvidenceProvided.name AS counts_toward_call,
       count(*) AS cites,
       string_agg(CASE WHEN item LIKE 'VCV%' THEN item END, ', ' ORDER BY item) AS cited_statements
FROM (SELECT id, unnest(has_evidence_lines) AS el_id
      FROM 'vcv.parquet' WHERE id LIKE 'VCV000000010.%') s
JOIN (SELECT id, strengthOfEvidenceProvided, unnest(evidence_items) AS item
      FROM 'vcv_evidenceLine.parquet') el ON el.id = s.el_id
GROUP BY ALL ORDER BY 1, 2;
```

```text
statement                     counts_toward_call  cites  cited_statements
VCV000000010.141-G-NP         Contributing        1      VCV000000010.141-G-NP-NOCL
VCV000000010.141-G-NP-NOCL    Contributing        4
VCV000000010.141-G-OTH        Contributing        1      VCV000000010.141-G-OTH-CP
VCV000000010.141-G-OTH-CP     Contributing        1
VCV000000010.141-G-PATH       Contributing        1      VCV000000010.141-G-PATH-CP
VCV000000010.141-G-PATH       Non-contributing    2      VCV000000010.141-G-PATH-FLAG, VCV000000010.141-G-PATH-NOCP
VCV000000010.141-G-PATH-CP    Contributing        45
VCV000000010.141-G-PATH-FLAG  Contributing        2
VCV000000010.141-G-PATH-NOCP  Contributing        8
VCV000000010.141-G-RF         Contributing        1      VCV000000010.141-G-RF-NOCP
VCV000000010.141-G-RF-NOCP    Contributing        1
```

The root `…-G-PATH` statement shows the aggregation rule at work. Its call comes from the highest level present, here `-CP` (criteria provided) with 45 SCVs. The 8 `-NOCP` SCVs and the 2 flagged ones are cited but marked **Non-contributing**. [Reading a variant's statements](tables.md#reading-a-variants-statements) explains the levels and their precedence.

## Seam E · Every SCV to its aggregate, in one pass

You don't need to walk the tree to find which aggregate an SCV belongs to. The citing statement's own id begins with the accession, so one join of `has_evidence_lines` to `evidence_items`, keeping only SCV items, gives every pair:

```sql
CREATE TABLE scv_vcv AS
SELECT regexp_extract(s.id, '^VCV[0-9]+', 0) AS vcv_accession,
       s.id    AS vcv_statement_id,           -- keeps the level: -PG, -EP, -CP, -NOCP, -NOCL, -FLAG
       it.item AS scv_id
FROM (SELECT id, unnest(has_evidence_lines) AS el_id FROM 'vcv.parquet') s
JOIN (SELECT id, unnest(evidence_items)     AS item  FROM 'vcv_evidenceLine.parquet') it
     ON it.id = s.el_id
WHERE it.item LIKE 'clinvar.submission:%';

SELECT * FROM scv_vcv WHERE vcv_accession = 'VCV000000010' ORDER BY vcv_statement_id, scv_id LIMIT 6;
```

```text
vcv_accession  vcv_statement_id            scv_id
VCV000000010   VCV000000010.141-G-NP-NOCL  clinvar.submission:SCV000020169.9
VCV000000010   VCV000000010.141-G-NP-NOCL  clinvar.submission:SCV000245789.3
VCV000000010   VCV000000010.141-G-NP-NOCL  clinvar.submission:SCV000607203.6
VCV000000010   VCV000000010.141-G-NP-NOCL  clinvar.submission:SCV001749317.2
VCV000000010   VCV000000010.141-G-OTH-CP   clinvar.submission:SCV000227124.6
VCV000000010   VCV000000010.141-G-PATH-CP  clinvar.submission:SCV000219176.11
```

The build takes under a second and yields **6,735,011** pairs, exactly one per SCV: every SCV is cited by exactly one VCV level statement. Keep `vcv_statement_id`, not just the accession; its suffix is what tells a `-CP` submission from a `-NOCP` or `-EP` one. Swap `vcv` for `rcv` to map SCVs to RCV accessions.

A useful identity: a VCV accession's number **is** the variation id. `VCV000000010` is `clinvar:10`, with no exceptions across all 9 million VCV propositions.

## Joins that lie

Every one of these returns a plausible answer with no error. Check them first when a count looks low.

!!! danger "Columns that point at more than one table"
    | Column | Points at | Dispatch on |
    | --- | --- | --- |
    | `object_id` on every proposition table | `condition`, `conditionSet`, `therapy` or `therapyGroup` | `object_type` |
    | `variation.members[]` | `allele`, `copyNumberCount`, or `copyNumberChange` | `ga4gh:VA.` / `ga4gh:CN.` / `ga4gh:CX.` |
    | `vcv_evidenceLine.evidence_items[]`, `rcv_evidenceLine.evidence_items[]` | an SCV, or another statement in the same table | `clinvar.submission:` vs `VCV`/`RCV` |

    Join every branch, or at least count the rows that matched nothing.

!!! note "Releases before 1.1.0 stored pointers, not ids"
    In releases before 1.1.0, `vartherapy-proposition.object_therapy` (now `propositionSomaticClinicalImpact.object_id`) held a JSON-quoted pointer (`"#/therapy/clinvar.therapy:…"`), and each variant gene-list entry held a `#/gene/ncbigene:…` pointer. Both now hold bare ids, and the 1.1.0 backfill rewrote the published Parquet for past releases. Parquet downloaded before the backfill still has the old tables and the old form. These expressions return the bare id from either form:

    ```sql
    regexp_replace(trim(p.object_therapy, '"'), '^#/[A-Za-z]+/', '')   -- -> clinvar.therapy:…
    replace(g.gene, '#/gene/', '')                                      -- -> ncbigene:…
    ```

!!! danger "The gene context is not the variant's genes"
    `gene_context_name` is a gene **symbol**, and symbols are not unique (`BTBD8` names two NCBI genes), so join on `gene_context_id`, its `ncbigene:` id (from 1.1.0). Both are filled in only on SCV propositions (6,655,967 of them) and are **NULL on every VCV and RCV proposition**, so filtering aggregates by them returns nothing. Both name **one representative gene per variant**, chosen upstream, not the genes the submitter named (those are in `submitted_gene_symbols`); see [Gene context](tables.md#gene-context). To find a gene's variants, use the variant's gene list, which carries `ncbigene:` ids, as in the [PubMed-ids-for-a-gene recipe](recipes.md#pubmed-ids-for-a-gene).

Next: [Recipes](recipes.md) puts these joins to work on real questions.
