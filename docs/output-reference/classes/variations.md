# Variations

ClinVar variations are represented using the GA4GH [Cat-VRS](https://cat-vrs.readthedocs.io/) (Categorical Variation) specification. Each variation maps to one of four ClinVar profiles of the Cat-VRS types, depending on how ClinVar resolves the variant's genomic identity.

The [ClinvarCategoricalVariant](ClinvarCategoricalVariant.md) union type encompasses all four. Its branches are mutually exclusive, so a `variation` record validates against exactly one of them:

| Cat-VRS Type | ClinVar Profile | Members | Constraints |
| --- | --- | --- | --- |
| CanonicalAllele | [ClinvarCanonicalAllele](ClinvarCanonicalAllele.md) | `#/allele/` | [ClinvarDefiningAlleleConstraint](ClinvarDefiningAlleleConstraint.md) |
| CategoricalCnv | [ClinvarCategoricalCnvChange](ClinvarCategoricalCnvChange.md) | `#/copyNumberChange/` | [ClinvarDefiningLocationConstraint](ClinvarDefiningLocationConstraint.md) and [ClinvarCopyChangeConstraint](ClinvarCopyChangeConstraint.md) (`loss` or `gain`) |
| CategoricalCnv | [ClinvarCategoricalCnvCount](ClinvarCategoricalCnvCount.md) | `#/copyNumberCount/` | [ClinvarDefiningLocationConstraint](ClinvarDefiningLocationConstraint.md) and [ClinvarCopyCountConstraint](ClinvarCopyCountConstraint.md) (an integer copy count) |
| CategoricalVariant | [ClinvarNonConstrainedVariant](ClinvarNonConstrainedVariant.md) | none | none |

- **ClinvarCanonicalAllele** — the vast majority of ClinVar variations, defined by a genomic allele mapped from the submitted variant attributes
- **ClinvarCategoricalCnvChange** and **ClinvarCategoricalCnvCount** — copy number variants with a qualitative change or an absolute copy count
- **ClinvarNonConstrainedVariant** — haplotypes, genotypes, and complex variants that cannot be mapped to a specific VRS allele or location; it carries no `members` or `constraints`

Variations carry `mappings` of type [ClinvarVariationMapping](ClinvarVariationMapping.md): its ClinVar identifier (`exactMatch`), ClinGen allele identifiers (`closeMatch`), and other cross-references (`relatedMatch`).

---

## ClinVar-Specific Extensions

All ClinVar variant types share a set of extensions that provide ClinVar metadata not captured by the Cat-VRS base types. They are defined on [ClinvarCategoricalVariant](ClinvarCategoricalVariant.md#extensions):

| Extension | Description |
| --- | --- |
| `clinvarHgvsList` | Complete list of HGVS expressions — nucleotide and protein forms, MANE select/plus designations, and molecular consequences (SO terms). Each entry is an [HgvsListItem](HgvsListItem.md). |
| `clinvarGeneList` | Gene associations with `#/gene/` references to [ClinvarGene](ClinvarGene.md) records, relationship types, and sources. Each entry is a [GeneListItem](GeneListItem.md). |
| `categoricalVariationType` | The Cat-VRS category assigned: `CanonicalAllele`, `CategoricalCnvChange`, `CategoricalCnvCount`, or `Undefined`. |
| `definingVrsVariationType` | The VRS class from upstream processing: `Allele`, `CopyNumberChange`, `CopyNumberCount`, `Haplotype`, `Unknown`, or `Not Available`. |
| `clinvarVariationType` | The variation type as reported by ClinVar (e.g., `Deletion`, `single nucleotide variant`, `Duplication`). |
| `clinvarSubclassType` | The ClinVar subclass: `SimpleAllele`, `Haplotype`, or `Genotype`. |
| `clinvarCytogeneticLocation` | Cytogenetic band location (e.g., `17q21.31`). |
| `vrsPreProcessingIssue` | Issues detected during VRS pre-processing. Present only when issues exist. |
| `vrsProcessingException` | Errors from the VRS processing service. Present only when errors occurred. |

---

## VRS Composition Chain

Variants reference their resolved VRS representations through bundle-internal `#/` pointers:

```
Variation → #/allele/{id} → #/location/{id} → #/sequenceReference/{id}
```

Copy number variants follow the same chain through `#/copyNumberChange/` or `#/copyNumberCount/` records, each of which points to a `#/location/`.

- **Alleles** ([ClinvarAllele](ClinvarAllele.md)) carry the state, SPDI/HGVS/gnomAD expressions ([ClinvarAlleleExpression](ClinvarAlleleExpression.md)), and a location pointer
- **Copy number records** ([ClinvarCopyNumberChange](ClinvarCopyNumberChange.md), [ClinvarCopyNumberCount](ClinvarCopyNumberCount.md)) carry the copy change or count and a location pointer
- **Locations** ([ClinvarSequenceLocation](ClinvarSequenceLocation.md)) carry start/end coordinates and a sequence reference pointer
- **Sequence references** ([ClinvarSequenceReference](ClinvarSequenceReference.md)) carry the refget accession, molecule type, residue alphabet, and an `assembly` extension (e.g., `GRCh38`)

Each of these is a ClinVar profile of its VRS class: the VRS fields the pipeline does not write (such as `description` and `aliases`) are forbidden, and the nested object references are `#/` pointers into the bundle.
