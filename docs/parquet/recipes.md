# Recipes

!!! info "Release"
    Outputs on this page are from the published Parquet of the **2026-11-15 release** (built 2026-11-20 with
    `gkm-bundle-parquet` 2.0.0), queried with DuckDB 1.5.4 on an Apple M2 Pro laptop (16 GB of memory). The
    [gene-panel](#gene-panel) recipe's tool step reads the 2026-11-15 weekly delta. The published set is
    overwritten every release: re-run a recipe to get today's numbers.

Each recipe answers one question: the question in plain language, a query you can run, and what to expect. They run against **downloaded** files; most touch one of the larger tables, which is too much for the [live console](index.md#run-a-query-now). See [Start Here](index.md#put-the-file-on-your-machine) to download.

Change the line marked `-- <-` to ask about your own variant, condition, gene or submitter. [Joining Tables](joining.md) explains each join used here.

!!! note "Prerequisites"
    - **[DuckDB CLI](https://duckdb.org/docs/installation/)**, tested with **1.5.4**. No extension is needed.
    - **All 20 tables in one folder**, about 4.6 GB: download them with the loop on
      [Parquet Files → Download](../data-access/parquet.md#download), then start `duckdb` in that folder. The
      queries name each table by its file name (`'scv.parquet'`) and read the four proposition tables with the
      glob `proposition*.parquet`.
    - Each recipe stands alone and names the tables it reads, so you can download only those. Most finish in a
      few seconds; the ones that read every variant's gene or HGVS list take 10 to 15 seconds on the test laptop,
      longer when the files aren't in the operating system's cache. The release-wide exports need up to 5 GB of
      memory.
    - **The [gene-panel](#gene-panel) recipe** also runs `gkm-bundle-parquet` 2.0.0 with
      [uv](https://docs.astral.sh/uv/getting-started/installation/) (tested with 0.6.14), in bash or zsh, and reads
      a weekly delta (5 MB) it downloads.

| Recipe | Tables it reads |
| --- | --- |
| [Everything ClinVar says about one variant](#one-variant) | `variation` or `allele`, the propositions, `vcv`, `rcv`, `scv`, `submitter`, `condition`, `conditionSet` |
| [PubMed ids cited for a variant](#pubmed-ids-for-a-variant) | `variation`, the propositions, `scv` |
| [Variants submitted for a condition](#variants-for-a-condition) | `condition`, `conditionSet`, the propositions, `scv`, `variation` |
| [One submitter's footprint](#submitter-footprint) | `submitter`, `scv` |
| [Why a variant is "conflicting"](#conflicting-classifications) | `vcv`, `evidenceLine`, `scv`, `submitter` |
| [Variants in a genomic window](#genomic-window) | `sequenceReference`, `location`, `allele`, `copyNumberCount`, `copyNumberChange`, `variation` |
| [Gene rollup of ClinVar's calls](#gene-rollup) | `variation`, `gene`, `vcv` |
| [PubMed ids cited for every variant in a gene](#pubmed-ids-for-a-gene) | `variation`, `gene`, the propositions, `scv` |
| [Gene-panel subset](#gene-panel) | `gene`, `variation`; then a bundle, with `gkm-bundle-parquet` |
| [VRS-keyed harmonization table](#harmonization-table) | `sequenceReference`, `location`, `allele`, `variation`, `vcv` |
| [Conflicting-classification watchlist](#conflict-watchlist) | `vcv`, `evidenceLine`, `scv`, `submitter` |
| [One submitter's dataset](#submitter-dataset) | `submitter`, `scv`, the propositions, `variation`, `condition`, `vcv` |
| [Flat analysis table, one row per SCV](#flat-scv-table) | `scv`, the propositions, `variation`, `submitter`, `condition`, `conditionSet` |
| [Export a slice to CSV or Parquet](#export) | the propositions, `scv` |

## Everything ClinVar says about one variant { #one-variant }

### Find the variant

If you know the ClinVar variation id, you already have it: `clinvar:<id>`. Otherwise look it up by any HGVS expression ClinVar lists for it (coding `c.`, genomic `g.`, non-coding `n.`, on any transcript or assembly):

```sql
SELECT id, name
FROM 'variation.parquet'
WHERE list_contains(
        flatten([[h.nucleotideExpression.value FOR h IN e.value_object_array]
                 FOR e IN extensions IF e.name = 'clinvarHgvsList']),
        'NM_000059.4:c.4090A>C');                                            -- <- your HGVS
```

```text
id             name
clinvar:51592  NM_000059.4(BRCA2):c.4090A>C (p.Ile1364Leu)
```

This scans every variant's HGVS list, the largest part of the 1.66 GB `variation.parquet`: about 7 seconds on the test laptop. For a GRCh38 genomic expression the allele table is much faster, because it is a short string column:

```sql
SELECT v.id, v.name
FROM 'allele.parquet' a
JOIN (SELECT id, name, unnest(members) AS member FROM 'variation.parquet') v
     ON v.member.id = a.id                -- an equality join; list_contains() in ON plans a nested loop
WHERE a.name = 'NC_000013.11:g.32338445A>C';
```

`allele.expressions` also holds the SPDI and gnomAD forms (`13-32338445-A-C`); see [the VRS chain](migrating-from-1.1.md#query-rewrites).

### ClinVar's aggregate calls

One row for each VCV root statement (one per classification type) and each RCV (one per condition), with the condition names resolved:

```sql
WITH prop AS (                    -- all four proposition tables, one glob
  SELECT id, type, subject, object, object_section
  FROM read_parquet('proposition*.parquet', union_by_name = true)
),
set_names AS (
  SELECT cs.id, string_agg(c.name, '; ' ORDER BY c.name) AS member_names
  FROM 'conditionSet.parquet' cs, unnest(cs.concepts) AS t(m)
  JOIN 'condition.parquet' c ON c.id = m.id
  GROUP BY cs.id
),
agg AS (
  SELECT 'VCV' AS tier, id, proposition, quality.name AS level, classification.name AS classification FROM 'vcv.parquet'
  UNION ALL
  SELECT 'RCV', id, proposition, quality.name, classification.name FROM 'rcv.parquet'
)
SELECT a.tier, a.id AS statement, p.type AS proposition_type, a.level, a.classification,
       coalesce(c.name, sn.member_names) AS condition
FROM agg a
JOIN prop p ON p.id = a.proposition
LEFT JOIN 'condition.parquet' c ON c.id = CASE WHEN p.object_section = 'condition'    THEN p.object END
LEFT JOIN set_names sn          ON sn.id = CASE WHEN p.object_section = 'conditionSet' THEN p.object END
WHERE p.subject = 'clinvar:51592'                                            -- <- your variant
  AND NOT regexp_matches(a.id, '-(PG|EP|CP|NOCP|NOCL|FLAG)(-T[0-9])?$')     -- root statements only
ORDER BY a.tier DESC, a.id;
```

```text
tier  statement                proposition_type                 level              classification        condition
VCV   VCV000051592.122-G-NP    ClinvarNotProvidedProposition    no classification  not provided          not specified
VCV   VCV000051592.122-G-PATH  VariantPathogenicityProposition  expert panel       Benign                Breast-ovarian cancer, familial, susceptibility to, 2
RCV   RCV000044344.34-G-PATH   VariantPathogenicityProposition  criteria provided  Benign                Hereditary breast ovarian cancer syndrome
RCV   RCV000113272.28-G-PATH   VariantPathogenicityProposition  expert panel       Benign                Breast-ovarian cancer, familial, susceptibility to, 2
RCV   RCV000120319.33-G-NP     ClinvarNotProvidedProposition    no classification  not provided          not specified
RCV   RCV000120319.33-G-PATH   VariantPathogenicityProposition  criteria provided  Benign/Likely benign  not specified
RCV   RCV000131014.17-G-PATH   VariantPathogenicityProposition  criteria provided  Benign/Likely benign  Hereditary cancer-predisposing syndrome
RCV   RCV000389513.13-G-PATH   VariantPathogenicityProposition  criteria provided  Likely benign         Fanconi anemia complementation group D1
RCV   RCV000469910.10-G-PATH   VariantPathogenicityProposition  criteria provided  Benign                Familial cancer of breast
RCV   RCV000656601.24-G-PATH   VariantPathogenicityProposition  criteria provided  Benign                not provided
RCV   RCV000770724.10-G-PATH   VariantPathogenicityProposition  criteria provided  Benign                Breast and/or ovarian cancer
```

Drop the root-statement filter to see each level statement as well (`-EP`, `-CP`, `-NOCP`, …); [Reading a variant's statements](tables.md#reading-a-variants-statements) explains them.

### Every submission

Who submitted, what they said, at what level, for which condition, and when they last evaluated it:

```sql
WITH prop AS (
  SELECT id, type, subject, object, object_section
  FROM read_parquet('proposition*.parquet', union_by_name = true)
),
set_names AS (
  SELECT cs.id, string_agg(c.name, '; ' ORDER BY c.name) AS member_names
  FROM 'conditionSet.parquet' cs, unnest(cs.concepts) AS t(m)
  JOIN 'condition.parquet' c ON c.id = m.id
  GROUP BY cs.id
)
SELECT replace(s.id, 'clinvar.submission:', '') AS scv,
       sub.name                AS submitter,
       s.classification.name   AS classification,
       s.quality.name          AS level,
       coalesce(c.name, sn.member_names) AS condition,
       [x.date FOR x IN s.contributions IF x.activityType = 'evaluated'][1] AS last_evaluated
FROM 'scv.parquet' s
JOIN prop p ON p.id = s.proposition
LEFT JOIN 'submitter.parquet' sub
       ON sub.id = [x.contributor FOR x IN s.contributions IF x.activityType = 'submitted'][1]
LEFT JOIN 'condition.parquet' c ON c.id = CASE WHEN p.object_section = 'condition'    THEN p.object END
LEFT JOIN set_names sn          ON sn.id = CASE WHEN p.object_section = 'conditionSet' THEN p.object END
WHERE p.subject = 'clinvar:51592'                                            -- <- your variant
ORDER BY last_evaluated DESC, scv
LIMIT 3;
```

```text
scv              submitter                                                                    classification  level              condition                                  last_evaluated
SCV000072357.18  Labcorp Genetics (formerly Invitae), Labcorp                                 Benign          criteria provided  Hereditary breast ovarian cancer syndrome  2026-02-03
SCV000602753.7   ARUP Laboratories, Molecular Genetics and Genomics, ARUP Laboratories        Benign          criteria provided  not provided                               2025-05-19
SCV004243027.2   Center for Genomic Medicine, Rigshospitalet, Copenhagen University Hospital  Benign          criteria provided  not specified                              2025-03-04
```

36 submissions for this variant; drop the `LIMIT` to see them all. `date` is ISO text, so it sorts correctly as text; `CAST(date AS DATE)` gives a `DATE`.

## PubMed ids cited for a variant { #pubmed-ids-for-a-variant }

PubMed ids appear only on **SCVs** (individual submissions), in `scv.reportedIn[].pmid`. The variant, VCV and RCV records carry none. So the query goes from the variant to its propositions, and from the propositions to the SCVs that cite them.

```sql
WITH v AS (
  SELECT id, name FROM 'variation.parquet' WHERE id = 'clinvar:10'         -- <- your variant
),
prop AS (                                     -- all four proposition tables, one glob
  SELECT id, subject FROM read_parquet('proposition*.parquet', union_by_name = true)
),
cites AS (                                    -- one row per (SCV, cited PubMed id)
  SELECT p.subject AS variant_id, s.id AS scv_id, unnest(s.reportedIn).pmid AS pmid
  FROM 'scv.parquet' s
  JOIN prop p ON p.id = s.proposition
  WHERE p.subject IN (SELECT id FROM v)
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
19159930       5  SCV000198337.5, SCV001194094.2, SCV001251532.1, SCV001519563.1, SCV002568070.8
8696333        5  SCV000461883.3, SCV001519563.1, SCV002502480.1, SCV002506442.3, SCV006582525.2
19554541       4  SCV000198337.5, SCV000461883.3, SCV001194094.2, SCV002769510.1
9356458        4  SCV000219176.11, SCV001519563.1, SCV002568070.8, SCV006582525.2
…
```

The query leaves out one kind of citation on purpose: `scv.specifiedBy.reportedIn.pmid` is the paper describing the submitter's *classification method*, such as the ACMG/AMP guidelines (PMID 25741868). It appears on most submissions, so it says nothing about the variant. Add it only if you want it.

!!! tip "Asking this often?"
    If you look up many variants, [materialize the statement–proposition join](performance.md#materialize-join-tables) once. Each lookup then reads one small table, and the PubMed ids are already gathered into a list per SCV.

## Variants submitted for a condition { #variants-for-a-condition }

Every variant with a submission for one condition, with how submitters classified it. A submission can name the condition directly or as a member of a condition set, so the query collects both (see [Seam B](joining.md#seam-b-proposition-condition-or-conditionset)):

```sql
WITH target AS (
  SELECT id FROM 'condition.parquet' WHERE name = 'Marfan syndrome'          -- <- your condition
),
members AS (                      -- one row per (condition set, member id)
  SELECT cs.id AS set_id, m.id AS member_id
  FROM 'conditionSet.parquet' cs, unnest(cs.concepts) AS t(m)
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
  SELECT id, subject, object FROM read_parquet('proposition*.parquet', union_by_name = true)
)
SELECT p.subject AS variant_id, v.name AS variant_name,
       count(*) AS scvs,
       count(*) FILTER (WHERE s.classification.primaryCoding.code IN ('pathogenic', 'likely pathogenic'))  AS p_lp,
       count(*) FILTER (WHERE s.classification.primaryCoding.code = 'uncertain significance')           AS vus,
       count(*) FILTER (WHERE s.classification.primaryCoding.code IN ('benign', 'likely benign'))       AS b_lb
FROM 'scv.parquet' s
JOIN prop p ON p.id = s.proposition
JOIN 'variation.parquet' v ON v.id = p.subject
WHERE p.object IN (SELECT id FROM objects)
GROUP BY ALL
ORDER BY scvs DESC, p.subject
LIMIT 10;
```

```text
variant_id      variant_name                                scvs  p_lp  vus  b_lb
clinvar:163462  NM_000138.5(FBN1):c.7754T>C (p.Ile2585Thr)    13    13    0     0
clinvar:16451   NM_000138.5(FBN1):c.3509G>A (p.Arg1170His)    13     1    4     7
clinvar:42394   NM_000138.5(FBN1):c.5788+5G>A                 13    13    0     0
clinvar:16445   NM_000138.5(FBN1):c.8176C>T (p.Arg2726Trp)    11     0    4     7
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
uncertain significance  criteria provided               18,830
benign                  criteria provided               18,791
likely benign           criteria provided               10,983
pathogenic              criteria provided                2,543
likely pathogenic       criteria provided                2,047
…
```

Find a submitter's exact name with `SELECT id, name FROM 'submitter.parquet' WHERE name ILIKE '%mayo%'`.

## Why a variant is "conflicting" { #conflicting-classifications }

ClinVar calls 184,296 variants *Conflicting classifications of pathogenicity* in 2026-11-15. This finds them:

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
  SELECT regexp_replace(el.id, '\.(non-)?contributing$', '') AS vcv_statement_id,
         item.id AS scv_id
  FROM 'evidenceLine.parquet' el, unnest(el.hasEvidenceItems) AS t(item)
  WHERE el.id LIKE 'VCV000000010.%-G-PATH-%'                                -- <- your variant's VCV accession
    AND item.section = 'scv'
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
VCV000000010.143-G-PATH-CP    pathogenic                    41  3billion; AiLife Diagnostics, …
VCV000000010.143-G-PATH-CP    likely pathogenic              2  Genomic Medicine Center of Excellence, …
VCV000000010.143-G-PATH-CP    uncertain significance         2  Cambridge Genomics Laboratory, …
VCV000000010.143-G-PATH-CP    pathogenic, low penetrance     1  Labcorp Genetics (formerly Invitae), Labcorp
VCV000000010.143-G-PATH-FLAG  benign                         1  Pathology and Clinical Laboratory Medicine, …
VCV000000010.143-G-PATH-FLAG  uncertain significance         1  Laboratory for Molecular Medicine, …
VCV000000010.143-G-PATH-NOCP  pathogenic                     8  Clinical Genetics DNA and cytogenetics Diagnostics Lab, …
```

The call comes from the `-CP` level, the highest present. Among those 46 submissions, two say *uncertain significance* against 43 pathogenic or likely pathogenic; that disagreement is the conflict. The `-NOCP` and `-FLAG` submissions are listed but don't count toward the call. The VCV accession number is the variation id zero-padded to nine digits (`clinvar:10` → `VCV000000010`).

## Variants in a genomic window { #genomic-window }

Every variant (alleles and copy-number variants) whose location overlaps a window on GRCh38 chromosome 13. Coordinates are **interbase** (0-based, end-exclusive), so the window `[32338400, 32338500)` covers 1-based positions 32,338,401–32,338,500.

```sql
WITH seq AS (
  SELECT id FROM 'sequenceReference.parquet' WHERE name = 'NC_000013.11'    -- <- chromosome (RefSeq accession)
),
loc AS (
  SELECT id, start_min, start_max, end_min, end_max FROM 'location.parquet'
  WHERE sequenceReference = (SELECT id FROM seq)
    AND start_max < 32338500 AND end_min > 32338400                         -- <- window
),
vrs AS (
  SELECT id, location FROM 'allele.parquet'
  UNION ALL SELECT id, location FROM 'copyNumberCount.parquet'
  UNION ALL SELECT id, location FROM 'copyNumberChange.parquet'
)
SELECT v.id, v.name, l.start_min, l.start_max, l.end_min, l.end_max
FROM vrs
JOIN loc l ON l.id = vrs.location
JOIN (SELECT id, name, unnest(members) AS member FROM 'variation.parquet') v ON v.member.id = vrs.id
ORDER BY l.start_max, v.id;
```

```text
id              name                                              start_min  start_max  end_min    end_max
clinvar:146305  GRCh38/hg38 13q11-34(chr13:18445862-114327173)x1  NULL       18445861   114327173  NULL
clinvar:151282  GRCh38/hg38 13q11-34(chr13:18456040-114340285)x3  NULL       18456039   114340285  NULL
clinvar:59851   GRCh38/hg38 13q11-34(chr13:18565048-114327173)x3  NULL       18565047   114327173  NULL
…
```

244 variants in this 100-base window in 2026-11-15. 35 of them are copy-number variants whose start or end is an uncertain range, like the three above: ClinVar knows the deleted or duplicated span covers at least `[start_max, end_min)`, but not how far beyond it. For a definite coordinate the min and max columns are equal.

The query matches on the span each variant **certainly** covers. To include every variant that **may** reach the window, match on the outer bounds instead, treating NULL as unbounded: `coalesce(start_min, 0) < 32338500 AND coalesce(end_max, 9e9) > 32338400` (641 variants here).

## Gene rollup of ClinVar's calls { #gene-rollup }

ClinVar's germline pathogenicity call for every variant in a gene. Genes come from the variant's ClinVar gene list (`ncbigene:` ids), not the gene-context symbol, which [isn't a reliable gene join](joining.md#joins-that-lie).

```sql
WITH v AS (                       -- variants whose ClinVar gene list names the gene
  SELECT x.id
  FROM (SELECT id,
               unnest(flatten([[g.gene FOR g IN e.value_object_array
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
Uncertain significance                           3,034
Likely benign                                    1,697
Conflicting classifications of pathogenicity       560
Likely pathogenic                                  257
Benign                                             146
Pathogenic/Likely pathogenic                        95
…
```

Nearly all the work, about 8 seconds on the test laptop, is reading the gene lists in `variation.parquet`. The `relationship_type` filter drops large copy-number variants that merely overlap the gene and variants near it; remove it to include them.

!!! tip "Reach into nested lists with `[… FOR … IN …]`, not `unnest`"
    The gene filter above uses a list comprehension. Written instead with `unnest(extensions)` and
    `unnest(value_object_array)`, the same filter returns the same variants, but `unnest` first expands every
    variant's whole extension list into rows, which is many times slower and uses more memory.

## PubMed ids cited for every variant in a gene { #pubmed-ids-for-a-gene }

The gene filter from the rollup, joined to the PubMed query:

```sql
WITH v AS (                                  -- variants whose ClinVar gene list names the gene
  SELECT x.id, x.name
  FROM (SELECT id, name,
               unnest(flatten([[g.gene FOR g IN e.value_object_array
                                -- drop large CNVs that merely overlap the gene, and near-gene variants:
                                IF g.relationship_type IN ('within single gene', 'within multiple genes by overlap',
                                                           'asserted, but not computed')]
                               FOR e IN extensions IF e.name = 'clinvarGeneList'])) AS gene_id
        FROM 'variation.parquet') x
  JOIN 'gene.parquet' gene ON gene.id = x.gene_id      -- an equality join, so DuckDB plans a fast hash join
  WHERE gene.name = 'MYH7'                                                     -- <- your gene symbol
),
prop AS (
  SELECT id, subject FROM read_parquet('proposition*.parquet', union_by_name = true)
),
cites AS (
  SELECT p.subject AS variant_id, s.id AS scv_id, unnest(s.reportedIn).pmid AS pmid
  FROM 'scv.parquet' s
  JOIN prop p ON p.id = s.proposition
  WHERE p.subject IN (SELECT id FROM v)
)
SELECT v.id AS variant_id, v.name AS variant_name, c.pmid,
       count(DISTINCT c.scv_id) AS n_scvs
FROM cites c JOIN v ON v.id = c.variant_id
WHERE c.pmid IS NOT NULL
GROUP BY ALL
ORDER BY v.id, c.pmid;
```

One row per (variant, PubMed id). For MYH7 that is 6,981 rows in 2026-11-15, covering 1,696 variants and 1,095 distinct PubMed ids. For a list of distinct PubMed ids instead, wrap the final `SELECT` and group by `pmid`. Like the rollup, nearly all of its 13 seconds on the test laptop is reading the gene lists.

## Gene-panel subset { #gene-panel }

**The question.** Which records concern the genes on my panel, and what changed on them this week?

**For** a laboratory or curation group that works on a fixed gene list and wants its part of ClinVar as tables or
as records.

**Reads** `gene.parquet` (3 MB) and `variation.parquet` (1.7 GB) to turn gene symbols into variant ids; then a
bundle, with [`gkm-bundle-parquet`](build-your-own.md) 2.0.0.

Write the panel, one gene symbol per line, into the folder you run DuckDB from:

```bash
printf 'MYH7\nMYBPC3\nTNNT2\nTNNI3\nTPM1\nACTC1\nMYL2\nMYL3\n' > panel.txt
```

Then, in DuckDB, write the ids of every variant whose ClinVar gene list names a panel gene (the same gene filter
as the [gene rollup](#gene-rollup)):

```sql
COPY (
  WITH panel AS (
    SELECT g.id FROM read_csv('panel.txt', header = false, columns = {'symbol': 'VARCHAR'}) p
    JOIN 'gene.parquet' g ON g.name = p.symbol
  )
  SELECT DISTINCT x.id
  FROM (SELECT id,
               unnest(flatten([[g.gene FOR g IN e.value_object_array
                                IF g.relationship_type IN ('within single gene', 'within multiple genes by overlap',
                                                           'asserted, but not computed')]
                               FOR e IN extensions IF e.name = 'clinvarGeneList'])) AS gene_id
        FROM 'variation.parquet') x
  WHERE x.gene_id IN (SELECT id FROM panel)
  ORDER BY x.id
) TO 'panel-variants.txt' (HEADER false);
```

`panel-variants.txt` holds 16,059 variant ids for these eight genes in 2026-11-15 (19 seconds). That list is the
panel's key into every release.

**The week's changes, as tables.** Download the 2026-11-15 weekly delta into the same folder, then build the
tables of a selection: every germline pathogenicity proposition about a panel variant, and the statements that
point to it. The `--where` reads the ids file, so ids the delta doesn't carry are simply not matched:

```bash
DELTA=$(curl -fsS https://data.clinvar-gkm.org/v1/1.2/index.json | python3 -c '
import json, sys
print(next(d["bundle"]["path"] for d in json.load(sys.stdin)["deltas"] if d["release"] == "2026-11-15"))')
curl -fO "https://data.clinvar-gkm.org/${DELTA}"
curl -fO "https://data.clinvar-gkm.org/${DELTA}.sha256"
P=(--bundle-schema https://w3id.org/clingen/schema/clinvar-gkm/1.2.0/clinvar-gkm-bundle.schema.json --version-property schema_version)
uvx gkm-bundle-parquet@2.0.0 build --full clinvar-gkm-delta_2026-1115.json.gz "${P[@]}" \
    --driver propositionPathogenicity \
    --where "subject IN (SELECT column0 FROM read_csv('panel-variants.txt', header = false))" \
    --follow in --max-depth 1 \
    --out panel/
```

```text
built 20 table(s) of spec sections 2.0, 34 rows, a selection driven by propositionPathogenicity
  …
  propositionPathogenicity                       17  4500826d4d63
  …
  scv                                             5  c95cc8a9571f
  vcv                                             6  28b71479ea6d
  rcv                                             6  9be4add670a3
manifest: panel/manifest.json
```

Then, in DuckDB, every changed statement about a panel variant:

```sql
SELECT p.subject AS variant, s.id AS statement, s.classification.name AS classification
FROM read_parquet(['panel/scv.parquet', 'panel/vcv.parquet', 'panel/rcv.parquet'], union_by_name = true) s
JOIN 'panel/propositionPathogenicity.parquet' p ON p.id = s.proposition
ORDER BY variant, statement;
```

```text
variant          statement                          classification
clinvar:1060806  RCV007130300.1-G-PATH              Likely pathogenic
clinvar:1060806  RCV007130300.1-G-PATH-CP           Likely pathogenic
clinvar:1060806  VCV001060806.11-G-PATH             Conflicting classifications of pathogenicity
clinvar:1060806  VCV001060806.11-G-PATH-CP          Conflicting classifications of pathogenicity
clinvar:1060806  clinvar.submission:SCV008145506.1  Likely pathogenic
clinvar:235031   clinvar.submission:SCV008131696.1  Pathogenic
…
```

17 rows: 5 new SCVs on five panel variants, and the 12 VCV and RCV statements that changed with them. That is the **week's
changes only**: a delta holds only the records that changed that week. The same command on a full bundle
(`clinvar-gkm_00-latest.json.gz`, about 4.9 GB, from [Monthly Full Bundles](../data-access/monthly-full.md))
gives the panel's whole record. To keep the records rather than tables, run `select` with the same options and
`--out panel.json.gz` ([Cut a mini-bundle](build-your-own.md#cut-a-mini-bundle)).

**Why this is hard with ClinVar's XML.** The genes of a variant sit inside each variant's XML record, so a panel
subset means parsing the whole release to find the variants, and then again to collect the submissions about
them. Here the variant ids come from one query, and the tool follows the bundle's references to collect the
records that mention them.

## VRS-keyed harmonization table { #harmonization-table }

**The question.** For every ClinVar variant on GRCh38: its VRS allele id, its VCF-style coordinates, and
ClinVar's call, in one file sorted by position for joining to a VCF, gnomAD or another VRS-aware dataset.

**For** bioinformaticians annotating variant calls, and knowledgebases that match their variants to ClinVar's.

**Reads** `sequenceReference`, `location` (428 MB), `allele` (701 MB), `variation` (1.7 GB) and `vcv` (148 MB).

```sql
COPY (
  WITH grch38 AS (                  -- GRCh38 chromosome sequences
    SELECT id FROM 'sequenceReference.parquet'
    WHERE list_contains([e.value_string FOR e IN extensions IF e.name = 'assembly'], 'GRCh38')
  ),
  a AS (                            -- GRCh38 alleles, with their gnomAD-style key
    SELECT a.id AS vrs_id, a.digest AS vrs_digest, a.name AS hgvs_g,
           [x.value FOR x IN a.expressions IF x.syntax = 'gnomad'][1] AS gnomad
    FROM 'allele.parquet' a
    JOIN 'location.parquet' l ON l.id = a.location
    WHERE l.sequenceReference IN (SELECT id FROM grch38)
  ),
  v AS (                            -- each variant and its allele
    SELECT id AS variation_id, name AS variation_name, unnest(members).id AS member_id
    FROM 'variation.parquet'
  ),
  call AS (                         -- ClinVar's germline pathogenicity call, one per variant
    SELECT 'clinvar:' || CAST(substr(id, 4, 9) AS INTEGER) AS variation_id,
           split_part(id, '-', 1) AS vcv,
           classification.name AS clinvar_call, quality.name AS review_level
    FROM 'vcv.parquet'
    WHERE regexp_matches(id, '-G-PATH$')
  )
  SELECT split_part(a.gnomad, '-', 1) AS chrom,
         CAST(split_part(a.gnomad, '-', 2) AS BIGINT) AS pos,
         split_part(a.gnomad, '-', 3) AS ref,
         split_part(a.gnomad, '-', 4) AS alt,
         a.vrs_id, a.vrs_digest, a.hgvs_g,
         v.variation_id, v.variation_name, c.vcv, c.clinvar_call, c.review_level
  FROM a
  JOIN v ON v.member_id = a.vrs_id
  LEFT JOIN call c ON c.variation_id = v.variation_id
  WHERE a.gnomad IS NOT NULL
  ORDER BY CASE chrom WHEN 'X' THEN 23 WHEN 'Y' THEN 24 WHEN 'MT' THEN 25 ELSE TRY_CAST(chrom AS INTEGER) END,
           pos, ref, alt, v.variation_id
) TO 'clinvar-vrs-grch38.parquet' (FORMAT parquet);
```

14 seconds and 2.7 GB of memory on the test laptop; a 500 MB file of 4,618,658 rows, one per GRCh38 allele, in
chromosome order (1–22, X, Y, MT) and then by position. Selected columns:

```text
chrom  pos    ref  alt  vrs_id                                     variation_id     vcv             clinvar_call            review_level
1      66926  AG   A    ga4gh:VA.-mXR2-dm4-wqnOb5QgVsIga0a6Qfq0I_  clinvar:3385321  VCV003385321.2  Uncertain significance  criteria provided
1      69134  A    G    ga4gh:VA.43Poe4YtM_kc0qf1FtG8ooVY2tSmCnMt  clinvar:2205837  VCV002205837.2  Likely benign           criteria provided
1      69241  C    T    ga4gh:VA.ripmOgVei3TsCVW7AZnpSlZjTRN1USSg  clinvar:4562067  VCV004562067.1  Uncertain significance  criteria provided
```

- `chrom`, `pos`, `ref` and `alt` come from the allele's gnomAD-style expression (`13-32338445-A-C`): 1-based, with
  VCF's anchor base for insertions and deletions, and chromosomes named without `chr`.
- `vrs_id` is the key for VRS-aware data: compute the same id for your variants with
  [vrs-python](https://github.com/ga4gh/vrs-python) and join on it, with no coordinates involved.
- 254,276 rows have no `clinvar_call`: variants with no germline pathogenicity classification (somatic-only
  submissions, or none). 1,440 alleles are left out: 1,031 neither on GRCh38 nor with a gnomAD-style
  expression, 305 on another assembly, and 104 on GRCh38 with no gnomAD-style expression.

To annotate a VCF, join on the four VCF fields. A small one to try (a real VCF works the same way; its `##` header
lines are skipped):

```bash
printf '##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\nchr6\t26090951\t.\tC\tG\t.\t.\t.\nchr13\t32338445\t.\tA\tC\t.\t.\t.\nchr17\t43124027\t.\tACT\tA\t.\t.\t.\nchr1\t10000\t.\tA\tG\t.\t.\t.\n' > my.vcf
```

```sql
SELECT x.chrom, x.pos, x.ref, x.alt, h.vrs_id, h.variation_id, h.clinvar_call, h.review_level
FROM read_csv('my.vcf', delim = '\t', comment = '#', header = false, auto_detect = false,
              columns = {'chrom': 'VARCHAR', 'pos': 'BIGINT', 'id': 'VARCHAR', 'ref': 'VARCHAR', 'alt': 'VARCHAR',
                         'qual': 'VARCHAR', 'filter': 'VARCHAR', 'info': 'VARCHAR'}) x
LEFT JOIN 'clinvar-vrs-grch38.parquet' h
       ON h.chrom = replace(x.chrom, 'chr', '') AND h.pos = x.pos AND h.ref = x.ref AND h.alt = x.alt
ORDER BY x.chrom, x.pos;
```

```text
chrom  pos       ref  alt  vrs_id                                     variation_id   clinvar_call                                  review_level
chr1   10000     A    G    NULL                                       NULL           NULL                                          NULL
chr13  32338445  A    C    ga4gh:VA.Apas_jvqBJU7l4DGHGlvTGRY3BBh-UR9  clinvar:51592  Benign                                        expert panel
chr17  43124027  ACT  A    ga4gh:VA.EE08XW4IpzeWhJAwComKOSmsPHTcP-1R  clinvar:17662  Pathogenic                                    expert panel
chr6   26090951  C    G    ga4gh:VA.ELQCnIBGqaTl0AEE0Az18XZ2cgIHAQIY  clinvar:10     Conflicting classifications of pathogenicity  criteria provided
```

`auto_detect = false` is needed: DuckDB's CSV sniffer rejects a VCF's header lines. For a tool that wants text,
such as `bcftools annotate`, write the table as tab-separated text instead:
`COPY (SELECT * FROM 'clinvar-vrs-grch38.parquet') TO 'clinvar-vrs-grch38.tsv' (HEADER, DELIMITER '\t')`.

**Why this is hard with ClinVar's XML.** The XML describes a variant by coordinates and HGVS expressions per
assembly, with no identifier computed from the change itself. Matching another dataset means normalizing both
sides the same way (shifting insertions and deletions, choosing a representation) and hoping they agree. Here
each allele carries its VRS id, which any VRS implementation computes the same way from the same normalized
change.

## Conflicting-classification watchlist { #conflict-watchlist }

**The question.** Every variant ClinVar calls *Conflicting classifications of pathogenicity*, one row each, with
how many submissions sit on each side and who submitted them.

**For** curators, expert panels and laboratories deciding which conflicts to resolve, and anyone tracking whether
a lab's submissions disagree with others'.

**Reads** `vcv` (148 MB), `evidenceLine` (265 MB), `scv` (785 MB) and `submitter`.

The call comes from one level of submissions (expert panel, criteria provided, …). The root statement's
`.contributing` evidence line names that level's statement, and the level's own `.contributing` evidence line
names its SCVs, so the query counts exactly the submissions behind the call
([Why a variant is "conflicting"](#conflicting-classifications) walks one variant).

```sql
COPY (
  WITH conflicting AS (             -- the germline pathogenicity root statement of each conflicting variant
    SELECT id AS vcv_statement, split_part(id, '-', 1) AS vcv
    FROM 'vcv.parquet'
    WHERE regexp_matches(id, '-G-PATH$')
      AND classification.name = 'Conflicting classifications of pathogenicity'
  ),
  level AS (                        -- the level statement the call comes from (-CP, -EP, ...)
    SELECT c.vcv, c.vcv_statement, item.id AS level_statement
    FROM conflicting c
    JOIN 'evidenceLine.parquet' el ON el.id = c.vcv_statement || '.contributing',
         unnest(el.hasEvidenceItems) AS t(item)
  ),
  scvs AS (                         -- the submissions that level counts
    SELECT l.vcv, l.vcv_statement, item.id AS scv_id
    FROM level l
    JOIN 'evidenceLine.parquet' el ON el.id = l.level_statement || '.contributing',
         unnest(el.hasEvidenceItems) AS t(item)
    WHERE item.section = 'scv'
  ),
  said AS (
    SELECT x.vcv, x.vcv_statement, x.scv_id,
           CASE WHEN s.classification.primaryCoding.code IN ('pathogenic', 'likely pathogenic') THEN 'P/LP'
                WHEN s.classification.primaryCoding.code IN ('benign', 'likely benign')         THEN 'B/LB'
                WHEN s.classification.primaryCoding.code = 'uncertain significance'            THEN 'VUS'
                ELSE coalesce(s.classification.primaryCoding.code, s.classification.name) END AS side,
           sub.name AS submitter
    FROM scvs x
    JOIN 'scv.parquet' s ON s.id = x.scv_id
    LEFT JOIN 'submitter.parquet' sub
           ON sub.id = [c.contributor FOR c IN s.contributions IF c.activityType = 'submitted'][1]
  )
  SELECT vcv,
         'clinvar:' || CAST(substr(vcv, 4, 9) AS INTEGER) AS variation_id,
         count(*) AS scvs,
         count(*) FILTER (WHERE side = 'P/LP') AS p_lp,
         count(*) FILTER (WHERE side = 'VUS')  AS vus,
         count(*) FILTER (WHERE side = 'B/LB') AS b_lb,
         list(DISTINCT submitter ORDER BY submitter) FILTER (WHERE side = 'P/LP') AS p_lp_submitters,
         list(DISTINCT submitter ORDER BY submitter) FILTER (WHERE side = 'VUS')  AS vus_submitters,
         list(DISTINCT submitter ORDER BY submitter) FILTER (WHERE side = 'B/LB') AS b_lb_submitters
  FROM said
  GROUP BY vcv
  ORDER BY vcv
) TO 'conflicts-watchlist.parquet' (FORMAT parquet);
```

4 seconds; 184,296 rows, one per conflicting variant, matching the count in
[Why a variant is "conflicting"](#conflicting-classifications). The submitter lists are `NULL` where a side has
no submissions. The widest disagreements, pathogenic against benign:

```sql
SELECT vcv, scvs, p_lp, vus, b_lb, len(p_lp_submitters) AS p_lp_labs, len(b_lb_submitters) AS b_lb_labs
FROM 'conflicts-watchlist.parquet'
WHERE p_lp > 0 AND b_lb > 0
ORDER BY scvs DESC, vcv
LIMIT 3;
```

```text
vcv               scvs  p_lp  vus  b_lb  p_lp_labs  b_lb_labs
VCV000002547.121    34    11   21     2         10          2
VCV000002542.117    33     1   17    15          1         15
VCV000163878.87     33     3   29     1          3          1
```

1,297 conflicts have submissions on both the pathogenic and the benign side; 152,879 are uncertain against
benign, and 30,004 pathogenic against uncertain. A few dozen count other classifications (risk factor, low
penetrance) on one side, which the three columns leave out. Filter on a submitter's name in the lists to watch
one laboratory's conflicts, or join `variation_id` to the [gene-panel](#gene-panel) ids.

**Why this is hard with ClinVar's XML.** The XML gives the conflicting call and a text description of the counts,
but to name the disagreeing submitters you have to collect the variant's submissions and work out which review
level ClinVar counted. Here the evidence lines record which submissions the call was made from.

## One submitter's dataset { #submitter-dataset }

**The question.** Everything one submitter has in ClinVar: each SCV with its variant, condition, classification
and date, next to ClinVar's own call for the variant.

**For** a laboratory auditing its submissions, a consortium collecting its members' work, or anyone comparing one
submitter with the aggregate. [Auditing a Submitter's Footprint](../user-story-audit.md) tells this story in
depth.

**Reads** `submitter`, `scv` (785 MB), the four proposition tables (405 MB), `variation` (1.7 GB), `condition` and
`vcv` (148 MB).

```sql
COPY (
  WITH sub AS (
    SELECT id FROM 'submitter.parquet' WHERE name = 'Mayo Clinic Laboratories, Mayo Clinic'   -- <- your submitter
  ),
  mine AS (                         -- the submitter's SCVs
    SELECT s.id, s.proposition, s.classification.name AS classification, s.quality.name AS level,
           [x.date FOR x IN s.contributions IF x.activityType = 'evaluated'][1] AS last_evaluated
    FROM 'scv.parquet' s
    WHERE [x.contributor FOR x IN s.contributions IF x.activityType = 'submitted'][1] IN (SELECT id FROM sub)
  ),
  prop AS (
    SELECT id, subject, object, object_section
    FROM read_parquet('proposition*.parquet', union_by_name = true)
  ),
  call AS (                         -- ClinVar's germline pathogenicity call per variant
    SELECT 'clinvar:' || CAST(substr(id, 4, 9) AS INTEGER) AS variation_id, classification.name AS clinvar_call
    FROM 'vcv.parquet'
    WHERE regexp_matches(id, '-G-PATH$')
  )
  SELECT replace(m.id, 'clinvar.submission:', '') AS scv,
         p.subject AS variation_id, v.name AS variation_name,
         c.name    AS condition,                  -- NULL when the object is a condition set
         m.classification, m.level, m.last_evaluated,
         k.clinvar_call
  FROM mine m
  JOIN prop p ON p.id = m.proposition
  LEFT JOIN 'variation.parquet' v ON v.id = p.subject
  LEFT JOIN 'condition.parquet' c ON c.id = CASE WHEN p.object_section = 'condition' THEN p.object END
  LEFT JOIN call k ON k.variation_id = p.subject
  ORDER BY scv
) TO 'mayo-scvs.parquet' (FORMAT parquet);
```

Under a second; 56,132 rows. Selected columns:

```text
scv             variation_name                            condition      classification     clinvar_call
SCV000256908.1  NM_000038.6(APC):c.1045C>T (p.Gln349Ter)  not provided   Likely pathogenic  Pathogenic
SCV000256909.1  NM_000038.6(APC):c.120G>A (p.Glu40=)      not specified  Likely benign      Benign/Likely benign
SCV000256910.3  NM_000038.6(APC):c.1213C>T (p.Arg405Ter)  not provided   Pathogenic         Pathogenic
```

How the submitter's calls line up with ClinVar's:

```sql
SELECT classification, clinvar_call, count(*) AS scvs
FROM 'mayo-scvs.parquet'
GROUP BY ALL
ORDER BY scvs DESC
LIMIT 4;
```

```text
classification          clinvar_call                                  scvs
Uncertain significance  Uncertain significance                        12963
Benign                  Benign                                        10046
Benign                  Benign/Likely benign                           8805
Uncertain significance  Conflicting classifications of pathogenicity   6112
```

**As records.** To keep the submitter's records as published, for sharing or for the GA4GH libraries, cut a
mini-bundle from a full bundle (about 4.9 GB) with `gkm-bundle-parquet`. It streams the bundle once per hop, with
little memory; this full-bundle command wasn't run for this page:

```bash
uvx gkm-bundle-parquet@2.0.0 select --full clinvar-gkm_00-latest.json.gz "${P[@]}" \
    --driver scv --where "[c.contributor FOR c IN contributions IF c.activityType = 'submitted'][1] = 'clinvar.submitter:500068'" \
    --follow out \
    --out mayo.json.gz
```

`P` is the schema array from [Gene-panel subset](#gene-panel); look up the submitter id with
`SELECT id, name FROM 'submitter.parquet' WHERE name ILIKE '%mayo%'`. `--follow out` from the SCVs adds their
propositions, variants, alleles, locations, conditions and the submitter. The same command on a weekly delta
returns only the week's changed SCVs, and needs `--max-depth 4`
([On a delta, set `--max-depth`](../build/cli-reference.md#selection)); [Your First Dataset](../build/first-dataset.md)
walks one.

**Why this is hard with ClinVar's XML.** A submitter's assertions are spread across the variant records they are
about, so collecting one submitter's work means reading every variant record in the release. Here it is one
filter on the `scv` table, and the joins bring the variant, the condition and ClinVar's call alongside.

## Flat analysis table, one row per SCV { #flat-scv-table }

**The question.** One wide table, one row per submission: the variant, the proposition, the condition, the
submitter, the classification, the date and the cited PubMed ids, for pandas, R or a statistics package.

**For** analysts who want ClinVar as a single data frame.

**Reads** `scv` (785 MB), the four proposition tables (405 MB), `variation` (1.7 GB), `submitter`, `condition`
and `conditionSet`.

```sql
COPY (
  WITH prop AS (                    -- all four proposition tables, one glob
    SELECT id, type, subject, object, object_section
    FROM read_parquet('proposition*.parquet', union_by_name = true)
  ),
  set_names AS (                    -- a condition set's member names, in one string
    SELECT cs.id, string_agg(c.name, '; ' ORDER BY c.name) AS member_names
    FROM 'conditionSet.parquet' cs, unnest(cs.concepts) AS t(m)
    JOIN 'condition.parquet' c ON c.id = m.id
    GROUP BY cs.id
  )
  SELECT replace(s.id, 'clinvar.submission:', '')                      AS scv,
         p.subject                                                     AS variation_id,
         v.name                                                        AS variation_name,
         p.type                                                        AS proposition_type,
         p.object                                                      AS condition_id,
         coalesce(c.name, sn.member_names)                             AS condition_name,
         sub.name                                                      AS submitter,
         s.classification.name                                         AS classification,
         s.classification.primaryCoding.code                           AS classification_code,
         s.quality.name                                                AS level,
         [x.date FOR x IN s.contributions IF x.activityType = 'evaluated'][1] AS last_evaluated,
         [r.pmid FOR r IN s.reportedIn IF r.pmid IS NOT NULL]          AS pmids
  FROM 'scv.parquet' s
  JOIN prop p ON p.id = s.proposition
  LEFT JOIN 'variation.parquet' v  ON v.id = p.subject
  LEFT JOIN 'submitter.parquet' sub
         ON sub.id = [x.contributor FOR x IN s.contributions IF x.activityType = 'submitted'][1]
  LEFT JOIN 'condition.parquet' c ON c.id = CASE WHEN p.object_section = 'condition'    THEN p.object END
  LEFT JOIN set_names sn          ON sn.id = CASE WHEN p.object_section = 'conditionSet' THEN p.object END
) TO 'scv-flat.parquet' (FORMAT parquet);
```

10 seconds and 4.8 GB of memory on the test laptop; 6,895,428 rows, every SCV in the release, in a 254 MB file.
Every row has a variant name, a condition name and a submitter. Three rows for one variant, selected columns:

```text
scv             variation_id   condition_name                                    submitter                                                   classification_code  last_evaluated
SCV008145163.1  clinvar:17662  BRCA1-related cancer predisposition               Hema, HEMA – Genetic and Molecular Diagnostic Laboratory    pathogenic           2026-09-14
SCV000806982.5  clinvar:17662  BRCA1-related disorder                            PreventionGenetics, part of Exact Sciences                  pathogenic           2026-09-13
SCV006560819.2  clinvar:17662  Inherited ovarian cancer (without breast cancer)  Genetics Laboratory, Great Ormond Street Hospital NHS …      pathogenic           2026-09-11
```

`pmids` is a list column; pandas reads it as arrays, and `unnest(pmids)` in DuckDB gives one row per citation.
For a spreadsheet, drop the list or join it to text (`array_to_string(pmids, ';')`) and write CSV
([Export a slice](#export)). The file is a derived table: [Data Use and Citation](../data-use.md) says how to
attribute it if you share it.

**Why this is hard with ClinVar's XML.** Each submission in the XML nests its submitter, its trait set, its
citations and its classification in separate elements under the variant record, and a flat table needs a parser
for each. Here they are typed columns of related tables, and one query joins them.

## Export a slice to CSV or Parquet { #export }

Spreadsheets and many tools can't read Parquet, and you rarely want a whole table anyway. Wrap any query in `COPY` to write its result to a file:

```sql
-- Expert-panel and practice-guideline submissions, with their variant
COPY (
  WITH prop AS (
    SELECT id, subject FROM read_parquet('proposition*.parquet', union_by_name = true)
  )
  SELECT replace(s.id, 'clinvar.submission:', '') AS scv,
         p.subject AS variant_id,
         s.classification.name AS classification,
         s.quality.name        AS level
  FROM 'scv.parquet' s
  JOIN prop p ON p.id = s.proposition
  WHERE s.quality.name IN ('expert panel', 'practice guidelines')
) TO 'expert_scvs.csv' (HEADER);
```

In 2026-11-15 that writes 25,962 rows plus a header. For another analytics tool, write Parquet instead, which keeps the column types and is far smaller: `TO 'expert_scvs.parquet' (FORMAT parquet)`.

To share a slice as **records** rather than rows, so others can read it with the same tools as the full release, cut a [mini-bundle](build-your-own.md#cut-a-mini-bundle) instead.
