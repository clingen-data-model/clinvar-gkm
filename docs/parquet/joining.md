# Joining Tables

!!! info "Release"
    Outputs, counts and timings on this page are from the **2026-10 monthly release** (published 14 Oct 2026), run with DuckDB 1.5 on a laptop against downloaded files. Re-run a query to get today's numbers.

The 22 tables connect in five places, the **seams**. Two are plain foreign keys. The other three hide the trap that causes most wrong answers: a column whose values point at **more than one table**, distinguished only by the id's prefix. Join just one branch and the rows for the others disappear without an error.

<iframe src="../assets/diagrams/parquet-join-seams.html" style="width:100%; height:760px; border:1px solid rgba(128,128,128,.25); border-radius:6px;" title="ClinVar-GKM Parquet join seams" loading="lazy"></iframe>

Every query on this page runs against **downloaded** files; the joins read multi-GB tables, which is too much for the [live console](index.md#run-a-query-now). Each runs in about a second or less unless noted. Each table name links to its entry in the [column reference](tables.md#column-reference).

## Seam A · Variant → Proposition

Every proposition has a subject, and every subject is a [`variation`](tables.md#variation) id: 27,655,456 references, all resolving. The catch is that the four proposition tables spell the subject column differently: `subject_variant_id` in three of them, `subject_id` in [`varcustom-proposition`](tables.md#varcustom-proposition).

Union the four tables **once**, renaming the column to one name, and reuse that union (`prop`) everywhere:

```sql
-- One variant, every proposition, from all four tables
WITH prop AS (
  SELECT id, type, predicate, subject_variant_id AS variant_id, 'varcond'    AS prop_table FROM 'varcond-proposition.parquet'
  UNION ALL SELECT id, type, predicate, subject_id,         'varcustom'  FROM 'varcustom-proposition.parquet'
  UNION ALL SELECT id, type, predicate, subject_variant_id, 'vartumor'   FROM 'vartumor-proposition.parquet'
  UNION ALL SELECT id, type, predicate, subject_variant_id, 'vartherapy' FROM 'vartherapy-proposition.parquet'
)
SELECT v.id, v.name, p.prop_table, p.type, count(*) AS propositions
FROM 'variation.parquet' v
JOIN prop p ON p.variant_id = v.id
WHERE v.id = 'clinvar:10'
GROUP BY ALL
ORDER BY propositions DESC;
```

```text
id          name                                    prop_table  type                             propositions
clinvar:10  NM_000410.4(HFE):c.187C>G (p.His63Asp)  varcond     VariantPathogenicityProposition  79
clinvar:10  NM_000410.4(HFE):c.187C>G (p.His63Asp)  varcustom   ClinvarNotProvidedProposition    12
clinvar:10  NM_000410.4(HFE):c.187C>G (p.His63Asp)  varcustom   ClinvarRiskFactorProposition      5
clinvar:10  NM_000410.4(HFE):c.187C>G (p.His63Asp)  varcustom   ClinvarOtherProposition           5
```

!!! warning "The trap"
    Joining `varcond-proposition` alone, the obvious table for "what is claimed about this variant", returns **79** of this variant's **101** propositions. It misses the risk-factor, not-provided and other claims, with no error.

## Seam B · Proposition → Condition or ConditionSet

The condition column of every proposition table points at one of two tables, and the prefix says which. The columns are `varcond-proposition.object_condition_id`, `varcustom-proposition.object_id`, `vartumor-proposition.object_tumor_type_id` and `vartherapy-proposition.condition_qualifier_id`. Across all four:

| Prefix | Joins to | References |
| --- | --- | ---: |
| `clinvar.trait:<n>` | [`condition`](tables.md#condition).`id` | 24,751,743 |
| `clinvar.traitset:<n>` | [`conditionSet`](tables.md#conditionSet).`id` (an accessioned ClinVar TraitSet) | 1,271,961 |
| `clinvar.conditionset:vcv-<md5>` | [`conditionSet`](tables.md#conditionSet).`id` (a set minted for a VCV aggregate) | 1,631,752 |

Every reference resolves, and no id matches both tables. Even the tumor-type column is not always a single condition: 12 `vartumor` propositions name a minted condition set. `LEFT JOIN` both and record which one matched, so a lost row shows up as `UNRESOLVED` instead of vanishing:

```sql
-- Resolve an object id to a name: condition.name, or the set's members joined by ';'
WITH set_names AS (
    SELECT cs.id, string_agg(c.name, '; ') AS member_names
    FROM 'conditionSet.parquet' cs, unnest(cs.concepts) AS t(cid)
    LEFT JOIN 'condition.parquet' c ON c.id = cid
    GROUP BY cs.id
)
SELECT DISTINCT p.object_condition_id,
    CASE WHEN c.id  IS NOT NULL THEN 'condition'
         WHEN sn.id IS NOT NULL THEN 'conditionSet' ELSE 'UNRESOLVED' END AS resolved_via,
    coalesce(c.name, sn.member_names) AS condition_name
FROM 'varcond-proposition.parquet' p
LEFT JOIN 'condition.parquet' c  ON c.id  = p.object_condition_id
LEFT JOIN set_names           sn ON sn.id = p.object_condition_id
WHERE p.object_condition_id IN (
    'clinvar.trait:16789', 'clinvar.traitset:10013',
    'clinvar.conditionset:vcv-c620785e2025efde81bdd15c814fa83d')
ORDER BY resolved_via;
```

```text
object_condition_id                                        resolved_via  condition_name
clinvar.trait:16789                                        condition     not specified
clinvar.traitset:10013                                     conditionSet  GM1 gangliosidosis; Mucopolysaccharidosis, MPS-IV-B
clinvar.conditionset:vcv-c620785e2025efde81bdd15c814fa83d  conditionSet  Epidermodysplasia verruciformis; Inborn genetic diseases
```

!!! warning "The trap"
    `JOIN 'condition.parquet' c ON c.id = p.object_condition_id` (an inner join to `condition` only) keeps **24,568,225** of the 27,459,666 `varcond` propositions. The **2.9 million** whose object is a set (10.5 %) silently disappear.

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

A proposition id's classification code names its table (`PATH` → `varcond-proposition`, `ONCO` → `vartumor-proposition`, and so on; see the [code table](tables.md#reading-a-variants-statements)). A query over every statement spans all four, so join the same four-table union:

```sql
-- Where every statement's proposition lives
WITH prop AS (
  SELECT id, 'varcond'    AS prop_table FROM 'varcond-proposition.parquet'
  UNION ALL SELECT id, 'varcustom'  FROM 'varcustom-proposition.parquet'
  UNION ALL SELECT id, 'vartumor'   FROM 'vartumor-proposition.parquet'
  UNION ALL SELECT id, 'vartherapy' FROM 'vartherapy-proposition.parquet'
),
stmt AS (
  SELECT 'scv' AS tier, proposition_id FROM 'scv.parquet'
  UNION ALL SELECT 'rcv', proposition_id FROM 'rcv.parquet'
  UNION ALL SELECT 'vcv', proposition_id FROM 'vcv.parquet'
)
SELECT s.tier, coalesce(p.prop_table, 'UNRESOLVED') AS prop_table, count(*) AS statements
FROM stmt s LEFT JOIN prop p ON p.id = s.proposition_id
GROUP BY ALL ORDER BY s.tier, statements DESC;
```

```text
tier  prop_table  statements
rcv   varcond     11,758,493
rcv   varcustom       77,087
rcv   vartumor         3,848
scv   varcond      6,694,282
scv   varcustom       38,805
scv   vartumor         1,924
vcv   varcond      9,005,336
vcv   varcustom       70,290
vcv   vartumor         3,823
```

Each tier's three rows sum to its exact row count, and nothing is `UNRESOLVED`. No statement points at `vartherapy-proposition`: those propositions are reached through SCI evidence lines (`evidenceLine.target_proposition_id`), as are the 1,555 `varcond` diagnostic and prognostic propositions that have no statement.

!!! warning "The trap"
    Joining statements to `varcond-proposition` alone drops **40,729** SCVs, **80,935** RCV statements and **74,113** VCV statements: every non-pathogenicity germline call and every somatic oncogenicity call.

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
    | `varcond-proposition.object_condition_id`, `varcustom-proposition.object_id`, `vartumor-proposition.object_tumor_type_id` | `condition` or `conditionSet` | `clinvar.trait:` vs `clinvar.traitset:` / `clinvar.conditionset:` |
    | `variation.members[]` | `allele`, `copyNumberCount`, or `copyNumberChange` | `ga4gh:VA.` / `ga4gh:CN.` / `ga4gh:CX.` |
    | `vartherapy-proposition.object_therapy` | `therapy` or `therapyGroup` | `clinvar.therapy:` vs `clinvar.therapygroup:` |
    | `vcv_evidenceLine.evidence_items[]`, `rcv_evidenceLine.evidence_items[]` | an SCV, or another statement in the same table | `clinvar.submission:` vs `VCV`/`RCV` |

    Join every branch, or at least count the rows that matched nothing.

!!! note "Releases before 1.1.0 stored pointers, not ids"
    In releases before 1.1.0, `vartherapy-proposition.object_therapy` held a JSON-quoted pointer (`"#/therapy/clinvar.therapy:…"`), and each variant gene-list entry held a `#/gene/ncbigene:…` pointer. Both now hold bare ids, and the backfill rewrote the published Parquet for past releases. Parquet downloaded before the backfill still has the old form. These expressions return the bare id from either form:

    ```sql
    regexp_replace(trim(p.object_therapy, '"'), '^#/[A-Za-z]+/', '')   -- -> clinvar.therapy:…
    replace(g.gene, '#/gene/', '')                                      -- -> ncbigene:…
    ```

!!! danger "The gene context is not the variant's genes"
    `gene_context_name` is a gene **symbol**, and symbols are not unique (`BTBD8` names two NCBI genes), so join on `gene_context_id`, its `ncbigene:` id (from 1.1.0). Both are filled in only on SCV propositions (6,655,967 of them) and are **NULL on every VCV and RCV proposition**, so filtering aggregates by them returns nothing. Both name **one representative gene per variant**, chosen upstream, not the genes the submitter named (those are in `submitted_gene_symbols`); see [Gene context](tables.md#gene-context). To find a gene's variants, use the variant's gene list, which carries `ncbigene:` ids, as in the [PubMed-ids-for-a-gene recipe](recipes.md#pubmed-ids-for-a-gene).

Next: [Recipes](recipes.md) puts these joins to work on real questions.
