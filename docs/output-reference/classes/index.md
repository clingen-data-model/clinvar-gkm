# Data Model

The ClinVar-GKM release file organizes data into bundle sections, each containing objects of a specific class. These classes form a directed graph of relationships — variants reference alleles, alleles reference locations, statements reference propositions, and so on.

This page provides a visual overview of how the classes relate to each other, with links to detailed documentation for each class.

---

## Bundle Section Map

The release bundle is a single JSON object of **named sections** — each section is a dictionary mapping a typed id to one object. Objects link across sections with `#/section/id` JSON pointers. The map below shows every section, its object type, an example id, and its outgoing references. See [ID References](../id-references.md) for the full pointer catalog.

<iframe src="../../assets/diagrams/bundle-section-map.html"
        style="width:100%; height:660px; border:1px solid rgba(128,128,128,.25); border-radius:6px;"
        title="ClinVar-GKM bundle section map"
        loading="lazy"></iframe>

The map renders at full size in a scrollable frame — scroll within it to follow the reference chain from statements down to VRS sequence references. Each drawer links to that section's class reference page.

**Reading the map:**

- **`{ } key`** is the section name — the JSON key under which that section's dictionary of objects lives
- **The pill** is an example object id (the dictionary key within the section)
- **`field → #/section/`** lines are the outgoing cross-section references an object in that section carries
- **Solid arrows** trace the primary reference flow between section clusters; **dashed** arrows are optional or back-references (e.g., evidence items pointing back at statements)
- The four `*-proposition` sections are datatype-homogeneous **delivery groups** of the proposition content, keyed by proposition type

---

## Variation Classes

These classes represent the variant and its genomic context. VRS types (SequenceReference, Location, Allele) use their upstream GA4GH schemas directly. ClinVar-specific profiles are documented under [Variations](variations.md).

| Class | Bundle Section | Key Pattern | Description |
| --- | --- | --- | --- |
| SequenceReference | `sequenceReference` | `SQ.{digest}` | Reference sequence with refget accession, molecule type, and assembly |
| Location | `location` | `ga4gh:SL.{digest}` | Position or range on a sequence reference |
| Allele | `allele` | `ga4gh:VA.{digest}` | Specific sequence change at a location |
| Gene | `gene` | `ncbigene:{id}` | Gene MappableConcept with NCBI Gene primaryCoding and HGNC mapping |
| [ClinvarCategoricalVariant](ClinvarCategoricalVariant.md) | `variation` | `clinvar:{id}` | ClinVar variation with Cat-VRS representation and extensions |

See [Variations](variations.md) for the full variant type hierarchy and extension documentation.

---

## Supporting Classes

These classes represent the conditions, submitters, and propositions that support classification statements. Conditions and submitters use upstream GA4GH types. Proposition content is delivered in **four datatype-homogeneous sections** keyed by proposition type — together they hold all 13 [ClinvarProposition](ClinvarProposition.md) types.

| Class | Bundle Section | Key Pattern | Description |
| --- | --- | --- | --- |
| Condition | `condition` | `clinvar.trait:{id}` | Disease or phenotype with MedGen coding and cross-references |
| ConditionSet | `conditionSet` | `clinvar.traitset:{id}` | Grouping of conditions with AND/OR membership operator |
| Therapy | `therapy` | `clinvar.therapy:{sha256}` | Drug therapy (content-addressed); `object` of therapeutic propositions via `#/therapy/` |
| TherapyGroup | `therapyGroup` | `clinvar.therapygroup:{sha256}` | Combination therapy whose `concepts` reference `#/therapy/` members |
| Submitter | `submitter` | `clinvar.submitter:{id}` | Submitting organization |
| [ClinvarProposition](ClinvarProposition.md) | `varcond-proposition` | `{scv_id}-{CODE}` | Variant–condition propositions: Pathogenicity, Clinical Significance, Diagnostic, Prognostic |
| [ClinvarProposition](ClinvarProposition.md) | `vartumor-proposition` | `{scv_id}-ONCO` | Variant–tumor-type Oncogenicity propositions |
| [ClinvarProposition](ClinvarProposition.md) | `vartherapy-proposition` | `{scv_id}-TR` | Variant–therapy Therapeutic Response propositions |
| [ClinvarProposition](ClinvarProposition.md) | `varcustom-proposition` | `{scv_id}-{CODE}` | ClinVar-specific proposition types (Risk Factor, Protective, Drug Response, …) |

See [Propositions](propositions.md) for the full type/code/predicate reference and [ID References](../id-references.md) for how the delivery groups are keyed.

---

## Statement Classes

These classes represent classification statements at different levels of aggregation. All are profiles of the VA-Spec Statement type documented under [Statements](statements.md).

| Class | Bundle Section | Key Pattern | Description |
| --- | --- | --- | --- |
| [ClinvarScvStatement](ClinvarScvStatement.md) | `scv` | `clinvar.submission:{id}.{ver}` | Submitted classification |
| [ClinvarVcvStatement](ClinvarVcvStatement.md) | `vcv` | `{vcv}-{group}-{prop}-{level}` | Variant-level aggregate |
| [ClinvarRcvStatement](ClinvarRcvStatement.md) | `rcv` | `{rcv}-{group}-{prop}-{level}` | Condition-level aggregate |
| [ClinvarSomaticEvidenceLine](ClinvarSomaticEvidenceLine.md) | `evidenceLine` | `{scv_id}.{ver}` / `{agg_id}.contributing` | Evidence line referenced via `hasEvidenceLines` |

See [Statements](statements.md) for the aggregation structure and [Evidence Lines](evidence.md) for the somatic tier mapping.
