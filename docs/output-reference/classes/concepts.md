# Concepts

Genes, conditions, and therapies are GKM-Core and VA-Spec concepts — a `MappableConcept`, or a `ConceptSet` for groups. ClinVar-GKM narrows each to a ClinVar profile, and narrows the codings and mappings they carry to the fields the pipeline writes.

---

## Concept Sections

| ClinVar Profile | Base Class | Bundle Section | Description |
| --- | --- | --- | --- |
| [ClinvarGene](ClinvarGene.md) | `MappableConcept` | `gene` | An NCBI Gene, with its primary coding and its HGNC mapping |
| [ClinvarCondition](ClinvarCondition.md) | `Condition` | `condition` | A ClinVar trait, with its name, aliases, primary coding, and mappings |
| [ClinvarConditionSet](ClinvarConditionSet.md) | `ConditionSet` | `conditionSet` | A set of conditions: its `concepts` are `#/condition/` or `#/conditionSet/` pointers, joined by `membershipOperator` `AND` or `OR` |
| [ClinvarTherapy](ClinvarTherapy.md) | `Therapy` | `therapy` | A drug therapy named by its submitted text |
| [ClinvarTherapyGroup](ClinvarTherapyGroup.md) | `TherapyGroup` | `therapyGroup` | A combination therapy: its `concepts` are `#/therapy/` pointers |

Two kinds of condition set share the `conditionSet` section: ClinVar trait sets (`clinvar.traitset:{id}`) and sets minted for VCV aggregates (`clinvar.conditionset:vcv-{md5}`).

---

## Codings, Mappings, and Terms

These classes appear inside concepts and statements rather than as section records.

| Class | Used For |
| --- | --- |
| [ClinvarCoding](ClinvarCoding.md) | A code and its system, with an optional name and IRIs — the primary coding of a gene, condition, or qualifier |
| [ClinvarMappingCoding](ClinvarMappingCoding.md) | The coding of a concept mapping: a ClinvarCoding without a name |
| [ClinvarConceptMapping](ClinvarConceptMapping.md) | A mapping of a concept to a ClinvarMappingCoding, with its SKOS relation |
| [ClinvarTermCoding](ClinvarTermCoding.md) | The coding of a ClinVar term: only a code and a system |
| [ClinvarCodedTerm](ClinvarCodedTerm.md) | A term of a ClinVar vocabulary (a strength, for example): a concept type, a name and, when it has one, a ClinvarTermCoding |
| [ClinvarTerm](ClinvarTerm.md) | A term with no coding (a quality, for example): only a concept type and a name |

The statement classes build on these: an SCV's `strength` is a [ClinvarStrength](ClinvarStrength.md) (a ClinvarCodedTerm), and an aggregate's `strength` and every `quality` are ClinvarTerms. See [Statements](statements.md).
