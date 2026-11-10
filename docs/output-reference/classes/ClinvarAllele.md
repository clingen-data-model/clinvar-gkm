# ClinvarAllele

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A record of the allele section: a VRS Allele with its name and expressions, whose location is a pointer to a record of the location section. No description, aliases or extensions.

**JSON Schema:** [ClinvarAllele](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarAllele){ target=_blank }

Some ClinvarAllele attributes are inherited from [Allele](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/allele.html#allele){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `id` | `string` | 1..1 | The 'logical' identifier of the Entity in the system of record, e.g. a UUID.  This 'id' is unique within a given system, but may or may not be globally unique outside the system. It is used within a system to reference an object from another. |
| `type` | `string`<br>`Allele` | 1..1 | MUST be "Allele" |
| `name` | `string` | 0..1 | A primary name for the entity. |
| `digest` | `string`<br>pattern `^[0-9A-Za-z_\-]{32}$` | 0..1 | A sha512t24u digest created using the VRS Computed Identifier algorithm. |
| `expressions` | [ClinvarAlleleExpression](ClinvarAlleleExpression.md)[] (unordered) | 0..m | The allele's SPDI, HGVS and gnomAD expressions. |
| `location` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }<br>pointer to `#/location/<id>` | 1..1 | The location of the allele, a '#/location/<id>' pointer into this bundle. |
| `state` | [SequenceExpression](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/sequence-expression.html#sequenceexpression){ target=_blank rel=noopener } | 1..1 | The allele's state: a LiteralSequenceExpression or a ReferenceLengthExpression (whose length is an integer). No id, name, description, aliases or extensions. |

**Not used by ClinVar-GKM:** `description`, `aliases`, `extensions`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

