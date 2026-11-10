# ClinvarVariantPrognosticProposition

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The target proposition of a prognostic somatic clinical impact SCV's evidence line, in the propositionSomaticClinicalImpact section: a VariantPrognosticProposition whose subject is a variation pointer and whose object is a condition or condition set pointer, with the SCV's gene context qualifier. No name, description, aliases, extensions or allele origin qualifier.

**JSON Schema:** [ClinvarVariantPrognosticProposition](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarVariantPrognosticProposition){ target=_blank }

Some ClinvarVariantPrognosticProposition attributes are inherited from [VariantPrognosticProposition](https://va-spec.ga4gh.org/en/1.1.0/va-standard-profiles/base-profiles/proposition-profiles.html#variantprognosticproposition){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`VariantPrognosticProposition` | 1..1 | MUST be "VariantPrognosticProposition". |
| `subject` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/variation/<id>` | 1..1 | The variant, a '#/variation/<id>' pointer into this bundle. |
| `predicate` | `string`<br>one of `associatedWithBetterOutcomeFor`, `associatedWithWorseOutcomeFor` | 1..1 | The relationship the Proposition describes between the subject variant and object Condition. MUST be one of "associatedWithBetterOutcomeFor" or "associatedWithWorseOutcomeFor". |
| `object` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/condition/<id>` or `#/conditionSet/<id>` | 1..1 | The disease, a '#/condition/<id>' or '#/conditionSet/<id>' pointer into this bundle. |
| `geneContextQualifier` | [ClinvarGeneContextQualifier](ClinvarGeneContextQualifier.md) | 0..1 | The variant's gene. |

**Not used by ClinVar-GKM:** `name`, `description`, `aliases`, `extensions`, `alleleOriginQualifier`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

