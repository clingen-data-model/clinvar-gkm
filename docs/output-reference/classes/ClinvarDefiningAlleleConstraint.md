# ClinvarDefiningAlleleConstraint

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The constraint of a ClinvarCanonicalAllele: a DefiningAlleleConstraint whose allele is a pointer to a record of the allele section, related by `liftover_to` and `transcribed_to`.

**JSON Schema:** [ClinvarDefiningAlleleConstraint](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarDefiningAlleleConstraint){ target=_blank }

Some ClinvarDefiningAlleleConstraint attributes are inherited from [DefiningAlleleConstraint](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/defining-allele-constraint.html#definingalleleconstraint){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`DefiningAlleleConstraint` | 1..1 | MUST be "DefiningAlleleConstraint" |
| `allele` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/allele/<id>` | 1..1 | The defining allele, a '#/allele/<id>' pointer into this bundle. |
| `relations` | [ClinvarLiftoverToRelation](ClinvarLiftoverToRelation.md) \| [ClinvarTranscribedToRelation](ClinvarTranscribedToRelation.md)[] (unordered) | 0..m | The `liftover_to` and `transcribed_to` relations. |

