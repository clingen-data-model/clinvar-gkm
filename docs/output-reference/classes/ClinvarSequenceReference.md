# ClinvarSequenceReference

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.1/appendices/maturity_model.html){ target=_blank rel=noopener }.

A record of the sequenceReference section: a VRS SequenceReference for an NCBI RefSeq sequence, with its accession as the name, its molecule type and residue alphabet, and its assembly in an extension when the sequence belongs to one. No id, description, aliases, sequence or circular flag.

**JSON Schema:** [ClinvarSequenceReference](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarSequenceReference){ target=_blank }

Some ClinvarSequenceReference attributes are inherited from [SequenceReference](https://va-spec.ga4gh.org/en/1.1.0/appendices/imported-models/sequence-reference.html#sequencereference){ target=_blank rel=noopener }.

## Information Model

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `type` | `string`<br>`SequenceReference` | 1..1 | MUST be "SequenceReference" |
| `name` | `string` | 0..1 | A primary name for the entity. |
| `extensions` | [ExtensionAssembly](ClinvarSequenceReference.md#extensionassembly)[] (unordered) | 0..m | The assembly of the sequence, when it belongs to one. |
| `refgetAccession` | `string`<br>pattern `^SQ.[0-9A-Za-z_\-]{32}$` | 1..1 | A `GA4GH RefGet <http://samtools.github.io/hts-specs/refget.html>`_ identifier for the referenced sequence, using the sha512t24u digest. |
| `residueAlphabet` | `string`<br>one of `aa`, `na` | 0..1 | The interpretation of the character codes referred to by the refget accession, where "aa" specifies an amino acid character set, and "na" specifies a nucleic acid character set. |
| `moleculeType` | `string`<br>one of `genomic`, `RNA`, `mRNA`, `protein` | 0..1 | Molecule types as `defined by RefSeq <https://www.ncbi.nlm.nih.gov/books/NBK21091/>`_ (see Table 1). MUST be one of "genomic", "RNA", "mRNA", or "protein". |

**Not used by ClinVar-GKM:** `id`, `description`, `aliases`, `sequence`, `circular`. The GA4GH base class defines these properties, but this profile forbids them (`false`), so they never appear in ClinVar-GKM bundles.

## Extensions

These extensions are defined for `ClinvarSequenceReference`.

### ExtensionAssembly

An extension item for the assembly of a genomic sequence reference.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string`<br>`assembly` | 1..1 | Must be 'assembly'. |
| `value` | `string`<br>one of `GRCh37`, `GRCh38`, `NCBI36` | 1..1 | The assembly of the sequence as provided by Clinvar. It must be one of the following: 'GRCh37', 'GRCh38', or 'NCBI36'. |

