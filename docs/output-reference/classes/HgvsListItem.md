# HgvsListItem

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A complex structure for sharing individual HGVS entries associated with Clinvar Variations including nucleotide expressions, protein expressions, molecular consequence and mane select/plus settings for the specific aligned and projected forms of the clinvar variant.

**JSON Schema:** [HgvsListItem](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/HgvsListItem){ target=_blank }

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `nucleotideExpression` | [Expression](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/expression.html#expression){ target=_blank rel=noopener } | 0..1 | The nucleotide HGVS expression with `syntax` (e.g.,` hgvs.c`, `hgvs.g`) and `value` (the HGVS string). ClinVar's submitted text is never altered: when ClinVar supplies an expression with no HGVS type letter (e.g. `NC_000017.10:9481617_9489649del`), it is kept as an extension of the listed expression. If ClinVar also supplies a valid expression for the same accession, that one is listed with extensions `invalidClinvarExpression` (the submitted text) and `expressionMerged` (`true`). Otherwise the listed expression is a repair (the type letter restored) with extensions `originalClinvarExpression` (the submitted text) and `expressionRepaired` (`true`). |
| `nucleotideType` | `string` | 0..1 | The type of nucleotide expression as reported by ClinVar (e.g., `coding`,  `genomic`, `genomic, top-level`). |
| `maneSelect` | `boolean` | 0..1 | `true` if this transcript is designated as MANE Select. Absent or `false` when  not applicable. |
| `manePlus` | `boolean` | 0..1 | `true` if this transcript is designated as MANE Plus Clinical. Absent or `false`  when not applicable. |
| `proteinExpression` | [Expression](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/expression.html#expression){ target=_blank rel=noopener } | 0..1 | The protein HGVS expression with syntax (typically `hgvs.p`) and `value`. Present  only when a protein-level expression exists for the nucleotide expression. |
| `molecularConsequence` | [Coding](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/coding.html#coding){ target=_blank rel=noopener }[] (unordered) | 0..m | Sequence Ontology terms describing the predicted molecular consequence.  Each entry includes `code` (SO identifier), `system`, `name` (SO term label),  and `iris` (identifiers.org link). |

