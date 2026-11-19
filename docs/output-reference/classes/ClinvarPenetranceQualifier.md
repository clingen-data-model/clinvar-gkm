# ClinvarPenetranceQualifier

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The penetrance qualifier on a ClinVar SCV proposition, derived from a low-penetrance or risk-allele classification: a MappableConcept named 'low' or 'risk', with the submitted classification in an ExtensionSubmittedClassification. No id, description, aliases, primary coding or mappings.

**JSON Schema:** [ClinvarPenetranceQualifier](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarPenetranceQualifier){ target=_blank }

Some ClinvarPenetranceQualifier attributes are inherited from [MappableConcept](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`MappableConcept` | 1..1 | MUST be "MappableConcept". |
| `name` | `string`<br>one of `low`, `risk` | 1..1 | 'low' for a pathogenic or likely pathogenic, low penetrance classification; 'risk' for an established, likely or uncertain risk allele classification. |
| `extensions` | [ExtensionSubmittedClassification](ClinvarPenetranceQualifier.md#extensionsubmittedclassification)[] (unordered) | 1..m | The submitted classification, in an ExtensionSubmittedClassification. |
| `conceptType` | `string`<br>`penetrance` | 1..1 | Always 'penetrance'. |

**Not used by ClinVar-GKM:** `id`, `description`, `aliases`, `primaryCoding`, `mappings`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

## Extensions

These extensions are defined for `ClinvarPenetranceQualifier`.

### ExtensionSubmittedClassification

The SCV's submitted classification that the penetrance qualifier was derived from.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`submittedClassification` | 1..1 | Must be 'submittedClassification'. |
| `value` | `string` | 1..1 | The submitted classification (e.g. 'Likely risk allele'). |

