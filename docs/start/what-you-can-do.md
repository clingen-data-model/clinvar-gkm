# What You Can Do

ClinVar-GKM turns each ClinVar release into typed records you can query directly: variants with computed
identifiers, every submission (SCV) as a structured statement, and ClinVar's own aggregate calls (VCV, RCV) with
the evidence lines that link them to the submissions behind them. This page is a gallery of questions that
structure makes practical. Each card names the data it reads and links to the query, recipe or page that answers it.

Each card carries a status tag, the same scheme as the [What It Unlocks](../reference/presentations/clinvar-gkm-unlocks.md)
presentation:

| Tag | Meaning |
| --- | --- |
| **Available now** | The published data answers it today, with the query or page linked from the card. |
| **Within reach** | The data supports it; the tool or app that packages it does not exist yet. |
| **On the roadmap** | Needs data or features ClinVar-GKM does not publish yet. |

Five of the cards have a full, tested query on this page, under [In depth](#in-depth). The others link to the
page that already covers them.

---

## Explore a variant

<div class="grid cards" markdown>

-   **What does ClinVar say about my variant?**

    ---

    **Available now** · anyone with a variant

    **Data:** `variation`, the proposition tables, `vcv`, `rcv`, `scv`, `submitter`, `condition`

    **Why it is hard with ClinVar XML:** a variant's aggregate calls, submissions and conditions are spread over
    nested elements of one large record per accession.

    **Try it:** [Everything ClinVar says about one variant](../parquet/recipes.md#one-variant) ·
    **Concept:** [VCV Statements](../output-reference/vcv-statements.md)

-   **Is my variant the one ClinVar classified?**

    ---

    **Available now** · labs, knowledgebases, anyone joining ClinVar to their own data

    **Data:** `allele` (`id`, a `ga4gh:VA.…` VRS identifier), `variation.members`

    **Why it is hard with ClinVar XML:** matching means normalizing HGVS, transcripts and coordinates on both sides;
    with VRS the join is an equality on a computed id.

    **Scope:** each variant has one member allele, its defining allele (GRCh38 where ClinVar has one). An id
    computed on another assembly won't match, and no lifted-over allele is published to join on.

    **Try it:** [User Story: Harmonizing ClinVar by VRS Identity](../user-story.md) ·
    **Concept:** [Variations](../output-reference/cat-vrs.md)

-   **Can I recompute a variant's VRS identifier myself?**

    ---

    **Available now** · developers, anyone checking identifiers

    **Data:** `allele`, `location`, `sequenceReference`, or the bundle

    **Why it is hard with ClinVar XML:** ClinVar's XML carries no VRS identifiers; computing one needs a normalized
    allele, which the bundle already holds.

    **Try it:** [VRS alleles and their identifiers](../working-in-python.md#vrs-alleles-and-their-identifiers) ·
    **Concept:** [GA4GH Standards](../reference/gks-standards.md)

-   **Which other identifiers point to this variant?**

    ---

    **Available now** · integrators, curators

    **Data:** `variation.mappings` (ClinVar, dbSNP, ClinGen Allele Registry, and others),
    `variation.extensions` → `clinvarHgvsList` (MANE Select and MANE Plus Clinical flags, Sequence Ontology
    consequences)

    **Why it is hard with ClinVar XML:** cross-references and HGVS expressions sit in different parts of the record,
    each with its own shape.

    **Try it:** the [`variation` columns](../parquet/tables.md#variation) ·
    **Concept:** [Mappings](../output-reference/cat-vrs.md#mappings)

-   **Which papers back a variant's classifications?**

    ---

    **Available now** · curators, researchers

    **Data:** `scv.reportedIn` (PubMed ids, DOIs, URLs), the proposition tables, `variation`

    **Why it is hard with ClinVar XML:** citations are attached at several levels of a submission, in mixed formats.

    **Try it:** [PubMed ids cited for a variant](../parquet/recipes.md#pubmed-ids-for-a-variant) ·
    [for every variant in a gene](../parquet/recipes.md#pubmed-ids-for-a-gene) ·
    **Concept:** [Citations](../output-reference/scv-statements.md#citations)

</div>

---

## Curate and audit

<div class="grid cards" markdown>

-   **What would the call be under my own rules?**

    ---

    **Available now** · curators, lab directors, methods researchers

    **Data:** `scv`, `propositionPathogenicity`, `vcv`

    **Why it is hard with ClinVar XML:** you would have to rebuild the submission-to-variant links and ClinVar's
    precedence rules before changing one of them.

    **Try it:** [Re-run the aggregation](#own-rules) (CLI; tested below) ·
    **Concept:** [VCV aggregation](../reference/glossary.md#vcv-aggregation)

-   **Why is a variant conflicting, and who disagrees?**

    ---

    **Available now** · curators, expert panels

    **Data:** `vcv`, `evidenceLine`, `scv`, `submitter`

    **Why it is hard with ClinVar XML:** the XML gives the conflict label and counts, not a table of which
    submission sits at which level and whether it counted.

    **Try it:** [Why a variant is "conflicting"](../parquet/recipes.md#conflicting-classifications) ·
    **Concept:** [Layer Hierarchy](../output-reference/vcv-statements.md#layer-hierarchy)

-   **How well were submitted conditions mapped?**

    ---

    **Available now** · curators, ClinVar submitters, data stewards

    **Data:** `scv.extensions` → `submittedCondition` (`normalized_resolution`, `original_medgen_match`,
    `direct_match`), `submitter`

    **Why it is hard with ClinVar XML:** the XML gives the submitted trait and the RCV's trait, not how one was
    matched to the other.

    **Try it:** [Measure condition-mapping quality](#condition-mapping-quality) (CLI; tested below) ·
    **Concept:** [SubmittedCondition](../output-reference/scv-statements.md#submittedcondition)

-   **Where does a submitter's gene differ from the variant's gene?**

    ---

    **Available now** · curators, submitters

    **Data:** the proposition tables' `geneContextQualifier`, with its `submittedGeneSymbols` and
    `geneContextSource` extensions

    **Why it is hard with ClinVar XML:** submitted gene symbols are free text beside the variant's gene list, with
    nothing saying whether they agree.

    **Try it:** [Gene context](../parquet/tables.md#gene-context) (filter on
    `geneContextSource = 'submittedSymbolDiffers'`) ·
    **Concept:** [Qualifier Extensions](../output-reference/scv-statements.md#qualifier-extensions)

-   **What does our lab's ClinVar footprint look like?**

    ---

    **Available now** · ClinVar submitters

    **Data:** `submitter`, `scv`, the proposition tables, `condition`, `therapy`

    **Why it is hard with ClinVar XML:** there is no export of "everything we submitted" as a table to re-run
    each release.

    **Try it:** [User Story: Auditing a Submitter's ClinVar Footprint](../user-story-audit.md) ·
    [One submitter's footprint](../parquet/recipes.md#submitter-footprint) ·
    **Concept:** [Review Status](../profiles/review-status.md)

-   **Which of my variants were reclassified this week?**

    ---

    **Available now** · labs re-contacting patients, curators watching a gene panel

    **Data:** a weekly delta and its manifest, your copy of last week's `vcv` table

    **Why it is hard with ClinVar XML:** each release is a new full file; finding what changed means diffing two
    of them yourself.

    **Try it:** [A weekly reclassification alert](#weekly-alert) (CLI; tested below) ·
    [Keep Your Data Current](../data-access/keep-current.md) ·
    **Concept:** [The delta manifest](../data-access/weekly-deltas.md#manifestjson)

</div>

---

## Oncology

<div class="grid cards" markdown>

-   **Which variants predict response to a drug in a tumor type?**

    ---

    **Available now** · molecular tumor boards, oncology knowledgebases

    **Data:** `propositionSomaticClinicalImpact` (therapeutic-response rows, `conditionQualifier`), `therapy`,
    `therapyGroup`, `condition`

    **Why it is hard with ClinVar XML:** drugs, drug combinations and the tumor context are free-text parts of a
    somatic submission, not linked records.

    **Try it:** [Drug response in a tumor type](#drug-response) (console or CLI; tested below; runs in the
    [live console](../parquet/index.md#run-a-query-now)) ·
    **Concept:** [`propositionSomaticClinicalImpact`](../parquet/tables.md#propositionSomaticClinicalImpact)

-   **Which somatic variants are Tier I or Tier II, and for what?**

    ---

    **Available now** · oncology curators

    **Data:** `evidenceLine` (the SCV lines: `targetProposition`, `evidenceOutcome`), `propositionSomaticClinicalImpact`

    **Why it is hard with ClinVar XML:** the AMP/ASCO/CAP tier and the specific impact (diagnostic, prognostic,
    therapeutic) are separate pieces of a somatic submission.

    **Try it:** [Reading a variant's statements](../parquet/tables.md#reading-a-variants-statements) and the
    [`evidenceLine` columns](../parquet/tables.md#evidenceLine) ·
    **Concept:** [Proposition Types](../profiles/propositions.md)

</div>

---

## Build and integrate

<div class="grid cards" markdown>

-   **Can I drop my ClinVar XML parser?**

    ---

    **Available now** · developers

    **Data:** a monthly full bundle or the Parquet set, then one weekly delta a week

    **Why it is hard with ClinVar XML:** a bespoke parser, variant normalization, and a patch for every XML change.

    **Try it:** [Keep Your Data Current](../data-access/keep-current.md) ·
    [Working in Python](../working-in-python.md) ·
    **Concept:** [Output Format](../output-reference/overview.md)

-   **Can I get just my gene panel, as a small bundle or tables?**

    ---

    **Available now** · labs, tool builders

    **Data:** any published bundle, cut with `gkm-bundle-parquet select`

    **Why it is hard with ClinVar XML:** a subset means parsing everything, then re-linking the pieces you kept.

    **Try it:** [Cut a mini-bundle](../parquet/build-your-own.md#cut-a-mini-bundle) ·
    **Concept:** [ID References](../output-reference/id-references.md)

-   **Can I build a VCF scoped to my panel and quality bar?**

    ---

    **Within reach** · clinical pipelines

    **Data:** `allele` (`expressions`: SPDI, gnomAD-style), `vcv`, the proposition tables

    **Why it is hard with ClinVar XML:** ClinVar's VCF is one fixed cut; a different one means starting from the
    XML.

    **Status:** the tables hold what such a VCF needs; no packaged exporter exists yet. A
    [genomic window](../parquet/recipes.md#genomic-window) and the [gene rollup](../parquet/recipes.md#gene-rollup)
    show the joins.

-   **Can my RAG system, agent or knowledge graph use ClinVar as ground truth?**

    ---

    **Within reach** · AI and tool builders

    **Data:** the bundle: statements with explicit propositions (subject, predicate, object), typed
    classifications, stable ids

    **Why it is hard with ClinVar XML:** the same meaning is written in several shapes, so every consumer
    re-interprets it.

    **Status:** the data is in that shape today; the applications are for others to build. See
    [Proposition Types](../profiles/propositions.md).

-   **Can I review and submit to ClinVar from my own system?**

    ---

    **Within reach** · ClinVar submitters, LIMS vendors

    **Data:** your SCVs as VA-Spec statements (`scv`), compared with ClinVar's current calls (`vcv`)

    **Why it is hard with ClinVar XML:** comparing your records with ClinVar's means parsing ClinVar first.

    **Status:** comparison works today ([User Story: Auditing a Submitter's ClinVar Footprint](../user-story-audit.md));
    submission tooling built on the model is an opportunity, not a product.

</div>

---

## Research at scale

<div class="grid cards" markdown>

-   **How have classifications changed since a past release?**

    ---

    **Available now**, from 2026-06-27 · researchers, curators

    **Data:** the `vcv` table of today and of a past release, built from an archived monthly

    **Why it is hard with ClinVar XML:** two releases of XML in two shapes, each parsed and normalized, before
    any comparison.

    **Try it:** [Compare classifications across releases](#compare-releases) (CLI; tested below) ·
    [Track Change Over Time](../build/track-change.md) ·
    **Concept:** [Previous Releases](../data-access/previous-releases.md)

-   **How do ClinVar's calls roll up by gene?**

    ---

    **Available now** · researchers, panel designers

    **Data:** `variation` (`clinvarGeneList`), `gene`, `vcv`

    **Why it is hard with ClinVar XML:** gene associations and the aggregate call are in different parts of each
    record.

    **Try it:** [Gene rollup of ClinVar's calls](../parquet/recipes.md#gene-rollup) ·
    **Concept:** [Gene context versus gene list](../parquet/tables.md#gene-context)

-   **Which classifications carry a mode of inheritance or a penetrance qualifier?**

    ---

    **Available now** · researchers, curators

    **Data:** `propositionPathogenicity` and `propositionClinvarCustom`: `modeOfInheritanceQualifier`
    (with its HPO code), `penetranceQualifier`

    **Why it is hard with ClinVar XML:** inheritance is free text on the submission, and low penetrance is folded
    into the classification text.

    **Try it:** [The proposition columns](../parquet/tables.md#proposition-columns) ·
    **Concept:** [Qualifier Types](../reference/glossary.md#qualifier-types)

-   **How has ClinVar changed over years, not months?**

    ---

    **On the roadmap** · researchers

    **Data:** ClinVar-GKM's history starts with the 2026-06-27 release; earlier ClinVar releases are not
    published in this form.

    **Status:** comparison within the published range works today (above). Longer history, and reclassification
    trend studies across ClinVar's past, need earlier releases transformed. See the [Roadmap](../reference/roadmap.md).

-   **Can I use case-level observations and functional evidence?**

    ---

    **On the roadmap** · researchers, variant scientists

    **Data:** not yet in the bundle: ClinVar's case-level observations and functional data (including MaveDB)
    are planned.

    **Status:** see the [Roadmap](../reference/roadmap.md).

</div>

---

## In depth { #in-depth }

The five tested cards. Each query ran as written against the **2026-11-15 release** (the Parquet set published
2026-11-20 at `v1/1.2/parquet/`); re-run them to get today's numbers.

!!! note "Prerequisites"
    - **[DuckDB CLI](https://duckdb.org/docs/installation/)**, tested with **1.5.4**. No extension is needed for
      downloaded files; a query that names a `https://` URL loads DuckDB's `httpfs` extension the first time.
    - **The tables each query reads**, downloaded into the directory you start `duckdb` from, as on
      [Parquet Files → Download](../data-access/parquet.md#download). Each section names its tables and their
      sizes. [Drug response in a tumor type](#drug-response) reads the published URLs and needs nothing
      downloaded.
    - [A weekly reclassification alert](#weekly-alert) and [Compare classifications across releases](#compare-releases)
      also build tables from a bundle with
      [`gkm-bundle-parquet`](../parquet/build-your-own.md#install) 2.0.0, run with `uvx` from
      [uv](https://docs.astral.sh/uv/getting-started/installation/) (tested with 0.6.14), and use `curl`,
      `python3` and `shasum` (macOS) or `sha256sum` (Linux). Each section's commands run in one directory, in
      bash or zsh: later blocks read the files earlier ones write.
    - The [live console](../parquet/index.md#run-a-query-now) takes no query from a link. To run a query there,
      copy it into the console. Only [Drug response in a tumor type](#drug-response) reads tables small enough
      for it; the others read large tables, which the console stops after 15 seconds.

### Re-run ClinVar's aggregation under your own rules { #own-rules }

ClinVar's germline call for a variant comes from its highest-ranked submissions: practice guideline and expert
panel above *criteria provided*, which is above *no assertion criteria*. Among submissions at the winning level,
any disagreement between *pathogenic or likely pathogenic*, *uncertain significance* and *benign or likely
benign* makes the call *Conflicting*. Every SCV, its level and its classification are rows, so you can change a
rule and recompute the call for every variant.

The query below keeps only submissions with assertion criteria (it drops flagged and *no assertion criteria*
submissions), lets the highest level win, and treats only *P/LP* against *B/LB* as a conflict: an *uncertain
significance* submission no longer blocks a call. It then counts the variants whose call differs from ClinVar's.
The lines marked `-- <-` are the rules; change them to try your own.

**CLI.** Tables: `scv.parquet` (785 MB), `propositionPathogenicity.parquet` (403 MB), `vcv.parquet` (148 MB). About 5
seconds on a laptop.

```sql
WITH sub AS (                    -- 1. the submissions your rule keeps
  SELECT p.subject AS variant,
         CASE WHEN s.quality.name IN ('practice guidelines', 'expert panel') THEN 2 ELSE 1 END AS rank,
         CASE WHEN lower(s.classification.primaryCoding.code) IN
                   ('pathogenic', 'likely pathogenic', 'pathogenic/likely pathogenic') THEN 'P/LP'
              WHEN lower(s.classification.primaryCoding.code) IN
                   ('benign', 'likely benign', 'benign/likely benign')                 THEN 'B/LB'
              WHEN lower(s.classification.primaryCoding.code) = 'uncertain significance'  THEN 'VUS'
         END AS tier
  FROM 'scv.parquet' s
  JOIN 'propositionPathogenicity.parquet' p ON p.id = s.proposition
  WHERE s.proposition_section = 'propositionPathogenicity'
    AND s.quality.name IN ('practice guidelines', 'expert panel', 'criteria provided')  -- <- drops flagged, no criteria
),
mine AS (                        -- 2. your call: the highest level wins; only P/LP against B/LB is a conflict
  SELECT variant,
         CASE WHEN bool_or(tier = 'P/LP') AND bool_or(tier = 'B/LB') THEN 'conflicting'
              WHEN bool_or(tier = 'P/LP') THEN 'P/LP'                 -- <- a VUS no longer blocks a P/LP call
              WHEN bool_or(tier = 'B/LB') THEN 'B/LB'
              WHEN bool_or(tier = 'VUS')  THEN 'VUS'
         END AS my_call
  FROM sub
  WHERE rank = (SELECT max(rank) FROM sub s2 WHERE s2.variant = sub.variant)
  GROUP BY variant
),
clinvar AS (                     -- 3. ClinVar's call: the germline pathogenicity root statement
  SELECT 'clinvar:' || CAST(substr(id, 4, 9) AS INTEGER) AS variant,
         CASE WHEN classification.name IN ('Pathogenic', 'Likely pathogenic', 'Pathogenic/Likely pathogenic') THEN 'P/LP'
              WHEN classification.name IN ('Benign', 'Likely benign', 'Benign/Likely benign')                 THEN 'B/LB'
              WHEN classification.name = 'Uncertain significance'                                             THEN 'VUS'
              WHEN classification.name LIKE 'Conflicting%'                                                    THEN 'conflicting'
         END AS clinvar_call
  FROM 'vcv.parquet'
  WHERE regexp_matches(id, '-G-PATH$')
)
SELECT clinvar_call, my_call, count(*) AS variants
FROM clinvar JOIN mine USING (variant)
WHERE clinvar_call IS DISTINCT FROM my_call
GROUP BY ALL
ORDER BY variants DESC;
```

```text
clinvar_call  my_call  variants
conflicting   B/LB      152,833
conflicting   P/LP       29,763
NULL          VUS           191
NULL          P/LP           61
conflicting   VUS            58
```

Under this rule, 182,596 of ClinVar's 184,296 *Conflicting* variants get a single call: most of ClinVar's
conflicts are a *VUS* against a benign or a pathogenic majority. The `NULL` rows are variants whose ClinVar call
is outside the four groups (a risk allele, a low-penetrance call), and the `conflicting → VUS` rows conflict over
such a call.

As a check, change rule 2 to ClinVar's own (`WHEN count(DISTINCT tier) > 1 THEN 'conflicting'`): the call then
matches ClinVar's for all but 361 of the 4,323,971 variants the query covers, and each of those 361 has a
submission at the winning level outside the four groups. The query covers only variants with at least one
submission that has assertion criteria; ClinVar still calls the others (132,157 more) from their *no assertion
criteria* submissions.

!!! warning "A research tool, not a new classification"
    The recomputed call is yours. ClinVar's precedence rules, and the reasons a submitter's VUS counts, are in
    [Review Status](../profiles/review-status.md) and the
    [VCV aggregation rules](../pipeline/vcv-statements/vcv-aggregation-rules.md).

### Measure condition-mapping quality { #condition-mapping-quality }

A submitter names a condition with a name, a MedGen id, or ids from OMIM, MONDO, HPO or Orphanet. ClinVar maps it
to one of its conditions, and ClinVar-GKM records how, on each single-condition SCV, in the `submittedCondition`
extension:

- `normalized_resolution`: which reference matched (`tm reftype xref medgen` is the submitted MedGen id,
  `tm reftype preferred name` the submitted name, and so on). `random trait assignment` means none of them
  matched ClinVar's trait mapping, and the condition was paired with the RCV's one remaining unmatched condition.
- `original_medgen_match`: set when the submitted MedGen concept was remapped to a different one.
- `direct_match`: set when the condition the submitted reference matched directly differs from the final one.

**CLI.** Tables: `scv.parquet` (785 MB). About 10 seconds.

```sql
WITH sc AS (
  SELECT [e.value_object FOR e IN extensions IF e.name = 'submittedCondition'][1] AS c
  FROM 'scv.parquet'
)
SELECT coalesce(c.normalized_resolution, '(none)')    AS resolution,
       count(*)                                        AS scvs,
       count(c.original_medgen_match)                  AS medgen_remapped,
       count(c.direct_match)                           AS direct_differs
FROM sc
WHERE c IS NOT NULL
GROUP BY ALL
ORDER BY scvs DESC;
```

```text
resolution                 scvs       medgen_remapped  direct_differs
tm reftype xref medgen     3,992,100                0               0
tm reftype preferred name  1,816,033          303,702               0
tm reftype xref omim         619,809                0               0
tm reftype xref mondo         91,710                0               0
random trait assignment       39,922            2,114          28,058
tm reftype xref HP             9,848                0               0
tm reftype xref omim.ps          485                0               0
tm reftype xref orpha             55               12              20
(none)                             2                0               2
```

About 6.57 million SCVs name one condition. 39,922 of them were paired by position, not matched; 28,058 of
those carry a `direct_match`, a ClinVar condition the submitted reference points to directly that is not the one
the SCV was paired with. Where that happens
most, by submitter (`submitter.parquet`, 138 KB, as well):

```sql
WITH sc AS (
  SELECT [c.contributor FOR c IN contributions IF c.activityType = 'submitted'][1]            AS submitter,
         [e.value_object.normalized_resolution FOR e IN extensions
          IF e.name = 'submittedCondition'][1]                                                AS resolution
  FROM 'scv.parquet'
)
SELECT sub.name                                                      AS submitter,
       count(*)                                                      AS scvs,
       count(*) FILTER (resolution = 'random trait assignment')      AS random_assignment,
       round(100.0 * random_assignment / scvs, 1)                    AS pct
FROM sc
JOIN 'submitter.parquet' sub ON sub.id = sc.submitter
WHERE resolution IS NOT NULL
GROUP BY ALL
HAVING scvs >= 1000                                                  -- <- only submitters with 1,000+ SCVs
ORDER BY pct DESC
LIMIT 10;
```

```text
submitter                                                            scvs     random_assignment  pct
LDLR-LOVD, British Heart Foundation                                    1,686              1,678  99.5
ClinVar Staff, National Center for Biotechnology Information (NCBI)    1,189                505  42.5
NIHR Bioresource Rare Diseases, University of Cambridge                2,000                295  14.8
OMIM                                                                  37,958              4,860  12.8
…
```

A high share is a prompt to look, not a verdict: it often means the submitter sends condition text that ClinVar's
trait mapping does not cover. Multi-condition SCVs keep the same fields per member in `submittedConditionSet`,
as JSON text; read them as in [Extensions](../parquet/table-anatomy.md#extensions).

### Drug response in a tumor type { #drug-response }

A somatic clinical-impact submission can say that a variant predicts sensitivity or resistance to a drug, or to
a combination of drugs given together, in a tumor type. Each such claim is a therapeutic-response proposition:
its `object` is a `therapy` or a `therapyGroup` (a combination, `membershipOperator` `AND`), and its
`conditionQualifier` is the tumor type.

**Console or CLI.** This query reads four small tables from the published URLs (about 2 MB together), so it runs in the
[live console](../parquet/index.md#run-a-query-now) (about 2 seconds) as well as the DuckDB CLI:

```sql
SELECT p.subject                                  AS variant,
       p.geneContextQualifier.name                AS gene,
       p.predicate,
       coalesce(t.name, (SELECT string_agg(m.name, ' + ' ORDER BY m.name)
                         FROM 'https://data.clinvar-gkm.org/v1/1.2/parquet/therapy.parquet' m
                         WHERE list_contains(g.concepts, m.id)))   AS therapy,
       tumor.name                                 AS tumor_type,
       count(*)                                   AS scvs
FROM 'https://data.clinvar-gkm.org/v1/1.2/parquet/propositionSomaticClinicalImpact.parquet' p
LEFT JOIN 'https://data.clinvar-gkm.org/v1/1.2/parquet/therapy.parquet'      t ON t.id = p.object
LEFT JOIN 'https://data.clinvar-gkm.org/v1/1.2/parquet/therapyGroup.parquet' g ON g.id = p.object
LEFT JOIN 'https://data.clinvar-gkm.org/v1/1.2/parquet/condition.parquet'    tumor ON tumor.id = p.conditionQualifier
WHERE p.type = 'VariantTherapeuticResponseProposition'
GROUP BY ALL
ORDER BY gene, therapy;
```

```text
variant          gene  predicate              therapy                                 tumor_type                                                   scvs
clinvar:3906852  ABL1  predictsResistanceTo   Dasatinib                               Blast phase chronic myelogenous leukemia, BCR-ABL1 positive     1
clinvar:13961    BRAF  predictsSensitivityTo  Cobimetinib + Vemurafenib               Melanoma                                                        1
clinvar:375941   BRAF  predictsSensitivityTo  Dabrafenib + Trametinib                 Melanoma                                                        1
clinvar:13961    BRAF  predictsSensitivityTo  Dabrafenib + Trametinib                 Melanoma                                                        1
clinvar:16609    EGFR  predictsSensitivityTo  Afatinib                                Non-small cell lung carcinoma                                   1
clinvar:16609    EGFR  predictsSensitivityTo  Erlotinib                               Non-small cell lung carcinoma                                   2
clinvar:16613    EGFR  predictsSensitivityTo  Osimertinib                             Non-small cell lung carcinoma                                   1
clinvar:4688085  IRF4  predictsSensitivityTo  Rituximab + acalabrutinib + durvalumab  Primary central nervous system lymphoma                         1
clinvar:4688084  IRF4  predictsSensitivityTo  Rituximab + acalabrutinib + durvalumab  Primary central nervous system lymphoma                         1
clinvar:4327835  IRF4  predictsSensitivityTo  Rituximab + acalabrutinib + durvalumab  Primary central nervous system lymphoma                         1
clinvar:189406   PTEN  predictsResistanceTo   Rituximab + acalabrutinib + durvalumab  Primary central nervous system lymphoma                         1
clinvar:13919    RET   predictsSensitivityTo  Selpercatinib                           Medullary thyroid carcinoma                                     1
```

ClinVar holds few of these yet: 13 therapeutic-response propositions in 12 rows. Add
`AND tumor.name ILIKE '%melanoma%'` or `AND p.predicate = 'predictsResistanceTo'` to the `WHERE` clause to
narrow it. Each proposition's AMP/ASCO/CAP tier is on the SCV's evidence line (`evidenceLine.parquet`, 265 MB:
download it first): `evidenceOutcome.name` of the row whose `targetProposition` is the proposition's `id`.

### A weekly reclassification alert { #weekly-alert }

A delta lists the records a week replaced, and holds their new versions. Since a new ClinVar version is a new
key (`VCV000066284.2-G-PATH` becomes `VCV000066284.3-G-PATH`), a reclassification shows up as a key in the
manifest's `deleted` list and a record with the same accession and statement code in the delta. Pair them, look
the old key up in last week's `vcv` table, and compare the calls. A new version doesn't always mean a new call:
most version bumps are a new or updated submission that leaves the call as it was.

**CLI.** You need:

- **Last week's `vcv.parquet`**, in a folder `last-week/`: the published file you downloaded the week before, or
  the copy you keep current ([Keep Your Data Current](../data-access/keep-current.md)). For a week whose Parquet is
  no longer published, build it: [Parquet for one weekly release](../parquet/build-your-own.md#parquet-for-one-weekly-release).
- **This week's delta and its manifest**, and the delta's `vcv` table. The commands look the paths up in the
  line's `index.json` (a delta moves to its month's folder when the month ends), then build the table, in about
  10 seconds. They work in bash and zsh:

```bash
P=(--bundle-schema https://w3id.org/clingen/schema/clinvar-gkm/1.2.0/clinvar-gkm-bundle.schema.json --version-property schema_version)
curl -fsS -o index.json https://data.clinvar-gkm.org/v1/1.2/index.json
for f in $(python3 -c '
import json, sys
d = next(x for x in json.load(open("index.json"))["deltas"] if x["release"] == sys.argv[1])
print(d["bundle"]["path"], d["manifest"])' 2026-11-08); do
  curl -fsS -O "https://data.clinvar-gkm.org/$f"
done
uvx gkm-bundle-parquet@2.0.0 build --full clinvar-gkm-delta_2026-1108.json.gz "${P[@]}" --tables vcv --out delta/
```

Change `2026-11-08` (and the file name in the last line) to the week you are checking. Then, in `duckdb`, list
the variants on your watch list whose call changed:

```sql
WITH watch(accession) AS (       -- <- your variants' VCV accessions
  VALUES ('VCV000000010'), ('VCV000051592'), ('VCV000066284'), ('VCV000546873')
),
replaced AS (                    -- keys the delta removed: last week's versions of the records it replaced
  SELECT unnest(sections.vcv.deleted) AS id
  FROM read_json('clinvar-gkm-delta_2026-1108.manifest.json', maximum_object_size = 200000000)
),
old AS (                         -- last week's root statements that were replaced
  SELECT split_part(id, '.', 1) AS accession, regexp_replace(id, '^[^-]+', '') AS statement,
         classification.name AS old_call
  FROM 'last-week/vcv.parquet'
  WHERE id IN (SELECT id FROM replaced)
    AND NOT regexp_matches(id, '-(PG|EP|CP|NOCP|NOCL|FLAG)(-T[0-9])?$')
),
new AS (                         -- this week's root statements, from the delta
  SELECT split_part(id, '.', 1) AS accession, regexp_replace(id, '^[^-]+', '') AS statement,
         id AS new_id, classification.name AS new_call
  FROM 'delta/vcv.parquet'
  WHERE NOT regexp_matches(id, '-(PG|EP|CP|NOCP|NOCL|FLAG)(-T[0-9])?$')
)
SELECT accession, new_id, old_call, new_call
FROM old JOIN new USING (accession, statement)
WHERE accession IN (SELECT accession FROM watch)
  AND old_call IS DISTINCT FROM new_call
ORDER BY accession;
```

```text
accession     new_id                  old_call                new_call
VCV000066284  VCV000066284.3-G-PATH   Uncertain significance  Likely pathogenic
VCV000546873  VCV000546873.42-G-PATH  Uncertain significance  Likely pathogenic
```

Tested with the 2026-11-08 delta, and the 2026-10-31 release's `vcv` table as last week's (built from the
`2026-11` monthly). `VCV000000010` also got a new version that week, `.143`, but kept its calls, so it isn't
listed. Over every variant, without the `watch` filter, 167,758 VCV accessions got a new version of a root
statement, and 2,252 of them changed call: most often *Likely benign* to *Benign/Likely benign* (1,086) and
*Uncertain significance* to *Conflicting* (481). The 2026-11-08 delta opened the 1.2 line and is much larger than
a usual week; its manifest is 71 MB, which is why `read_json` is given a larger `maximum_object_size`.

The query reads the root statement of each classification type (`-G-PATH`, `-G-RF`, `-S-ONCO`, …). The same
pairing works for submissions: an SCV key is `clinvar.submission:SCV<n>.<version>`, so match `scv` rows on the
key without its version, using `sections.scv.deleted` and the delta's `scv` table.

### Compare classifications across releases { #compare-releases }

ClinVar-GKM's history starts with the **2026-06-27** release: the oldest monthly, `2026-07` in the frozen `v1/1.1/`
line. Every release since then can be compared with today's, from a monthly, or a monthly plus the weekly deltas
after it. Earlier ClinVar releases are not published in this form.

**CLI.** The published Parquet is only the current release. For a past one, build the table you need from its bundle.
Here, only the germline pathogenicity root statements of the 2026-07 monthly, with
[`gkm-bundle-parquet`](../parquet/build-your-own.md) and the
[1.1.0 column set](../parquet/previous-releases.md#the-110-column-set) (the monthly is in the 1.1 line):

```bash
M=$(curl -fsS https://data.clinvar-gkm.org/v1/1.1/index.json | python3 -c '
import json, sys
print(next(m["path"] for m in json.load(sys.stdin)["datasets"]["monthly"] if m["release"] == "2026-07"))')
curl -f --retry 5 -O "https://data.clinvar-gkm.org/$M" -O "https://data.clinvar-gkm.org/$M.sha256"
shasum -a 256 -c clinvar-gkm_2026-07.json.gz.sha256
uvx gkm-bundle-parquet@2.0.0 build --full clinvar-gkm_2026-07.json.gz \
    --bundle-schema https://w3id.org/clingen/schema/clinvar-gkm/1.1.0/clinvar-gkm-bundle.schema.json \
    --column-set https://dataexchange.clinicalgenome.org/clinvar-gkm/1.2/assets/column-sets/clinvar-gkm-1.1.0.columns.yaml \
    --driver vcv --where "regexp_matches(id, '-G-PATH$')" --max-depth 0 \
    --out vcv-2026-07/
```

The monthly is 4.5 GB. The build streams it and keeps only the selected rows: 11 minutes on a 16 GB laptop, writing `vcv-2026-07/vcv.parquet` (4,273,584 rows). On Linux, use `sha256sum -c` for
`shasum -a 256 -c`. Then compare it with the current `vcv.parquet` (148 MB), matching on the VCV accession
without its version:

```sql
WITH then_ AS (                  -- the 2026-06-27 release, built from the 2026-07 monthly
  SELECT split_part(id, '.', 1) AS accession, classification.name AS call_2026_06_27
  FROM 'vcv-2026-07/vcv.parquet'
  WHERE regexp_matches(id, '-G-PATH$')
),
now_ AS (                        -- the current Parquet set
  SELECT split_part(id, '.', 1) AS accession, classification.name AS call_now
  FROM 'vcv.parquet'
  WHERE regexp_matches(id, '-G-PATH$')
)
SELECT call_2026_06_27, call_now, count(*) AS variants
FROM then_ JOIN now_ USING (accession)
WHERE call_2026_06_27 <> call_now
GROUP BY ALL
ORDER BY variants DESC
LIMIT 10;
```

```text
call_2026_06_27               call_now                                      variants
Benign                        Benign/Likely benign                            16,909
Uncertain significance        Conflicting classifications of pathogenicity    13,319
Pathogenic                    Pathogenic/Likely pathogenic                     4,966
Likely benign                 Conflicting classifications of pathogenicity     3,970
Likely benign                 Benign/Likely benign                             3,227
Likely pathogenic             Conflicting classifications of pathogenicity     1,664
Likely pathogenic             Pathogenic/Likely pathogenic                     1,336
Uncertain significance        Likely benign                                      842
Pathogenic/Likely pathogenic  Conflicting classifications of pathogenicity       637
Pathogenic                    Conflicting classifications of pathogenicity       590
```

Between 2026-06-27 and 2026-11-15, 52,675 of the 4,272,983 variants with a germline pathogenicity call in both
releases changed call; 736 went from *Uncertain significance* to pathogenic or likely pathogenic, and 865 to
benign or likely benign. Add `AND accession = 'VCV000066284'` to the `WHERE` clause to follow one variant.

!!! note "What this comparison can and can't tell you"
    - **The range is short.** Under five months of releases, not ClinVar's history. Trend studies over years need
      earlier releases transformed, which is [on the roadmap](../reference/roadmap.md).
    - **It compares two snapshots.** To see each step in between, compare consecutive releases, or read the
      weekly deltas' manifests as in [A weekly reclassification alert](#weekly-alert).
    - **The two releases are from different lines.** The 2026-07 monthly has schema 1.1.0, today's tables 1.2.0.
      The VCV ids and `classification.name` are the same in both; other columns can differ
      ([Parquet for Previous Releases](../parquet/previous-releases.md)).

[Track Change Over Time](../build/track-change.md) covers comparing releases end to end, for a variant or a
submitter.
