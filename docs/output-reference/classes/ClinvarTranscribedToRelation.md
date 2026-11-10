# ClinvarTranscribedToRelation

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The `transcribed_to` relation of a ClinVar defining allele constraint: a MappableConcept with only its type and primary coding (code `transcribed_to`, system `http://www.sequenceontology.org/` and the term's IRI).

**JSON Schema:** [ClinvarTranscribedToRelation](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarTranscribedToRelation){ target=_blank }

Some ClinvarTranscribedToRelation attributes are inherited from [MappableConcept](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/mappable-concept.html#mappableconcept){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`MappableConcept` | 1..1 | MUST be "MappableConcept". |
| `primaryCoding` | [Coding](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/coding.html#coding){ target=_blank rel=noopener }<br>`code`: `transcribed_to`; `system`: `http://www.sequenceontology.org/`; `iris`: `http://www.sequenceontology.org/browser/current_release/term/transcribed_to` | 1..1 | The relation's code, system and IRI. |

**Not used by ClinVar-GKM:** `id`, `name`, `description`, `aliases`, `extensions`, `conceptType`, `mappings`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

