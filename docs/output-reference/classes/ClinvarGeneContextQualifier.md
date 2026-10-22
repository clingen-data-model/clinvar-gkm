# ClinvarGeneContextQualifier

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The gene context qualifier on a ClinVar SCV proposition: a gene MappableConcept. When it carries a 'geneContextSource' extension, that extension's value MUST be one of the four values defined by ExtensionGeneContextSource. Other extensions (e.g. 'submittedGeneSymbols') are not constrained here.

**JSON Schema:** [ClinvarGeneContextQualifier](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarGeneContextQualifier){ target=_blank }

Some ClinvarGeneContextQualifier attributes are inherited from [MappableConcept](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string` | 0..1 | MUST be "MappableConcept". |
| `name` | `string` | 0..1 | A primary name for the concept. |
| `description` | `string` | 0..1 | A free-text description of the Entity. |
| `aliases` | `string`[] (unordered) | 0..m | Alternative name(s) for the Entity. |
| `extensions` | [Extension](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/extension.html#extension){ target=_blank rel=noopener }[] (unordered) | 0..m | Extensions on the qualifier. An item named 'geneContextSource' must match ExtensionGeneContextSource. |
| `conceptType` | `string` | 0..1 | A term indicating the type of concept being represented by the MappableConcept. |
| `primaryCoding` | [Coding](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/coding.html#coding){ target=_blank rel=noopener } | 0..1 | A primary coding for the concept. |
| `mappings` | [ConceptMapping](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/concept-mapping.html#conceptmapping){ target=_blank rel=noopener }[] (unordered) | 0..m | A list of mappings to concepts in terminologies or code systems. Each mapping should include a coding and a relation. |

## Extensions

These extensions are defined for `ClinvarGeneContextQualifier`.

### ExtensionGeneContextSource

Where the gene on a SCV proposition's geneContextQualifier came from, compared with the gene symbols the submitter gave.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'geneContextSource'. |
| `value` | `string` | 0..1 | submittedSymbolMatches: the submitter's symbols include the qualifier's symbol. submittedSymbolDiffers: the submitter gave symbols, but none equals the qualifier's symbol (most are previous symbols of the same gene). inferredFromVariant: the submitter gave no symbols. submittedNotNormalized: the variant has no single representative gene, so the qualifier is a placeholder named with the submitter's symbol(s). Symbols are compared trimmed and case-insensitively. |

