# Data Model

The ClinVar-GKM release file organizes data into bundle sections, each containing objects of a specific class. These classes form a directed graph of relationships — variants reference alleles, alleles reference locations, statements reference propositions, and so on.

This page explains how the ClinVar-GKM schemas relate to the GA4GH classes, gives a visual overview of how the classes relate to each other, and links to detailed documentation for each class.

---

## An Implementation Schema

ClinVar-GKM publishes an **implementation schema**: ClinVar **profiles** of the GA4GH GKM classes (VRS, Cat-VRS, VA-Spec and GKM-Core), each narrowed to exactly what this project's pipeline produces. Every bundle section points at a ClinVar profile — `allele` at [ClinvarAllele](ClinvarAllele.md), `condition` at [ClinvarCondition](ClinvarCondition.md), `scv` at [ClinvarScvStatement](ClinvarScvStatement.md), and so on. The class pages in this section document those profiles: each page's **Information Model** lists only the properties the profile allows, with the narrowed types, values and pointer targets, and the base-class properties the profile forbids are listed below the table under **Not used by ClinVar-GKM**.

### Why the profiles are narrowed

- **You know exactly what can appear.** A profile lists the properties a record can carry and the values they can take. A property the profile forbids never appears in the bundle.
- **Validation catches pipeline regressions.** Every published bundle, full and delta, is checked against these schemas before release, and every record a release publishes is strictly validated ([Release Validation](../../reference/release-validation.md)). A property, value or pointer the pipeline should not write fails validation instead of reaching consumers.
- **Tooling can be derived from the schema.** Parquet column sets, documentation such as these class pages, and other tooling can be generated from a schema that describes the data precisely.
- **A ClinVar-GKM record is still a GA4GH record.** The GA4GH base classes are unchanged. Every ClinVar profile is an `allOf` of its GA4GH base class plus the narrowing, and narrowing only ever restricts — it never widens. A record that is valid against a ClinVar profile is valid against the GA4GH class it narrows.

### Narrowing rules

- **A property is forbidden only when the pipeline cannot write it.** Forbidden properties are set to `false`. A property the pipeline can write stays allowed even when the current release happens to contain none — for example the `isDiagnosticExclusionCriterionFor` predicate, or [ClinvarUndefinedProposition](ClinvarUndefinedProposition.md), the fallback for a classification that maps to no proposition type.
- **Enums are added only for values the pipeline fixes.** A `type`, a predicate, a `conceptType` or an extension `name` is constrained to its exact values. Values that come from ClinVar or from upstream lookup tables are not restricted further: the type and group codes in statement and proposition ids, for example, match `[A-Z]+` rather than a fixed list. Enumerations of ClinVar vocabularies that predate the narrowing, such as review status, are unchanged.
- **Every pointer is limited to the sections it may target.** A `#/<section>/<id>` pointer carries a pattern naming its target section or sections: a proposition's `subject` matches `^#/variation/`, an aggregate evidence line's `hasEvidenceItems` match `^#/(scv|vcv|rcv)/`.
- **Extensions are closed classes.** Each extension is its own class with a constant `name`, a typed `value` and no other properties, and each profile lists the extensions it accepts.
- **A profile is never more mature than its base.** A profile of a draft GA4GH class is itself draft.
- **Section keys match the exact id format.** Each bundle section's keys must match the full id the pipeline builds — a 32-character VRS digest, a 9-digit accession, a 64-character SHA-256 therapy key — not just a prefix. See [ID References](../id-references.md).
- **Validation runs on the real published bundles**, not on hand-built samples, so export bugs cannot hide.

### When the pipeline changes

A new property, or a new value for a field the pipeline fixes, is a schema change and is published under a new schema version — the version every bundle states in its `schema_version`. See [Versioning & Releases](../../reference/versioning.md).

---

## Bundle Section Map

The release bundle is a single JSON object of **named sections** — each section is a keyed collection mapping a typed id to one object. Objects link across sections with `#/section/id` JSON pointers. The map below shows every section, its object type, an example id, and its outgoing references. See [ID References](../id-references.md) for the full pointer catalog.

<iframe src="../../assets/diagrams/bundle-section-map.html"
        style="width:100%; height:660px; border:1px solid rgba(128,128,128,.25); border-radius:6px;"
        title="ClinVar-GKM bundle section map"
        loading="lazy"></iframe>

The map renders at full size in a scrollable frame — scroll within it to follow the reference chain from statements down to VRS sequence references. Each drawer links to that section's class reference page.

**Reading the map:**

- **`{ } key`** is the section name — the JSON key under which that section's objects live
- **The pill** is an example object id (the key within the section)
- **`field → #/section/`** lines are the outgoing cross-section references an object in that section carries
- **Solid arrows** trace the primary reference flow between section clusters; **dashed** arrows are optional or back-references (e.g., evidence items pointing back at statements)
- The four `proposition*` sections group the propositions by **meaning** (pathogenicity, oncogenicity, somatic clinical impact, ClinVar custom); a proposition's section is a function of its `type`

---

## Variation Classes

These classes represent the variant and its genomic context. Each section's records are a ClinVar profile of the VRS or Cat-VRS class; see [Variations](variations.md) for the variant type hierarchy.

