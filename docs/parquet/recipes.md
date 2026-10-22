# Recipes

!!! info "Release"
    Outputs, timings and memory figures on this page are from the **2026-10 monthly release** (published 14 Oct 2026), run with DuckDB 1.5 on a laptop against downloaded files. Re-run a recipe to get today's numbers.

Each recipe answers one question: the question in plain language, a query you can run, and what to expect, including how long it takes and how much memory it uses. They run against **downloaded** files; each touches at least one multi-GB table, which is too much for the [live console](index.md#run-a-query-now). See [Start Here](index.md#put-the-file-on-your-machine) to download.

Change the line marked `-- <-` to ask about your own variant, condition, gene or submitter. [Joining Tables](joining.md) explains each join used here.

| Recipe | Time | Peak memory |
| --- | ---: | ---: |
| [Everything ClinVar says about one variant](#one-variant) | < 1 s | 0.6 GB |
| [PubMed ids cited for a variant](#pubmed-ids-for-a-variant) | < 1 s | 0.4 GB |
| [Variants submitted for a condition](#variants-for-a-condition) | < 1 s | 1.1 GB |
| [One submitter's footprint](#submitter-footprint) | < 1 s | 0.1 GB |
| [Why a variant is "conflicting"](#conflicting-classifications) | < 1 s | 0.3 GB |
| [Variants in a genomic window](#genomic-window) | < 1 s | 0.7 GB |
| [Gene rollup of ClinVar's calls](#gene-rollup) | 5 s | 1.6 GB |
| [PubMed ids cited for every variant in a gene](#pubmed-ids-for-a-gene) | 5 s | 1.5 GB |
| [Export a slice to CSV or Parquet](#export) | < 1 s | 0.4 GB |

## Everything ClinVar says about one variant { #one-variant }

### Find the variant

If you know the ClinVar variation id, you already have it: `clinvar:<id>`. Otherwise look it up by any HGVS expression ClinVar lists for it (coding `c.`, genomic `g.`, non-coding `n.`, on any transcript or assembly):

```sql
SELECT id, name
FROM 'variation.parquet'
WHERE list_contains(
        flatten([[h.nucleotideExpression.value FOR h IN e.value_hgvs_array] FOR e IN extensions]),
        'NM_000059.4:c.4090A>C');                                            -- <- your HGVS
```

```text
id             name
clinvar:51592  NM_000059.4(BRCA2):c.4090A>C (p.Ile1364Leu)
```

This scans every variant's HGVS list: about **4.5 s** and **1.4 GB**. For a GRCh38 genomic expression, the allele table is much faster (0.2 s):

```sql
SELECT v.id, v.name
FROM 'allele.parquet' a
JOIN (SELECT id, name, unnest(members) AS member FROM 'variation.parquet') v
     ON v.member = a.id                   -- an equality join; list_contains() in ON plans a nested loop
WHERE a.name = 'NC_000013.11:g.32338445A>C';
```

### ClinVar's aggregate calls

One row for each VCV root statement (one per classification type) and each RCV (one per condition), with the condition names resolved:

```sql
WITH prop AS (                    -- all four proposition tables: one shared schema, one glob
  SELECT id, type, subject_variant_id AS variant_id, object_id FROM read_parquet('proposition*.parquet')
),
set_names AS (
  SELECT cs.id, string_agg(c.name, '; ' ORDER BY c.name) AS member_names
  FROM 'conditionSet.parquet' cs, unnest(cs.concepts) AS t(cid)
  JOIN 'condition.parquet' c ON c.id = cid
  GROUP BY cs.id
),
agg AS (
  SELECT 'VCV' AS tier, id, proposition_id, quality.name AS level, classification.name AS classification FROM 'vcv.parquet'
  UNION ALL
  SELECT 'RCV', id, proposition_id, quality.name, classification.name FROM 'rcv.parquet'
)
SELECT a.tier, a.id AS statement, p.type AS proposition_type, a.level, a.classification,
       coalesce(c.name, sn.member_names) AS condition
FROM agg a
JOIN prop p ON p.id = a.proposition_id
LEFT JOIN 'condition.parquet' c ON c.id = p.object_id
LEFT JOIN set_names sn ON sn.id = p.object_id
WHERE p.variant_id = 'clinvar:51592'                                         -- <- your variant
  AND NOT regexp_matches(a.id, '-(PG|EP|CP|NOCP|NOCL|FLAG)(-T[0-9])?$')     -- root statements only
ORDER BY a.tier DESC, a.id;
```

```text
tier  statement                proposition_type                 level              classification        condition
VCV   VCV000051592.122-G-NP    ClinvarNotProvidedProposition    no classification  not provided          not specified
VCV   VCV000051592.122-G-PATH  VariantPathogenicityProposition  expert panel       Benign                Breast-ovarian cancer, familial, susceptibility to, 2
RCV   RCV000044344.34-G-PATH   VariantPathogenicityProposition  criteria provided  Benign                Hereditary breast ovarian cancer syndrome
RCV   RCV000113272.28-G-PATH   VariantPathogenicityProposition  expert panel       Benign                Breast-ovarian cancer, familial, susceptibility to, 2
…
```

Drop the root-statement filter to see each level statement as well (`-EP`, `-CP`, `-NOCP`, …); [Reading a variant's statements](tables.md#reading-a-variants-statements) explains them.

### Every submission

Who submitted, what they said, at what level, for which condition, and when they last evaluated it:

```sql
WITH prop AS (                    -- all four proposition tables: one shared schema, one glob
  SELECT id, type, subject_variant_id AS variant_id, object_id FROM read_parquet('proposition*.parquet')
),
set_names AS (
  SELECT cs.id, string_agg(c.name, '; ' ORDER BY c.name) AS member_names
  FROM 'conditionSet.parquet' cs, unnest(cs.concepts) AS t(cid)
  JOIN 'condition.parquet' c ON c.id = cid
  GROUP BY cs.id
)
SELECT replace(s.id, 'clinvar.submission:', '') AS scv,
       sub.name                AS submitter,
       s.classification.name   AS classification,
       s.quality.name          AS level,
       coalesce(c.name, sn.member_names) AS condition,
       [x.date FOR x IN s.contributions IF x.activityType = 'evaluated'][1] AS last_evaluated
FROM 'scv.parquet' s
JOIN prop p ON p.id = s.proposition_id
LEFT JOIN 'submitter.parquet' sub
       ON sub.id = [x.contributor FOR x IN s.contributions IF x.activityType = 'submitted'][1]
LEFT JOIN 'condition.parquet' c ON c.id = p.object_id
LEFT JOIN set_names sn ON sn.id = p.object_id
WHERE p.variant_id = 'clinvar:51592'                                         -- <- your variant
ORDER BY last_evaluated DESC;
```

```text
scv              submitter                                              classification  level              condition                                  last_evaluated
SCV000072357.18  Labcorp Genetics (formerly Invitae), Labcorp           Benign          criteria provided  Hereditary breast ovarian cancer syndrome  2026-02-03
SCV000602753.7   ARUP Laboratories, Molecular Genetics and Genomics, …  Benign          criteria provided  not provided                               2025-05-19
SCV004243027.2   Center for Genomic Medicine, Rigshospitalet, …         Benign          criteria provided  not specified                              2025-03-04
…
```

36 submissions for this variant. Each of these two queries takes under a second.

## PubMed ids cited for a variant { #pubmed-ids-for-a-variant }

PubMed ids appear only on **SCVs** (individual submissions), in `scv.reportedIn[].pmid`. The variant, VCV and RCV records carry none. So the query goes from the variant to its propositions, and from the propositions to the SCVs that cite them.

```sql
WITH v AS (
  SELECT id, name FROM 'variation.parquet' WHERE id = 'clinvar:10'         -- <- your variant
),
prop AS (                                     -- all four proposition tables, one glob
  SELECT id, subject_variant_id AS variant_id FROM read_parquet('proposition*.parquet')
),
cites AS (                                    -- one row per (SCV, cited PubMed id)
  SELECT p.variant_id, s.id AS scv_id, unnest(s.reportedIn).pmid AS pmid
  FROM 'scv.parquet' s
  JOIN prop p ON p.id = s.proposition_id
  WHERE p.variant_id IN (SELECT id FROM v)
)
SELECT v.id AS variant_id, v.name AS variant_name, c.pmid,
       'https://pubmed.ncbi.nlm.nih.gov/' || c.pmid AS pubmed_url,
       count(DISTINCT c.scv_id) AS n_scvs,
       string_agg(DISTINCT replace(c.scv_id, 'clinvar.submission:', ''), ', '
                  ORDER BY replace(c.scv_id, 'clinvar.submission:', '')) AS scvs
FROM cites c JOIN v ON v.id = c.variant_id
WHERE c.pmid IS NOT NULL
GROUP BY ALL
ORDER BY n_scvs DESC, c.pmid;
```

For `clinvar:10`, NM_000410.4(HFE):c.187C>G (p.His63Asp), the most-cited PubMed ids, each with the SCVs that cite it. Selected columns:

```text
pmid      n_scvs  scvs
19159930  5       SCV000198337.5, SCV001194094.2, SCV001251532.1, SCV001519563.1, SCV002568070.8
8696333   5       SCV000461883.3, SCV001519563.1, SCV002502480.1, SCV002506442.3, SCV006582525.2
19554541  4       SCV000198337.5, SCV000461883.3, SCV001194094.2, SCV002769510.1
…
```

The query leaves out one kind of citation on purpose: `scv.specifiedBy.reportedIn.pmid` is the paper describing the submitter's *classification method*, such as the ACMG/AMP guidelines (PMID 25741868). It appears on most submissions, so it says nothing about the variant. Add it only if you want it.

!!! tip "Asking this often?"
    If you look up many variants, [materialize the statement–proposition join](performance.md#materialize-join-tables) once. Each lookup then takes about 10 ms, and the PubMed ids are already gathered into a list per SCV.

## Variants submitted for a condition { #variants-for-a-condition }

Every variant with a submission for one condition, with how submitters classified it. A submission can name the condition directly or as a member of a condition set, so the query collects both (see [Seam B](joining.md#seam-b-proposition-condition-or-conditionset)):

```sql
WITH target AS (
  SELECT id FROM 'condition.parquet' WHERE name = 'Marfan syndrome'          -- <- your condition
),
members AS (                      -- one row per (condition set, member id)
  SELECT cs.id AS set_id, cid AS member_id
  FROM 'conditionSet.parquet' cs, unnest(cs.concepts) AS t(cid)
),
sets AS (                         -- the sets that list the condition directly
  SELECT m.set_id AS id FROM members m JOIN target ON target.id = m.member_id
),
objects AS (                      -- the condition itself, plus every set that contains it (one level of nesting)
  SELECT id FROM target
  UNION
  SELECT id FROM sets
  UNION
  SELECT m.set_id FROM members m JOIN sets ON sets.id = m.member_id
),
prop AS (
  SELECT id, subject_variant_id AS variant_id, object_id FROM read_parquet('proposition*.parquet')
)
SELECT p.variant_id, v.name AS variant_name,
       count(*) AS scvs,
       count(*) FILTER (WHERE s.classification.primaryCoding.code IN ('pathogenic', 'likely pathogenic'))  AS p_lp,
       count(*) FILTER (WHERE s.classification.primaryCoding.code = 'uncertain significance')           AS vus,
       count(*) FILTER (WHERE s.classification.primaryCoding.code IN ('benign', 'likely benign'))       AS b_lb
FROM 'scv.parquet' s
JOIN prop p ON p.id = s.proposition_id
JOIN 'variation.parquet' v ON v.id = p.variant_id
WHERE p.object_id IN (SELECT id FROM objects)
GROUP BY ALL
ORDER BY scvs DESC, p.variant_id
LIMIT 10;
```

```text
variant_id      variant_name                                scvs  p_lp  vus  b_lb
clinvar:163462  NM_000138.5(FBN1):c.7754T>C (p.Ile2585Thr)  13    13    0    0
clinvar:16451   NM_000138.5(FBN1):c.3509G>A (p.Arg1170His)  13    1     4    7
clinvar:42394   NM_000138.5(FBN1):c.5788+5G>A               13    13    0    0
clinvar:16445   NM_000138.5(FBN1):c.8176C>T (p.Arg2726Trp)  11    0     4    7
…
```

The counts use the normalized `classification.primaryCoding.code`, not the submitted text; [Anatomy of a Table](table-anatomy.md#a-worked-example-what-do-submitters-say) explains why.

## One submitter's footprint { #submitter-footprint }

What one organization has submitted, by classification and submission level. The [Auditing a Submitter's Footprint](../user-story-audit.md) story walks through this kind of audit in depth.

```sql
WITH sub AS (
  SELECT id FROM 'submitter.parquet' WHERE name = 'Mayo Clinic Laboratories, Mayo Clinic'   -- <- your submitter
)
SELECT s.classification.primaryCoding.code AS classification,
       s.quality.name                      AS level,
       count(*)                            AS scvs
FROM 'scv.parquet' s
WHERE [c.contributor FOR c IN s.contributions IF c.activityType = 'submitted'][1] IN (SELECT id FROM sub)
GROUP BY ALL
ORDER BY scvs DESC;
```

```text
classification          level                           scvs
uncertain significance  criteria provided               18,832
benign                  criteria provided               18,791
likely benign           criteria provided               10,983
pathogenic              criteria provided                2,543
likely pathogenic       criteria provided                2,047
…
```

Find a submitter's exact name with `SELECT id, name FROM 'submitter.parquet' WHERE name ILIKE '%mayo%'`.

## Why a variant is "conflicting" { #conflicting-classifications }

ClinVar calls 178,208 variants *Conflicting classifications of pathogenicity*. This finds them:

```sql
SELECT classification.name AS classification, count(*) AS variants
FROM 'vcv.parquet'
WHERE regexp_matches(id, '-G-PATH$')                -- the germline pathogenicity root statement
  AND classification.name ILIKE 'conflicting%'
GROUP BY ALL;
```

To see **why** one variant is conflicting, list the submissions behind each level of its pathogenicity call, grouped by what they said. This walks the VCV evidence lines down to the SCVs ([Seam E](joining.md#seam-e-every-scv-to-its-aggregate-in-one-pass)):

```sql
WITH scv_vcv AS (
  SELECT s.id AS vcv_statement_id, it AS scv_id
  FROM (SELECT id, unnest(has_evidence_lines) AS el_id FROM 'vcv.parquet'
        WHERE id LIKE 'VCV000000010.%-G-PATH-%') s                       -- <- your variant's VCV accession
  JOIN 'vcv_evidenceLine.parquet' el ON el.id = s.el_id,
       unnest(el.evidence_items) AS t(it)
  WHERE it LIKE 'clinvar.submission:%'
)
SELECT x.vcv_statement_id,
       s.classification.primaryCoding.code AS classification,
       count(*) AS scvs,
       string_agg(DISTINCT sub.name, '; ' ORDER BY sub.name) AS submitters
FROM scv_vcv x
JOIN 'scv.parquet' s ON s.id = x.scv_id
LEFT JOIN 'submitter.parquet' sub
       ON sub.id = [c.contributor FOR c IN s.contributions IF c.activityType = 'submitted'][1]
GROUP BY ALL
ORDER BY x.vcv_statement_id, scvs DESC, classification;
```

```text
vcv_statement_id              classification              scvs  submitters
VCV000000010.141-G-PATH-CP    pathogenic                  40    3billion; AiLife Diagnostics, …
VCV000000010.141-G-PATH-CP    likely pathogenic            2    Genomic Medicine Center of Excellence, …
VCV000000010.141-G-PATH-CP    uncertain significance       2    Cambridge Genomics Laboratory, …
VCV000000010.141-G-PATH-CP    pathogenic, low penetrance   1    Labcorp Genetics (formerly Invitae), Labcorp
VCV000000010.141-G-PATH-FLAG  benign                       1    Pathology and Clinical Laboratory Medicine, …
VCV000000010.141-G-PATH-FLAG  uncertain significance       1    Laboratory for Molecular Medicine, …
VCV000000010.141-G-PATH-NOCP  pathogenic                   8    Clinical Genetics DNA and cytogenetics Diagnostics Lab, …
```

The call comes from the `-CP` level, the highest present. Among those 45 submissions, two say *uncertain significance* against 42 pathogenic or likely pathogenic; that disagreement is the conflict. The `-NOCP` and `-FLAG` submissions are listed but don't count toward the call. The VCV accession number is the variation id zero-padded to nine digits (`clinvar:10` → `VCV000000010`).

## Variants in a genomic window { #genomic-window }

Every variant (alleles and copy-number variants) whose location overlaps a window on GRCh38 chromosome 13. Coordinates are **interbase** (0-based, end-exclusive), so the window `[32338400, 32338500)` covers 1-based positions 32,338,401–32,338,500.

```sql
WITH seq AS (
  SELECT id FROM 'sequenceReference.parquet' WHERE name = 'NC_000013.11'    -- <- chromosome (RefSeq accession)
),
loc AS (
  SELECT id, loc_start_min, loc_start_max, loc_end_min, loc_end_max FROM 'location.parquet'
  WHERE sequence_reference_id = (SELECT id FROM seq)
    AND loc_start_max < 32338500 AND loc_end_min > 32338400                 -- <- window
),
vrs AS (
  SELECT id, location_id FROM 'allele.parquet'
  UNION ALL SELECT id, location_id FROM 'copyNumberCount.parquet'
  UNION ALL SELECT id, location_id FROM 'copyNumberChange.parquet'
)
SELECT v.id, v.name, l.loc_start_min, l.loc_start_max, l.loc_end_min, l.loc_end_max
FROM vrs
JOIN loc l ON l.id = vrs.location_id
JOIN (SELECT id, name, unnest(members) AS member FROM 'variation.parquet') v ON v.member = vrs.id
ORDER BY l.loc_start_max, v.id;
```

```text
id              name                                              loc_start_min  loc_start_max  loc_end_min  loc_end_max
clinvar:146305  GRCh38/hg38 13q11-34(chr13:18445862-114327173)x1  NULL           18445861       114327173    NULL
clinvar:151282  GRCh38/hg38 13q11-34(chr13:18456040-114340285)x3  NULL           18456039       114340285    NULL
clinvar:59851   GRCh38/hg38 13q11-34(chr13:18565048-114327173)x3  NULL           18565047       114327173    NULL
…
```

243 variants in this 100-base window. 35 of them are copy-number variants whose start or end is an uncertain range, like the three above: ClinVar knows the deleted or duplicated span covers at least `[loc_start_max, loc_end_min)`, but not how far beyond it. For a definite coordinate the min and max columns are equal.

The query matches on the span each variant **certainly** covers. To include every variant that **may** reach the window, match on the outer bounds instead, treating NULL as unbounded: `coalesce(loc_start_min, 0) < 32338500 AND coalesce(loc_end_max, 9e9) > 32338400` (638 variants here).

!!! note "From release 1.1.0"
    The `loc_start_min` … `loc_end_max` columns exist in `location.parquet` from release 1.1.0. On earlier releases, filter on `loc_start` and `loc_end` instead (`loc_start < 32338500 AND loc_end > 32338400`); that finds 208 variants here, because it skips every location whose start or end is an uncertain range (their range is only in `location.data`).

## Gene rollup of ClinVar's calls { #gene-rollup }

ClinVar's germline pathogenicity call for every variant in a gene. Genes come from the variant's ClinVar gene list (`ncbigene:` ids), not the free-text `gene_context_name`, which [isn't a reliable gene join](joining.md#joins-that-lie).

```sql
WITH v AS (                       -- variants whose ClinVar gene list names the gene
  SELECT x.id
  FROM (SELECT id,
               unnest(flatten([[replace(g.gene, '#/gene/', '') FOR g IN e.value_gene_array   -- bare ncbigene: id
                                IF g.relationship_type IN ('within single gene', 'within multiple genes by overlap',
                                                           'asserted, but not computed')]
                               FOR e IN extensions IF e.name = 'clinvarGeneList'])) AS gene_id
        FROM 'variation.parquet') x
  JOIN 'gene.parquet' gene ON gene.id = x.gene_id      -- an equality join, so DuckDB plans a fast hash join
  WHERE gene.name = 'MYH7'                                                    -- <- your gene symbol
)
SELECT classification.name AS clinvar_call, count(*) AS variants
FROM 'vcv.parquet'
WHERE regexp_matches(id, '-G-PATH$')                                          -- germline pathogenicity root
  AND 'clinvar:' || CAST(substr(id, 4, 9) AS INTEGER) IN (SELECT id FROM v)   -- VCV accession number = variation id
GROUP BY ALL
ORDER BY variants DESC;
```

```text
clinvar_call                                  variants
Uncertain significance                        3,005
Likely benign                                 1,690
Conflicting classifications of pathogenicity    555
Likely pathogenic                               256
Benign                                          146
Pathogenic                                       96
…
```

About **5 s** and **1.6 GB**, nearly all of it reading the gene lists in the 4 GB `variation.parquet`. The `relationship_type` filter drops large copy-number variants that merely overlap the gene and variants near it; remove it to include them. The `replace(…, '#/gene/', '')` lets the query run on any release: before 1.1.0 each gene was a `#/gene/ncbigene:…` pointer, and on the bare `ncbigene:` ids from 1.1.0 on it changes nothing.

!!! tip "Reach into nested lists with `[… FOR … IN …]`, not `unnest`"
    The gene filter above uses a list comprehension. Written instead with `unnest(extensions)` and `unnest(value_gene_array)`, the same filter returns the same 5,942 variants but takes about **37 s** and **2.5 GB**, because `unnest` expands every variant's whole extension list into rows first.

## PubMed ids cited for every variant in a gene { #pubmed-ids-for-a-gene }

The gene filter from the rollup, joined to the PubMed query:

```sql
WITH v AS (                                  -- variants whose ClinVar gene list names the gene
  SELECT x.id, x.name
  FROM (SELECT id, name,
               unnest(flatten([[replace(g.gene, '#/gene/', '') FOR g IN e.value_gene_array   -- bare ncbigene: id
                                -- drop large CNVs that merely overlap the gene, and near-gene variants:
                                IF g.relationship_type IN ('within single gene', 'within multiple genes by overlap',
                                                           'asserted, but not computed')]
                               FOR e IN extensions IF e.name = 'clinvarGeneList'])) AS gene_id
        FROM 'variation.parquet') x
  JOIN 'gene.parquet' gene ON gene.id = x.gene_id      -- an equality join, so DuckDB plans a fast hash join
  WHERE gene.name = 'MYH7'                                                     -- <- your gene symbol
),
prop AS (
  SELECT id, subject_variant_id AS variant_id FROM read_parquet('proposition*.parquet')
),
cites AS (
  SELECT p.variant_id, s.id AS scv_id, unnest(s.reportedIn).pmid AS pmid
  FROM 'scv.parquet' s
  JOIN prop p ON p.id = s.proposition_id
  WHERE p.variant_id IN (SELECT id FROM v)
)
SELECT v.id AS variant_id, v.name AS variant_name, c.pmid,
       count(DISTINCT c.scv_id) AS n_scvs
FROM cites c JOIN v ON v.id = c.variant_id
WHERE c.pmid IS NOT NULL
GROUP BY ALL
ORDER BY v.id, c.pmid;
```

One row per (variant, PubMed id). For MYH7 that is 6,976 rows covering 1,694 variants and 1,093 distinct PubMed ids, in about **5 s** and **1.5 GB**. For a list of distinct PubMed ids instead, wrap the final `SELECT` and group by `pmid`.

## Export a slice to CSV or Parquet { #export }

Spreadsheets and many tools can't read Parquet, and you rarely want a whole table anyway. Wrap any query in `COPY` to write its result to a file:

```sql
-- Expert-panel and practice-guideline submissions, with their variant
COPY (
  WITH prop AS (
    SELECT id, subject_variant_id AS variant_id FROM read_parquet('proposition*.parquet')
  )
  SELECT replace(s.id, 'clinvar.submission:', '') AS scv,
         p.variant_id,
         s.classification.name AS classification,
         s.quality.name        AS level
  FROM 'scv.parquet' s
  JOIN prop p ON p.id = s.proposition_id
  WHERE s.quality.name IN ('expert panel', 'practice guidelines')
) TO 'expert_scvs.csv' (HEADER);
```

That writes 25,379 rows plus a header. For another analytics tool, write Parquet instead, which keeps the column types and is far smaller: `TO 'expert_scvs.parquet' (FORMAT parquet)`.
