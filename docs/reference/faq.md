# FAQ

Answers to recurring questions about how ClinVar content appears in ClinVar-GKM. Each answer states where the
behavior comes from in the pipeline and how to see it in the data.

---

## Where does an SCV proposition's gene context come from?

The gene in an SCV proposition's `geneContextQualifier` always comes from the **variant**, never from the
submitter. The submitter's own gene symbols are kept alongside it, in the `submittedGeneSymbols` extension. From
1.1.0, a `geneContextSource` extension says where the gene came from.

### How the qualifier is built

Step 2 of `gkm_scv_statement_proc` (see [Propositions](../pipeline/scv-statements/propositions.md)) builds the
qualifier as follows:

- **The gene** is the variant's single representative gene, taken from the upstream `single_gene_variation`
  table (built by `clinvar-ingest-bq-tools`). That table picks at most one gene per variant by rules applied in
  order, strongest evidence first: the gene named in the variant's own name (a MANE transcript, an HGVS-style
  name or a star allele), then ClinVar's gene associations, then the shared gene of a haplotype's or genotype's
  alleles. Several rules are calculated upstream rather than supplied by ClinVar. See the
  [Single Gene Variation method](https://github.com/clingen-data-model/clinvar-ingest-bq-tools/blob/main/docs/methods/single-gene-variation.md) for the rules, the reasons for them and their known limitations.
- **The gene sets** the qualifier's `name` (the gene symbol), its `primaryCoding` (the NCBI Gene id) and its
  HGNC `mappings`. The symbol and HGNC id are the ones the upstream method used for that release, so they come
  with the gene, even for a gene ClinVar names in the variant title without associating it.
- **The submitter's genes** are the symbols the submitter gave in their submitted variant record. They are
  attached to the qualifier as the `submittedGeneSymbols` extension, verbatim and in submitted order. They never
  choose the gene.
- **The source** is the `geneContextSource` extension, on every qualifier from 1.1.0:
    - `submittedSymbolMatches`: the submitter's symbols include the qualifier's symbol
    - `submittedSymbolDiffers`: the submitter gave symbols, but none equals the qualifier's symbol
    - `inferredFromVariant`: the submitter gave no symbols
    - `submittedNotNormalized`: the placeholder (next item)

  Symbols are compared after trimming spaces and ignoring case, so `C19ORF12` matches `C19orf12`. The schema
  accepts only these four values.
- **The placeholder** applies when the variant has no single representative gene but the submitter named one.
  From 1.1.0, the qualifier's `name` is the submitter's symbol, verbatim; several symbols are joined with
  `, ` in submitted order. It has no `primaryCoding`, the submitter's symbols are in `submittedGeneSymbols`, and
  `geneContextSource` is `submittedNotNormalized`. The 1.0.1 releases name it with the literal text
  `submitted genes were not normalized`.
- **When neither source has a gene**, the proposition has no `geneContextQualifier`.

VCV and RCV propositions carry no gene context qualifier.

For example, `SCV000024718-PATH` has a qualifier gene of `GBA1` (NCBI Gene `2629`), while the submitter
wrote `GBA`, the gene's previous symbol. The symbols differ, but the gene is the same:

```json
"geneContextQualifier": {
  "type": "MappableConcept",
  "conceptType": "gene",
  "name": "GBA1",
  "primaryCoding": {
    "code": "2629",
    "name": "GBA1",
    "system": "https://www.ncbi.nlm.nih.gov/gene/",
    "iris": ["https://identifiers.org/ncbigene:2629", "https://www.ncbi.nlm.nih.gov/gene/2629"]
  },
  "mappings": [
    {
      "coding": {
        "code": "4177",
        "system": "https://www.genenames.org",
        "iris": ["https://identifiers.org/hgnc:4177", "https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/4177"]
      },
      "relation": "exactMatch"
    }
  ],
  "extensions": [
    { "name": "submittedGeneSymbols", "value": ["GBA"] },
    { "name": "geneContextSource", "value": "submittedSymbolDiffers" }
  ]
}
```

### How the two sources compare

Across the 6.74 million SCV propositions in the 1.0.1 2026-10 monthly (built from the 2026-09-28 release and
frozen under `v1/1.0/`), the last release before `geneContextSource`, with symbols compared exactly:

| Case | Propositions | Share |
| --- | --- | --- |
| The submitter's gene is the qualifier gene | 5,781,673 | 85.8% |
| The submitter gave the qualifier gene plus others | 101 | <0.1% |
| The submitter's gene differs from the qualifier gene | 27,817 | 0.4% |
| The gene is inferred from the variant; the submitter gave none | 881,325 | 13.1% |
| Placeholder: the submitter gave a gene, the variant has no single gene | 4,814 | 0.1% |
| No gene from either source | 40,849 | 0.6% |

The 27,817 differing cases break down as follows:

| Kind of difference | Propositions | Example |
| --- | --- | --- |
| The submitted symbol is not a gene symbol in the release's gene list — mostly a previous symbol of the same gene (`GBA` → `GBA1`, `MUT` → `MMUT`, `C10orf2` → `TWNK`, `IKBKAP` → `ELP1`) | 24,545 | `SCV000024718-PATH` |
| The submitted gene is another gene ClinVar associates with the variant | 2,541 | `SCV000425435-PATH`: `ITGA4` vs submitted `CERKL` |
| The submitted gene is a gene ClinVar does not associate with the variant | 731 | `SCV004053541-PATH`: `PRAMEF18` vs submitted `PRAMEF22` |

The two sources therefore agree almost everywhere. In the 1.0.1 releases (frozen under `v1/1.0/`), three gaps
remained:

- **Inferred genes were not marked.** For 881,325 propositions the qualifier states a gene the submitter never
  stated, and nothing in the record distinguished an inferred gene from a submitted one. You had to compare
  `name` with `submittedGeneSymbols`: when the extension is absent, the gene is inferred.
- **Placeholder names were not genes.** For the 4,814 placeholder propositions, the submitter's gene was only
  in `submittedGeneSymbols`. Grouping or filtering on the qualifier `name` treated `submitted genes were not
  normalized` as if it were a gene.
- **A differing symbol is usually a renamed gene.** Matching the submitter's symbol to the qualifier's symbol
  by string comparison over-reports disagreement. Only the last two rows of the table above are different
  genes.

From 1.1.0, the first two gaps are closed and the third is labeled:

- Inferred genes are marked `geneContextSource` = `inferredFromVariant`.
- Placeholder names carry the submitter's symbol and are marked `submittedNotNormalized`. A placeholder is still
  not a normalized gene, so filter on `primaryCoding` (or the Parquet `gene_context_id`) when you need one.
  Filtering on `name` alone now also matches placeholders: 29 `TP53` placeholders in 2026-10-18, for example.
- `submittedSymbolDiffers` says only that the symbols differ, not that the genes do. With the case-insensitive
  comparison it covers 28,507 propositions in 2026-10-18, where an exact comparison finds 28,653. The other 146
  differ only by case and are now `submittedSymbolMatches`.

### How to see it in the data

The qualifier is part of each SCV proposition in the bundle and in the `data` column of the proposition Parquet
tables:

```sql
-- Extensions are picked by name: the qualifier can carry two. (`lambda e:` needs DuckDB 1.3 or later.)
SELECT id,
       data->>'$.geneContextQualifier.name'               AS qualifier_gene,
       data->>'$.geneContextQualifier.primaryCoding.code' AS ncbi_gene,
       list_filter(CAST(data->'$.geneContextQualifier.extensions' AS JSON[]),
                   lambda e: e->>'$.name' = 'submittedGeneSymbols')[1]->'$.value' AS submitted_gene_symbols,
       list_filter(CAST(data->'$.geneContextQualifier.extensions' AS JSON[]),
                   lambda e: e->>'$.name' = 'geneContextSource')[1]->>'$.value'  AS gene_context_source
FROM 'propositionPathogenicity.parquet'
WHERE id IN ('SCV001494816-PATH', 'SCV000024718-PATH', 'SCV005419060-PATH', 'SCV000039919-PATH');
```

With 1.1.0 data:

```text
id                 qualifier_gene  ncbi_gene  submitted_gene_symbols  gene_context_source
SCV005419060-PATH  TTN             7273       ["TTN","TTN-AS1"]       submittedSymbolMatches
SCV001494816-PATH  KCNT1           NULL       ["KCNT1"]               submittedNotNormalized
SCV000024718-PATH  GBA1            2629       ["GBA"]                 submittedSymbolDiffers
SCV000039919-PATH  SERPINC1        462        NULL                    inferredFromVariant
```

In the 1.0.1 releases (frozen under `v1/1.0/`), `SCV001494816-PATH` is named `submitted genes were not
normalized` and has no `geneContextSource`.

From 1.1.0, the four proposition Parquet tables also carry typed `gene_context_id` (the qualifier's
`ncbigene:` id, NULL for the placeholder), `submitted_gene_symbols` and `gene_context_source` columns.

### Gene context is not the variant's gene list

The qualifier holds one representative gene. A variant's full set of ClinVar gene associations — every gene it
lies in, overlaps or is near, each with a relationship type — is a different relationship. It is carried on the
variant as the `clinvarGeneList` extension (see [GeneListItem](../output-reference/classes/GeneListItem.md)).
Use the gene list to find all variants touching a gene, and the gene context qualifier for the gene a
classification is framed around.
