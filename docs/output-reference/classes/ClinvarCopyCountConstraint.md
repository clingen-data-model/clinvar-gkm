# ClinvarCopyCountConstraint

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The copy count constraint of a ClinvarCategoricalCnvCount: a CopyCountConstraint with an integer copy count.

**JSON Schema:** [ClinvarCopyCountConstraint](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarCopyCountConstraint){ target=_blank }

Some ClinvarCopyCountConstraint attributes are inherited from [CopyCountConstraint](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/copy-count-constraint.html#copycountconstraint){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`CopyCountConstraint` | 1..1 | MUST be "CopyCountConstraint" |
| `copies` | `integer` | 1..1 | The integral number of copies. |

