# ClinvarDefiningLocationConstraint

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The location constraint of a ClinVar copy number variant: a DefiningLocationConstraint whose location is a pointer to a record of the location section, matched `is_within` and related by `liftover_to`.

**JSON Schema:** [ClinvarDefiningLocationConstraint](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarDefiningLocationConstraint){ target=_blank }

Some ClinvarDefiningLocationConstraint attributes are inherited from [DefiningLocationConstraint](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/defining-location-constraint.html#defininglocationconstraint){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`DefiningLocationConstraint` | 1..1 | MUST be "DefiningLocationConstraint" |
| `location` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/location/<id>` | 1..1 | The defining location, a '#/location/<id>' pointer into this bundle. |
| `relations` | [ClinvarLiftoverToRelation](ClinvarLiftoverToRelation.md)[] (unordered) | 1..m | The `liftover_to` relation. |
| `matchCharacteristic` | [ClinvarIsWithinMatch](ClinvarIsWithinMatch.md) | 1..1 | The `is_within` match characteristic. |

