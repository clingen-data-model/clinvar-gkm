# ClinvarVariantClinicalSignificanceProposition

!!! warning "Draft"

    May change significantly in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A somatic clinical impact proposition of the propositionSomaticClinicalImpact section: a VariantClinicalSignificanceProposition whose subject is a variation pointer and whose object is a condition or condition set pointer. SCV propositions may carry a gene context qualifier. No name, description, aliases, extensions or allele origin qualifier.

**JSON Schema:** [ClinvarVariantClinicalSignificanceProposition](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarVariantClinicalSignificanceProposition){ target=_blank }

Some ClinvarVariantClinicalSignificanceProposition attributes are inherited from [VariantClinicalSignificanceProposition](https://va-spec.ga4gh.org/en/1.1.0/va-standard-profiles/base-profiles/proposition-profiles.html#variantclinicalsignificanceproposition){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`VariantClinicalSignificanceProposition` | 1..1 | MUST be "VariantClinicalSignificanceProposition". |
| `subject` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/variation/<id>` | 1..1 | The variant, a '#/variation/<id>' pointer into this bundle. |
| `predicate` | `string`<br>`hasClinicalSignificanceFor` | 1..1 | The predicate associating the subject variant to clinical significance for the object Condition. MUST be "hasClinicalSignificanceFor". |
| `object` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/condition/<id>` or `#/conditionSet/<id>` | 1..1 | The condition, a '#/condition/<id>' or '#/conditionSet/<id>' pointer into this bundle. |
| `geneContextQualifier` | [ClinvarGeneContextQualifier](ClinvarGeneContextQualifier.md) | 0..1 | The variant's gene (SCV propositions only). |

**Not used by ClinVar-GKM:** `name`, `description`, `aliases`, `extensions`, `alleleOriginQualifier`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

