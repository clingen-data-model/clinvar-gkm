# ClinvarVariantTherapeuticResponseProposition

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The target proposition of a therapeutic somatic clinical impact SCV's evidence line, in the propositionSomaticClinicalImpact section: a VariantTherapeuticResponseProposition whose subject is a variation pointer, whose object is a therapy or therapy group pointer and whose condition qualifier is a condition or condition set pointer, with the SCV's gene context qualifier. No name, description, aliases, extensions or allele origin qualifier.

**JSON Schema:** [ClinvarVariantTherapeuticResponseProposition](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarVariantTherapeuticResponseProposition){ target=_blank }

Some ClinvarVariantTherapeuticResponseProposition attributes are inherited from [VariantTherapeuticResponseProposition](https://va-spec.ga4gh.org/en/1.1.0/va-standard-profiles/base-profiles/proposition-profiles.html#varianttherapeuticresponseproposition){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`VariantTherapeuticResponseProposition` | 1..1 | MUST be "VariantTherapeuticResponseProposition". |
| `subject` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/variation/<id>` | 1..1 | The variant, a '#/variation/<id>' pointer into this bundle. |
| `predicate` | `string`<br>one of `predictsSensitivityTo`, `predictsResistanceTo` | 1..1 | The relationship the Proposition describes between the subject variant and object therapeutic. MUST be one of "predictsSensitivityTo" or "predictsResistanceTo". |
| `object` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/therapy/<id>` or `#/therapyGroup/<id>` | 1..1 | The drug, a '#/therapy/<id>' pointer, or a combination of drugs, a '#/therapyGroup/<id>' pointer into this bundle. |
| `geneContextQualifier` | [ClinvarGeneContextQualifier](ClinvarGeneContextQualifier.md) | 0..1 | The variant's gene. |
| `conditionQualifier` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/condition/<id>` or `#/conditionSet/<id>` | 1..1 | The disease context, a '#/condition/<id>' or '#/conditionSet/<id>' pointer into this bundle. |

**Not used by ClinVar-GKM:** `name`, `description`, `aliases`, `extensions`, `alleleOriginQualifier`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

