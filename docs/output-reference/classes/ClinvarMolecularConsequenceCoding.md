# ClinvarMolecularConsequenceCoding

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A Sequence Ontology molecular consequence of a HgvsListItem: the SO code, its label as the name, the SO system and one identifiers.org IRI.

**JSON Schema:** [ClinvarMolecularConsequenceCoding](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarMolecularConsequenceCoding){ target=_blank }

Some ClinvarMolecularConsequenceCoding attributes are inherited from [ClinvarCoding](ClinvarCoding.md).

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>one of `missense_variant`, `intron_variant`, `inframe_indel`, `inframe_deletion`, `no_sequence_alteration`, `inframe_insertion`, `stop_gained`, `5_prime_UTR_variant`, `stop_lost`, `genic_upstream_transcript_variant`, `splice_acceptor_variant`, `non_coding_transcript_variant`, `genic_downstream_transcript_variant`, `splice_donor_variant`, `3_prime_UTR_variant`, `synonymous_variant`, `frameshift_variant`, `initiator_codon_variant` | 0..1 | The SO term label. |
| `system` | `string`<br>`http://www.sequenceontology.org/` | 1..1 | Must be 'http://www.sequenceontology.org/'. |
| `code` | `string`<br>one of `SO:0001583`, `SO:0001627`, `SO:0001820`, `SO:0001822`, `SO:0002073`, `SO:0001821`, `SO:0001587`, `SO:0001623`, `SO:0001578`, `SO:0002153`, `SO:0001574`, `SO:0001619`, `SO:0002152`, `SO:0001575`, `SO:0001624`, `SO:0001819`, `SO:0001589`, `SO:0001582` | 1..1 | The SO identifier. |
| `iris` | [iriReference](https://va-spec.ga4gh.org/en/1.1.0/core-information-model/data-types.html#irireference){ target=_blank rel=noopener }[] (unordered)<br>pattern `^https://identifiers\.org/SO:[0-9]{7}$` | 0..m | The identifiers.org IRI of the SO term. |

**Not used by ClinVar-GKM:** `id`, `extensions`, `systemVersion`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