| Class | Bundle Section | Key Pattern | Description |
| --- | --- | --- | --- |
| [ClinvarSequenceReference](ClinvarSequenceReference.md) | `sequenceReference` | `SQ.{digest}` | Reference sequence with refget accession, molecule type, residue alphabet, and assembly |
| [ClinvarSequenceLocation](ClinvarSequenceLocation.md) | `location` | `ga4gh:SL.{digest}` | Position or range on a sequence reference |
| [ClinvarAllele](ClinvarAllele.md) | `allele` | `ga4gh:VA.{digest}` | Specific sequence change at a location |
| [ClinvarCopyNumberCount](ClinvarCopyNumberCount.md) | `copyNumberCount` | `ga4gh:CN.{digest}` | Absolute copy count at a location |
| [ClinvarCopyNumberChange](ClinvarCopyNumberChange.md) | `copyNumberChange` | `ga4gh:CX.{digest}` | Copy gain or loss at a location |
| [ClinvarGene](ClinvarGene.md) | `gene` | `ncbigene:{id}` | Gene concept with NCBI Gene primaryCoding and HGNC mapping |
| [ClinvarCategoricalVariant](ClinvarCategoricalVariant.md) | `variation` | `clinvar:{id}` | ClinVar variation with Cat-VRS representation and extensions |

Every `{digest}` is the 32-character VRS digest.

---

## Supporting Classes

These classes represent the conditions, therapies, submitters, and propositions that support classification statements. Proposition content is delivered in **four sections grouped by meaning**; see [Propositions](propositions.md) for the type each section holds.

| Class | Bundle Section | Key Pattern | Description |
| --- | --- | --- | --- |
| [ClinvarCondition](ClinvarCondition.md) | `condition` | `clinvar.trait:{id}` | Disease or phenotype with its primary coding and cross-references |
| [ClinvarConditionSet](ClinvarConditionSet.md) | `conditionSet` | `clinvar.traitset:{id}` or `clinvar.conditionset:vcv-{md5}` | Grouping of conditions with an AND/OR membership operator |
| [ClinvarTherapy](ClinvarTherapy.md) | `therapy` | `clinvar.therapy:{sha256}` | Drug therapy (content-addressed); `object` of therapeutic propositions via `#/therapy/` |
| [ClinvarTherapyGroup](ClinvarTherapyGroup.md) | `therapyGroup` | `clinvar.therapygroup:{sha256}` | Combination therapy whose `concepts` reference `#/therapy/` members |
| [ClinvarSubmitter](ClinvarSubmitter.md) | `submitter` | `clinvar.submitter:{id}` | Submitting organization |
| [ClinvarVariantPathogenicityProposition](ClinvarVariantPathogenicityProposition.md) | `propositionPathogenicity` | `{scv_id}-PATH` | Pathogenicity propositions |
| [ClinvarVariantOncogenicityProposition](ClinvarVariantOncogenicityProposition.md) | `propositionOncogenicity` | `{scv_id}-ONCO` | Oncogenicity propositions |
| [ClinvarVariantClinicalSignificanceProposition](ClinvarVariantClinicalSignificanceProposition.md), [Diagnostic](ClinvarVariantDiagnosticProposition.md), [Prognostic](ClinvarVariantPrognosticProposition.md), [TherapeuticResponse](ClinvarVariantTherapeuticResponseProposition.md) | `propositionSomaticClinicalImpact` | `{scv_id}-{CODE}` | Somatic clinical impact propositions |
| [ClinvarGermlineCustomProposition](ClinvarGermlineCustomProposition.md) subtypes | `propositionClinvarCustom` | `{scv_id}-{CODE}` | ClinVar-specific proposition types (Risk Factor, Protective, Drug Response, …, Undefined) |

Proposition keys show the SCV form; VCV and RCV propositions are keyed `{accession}-{group}-{PROP}[-{level}]`, and somatic clinical impact propositions may add `-{TIER}`. See [ID References](../id-references.md) for every key format.

---

## Statement Classes

These classes represent classification statements at different levels of aggregation and the evidence lines that connect them. All statements are profiles of the VA-Spec Statement type documented under [Statements](statements.md).

| Class | Bundle Section | Key Pattern | Description |
| --- | --- | --- | --- |
| [ClinvarScvStatement](ClinvarScvStatement.md) | `scv` | `clinvar.submission:{scv_id}.{ver}` | Submitted classification |
| [ClinvarVcvStatement](ClinvarVcvStatement.md) | `vcv` | `{vcv}.{ver}-{group}-{PROP}[-{level}[-{TIER}]]` | Variant-level aggregate |
| [ClinvarRcvStatement](ClinvarRcvStatement.md) | `rcv` | `{rcv}.{ver}-{group}-{PROP}[-{level}[-{TIER}]]` | Condition-level aggregate |
| [ClinvarSomaticEvidenceLine](ClinvarSomaticEvidenceLine.md) | `evidenceLine` | `clinvar.submission:{scv_id}.{ver}` | Evidence line of a somatic clinical impact SCV statement |
| [ClinvarAggregateEvidenceLine](ClinvarAggregateEvidenceLine.md) | `evidenceLine` | `{vcv_or_rcv_id}.contributing` / `.non-contributing` | Evidence line of a VCV or RCV aggregate statement |

See [Statements](statements.md) for the aggregation structure and [Evidence Lines](evidence.md) for both kinds of evidence line.
