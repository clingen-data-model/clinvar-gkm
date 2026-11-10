# ClinvarCopyNumberCount

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A record of the copyNumberCount section: a VRS CopyNumberCount with an integer copy count, whose location is a pointer to a record of the location section. No name, description, aliases, extensions or expressions.

**JSON Schema:** [ClinvarCopyNumberCount](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarCopyNumberCount){ target=_blank }

Some ClinvarCopyNumberCount attributes are inherited from [CopyNumberCount](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/copy-number-count.html#copynumbercount){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 1..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`CopyNumberCount` | 1..1 | MUST be "CopyNumberCount" |
| `digest` | `string`<br>pattern `^[0-9A-Za-z_\-]{32}$` | 0..1 | A sha512t24u digest created using the VRS Computed Identifier algorithm. |
| `location` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/location/<id>` | 1..1 | The location of the copy number count, a '#/location/<id>' pointer into this bundle. |
| `copies` | `integer` | 1..1 | The integral number of copies. |

**Not used by ClinVar-GKM:** `name`, `description`, `aliases`, `extensions`, `expressions`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

