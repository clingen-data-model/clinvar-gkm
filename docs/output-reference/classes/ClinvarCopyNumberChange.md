# ClinvarCopyNumberChange

!!! warning "Draft"

    May change significantly in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A record of the copyNumberChange section: a VRS CopyNumberChange whose location is a pointer to a record of the location section. No name, description, aliases, extensions or expressions.

**JSON Schema:** [ClinvarCopyNumberChange](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarCopyNumberChange){ target=_blank }

Some ClinvarCopyNumberChange attributes are inherited from [CopyNumberChange](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/copy-number-change.html#copynumberchange){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 1..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`CopyNumberChange` | 1..1 | MUST be "CopyNumberChange" |
| `digest` | `string`<br>pattern `^[0-9A-Za-z_\-]{32}$` | 0..1 | A sha512t24u digest created using the VRS Computed Identifier algorithm. |
| `location` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/location/<id>` | 1..1 | The location of the copy number change, a '#/location/<id>' pointer into this bundle. |
| `copyChange` | `string`<br>one of `loss`, `gain` | 1..1 | The copy change: 'loss' or 'gain', the only values the pipeline writes. |

**Not used by ClinVar-GKM:** `name`, `description`, `aliases`, `extensions`, `expressions`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

