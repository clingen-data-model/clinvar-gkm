# SubmittedConditionMapping

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The submitter's original condition details and how they were mapped to a ClinVar canonical condition. Includes the submitted name, type, MedGen ID, cross-references, and the normalization path (direct match, original medgen match, normalized match, resolution type, mapping details).

**JSON Schema:** [SubmittedConditionMapping](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/SubmittedConditionMapping){ target=_blank }

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The submitted trait category assignment identifier (cat_id). |
| `name` | `string` | 0..1 | The condition name as submitted by the submitter. |
| `type` | `string` | 0..1 | The condition type as submitted (e.g., "Disease", "Finding"). |
| `medgen_id` | `string` | 0..1 | The MedGen ID submitted by the submitter, if provided. |
| `xrefs` | [Coding](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/elements/coding.html#coding){ target=_blank rel=noopener }[] (unordered) | 0..m | Cross-references submitted by the submitter for this condition. |
| `original_medgen_match` | `object` | 0..1 | The original MedGen match when the submitted MedGen ID was remapped to a different canonical MedGen concept. Contains id and name of the original match. Null when no remapping occurred. |
| `direct_match` | `string` | 0..1 | The CURIE of the directly matched condition (e.g., "clinvar.trait:123"; the key of the corresponding #/condition/ bundle entry). Present only when the direct match differs from the normalized match. |
| `normalized_match` | `string` | 0..1 | The CURIE of the final normalized condition (e.g., "clinvar.trait:456"; the key of the corresponding #/condition/ bundle entry). |
| `normalized_resolution` | `string` | 0..1 | How the condition normalization was resolved (e.g., "rcv-tm medgen id", "rcv-tm preferred name", "random trait assignment"). |
| `mapping` | `object` | 0..1 | The mapping details used to resolve the submitted condition to a ClinVar trait, including mapping type, reference field, and value. |

