# Joining Tables

!!! info "Release"
    Outputs on this page are from the **2026-10-31 release**, built with `gkm-bundle-parquet` 2.0.0. Whole-release
    counts were computed from the 2026-10-31 bundle, which the tables reproduce record for record; the query outputs
    come from tables built from a [selection](build-your-own.md#cut-a-mini-bundle) of that bundle that holds
    every record about the example variants. Re-run a query to get today's numbers.

The 20 tables connect in five places, the **seams**. Two are plain foreign keys. The other three hide the trap that causes most wrong answers: a column whose values point at **more than one table**. A `_section` column next to it names the table each value points at. Join just one branch and the rows for the others disappear without an error.

<iframe src="../assets/diagrams/parquet-join-seams.html" style="width:100%; height:760px; border:1px solid rgba(128,128,128,.25); border-radius:6px;" title="ClinVar-GKM Parquet join seams" loading="lazy"></iframe>

Every query on this page runs against **downloaded** files; the joins read the larger tables, which is too much for the [live console](index.md#run-a-query-now). Each table name links to its entry in the [column reference](tables.md#column-reference).

## Seam A · Variant → Proposition

Every proposition has a subject, and every subject is a [`variation`](tables.md#variation) id: 28,192,371 references in 2026-10-31. One glob reads the four proposition tables as a single table; `union_by_name = true` lines up their [different columns](tables.md#proposition-columns), and `filename = true` adds the file each row came from:

```sql
-- One variant, every proposition, from all four tables
SELECT v.id, v.name,
       regexp_extract(p.filename, 'proposition[A-Za-z]+') AS prop_table,
       p.type, count(*) AS propositions
FROM 'variation.parquet' v
JOIN read_parquet('proposition*.parquet', union_by_name = true, filename = true) p ON p.subject = v.id
WHERE v.id = 'clinvar:10'
GROUP BY ALL
ORDER BY propositions DESC;
```

```text
id          name                                    prop_table                type                             propositions
clinvar:10  NM_000410.4(HFE):c.187C>G (p.His63Asp)  propositionPathogenicity  VariantPathogenicityProposition            80
clinvar:10  NM_000410.4(HFE):c.187C>G (p.His63Asp)  propositionClinvarCustom  ClinvarNotProvidedProposition              12
clinvar:10  NM_000410.4(HFE):c.187C>G (p.His63Asp)  propositionClinvarCustom  ClinvarOtherProposition                     5
clinvar:10  NM_000410.4(HFE):c.187C>G (p.His63Asp)  propositionClinvarCustom  ClinvarRiskFactorProposition                5
```

!!! warning "The trap"
    Reading `propositionPathogenicity` alone, the obvious table for "what is claimed about this variant", returns **80** of this variant's **102** propositions. It misses the risk-factor, not-provided and other claims, with no error. Read `proposition*.parquet` unless you mean only pathogenicity.

## Seam B · Proposition → Condition or ConditionSet

A proposition's object is in `object`, and `object_section` names the table it points at. Across all four tables, in 2026-10-31:

| `object_section` | Joins to | References |
| --- | --- | ---: |
| `condition` | [`condition`](tables.md#condition).`id` (`clinvar.trait:<n>`) | 25,214,935 |
| `conditionSet` | [`conditionSet`](tables.md#conditionSet).`id`: an accessioned ClinVar TraitSet (`clinvar.traitset:<n>`) or a set minted for a VCV aggregate (`clinvar.conditionset:vcv-<md5>`) | 2,977,423 |
| `therapy` | [`therapy`](tables.md#therapy).`id` | 6 |
| `therapyGroup` | [`therapyGroup`](tables.md#therapyGroup).`id` | 7 |

Even a tumor type is not always a single condition: 32 `propositionOncogenicity` rows name a minted condition set. The 13 therapeutic-response propositions put their tumor type in `conditionQualifier` instead, which always names a `condition`. Join each branch on `object_section`, and `LEFT JOIN` so a lost row shows up as `UNRESOLVED` instead of vanishing:

```sql
-- Resolve an object id to a name: condition.name, or the set's members joined by ';'
WITH set_names AS (
    SELECT cs.id, string_agg(c.name, '; ' ORDER BY c.name) AS member_names
    FROM 'conditionSet.parquet' cs, unnest(cs.concepts) AS t(m)
    LEFT JOIN 'condition.parquet' c ON c.id = m.id
    GROUP BY cs.id
)
SELECT DISTINCT p.object, p.object_section,
    coalesce(c.name, sn.member_names, 'UNRESOLVED') AS condition_name
FROM 'propositionPathogenicity.parquet' p
-- CASE keeps each join an equi-join (fast); an AND in ON plans a nested loop
LEFT JOIN 'condition.parquet' c  ON c.id  = CASE WHEN p.object_section = 'condition'    THEN p.object END
LEFT JOIN set_names           sn ON sn.id = CASE WHEN p.object_section = 'conditionSet' THEN p.object END
WHERE p.object IN (
    'clinvar.trait:16789', 'clinvar.traitset:13451',
    'clinvar.conditionset:vcv-5f128f0653d9f37c2777f7f939c33528')
ORDER BY p.object_section, p.object;
```

```text
object                                                     object_section  condition_name
clinvar.trait:16789                                        condition       not specified
clinvar.conditionset:vcv-5f128f0653d9f37c2777f7f939c33528  conditionSet    Breast-ovarian cancer, familial, susceptibility to, 2; Hereditary cancer-predisposing syndrome; not provided; not specified
clinvar.traitset:13451                                     conditionSet    Alzheimer disease; Familial porphyria cutanea tarda; Hemochromatosis type 1; Microvascular complications of diabetes, susceptibility to, 7; TRANSFERRIN SERUM LEVEL QUANTITATIVE TRAIT LOCUS 2; Variegate porphyria
```

!!! warning "The trap"
    `JOIN 'condition.parquet' c ON c.id = p.object` (an inner join to `condition` only) keeps **25,016,660** of the 27,981,342 `propositionPathogenicity` rows. The **2.96 million** whose object is a set (10.6 %) silently disappear.

### Expanding a set to its member names

`conditionSet.concepts` is a list of `{id, section}` members, not names:

```sql
SELECT id, membershipOperator, array_to_string([m.id FOR m IN concepts], '; ') AS members
FROM 'conditionSet.parquet'
WHERE id = 'clinvar.traitset:13451';
```

```text
id                      membershipOperator  members
clinvar.traitset:13451  AND                 clinvar.trait:222; clinvar.trait:3370; clinvar.trait:5535; clinvar.trait:9582; clinvar.trait:9587; clinvar.trait:9601
```

To get names, `unnest` the list and join each member to `condition`, as `set_names` does above. Two more things matter:

- **`membershipOperator` changes what the set asserts.** `AND` means the members together (a TraitSet describing one patient presentation); `OR` means any of them (every set minted for a VCV aggregate is `OR`). Carry it as its own column next to the names.
- **A minted set can contain a TraitSet.** 28,776 of the 95,455 minted sets list a `clinvar.traitset:` member (`section` = `conditionSet`), so expansion goes one level deeper than it looks. It never goes further; TraitSets contain only traits.

This version handles the nesting:

```sql
WITH m1 AS (                                   -- direct members
  SELECT cs.id AS set_id, cs.membershipOperator AS op, m.id AS member, m.section
  FROM 'conditionSet.parquet' cs, unnest(cs.concepts) AS t(m)
),
m2 AS (                                        -- a member that is itself a TraitSet -> its members
  SELECT m1.set_id, m1.op, coalesce(n.inner_id, m1.member) AS trait_id
  FROM m1
  LEFT JOIN (SELECT cs.id AS sid, m.id AS inner_id
             FROM 'conditionSet.parquet' cs, unnest(cs.concepts) AS t(m)) n
         ON n.sid = CASE WHEN m1.section = 'conditionSet' THEN m1.member END
)
SELECT m2.set_id, m2.op,
       count(DISTINCT c.id) AS traits,
       string_agg(DISTINCT c.name, '; ' ORDER BY c.name) AS member_names,
       count(*) FILTER (WHERE c.id IS NULL) AS unresolved
FROM m2
LEFT JOIN 'condition.parquet' c ON c.id = m2.trait_id
WHERE m2.set_id = 'clinvar.conditionset:vcv-48e5fe986b5c30669858fd0b2177c4e6'
GROUP BY ALL;
```

```text
set_id                                                     op  traits  member_names                                                                                                                                                                                                                                                                                                       unresolved
clinvar.conditionset:vcv-48e5fe986b5c30669858fd0b2177c4e6  OR      11  Alzheimer disease; Cardiomyopathy; Familial porphyria cutanea tarda; Hemochromatosis type 1; Hereditary hemochromatosis; Microvascular complications of diabetes, susceptibility to, 7; Neuroendocrine neoplasm; See cases; TRANSFERRIN SERUM LEVEL QUANTITATIVE TRAIT LOCUS 2; Variegate porphyria; not provided           0
```

That set has seven traits and `clinvar.traitset:13451` as members; the TraitSet's six traits overlap two of them, so the set covers 11 distinct traits. Flattening like this is right for a label. If the meaning matters, keep the nested set as a unit, since its members are `AND`-ed within an `OR` set.

## Seam C · Proposition → Statements (1 : 1) { #seam-c-proposition-statements-1-1 }

Each statement table (`scv`, `rcv`, `vcv`) has a `proposition` column, and a proposition has **at most one** statement: in 2026-10-31, 28,190,803 statements point at 28,190,803 distinct propositions. Treat the proposition as a side table of its statement.

`proposition_section` names the table that holds the proposition, so a query about one kind of claim reads one file. A query over every statement spans all four; join the glob:

```sql
-- Where every statement's proposition lives
WITH stmt AS (
  SELECT 'scv' AS tier, proposition, proposition_section FROM 'scv.parquet'
  UNION ALL SELECT 'rcv', proposition, proposition_section FROM 'rcv.parquet'
  UNION ALL SELECT 'vcv', proposition, proposition_section FROM 'vcv.parquet'
)
SELECT s.tier, s.proposition_section,
       count(*) AS statements,
       count(*) FILTER (WHERE p.id IS NULL) AS unresolved
FROM stmt s
LEFT JOIN read_parquet('proposition*.parquet', union_by_name = true) p ON p.id = s.proposition
GROUP BY ALL ORDER BY s.tier, statements DESC;
```

On the 2026-10-31 release:

```text
tier  proposition_section               statements  unresolved
rcv   propositionPathogenicity          12,021,260           0
rcv   propositionClinvarCustom              77,089           0
rcv   propositionSomaticClinicalImpact       5,239           0
rcv   propositionOncogenicity                4,912           0
scv   propositionPathogenicity           6,838,781           0
scv   propositionClinvarCustom              38,806           0
scv   propositionOncogenicity                2,456           0
scv   propositionSomaticClinicalImpact       1,752           0
vcv   propositionPathogenicity           9,121,301           0
vcv   propositionClinvarCustom              70,294           0
vcv   propositionOncogenicity                4,865           0
vcv   propositionSomaticClinicalImpact       4,048           0
```

Each tier's four rows sum to its row count. The 1,568 other `propositionSomaticClinicalImpact` rows (the diagnostic, prognostic and therapeutic-response propositions) have no statement: they are reached through SCI evidence lines (`evidenceLine.targetProposition`).

!!! warning "The trap"
    Joining statements to `propositionPathogenicity` alone drops **43,014** SCVs, **87,240** RCV statements and **79,207** VCV statements: every non-pathogenicity germline call, every somatic clinical-impact call and every oncogenicity call.

The [column-reference entry for `scv`](tables.md#scv) lists what each statement carries. To query statements directly by their proposition's subject, object or qualifiers without repeating this join, [materialize it once](performance.md#materialize-join-tables).

## Seam D · Inside an aggregate

A VCV (or RCV) accession is not one statement but a small tree. Each **root** statement (`…-G-PATH`) cites its **level** statements (`…-G-PATH-CP`, `…-G-PATH-NOCP`, …) through an evidence line, and each level statement cites the **SCVs** at that level. SCVs cite nothing.

The edge is `hasEvidenceLines` (statement → evidence-line ids) followed by `hasEvidenceItems` (evidence line → cited `{id, section}`). All three kinds of evidence line are in the one [`evidenceLine`](tables.md#evidenceLine) table; a VCV statement's lines have ids starting with `VCV`:

```sql
-- One aggregate group: what each VCV statement cites, and whether it counts
SELECT s.id AS statement,
       el.strengthOfEvidenceProvided.name AS counts_toward_call,
       count(*) AS cites,
       string_agg(CASE WHEN item.section = 'vcv' THEN item.id END, ', ' ORDER BY item.id) AS cited_statements
FROM (SELECT id, unnest(hasEvidenceLines) AS el_id
      FROM 'vcv.parquet' WHERE id LIKE 'VCV000000010.%') s
JOIN (SELECT id, strengthOfEvidenceProvided, unnest(hasEvidenceItems) AS item
      FROM 'evidenceLine.parquet' WHERE id LIKE 'VCV000000010.%') el ON el.id = s.el_id
GROUP BY ALL ORDER BY 1, 2;
```

```text
statement                     counts_toward_call  cites  cited_statements
VCV000000010.142-G-NP         Contributing            1  VCV000000010.142-G-NP-NOCL
VCV000000010.142-G-NP-NOCL    Contributing            4
VCV000000010.142-G-OTH        Contributing            1  VCV000000010.142-G-OTH-CP
VCV000000010.142-G-OTH-CP     Contributing            1
VCV000000010.142-G-PATH       Contributing            1  VCV000000010.142-G-PATH-CP
VCV000000010.142-G-PATH       Non-contributing        2  VCV000000010.142-G-PATH-FLAG, VCV000000010.142-G-PATH-NOCP
VCV000000010.142-G-PATH-CP    Contributing           46
VCV000000010.142-G-PATH-FLAG  Contributing            2
VCV000000010.142-G-PATH-NOCP  Contributing            8
VCV000000010.142-G-RF         Contributing            1  VCV000000010.142-G-RF-NOCP
VCV000000010.142-G-RF-NOCP    Contributing            1
```

The root `…-G-PATH` statement shows the aggregation rule at work. Its call comes from the highest level present, here `-CP` (criteria provided). The `-NOCP` SCVs and the flagged ones are cited but marked **Non-contributing**. [Reading a variant's statements](tables.md#reading-a-variants-statements) explains the levels and their precedence.

Filtering `evidenceLine` by the accession prefix as well as `vcv` is what keeps this fast: rows are sorted by id, so the filter reads only the row groups for that accession.

## Seam E · Every SCV to its aggregate, in one pass

You don't need to walk the tree to find which aggregate an SCV belongs to. Every VCV evidence line's id begins with its statement's id, so one pass over `evidenceLine`, keeping only the SCV items, gives every pair:

```sql
CREATE TABLE scv_vcv AS
SELECT regexp_extract(el.id, '^VCV[0-9]+', 0)                  AS vcv_accession,
       regexp_replace(el.id, '\.(non-)?contributing$', '')     AS vcv_statement_id,  -- keeps the level: -PG, -EP, -CP, …
       item.id                                                 AS scv_id
FROM (SELECT id, unnest(hasEvidenceItems) AS item
      FROM 'evidenceLine.parquet' WHERE id LIKE 'VCV%') el
WHERE item.section = 'scv';

SELECT * FROM scv_vcv WHERE vcv_accession = 'VCV000000010' ORDER BY vcv_statement_id, scv_id LIMIT 6;
```

```text
vcv_accession  vcv_statement_id            scv_id
VCV000000010   VCV000000010.142-G-NP-NOCL  clinvar.submission:SCV000020169.9
VCV000000010   VCV000000010.142-G-NP-NOCL  clinvar.submission:SCV000245789.3
VCV000000010   VCV000000010.142-G-NP-NOCL  clinvar.submission:SCV000607203.6
VCV000000010   VCV000000010.142-G-NP-NOCL  clinvar.submission:SCV001749317.2
VCV000000010   VCV000000010.142-G-OTH-CP   clinvar.submission:SCV000227124.6
VCV000000010   VCV000000010.142-G-PATH-CP  clinvar.submission:SCV000219176.11
```

On the whole release this yields **6,881,795** pairs, exactly one per SCV: every SCV is cited by exactly one VCV level statement. Keep `vcv_statement_id`, not just the accession; its suffix is what tells a `-CP` submission from a `-NOCP` or `-EP` one. Swap `VCV` for `RCV` to map SCVs to RCV accessions.

A useful identity: a VCV accession's number **is** the variation id. `VCV000000010` is `clinvar:10`, with no exceptions across all 9,200,508 VCV propositions.

## Joins that lie

Every one of these returns a plausible answer with no error. Check them first when a count looks low.

!!! danger "Columns that point at more than one table"
    | Column | Points at | Dispatch on |
    | --- | --- | --- |
    | `object` on every proposition table | `condition`, `conditionSet`, `therapy` or `therapyGroup` | `object_section` |
    | `proposition` on `scv`, `vcv`, `rcv` | one of the four proposition tables | `proposition_section` |
    | `variation.members[]` | `allele`, `copyNumberCount`, or `copyNumberChange` | `members[].section` |
    | `conditionSet.concepts[]` | `condition`, or a nested `conditionSet` | `concepts[].section` |
    | `evidenceLine.hasEvidenceItems[]` | an SCV, or another statement in the same tier | `hasEvidenceItems[].section` |

    Join every branch, or at least count the rows that matched nothing.

!!! danger "The gene context is not the variant's genes"
    `geneContextQualifier.name` is a gene **symbol**, and symbols are not unique (`BTBD8` names two NCBI genes), so join on its NCBI Gene number, `'ncbigene:' || geneContextQualifier.primaryCoding.code`. The qualifier is filled in only on SCV propositions (6,843,043 of them) and is **NULL on every VCV and RCV proposition**, so filtering aggregates by it returns nothing. It names **one representative gene per variant**, chosen upstream, not the genes the submitter named (those are in its `submittedGeneSymbols` extension); see [Gene context](tables.md#gene-context). To find a gene's variants, use the variant's gene list, which carries `ncbigene:` ids, as in the [PubMed-ids-for-a-gene recipe](recipes.md#pubmed-ids-for-a-gene).

Next: [Recipes](recipes.md) puts these joins to work on real questions.
