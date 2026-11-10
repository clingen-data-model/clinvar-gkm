# ClinvarModeOfInheritanceQualifier

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The mode of inheritance qualifier on a ClinVar SCV proposition: a MappableConcept named by the submitted mode of inheritance, with its HPO coding when the name matches an HPO term, and the submitted value in an ExtensionSubmittedModeOfInheritance. No id, description, aliases or mappings.

**JSON Schema:** [ClinvarModeOfInheritanceQualifier](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarModeOfInheritanceQualifier){ target=_blank }

Some ClinvarModeOfInheritanceQualifier attributes are inherited from [MappableConcept](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`MappableConcept` | 1..1 | MUST be "MappableConcept". |
| `name` | `string` | 0..1 | A primary name for the concept. |
| `extensions` | [ExtensionSubmittedModeOfInheritance](ClinvarModeOfInheritanceQualifier.md#extensionsubmittedmodeofinheritance)[] (unordered) | 1..m | The submitted mode of inheritance, in an ExtensionSubmittedModeOfInheritance. |
| `conceptType` | `string`<br>`modeOfInheritance` | 1..1 | Always 'modeOfInheritance'. |
| `primaryCoding` | [ClinvarCoding](ClinvarCoding.md) | 0..1 | The HPO term whose label matches the submitted mode of inheritance (case-insensitively). Absent when no HPO term matches. |

**Not used by ClinVar-GKM:** `id`, `description`, `aliases`, `mappings`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

## Extensions

These extensions are defined for `ClinvarModeOfInheritanceQualifier`.

### ExtensionSubmittedModeOfInheritance

The mode of inheritance the submitter gave for the SCV, as submitted.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`submittedModeOfInheritance` | 1..1 | Must be 'submittedModeOfInheritance'. |
| `value` | `string` | 1..1 | The submitted mode of inheritance. |

