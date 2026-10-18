# FAQ

Answers to recurring questions about how ClinVar content appears in ClinVar-GKM. Each answer states where the
behavior comes from in the pipeline and how to see it in the data.

---

## Where does an SCV proposition's gene context come from?

The gene in an SCV proposition's `geneContextQualifier` always comes from the **variant**, never from the
submitter. The submitter's own gene symbols are kept alongside it, in the `submittedGeneSymbols` extension.

### How the qualifier is built

Step 2 of `gkm_scv_statement_proc` (see [Propositions](../pipeline/scv-statements/propositions.md)) builds the
qualifier as follows:

- **The gene** is the variant's single representative gene, taken from the upstream `single_gene_variation`
  table (built by `clinvar-ingest-bq-tools`). That table picks one gene per variant by a priority order:
    1. a MANE Select transcript named in the variant name
    2. a gene symbol in an HGVS-style variant name, such as `NM_000059.4(BRCA2):c.…`
    3. a star-allele name, such as `CYP2C19*10`
    4. exactly one gene in ClinVar's gene associations for the variant
    5. exactly one submitted association that is not "genes overlapped by variant" or "asserted, but not computed"
    6. exactly one "within single gene" association
    7. for a haplotype or genotype, component variants that all share one gene

  Several of these rules are calculated by the upstream pipeline rather than supplied by ClinVar.
- **The gene sets** the qualifier's `name` (the gene symbol), its `primaryCoding` (the NCBI Gene id) and its
  HGNC `mappings`.
- **The submitter's genes** are the symbols the submitter gave in their submitted variant record. They are
  attached to the qualifier as the `submittedGeneSymbols` extension, verbatim. They never choose the gene.
- **The placeholder** applies when the variant has no single representative gene but the submitter named one.
  The qualifier's `name` is then the literal text `submitted genes were not normalized`, with no
  `primaryCoding`, and the submitter's symbols are in `submittedGeneSymbols`.
- **When neither source has a gene**, the proposition has no `geneContextQualifier`.

VCV and RCV propositions carry no gene context qualifier.

For example, `SCV000024718-PATH` has a qualifier gene of `GBA1` (NCBI Gene `2629`), while the submitter
wrote `GBA`, the gene's previous symbol:

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
  "extensions": [ { "name": "submittedGeneSymbols", "value": ["GBA"] } ]
}
```

### How the two sources compare

Across the 6.74 million SCV propositions in the 2026-10 monthly release:

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

The two sources therefore agree almost everywhere. Three gaps remain:

- **Inferred genes are not marked.** For 881,325 propositions the qualifier states a gene the submitter never
  stated, and nothing in the record distinguishes an inferred gene from a submitted one. Compare `name` with
  `submittedGeneSymbols`: when the extension is absent, the gene is inferred.
- **Placeholder names are not genes.** For the 4,814 placeholder propositions, the submitter's gene is only in
  `submittedGeneSymbols`. Grouping or filtering on the qualifier `name` treats `submitted genes were not
  normalized` as if it were a gene.
- **A differing symbol is usually a renamed gene.** Matching the submitter's symbol to the qualifier's symbol
  by string comparison over-reports disagreement. Only the last two rows of the table above are different
  genes.

### How to see it in the data

The qualifier is part of each SCV proposition in the bundle and in the `data` column of the proposition Parquet
tables:

```sql
SELECT id,
       data->>'$.geneContextQualifier.name'               AS qualifier_gene,
       data->>'$.geneContextQualifier.primaryCoding.code' AS ncbi_gene,
       data->'$.geneContextQualifier.extensions[0].value' AS submitted_gene_symbols
FROM 'varcond-proposition.parquet'
WHERE id IN ('SCV001494816-PATH', 'SCV000024718-PATH', 'SCV005419060-PATH');
```

```text
id                 qualifier_gene                       ncbi_gene  submitted_gene_symbols
SCV005419060-PATH  TTN                                  7273       ["TTN","TTN-AS1"]
SCV001494816-PATH  submitted genes were not normalized  NULL       ["KCNT1"]
SCV000024718-PATH  GBA1                                 2629       ["GBA"]
```

From release 1.0.2, the four proposition Parquet tables also carry typed `gene_context_id` (the qualifier's
`ncbigene:` id, NULL for the placeholder) and `submitted_gene_symbols` columns.

### Gene context is not the variant's gene list

The qualifier holds one representative gene. A variant's full set of ClinVar gene associations — every gene it
lies in, overlaps or is near, each with a relationship type — is a different relationship. It is carried on the
variant as the `clinvarGeneList` extension (see [GeneListItem](../output-reference/classes/GeneListItem.md)).
Use the gene list to find all variants touching a gene, and the gene context qualifier for the gene a
classification is framed around.
