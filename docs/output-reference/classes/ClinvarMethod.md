# ClinvarMethod

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A Method as ClinVar-GKM writes it for a submission's assertion method: its method type, its name and its first citation; further citations are in an extension. No id, description or aliases.

**JSON Schema:** [ClinvarMethod](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarMethod){ target=_blank }

Some ClinvarMethod attributes are inherited from [Method](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/entities/information-entities/method.html#method){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`Method` | 1..1 | MUST be "Method". |
| `name` | `string` | 0..1 | A primary name for the entity. |
| `extensions` | [ExtensionAdditionalClinvarMethodCitations](ClinvarMethod.md#extensionadditionalclinvarmethodcitations)[] (unordered) | 0..m | The method's further citations, in an ExtensionAdditionalClinvarMethodCitations. |
| `methodType` | `string` | 0..1 | A specific type of method that a Method instance represents (e.g. 'Variant Interpretation Guideline', or 'Experimental Protocol'). |
| `reportedIn` | [ClinvarDocument](ClinvarDocument.md) | 0..1 | The method's first citation. |

**Not used by ClinVar-GKM:** `id`, `description`, `aliases`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

## Extensions

These extensions are defined for `ClinvarMethod`.

### ExtensionAdditionalClinvarMethodCitations

The citations of an assertion method after its first, in ClinVar's order (the first is the method's reportedIn).

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`additionalClinvarMethodCitations` | 0..1 | Must be 'additionalClinvarMethodCitations'. |
| `value` | [ClinvarDocument](ClinvarDocument.md)[] (ordered) | 0..m | The further citations, each a ClinvarDocument. |

