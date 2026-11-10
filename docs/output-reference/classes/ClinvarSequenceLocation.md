# ClinvarSequenceLocation

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A record of the location section: a VRS SequenceLocation whose sequence reference is a pointer to a record of the sequenceReference section. No name, description, aliases, extensions or sequence.

**JSON Schema:** [ClinvarSequenceLocation](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarSequenceLocation){ target=_blank }

Some ClinvarSequenceLocation attributes are inherited from [SequenceLocation](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/sequence-location.html#sequencelocation){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 0..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`SequenceLocation` | 1..1 | MUST be "SequenceLocation" |
| `digest` | `string`<br>pattern `^[0-9A-Za-z_\-]{32}$` | 0..1 | A sha512t24u digest created using the VRS Computed Identifier algorithm. |
| `sequenceReference` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/sequenceReference/<id>` | 0..1 | The reference sequence for the location, a '#/sequenceReference/<id>' pointer into this bundle. |
| `start` | `integer` \| [Range](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/range.html#range){ target=_blank rel=noopener } | 0..1 | The start coordinate or range of the SequenceLocation. The minimum value of this coordinate or range is 0. For locations on linear sequences, this MUST represent a coordinate or range less than or equal to the value of `end`. For circular sequences, `start` is greater than `end` when the location spans the sequence 0 coordinate. |
| `end` | `integer` \| [Range](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/range.html#range){ target=_blank rel=noopener } | 0..1 | The end coordinate or range of the SequenceLocation. The minimum value of this coordinate or range is 0. For locations on linear sequences, this MUST represent a coordinate or range greater than or equal to the value of `start`. For circular sequences, `end` is less than `start` when the location spans the sequence 0 coordinate. |

**Not used by ClinVar-GKM:** `name`, `description`, `aliases`, `extensions`, `sequence`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

