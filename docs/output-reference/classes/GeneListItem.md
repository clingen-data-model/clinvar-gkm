# GeneListItem

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

One gene associated with a ClinVar variation: a reference to the gene's MappableConcept in the bundle's `gene` section, plus ClinVar's `relationship_type` and `source`.

**JSON Schema:** [GeneListItem](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/GeneListItem){ target=_blank }

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `gene` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener } | 1..1 | Reference to the gene MappableConcept in the bundle's `gene` section (e.g. `#/gene/ncbigene:672`). |
| `relationship_type` | `string` | 1..1 | The relationship between the variation and the gene as reported by ClinVar (e.g.,  `within single gene`, `genes overlapped by variant`). |
| `source` | `string` | 1..1 | The source of the gene association: `submitted` (asserted by the submitter) or `calculated` (computed by ClinVar). |

