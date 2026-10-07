# ClinvarCategoricalVariant

!!! note "Trial Use"

    May change in future releases. See the [GKM Maturity Model](https://vrs.ga4gh.org/en/2.0/appendices/maturity_model.html){ target=_blank rel=noopener }.

The Clinvar specific representations of categorical variants.

**JSON Schema:** [ClinvarCategoricalVariant](https://github.com/clingen-data-model/clinvar-gkm/blob/main/schema/clinvar-gkm/json/ClinvarCategoricalVariant){ target=_blank }

**One of:**

- [ClinvarCanonicalAllele](ClinvarCanonicalAllele.md)
- [ClinvarCategoricalCnvChange](ClinvarCategoricalCnvChange.md)
- [ClinvarCategoricalCnvCount](ClinvarCategoricalCnvCount.md)
- [ClinvarNonConstrainedVariant](ClinvarNonConstrainedVariant.md)

## Extensions

These extensions are defined for `ClinvarCategoricalVariant`.

### ExtensionAssembly

An extension item for the assembly associated with a Clinvar variant.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'assembly'. |
| `value` | `string` | 0..1 | The assembly of the variant as provided by Clinvar. It must be one of the following: 'GRCh37', 'GRCh38', or 'NCBI36'. |

### ExtensionCategoricalVariationType

The Cat-VRS category assigned to this variation: `CanonicalAllele`, `CategoricalCnvChange`,  `CategoricalCnvCount`, or `Undefined`. Determines which constraint types are generated.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'categoricalVariationType'. |
| `value` | `string` | 0..1 | The type of categorical variant. It must be one of the following: `CanonicalAllele`, `CategoricalCnvChange`, `CategoricalCnvCount`, or `Undefined`. |

### ExtensionClinvarCytogeneticLocation

The cytogenetic band location of the variation (e.g., 1p36.22, 17q21.31). Present when  ClinVar provides a cytogenetic location.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'clinvarCytogeneticLocation'. |
| `value` | `string` | 0..1 | The cytogenetic location of the variant as provided by Clinvar. |

### ExtensionClinvarGeneList

Gene associations for this variation from ClinVar, including Entrez gene IDs, HGNC IDs,  gene symbols, relationship types, and identifier IRIs.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'clinvarGeneList'. |
| `value` | [GeneListItem](GeneListItem.md)[] (unordered) | 0..m | Clinvar's data structure for representing genes associated with a clinvar variant.           |

### ExtensionClinvarHgvsList

Complete list of HGVS expressions from ClinVar for a variant, including nucleotide  and protein expressions, molecular consequences (SO terms), and MANE transcript  designations.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'clinvarHgvsList'. |
| `value` | [HgvsListItem](HgvsListItem.md)[] (unordered) | 0..m | Clinvar's data structure for representing the HGVS expressions, mane select/plus settings and  molecular consequence for dervied genomic/transcript sequence alignmnents and protein sequence projections originating from the definining allele or location for CNVs. |

### ExtensionClinvarSubclassType

The variation subclass as reported by ClinVar (e.g., SimpleAllele, Haplotype,  CompoundHeterozygote). Present when ClinVar provides a subclass type.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'clinvarSubclassType'. |
| `value` | `string` | 0..1 | The subclass type of the variant as provided by Clinvar. It must be one of the following: 'Genotype', 'Haplotype', or 'SimpleAllele'. |

### ExtensionClinvarVariationType

The variation type as reported by ClinVar (e.g., Deletion, single nucleotide variant,  Duplication, Indel). Present when ClinVar provides a variation type.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'clinvarVariationType'. |
| `value` | `string` | 0..1 | The type of variant as provided by Clinvar. It must be one of the following: 'Complex', 'CompoundHeterozygote', 'copy number gain', 'copy number loss', 'Deletion', 'Diplotype', 'Distinct chromosomes', 'Duplication', 'fusion', 'Haplotype, single variant', 'Haplotype', 'Indel', 'Insertion', 'Inversion', 'Microsatellite', 'Phase unknown', 'protein only', 'single nucleotide variant', 'Tandem duplication', 'Translocation', or 'Variation'. |

### ExtensionDefiningVrsVariationType

The VRS class assigned during variation identity processing (e.g., `Allele`, `CopyNumberChange`,  `CopyNumberCount`, `Not Available`). Reflects the upstream classification used to route the  variant through VRS processing.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'definingVrsVariationType'. |
| `value` | `string` | 0..1 | The type of categorical variant. It must be one of the following: `Allele`,  `CopyNumberChange`, `CopyNumberCount`, `Haplotype`, `Unknown`, or `Not Available`. |

### ExtensionVrsPreProcessingIssue

Issues detected during VRS pre-processing of the variation's input expressions. Present only  when issues exist. May contain multiple issues separated by newlines

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'vrsPreProcessingIssue'. |
| `value` | `string` | 0..1 | The VRS processing errors associated with the Clinvar variant. |

### ExtensionsVrsProcessingException

Errors returned by the external VRS Python processing service. Present only when  errors occurred during VRS resolution.

| Field | Type | Limits | Description |
| --- | --- | --- | --- |
| `name` | `string` | 0..1 | Must be 'vrsProcessingException'. |
| `value` | `string` | 0..1 | The VRS processing errors associated with the Clinvar variant. |

