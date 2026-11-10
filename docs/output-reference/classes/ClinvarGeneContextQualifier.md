# ClinvarGeneContextQualifier

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The gene context qualifier on a ClinVar SCV proposition: a gene MappableConcept with the codings of a ClinvarGene, and extensions saying where its gene came from (ExtensionGeneContextSource) and which gene symbols the submitter gave (ExtensionSubmittedGeneSymbols). No id, description or aliases.

**JSON Schema:** [ClinvarGeneContextQualifier](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarGeneContextQualifier){ target=_blank }

Some ClinvarGeneContextQualifier attributes are inherited from [MappableConcept](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`MappableConcept` | 1..1 | MUST be "MappableConcept". |
| `name` | `string` | 1..1 | A primary name for the concept. |
| `extensions` | [ExtensionGeneContextSource](ClinvarGeneContextQualifier.md#extensiongenecontextsource) \| [ExtensionSubmittedGeneSymbols](ClinvarGeneContextQualifier.md#extensionsubmittedgenesymbols)[] (unordered) | 1..m | The qualifier's extensions, each an ExtensionGeneContextSource or an ExtensionSubmittedGeneSymbols. |
| `conceptType` | `string`<br>`gene` | 1..1 | Always 'gene'. |
| `primaryCoding` | [ClinvarCoding](ClinvarCoding.md) | 0..1 | The gene's NCBI Gene coding. Absent on a placeholder qualifier (geneContextSource 'submittedNotNormalized'). |
| `mappings` | [ClinvarConceptMapping](ClinvarConceptMapping.md)[] (unordered) | 0..m | Mappings of the gene to other gene codes (its HGNC coding). Absent on a placeholder qualifier. |

**Not used by ClinVar-GKM:** `id`, `description`, `aliases`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

## Extensions

These extensions are defined for `ClinvarGeneContextQualifier`.

### ExtensionGeneContextSource

Where the gene on a SCV proposition's geneContextQualifier came from, compared with the gene symbols the submitter gave.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`geneContextSource` | 1..1 | Must be 'geneContextSource'. |
| `value` | `string`<br>one of `submittedSymbolMatches`, `submittedSymbolDiffers`, `inferredFromVariant`, `submittedNotNormalized` | 1..1 | submittedSymbolMatches: the submitter's symbols include the qualifier's symbol. submittedSymbolDiffers: the submitter gave symbols, but none equals the qualifier's symbol (most are previous symbols of the same gene). inferredFromVariant: the submitter gave no symbols. submittedNotNormalized: the variant has no single representative gene, so the qualifier is a placeholder named with the submitter's symbol(s). Symbols are compared trimmed and case-insensitively. |

### ExtensionSubmittedGeneSymbols

The gene symbols the submitter gave for the SCV, as submitted.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`submittedGeneSymbols` | 1..1 | Must be 'submittedGeneSymbols'. |
| `value` | `string`[] (ordered) | 1..m | The submitted gene symbols. |

