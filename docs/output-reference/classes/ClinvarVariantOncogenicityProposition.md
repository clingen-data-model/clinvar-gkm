# ClinvarVariantOncogenicityProposition

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A record of the propositionOncogenicity section: a VariantOncogenicityProposition whose subject is a variation pointer and whose object is a condition or condition set pointer. SCV propositions may carry a gene context qualifier. No name, description, aliases, extensions or allele origin qualifier.

**JSON Schema:** [ClinvarVariantOncogenicityProposition](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarVariantOncogenicityProposition){ target=_blank }

Some ClinvarVariantOncogenicityProposition attributes are inherited from [VariantOncogenicityProposition](https://va-spec.ga4gh.org/en/1.1.0/va-standard-profiles/base-profiles/proposition-profiles.html#variantoncogenicityproposition){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`VariantOncogenicityProposition` | 1..1 | MUST be "VariantOncogenicityProposition". |
| `subject` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/variation/<id>` | 1..1 | The variant, a '#/variation/<id>' pointer into this bundle. |
| `predicate` | `string`<br>`isOncogenicFor` | 1..1 | The relationship the Proposition describes between the subject variant and object tumor type. MUST be "isOncogenicFor". |
| `object` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/condition/<id>` or `#/conditionSet/<id>` | 1..1 | The tumor type, a '#/condition/<id>' or '#/conditionSet/<id>' pointer into this bundle. |
| `geneContextQualifier` | [ClinvarGeneContextQualifier](ClinvarGeneContextQualifier.md) | 0..1 | The variant's gene (SCV propositions only). |

**Not used by ClinVar-GKM:** `name`, `description`, `aliases`, `extensions`, `alleleOriginQualifier`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

