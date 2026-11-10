# SubmittedCondition

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

The value of a submittedCondition extension: the submitted condition's mapping, with the condition (or, rarely, the condition set) it resolved to.

**JSON Schema:** [SubmittedCondition](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/SubmittedCondition){ target=_blank }

Some SubmittedCondition attributes are inherited from [SubmittedConditionMappingProperties](SubmittedConditionMappingProperties.md).

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The submitted trait category assignment identifier (cat_id). |
| `name` | `string` | 0..1 | The condition name as submitted by the submitter. |
| `type` | `string` | 0..1 | The condition type as submitted (e.g., "Disease", "Finding"). |
| `medgen_id` | `string` | 0..1 | The MedGen ID submitted by the submitter, if provided. |
| `xrefs` | [ClinvarTermCoding](ClinvarTermCoding.md)[] (unordered) | 0..m | Cross-references submitted by the submitter for this condition. |
| `original_medgen_match` | `object` | 0..1 | The original MedGen match when the submitted MedGen ID was remapped to a different canonical MedGen concept. Contains id and name of the original match. Null when no remapping occurred. |
| `direct_match` | `string` | 0..1 | The CURIE of the directly matched condition (e.g., "clinvar.trait:123"; the key of the corresponding #/condition/ bundle entry). Present only when the direct match differs from the normalized match. |
| `normalized_match` | `string` | 0..1 | The CURIE of the final normalized condition (e.g., "clinvar.trait:456"; the key of the corresponding #/condition/ bundle entry). |
| `normalized_resolution` | `string`<br>one of `tm reftype xref medgen`, `tm reftype preferred name`, `tm reftype xref omim`, `tm reftype xref mondo`, `tm reftype xref HP`, `tm reftype xref omim.ps`, `tm reftype xref orpha`, `tm reftype xref mesh`, `random trait assignment` | 0..1 | How the condition normalization was resolved: by the trait mapping of one of the submitted references ("tm reftype xref medgen", "tm reftype preferred name", ...), or, when none matched, by "random trait assignment". |
| `mapping` | `object`<br>`type`: one of `Name`, `XRef` | 0..1 | The mapping details used to resolve the submitted condition to a ClinVar trait, including mapping type, reference field, and value. |
| `condition` | `string` | 0..1 | The CURIE of the resolved condition (e.g., "clinvar.trait:123"; the key of the corresponding #/condition/ bundle entry). |
| `conditionSet` | `string` | 0..1 | Usually absent for single-condition submissions; when a single-trait submission maps to a multi-trait RCV it holds the CURIE of that condition set (e.g., clinvar.traitset:123). |

