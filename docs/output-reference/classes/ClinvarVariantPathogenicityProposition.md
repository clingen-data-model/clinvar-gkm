# ClinvarVariantPathogenicityProposition

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A record of the propositionPathogenicity section: a VariantPathogenicityProposition whose subject is a variation pointer and whose object is a condition or condition set pointer. SCV propositions may carry gene context, mode of inheritance and penetrance qualifiers; VCV and RCV propositions carry none. No name, description, aliases, extensions or allele origin qualifier.

**JSON Schema:** [ClinvarVariantPathogenicityProposition](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarVariantPathogenicityProposition){ target=_blank }

Some ClinvarVariantPathogenicityProposition attributes are inherited from [VariantPathogenicityProposition](https://va-spec.ga4gh.org/en/1.1.0/va-standard-profiles/base-profiles/proposition-profiles.html#variantpathogenicityproposition){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 1..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`VariantPathogenicityProposition` | 1..1 | Must be "VariantPathogenicityProposition" |
| `subject` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/variation/<id>` | 1..1 | The variant, a '#/variation/<id>' pointer into this bundle. |
| `predicate` | `string`<br>`isCausalFor` | 1..1 | The relationship the Proposition describes between the subject variant and object condition. MUST be "isCausalFor". |
| `object` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/condition/<id>` or `#/conditionSet/<id>` | 1..1 | The condition, a '#/condition/<id>' or '#/conditionSet/<id>' pointer into this bundle. |
| `geneContextQualifier` | [ClinvarGeneContextQualifier](ClinvarGeneContextQualifier.md) | 0..1 | The variant's gene (SCV propositions only). |
| `penetranceQualifier` | [ClinvarPenetranceQualifier](ClinvarPenetranceQualifier.md) | 0..1 | The penetrance implied by a low-penetrance or risk-allele classification (SCV propositions only). |
| `modeOfInheritanceQualifier` | [ClinvarModeOfInheritanceQualifier](ClinvarModeOfInheritanceQualifier.md) | 0..1 | The submitted mode of inheritance (SCV propositions only). |

**Not used by ClinVar-GKM:** `name`, `description`, `aliases`, `extensions`, `alleleOriginQualifier`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

