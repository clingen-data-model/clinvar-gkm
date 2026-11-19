# ClinvarCopyChangeConstraint

!!! warning "Draft"

    May change significantly in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The copy change constraint of a ClinvarCategoricalCnvChange: a CopyChangeConstraint whose copy change is 'loss' or 'gain'.

**JSON Schema:** [ClinvarCopyChangeConstraint](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarCopyChangeConstraint){ target=_blank }

Some ClinvarCopyChangeConstraint attributes are inherited from [CopyChangeConstraint](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/copy-change-constraint.html#copychangeconstraint){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`CopyChangeConstraint` | 1..1 | MUST be "CopyChangeConstraint" |
| `copyChange` | `string`<br>one of `loss`, `gain` | 1..1 | The copy change: 'loss' or 'gain', the only values the pipeline writes. |

