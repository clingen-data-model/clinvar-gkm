# SubmittedConditionSet

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The value of a submittedConditionSet extension: the submitted condition set with the mapping of each of its conditions.

**JSON Schema:** [SubmittedConditionSet](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/SubmittedConditionSet){ target=_blank }

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `conditionSet` | `string` | 0..1 | The CURIE of the resolved condition set (e.g., "clinvar.traitset:123"; the key of the corresponding #/conditionSet/ bundle entry). |
| `condition` | `string` | 0..1 | Usually absent for multi-condition submissions; when present, the CURIE of a condition (e.g., "clinvar.trait:123"; the key of the corresponding #/condition/ bundle entry). |
| `multiple_condition_explanation` | `string` | 0..1 | ClinVar's explanation for how multiple conditions relate (maps to the ConditionSet membership operator: AND or OR). |
| `concepts` | [SubmittedConditionMapping](SubmittedConditionMapping.md)[] (ordered) | 0..m | Array of individual submitted condition mappings, one per condition in the set. Ordered by the condition's cat_id suffix. |

